from __future__ import annotations

from flask import Blueprint, jsonify, current_app, request
from pathlib import Path
from typing import Dict, List
import os
import sys
import subprocess
import threading
import time
import json
import uuid

from ...utils.env_reader import read_dotenv_values, is_sensitive_key, mask_value
from ...services.backups import perform_sqlite_backup, BackupError
from ...utils.process import spawn_detached_silent
from ... import extensions as ext
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from ...services.scheduler_jobs import backup_db_job


bp = Blueprint("settings_api", __name__, url_prefix="/api/v1")


@bp.get("/settings/env")
def get_env_settings():
    """Return environment key/value pairs for Settings panel (dev/test only)."""
    # Gate to dev/test
    cfg_env = (getattr(current_app, "env", "") or "").lower()
    from os import getenv
    env_var = (getenv("APP_ENV") or getenv("FLASK_ENV") or "").lower()
    is_dev_like = (
        bool(current_app.config.get("DEBUG"))
        or bool(current_app.debug)
        or bool(current_app.config.get("TESTING"))
        or cfg_env in {"development", "testing", "test"}
        or env_var in {"development", "testing", "test"}
    )
    if not is_dev_like:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404

    # Resolve project root: routes.py -> settings -> blueprints -> app -> root
    here = Path(__file__).resolve()
    root = here.parents[3]

    values: Dict[str, str] = read_dotenv_values(root)
    source = ".env"
    fallback_used = False
    if not values:
        # Conservative fallback to a subset of process env
        candidates = [
            "FLASK_ENV", "APP_ENV", "HOST", "PORT", "DATABASE_URL", "LOG_LEVEL",
        ]
        values = {k: os.environ.get(k, "") for k in candidates if k in os.environ}
        source = "os.environ (fallback)"
        fallback_used = True

    entries: List[Dict[str, object]] = []
    for k, v in sorted(values.items(), key=lambda x: x[0].lower()):
        sensitive = is_sensitive_key(k)
        entries.append({
            "key": k,
            "value": v,
            "masked": mask_value(v or ""),
            "is_sensitive": sensitive,
        })

    return jsonify({
        "data": entries,
        "meta": {"source": source, "fallback_used": fallback_used}
    })



@bp.post("/settings/restart")
def restart_server():
    """Restart the dev server (dev/test only).
    Spawns a detached relauncher script and then gracefully shuts down the server.
    Returns 202 immediately so the client can start polling health.
    """
    # Gate to dev/test
    cfg_env = (getattr(current_app, "env", "") or "").lower()
    from os import getenv
    env_var = (getenv("APP_ENV") or getenv("FLASK_ENV") or "").lower()
    is_dev_like = (
        bool(current_app.config.get("DEBUG"))
        or bool(current_app.debug)
        or bool(current_app.config.get("TESTING"))
        or cfg_env in {"development", "testing", "test"}
        or env_var in {"development", "testing", "test"}
    )
    if not is_dev_like:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404

    # Resolve project root
    here = Path(__file__).resolve()
    root = here.parents[3]

    # Prepare relauncher command
    # Prefer pythonw.exe on Windows to avoid flashing a console window
    py = sys.executable or "python"
    if os.name == "nt":
        try:
            from pathlib import Path as _P
            cand = _P(py).with_name("pythonw.exe")
            if cand.exists():
                py = str(cand)
        except Exception:
            pass
    relauncher = root / "scripts" / "restart_server.py"
    envv: Dict[str, str] = read_dotenv_values(root)
    host = (envv.get("HOST") or "http://127.0.0.1").strip().rstrip("/")
    port = str(int(envv.get("PORT") or 5050))

    # Generate operation id and ensure status directory exists
    op_id = uuid.uuid4().hex
    ops_dir = root / "instance" / "restart_ops"
    ops_dir.mkdir(parents=True, exist_ok=True)

    args: List[str] = [py, str(relauncher), "--host", host, "--port", port, "--op-id", op_id]

    # Spawn detached process cross-platform
    try:
        current_app.logger.info("[restart] spawning relauncher: %s", " ".join(args))
        spawn_detached_silent(args, cwd=str(root))
        # Best-effort: wait briefly for op status file to appear to ensure relauncher actually started
        op_path = ops_dir / f"{op_id}.json"
        deadline = time.time() + 2.0
        appeared = False
        while time.time() < deadline:
            if op_path.exists():
                appeared = True
                break
            time.sleep(0.1)
        if not appeared:
            current_app.logger.warning("[restart] op file not observed within 2s, retrying spawn via python.exe fallback")
            # Fallback to python.exe in case pythonw had issues
            py_fallback = sys.executable or "python"
            try:
                spawn_detached_silent([py_fallback, str(relauncher), "--host", host, "--port", port, "--op-id", op_id], cwd=str(root))
            except Exception:
                pass
        current_app.logger.info("[restart] relauncher spawned, scheduling shutdown")
    except Exception as e:
        current_app.logger.exception("[restart] failed to spawn relauncher")
        return jsonify({"errors": [{"status": 500, "title": "Failed to spawn relauncher", "detail": str(e)}]}), 500

    # Schedule graceful shutdown after short delay to let response flush
    # Capture shutdown func from this request context
    shutdown_func = request.environ.get("werkzeug.server.shutdown")

    def _shutdown_later():
        try:
            # Allow relauncher to spawn before shutting down
            time.sleep(0.75)
            if callable(shutdown_func):
                current_app.logger.info("[restart] invoking werkzeug shutdown")
                shutdown_func()  # type: ignore[misc]
                # Give werkzeug a moment to stop
                time.sleep(0.75)
            # Hard fallback for cases when shutdown is unavailable or ignored
            try:
                import os as _os
                current_app.logger.info("[restart] forcing process exit(0)")
                _os._exit(0)
            except Exception:
                pass
        except Exception:
            pass

    threading.Thread(target=_shutdown_later, daemon=True).start()

    return jsonify({"data": {"restarting": True, "op_id": op_id}}), 202


