from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.settings import settings

_JSON_HANDLER_ATTR = "_kafka_processing_json_handler"


def setup_logging(*, force: bool = False) -> None:
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
    setattr(handler, _JSON_HANDLER_ATTR, True)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    if force:
        for existing_handler in list(root_logger.handlers):
            root_logger.removeHandler(existing_handler)

    for existing_handler in root_logger.handlers:
        if getattr(existing_handler, _JSON_HANDLER_ATTR, False):
            existing_handler.setFormatter(formatter)
            return

    root_logger.addHandler(handler)


setup_logging()
