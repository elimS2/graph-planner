import os
from pathlib import Path
from .utils.env_reader import read_dotenv_values


def _project_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent


_ENV = {}
try:
    _ENV = read_dotenv_values(_project_root())
except Exception:
    _ENV = {}


def _get_env(key: str, default: str | None = None) -> str | None:
    val = _ENV.get(key)
    if val is None or str(val).strip() == "":
        return default
    return val


class BaseConfig:
    SECRET_KEY = _get_env("SECRET_KEY", "dev-secret-key")
    # Prefer DATABASE_URL from .env; else prefer instance sqlite; else project root sqlite
    _db_env = _get_env("DATABASE_URL")
    if _db_env:
        SQLALCHEMY_DATABASE_URI = _db_env
    else:
        try:
            root = _project_root()
            inst = root / "instance" / "graph_tracker.db"
            if inst.exists():
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{inst}"
            else:
                SQLALCHEMY_DATABASE_URI = "sqlite:///graph_tracker.db"
        except Exception:
            SQLALCHEMY_DATABASE_URI = "sqlite:///graph_tracker.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    LOG_LEVEL = _get_env("LOG_LEVEL", "INFO")
    SCHEDULER_ENABLED = (_get_env("SCHEDULER_ENABLED", "1").strip() != "0")

    # File uploads configuration (read strictly from .env)
    # Root directory for storing uploaded files; can be absolute or relative to project root
    FILES_ROOT = _get_env("FILES_ROOT")
    # Max upload size in megabytes per file
    MAX_UPLOAD_MB = int((_get_env("MAX_UPLOAD_MB", "25") or "25").strip() or "25")
    # Comma-separated list of allowed MIME types (broad defaults; enforced in service)
    ALLOWED_UPLOAD_MIME = (
        _get_env(
            "ALLOWED_UPLOAD_MIME",
            ",".join(
                [
                    # images
                    "image/png",
                    "image/jpeg",
                    "image/gif",
                    "image/webp",
                    "image/svg+xml",
                    # docs
                    "application/pdf",
                    "application/zip",
                    "application/x-zip-compressed",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    # office docs
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "text/plain",
                    "text/markdown",
                ]
            ),
        )
        or ""
    ).strip()

    # Google OAuth configuration
    GOOGLE_OAUTH_ENABLED = (_get_env("GOOGLE_OAUTH_ENABLED", "1").strip() != "0")
    GOOGLE_OAUTH_CLIENT_ID = _get_env("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = _get_env("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI = _get_env("GOOGLE_OAUTH_REDIRECT_URI")
    GOOGLE_OAUTH_SCOPES = _get_env("GOOGLE_OAUTH_SCOPES", "openid email profile")
    GOOGLE_OAUTH_HD = _get_env("GOOGLE_OAUTH_HD")  # optional hosted domain restriction


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

