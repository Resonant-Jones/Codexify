import importlib
import os


def test_default_pg_dsn_prefers_database_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://runtime:runtime@db:5432/runtime"
    )
    monkeypatch.setenv(
        "GUARDIAN_DATABASE_URL",
        "postgresql://override:override@db:5432/override",
    )
    monkeypatch.delenv("GUARDIAN_DB_URL", raising=False)

    import guardian.config.db_defaults as db_defaults

    importlib.reload(db_defaults)

    assert db_defaults.DEFAULT_PG_DSN == (
        "postgresql://runtime:runtime@db:5432/runtime"
    )


def test_default_pg_dsn_uses_compose_host(monkeypatch):
    monkeypatch.delenv("GUARDIAN_DB_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Reload module so the default is recomputed without env overrides
    import guardian.config.db_defaults as db_defaults

    importlib.reload(db_defaults)

    assert db_defaults.DEFAULT_PG_DSN == (
        "postgresql://codexify:codexify@db:5432/Codexify"
    )
