from __future__ import annotations

import argparse
import json
import re
from typing import Any, Dict, List

import requests


def guess_lang(text: str) -> str:
    t = text or ""
    if re.search(r"[\u0400-\u04FF]", t):
        return "uk" if re.search(r"[іїєґІЇЄҐ]", t) else "ru"
    if re.search(r"[A-Za-z]", t):
        return "en"
    return "unknown"


def fetch_nodes(host: str, project_id: str) -> List[Dict[str, Any]]:
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/nodes"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return list(resp.json().get("data", []))


def build_summary(nodes: List[Dict[str, Any]], limit: int) -> Dict[str, Any]:
    counts: Dict[str, int] = {"ru": 0, "uk": 0, "en": 0, "unknown": 0}
    items: List[Dict[str, str]] = []
    for n in nodes:
        title = (n.get("title") or "").strip()
        lang = guess_lang(title)
        counts[lang] = counts.get(lang, 0) + 1
        if len(items) < limit:
            items.append({"id": n.get("id", ""), "title": title, "guess": lang})
    return {"total": len(nodes), "counts": counts, "items": items}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch node titles for a project and guess languages")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--host", default="http://127.0.0.1:5050", help="API host, default: http://127.0.0.1:5050")
    parser.add_argument("--limit", type=int, default=50, help="Number of sample items to include in output")
    parser.add_argument("--print-all", action="store_true", help="Print all id|title lines after JSON summary")
    parser.add_argument("--outfile", default=None, help="If set, write output to this file in UTF-8 instead of stdout")
    args = parser.parse_args()

    nodes = fetch_nodes(args.host, args.project)
    summary = build_summary(nodes, args.limit)
    if args.outfile:
        import os
        os.makedirs(os.path.dirname(args.outfile), exist_ok=True)
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False, indent=2))
            f.write("\n")
            if args.print_all:
                for n in nodes:
                    title = (n.get("title") or "").strip()
                    f.write(f"{n.get('id', '')}|{title}\n")
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if args.print_all:
            for n in nodes:
                title = (n.get("title") or "").strip()
                print(f"{n.get('id', '')}|{title}")


if __name__ == "__main__":
    main()


