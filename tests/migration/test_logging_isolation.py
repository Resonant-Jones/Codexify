"""Programmatic migrations must not disable application log capture."""

import logging
import logging.config
from pathlib import Path


def test_alembic_logging_configuration_preserves_application_capture(caplog):
    logger = logging.getLogger("guardian.routes.auth")
    handlers = list(logging.getLogger().handlers)
    config_path = Path(__file__).resolve().parents[2] / "backend" / "alembic.ini"

    with caplog.at_level(logging.WARNING, logger=logger.name):
        logging.config.fileConfig(config_path)
        logger.warning("migration_log_capture_preserved")

    assert logging.getLogger().handlers == handlers
    assert not logger.disabled
    assert "migration_log_capture_preserved" in caplog.text
