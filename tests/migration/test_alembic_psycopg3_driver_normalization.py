"""
Focused contract tests for Alembic psycopg v3 driver normalization.

The canonical Compose migrator supplies ``DATABASE_URL`` in driver-neutral
``postgresql://...`` form. SQLAlchemy resolves a bare PostgreSQL URL through
its default driver selection (psycopg2); Codexify's canonical Postgres driver
is psycopg v3, so ``guardian/db/migrations/env.py`` normalizes the bare scheme
to ``postgresql+psycopg://`` before SQLAlchemy engine construction.

These tests are pure unit tests: they do not connect to any database, do not
perform network I/O, and never touch the preserved tester database. The inert
sample credentials used here do not correspond to any real service.

Contract covered:

1. A bare ``postgresql://...`` URL normalizes to ``postgresql+psycopg://...``.
2. Username, password, host, port, database, and query-string bytes are
   preserved exactly (including percent-encoded characters).
3. Explicit ``postgresql+psycopg://`` and ``postgresql+psycopg2://`` URLs are
   preserved unchanged (never silently override an explicit driver choice).
4. Non-PostgreSQL schemes and non-string inputs pass through unchanged.
5. SQLAlchemy parses the normalized URL with drivername ``postgresql+psycopg``
   and instantiates an engine without connecting or importing psycopg2.
6. The Alembic environment applies normalization for both the ``DATABASE_URL``
   environment path and the configured ``sqlalchemy.url`` path (offline and
   online modes share ``_get_database_url()``).
7. The process-wide ``DATABASE_URL`` environment variable is never modified,
   preserving the external contract for seed/runtime consumers.
"""

from __future__ import annotations

import os
import runpy
import sys
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import NullPool

ENV_PY = (
    Path(__file__).resolve().parents[2]
    / "guardian"
    / "db"
    / "migrations"
    / "env.py"
)

# Inert sample credentials only. Do not correspond to any real service.
INERT_HOST = "127.0.0.1"
INERT_PORT = 65535  # unprivileged, high, inert
INERT_USER = "alembic_contract_user"
INERT_PASSWORD = "inert-contract-password"
INERT_DB = "codexify_contract_inert"

BARE_SCHEME = "postgresql://"
PSYCOPG_SCHEME = "postgresql+psycopg://"


def _bare_url() -> str:
    return (
        f"{BARE_SCHEME}{INERT_USER}:{INERT_PASSWORD}"
        f"@{INERT_HOST}:{INERT_PORT}/{INERT_DB}"
    )


# --- Alembic environment execution harness ---------------------------------


class FakeConfig:
    """Minimal stand-in for alembic.config.Config consumed by env.py."""

    config_file_name = None
    config_ini_section = "alembic"

    def __init__(self, config_url: str | None = None) -> None:
        self.options: dict[str, str] = (
            {"sqlalchemy.url": config_url} if config_url else {}
        )

    def get_main_option(self, name: str) -> str | None:
        return self.options.get(name)

    def set_main_option(self, name: str, value: str) -> None:
        self.options[name] = value

    def get_section(self, _name: str, _default: dict) -> dict:
        return dict(self.options)


class FakeAlembicContext:
    """Offline-mode alembic.context stand-in that records configure() kwargs."""

    def __init__(self, config: FakeConfig) -> None:
        self.config = config
        self.configure_options: dict | None = None

    def is_offline_mode(self) -> bool:
        return True

    def configure(self, **kwargs) -> None:
        self.configure_options = kwargs

    def begin_transaction(self):
        return nullcontext()

    def run_migrations(self) -> None:
        return None


