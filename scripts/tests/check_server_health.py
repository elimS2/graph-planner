from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _ensure_http_scheme(value: str) -> str:
    v = value.strip()
    if not (v.startswith("http://") or v.startswith("https://")):
        return f"http://{v}"
    return v


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


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)

    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    started = datetime.utcnow().isoformat() + "Z"
    out: Dict[str, Any] = {
        "action": "check_server_health",
        "base_url": base_url,
        "started": started,
    }

    # Poll up to ~15s for server to become healthy
    health: Optional[Dict[str, Any]] = None
    for _ in range(30):
        health = read_health(base_url, timeout=1.2)
        if health:
            break
        time.sleep(0.5)

    finished = datetime.utcnow().isoformat() + "Z"
    out["finished"] = finished
    if health:
        out["ok"] = True
        out["health"] = health
    else:
        out["ok"] = False
        out["error"] = "No response from /api/v1/health"

    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())


