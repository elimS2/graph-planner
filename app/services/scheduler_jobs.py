from __future__ import annotations

from pathlib import Path
from flask import current_app

from .backups import perform_sqlite_backup
from ..utils.env_reader import read_dotenv_values


def backup_db_job() -> None:
    """APScheduler job: perform SQLite DB backup using BACKUPS_DIR from .env.

    Safe to call without an active request context. Pushes an app context if needed.
    """
    try:
        try:
            app = current_app._get_current_object()
            # app context is assumed present if this did not raise
            push_ctx = False
        except Exception:
            from .. import create_app
            app = create_app()
            push_ctx = True

        ctx = app.app_context() if push_ctx else None
        if ctx:
            ctx.push()
        try:
            here = Path(__file__).resolve()
            root = here.parents[2]  # services -> app -> root
            envv = read_dotenv_values(root)
            backups_dir_raw = (envv.get("BACKUPS_DIR") or "").strip()
            if not backups_dir_raw:
                app.logger.warning('[scheduler] BACKUPS_DIR missing; skip backup')
                return
            backups_dir = Path(backups_dir_raw)
            if not backups_dir.is_absolute():
                backups_dir = (root / backups_dir).resolve()

            db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "") or ""
            if not db_uri.lower().startswith("sqlite:"):
                app.logger.warning('[scheduler] non-sqlite engine; skip backup')
                return

            perform_sqlite_backup(backups_dir, db_uri)
            app.logger.info('[scheduler] backup completed')
        finally:
            if ctx:
                ctx.pop()
    except Exception:
        try:
            # Try to log via app logger if possible
            app.logger.exception('[scheduler] backup failed')  # type: ignore[name-defined]
        except Exception:
            # Last resort
            print('[scheduler] backup failed (no logger available)')


