import importlib
import os


def test_default_pg_dsn_uses_compose_host(monkeypatch):
    monkeypatch.delenv("GUARDIAN_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Reload module so the default is recomputed without env overrides
    import guardian.config.db_defaults as db_defaults

    importlib.reload(db_defaults)

    assert "db:5432" in db_defaults.DEFAULT_PG_DSN
