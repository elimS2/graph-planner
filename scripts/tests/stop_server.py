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
    if not env_path.exists():
        return values
    try:
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


def read_health(base_url: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    try:
        import urllib.request

        req = urllib.request.Request(f"{base_url}/api/v1/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - local call
            body = resp.read().decode("utf-8", errors="ignore")
        js = json.loads(body)
        return js.get("data") if isinstance(js, dict) else None
    except Exception:
        return None


def is_port_listening(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def kill_pid(pid: int) -> Dict[str, Any]:
    result: Dict[str, Any] = {"pid": pid, "method": None, "returncode": None, "error": None}
    try:
        if os.name == "nt":
            # Kill process tree forcefully on Windows
            result["method"] = "taskkill"
            proc = subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True, text=True)  # nosec
            result["returncode"] = proc.returncode
            result["stdout"] = (proc.stdout or "").strip()
            result["stderr"] = (proc.stderr or "").strip()
        else:
            import signal

            result["method"] = "os.kill-SIGTERM/SIGKILL"
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                return result
            time.sleep(0.6)
            try:
                os.kill(pid, 0)
                # still alive -> SIGKILL
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except Exception as e:  # pragma: no cover
        result["error"] = str(e)
    return result


def write_json_result(root: Path, data: Dict[str, Any]) -> None:
    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop local Flask server by PID from /api/v1/health")
    parser.add_argument("--host", default=None, help="Base URL, e.g. http://127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="Port (default from .env PORT or 5050)")
    parser.add_argument("--timeout", type=float, default=2.0, help="HTTP connect timeout seconds")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)

    host = (args.host or envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    port = int(args.port or envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    started = datetime.utcnow().isoformat() + "Z"
    result: Dict[str, Any] = {
        "action": "stop_server",
        "base_url": base_url,
        "started": started,
    }

    # Probe health for PID
    health = read_health(base_url, timeout=args.timeout)
    if not health or not isinstance(health, dict) or ("pid" not in health or not health.get("pid")):
        # Fallback: enumerate and kill listeners by port (Windows PowerShell)
        result["pid_before"] = None
        result["fallback"] = {"by_port": port}
        attempts: list[dict[str, Any]] = []
        try:
            for attempt in range(1, 11):
                entry: dict[str, Any] = {"attempt": attempt}
                if os.name == "nt":
                    ps_cmd = [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | Out-String"
                    ]
                    proc = subprocess.run(ps_cmd, capture_output=True, text=True)  # nosec
                    pids: list[int] = []
                    if proc.returncode == 0:
                        for line in (proc.stdout or "").splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                pids.append(int(line))
                            except ValueError:
                                pass
                    entry["pids_found"] = pids
                    kills: list[dict[str, Any]] = []
                    for pid in pids:
                        kills.append(kill_pid(pid))
                    entry["kills"] = kills
                else:
                    try:
                        proc = subprocess.run(["lsof", f"-i:{port}", "-t"], capture_output=True, text=True)  # nosec
                        pids: list[int] = []
                        if proc.returncode == 0:
                            for line in (proc.stdout or "").splitlines():
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    pids.append(int(line))
                                except ValueError:
                                    pass
                        entry["pids_found"] = pids
                        kills: list[dict[str, Any]] = []
                        for pid in pids:
                            kills.append(kill_pid(pid))
                        entry["kills"] = kills
                    except Exception as e:  # pragma: no cover
                        entry["error"] = str(e)

                attempts.append(entry)
                time.sleep(0.6)
                if not is_port_listening("127.0.0.1", port, 0.5):
                    result["status"] = "stopped"
                    break
            else:
                result["status"] = "still_running"
        except Exception as e:  # pragma: no cover
            result["fallback_error"] = str(e)

        result["kill_attempts_fallback"] = attempts
        write_json_result(root, result)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "stopped" else 2

    pid = health.get("pid")
    result["pid_before"] = pid

    # Iterative kill up to 10 attempts
    attempts_log = []
    for attempt in range(1, 11):
        kill_info = kill_pid(int(pid))
        attempts_log.append({"attempt": attempt, **kill_info})
        time.sleep(0.6)
        health_after = read_health(base_url, timeout=0.8)
        listening = is_port_listening("127.0.0.1", port, 0.5)
        if not health_after and not listening:
            result["status"] = "stopped"
            break
        # refresh pid from health if still running
        if health_after and isinstance(health_after, dict) and health_after.get("pid"):
            try:
                pid = int(health_after.get("pid"))
            except Exception:
                pass
    else:
        result["status"] = "still_running"
        result["health_after"] = read_health(base_url, timeout=0.8)

    result["kill_attempts"] = attempts_log

    write_json_result(root, result)
    # Print to stdout too (may be redirected by shell)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "stopped" else 2


if __name__ == "__main__":
    raise SystemExit(main())


