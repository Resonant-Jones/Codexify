"""Keep programmatic Alembic tests inside pytest's logging environment."""

import logging.config

import pytest


@pytest.fixture(autouse=True)
def preserve_pytest_logging(monkeypatch):
    # Alembic's env.py configures CLI logging with fileConfig. In this shared
    # process that disables already-imported application loggers and replaces
    # pytest's handlers, affecting unrelated tests after the migration finishes.
    monkeypatch.setattr(logging.config, "fileConfig", lambda *args, **kwargs: None)
