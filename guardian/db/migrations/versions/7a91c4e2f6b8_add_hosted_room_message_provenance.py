"""add Hosted Room participant provenance to chat_messages

Revision ID: 7a91c4e2f6b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-28 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Inspector

revision: str = "7a91c4e2f6b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Maximum display-name snapshot length (matches participant display_name)
_SNAPSHOT_MAX_LENGTH = 255
_TABLE_SCHEMA = "public"
_PROVENANCE_CHECK = (
    "("
    "hosted_room_participant_id IS NULL "
    "AND sender_display_name_snapshot IS NULL"
    ") OR ("
    "hosted_room_participant_id IS NOT NULL "
    "AND sender_display_name_snapshot IS NOT NULL "
    "AND sender_display_name_snapshot <> ''"
    ")"
)
_OWNERSHIP_MARKER = "codexify:7a91c4e2f6b8:created"
_PROVENANCE_CLEANUP_FUNCTION = (
    "fn_chat_messages_clear_participant_snapshot"
)
_PROVENANCE_CLEANUP_TRIGGER = (
    "trg_chat_messages_clear_participant_snapshot"
)


def _inspector() -> Inspector:
    return sa.inspect(op.get_bind())


def _fail(object_name: str, detail: str) -> None:
    raise RuntimeError(
        f"Migration {revision} cannot reconcile {object_name}: {detail}"
    )


def _normalize_sql(expression: str | None) -> str:
    if expression is None:
        return ""
    normalized = "".join(expression.lower().split())
    for postgres_cast in ("::text", "::charactervarying", "::varchar"):
        normalized = normalized.replace(postgres_cast, "")
    normalized = normalized.replace("(", "").replace(")", "")
    return normalized


def _column_matches(column: dict, length: int) -> bool:
    column_type = column["type"]
    return (
        isinstance(column_type, sa.String)
        and column_type.length == length
        and column["nullable"] is True
    )


def _ensure_column(
    inspector: Inspector,
    *,
    name: str,
    length: int,
) -> None:
    columns = {
        column["name"]: column
        for column in inspector.get_columns("chat_messages", schema=_TABLE_SCHEMA)
    }
    existing = columns.get(name)
    if existing is not None:
        if not _column_matches(existing, length):
            _fail(
                f"chat_messages.{name}",
                f"expected nullable VARCHAR({length}), observed "
                f"type={existing['type']!s}, nullable={existing['nullable']!r}",
            )
        return

    op.add_column(
        "chat_messages",
        sa.Column(name, sa.String(length=length), nullable=True),
        schema=_TABLE_SCHEMA,
    )
    op.execute(
        sa.text(
            f"COMMENT ON COLUMN {_TABLE_SCHEMA}.chat_messages.{name} "
            f"IS '{_OWNERSHIP_MARKER}'"
        )
    )


def _ensure_check_constraint(inspector: Inspector) -> None:
    checks = {
        check["name"]: check
        for check in inspector.get_check_constraints(
            "chat_messages", schema=_TABLE_SCHEMA
        )
    }
    existing = checks.get("ck_chat_messages_paired_provenance")
    if existing is not None:
        if _normalize_sql(existing.get("sqltext")) != _normalize_sql(
            _PROVENANCE_CHECK
        ):
            _fail(
                "constraint ck_chat_messages_paired_provenance",
                f"expected {_PROVENANCE_CHECK!r}, observed "
                f"{existing.get('sqltext')!r}",
            )
        return

    bind = op.get_bind()
    invalid_count = bind.execute(
        sa.text(
            "SELECT count(*) FROM public.chat_messages "
            "WHERE NOT ("
            "(hosted_room_participant_id IS NULL "
            "AND sender_display_name_snapshot IS NULL) OR ("
            "hosted_room_participant_id IS NOT NULL "
            "AND sender_display_name_snapshot IS NOT NULL "
            "AND sender_display_name_snapshot <> ''))"
        )
    ).scalar_one()
    if invalid_count:
        sample_ids = [
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT id FROM public.chat_messages "
                    "WHERE NOT ("
                    "(hosted_room_participant_id IS NULL "
                    "AND sender_display_name_snapshot IS NULL) OR ("
                    "hosted_room_participant_id IS NOT NULL "
                    "AND sender_display_name_snapshot IS NOT NULL "
                    "AND sender_display_name_snapshot <> '')) "
                    "ORDER BY id LIMIT 5"
                )
            )
        ]
        _fail(
            "constraint ck_chat_messages_paired_provenance",
            f"{invalid_count} existing row(s) violate the paired-provenance "
            f"rule; sample message ids={sample_ids!r}",
        )

    op.create_check_constraint(
        "ck_chat_messages_paired_provenance",
        "chat_messages",
        _PROVENANCE_CHECK,
        schema=_TABLE_SCHEMA,
    )
    op.execute(
        sa.text(
            "COMMENT ON CONSTRAINT ck_chat_messages_paired_provenance "
            "ON public.chat_messages "
            f"IS '{_OWNERSHIP_MARKER}'"
        )
    )


def _ensure_foreign_key(inspector: Inspector) -> None:
    existing = next(
        (
            foreign_key
            for foreign_key in inspector.get_foreign_keys(
                "chat_messages", schema=_TABLE_SCHEMA
            )
            if foreign_key.get("name")
            == "fk_chat_messages_hosted_room_participant_id"
        ),
        None,
    )
    if existing is not None:
        options = existing.get("options") or {}
        observed_ondelete = (options.get("ondelete") or "").upper()
        if (
            existing.get("constrained_columns")
            != ["hosted_room_participant_id"]
            or existing.get("referred_table") != "hosted_room_participants"
            or existing.get("referred_columns") != ["id"]
            or existing.get("referred_schema") not in (None, _TABLE_SCHEMA)
            or observed_ondelete != "SET NULL"
        ):
            _fail(
                "foreign key fk_chat_messages_hosted_room_participant_id",
                "expected chat_messages.hosted_room_participant_id -> "
                "hosted_room_participants.id ON DELETE SET NULL, observed "
                f"{existing!r}",
            )
        return

    bind = op.get_bind()
    invalid_count = bind.execute(
        sa.text(
            "SELECT count(*) FROM public.chat_messages AS messages "
            "LEFT JOIN public.hosted_room_participants AS participants "
            "ON participants.id = messages.hosted_room_participant_id "
            "WHERE messages.hosted_room_participant_id IS NOT NULL "
            "AND participants.id IS NULL"
        )
    ).scalar_one()
    if invalid_count:
        sample_ids = [
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT messages.id FROM public.chat_messages AS messages "
                    "LEFT JOIN public.hosted_room_participants AS participants "
                    "ON participants.id = messages.hosted_room_participant_id "
                    "WHERE messages.hosted_room_participant_id IS NOT NULL "
                    "AND participants.id IS NULL "
                    "ORDER BY messages.id LIMIT 5"
                )
            )
        ]
        _fail(
            "foreign key fk_chat_messages_hosted_room_participant_id",
            f"{invalid_count} existing row(s) reference missing Hosted Room "
            f"participants; sample message ids={sample_ids!r}",
        )

    op.create_foreign_key(
        "fk_chat_messages_hosted_room_participant_id",
        "chat_messages",
        "hosted_room_participants",
        ["hosted_room_participant_id"],
        ["id"],
        source_schema=_TABLE_SCHEMA,
        referent_schema=_TABLE_SCHEMA,
        ondelete="SET NULL",
    )
    op.execute(
        sa.text(
            "COMMENT ON CONSTRAINT fk_chat_messages_hosted_room_participant_id "
            "ON public.chat_messages "
            f"IS '{_OWNERSHIP_MARKER}'"
        )
    )


def _ensure_index(inspector: Inspector) -> None:
    existing = next(
        (
            index
            for index in inspector.get_indexes(
                "chat_messages", schema=_TABLE_SCHEMA
            )
            if index.get("name") == "ix_chat_messages_hosted_room_participant_id"
        ),
        None,
    )
    if existing is not None:
        if existing.get("column_names") != ["hosted_room_participant_id"] or bool(
            existing.get("unique")
        ):
            _fail(
                "index ix_chat_messages_hosted_room_participant_id",
                "expected a non-unique index on "
                "chat_messages.hosted_room_participant_id, observed "
                f"{existing!r}",
            )
        return

    op.create_index(
        "ix_chat_messages_hosted_room_participant_id",
        "chat_messages",
        ["hosted_room_participant_id"],
        schema=_TABLE_SCHEMA,
    )
    op.execute(
        sa.text(
            "COMMENT ON INDEX public.ix_chat_messages_hosted_room_participant_id "
            f"IS '{_OWNERSHIP_MARKER}'"
        )
    )


def _ensure_provenance_cleanup_trigger() -> None:
    """Keep the strict pair valid when the FK nulls its participant ID."""
    bind = op.get_bind()
    function_definition = bind.execute(
        sa.text(
            "SELECT pg_get_functiondef(pg_proc.oid) "
            "FROM pg_proc "
            "JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace "
            "WHERE pg_namespace.nspname = 'public' "
            "AND pg_proc.proname = :name "
            "AND pg_proc.pronargs = 0"
        ),
        {"name": _PROVENANCE_CLEANUP_FUNCTION},
    ).scalar()
    if function_definition is None:
        op.execute(
            sa.text(
                f"""
                CREATE FUNCTION public.{_PROVENANCE_CLEANUP_FUNCTION}()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    IF NEW.hosted_room_participant_id IS NULL
                       AND OLD.hosted_room_participant_id IS NOT NULL
                    THEN
                        NEW.sender_display_name_snapshot := NULL;
                    END IF;
                    RETURN NEW;
                END;
                $$
                """
            )
        )
        op.execute(
            sa.text(
                f"COMMENT ON FUNCTION public.{_PROVENANCE_CLEANUP_FUNCTION}() "
                f"IS '{_OWNERSHIP_MARKER}'"
            )
        )
    elif not all(
        fragment in _normalize_sql(function_definition)
        for fragment in (
            "new.hosted_room_participant_idisnull",
            "old.hosted_room_participant_idisnotnull",
            "new.sender_display_name_snapshot:=null",
        )
    ):
        _fail(
            f"function {_PROVENANCE_CLEANUP_FUNCTION}()",
            "existing function does not clear the paired snapshot when the "
            "participant foreign key is nulled",
        )

    trigger_definition = bind.execute(
        sa.text(
            "SELECT pg_get_triggerdef(pg_trigger.oid) "
            "FROM pg_trigger "
            "JOIN pg_class ON pg_class.oid = pg_trigger.tgrelid "
            "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
            "WHERE pg_namespace.nspname = 'public' "
            "AND pg_class.relname = 'chat_messages' "
            "AND pg_trigger.tgname = :name "
            "AND NOT pg_trigger.tgisinternal"
        ),
        {"name": _PROVENANCE_CLEANUP_TRIGGER},
    ).scalar()
    if trigger_definition is None:
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER {_PROVENANCE_CLEANUP_TRIGGER}
                BEFORE UPDATE OF hosted_room_participant_id
                ON public.chat_messages
                FOR EACH ROW
                EXECUTE FUNCTION public.{_PROVENANCE_CLEANUP_FUNCTION}()
                """
            )
        )
        op.execute(
            sa.text(
                f"COMMENT ON TRIGGER {_PROVENANCE_CLEANUP_TRIGGER} "
                "ON public.chat_messages "
                f"IS '{_OWNERSHIP_MARKER}'"
            )
        )
    elif not all(
        fragment in _normalize_sql(trigger_definition)
        for fragment in (
            "beforeupdateofhosted_room_participant_id",
            f"public.{_PROVENANCE_CLEANUP_FUNCTION}()",
        )
    ):
        _fail(
            f"trigger {_PROVENANCE_CLEANUP_TRIGGER}",
            "existing trigger does not run the canonical participant-snapshot "
            "cleanup before the provenance foreign key is nulled",
        )