@bp.get("/settings/restart/status/<op_id>")
def get_restart_status(op_id: str):
    # Gate to dev/test
    cfg_env = (getattr(current_app, "env", "") or "").lower()
    from os import getenv
    env_var = (getenv("APP_ENV") or getenv("FLASK_ENV") or "").lower()
    is_dev_like = (
        bool(current_app.config.get("DEBUG"))
        or bool(current_app.debug)
        or bool(current_app.config.get("TESTING"))
        or cfg_env in {"development", "testing", "test"}
        or env_var in {"development", "testing", "test"}
    )
    if not is_dev_like:
        return jsonify({"errors": [{"status": 404, "title": "Not Found"}]}), 404

    here = Path(__file__).resolve()
    root = here.parents[3]
    path = root / "instance" / "restart_ops" / f"{op_id}.json"
    if not path.exists():
        # Pending
        return jsonify({"data": {"op_id": op_id, "pending": True}})
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
        js = json.loads(txt)
    except Exception as e:
        return jsonify({"errors": [{"status": 500, "title": "Read error", "detail": str(e)}]}), 500
    return jsonify({"data": js})


@bp.post("/settings/backup-db")
def backup_db():
    """Create a database backup into the directory specified by BACKUPS_DIR in .env.

    Success: { data: { ok, path, size_bytes, created_at } }
    Errors:
      - 400 if BACKUPS_DIR is missing/empty or DB engine unsupported
      - 500 on unexpected I/O errors
    """
    # Resolve project root
    here = Path(__file__).resolve()
    root = here.parents[3]

    envv = read_dotenv_values(root)
    backups_dir_raw = (envv.get("BACKUPS_DIR") or "").strip()
    if not backups_dir_raw:
        return jsonify({
            "errors": [{
                "status": 400,
                "title": "Missing BACKUPS_DIR",
                "detail": "Provide BACKUPS_DIR in .env at the project root.",
                "hint": "Example: BACKUPS_DIR=backups"
            }]
        }), 400

    backups_dir = Path(backups_dir_raw)
    if not backups_dir.is_absolute():
        backups_dir = (root / backups_dir).resolve()

    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "") or ""
    if not db_uri.lower().startswith("sqlite:"):
        return jsonify({
            "errors": [{
                "status": 400,
                "title": "Unsupported database engine",
                "detail": "Only SQLite is supported for backups in this version."
            }]
        }), 400

    try:
        result = perform_sqlite_backup(backups_dir, db_uri)
        return jsonify({"data": result})
    except BackupError as e:
        return jsonify({
            "errors": [{"status": 400, "title": "Backup error", "detail": str(e)}]
        }), 400
    except Exception as e:
        current_app.logger.exception("[backup] unexpected failure")
        return jsonify({
            "errors": [{
                "status": 500,
                "title": "Unexpected error",
                "detail": str(e) if current_app.config.get("DEBUG") else ""
            }]
        }), 500


@bp.get("/settings/scheduler")
def get_scheduler_status():
    jobs = []
    try:
        if ext.scheduler:
            for j in ext.scheduler.get_jobs():
                jobs.append({
                    "id": j.id,
                    "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
                    "trigger": str(j.trigger),
                })
        return jsonify({"data": {"jobs": jobs}})
    except Exception as e:
        return jsonify({"errors": [{"status": 500, "title": "Scheduler error", "detail": str(e)}]}), 500


