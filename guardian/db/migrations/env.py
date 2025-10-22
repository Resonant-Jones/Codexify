from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# Alembic config object (reads alembic.ini)
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure project root (/app) is importable (works in container & local)
HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]  # /app
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import Base from guardian.db.models per project conventions
from guardian.db.models import Base

# Alembic target metadata for autogenerate
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    # Keep everything; you can filter here later if desired
    return True


def _maybe_set_sqlalchemy_url_from_env() -> None:
    # Let DATABASE_URL override alembic.ini (useful in Docker)
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        config.set_main_option("sqlalchemy.url", env_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    _maybe_set_sqlalchemy_url_from_env()
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("sqlalchemy.url is not set for offline migrations")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    _maybe_set_sqlalchemy_url_from_env()

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:  # type: Connection
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
