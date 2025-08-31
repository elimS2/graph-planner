from flask import Blueprint, render_template, current_app
from pathlib import Path
from typing import List, Dict
from ...utils.env_reader import read_dotenv_values, is_sensitive_key, mask_value
from ...extensions import db
from ...models import Project


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/projects/<id>")
def project_view(id: str):
    project = db.session.get(Project, id)
    if not project:
        return ("Project not found", 404)
    return render_template("project.html", project=project)


@bp.get("/settings")
def settings_view():
    # Gate: allow only in development or testing
    cfg_env = (current_app.env or "").lower() if hasattr(current_app, "env") else ""
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
        return ("Not Found", 404)

    # Determine project root (two levels up from this file: app/blueprints/main/routes.py -> app -> root)
    here = Path(__file__).resolve()
    root = here.parents[3]  # routes.py -> main -> blueprints -> app -> project root

    # Read .env values; fallback to selected os.environ keys if missing
    env_values = read_dotenv_values(root)
    source = ".env"
    fallback_used = False
    if not env_values:
        # Conservative fallback: select a limited subset from os.environ
        import os
        candidates = [
            "FLASK_ENV", "APP_ENV", "HOST", "PORT", "DATABASE_URL", "LOG_LEVEL",
        ]
        env_values = {k: os.environ.get(k, "") for k in candidates if k in os.environ}
        source = "os.environ (fallback)"
        fallback_used = True

    # Prepare entries with masking
    entries: List[Dict[str, str | bool]] = []
    for k, v in sorted(env_values.items(), key=lambda x: x[0].lower()):
        sensitive = is_sensitive_key(k)
        entries.append({
            "key": k,
            "value": v,
            "masked": mask_value(v or ""),
            "is_sensitive": sensitive,
        })

    return render_template(
        "settings.html",
        entries=entries,
        source=source,
        fallback_used=fallback_used,
    )

