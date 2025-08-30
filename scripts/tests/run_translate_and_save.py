from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List
import time
from datetime import datetime
import sys

import requests


def fetch_nodes(host: str, project_id: str) -> List[Dict[str, Any]]:
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/nodes"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return list(r.json().get("data", []))


def fetch_stats(host: str, project_id: str, lang: str) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/translation/stats?lang={lang}"
    r = requests.get(url, timeout=30)
    ok = r.status_code < 400
    return {"ok": ok, "status": r.status_code, "data": r.json().get("data", {}) if ok else {"error": r.text}}


def translate_node(host: str, node_id: str, lang: str, provider: str) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/nodes/{node_id}/translate"
    r = requests.post(url, json={"lang": lang, "provider": provider}, timeout=60)
    ok = r.status_code < 400
    data = r.json() if ok else {"errors": [{"title": f"HTTP {r.status_code}", "detail": r.text}]}
    return {"ok": ok, "response": data}


def bulk_translate(host: str, project_id: str, lang: str, provider: str, force: bool) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/projects/{project_id}/translate"
    payload = {
        "lang": lang,
        "include_nodes": True,
        "include_comments": True,
        "stale": True,
        "provider": provider,
        "force": force,
    }
    r = requests.post(url, json=payload, timeout=180)
    ok = r.status_code < 400
    data = r.json() if ok else {"errors": [{"title": f"HTTP {r.status_code}", "detail": r.text}]}
    return {"ok": ok, "response": data}


def fetch_job_logs(host: str, job_id: str) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/logs/jobs/{job_id}"
    r = requests.get(url, timeout=30)
    ok = r.status_code < 400
    data = r.json() if ok else {"errors": [{"title": f"HTTP {r.status_code}", "detail": r.text}]}
    return {"ok": ok, "response": data}


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


def init_logger() -> tuple[Path, callable]:
    root = Path(__file__).resolve().parents[2]
    env_values = load_dotenv_values(root)
    logs_dir = env_values.get("LOGS_DIR", "logs")
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_path = Path(logs_dir) / f"run_translate_and_save-{ts}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        line = f"{datetime.utcnow().isoformat()}Z {msg}\n"
        with open(log_path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(line)

    return log_path, _log


def main() -> None:
    ap = argparse.ArgumentParser(description="Run translate tests and save JSON result")
    ap.add_argument("--project", required=True)
    ap.add_argument("--host", default="http://127.0.0.1:5050")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--mode", choices=["nodes", "bulk"], default="nodes")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--outfile", default=str(Path("scripts/tests/json-result.json")))
    ap.add_argument("--joblog", action="store_true")
    args = ap.parse_args()

    log_file, log = init_logger()
    log(f"START project={args.project} host={args.host} mode={args.mode} lang={args.lang} provider={args.provider} force={args.force}")
    log(f"LOG_FILE path={log_file}")
    # Early check: log file must exist and be non-empty after first write
    try:
        if (not log_file.exists()) or (log_file.stat().st_size <= 0):
            early_err = {"error": "Log file not writable", "log_file": str(log_file)}
            outfile = Path(args.outfile)
            save_json(early_err, outfile)
            print(json.dumps(early_err, ensure_ascii=False))
            sys.exit(1)
    except Exception as e:
        early_err = {"error": f"Log check failed: {e}", "log_file": str(log_file)}
        outfile = Path(args.outfile)
        save_json(early_err, outfile)
        print(json.dumps(early_err, ensure_ascii=False))
        sys.exit(1)

    out: Dict[str, Any] = {"project_id": args.project, "lang": args.lang, "provider": args.provider, "mode": args.mode}
    if args.mode == "nodes":
        items: List[Dict[str, Any]] = []
        log("NODES prefetch start")
        for n in fetch_nodes(args.host, args.project):
            nid = str(n.get("id"))
            title = (n.get("title") or "")
            tr = translate_node(args.host, nid, args.lang, args.provider)
            log(f"NODE id={nid} ok={tr.get('ok', False)}")
            row: Dict[str, Any] = {"id": nid, "title": title, "ok": tr.get("ok", False)}
            if tr.get("ok"):
                row["translated"] = tr["response"].get("data", {}).get("text")
            else:
                row["error"] = tr["response"].get("errors")
            items.append(row)
        out["items"] = items
        out["count"] = len(items)
        log(f"NODES fetched count={len(items)}")
    else:
        # Kick async job
        # Preflight stats for totals and missing/stale breakdown
        st = fetch_stats(args.host, args.project, args.lang)
        out["preflight_stats"] = st
        try:
            d = st.get("data", {})
            total_nodes = int(d.get("total_nodes", 0))
            total_comments = int(d.get("total_comments", 0))
            missing_nodes = int(d.get("missing_nodes", 0))
            stale_nodes = int(d.get("stale_nodes", 0))
            missing_comments = int(d.get("missing_comments", 0))
            stale_comments = int(d.get("stale_comments", 0))
            denom = total_nodes + total_comments
            left = missing_nodes + stale_nodes + missing_comments + stale_comments
            log(f"PREFLIGHT totals nodes={total_nodes} comments={total_comments} denom={denom} left={left} (mn={missing_nodes}, sn={stale_nodes}, mc={missing_comments}, sc={stale_comments})")
        except Exception:
            denom = 0
            log("PREFLIGHT totals unavailable")
        url_async = f"{args.host.rstrip('/')}/api/v1/projects/{args.project}/translate/async"
        payload = {"lang": args.lang, "include_nodes": True, "include_comments": True, "stale": True, "provider": args.provider, "force": args.force}
        log(f"ASYNC kick url={url_async} payload={payload} pre_denom={denom}")
        r = requests.post(url_async, json=payload, timeout=60)
        r.raise_for_status()
        job_id = r.json().get("data", {}).get("job_id")
        log(f"ASYNC job_id={job_id}")
        out["job_id"] = job_id
        # Poll status
        status: Dict[str, Any] = {}
        for i in range(600):  # up to 10 minutes, heartbeat every second
            try:
                s = requests.get(f"{args.host.rstrip('/')}/api/v1/jobs/{job_id}", timeout=30)
                status = s.json().get("data", {})
                dn = int(status.get("done") or 0)
                tt = int(status.get("total") or 0)
                base = tt if tt > 0 else denom
                pct = (dn / base * 100.0) if base > 0 else 0.0
                log("ASYNC poll i={i} status={st} done={dn} total={tt} denom={denom} pct={pct:.1f} translated={tr} updated_at={ua}".format(
                    i=i,
                    st=status.get("status"),
                    dn=dn,
                    tt=tt,
                    denom=denom,
                    pct=pct,
                    tr=status.get("translated"),
                    ua=status.get("updated_at"),
                ))
                if status.get("status") in ("finished", "failed"):
                    log(f"ASYNC end status={status.get('status')}")
                    break
            except Exception as e:
                log(f"ASYNC poll error i={i} err={e}")
            time.sleep(1)
        out["job_status"] = status
        if args.joblog and job_id:
            log("ASYNC fetch logs via API")
            jl = fetch_job_logs(args.host, job_id)
            out["job_logs"] = jl
            try:
                lines = jl.get("response", {}).get("data", {}).get("lines", []) if jl.get("ok") else []
                log(f"ASYNC job logs count={len(lines)}")
            except Exception:
                pass

    outfile = Path(args.outfile)
    save_json(out, outfile)
    # Also print to stdout
    print(json.dumps(out, ensure_ascii=False))
    log(f"DONE saved_json={outfile} log_file={log_file}")


if __name__ == "__main__":
    main()


