from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from flask import current_app
from werkzeug.datastructures import FileStorage

from ..extensions import db
from ..models import Attachment


@dataclass
class SavedFile:
    attachment: Attachment
    abs_path: Path


def _resolve_files_root() -> Path:
    cfg_root = (current_app.config.get("FILES_ROOT") or "").strip()
    if cfg_root:
        root = Path(cfg_root)
        if not root.is_absolute():
            # Resolve relative to project root
            here = Path(__file__).resolve().parents[2]
            root = (here / cfg_root).resolve()
    else:
        # Default to instance/uploads
        here = Path(__file__).resolve().parents[2]
        root = (here / "instance" / "uploads").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha256_stream(fp: BinaryIO) -> str:
    h = hashlib.sha256()
    for chunk in iter(lambda: fp.read(1024 * 1024), b""):
        h.update(chunk)
    return h.hexdigest()


def _guess_kind(mime: str) -> str:
    return "image" if (mime or "").lower().startswith("image/") else "file"


def _normalize_mime(mime: str) -> str:
    m = (mime or "").strip().lower()
    # Common browser/OS variants
    if m == "application/x-zip-compressed":
        return "application/zip"
    return m


def _allowed_mime(mime: str) -> bool:
    raw = (current_app.config.get("ALLOWED_UPLOAD_MIME") or "").split(",")
    allowed = {m.strip().lower() for m in raw if m.strip()}
    nm = _normalize_mime(mime)
    return nm in allowed if allowed else False


def save_filestorage(file: FileStorage, uploader_user_id: str) -> SavedFile:
    if not file or not file.filename:
        raise ValueError("Empty file")
    mime = file.mimetype or "application/octet-stream"
    mime = _normalize_mime(mime)
    # Fallback by extension for octet-stream from some browsers/OSes
    if mime == "application/octet-stream":
        try:
            name = (file.filename or "").strip().lower()
            ext = Path(name).suffix
            if ext == ".zip":
                mime = "application/zip"
            elif ext == ".doc":
                mime = "application/msword"
            elif ext == ".docx":
                mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except Exception:
            pass
    if not _allowed_mime(mime):
        raise ValueError("Disallowed file type")
    # Size guard (werkzeug may not give length up-front; enforce at stream level if needed)
    max_mb = int(current_app.config.get("MAX_UPLOAD_MB", 25))
    max_bytes = max_mb * 1024 * 1024

    # Read into memory for hashing while guarding size
    file.stream.seek(0)
    data = file.stream.read()
    if data is None:
        data = b""
    if len(data) > max_bytes:
        raise ValueError("File too large")
    checksum = hashlib.sha256(data).hexdigest()

    # Deduplicate by checksum: if already stored, reuse existing record
    existing = db.session.query(Attachment).filter(Attachment.checksum_sha256 == checksum).first()
    if existing is not None:
        root = _resolve_files_root()
        abs_existing = (root / existing.storage_path).resolve()
        # Ensure file exists on disk (best-effort recovery)
        try:
            abs_existing.parent.mkdir(parents=True, exist_ok=True)
            if not abs_existing.exists():
                abs_existing.write_bytes(data)
        except Exception:
            pass
        return SavedFile(attachment=existing, abs_path=abs_existing)

    # Path planning: YYYY/MM/hash.ext
    now = datetime.utcnow()
    subdir = now.strftime("%Y/%m")
    root = _resolve_files_root()
    # Keep original extension if any
    name = (file.filename or "file").strip()
    ext = Path(name).suffix
    rel_path = Path(subdir) / f"{checksum}{ext}"
    abs_path = (root / rel_path).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file to disk; if same path exists, do not rewrite
    if not abs_path.exists():
        abs_path.write_bytes(data)

    att = Attachment(
        uploader_user_id=uploader_user_id,
        mime_type=mime,
        kind=_guess_kind(mime),
        original_name=name,
        storage_path=str(rel_path).replace("\\", "/"),
        size_bytes=len(data),
        checksum_sha256=checksum,
    )
    db.session.add(att)
    db.session.commit()
    return SavedFile(attachment=att, abs_path=abs_path)