def _run_alembic_environment(
    monkeypatch,
    *,
    env_url: str | None = None,
    config_url: str | None = None,
):
    """Execute guardian/db/migrations/env.py with a faked offline alembic module.

    Returns (namespace, fake_context). The module body runs in offline mode
    against the fake context, so the DATABASE_URL / sqlalchemy.url resolution
    path is exercised without any database or engine construction.
    """
    fake_config = FakeConfig(config_url=config_url)
    fake_context = FakeAlembicContext(fake_config)

    fake_alembic = ModuleType("alembic")
    setattr(fake_alembic, "context", fake_context)
    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    if env_url is not None:
        monkeypatch.setenv("DATABASE_URL", env_url)

    ns = runpy.run_path(str(ENV_PY))
    return ns, fake_context


def _normalize(monkeypatch, url: str) -> str:
    """Grab env.py's normalizer from an isolated module execution."""
    ns, _context = _run_alembic_environment(
        monkeypatch, config_url=_bare_url()
    )
    return ns["normalize_alembic_database_url"](url)


# --- Pure function contract ------------------------------------------------


def test_bare_postgresql_url_normalizes_to_psycopg3_dialect(monkeypatch) -> None:
    normalized = _normalize(monkeypatch, _bare_url())
    expected = f"{PSYCOPG_SCHEME}{_bare_url()[len(BARE_SCHEME):]}"
    assert normalized == expected


def test_normalization_preserves_user_password_host_port_database_suffix(
    monkeypatch,
) -> None:
    """Every byte after the scheme delimiter is preserved exactly."""
    bare = _bare_url()
    normalized = _normalize(monkeypatch, bare)

    suffix = bare[len(BARE_SCHEME):]
    assert normalized.endswith(suffix)

    parsed = make_url(normalized)
    assert parsed.username == INERT_USER
    assert parsed.password == INERT_PASSWORD
    assert parsed.host == INERT_HOST
    assert parsed.port == INERT_PORT
    assert parsed.database == INERT_DB


def test_normalization_preserves_query_string_suffix(monkeypatch) -> None:
    """Query-string parameters remain unchanged after normalization."""
    bare = f"{_bare_url()}?sslmode=disable&application_name=alembic-contract"
    normalized = _normalize(monkeypatch, bare)

    assert "sslmode=disable" in normalized
    assert "application_name=alembic-contract" in normalized

    parsed = make_url(normalized)
    assert parsed.query["sslmode"] == "disable"
    assert parsed.query["application_name"] == "alembic-contract"


def test_normalization_preserves_url_escaped_credential_characters(
    monkeypatch,
) -> None:
    """Percent-encoded characters survive normalization byte-for-byte.

    SQLAlchemy's ``make_url`` decodes percent-encoded characters when parsing,
    so byte-equality is asserted against the URL string, not parsed fields.
    """
    encoded_user = "user%40codexify"
    encoded_password = "p%3A%2F%2Fword"  # encodes "p://word"
    bare = (
        f"{BARE_SCHEME}{encoded_user}:{encoded_password}"
        f"@{INERT_HOST}:{INERT_PORT}/{INERT_DB}"
    )

    normalized = _normalize(monkeypatch, bare)

    assert encoded_user in normalized
    assert encoded_password in normalized
    assert normalized == f"{PSYCOPG_SCHEME}{bare[len(BARE_SCHEME):]}"


def test_explicit_psycopg_url_remains_unchanged(monkeypatch) -> None:
    """An explicitly selected psycopg 3 URL is returned as-is."""
    explicit = (
        f"{PSYCOPG_SCHEME}{INERT_USER}:{INERT_PASSWORD}"
        f"@{INERT_HOST}:{INERT_PORT}/{INERT_DB}"
    )
    assert _normalize(monkeypatch, explicit) == explicit


def test_explicit_psycopg2_url_remains_unchanged(monkeypatch) -> None:
    """An explicitly selected psycopg 2 URL is returned as-is.

    The normalizer must never silently override an explicitly selected driver.
    """
    explicit = (
        f"postgresql+psycopg2://{INERT_USER}:{INERT_PASSWORD}"
        f"@{INERT_HOST}:{INERT_PORT}/{INERT_DB}"
    )
    assert _normalize(monkeypatch, explicit) == explicit


