import logging
import sys
from flask import Flask


def configure_logging(app: Flask) -> None:
    level = getattr(logging, str(app.config.get("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)

    app.logger.setLevel(level)

