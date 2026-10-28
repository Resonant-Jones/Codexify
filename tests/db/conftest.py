"""Keep programmatic Alembic tests inside pytest's logging environment.

`guardian/db/migrations/env.py` configures logging with
`logging.config.fileConfig` when Alembic loads it. Python's default
`disable_existing_loggers=True` then disables every already-created
application logger the Alembic configuration does not name, and replaces the
root handlers — including pytest's `caplog` handler. A later test in the same
process that asserts on a log record then sees nothing, which is how
`tests/identity/test_scout_no_seed_startup.py` fails in CI after the
migration tests in this directory have run.

`tests/migration/conftest.py` already owns this protection for its own
directory. This module gives `tests/db/` the equivalent guard so the
migration tests here cannot contaminate logging state for later tests.

The guard is test-scoped: it is installed for the duration of a single test
and the genuine `logging.config.fileConfig` is restored when that test
finishes. Alembic's production logging configuration is not modified.
"""

import contextlib
import logging.config

import pytest

# Captured while this module is imported, before any fixture runs, so the
# guard restores the genuine function rather than another patched copy.
REAL_FILE_CONFIG = logging.config.fileConfig


def _no_op_file_config(*args, **kwargs):
    """Stand in for Alembic's logging reconfiguration.

    `guardian/db/migrations/env.py` performs `from logging.config import
    fileConfig` in its module body, so the function it calls is resolved when
    Alembic loads the environment. While this guard is installed that
    resolution yields this no-op, and the application loggers the Alembic
    configuration does not name stay enabled.
    """
    return None


@contextlib.contextmanager
def alembic_logging_isolation():
    """Prevent Alembic's logging reconfiguration from disabling loggers."""
    logging.config.fileConfig = _no_op_file_config
    try:
        yield
    finally:
        logging.config.fileConfig = REAL_FILE_CONFIG


@pytest.fixture(autouse=True)
def preserve_pytest_logging():
    # Alembic's env.py configures CLI logging with fileConfig. In this shared
    # process that disables already-imported application loggers and replaces
    # pytest's handlers, affecting unrelated tests after the migration finishes.
    # Own the patch context so this fixture does not change teardown ordering
    # for tests that depend on pytest's shared monkeypatch fixture.
    with alembic_logging_isolation():
        yield
