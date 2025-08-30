from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

import requests


def list_logs_in_dir(logs_dir: str, limit: int = 10) -> Dict[str, Any]:
    result: Dict[str, Any] = {"exists": False, "dir": logs_dir, "logs": []}
    try:
        p = Path(logs_dir)
        if not p.exists() or not p.is_dir():
            return result
        result["exists"] = True
        files = sorted(p.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        out: List[Dict[str, Any]] = []
        for f in files[:limit]:
            try:
                st = f.stat()
                out.append({
                    "name": f.name,
                    "path": str(f.resolve()),
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "mtime_iso": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z",
                })
            except Exception as e:
                out.append({"name": f.name, "error": str(e)})
        result["logs"] = out
        return result
    except Exception as e:
        return {"exists": False, "dir": logs_dir, "error": str(e), "logs": []}


def tail_file(path: str, n: int = 50) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [ln.rstrip("\n") for ln in lines[-n:]]
    except Exception:
        return []


def fetch_latest_api(host: str) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/logs/latest"
    try:
        r = requests.get(url, timeout=15)
        ok = r.status_code < 400
        return {"ok": ok, "status": r.status_code, "data": r.json() if ok else r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fetch_job_api(host: str, job_id: str) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/logs/jobs/{job_id}"
    try:
        r = requests.get(url, timeout=15)
        ok = r.status_code < 400
        return {"ok": ok, "status": r.status_code, "data": r.json() if ok else r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def save_json(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def main() -> None:
    ap = argparse.ArgumentParser(description="Check logs presence and read via API")
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--job-id", default="", help="Optional job id to filter logs")
    ap.add_argument("--tail", type=int, default=50, help="Tail lines from newest file in LOGS_DIR")
    ap.add_argument("--outfile", default=str(Path("scripts/tests/json-result.json")))
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    env_values = load_dotenv_values(root)
    logs_dir = env_values.get("LOGS_DIR", "logs")

    fs_info = list_logs_in_dir(logs_dir)
    newest_tail: List[str] = []
    if fs_info.get("exists") and fs_info.get("logs"):
        newest_tail = tail_file(fs_info["logs"][0]["path"], n=args.tail)

    api_latest = fetch_latest_api(args.host)
    api_job = fetch_job_api(args.host, args.job_id) if args.job_id else None

    out: Dict[str, Any] = {
        "env": {"LOGS_DIR": logs_dir},
        "fs": fs_info,
        "fs_tail": newest_tail,
        "api": {"latest": api_latest, "job": api_job},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    save_json(out, Path(args.outfile))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()


