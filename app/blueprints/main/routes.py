from flask import Blueprint, render_template
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