def _owned_column(name: str) -> bool:
    return (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT col_description('public.chat_messages'::regclass, "
                "attnum) FROM pg_attribute "
                "WHERE attrelid = 'public.chat_messages'::regclass "
                "AND attname = :name"
            ),
            {"name": name},
        )
        .scalar()
        == _OWNERSHIP_MARKER
    )


def _owned_constraint(name: str) -> bool:
    return (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT obj_description(pg_constraint.oid, 'pg_constraint') "
                "FROM pg_constraint "
                "JOIN pg_class ON pg_class.oid = pg_constraint.conrelid "
                "WHERE pg_class.relnamespace = 'public'::regnamespace "
                "AND pg_class.relname = 'chat_messages' "
                "AND pg_constraint.conname = :name"
            ),
            {"name": name},
        )
        .scalar()
        == _OWNERSHIP_MARKER
    )


def _owned_index(name: str) -> bool:
    return (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT obj_description(pg_class.oid, 'pg_class') "
                "FROM pg_class "
                "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                "WHERE pg_namespace.nspname = 'public' "
                "AND pg_class.relname = :name"
            ),
            {"name": name},
        )
        .scalar()
        == _OWNERSHIP_MARKER
    )


def _owned_trigger() -> bool:
    return (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT obj_description(pg_trigger.oid, 'pg_trigger') "
                "FROM pg_trigger "
                "JOIN pg_class ON pg_class.oid = pg_trigger.tgrelid "
                "JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace "
                "WHERE pg_namespace.nspname = 'public' "
                "AND pg_class.relname = 'chat_messages' "
                "AND pg_trigger.tgname = :name "
                "AND NOT pg_trigger.tgisinternal"
            ),
            {"name": _PROVENANCE_CLEANUP_TRIGGER},
        )
        .scalar()
        == _OWNERSHIP_MARKER
    )


