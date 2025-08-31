from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


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


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)

    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    # pick any node id from template if available, otherwise a dummy that should 404
    # Prefer reading from instance DB is out of scope for a simple HTTP test
    test_node_id = envv.get("TEST_NODE_ID") or "00000000-0000-0000-0000-000000000000"

    url = f"{base_url}/api/v1/nodes/{test_node_id}/status-history"

    out: Dict[str, Any] = {"action": "test_status_history", "url": url}

    try:
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.0) as resp:  # nosec - local
            body = resp.read().decode("utf-8", errors="ignore")
            js = json.loads(body)
            out["ok"] = True
            out["status"] = resp.status
            out["data_keys"] = list(js.keys()) if isinstance(js, dict) else []
    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)

    out_path = root / "scripts" / "tests" / "json-result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())


