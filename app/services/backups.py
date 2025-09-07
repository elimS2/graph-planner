from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse


class BackupError(Exception):
    pass


def _resolve_sqlite_path(db_uri: str) -> Path:
    """Resolve filesystem path of a SQLite database from SQLAlchemy-style URI.

    Supports forms like:
    - sqlite:///relative/path.db
    - sqlite:////absolute/path.db
    - sqlite:///C:/absolute/windows/path.db
    """
    if not db_uri.lower().startswith("sqlite:"):
        raise BackupError("Only SQLite databases are supported")
    # Special in-memory case
    if ":memory:" in db_uri:
        raise BackupError("In-memory SQLite database cannot be backed up")

    u = urlparse(db_uri)
    raw_path = u.path or ""
    # Normalize Windows paths: strip any leading slashes or backslashes
    # Examples:
    #   /C:/path/to/db -> C:/path/to/db
    #   \C:\path\to\db -> C:\path\to\db
    if os.name == "nt":
        fs_path = raw_path.lstrip("/\\")
    else:
        fs_path = raw_path
    p = Path(fs_path)
    return p


def perform_sqlite_backup(backups_dir: Path, db_uri: str) -> Dict[str, object]:
    """Create a SQLite database backup file under backups_dir using sqlite3 backup API.

    Returns a dict with keys: ok, path, size_bytes, created_at.
    Raises BackupError on expected validation errors.
    """
    src_path = _resolve_sqlite_path(db_uri)
    if not src_path.exists():
        raise BackupError(f"Database file not found: {src_path}")

    backups_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Keep original extension if any; default to .sqlite
    ext = src_path.suffix or ".sqlite"
    dest_name = f"graph_tracker_{ts}{ext}"
    dest_path = backups_dir / dest_name

    # Use sqlite backup API for consistency while DB is running
    src_conn = sqlite3.connect(str(src_path))
    try:
        dst_conn = sqlite3.connect(str(dest_path))
        try:
            src_conn.backup(dst_conn)
        finally:
            try:
                dst_conn.close()
            except Exception:
                pass
    finally:
        try:
            src_conn.close()
        except Exception:
            pass

    # Copy file metadata timestamps as a courtesy (optional)
    try:
        shutil.copystat(str(src_path), str(dest_path))
    except Exception:
        pass

    size = dest_path.stat().st_size if dest_path.exists() else 0
    return {
        "ok": True,
        "path": str(dest_path.resolve()),
        "size_bytes": int(size),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