def _owned_function() -> bool:
    return (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT obj_description(pg_proc.oid, 'pg_proc') "
                "FROM pg_proc "
                "JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace "
                "WHERE pg_namespace.nspname = 'public' "
                "AND pg_proc.proname = :name "
                "AND pg_proc.pronargs = 0"
            ),
            {"name": _PROVENANCE_CLEANUP_FUNCTION},
        )
        .scalar()
        == _OWNERSHIP_MARKER
    )


def upgrade() -> None:
    # Existing-instance reconciliation is structural, not an IF NOT EXISTS skip.
    # New objects receive a PostgreSQL comment marker so downgrade can reverse
    # only objects this migration created; matching pre-existing objects remain.
    inspector = _inspector()
    _ensure_column(
        inspector,
        name="hosted_room_participant_id",
        length=36,
    )
    _ensure_column(
        inspector,
        name="sender_display_name_snapshot",
        length=_SNAPSHOT_MAX_LENGTH,
    )
    inspector = _inspector()
    _ensure_check_constraint(inspector)
    inspector = _inspector()
    _ensure_foreign_key(inspector)
    inspector = _inspector()
    _ensure_provenance_cleanup_trigger()
    inspector = _inspector()
    _ensure_index(inspector)


def downgrade() -> None:
    # A matching object may predate this revision, so never drop it merely
    # because upgrade observed it.  The migration-local PostgreSQL comments
    # above are the ownership record for safe reversal on clean installs.
    inspector = _inspector()
    if any(
        index.get("name") == "ix_chat_messages_hosted_room_participant_id"
        for index in inspector.get_indexes("chat_messages", schema=_TABLE_SCHEMA)
    ) and _owned_index("ix_chat_messages_hosted_room_participant_id"):
        op.drop_index(
            "ix_chat_messages_hosted_room_participant_id",
            table_name="chat_messages",
            schema=_TABLE_SCHEMA,
        )

    if _owned_trigger():
        op.execute(
            sa.text(
                f"DROP TRIGGER {_PROVENANCE_CLEANUP_TRIGGER} "
                "ON public.chat_messages"
            )
        )
    if _owned_function():
        op.execute(
            sa.text(
                f"DROP FUNCTION public.{_PROVENANCE_CLEANUP_FUNCTION}()"
            )
        )

    inspector = _inspector()
    if any(
        foreign_key.get("name")
        == "fk_chat_messages_hosted_room_participant_id"
        for foreign_key in inspector.get_foreign_keys(
            "chat_messages", schema=_TABLE_SCHEMA
        )
    ) and _owned_constraint("fk_chat_messages_hosted_room_participant_id"):
        op.drop_constraint(
            "fk_chat_messages_hosted_room_participant_id",
            "chat_messages",
            type_="foreignkey",
            schema=_TABLE_SCHEMA,
        )

    inspector = _inspector()
    if any(
        check.get("name") == "ck_chat_messages_paired_provenance"
        for check in inspector.get_check_constraints(
            "chat_messages", schema=_TABLE_SCHEMA
        )
    ) and _owned_constraint("ck_chat_messages_paired_provenance"):
        op.drop_constraint(
            "ck_chat_messages_paired_provenance",
            "chat_messages",
            type_="check",
            schema=_TABLE_SCHEMA,
        )

    if _owned_column("sender_display_name_snapshot"):
        op.drop_column(
            "chat_messages",
            "sender_display_name_snapshot",
            schema=_TABLE_SCHEMA,
        )
    if _owned_column("hosted_room_participant_id"):
        op.drop_column(
            "chat_messages",
            "hosted_room_participant_id",
            schema=_TABLE_SCHEMA,
        )
