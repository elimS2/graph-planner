from __future__ import annotations

import json
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


def write_json_result(root: Path, data: Dict[str, Any]) -> None:
    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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


def post_restart(base_url: str, timeout: float = 2.5) -> Dict[str, Any]:
    try:
        import urllib.request

        req = urllib.request.Request(f"{base_url}/api/v1/settings/restart", method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - local call
            body = resp.read().decode("utf-8", errors="ignore")
            return {"status": int(resp.status), "body": body}
    except Exception:
        return {"status": 0, "body": None}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)
    host = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    # Ensure scheme present
    if not (host.startswith("http://") or host.startswith("https://")):
        host = f"http://{host}"
    port = int(envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    started = datetime.utcnow().isoformat() + "Z"
    result: Dict[str, Any] = {
        "action": "restart_via_api",
        "base_url": base_url,
        "started": started,
        "phases": [],
    }

    # Phase A: capture pid before
    before = read_health(base_url)
    result["before"] = before

    # Phase B: POST restart
    post = post_restart(base_url)
    result["post_status"] = post.get("status")
    op_id: Optional[str] = None
    if post.get("status") == 202 and isinstance(post.get("body"), str):
        try:
            jr = json.loads(post.get("body") or "{}")
            op_id = (jr.get("data") or {}).get("op_id")
        except Exception:
            op_id = None
    result["op_id"] = op_id
    if post.get("status") != 202:
        result["status"] = "restart_endpoint_failed"
        write_json_result(root, result)
        print(json.dumps(result, ensure_ascii=False))
        return 2

    # Phase C/D: poll status endpoint if op_id present; fallback to health
    op_phase = {"phase": "poll_status", "attempts": 0}
    after: Optional[Dict[str, Any]] = None
    deadline = time.time() + 60
    while time.time() < deadline:
        op_phase["attempts"] = op_phase.get("attempts", 0) + 1
        if op_id:
            try:
                import urllib.request
                r = urllib.request.urlopen(f"{base_url}/api/v1/settings/restart/status/{op_id}", timeout=1.2)  # nosec
                body = r.read().decode("utf-8", errors="ignore")
                js = json.loads(body)
                data = js.get("data") if isinstance(js, dict) else None
                if data and data.get("status") in ("restarted", "started_but_unhealthy", "port_still_in_use", "spawn_failed"):
                    result["op_status"] = data
                    after = read_health(base_url, timeout=0.8)
                    break
            except Exception:
                pass
        h = read_health(base_url, timeout=0.8)
        if h:
            # accept only if pid changed
            try:
                new_pid = int(h.get("pid")) if h.get("pid") is not None else None
                old_pid = int(before.get("pid")) if before and before.get("pid") is not None else None
            except Exception:
                new_pid = None; old_pid = None
            if old_pid is None or (new_pid is not None and new_pid != old_pid):
                after = h
                break
        time.sleep(1.0)
    result["phases"].append(op_phase)

    if not after:
        result["status"] = "did_not_come_back"
        write_json_result(root, result)
        print(json.dumps(result, ensure_ascii=False))
        return 2

    # Verify pid changed (best-effort)
    result["after"] = after
    try:
        pid_before = int(before.get("pid")) if isinstance(before, dict) and before.get("pid") is not None else None
        pid_after = int(after.get("pid")) if isinstance(after, dict) and after.get("pid") is not None else None
    except Exception:
        pid_before = None
        pid_after = None
    result["pid_before"] = pid_before
    result["pid_after"] = pid_after
    result["pid_changed"] = (pid_before is not None and pid_after is not None and pid_before != pid_after)

    result["finished"] = datetime.utcnow().isoformat() + "Z"
    result["status"] = "restarted"
    write_json_result(root, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


