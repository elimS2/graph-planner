from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import psutil  # type: ignore
except Exception as e:  # pragma: no cover
    print(json.dumps({"ok": False, "error": f"psutil not available: {e}"}))
    sys.exit(1)


def project_root() -> Path:
    # scripts/tests -> scripts -> project root
    return Path(__file__).resolve().parents[2]


def find_server_pids(root: Path) -> List[int]:
    candidates: List[int] = []
    root_str = str(root)
    for p in psutil.process_iter(attrs=["pid", "name", "cmdline", "cwd"]):
        try:
            cmd = p.info.get("cmdline") or []
            cwd = p.info.get("cwd") or ""
            if not isinstance(cmd, list):
                continue
            cmdline_join = " ".join(cmd)
            if "wsgi.py" in cmdline_join and root_str in (cwd or root_str) or root_str in cmdline_join:
                candidates.append(int(p.info.get("pid") or p.pid))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return sorted(set(candidates))


def stop_pid(pid: int, timeout: float = 5.0) -> bool:
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
            return True
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=timeout)
            return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def start_server(root: Path) -> Dict[str, Any]:
    import subprocess

    python_path = root / ".venv" / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = Path(sys.executable)

    log_dir = root
    ts = time.strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"server-restart-{ts}.log"
    env = os.environ.copy()
    env.setdefault("PORT", "5050")
    # Do not override provider here; rely on .env already present

    # Detach on Windows
    creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    with open(log_path, "ab", buffering=0) as lf:
        p = subprocess.Popen(
            [str(python_path), str(root / "wsgi.py")],
            cwd=str(root),
            env=env,
            stdout=lf,
            stderr=lf,
            creationflags=creationflags,
        )
    # small delay to allow boot
    time.sleep(0.6)
    alive = psutil.pid_exists(p.pid)
    return {"pid": p.pid, "log": str(log_path), "alive": alive}


def main() -> None:
    root = project_root()
    before = find_server_pids(root)
    found_pid = before[0] if before else None

    stopped_ok = False
    if found_pid is not None:
        stopped_ok = stop_pid(found_pid)
        # wait a moment and re-check
        time.sleep(0.4)
    after_stop = find_server_pids(root)

    started = start_server(root)
    new_pids = find_server_pids(root)

    out = {
        "root": str(root),
        "found_pid": found_pid,
        "stopped": bool(stopped_ok or found_pid is None),
        "pids_after_stop": new_pids if not new_pids else new_pids,  # for visibility
        "started": started,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()


