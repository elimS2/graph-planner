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
    from urllib import request
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)
    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    out: Dict[str, Any] = {"action": "make_status_change", "base_url": base_url}
    try:
        # pick first project and node, then toggle status planned -> in-progress -> done
        with request.urlopen(request.Request(f"{base_url}/api/v1/projects"), timeout=3.0) as resp:
            projs = json.loads(resp.read().decode("utf-8", errors="ignore"))
        pid = (projs.get("data") or [{}])[0].get("id")
        with request.urlopen(request.Request(f"{base_url}/api/v1/projects/{pid}/nodes"), timeout=3.0) as resp:
            nodes = json.loads(resp.read().decode("utf-8", errors="ignore"))
        items = (nodes.get("data") or [])
        if not items:
            raise RuntimeError("no nodes")
        nid = items[0]["id"]
        # Read current node
        with request.urlopen(request.Request(f"{base_url}/api/v1/nodes/{nid}"), timeout=2.0) as resp:
            node = json.loads(resp.read().decode("utf-8", errors="ignore"))
        st = ((node.get("data") or {}).get("status") or "planned")
        nxt = "in-progress" if st == "planned" else ("done" if st == "in-progress" else "planned")
        req = request.Request(f"{base_url}/api/v1/nodes/{nid}", method="PATCH", headers={"Content-Type": "application/json"}, data=json.dumps({"status": nxt}).encode("utf-8"))
        with request.urlopen(req, timeout=3.0) as resp:
            _ = resp.read()
        # Fetch history
        with request.urlopen(request.Request(f"{base_url}/api/v1/nodes/{nid}/status-history"), timeout=2.0) as resp:
            hist = json.loads(resp.read().decode("utf-8", errors="ignore"))
        out["ok"] = True
        out["node_id"] = nid
        out["new_status"] = nxt
        out["history_count"] = len(hist.get("data") or [])
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


