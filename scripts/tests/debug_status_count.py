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


def http_json(url: str, timeout: float = 3.0) -> Any:
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:  # nosec
        body = resp.read().decode("utf-8", errors="ignore")
    return json.loads(body)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)
    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base = f"{host}:{port}"

    # Node id from the Task Panel screenshot
    node_id = envv.get("PANEL_NODE_ID") or "a0ff26bc-73b4-4f62-b8c7-094f839b0196"

    out: Dict[str, Any] = {"action": "debug_status_count", "base_url": base, "node_id": node_id}
    try:
        out["db"] = http_json(f"{base}/api/v1/debug/db-url", timeout=2.0)
        out["debug_status"] = http_json(f"{base}/api/v1/debug/status-count/{node_id}", timeout=3.0)
        out["history_api"] = http_json(f"{base}/api/v1/nodes/{node_id}/status-history", timeout=3.0)
        out["ok"] = True
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


