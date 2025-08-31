import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask

from .config import DevelopmentConfig, ProductionConfig, TestingConfig
from .extensions import db, migrate, ma, login_manager
from flask_login import AnonymousUserMixin
from .logging_config import configure_logging
from .error_handlers import register_error_handlers
from .cli import register_cli


def create_app(config_name: str | None = None) -> Flask:
    """Application factory."""
    app = Flask(__name__)

    # Load .env
    load_dotenv()
    # Select config
    env = config_name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development"
    if env.lower() in {"prod", "production"}:
        app.config.from_object(ProductionConfig())
    elif env.lower() in {"test", "testing"}:
        app.config.from_object(TestingConfig())
    else:
        app.config.from_object(DevelopmentConfig())

    # Configure logging and extensions
    configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    login_manager.init_app(app)
    # Minimal login setup for anonymous sessions
    login_manager.anonymous_user = AnonymousUserMixin

    @login_manager.user_loader
    def _load_user(user_id: str):
        from .models import User
        return db.session.get(User, user_id)

    # Register blueprints
    from .blueprints.main.routes import bp as main_bp
    from .blueprints.graph.routes import bp as graph_bp
    from .blueprints.tasks.routes import bp as tasks_bp
    from .blueprints.tracking.routes import bp as tracking_bp
    from .blueprints.users.routes import bp as users_bp
    from .blueprints.settings.routes import bp as settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)

    # Error handlers
    register_error_handlers(app)
    register_cli(app)

    # Server boot timestamp (UTC) for health/uptime reporting
    try:
        app.config["SERVER_STARTED_AT"] = datetime.utcnow().isoformat() + "Z"
    except Exception:
        pass

    return app

