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


essential_keys = ["id", "title", "status", "created_at"]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    envv = load_dotenv_values(root)

    host_raw = (envv.get("HOST") or "http://127.0.0.1").rstrip("/")
    host = _ensure_http_scheme(host_raw)
    port = int(envv.get("PORT") or 5050)
    base_url = f"{host}:{port}"

    out: Dict[str, Any] = {"action": "probe_status_history", "base_url": base_url}

    try:
        import urllib.request
        import urllib.error

        # Fetch any project
        proj_url = f"{base_url}/api/v1/projects"
        with urllib.request.urlopen(urllib.request.Request(proj_url), timeout=2.0) as resp:
            projs = json.loads(resp.read().decode("utf-8", errors="ignore"))
        pitems = (projs.get("data") or []) if isinstance(projs, dict) else []
        if not pitems:
            out["error"] = "no projects"
        else:
            pid = pitems[0]["id"]
            out["project_id"] = pid
            # Fetch nodes of project
            nodes_url = f"{base_url}/api/v1/projects/{pid}/nodes"
            with urllib.request.urlopen(urllib.request.Request(nodes_url), timeout=3.0) as resp:
                nodes = json.loads(resp.read().decode("utf-8", errors="ignore"))
            nitems = (nodes.get("data") or []) if isinstance(nodes, dict) else []
            out["nodes_count"] = len(nitems)
            if nitems:
                nid = nitems[0]["id"]
                out["node_id"] = nid
                hist_url = f"{base_url}/api/v1/nodes/{nid}/status-history"
                try:
                    with urllib.request.urlopen(urllib.request.Request(hist_url), timeout=2.0) as resp:
                        hist = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    out["history"] = hist.get("data") if isinstance(hist, dict) else None
                    out["ok"] = True
                except urllib.error.HTTPError as he:
                    out["ok"] = False
                    out["http_status"] = he.code
                    out["error"] = "history http error"
            else:
                out["ok"] = False
                out["error"] = "no nodes in project"
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
