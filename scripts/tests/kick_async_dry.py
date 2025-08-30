from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

import requests


def save_json(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Kick async translate with no items (dry-run to see job init log)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--outfile", default=str(Path("scripts/tests/json-result.json")))
    args = ap.parse_args()

    host = args.host.rstrip("/")
    out: Dict[str, Any] = {"project_id": args.project, "lang": args.lang, "provider": args.provider}

    # Start async with no nodes/comments to force minimal job
    payload = {
        "lang": args.lang,
        "include_nodes": False,
        "include_comments": False,
        "stale": False,
        "provider": args.provider,
        "force": False,
    }
    r = requests.post(f"{host}/api/v1/projects/{args.project}/translate/async", json=payload, timeout=30)
    r.raise_for_status()
    job_id = r.json().get("data", {}).get("job_id")
    out["job_id"] = job_id

    # Poll briefly
    status: Dict[str, Any] = {}
    for _ in range(10):
        s = requests.get(f"{host}/api/v1/jobs/{job_id}", timeout=15)
        status = s.json().get("data", {})
        if status.get("status") in ("finished", "failed"):
            break
        time.sleep(0.5)
    out["job_status"] = status

    # Fetch job-specific log lines
    try:
        lj = requests.get(f"{host}/api/v1/logs/jobs/{job_id}", timeout=15)
        out["job_log"] = lj.json()
    except Exception as e:
        out["job_log_error"] = str(e)

    save_json(out, Path(args.outfile))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()


