import os
import logging
from pathlib import Path
from datetime import datetime
from app import create_app

app = create_app()

def _load_dotenv_values(root: Path) -> dict:
    env_path = root / ".env"
    values: dict[str, str] = {}
    try:
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    except Exception:
        pass
    return values


def _configure_logging_from_env() -> Path:
    root = Path(__file__).resolve().parent
    envv = _load_dotenv_values(root)
    logs_dir = envv.get("LOGS_DIR", "logs")
    log_dir_path = (Path(logs_dir) if Path(logs_dir).is_absolute() else (root / logs_dir))
    log_dir_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir_path / f"server-{ts}.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # Remove existing handlers to avoid duplicates on reload
    for h in list(logger.handlers):
        logger.removeHandler(h)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return log_file


if __name__ == "__main__":
    log_path = _configure_logging_from_env()
    logging.info(f"Server starting, logging to {log_path}")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5050"))
    # Disable reloader/debug so background threads (executor) run in a single process
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

