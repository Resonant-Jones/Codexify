from __future__ import annotations

import os
from logging.config import fileConfig
from guardian.db import models
target_metadata = models.Base.metadata
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# Alembic config object (reads alembic.ini)
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base from guardian.db.models per project conventions
from guardian.db.models import Base

# Alembic target metadata for autogenerate
target_metadata = Base.metadata


# Filter objects Alembic should manage
DO_NOT_TOUCH = {"vw_big_scary_view"}  # example: list exact names to ignore
DO_NOT_TOUCH_PREFIXES = {"vw_", "mat_"}  # prefixes for views/materialized views

def include_object(object, name, type_, reflected, compare_to):
    # Never manage Alembic’s version table
    if name == "alembic_version":
        return False

    # Skip views or tables you explicitly don’t want touched
    if type_ == "table":
        is_view_flag = getattr(object, "info", {}).get("is_view", False)
        if is_view_flag or name in DO_NOT_TOUCH or any(name.startswith(p) for p in DO_NOT_TOUCH_PREFIXES):
            return False

        # Avoid dropping legacy tables that exist in DB but not in models
        if reflected and compare_to is None:
            return False

    # Ignore some index/constraint chatter if desired (comment out to re-enable)
    # if type_ in {"index", "unique_constraint", "foreign_key_constraint"}:
    #     return False

    return True


def _server_default_compare(ctx, ins_col, meta_col, rendered_meta_default, rendered_inspect_default):
    # Ignore server-default churn like NOW() vs now() formatting
    table = ins_col.table.name if ins_col is not None else (meta_col.table.name if meta_col is not None else None)
    col = ins_col.name if ins_col is not None else (meta_col.name if meta_col is not None else None)

    noisy_tables = {"chat_messages"}  # example
    noisy_cols = {("chat_messages", "created_at"), ("chat_messages", "updated_at")}

    if table in noisy_tables or (table, col) in noisy_cols:
        return False  # treat as no change
    return None  # fallback to Alembic’s normal behavior


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
        compare_server_default=_server_default_compare,
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
            compare_server_default=_server_default_compare,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
