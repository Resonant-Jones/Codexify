"""Database fixture isolation contracts, checked without a database."""

import os
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import make_url

from tests.services import (
    test_account_export_restore_unified_memory_roundtrip as roundtrip,
    test_memory_vault_creation as creation,
    test_memory_vault_mutation as mutation,
    test_memory_vault_read_projection as projection,
)


@pytest.mark.parametrize(
    "admin_url",
    [
        "postgresql://codexify_ci:ci_only@127.0.0.1:5432/codexify_ci",
        "postgresql://test_runner@/postgres?host=/tmp&port=55432",
    ],
)
def test_disposable_database_url_preserves_connection_identity(monkeypatch, admin_url):
    import psycopg

    monkeypatch.setattr(psycopg, "connect", MagicMock())
    result = make_url(creation._create_disposable_database(admin_url, "test_disposable"))
    original = make_url(admin_url)

    assert result.database == "test_disposable"
    assert result.set(database=original.database) == original


@pytest.mark.parametrize("module", [creation, mutation, projection, roundtrip])
@pytest.mark.parametrize("fails", [False, True])
def test_migration_setup_restores_environment_and_preserves_logging(
    monkeypatch, module, fails
):
    from alembic import command

    original_url = "postgresql://test_runner@localhost/original"
    disposable_url = "postgresql://test_runner@localhost/disposable"
    monkeypatch.setenv("DATABASE_URL", original_url)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    called = []

    def upgrade(config, revision):
        called.append(revision)
        assert config.config_file_name is None
        assert config.get_main_option("sqlalchemy.url") == disposable_url
        assert os.environ["DATABASE_URL"] == disposable_url
        assert os.environ["GUARDIAN_DATABASE_URL"] == disposable_url
        if fails:
            raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr(command, "upgrade", upgrade)
    if fails:
        with pytest.raises(RuntimeError, match="synthetic migration failure"):
            module._migrate_to_head(disposable_url)
    else:
        module._migrate_to_head(disposable_url)

    assert called == ["head"]
    assert os.environ["DATABASE_URL"] == original_url
    assert "GUARDIAN_DATABASE_URL" not in os.environ
