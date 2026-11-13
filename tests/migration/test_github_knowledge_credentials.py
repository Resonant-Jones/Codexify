"""Pilot schema is opt-in application state; no production migration is run."""

import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from guardian.db.models import GitHubKnowledgeCredential


def test_lineage_and_schema_upgrade_downgrade(monkeypatch):
    path = Path(
        "guardian/db/migrations/versions/c13f0713a901_add_github_knowledge_credentials.py"
    )
    spec = importlib.util.spec_from_file_location("github_pilot_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "c7e4a1b9d602"
    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    assert script.get_heads() == ["d8a90bf32107"]
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        monkeypatch.setattr(
            module, "op", Operations(MigrationContext.configure(connection))
        )
        module.upgrade()
        columns = {
            c["name"]
            for c in inspect(connection).get_columns("github_knowledge_credentials")
        }
        assert columns == set(GitHubKnowledgeCredential.__table__.columns.keys())
        assert "encrypted_token" in columns and "token" not in columns
        module.downgrade()
        assert (
            "github_knowledge_credentials" not in inspect(connection).get_table_names()
        )
    ddl = str(
        CreateTable(GitHubKnowledgeCredential.__table__).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "JSONB" in ddl and "UNIQUE (user_id)" in ddl
