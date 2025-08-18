"""Logging configuration using structlog."""

import logging
import structlog


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level))
logger = structlog.get_logger("guardian")