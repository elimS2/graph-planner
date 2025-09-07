import os


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    # Prefer instance database if exists; fallback to project root
    _db_env = os.getenv("DATABASE_URL")
    if _db_env:
        SQLALCHEMY_DATABASE_URI = _db_env
    else:
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            root = os.path.abspath(os.path.join(here, os.pardir))
            inst = os.path.join(root, "instance", "graph_tracker.db")
            if os.path.exists(inst):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{inst}"
            else:
                SQLALCHEMY_DATABASE_URI = "sqlite:///graph_tracker.db"
        except Exception:
            SQLALCHEMY_DATABASE_URI = "sqlite:///graph_tracker.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SCHEDULER_ENABLED = (os.getenv("SCHEDULER_ENABLED", "1").strip() != "0")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