def test_non_postgres_scheme_remains_unchanged(monkeypatch) -> None:
    """Non-PostgreSQL schemes pass through; env.py's own validation rejects them."""
    sqlite_url = "sqlite:////tmp/example.db"
    assert _normalize(monkeypatch, sqlite_url) == sqlite_url


def test_non_string_input_remains_unchanged(monkeypatch) -> None:
    """Defensive guard: non-string input passes through unchanged."""
    assert _normalize(monkeypatch, None) is None  # type: ignore[arg-type]


# --- SQLAlchemy dialect resolution -----------------------------------------


def test_sqlalchemy_parses_normalized_bare_url_with_psycopg_driver(
    monkeypatch,
) -> None:
    """SQLAlchemy reports ``postgresql+psycopg`` as the drivername."""
    parsed = make_url(_normalize(monkeypatch, _bare_url()))
    assert parsed.drivername == "postgresql+psycopg"


def test_sqlalchemy_engine_instantiation_uses_psycopg_without_network(
    monkeypatch,
) -> None:
    """create_engine against the inert URL selects the psycopg dialect, no connect.

    NullPool disables connection pooling; the engine is created and disposed
    without any network I/O against the inert host (no ``connect()`` call).
    """
    engine = create_engine(
        _normalize(monkeypatch, _bare_url()), poolclass=NullPool
    )

    try:
        assert engine.dialect.name == "postgresql"
        assert engine.url.drivername == "postgresql+psycopg"
        assert "psycopg" in engine.dialect.driver
    finally:
        engine.dispose()


# --- Alembic environment wiring --------------------------------------------


def test_alembic_environment_normalizes_database_url_before_sqlalchemy(
    monkeypatch,
) -> None:
    """DATABASE_URL path: config sqlalchemy.url and offline url are normalized."""
    plain_url = _bare_url()

    _ns, context = _run_alembic_environment(monkeypatch, env_url=plain_url)

    expected = f"{PSYCOPG_SCHEME}{plain_url[len(BARE_SCHEME):]}"
    assert context.config.get_main_option("sqlalchemy.url") == expected
    assert context.configure_options is not None
    assert context.configure_options["url"] == expected


def test_alembic_environment_normalizes_configured_url(monkeypatch) -> None:
    """alembic.ini sqlalchemy.url path is normalized the same way."""
    plain_url = f"{_bare_url()}?sslmode=require"

    _ns, context = _run_alembic_environment(
        monkeypatch, config_url=plain_url
    )

    expected = f"{PSYCOPG_SCHEME}{plain_url[len(BARE_SCHEME):]}"
    assert context.config.get_main_option("sqlalchemy.url") == expected
    assert context.configure_options is not None
    assert context.configure_options["url"] == expected


def test_alembic_environment_preserves_original_database_url_environment(
    monkeypatch,
) -> None:
    """The process-wide DATABASE_URL contract is never modified."""
    plain_url = _bare_url()

    _ns, context = _run_alembic_environment(monkeypatch, env_url=plain_url)

    assert plain_url.startswith(BARE_SCHEME)
    assert (
        context.config.get_main_option("sqlalchemy.url")
        == f"{PSYCOPG_SCHEME}{plain_url[len(BARE_SCHEME):]}"
    )
    # External contract intact: the env var is still the driver-neutral URL.
    assert os.environ["DATABASE_URL"] == plain_url


def test_alembic_environment_passes_explicit_psycopg_url_through(
    monkeypatch,
) -> None:
    """Explicit +psycopg DATABASE_URL reaches SQLAlchemy unchanged."""
    explicit = (
        f"{PSYCOPG_SCHEME}{INERT_USER}:{INERT_PASSWORD}"
        f"@{INERT_HOST}:{INERT_PORT}/{INERT_DB}"
    )

    _ns, context = _run_alembic_environment(monkeypatch, env_url=explicit)

    assert context.config.get_main_option("sqlalchemy.url") == explicit
    assert context.configure_options is not None
    assert context.configure_options["url"] == explicit
