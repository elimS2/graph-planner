from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:  # nosec - local call
        body = resp.read().decode("utf-8", errors="ignore")
    return json.loads(body)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)
    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base = f"{host}:{port}"

    out: Dict[str, Any] = {"action": "test_status_history_e2e", "base_url": base}
    try:
        # 1) Debug DB URI
        try:
            dbg = http_json(f"{base}/api/v1/debug/db-url", timeout=2.0)
            out["db_uri"] = (dbg.get("data") or {}).get("sqlalchemy_database_uri")
        except Exception:
            out["db_uri"] = None

        # 2) Find project 'Graph Planner'
        projs = http_json(f"{base}/api/v1/projects", timeout=3.0)
        proj_id: Optional[str] = None
        for p in (projs.get("data") or []):
            if isinstance(p, dict) and ("Graph Planner" in str(p.get("name") or "")):
                proj_id = p.get("id")
                break
        if not proj_id:
            out["ok"] = False
            out["error"] = "Graph Planner project not found"
        else:
            out["project_id"] = proj_id
            nodes = http_json(f"{base}/api/v1/projects/{proj_id}/nodes", timeout=5.0)
            nitems: List[Dict[str, Any]] = (nodes.get("data") or []) if isinstance(nodes, dict) else []
            with_history: List[Dict[str, Any]] = []
            panel_title = "Line colors"
            panel_node_id: Optional[str] = None
            for n in nitems:
                if isinstance(n, dict) and str(n.get("title") or "") == panel_title:
                    panel_node_id = n.get("id")
                    break
            # Query each node's status history via official endpoint
            import urllib.error
            for n in nitems:
                if not isinstance(n, dict):
                    continue
                nid = n.get("id")
                title = n.get("title")
                try:
                    h = http_json(f"{base}/api/v1/nodes/{nid}/status-history", timeout=3.0)
                    cnt = len(h.get("data") or []) if isinstance(h, dict) else 0
                except urllib.error.HTTPError as he:  # type: ignore[attr-defined]
                    cnt = 0
                if cnt > 0:
                    with_history.append({"id": nid, "title": title, "count": cnt})
                if panel_node_id and nid == panel_node_id:
                    out["panel_node"] = {"id": nid, "title": title, "count": cnt}

            out["nodes_with_history_count"] = len(with_history)
            # shorten list for output
            out["nodes_with_history"] = with_history[:20]
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


