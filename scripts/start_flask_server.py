from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict


def load_dotenv_values(root: Path) -> Dict[str, str]:
    env_path = root / ".env"
    values: Dict[str, str] = {}
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


def configure_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_file = logs_dir / f"server-{ts}.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    fh.setFormatter(fmt)
    root.addHandler(fh)
    logging.info("Logging to %s", log_file)


def main() -> int:
    root_dir = Path(__file__).resolve().parents[1]
    envv = load_dotenv_values(root_dir)
    # Ensure project root is importable when running as a file (python scripts/..)
    root_str = str(root_dir)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    host = (envv.get("HOST") or "127.0.0.1").strip().rstrip("/")
    port = int(envv.get("PORT") or 5050)
    logs_dir = envv.get("LOGS_DIR") or "instance/logs"
    logs_path = Path(logs_dir) if Path(logs_dir).is_absolute() else (root_dir / logs_dir)
    configure_logging(logs_path)

    # Ensure Flask gets correct env
    os.environ.setdefault("FLASK_ENV", "development")
    # Run app using development server directly
    from app import create_app

    app = create_app("development")
    logging.info("Starting Flask dev server on %s:%s", host, port)
    # Single-threaded dev server; disable reloader for background stability
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(0)


