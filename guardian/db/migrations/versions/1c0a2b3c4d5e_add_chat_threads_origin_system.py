"""add canonical conversation origin_system to chat_threads

Revision ID: 1c0a2b3c4d5e
Revises: 9d4c2a7e1b6f
Create Date: 2026-08-14 00:00:00.000000

This migration establishes the canonical, durable, queryable
``chat_threads.origin_system`` column. It is the authoritative
conversation-origin truth surface for every ``chat_threads`` row, governed
by the bounded registry in ``guardian.conversation_origin``.

Backfill rules (deterministic, never inferred from runtime model/provider):

1. Threads whose legacy ``metadata->>'import_source'`` identifies ChatGPT or
   OpenAI (tokens ``"chatgpt"`` or ``"openai"``) -> ``"openai"``.
2. Threads whose legacy import-source identifies Claude or Anthropic
   (tokens ``"claude"`` or ``"anthropic"``) -> ``"anthropic"``.
3. All remaining existing threads -> ``"codexify"`` (native Codexify).

After backfill, the migration enforces:

* non-null ``origin_system``
* bounded canonical values via a CHECK constraint
* an owner-aware composite index on ``(user_id, origin_system)`` for
  user-scoped origin filtering

The migration does NOT delete or rewrite existing import provenance
metadata. Legacy ``metadata->>'import_source'`` keys remain preserved for
audit and backward compatibility.

The downgrade is fail-closed: legacy rows without ``origin_system``
cannot be losslessly reconstructed, and backfilled values cannot be
re-derived from the canonical column alone (the legacy ``import_source``
metadata is still authoritative for audit, but the canonical column is the
new truth surface).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1c0a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "9d4c2a7e1b6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Bounded canonical origin registry. Mirrored here as a literal set so the
# migration is self-contained even if the Python module is unreachable during
# DDL execution.
CANONICAL_VALUES = ("codexify", "openai", "anthropic")

# Legacy product-name tokens actually present in existing
# ``chat_threads.metadata->>'import_source'`` rows, mapped to their canonical
# origin. Mirrors ``guardian.conversation_origin.normalize_legacy_import_source``.
LEGACY_OPENAI_TOKENS = ("chatgpt", "openai")
LEGACY_ANTHROPIC_TOKENS = ("claude", "anthropic")


def _inspector():
    bind = op.get_bind()
    return sa.inspect(bind)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _inspector().get_table_names().__contains__(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in _inspector().get_columns(table_name)
    )


def _check_constraint_exists(table_name: str, constraint_name: str) -> bool:
    return constraint_name in {
        check["name"]
        for check in _inspector().get_check_constraints(table_name)
        if check.get("name")
    }


def _index_exists(index_name: str) -> bool:
    for table in _inspector().get_table_names():
        for index in _inspector().get_indexes(table):
            if index.get("name") == index_name:
                return True
    return False


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Add the column with a server default of ``codexify`` so even rows
    #    written between ADD COLUMN and backfill pick up a valid canonical
    #    value. The default matches the canonical native-creation seam
    #    described in ``guardian.conversation_origin``.
    if not _column_exists("chat_threads", "origin_system"):
        op.execute(
            "ALTER TABLE chat_threads "
            "ADD COLUMN origin_system VARCHAR(32) NOT NULL "
            "DEFAULT 'codexify'"
        )

    # 2) Deterministic legacy backfill. Only legacy ChatGPT/OpenAI and
    #    Claude/Anthropic tokens map to external origins; everything else
    #    is native Codexify.
    # The CASE expression uses JSONB ``->>`` text extraction which returns
    # NULL when the key is absent; the COALESCE ensures the canonical
    # ``codexify`` default applies to those rows.
    backfill_statement = sa.text(
        """
            UPDATE chat_threads
            SET origin_system = CASE
                WHEN metadata->>'import_source' IN :openai_tokens THEN 'openai'
                WHEN metadata->>'import_source' IN :anthropic_tokens THEN 'anthropic'
                ELSE 'codexify'
            END
            WHERE origin_system = 'codexify'
              AND metadata->>'import_source' IS NOT NULL
            """
    ).bindparams(
        sa.bindparam("openai_tokens", expanding=True),
        sa.bindparam("anthropic_tokens", expanding=True),
    )
    bind.execute(
        backfill_statement,
        {
            "openai_tokens": LEGACY_OPENAI_TOKENS,
            "anthropic_tokens": LEGACY_ANTHROPIC_TOKENS,
        },
    )

    # 3) Enforce the bounded registry via a CHECK constraint.
    if not _check_constraint_exists(
        "chat_threads", "ck_chat_threads_origin_system_canonical"
    ):
        op.execute(
            "ALTER TABLE chat_threads "
            "ADD CONSTRAINT ck_chat_threads_origin_system_canonical "
            f"CHECK (origin_system IN {tuple(CANONICAL_VALUES)})"
        )

    # 4) Owner-aware composite index for user-scoped origin filtering. This
    #    index is intentionally NOT unindexed JSONB metadata scans; the
    #    canonical column is the authoritative filter surface.
    if not _index_exists("ix_chat_threads_user_origin"):
        op.create_index(
            "ix_chat_threads_user_origin",
            "chat_threads",
            ["user_id", "origin_system"],
        )


def downgrade() -> None:
    # Fail-closed: dropping the canonical column cannot be proven lossless
    # because legacy rows did not carry the field and the backfill cannot be
    # reversed from the canonical column alone. Operators who need to roll
    # back must do so against a captured backup; we do not silently destroy
    # the new truth surface.
    raise RuntimeError(
        "chat_threads_origin_system downgrade is fail-closed: "
        "the canonical column cannot be losslessly dropped. "
        "Restore from backup instead."
    )
