from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.settings import settings


def setup_logging() -> None:
    """Configure structured JSON logging for all application loggers.

    Outputs JSON lines to stderr with fields: timestamp, level, logger, message.
    Any extra= kwargs passed to logger calls are included automatically.
    """
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.addHandler(handler)


setup_logging()
