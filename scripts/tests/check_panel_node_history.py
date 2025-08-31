from __future__ import annotations

import json
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


def main() -> int:
    from urllib import request
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)
    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    title = "цвет линий"
    out: Dict[str, Any] = {"action": "check_panel_node_history", "base_url": base_url, "title": title}
    try:
        # find project by name
        with request.urlopen(request.Request(f"{base_url}/api/v1/projects"), timeout=3.0) as resp:
            projs = json.loads(resp.read().decode("utf-8", errors="ignore"))
        proj_id: Optional[str] = None
        for p in (projs.get("data") or []):
            if isinstance(p, dict) and ("Graph Planner" in str(p.get("name") or "")):
                proj_id = p.get("id")
                break
        if not proj_id:
            out["ok"] = False
            out["error"] = "Graph Planner project not found"
        else:
            with request.urlopen(request.Request(f"{base_url}/api/v1/projects/{proj_id}/nodes"), timeout=4.0) as resp:
                nodes = json.loads(resp.read().decode("utf-8", errors="ignore"))
            node_id: Optional[str] = None
            for n in (nodes.get("data") or []):
                if isinstance(n, dict) and str(n.get("title") or "") == title:
                    node_id = n.get("id")
                    break
            out["node_id"] = node_id
            if not node_id:
                out["ok"] = False
                out["error"] = "node not found by title"
            else:
                with request.urlopen(request.Request(f"{base_url}/api/v1/nodes/{node_id}/status-history"), timeout=3.0) as resp:
                    h = json.loads(resp.read().decode("utf-8", errors="ignore"))
                out["ok"] = True
                out["count"] = len(h.get("data") or []) if isinstance(h, dict) else 0
                out["sample"] = (h.get("data") or [])[:5] if isinstance(h, dict) else []
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


