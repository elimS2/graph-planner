from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List

import requests


def post_translate(host: str, project_id: str, lang: str, provider: str, force: bool) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/translate"
    payload = {
        "lang": lang,
        "include_nodes": True,
        "include_comments": True,
        "stale": True,
        "provider": provider,
        "force": force,
    }
    r = requests.post(url, json=payload, timeout=120)
    ok = r.status_code < 400
    return {"ok": ok, "status": r.status_code, "json": r.json() if ok else {"errors": r.text}}


def fetch_nodes(host: str, project_id: str, lang: str | None = None) -> List[Dict[str, Any]]:
    q = f"?lang={lang}" if lang else ""
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/nodes{q}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return list(r.json().get("data", []))


def fetch_comments(host: str, node_id: str, lang: str | None = None) -> List[Dict[str, Any]]:
    q = f"?lang={lang}" if lang else ""
    url = f"{host.rstrip('/')}/api/v1/nodes/{node_id}/comments{q}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return list(r.json().get("data", []))


def main() -> None:
    ap = argparse.ArgumentParser(description="API bulk translate test (nodes+comments), returns JSON summary")
    ap.add_argument("--project", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--provider", default="mymemory")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--samples", type=int, default=5)
    args = ap.parse_args()

    t0 = time.time()
    kicked = post_translate(args.host, args.project, args.lang, args.provider, args.force)

    # After bulk call, fetch nodes and comments with lang to verify storage
    nodes_lang = fetch_nodes(args.host, args.project, args.lang)
    node_samples: List[Dict[str, Any]] = []
    comment_samples: List[Dict[str, Any]] = []
    for n in nodes_lang[: args.samples]:
        node_samples.append(
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "title_translated": n.get("title_translated"),
            }
        )
        try:
            comments = fetch_comments(args.host, str(n.get("id")), args.lang)
            for c in comments[: args.samples]:
                comment_samples.append(
                    {
                        "id": c.get("id"),
                        "body": c.get("body"),
                        "body_translated": c.get("body_translated"),
                        "node_id": n.get("id"),
                    }
                )
        except Exception:
            pass

    out = {
        "project_id": args.project,
        "lang": args.lang,
        "provider": args.provider,
        "force": args.force,
        "kicked": kicked,
        "duration_s": round(time.time() - t0, 3),
        "samples": {"nodes": node_samples, "comments": comment_samples},
    }
    print(json.dumps(out, ensure_ascii=True))


if __name__ == "__main__":
    main()


