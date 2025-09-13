import json
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Project, Node, User, Comment


def _ensure_dirs():
    out_dir = Path(__file__).resolve().parent
    json_path = out_dir / "json-result.json"
    return json_path


def run():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Seed minimal data
        user = User(email="tester@example.com", name="Tester")
        project = Project(name="Test Project")
        db.session.add_all([user, project])
        db.session.flush()
        node = Node(project_id=project.id, title="Test Node")
        db.session.add(node)
        db.session.flush()
        # Add three comments in sequence (older to newer)
        c1 = Comment(node_id=node.id, user_id=user.id, body="first")
        db.session.add(c1)
        db.session.flush()
        c2 = Comment(node_id=node.id, user_id=user.id, body="second")
        db.session.add(c2)
        db.session.flush()
        c3 = Comment(node_id=node.id, user_id=user.id, body="third")
        db.session.add(c3)
        db.session.commit()

        client = app.test_client()
        rv = client.get(f"/api/v1/nodes/{node.id}/comments")
        data = rv.get_json()
        items = data.get("data", []) if isinstance(data, dict) else []
        bodies = [x.get("body") for x in items]
        is_ascending = bodies == ["first", "second", "third"]

        out = {
            "ok": bool(rv.status_code == 200 and is_ascending),
            "status_code": rv.status_code,
            "order": bodies,
            "expected": ["first", "second", "third"],
            "count": len(items),
        }

        json_path = _ensure_dirs()
        json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        return out


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False))


