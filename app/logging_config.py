from __future__ import annotations

import logging

from app.settings import settings

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=settings.LOG_LEVEL,
)
