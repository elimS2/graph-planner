import click
from flask import Flask
from .extensions import db
from .models import User, Project, Node, Edge
from sqlalchemy import text
import os
from datetime import datetime
from .repositories.translations import (
    get_missing_node_titles,
    get_stale_node_titles,
    upsert_node_translations,
    get_missing_comment_bodies,
    get_stale_comment_bodies,
    upsert_comment_translations,
)
from .services.translation import translate_texts, TranslationError


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        db.create_all()
        click.echo("Database initialized")

    @app.cli.command("backup-sqlite")
    def backup_sqlite() -> None:
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if not uri.startswith("sqlite"):
            click.echo("Not using SQLite; skipping backup")
            return
        path = uri.split("///", 1)[-1]
        if not os.path.exists(path):
            click.echo("Database file not found")
            return
        os.makedirs("backups", exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        dest = os.path.join("backups", f"graph_tracker-{ts}.sqlite3")
        import shutil
        shutil.copy2(path, dest)
        click.echo(f"Backup created: {dest}")

    @app.cli.command("seed-demo")
    def seed_demo() -> None:
        # Create demo user if not exists
        u = db.session.query(User).filter_by(email="demo@example.com").first()
        if not u:
            u = User(email="demo@example.com", name="Demo User")
            u.set_password("demo1234")
            db.session.add(u)
        # Create project and simple graph
        p = Project(name="Demo Project", description="Seeded")
        db.session.add(p)
        db.session.flush()
        n1 = Node(project_id=p.id, title="Seed Start")
        n2 = Node(project_id=p.id, title="Seed Finish")
        db.session.add_all([n1, n2])
        db.session.flush()
        e = Edge(project_id=p.id, source_node_id=n1.id, target_node_id=n2.id)
        db.session.add(e)
        db.session.commit()
        click.echo(f"Seeded project id: {p.id}")

    @app.cli.command("upgrade-dev")
    def upgrade_dev() -> None:
        """Lightweight dev upgrader for SQLite: add missing columns."""
        engine = db.get_engine()
        with engine.connect() as conn:
            # Ensure password_hash exists on user
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(user)"))]
            if "password_hash" not in cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN password_hash TEXT"))
                click.echo("Added user.password_hash")
            # Ensure updated_at on user
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(user)"))]
            if "updated_at" not in cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN updated_at TEXT"))
                click.echo("Added user.updated_at")
            # Ensure is_group exists on node
            ncols = [row[1] for row in conn.execute(text("PRAGMA table_info(node)"))]
            if "is_group" not in ncols:
                conn.execute(text("ALTER TABLE node ADD COLUMN is_group INTEGER NOT NULL DEFAULT 0"))
                click.echo("Added node.is_group")
            # Ensure priority exists on node
            ncols = [row[1] for row in conn.execute(text("PRAGMA table_info(node)"))]
            if "priority" not in ncols:
                conn.execute(text("ALTER TABLE node ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'"))
                click.echo("Added node.priority")
            # Ensure updated_at on node
            ncols = [row[1] for row in conn.execute(text("PRAGMA table_info(node)"))]
            if "updated_at" not in ncols:
                conn.execute(text("ALTER TABLE node ADD COLUMN updated_at TEXT"))
                click.echo("Added node.updated_at")
            # Ensure updated_at on comment
            ccols = [row[1] for row in conn.execute(text("PRAGMA table_info(comment)"))]
            if "updated_at" not in ccols:
                conn.execute(text("ALTER TABLE comment ADD COLUMN updated_at TEXT"))
                click.echo("Added comment.updated_at")
            # Ensure updated_at on project
            pcols = [row[1] for row in conn.execute(text("PRAGMA table_info(project)"))]
            if "updated_at" not in pcols:
                conn.execute(text("ALTER TABLE project ADD COLUMN updated_at TEXT"))
                click.echo("Added project.updated_at")
            # Ensure updated_at on edge
            ecols = [row[1] for row in conn.execute(text("PRAGMA table_info(edge)"))]
            if "updated_at" not in ecols:
                conn.execute(text("ALTER TABLE edge ADD COLUMN updated_at TEXT"))
                click.echo("Added edge.updated_at")
            # Ensure background_job table exists
        db.create_all()
        click.echo("Upgrade complete")

    @app.cli.command("translate-project")
    @click.option("--project", "project_id", required=True, help="Project ID")
    @click.option("--lang", default="en", help="Target language code, e.g., en")
    @click.option("--include-nodes/--no-include-nodes", default=True)
    @click.option("--include-comments/--no-include-comments", default=False)
    @click.option("--stale/--no-stale", default=False, help="Also refresh stale translations")
    @click.option("--provider", default=None, help="Translation provider: deepl|libre|mymemory|mock")
    @click.option("--force/--no-force", default=False, help="Force re-translate all items (overwrite cache)")
    @click.option("--verbose/--no-verbose", default=False, help="Print per-item progress (id, source, translation)")
    def translate_project_cli(project_id: str, lang: str, include_nodes: bool, include_comments: bool, stale: bool, provider: str | None, force: bool, verbose: bool) -> None:
        """Translate missing (and optionally stale) node titles and comments for a project."""
        translated = 0
        skipped = 0
        prov = (provider or os.getenv("TRANSLATION_PROVIDER") or ("deepl" if os.getenv("DEEPL_API_KEY") else "mock")).lower()
        try:
            if include_nodes:
                if force:
                    from .models import Node
                    todo = [(nid, title or "") for nid, title in db.session.query(Node.id, Node.title).filter(Node.project_id == project_id).all()]
                else:
                    missing = get_missing_node_titles(project_id, lang)
                    stale_nodes = get_stale_node_titles(project_id, lang) if stale else []
                    todo = list({(nid, t) for (nid, t) in missing + stale_nodes})
                if todo:
                    texts = [t for (_, t) in todo]
                    res = translate_texts(texts, lang, provider=prov)
                    records = []
                    for (nid, src), tr in zip(todo, res):
                        records.append((nid, lang, tr.text, tr.detected_source_lang))
                        if verbose:
                            click.echo(f"node {nid}: '{src}' -> '{tr.text}'")
                    upsert_node_translations(records)
                    translated += len(records)
                else:
                    skipped += 1
            if include_comments:
                if force:
                    from .models import Comment, Node
                    todo_c = [ (cid, body or "") for cid, body in db.session.query(Comment.id, Comment.body).join(Node, Node.id == Comment.node_id).filter(Node.project_id == project_id).all() ]
                else:
                    missing_c = get_missing_comment_bodies(project_id, lang)
                    stale_c = get_stale_comment_bodies(project_id, lang) if stale else []
                    todo_c = list({(cid, b) for (cid, b) in missing_c + stale_c})
                if todo_c:
                    texts = [b for (_, b) in todo_c]
                    res = translate_texts(texts, lang, provider=prov)
                    records = []
                    for (cid, src), tr in zip(todo_c, res):
                        records.append((cid, lang, tr.text, tr.detected_source_lang))
                        if verbose:
                            click.echo(f"comment {cid}: '{src}' -> '{tr.text}'")
                    upsert_comment_translations(records)
                    translated += len(records)
        except TranslationError as e:
            click.echo(f"Provider error: {e}")
            raise SystemExit(2)

        click.echo(f"Translated: {translated}, Skipped groups: {skipped}")

