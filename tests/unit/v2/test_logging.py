import logging

from sourcetrace_v2.runtime.config.models import LoggingPolicy
from sourcetrace_v2.runtime.logging.setup import configure_logging


def test_configure_logging_json_mode() -> None:
    logger = configure_logging(LoggingPolicy(format="json"))

    assert logger.name == "sourcetrace_v2"
    assert logger.level == logging.INFO
    assert logger.handlers


def test_configure_logging_text_mode() -> None:
    logger = configure_logging(LoggingPolicy(format="text", level="DEBUG"))

    assert logger.level == logging.DEBUG
    assert logger.handlers
