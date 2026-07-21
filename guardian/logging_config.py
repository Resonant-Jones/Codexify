"""Logging configuration using structlog."""

import logging

import structlog

from guardian.utils.log_safety import install_safe_logging


def configure_logging(level: int = logging.INFO) -> None:
    install_safe_logging()
    logging.basicConfig(level=level, format="%(message)s")
    install_safe_logging()
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level)
    )


logger = structlog.get_logger("guardian")
