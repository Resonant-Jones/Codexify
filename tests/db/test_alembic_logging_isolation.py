"""Database tests must not contaminate pytest's logging state.

`guardian/db/migrations/env.py` configures logging with `fileConfig` when
Alembic loads it. Python's default `disable_existing_loggers=True` then
disables application loggers the Alembic configuration does not name, and
replaces the root handlers — including pytest's `caplog` handler. A later test
in the same process that asserts on a log record sees nothing, which is how
`tests/identity/test_scout_no_seed_startup.py` fails in CI after the
migration tests in this directory have run.

These regressions need no PostgreSQL: they exercise the logging contract
directly, and they fail without the `tests/db/` guard.
"""

import importlib
import logging
import logging.config
from pathlib import Path

from tests.db.conftest import REAL_FILE_CONFIG, alembic_logging_isolation

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "backend" / "alembic.ini"

# The logger and message the Scout startup test asserts on.
GUARDIAN_LOGGER = "guardian.guardian_api"
RECORD = "scout_startup_provisioning_disabled"


def test_guardian_logger_is_initially_enabled() -> None:
    """The application logger starts enabled, before any migration runs."""
    logger = logging.getLogger(GUARDIAN_LOGGER)
    assert logger.disabled is False


def test_records_are_captured_before_alembic_configuration(caplog) -> None:
    """Log capture works normally while the guard is active."""
    logger = logging.getLogger(GUARDIAN_LOGGER)
    with caplog.at_level(logging.INFO, logger=GUARDIAN_LOGGER):
        logger.info(RECORD)
    assert RECORD in caplog.text


def test_alembic_configuration_cannot_disable_the_guardian_logger(caplog) -> None:
    """Alembic's logging configuration must not disable the logger.

    This is the contamination itself: the real `fileConfig` call would set
    `disabled` on the application logger and drop pytest's root handlers, so
    the record below would never be captured.
    """
    logger = logging.getLogger(GUARDIAN_LOGGER)
    root_handlers = list(logging.getLogger().handlers)

    with caplog.at_level(logging.INFO, logger=GUARDIAN_LOGGER):
        logging.config.fileConfig(ALEMBIC_INI)
        logger.info(RECORD)

    assert logger.disabled is False
    assert logging.getLogger().handlers == root_handlers
    assert RECORD in caplog.text


def test_alembic_environment_binds_the_guarded_file_config() -> None:
    """`env.py` binds `fileConfig` at import time; that binding must be guarded.

    `guardian/db/migrations/env.py` performs `from logging.config import
    fileConfig` in its module body, so the function it calls is resolved when
    the module is imported. Resolving that import the same way proves an
    Alembic environment loaded while the guard is active binds the guarded
    function rather than the genuine one.
    """
    module = importlib.import_module("logging.config")
    assert module.fileConfig is not REAL_FILE_CONFIG
    assert module.fileConfig is logging.config.fileConfig


def test_guard_is_removed_after_fixture_teardown() -> None:
    """The guard is scoped to the test and does not outlive it."""
    # The autouse guard is active for this test.
    assert logging.config.fileConfig is not REAL_FILE_CONFIG

    # The same guard, driven directly, restores the genuine function when its
    # scope ends.
    with alembic_logging_isolation():
        assert logging.config.fileConfig is not REAL_FILE_CONFIG

    assert logging.config.fileConfig is REAL_FILE_CONFIG
