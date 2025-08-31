from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def load_dotenv_values(root: Path) -> Dict[str, str]:
    env_path = root / ".env"
    values: Dict[str, str] = {}
    try:
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    except Exception:
        pass
    return values


def is_port_listening(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def write_json_result(root: Path, data: Dict[str, Any]) -> None:
    # Write to two locations: op-specific file (if provided) and generic test JSON
    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_op_status(root: Path, op_id: Optional[str], data: Dict[str, Any]) -> None:
    if not op_id:
        return
    try:
        op_dir = root / "instance" / "restart_ops"
        op_dir.mkdir(parents=True, exist_ok=True)
        (op_dir / f"{op_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def read_health(base_url: str, timeout: float = 1.5) -> Optional[Dict[str, Any]]:
    try:
        import urllib.request

        req = urllib.request.Request(f"{base_url}/api/v1/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - local call
            body = resp.read().decode("utf-8", errors="ignore")
        js = json.loads(body)
        return js.get("data") if isinstance(js, dict) else None
    except Exception:
        return None


def run_silent(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a subprocess without showing a console window on Windows.

    Returns CompletedProcess with stdout/stderr captured as text.
    """
    kwargs: Dict[str, Any] = {"capture_output": True, "text": True}
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        si.wShowWindow = 0  # SW_HIDE
        kwargs.update({
            "startupinfo": si,
            "creationflags": 0x08000000 | 0x00000008 | 0x00000200,  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        })
    return subprocess.run(cmd, **kwargs)  # nosec


def pids_listening_on_port(port: int) -> list[int]:
    """Return list of PIDs listening on given TCP port (best-effort)."""
    pids: list[int] = []
    try:
        if os.name == "nt":
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | Out-String",
            ]
            proc = run_silent(cmd)
            if proc.returncode == 0:
                for line in (proc.stdout or "").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pids.append(int(line))
                    except ValueError:
                        pass
        else:
            proc = subprocess.run(["lsof", f"-i:{port}", "-t"], capture_output=True, text=True)  # nosec
            if proc.returncode == 0:
                for line in (proc.stdout or "").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pids.append(int(line))
                    except ValueError:
                        pass
    except Exception:
        pass
    # deduplicate
    return sorted(list({p for p in pids}))

def main() -> int:
    parser = argparse.ArgumentParser(description="Relaunch dev server after current instance exits")
    parser.add_argument("--host", default=None, help="Base URL host, e.g. http://127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="Port to wait for and start on")
    parser.add_argument("--op-id", default=None, help="Operation id to report status into instance/restart_ops")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    # Ensure project root is importable for relative imports (e.g., app.utils.process)
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    envv = load_dotenv_values(root)
    host = (args.host or envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    if not (host.startswith("http://") or host.startswith("https://")):
        host = f"http://{host}"
    port = int(args.port or envv.get("PORT") or 5050)

    started = datetime.utcnow().isoformat() + "Z"
    result: Dict[str, Any] = {
        "action": "restart_server",
        "host": host,
        "port": port,
        "started": started,
        "phases": [],
    }
    if args.op_id:
        result["op_id"] = args.op_id
    # Write initial status as early as possible
    result["status"] = "started"
    write_op_status(root, args.op_id, result)

    # Capture pid_before (best-effort)
    h0 = read_health(f"{host}:{port}", timeout=0.8)
    try:
        result["pid_before"] = int(h0.get("pid")) if isinstance(h0, dict) and h0.get("pid") else None
    except Exception:
        result["pid_before"] = None

    # Phase 1: immediately stop current server if running (by PID or by-port), then wait for port to go down
    phase1 = {"phase": "kill_by_pid", "pid": result.get("pid_before"), "attempts": 0, "kills": [], "by_port": []}
    def kill_pid(pid_val: int) -> Dict[str, Any]:
        info: Dict[str, Any] = {"pid": pid_val, "method": None, "returncode": None, "error": None}
        try:
            if os.name == "nt":
                info["method"] = "taskkill"
                # Important: do NOT use /T (kill tree), it may terminate this relauncher if the OS still
                # considers it a child process of the server. We only kill the target PID.
                proc = run_silent(["taskkill", "/PID", str(pid_val), "/F"])  # nosec
                info["returncode"] = proc.returncode
                info["stdout"] = (proc.stdout or "").strip()
                info["stderr"] = (proc.stderr or "").strip()
            else:
                import signal
                info["method"] = "SIGTERM/SIGKILL"
                try:
                    os.kill(pid_val, signal.SIGTERM)
                except ProcessLookupError:
                    return info
                time.sleep(0.6)
                try:
                    os.kill(pid_val, 0)
                    os.kill(pid_val, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except Exception as e:
            info["error"] = str(e)
        return info

    pid_b = result.get("pid_before")
    candidates: list[int] = []
    if isinstance(pid_b, int) and pid_b > 0:
        candidates.append(pid_b)
    if not candidates:
        candidates = pids_listening_on_port(port)
        phase1["by_port"] = candidates
    if candidates:
        for i in range(1, 21):  # up to ~12s
            phase1["attempts"] = i
            for p in candidates:
                phase1["kills"].append(kill_pid(p))
            time.sleep(0.6)
            if not is_port_listening("127.0.0.1", port, timeout=0.5):
                break
    else:
        # No PID candidates — wait a bit for shutdown
        for i in range(10):
            phase1["attempts"] = i + 1
            if not is_port_listening("127.0.0.1", port, timeout=0.5):
                break
            time.sleep(0.6)
    result["phases"].append(phase1)
    write_op_status(root, args.op_id, result)

    if is_port_listening("127.0.0.1", port, timeout=0.5):
        result["status"] = "port_still_in_use"
        write_op_status(root, args.op_id, result)
        write_json_result(root, result)
        print(json.dumps(result, ensure_ascii=False))
        return 2

    # Phase 2: start the server detached
    phase2 = {"phase": "start_server", "ok": False}
    # Prefer pythonw.exe on Windows to avoid console window
    py = sys.executable or "python"
    if os.name == "nt":
        try:
            cand = Path(py).with_name("pythonw.exe")
            if cand.exists():
                py = str(cand)
        except Exception:
            pass
    start_script = root / "scripts" / "start_flask_server.py"
    args2 = [py, str(start_script)]
    try:
        from app.utils.process import spawn_detached_silent  # type: ignore
        spawn_detached_silent(args2, cwd=str(root))
        phase2["ok"] = True
    except Exception as e:
        phase2["error"] = str(e)
        result["phases"].append(phase2)
        result["status"] = "spawn_failed"
        write_op_status(root, args.op_id, result)
        write_json_result(root, result)
        print(json.dumps(result, ensure_ascii=False))
        return 2
    result["phases"].append(phase2)
    write_op_status(root, args.op_id, result)

    # Phase 3: wait until health comes back and PID changes
    phase3 = {"phase": "wait_up", "attempts": 0}
    for i in range(90):  # ~90s
        phase3["attempts"] = i + 1
        try:
            h = read_health(f"{host}:{port}", timeout=1.0)
            if h:
                try:
                    result["pid_after"] = int(h.get("pid")) if h.get("pid") else None
                except Exception:
                    result["pid_after"] = None
                if result.get("pid_before") and result.get("pid_after") and result["pid_after"] != result["pid_before"]:
                    result["status"] = "restarted"
                    result["finished"] = datetime.utcnow().isoformat() + "Z"
                    result["ok"] = True
                    result["phases"].append(phase3)
                    write_op_status(root, args.op_id, result)
                    write_json_result(root, result)
                    print(json.dumps(result, ensure_ascii=False))
                    return 0
                # If no pid_before, accept first healthy state as success
                if not result.get("pid_before") and result.get("pid_after"):
                    result["status"] = "restarted"
                    result["finished"] = datetime.utcnow().isoformat() + "Z"
                    result["ok"] = True
                    result["phases"].append(phase3)
                    write_op_status(root, args.op_id, result)
                    write_json_result(root, result)
                    print(json.dumps(result, ensure_ascii=False))
                    return 0
        except Exception:
            pass
        # Heartbeat status during wait_up
        write_op_status(root, args.op_id, result)
        time.sleep(1.0)

    result["phases"].append(phase3)
    # Distinguish cases
    if result.get("pid_after") == result.get("pid_before") and result.get("pid_after") is not None:
        result["status"] = "pid_unchanged"
    else:
        result["status"] = "started_but_unhealthy"
    result["finished"] = datetime.utcnow().isoformat() + "Z"
    write_op_status(root, args.op_id, result)
    write_json_result(root, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