def _ensure_scheduler():
    if not ext.scheduler:
        raise RuntimeError("Scheduler is not initialized")


@bp.post("/settings/scheduler/backup")
def set_backup_schedule():
    """Create or update the backup schedule.

    Body: { mode: 'disabled'|'daily'|'weekly'|'cron'|'interval', hour?, minute?, weekday?, cron?, every_hours? }
    """
    try:
        _ensure_scheduler()
        js = request.get_json(silent=True) or {}
        mode = (js.get('mode') or '').lower()
        job_id = 'backup_db'

        # Remove existing
        try:
            ext.scheduler.remove_job(job_id)
        except Exception:
            pass

        if mode in ('', 'disabled'):
            return jsonify({"data": {"disabled": True}})

        trigger = None
        if mode == 'daily':
            hour = int(js.get('hour') or 0)
            minute = int(js.get('minute') or 0)
            trigger = CronTrigger(hour=hour, minute=minute)
        elif mode == 'weekly':
            hour = int(js.get('hour') or 0)
            minute = int(js.get('minute') or 0)
            weekday = str(js.get('weekday') or 'mon')
            trigger = CronTrigger(day_of_week=weekday, hour=hour, minute=minute)
        elif mode == 'cron':
            expr = str(js.get('cron') or '').strip()
            if not expr:
                return jsonify({"errors":[{"status":400,"title":"Invalid cron","detail":"Cron expression is required"}]}), 400
            try:
                trigger = CronTrigger.from_crontab(expr)
            except Exception as e:
                return jsonify({"errors":[{"status":400,"title":"Invalid cron","detail":str(e)}]}), 400
        elif mode == 'interval':
            every = int(js.get('every_hours') or 0)
            if every < 1:
                return jsonify({"errors":[{"status":400,"title":"Invalid interval","detail":"every_hours must be >= 1"}]}), 400
            trigger = IntervalTrigger(hours=every)
        else:
            return jsonify({"errors":[{"status":400,"title":"Invalid mode","detail":"Unsupported scheduling mode"}]}), 400

        # Use dotted callable reference to make the job serializable
        ext.scheduler.add_job(backup_db_job, trigger=trigger, id=job_id, replace_existing=True, coalesce=True, max_instances=1)
        j = ext.scheduler.get_job(job_id)
        return jsonify({"data": {"scheduled": True, "job": {"id": j.id, "next_run_time": j.next_run_time.isoformat() if j and j.next_run_time else None}}})
    except Exception as e:
        current_app.logger.exception('[scheduler] set schedule failed')
        return jsonify({"errors":[{"status":500,"title":"Set schedule failed","detail":str(e)}]}), 500


@bp.delete("/settings/scheduler/backup")
def delete_backup_schedule():
    try:
        _ensure_scheduler()
        job_id = 'backup_db'
        try:
            ext.scheduler.remove_job(job_id)
        except Exception:
            pass
        return jsonify({"data": {"deleted": True}})
    except Exception as e:
        return jsonify({"errors":[{"status":500,"title":"Delete failed","detail":str(e)}]}), 500


@bp.post("/settings/scheduler/backup/run")
def run_backup_now():
    try:
        here = Path(__file__).resolve()
        root = here.parents[3]
        envv = read_dotenv_values(root)
        backups_dir_raw = (envv.get("BACKUPS_DIR") or "").strip()
        if not backups_dir_raw:
            return jsonify({"errors":[{"status":400,"title":"Missing BACKUPS_DIR","detail":"Provide BACKUPS_DIR in .env at the project root."}]}), 400
        backups_dir = Path(backups_dir_raw)
        if not backups_dir.is_absolute():
            backups_dir = (root / backups_dir).resolve()
        db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "") or ""
        if not db_uri.lower().startswith("sqlite:"):
            return jsonify({"errors":[{"status":400,"title":"Unsupported database engine","detail":"Only SQLite is supported for backups in this version."}]}), 400
        result = perform_sqlite_backup(backups_dir, db_uri)
        return jsonify({"data": result})
    except BackupError as e:
        return jsonify({"errors":[{"status":400,"title":"Backup error","detail":str(e)}]}), 400
    except Exception as e:
        current_app.logger.exception('[scheduler] run-now failed')
        return jsonify({"errors":[{"status":500,"title":"Unexpected error","detail":str(e) if current_app.config.get('DEBUG') else ''}]}), 500
