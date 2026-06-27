from __future__ import annotations

import logging

from sourcetrace_v2.runtime.config.models import LoggingPolicy
from sourcetrace_v2.runtime.logging.json_formatter import JsonFormatter
from sourcetrace_v2.runtime.logging.text_formatter import TextFormatter


def configure_logging(policy: LoggingPolicy) -> logging.Logger:
    logger = logging.getLogger("sourcetrace_v2")
    logger.handlers.clear()
    logger.setLevel(policy.level.upper())
    handler = logging.StreamHandler()
    if policy.format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
