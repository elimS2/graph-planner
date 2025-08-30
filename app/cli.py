import click
from flask import Flask
from .extensions import db
from .models import User, Project, Node, Edge
from sqlalchemy import text
import os
from datetime import datetime


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
            # Ensure is_group exists on node
            ncols = [row[1] for row in conn.execute(text("PRAGMA table_info(node)"))]
            if "is_group" not in ncols:
                conn.execute(text("ALTER TABLE node ADD COLUMN is_group INTEGER NOT NULL DEFAULT 0"))
                click.echo("Added node.is_group")
        # Ensure new tables exist
        db.create_all()
        click.echo("Upgrade complete")

