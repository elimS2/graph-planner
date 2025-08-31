from __future__ import annotations

from flask import Blueprint, jsonify, current_app
from pathlib import Path
from typing import Dict, List
import os

from ...utils.env_reader import read_dotenv_values, is_sensitive_key, mask_value


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


