"""Focused metadata-contract proof for ThreadSpace membership ORM mappings.

This module proves that ``guardian.db.models::Base.metadata`` describes the
already-persisted ThreadSpace membership schema created by
``d6f7a8b9c0d1_add_threadspace_node_membership``.  It exercises only the
declarative schema metadata; it does not connect to a database and does not
assert any runtime behavior.
"""

from __future__ import annotations

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from guardian.db.models import (
    Base,
    ThreadSpaceMembershipGrant,
    ThreadSpaceMembershipInvitation,
    ThreadSpaceNode,
)

INVITATION_TABLE_NAME = "threadspace_membership_invitations"
GRANT_TABLE_NAME = "threadspace_membership_grants"
NODE_TABLE_NAME = "threadspace_nodes"

INVITATION_PRIMARY_KEY = ("invitation_id",)
GRANT_PRIMARY_KEY = ("membership_id",)
NODE_PRIMARY_KEY = ("node_id",)

INVITATION_FOREIGN_KEYS = {
    "fk_threadspace_membership_invitations_node": (
        "node_id",
        "threadspace_nodes.node_id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_invitations_intended_account": (
        "intended_account_id",
        "users.id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_invitations_issuer_account": (
        "issuer_account_id",
        "users.id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_invitations_accepted_by_account": (
        "accepted_by_account_id",
        "users.id",
        "RESTRICT",
    ),
}

GRANT_FOREIGN_KEYS = {
    "fk_threadspace_membership_grants_node": (
        "node_id",
        "threadspace_nodes.node_id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_grants_subject_account": (
        "subject_account_id",
        "users.id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_grants_source_invitation": (
        "source_invitation_id",
        "threadspace_membership_invitations.invitation_id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_grants_issuer_account": (
        "issuer_account_id",
        "users.id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_grants_accepted_by_account": (
        "accepted_by_account_id",
        "users.id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_grants_suspended_by_account": (
        "suspended_by_account_id",
        "users.id",
        "RESTRICT",
    ),
    "fk_threadspace_membership_grants_revoked_by_account": (
        "revoked_by_account_id",
        "users.id",
        "RESTRICT",
    ),
}


def _column_map(table) -> dict[str, object]:
    return {column.name: column for column in table.columns}


def _expected_string_length(column, length: int) -> bool:
    return isinstance(column.type, String) and column.type.length == length


def _server_default_value(server_default) -> str:
    """Coerce a server_default's literal representation to its raw token.

    ``sa.text(\"'active'\")`` and the string ``'active'`` both resolve to the
    same SQL literal, but their ``.arg`` attributes differ in shape. This
    helper extracts the token value for comparison.
    """
    if server_default is None:
        return ""
    arg = getattr(server_default, "arg", server_default)
    if hasattr(arg, "text"):
        return arg.text.strip("'\"")
    if isinstance(arg, str):
        return arg.strip("'\"")
    return str(arg)


def test_membership_invitation_table_is_in_base_metadata() -> None:
    assert INVITATION_TABLE_NAME in Base.metadata.tables
    assert Base.metadata.tables[INVITATION_TABLE_NAME].name == INVITATION_TABLE_NAME


def test_membership_grant_table_is_in_base_metadata() -> None:
    assert GRANT_TABLE_NAME in Base.metadata.tables
    assert Base.metadata.tables[GRANT_TABLE_NAME].name == GRANT_TABLE_NAME


def test_threadspace_node_metadata_unchanged() -> None:
    assert NODE_TABLE_NAME in Base.metadata.tables
    node_table = Base.metadata.tables[NODE_TABLE_NAME]
    assert node_table.primary_key.columns.keys() == list(NODE_PRIMARY_KEY)
    columns = _column_map(node_table)
    for column_name in (
        "node_id",
        "name",
        "status",
        "created_at",
        "updated_at",
    ):
        assert column_name in columns


def test_invitation_primary_key_matches_migration() -> None:
    table = Base.metadata.tables[INVITATION_TABLE_NAME]
    assert tuple(table.primary_key.columns.keys()) == INVITATION_PRIMARY_KEY


def test_grant_primary_key_matches_migration() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    assert tuple(table.primary_key.columns.keys()) == GRANT_PRIMARY_KEY


def test_invitation_columns_match_migration_schema() -> None:
    table = Base.metadata.tables[INVITATION_TABLE_NAME]
    columns = _column_map(table)

    assert _expected_string_length(columns["invitation_id"], 64)
    assert columns["invitation_id"].primary_key is True
    assert columns["invitation_id"].nullable is False

    assert _expected_string_length(columns["node_id"], 64)
    assert columns["node_id"].nullable is False

    assert _expected_string_length(columns["intended_account_id"], 255)
    assert columns["intended_account_id"].nullable is False

    assert _expected_string_length(columns["proposed_role"], 32)
    assert columns["proposed_role"].nullable is False

    assert _expected_string_length(columns["state"], 32)
    assert columns["state"].nullable is False
    assert _server_default_value(columns["state"].server_default) == "pending"

    assert _expected_string_length(columns["issuer_account_id"], 255)
    assert columns["issuer_account_id"].nullable is False

    assert isinstance(columns["issued_at"].type, TIMESTAMP)
    assert columns["issued_at"].nullable is False

    for nullable_column in (
        "expires_at",
        "accepted_at",
        "declined_at",
        "revoked_at",
    ):
        assert isinstance(columns[nullable_column].type, TIMESTAMP)
        assert columns[nullable_column].nullable is True

    assert _expected_string_length(columns["accepted_by_account_id"], 255)
    assert columns["accepted_by_account_id"].nullable is True

    assert _expected_string_length(columns["idempotency_key"], 128)
    assert columns["idempotency_key"].nullable is False

    for timestamp_column in ("created_at", "updated_at"):
        assert isinstance(columns[timestamp_column].type, TIMESTAMP)
        assert columns[timestamp_column].nullable is False


def test_grant_columns_match_migration_schema() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    columns = _column_map(table)

    assert _expected_string_length(columns["membership_id"], 64)
    assert columns["membership_id"].primary_key is True
    assert columns["membership_id"].nullable is False

    assert _expected_string_length(columns["node_id"], 64)
    assert columns["node_id"].nullable is False

    assert _expected_string_length(columns["subject_account_id"], 255)
    assert columns["subject_account_id"].nullable is False

    assert _expected_string_length(columns["role"], 32)
    assert columns["role"].nullable is False

    assert _expected_string_length(columns["lifecycle_state"], 32)
    assert columns["lifecycle_state"].nullable is False
    assert _server_default_value(columns["lifecycle_state"].server_default) == "active"

    assert _expected_string_length(columns["source_invitation_id"], 64)
    assert columns["source_invitation_id"].nullable is True

    assert _expected_string_length(columns["issuer_account_id"], 255)
    assert columns["issuer_account_id"].nullable is False

    assert _expected_string_length(columns["accepted_by_account_id"], 255)
    assert columns["accepted_by_account_id"].nullable is True

    assert isinstance(columns["record_version"].type, Integer)
    assert columns["record_version"].nullable is False
    assert _server_default_value(columns["record_version"].server_default) == "1"

    assert isinstance(columns["effective_at"].type, TIMESTAMP)
    assert columns["effective_at"].nullable is False

    for nullable_column in (
        "suspended_at",
        "revoked_at",
        "expires_at",
    ):
        assert isinstance(columns[nullable_column].type, TIMESTAMP)
        assert columns[nullable_column].nullable is True

    assert _expected_string_length(columns["suspended_by_account_id"], 255)
    assert columns["suspended_by_account_id"].nullable is True
    assert _expected_string_length(columns["revoked_by_account_id"], 255)
    assert columns["revoked_by_account_id"].nullable is True
    assert _expected_string_length(columns["revocation_reason"], 512)
    assert columns["revocation_reason"].nullable is True

    for timestamp_column in ("created_at", "updated_at"):
        assert isinstance(columns[timestamp_column].type, TIMESTAMP)
        assert columns[timestamp_column].nullable is False


def test_invitation_foreign_keys_match_migration() -> None:
    table = Base.metadata.tables[INVITATION_TABLE_NAME]
    fk_signatures = {
        _foreign_key_signature(constraint)
        for constraint in table.foreign_key_constraints
    }
    expected_signatures = {
        (columns[0], columns[1], columns[2])
        for columns in INVITATION_FOREIGN_KEYS.values()
    }
    assert fk_signatures == expected_signatures


def test_grant_foreign_keys_match_migration() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    fk_signatures = {
        _foreign_key_signature(constraint)
        for constraint in table.foreign_key_constraints
    }
    expected_signatures = {
        (columns[0], columns[1], columns[2]) for columns in GRANT_FOREIGN_KEYS.values()
    }
    assert fk_signatures == expected_signatures


def _foreign_key_signature(constraint: ForeignKeyConstraint) -> tuple[str, ...]:
    ondelete = (constraint.ondelete or "").upper()
    return (
        list(constraint.column_keys)[0],
        ".".join(
            f"{fk.column.table.name}.{fk.column.name}" for fk in constraint.elements
        ),
        ondelete,
    )


def test_invitation_unique_constraint_matches_migration() -> None:
    table = Base.metadata.tables[INVITATION_TABLE_NAME]
    unique_constraints = {
        tuple(constraint.columns.keys()): constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert (
        unique_constraints[("node_id", "issuer_account_id", "idempotency_key")]
        == "uq_threadspace_membership_invitations_idempotency"
    )


def test_grant_unique_constraint_matches_migration() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    unique_constraints = {
        tuple(constraint.columns.keys()): constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints[("source_invitation_id",)] == (
        "uq_threadspace_membership_grants_source_invitation"
    )


def test_invitation_check_constraint_names_match_migration() -> None:
    table = Base.metadata.tables[INVITATION_TABLE_NAME]
    check_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraint_names == {
        "threadspace_membership_invitations_role_check",
        "threadspace_membership_invitations_state_check",
        "threadspace_membership_invitations_lifecycle_check",
        "threadspace_membership_invitations_idempotency_key_check",
        "threadspace_membership_invitations_expiry_check",
        "threadspace_membership_invitations_accepted_order_check",
        "threadspace_membership_invitations_declined_order_check",
        "threadspace_membership_invitations_revoked_order_check",
    }


def test_grant_check_constraint_names_match_migration() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    check_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraint_names == {
        "threadspace_membership_grants_role_check",
        "threadspace_membership_grants_lifecycle_state_check",
        "threadspace_membership_grants_source_check",
        "threadspace_membership_grants_lifecycle_check",
        "threadspace_membership_grants_record_version_check",
        "threadspace_membership_grants_suspended_order_check",
        "threadspace_membership_grants_revoked_order_check",
        "threadspace_membership_grants_expiry_check",
        "threadspace_membership_grants_revocation_reason_check",
    }


def test_invitation_indexes_match_migration() -> None:
    table = Base.metadata.tables[INVITATION_TABLE_NAME]
    index_signatures = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    assert index_signatures == {
        "ix_threadspace_membership_invitations_node_id": ("node_id",),
        "ix_threadspace_membership_invitations_intended_account_id": (
            "intended_account_id",
        ),
        "ix_threadspace_membership_invitations_state": ("state",),
    }


def test_grant_indexes_match_migration() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    index_signatures = {
        (index.name, index.unique): tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    assert index_signatures == {
        ("ix_threadspace_membership_grants_node_id", False): ("node_id",),
        ("ix_threadspace_membership_grants_subject_account_id", False): (
            "subject_account_id",
        ),
        ("ix_threadspace_membership_grants_lifecycle_state", False): (
            "lifecycle_state",
        ),
        (
            "uq_threadspace_membership_grants_node_subject_non_revoked",
            True,
        ): ("node_id", "subject_account_id"),
    }


def test_grant_partial_unique_index_matches_migration_predicate() -> None:
    table = Base.metadata.tables[GRANT_TABLE_NAME]
    partial_index = next(
        index
        for index in table.indexes
        if index.name == "uq_threadspace_membership_grants_node_subject_non_revoked"
    )
    assert partial_index.unique is True
    assert "lifecycle_state" in str(
        partial_index.dialect_options["postgresql"]["where"]
    )
    assert "<> 'revoked'" in str(partial_index.dialect_options["postgresql"]["where"])


def test_invitation_model_class_attached_to_table() -> None:
    assert ThreadSpaceMembershipInvitation.__tablename__ == INVITATION_TABLE_NAME
    assert (
        ThreadSpaceMembershipInvitation.__table__
        is Base.metadata.tables[INVITATION_TABLE_NAME]
    )


def test_grant_model_class_attached_to_table() -> None:
    assert ThreadSpaceMembershipGrant.__tablename__ == GRANT_TABLE_NAME
    assert (
        ThreadSpaceMembershipGrant.__table__ is Base.metadata.tables[GRANT_TABLE_NAME]
    )


def test_no_threadspace_relationships_or_runtime_hooks() -> None:
    """Mappings expose schema only; no navigation or runtime hooks are added."""
    for cls in (
        ThreadSpaceNode,
        ThreadSpaceMembershipInvitation,
        ThreadSpaceMembershipGrant,
    ):
        assert not getattr(
            cls, "__relationships__", {}
        ), f"{cls.__name__} must not declare ORM relationships"
        for event_hooks in (
            "__before_insert__",
            "__after_insert__",
            "__before_update__",
            "__after_update__",
        ):
            assert not hasattr(
                cls, event_hooks
            ), f"{cls.__name__} must not declare event hooks"
