from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List

import requests


def fetch_nodes(host: str, project_id: str) -> List[Dict[str, Any]]:
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/nodes"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return list(r.json().get("data", []))


def translate_node(host: str, node_id: str, lang: str, provider: str) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/nodes/{node_id}/translate"
    r = requests.post(url, json={"lang": lang, "provider": provider}, timeout=30)
    ok = r.status_code < 400
    data = r.json() if ok else {"errors": [{"title": f"HTTP {r.status_code}", "detail": r.text}]}
    return {"ok": ok, "response": data}


def main() -> None:
    ap = argparse.ArgumentParser(description="Mass translate node titles and return JSON with per-item results")
    ap.add_argument("--project", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--provider", default="mymemory")
    args = ap.parse_args()

    started = time.time()
    nodes = fetch_nodes(args.host, args.project)
    items: List[Dict[str, Any]] = []
    for n in nodes:
        nid = str(n.get("id"))
        title = (n.get("title") or "")
        tr = translate_node(args.host, nid, args.lang, args.provider)
        item: Dict[str, Any] = {"id": nid, "title": title, "ok": tr.get("ok", False)}
        if tr.get("ok"):
            item["translated"] = tr["response"].get("data", {}).get("text")
        else:
            item["error"] = tr["response"].get("errors")
        items.append(item)

    out = {
        "project_id": args.project,
        "lang": args.lang,
        "provider": args.provider,
        "count": len(items),
        "duration_s": round(time.time() - started, 3),
        "items": items,
    }
    # ensure_ascii=True to be safe in various shells
    print(json.dumps(out, ensure_ascii=True))


if __name__ == "__main__":
    main()


