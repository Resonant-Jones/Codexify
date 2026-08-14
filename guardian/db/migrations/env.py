"""
Alembic migration environment - Postgres-only.

All schema is managed via SQLAlchemy models in guardian/db/models.py.
No SQLite support - Codexify is Postgres-only as of 2025-10-26.
"""
from __future__ import annotations

import logging
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# Import ORM models
from guardian.db.models import Base

# Alembic config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Target metadata for autogenerate
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter which database objects Alembic should manage.

    - Ignores alembic_version table
    - Ignores views (vw_*, mat_*)
    - Prevents dropping tables that exist in DB but not in models (safety)
    """
    # Never manage Alembic's version table
    if name == "alembic_version":
        return False

    # Skip views
    if type_ == "table":
        is_view = getattr(object, "info", {}).get("is_view", False)
        if is_view or name.startswith("vw_") or name.startswith("mat_"):
            return False

        # Safety: Don't drop tables that exist in DB but not in models
        # This prevents accidental data loss during schema evolution
        if reflected and compare_to is None:
            logger.warning(
                f"Table '{name}' exists in DB but not in models - will not drop"
            )
            return False

    return True


def _server_default_compare(
    context,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    """
    Reduce noise from server_default comparisons.

    Postgres may format defaults differently (now() vs NOW() vs CURRENT_TIMESTAMP).
    This prevents spurious migration generation.

    Returns None to use Alembic's default comparison logic.
    """
    return None  # Use Alembic's default comparison


def normalize_alembic_database_url(url: str) -> str:
    """
    Normalize a driver-neutral PostgreSQL URL to the canonical psycopg v3
    SQLAlchemy dialect.

    SQLAlchemy resolves a bare ``postgresql://`` URL through its default
    PostgreSQL driver selection (psycopg2). Codexify's canonical Postgres
    driver is psycopg v3 (``psycopg[binary]`` in the backend runtime
    manifest), so the Alembic environment rewrites the bare scheme to
    ``postgresql+psycopg://`` before SQLAlchemy engine construction.

    Only the scheme prefix is rewritten; every byte after it is preserved.
    Explicit driver selections (``postgresql+psycopg://``,
    ``postgresql+psycopg2://``, ...) are preserved unchanged. The
    process-wide ``DATABASE_URL`` environment contract is never modified.
    """
    if not isinstance(url, str):
        # Defensive guard: keep downstream errors descriptive rather than
        # masked by an unexpected coercion.
        return url

    bare_scheme = "postgresql://"
    if url.startswith(bare_scheme):
        return "postgresql+psycopg://" + url[len(bare_scheme):]

    # Explicit driver selections (psycopg, psycopg2, asyncpg, ...) are
    # preserved exactly. No silent override of an explicitly selected driver.
    return url


def _get_database_url() -> str:
    """
    Get database URL with environment override support.

    Priority:
    1. DATABASE_URL environment variable (Docker/prod)
    2. alembic.ini sqlalchemy.url setting (local dev)

    A driver-neutral ``postgresql://`` URL is normalized to the canonical
    ``postgresql+psycopg://`` SQLAlchemy dialect before engine construction
    so the resolved DBAPI driver matches the psycopg v3 runtime dependency.
    Explicit driver selections are preserved unchanged. The ``DATABASE_URL``
    environment variable itself is never modified, so seed/runtime consumers
    keep the original external contract.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Ensure it's Postgres
        if not env_url.startswith("postgresql"):
            raise RuntimeError(
                f"Codexify requires Postgres. Got: {env_url[:30]}...\n"
                f"Set DATABASE_URL to a postgresql:// URL"
            )
        normalized = normalize_alembic_database_url(env_url)
        logger.info("Using DATABASE_URL from environment")
        config.set_main_option("sqlalchemy.url", normalized)
        return normalized

    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "sqlalchemy.url not configured. "
            "Set DATABASE_URL environment variable or update alembic.ini"
        )

    if not url.startswith("postgresql"):
        raise RuntimeError(
            f"Codexify requires Postgres. Check alembic.ini: {url[:30]}..."
        )

    normalized = normalize_alembic_database_url(url)
    config.set_main_option("sqlalchemy.url", normalized)
    return normalized


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (SQL script generation).

    This generates a SQL script without connecting to the database.
    Useful for review or manual application.
    """
    url = _get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=False,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (direct database execution).

    This connects to the database and applies migrations directly.
    """
    _get_database_url()  # Validate and set URL

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No connection pooling for migrations
    )

    with connectable.connect() as connection:  # type: Connection
        # Verify it's Postgres
        dialect_name = connection.dialect.name
        if dialect_name != "postgresql":
            raise RuntimeError(
                f"Codexify requires Postgres. Connected to: {dialect_name}"
            )

        logger.info(f"Running migrations on Postgres database")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=False,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


# Entry point
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
