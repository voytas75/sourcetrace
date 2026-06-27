from __future__ import annotations

import logging

from sourcetrace_v2.runtime.logging.context import LoggingContext


class EventLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def info(self, message: str, *, context: LoggingContext) -> None:
        self.logger.info(message, extra=context.as_extra())

    def warning(self, message: str, *, context: LoggingContext) -> None:
        self.logger.warning(message, extra=context.as_extra())

    def error(self, message: str, *, context: LoggingContext) -> None:
        self.logger.error(message, extra=context.as_extra())
