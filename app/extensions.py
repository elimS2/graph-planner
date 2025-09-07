from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_marshmallow import Marshmallow
from sqlalchemy import event
from sqlalchemy.engine import Engine
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from typing import Optional


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
ma = Marshmallow()
scheduler: Optional[BackgroundScheduler] = None

# Enable SQLite foreign keys to prevent ghost references
@event.listens_for(Engine, "connect")
def _set_sqlite_fk(dbapi_connection, connection_record):  # type: ignore[no-redef]
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


def init_scheduler(app) -> None:
    global scheduler
    if scheduler and scheduler.running:
        return
    try:
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config.get('SQLALCHEMY_DATABASE_URI'))
        }
        sched = BackgroundScheduler(jobstores=jobstores, daemon=True)
        sched.start(paused=False)
        scheduler = sched
        app.logger.info('[scheduler] started with SQLAlchemyJobStore')
    except Exception:
        app.logger.exception('[scheduler] failed to start')

