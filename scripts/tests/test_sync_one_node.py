from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import requests


def save_json(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync translate one node to trigger provider logging")
    ap.add_argument("--project", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--outfile", default=str(Path("scripts/tests/json-result.json")))
    args = ap.parse_args()

    host = args.host.rstrip('/')
    out: Dict[str, Any] = {"project_id": args.project, "lang": args.lang, "provider": args.provider}

    # Fetch nodes
    ns = requests.get(f"{host}/api/v1/projects/{args.project}/nodes", timeout=30)
    ns.raise_for_status()
    nodes: List[Dict[str, Any]] = list(ns.json().get("data", []))
    out["nodes_total"] = len(nodes)
    if not nodes:
        save_json(out, Path(args.outfile))
        print(json.dumps(out, ensure_ascii=False))
        return

    node_id = str(nodes[0].get("id"))
    title = nodes[0].get("title")
    # Call sync node translate
    tr = requests.post(
        f"{host}/api/v1/nodes/{node_id}/translate",
        json={"lang": args.lang, "provider": args.provider},
        timeout=60,
    )
    ok = tr.status_code < 400
    out["node"] = {"id": node_id, "title": title}
    out["response_ok"] = ok
    out["response"] = tr.json() if ok else {"status": tr.status_code, "text": tr.text}

    save_json(out, Path(args.outfile))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()


