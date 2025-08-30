from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import requests


def save_json(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync bulk translate via /translate to trigger provider logs")
    ap.add_argument("--project", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--outfile", default=str(Path("scripts/tests/json-result.json")))
    args = ap.parse_args()

    host = args.host.rstrip('/')
    payload = {
        "lang": args.lang,
        "include_nodes": True,
        "include_comments": True,
        "stale": True,
        "provider": args.provider,
        "force": args.force,
    }
    r = requests.post(f"{host}/api/v1/projects/{args.project}/translate", json=payload, timeout=180)
    ok = r.status_code < 400
    out: Dict[str, Any] = {
        "project_id": args.project,
        "lang": args.lang,
        "provider": args.provider,
        "sync": True,
        "ok": ok,
        "response": r.json() if ok else {"status": r.status_code, "text": r.text},
    }
    save_json(out, Path(args.outfile))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()


