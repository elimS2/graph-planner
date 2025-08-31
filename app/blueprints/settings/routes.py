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
from ...utils.process import spawn_detached_silent


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
        spawn_detached_silent(args, cwd=str(root))
    except Exception as e:
        return jsonify({"errors": [{"status": 500, "title": "Failed to spawn relauncher", "detail": str(e)}]}), 500

    # Schedule graceful shutdown after short delay to let response flush
    # Capture shutdown func from this request context
    shutdown_func = request.environ.get("werkzeug.server.shutdown")

    def _shutdown_later():
        try:
            # Allow relauncher to spawn before shutting down
            time.sleep(0.75)
            if callable(shutdown_func):
                shutdown_func()  # type: ignore[misc]
                # Give werkzeug a moment to stop
                time.sleep(0.75)
            # Hard fallback for cases when shutdown is unavailable or ignored
            try:
                import os as _os
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

