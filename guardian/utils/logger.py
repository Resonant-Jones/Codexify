import logging
import sys


def get_logger(name="guardian", level=logging.INFO):
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Avoid adding multiple handlers

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = get_logger()
