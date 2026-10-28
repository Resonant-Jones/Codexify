"""Keep programmatic Alembic migrations inside pytest's logging environment.

``guardian/db/migrations/env.py`` configures Alembic's CLI logging with
``logging.config.fileConfig`` at module import. In this shared pytest process
that call replaces the root handlers and, because ``disable_existing_loggers``
defaults to true, disables application loggers that already exist -- including
``guardian.guardian_api``. Every later test in the same process then observes
an empty log capture, so an unrelated runtime assertion can fail far away from
the migration that caused it.

``tests/migration/conftest.py`` already owns this protection for its own
directory. The migrations under ``tests/db/`` run programmatically in the same
process and are selected by the canonical backend CI selection, but they live
outside that fixture's scope. This module closes that gap.

The fixture changes only the test process's logging configuration. Alembic
operations themselves, migration selection, schema readback and every database
assertion are untouched.
"""

import logging.config

import pytest


@pytest.fixture(autouse=True)
def preserve_pytest_logging():
    # Own the patch context so this fixture does not change teardown ordering
    # for tests that depend on pytest's shared monkeypatch fixture.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(logging.config, "fileConfig", lambda *args, **kwargs: None)
        yield
