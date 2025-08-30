from app import create_app
from app.extensions import db
from app.services.projects import ProjectService, ProjectCreateInput


def setup_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def test_create_project_success():
    app = setup_app()
    with app.app_context():
        svc = ProjectService()
        res = svc.create(ProjectCreateInput(name="Test Project", description="Desc"))
        assert res.ok
        assert res.data is not None


def test_create_project_missing_name():
    app = setup_app()
    with app.app_context():
        svc = ProjectService()
        res = svc.create(ProjectCreateInput(name=""))
        assert not res.ok
        assert res.error == "name is required"

