#!/usr/bin/env python3
"""Round-trip-stable governed-schema equivalence for PostgreSQL.

The contract deliberately compares the schema after one controlled
``pg_dump --schema-only --no-owner --no-privileges`` and clean restore.  It is
evidence tooling, not an Alembic runner and not a production migration path.
Only the six relations named by the reconciled R2 surface are in scope.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

CONTRACT_VERSION = "governed-schema-equivalence/v1"
EXPECTED_POSTGRES_MAJOR = 15
EXPECTED_ALEMBIC_REVISION = "9c66e490a42b"

GOVERNED_RELATIONS: tuple[str, ...] = (
    "github_watchdog_delivery_receipts",
    "github_watchdog_review_attempts",
    "github_watchdog_review_input_snapshots",
    "github_watchdog_review_results",
    "github_watchdog_review_dispatches",
    "notion_connection_credentials",
)

_DESCRIPTOR_SECTIONS = ("relations", "columns", "constraints", "indexes")
_DESCRIPTOR_KEYS = {
    "relations": frozenset({"schema", "name"}),
    "columns": frozenset(
        {
            "schema",
            "relation",
            "ordinal",
            "name",
            "type",
            "not_null",
            "default",
            "identity",
            "generated",
            "collation",
        }
    ),
    "constraints": frozenset(
        {
            "schema",
            "relation",
            "name",
            "type",
            "deferrable",
            "initially_deferred",
            "on_delete",
            "on_update",
            "definition",
            "local_columns",
            "referenced_relation",
            "referenced_columns",
        }
    ),
    "indexes": frozenset(
        {
            "schema",
            "relation",
            "name",
            "unique",
            "primary",
            "definition",
            "predicate",
        }
    ),
}
_ACTION_NAMES = {
    "": "NOT APPLICABLE",
    "a": "NO ACTION",
    "r": "RESTRICT",
    "c": "CASCADE",
    "n": "SET NULL",
    "d": "SET DEFAULT",
}


class ContractError(RuntimeError):
    """Base class for fail-closed contract errors."""

    code = "CONTRACT_ERROR"


class PostgresMajorMismatch(ContractError):
    code = "POSTGRES_MAJOR_MISMATCH"

    def __init__(self, expected: int, observed: int) -> None:
        super().__init__(
            f"PostgreSQL major mismatch: expected {expected}, observed {observed}"
        )
        self.expected = expected
        self.observed = observed


class AlembicRevisionMismatch(ContractError):
    code = "ALEMBIC_REVISION_MISMATCH"

    def __init__(self, expected: str, observed: Sequence[str]) -> None:
        rendered = ",".join(observed) if observed else "<none>"
        super().__init__(
            f"Alembic revision mismatch: expected {expected}, observed {rendered}"
        )
        self.expected = expected
        self.observed = tuple(observed)


class MissingGovernedRelation(ContractError):
    code = "MISSING_GOVERNED_RELATION"

    def __init__(self, missing: Sequence[str]) -> None:
        super().__init__("Missing governed relation(s): " + ", ".join(sorted(missing)))
        self.missing = tuple(sorted(missing))


class DisposableTargetRequired(ContractError):
    code = "DISPOSABLE_TARGET_REQUIRED"


class CommandExecutionFailure(ContractError):
    code = "CONTROLLED_COMMAND_FAILED"

    def __init__(self, command_name: str, return_code: int) -> None:
        super().__init__(
            f"controlled {command_name} failed with exit status {return_code}"
        )
        self.command_name = command_name
        self.return_code = return_code


class InvalidSnapshot(ContractError):
    code = "INVALID_SNAPSHOT"


@dataclass(frozen=True)
class SourceMetadata:
    """Source identity captured before schema canonicalization."""

    postgres_major: int
    alembic_revisions: tuple[str, ...]

    @property
    def alembic_revision(self) -> str:
        if len(self.alembic_revisions) != 1:
            raise InvalidSnapshot(
                "source metadata must contain exactly one Alembic revision"
            )
        return self.alembic_revisions[0]


@dataclass(frozen=True)
class GovernedSchemaSnapshot:
    """Digest-bearing canonical descriptor envelope."""

    contract_version: str
    postgres_major: int
    source_revision: str
    descriptors: dict[str, Any]
    digest: str

    def envelope(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "postgres_major": self.postgres_major,
            "source_revision": self.source_revision,
            "descriptors": normalize_descriptors(self.descriptors),
        }

    def as_dict(self) -> dict[str, Any]:
        result = self.envelope()
        result["digest"] = self.digest
        return result


@dataclass(frozen=True)
class ComparisonResult:
    equivalent: bool
    reasons: tuple[str, ...]
    descriptor_diff: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "equivalent": self.equivalent,
            "reasons": list(self.reasons),
            "descriptor_diff": list(self.descriptor_diff),
        }


def _rows(connection: Any, statement: str, parameters: Sequence[Any] = ()) -> list[Any]:
    """Run a read-only catalog query and return its rows."""

    with connection.cursor() as cursor:
        cursor.execute(statement, tuple(parameters))
        return list(cursor.fetchall())


def _scalar(connection: Any, statement: str, parameters: Sequence[Any] = ()) -> Any:
    rows = _rows(connection, statement, parameters)
    if not rows:
        raise ContractError("catalog query returned no scalar row")
    return rows[0][0]


def postgres_major(connection: Any) -> int:
    """Read the server major without changing the connection or database."""

    version_num = int(
        str(_scalar(connection, "SELECT current_setting('server_version_num')"))
    )
    return version_num // 10000


def read_alembic_revisions(connection: Any) -> tuple[str, ...]:
    """Read the complete version table in deterministic order."""

    exists = _scalar(
        connection,
        "SELECT to_regclass('public.alembic_version') IS NOT NULL",
    )
    if not exists:
        return ()
    rows = _rows(
        connection,
        "SELECT version_num FROM public.alembic_version ORDER BY version_num",
    )
    return tuple(str(row[0]) for row in rows)


def verify_source_metadata(
    connection: Any,
) -> SourceMetadata:
    """Capture and validate source identity before invoking ``pg_dump``."""

    observed_major = postgres_major(connection)
    if observed_major != EXPECTED_POSTGRES_MAJOR:
        raise PostgresMajorMismatch(EXPECTED_POSTGRES_MAJOR, observed_major)

    revisions = read_alembic_revisions(connection)
    if revisions != (EXPECTED_ALEMBIC_REVISION,):
        raise AlembicRevisionMismatch(EXPECTED_ALEMBIC_REVISION, revisions)

    return SourceMetadata(observed_major, revisions)


def verify_schema_source_metadata(
    connection: Any,
    *,
    carried_source_revision: str | None = None,
) -> SourceMetadata:
    """Validate a source, allowing explicit lineage for a schema-only dump.

    ``pg_dump --schema-only`` intentionally does not carry Alembic table data.
    A subsequent canonicalization therefore may receive the previously
    validated revision explicitly.  A source that does expose version rows is
    always checked against the expected revision; an observed wrong revision
    can never be overridden by the carried value.
    """

    observed_major = postgres_major(connection)
    if observed_major != EXPECTED_POSTGRES_MAJOR:
        raise PostgresMajorMismatch(EXPECTED_POSTGRES_MAJOR, observed_major)

    revisions = read_alembic_revisions(connection)
    if revisions:
        if revisions != (EXPECTED_ALEMBIC_REVISION,):
            raise AlembicRevisionMismatch(EXPECTED_ALEMBIC_REVISION, revisions)
        return SourceMetadata(observed_major, revisions)

    if carried_source_revision == EXPECTED_ALEMBIC_REVISION:
        return SourceMetadata(observed_major, (carried_source_revision,))

    raise AlembicRevisionMismatch(EXPECTED_ALEMBIC_REVISION, revisions)


def verify_target_postgres_major(
    connection: Any,
) -> int:
    """Require the disposable restore target to use the same major."""

    observed_major = postgres_major(connection)
    if observed_major != EXPECTED_POSTGRES_MAJOR:
        raise PostgresMajorMismatch(EXPECTED_POSTGRES_MAJOR, observed_major)
    return observed_major


def verify_disposable_target_identity(
    connection: Any,
    *,
    expected_database_name: str,
) -> None:
    """Ensure the explicitly supplied target name matches the live target."""

    observed_name = _text(_scalar(connection, "SELECT current_database()"))
    if observed_name != expected_database_name:
        raise DisposableTargetRequired(
            "target DSN database does not match the explicitly named disposable target"
        )


def verify_disposable_target_empty(connection: Any) -> None:
    """Reject a target that already contains user-owned database objects."""

    object_count = _scalar(
        connection,
        """
        SELECT COUNT(*)
          FROM (
                SELECT 'schema' AS object_kind, n.oid::text AS object_id
                 FROM pg_namespace AS n
                 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'public')
                   AND n.nspname NOT LIKE 'pg_toast%'
                   AND n.nspname NOT LIKE 'pg_temp_%'
                   AND n.nspname NOT LIKE 'pg_toast_temp_%'
                UNION ALL
                SELECT 'relation' AS object_kind, c.oid::text AS object_id
                  FROM pg_class AS c
                 JOIN pg_namespace AS n ON n.oid = c.relnamespace
                 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                   AND n.nspname NOT LIKE 'pg_toast%'
                   AND n.nspname NOT LIKE 'pg_temp_%'
                   AND n.nspname NOT LIKE 'pg_toast_temp_%'
                UNION ALL
                SELECT 'routine' AS object_kind, p.oid::text AS object_id
                  FROM pg_proc AS p
                 JOIN pg_namespace AS n ON n.oid = p.pronamespace
                 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                   AND n.nspname NOT LIKE 'pg_toast%'
                   AND n.nspname NOT LIKE 'pg_temp_%'
                   AND n.nspname NOT LIKE 'pg_toast_temp_%'
                UNION ALL
                SELECT 'type' AS object_kind, t.oid::text AS object_id
                  FROM pg_type AS t
                 JOIN pg_namespace AS n ON n.oid = t.typnamespace
                 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                   AND n.nspname NOT LIKE 'pg_toast%'
                   AND n.nspname NOT LIKE 'pg_temp_%'
                   AND n.nspname NOT LIKE 'pg_toast_temp_%'
                UNION ALL
                SELECT 'extension' AS object_kind, e.oid::text AS object_id
                  FROM pg_extension AS e
                 JOIN pg_namespace AS n ON n.oid = e.extnamespace
                 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                   AND n.nspname NOT LIKE 'pg_toast%'
                   AND n.nspname NOT LIKE 'pg_temp_%'
                   AND n.nspname NOT LIKE 'pg_toast_temp_%'
          ) AS user_objects
        """,
    )
    try:
        count = int(object_count)
    except (TypeError, ValueError) as exc:
        raise ContractError("target object count was not numeric") from exc
    if count:
        raise DisposableTargetRequired(
            f"disposable target is not empty: {count} user object(s) already exist"
        )


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value]
    return [_text(value)]


def _action(value: Any) -> str:
    code = _text(value).strip()
    return _ACTION_NAMES.get(code, f"UNKNOWN({code})")


def _governed_relation_names(connection: Any) -> set[str]:
    rows = _rows(
        connection,
        """
        SELECT c.relname
          FROM pg_class AS c
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public'
           AND c.relname = ANY(%s)
           AND c.relkind IN ('r', 'p')
         ORDER BY c.relname
        """,
        (list(GOVERNED_RELATIONS),),
    )
    return {_text(row[0]) for row in rows}


def collect_governed_descriptors(connection: Any) -> dict[str, Any]:
    """Collect the exact v1 descriptor surface using read-only catalog SQL.

    The returned data intentionally contains names and rendered definitions,
    never catalog object identifiers or connection material.  CHECK
    semantics are represented by PostgreSQL's restored constraint definition;
    no expression rewriting is applied here.
    """

    missing = set(GOVERNED_RELATIONS) - _governed_relation_names(connection)
    if missing:
        raise MissingGovernedRelation(tuple(missing))

    column_rows = _rows(
        connection,
        """
        SELECT n.nspname,
               c.relname,
               a.attnum,
               a.attname,
               pg_catalog.format_type(a.atttypid, a.atttypmod),
               a.attnotnull,
               COALESCE(pg_get_expr(ad.adbin, ad.adrelid), ''),
               a.attidentity,
               a.attgenerated,
               COALESCE(coll.collname, '')
          FROM pg_attribute AS a
          JOIN pg_class AS c ON c.oid = a.attrelid
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
          LEFT JOIN pg_attrdef AS ad
            ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
          LEFT JOIN pg_collation AS coll ON coll.oid = a.attcollation
         WHERE n.nspname = 'public'
           AND c.relname = ANY(%s)
           AND a.attnum > 0
           AND NOT a.attisdropped
         ORDER BY c.relname, a.attnum
        """,
        (list(GOVERNED_RELATIONS),),
    )
    columns = [
        {
            "schema": _text(row[0]),
            "relation": _text(row[1]),
            "ordinal": int(row[2]),
            "name": _text(row[3]),
            "type": _text(row[4]),
            "not_null": bool(row[5]),
            "default": _text(row[6]),
            "identity": _text(row[7]),
            "generated": _text(row[8]),
            "collation": _text(row[9]),
        }
        for row in column_rows
    ]

    constraint_rows = _rows(
        connection,
        """
        SELECT n.nspname,
               c.relname,
               con.conname,
               con.contype,
               con.condeferrable,
               con.condeferred,
               con.confdeltype,
               con.confupdtype,
               pg_get_constraintdef(con.oid, true),
               COALESCE((
                   SELECT array_agg(local_att.attname ORDER BY local_pos.ordinality)
                     FROM unnest(con.conkey) WITH ORDINALITY
                          AS local_pos(attnum, ordinality)
                     JOIN pg_attribute AS local_att
                       ON local_att.attrelid = con.conrelid
                      AND local_att.attnum = local_pos.attnum
               ), ARRAY[]::text[]),
               CASE
                   WHEN con.contype = 'f' THEN ref_n.nspname || '.' || ref_c.relname
                   ELSE ''
               END,
               COALESCE((
                   SELECT array_agg(ref_att.attname ORDER BY ref_pos.ordinality)
                     FROM unnest(con.confkey) WITH ORDINALITY
                          AS ref_pos(attnum, ordinality)
                     JOIN pg_attribute AS ref_att
                       ON ref_att.attrelid = con.confrelid
                      AND ref_att.attnum = ref_pos.attnum
               ), ARRAY[]::text[])
          FROM pg_constraint AS con
          JOIN pg_class AS c ON c.oid = con.conrelid
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
          LEFT JOIN pg_class AS ref_c ON ref_c.oid = con.confrelid
          LEFT JOIN pg_namespace AS ref_n ON ref_n.oid = ref_c.relnamespace
         WHERE n.nspname = 'public'
           AND c.relname = ANY(%s)
         ORDER BY c.relname, con.conname
        """,
        (list(GOVERNED_RELATIONS),),
    )
    constraints = [
        {
            "schema": _text(row[0]),
            "relation": _text(row[1]),
            "name": _text(row[2]),
            "type": _text(row[3]),
            "deferrable": bool(row[4]),
            "initially_deferred": bool(row[5]),
            "on_delete": _action(row[6]),
            "on_update": _action(row[7]),
            "definition": _text(row[8]),
            "local_columns": _text_list(row[9]),
            "referenced_relation": _text(row[10]),
            "referenced_columns": _text_list(row[11]),
        }
        for row in constraint_rows
    ]

    index_rows = _rows(
        connection,
        """
        SELECT n.nspname,
               tbl.relname,
               idx.relname,
               ind.indisunique,
               ind.indisprimary,
               pg_get_indexdef(ind.indexrelid),
               COALESCE(pg_get_expr(ind.indpred, ind.indrelid), '')
          FROM pg_index AS ind
          JOIN pg_class AS idx ON idx.oid = ind.indexrelid
          JOIN pg_class AS tbl ON tbl.oid = ind.indrelid
          JOIN pg_namespace AS n ON n.oid = tbl.relnamespace
         WHERE n.nspname = 'public'
           AND tbl.relname = ANY(%s)
         ORDER BY tbl.relname, idx.relname
        """,
        (list(GOVERNED_RELATIONS),),
    )
    indexes = [
        {
            "schema": _text(row[0]),
            "relation": _text(row[1]),
            "name": _text(row[2]),
            "unique": bool(row[3]),
            "primary": bool(row[4]),
            "definition": _text(row[5]),
            "predicate": _text(row[6]),
        }
        for row in index_rows
    ]

    return normalize_descriptors(
        {
            "relations": [
                {"schema": "public", "name": relation}
                for relation in GOVERNED_RELATIONS
            ],
            "columns": columns,
            "constraints": constraints,
            "indexes": indexes,
        }
    )


def _relation_order(value: Any) -> int:
    if isinstance(value, Mapping):
        name = value.get("relation", value.get("name", ""))
    else:
        name = value
    try:
        return GOVERNED_RELATIONS.index(str(name))
    except ValueError:
        return len(GOVERNED_RELATIONS)


def normalize_descriptors(descriptors: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and deterministically order v1 descriptors without rewrites."""

    if set(descriptors) != set(_DESCRIPTOR_SECTIONS):
        raise InvalidSnapshot(
            "descriptor sections must be exactly " + ", ".join(_DESCRIPTOR_SECTIONS)
        )

    relations = list(descriptors["relations"])
    columns = list(descriptors["columns"])
    constraints = list(descriptors["constraints"])
    indexes = list(descriptors["indexes"])

    for section, rows in (
        ("relations", relations),
        ("columns", columns),
        ("constraints", constraints),
        ("indexes", indexes),
    ):
        for row in rows:
            if not isinstance(row, Mapping):
                raise InvalidSnapshot(f"{section} descriptors must be objects")
            if set(row) != _DESCRIPTOR_KEYS[section]:
                raise InvalidSnapshot(f"{section} descriptor fields are not v1 exact")

    if relations != [
        {"schema": "public", "name": relation} for relation in GOVERNED_RELATIONS
    ]:
        raise InvalidSnapshot("descriptor relation identity does not match governed v1")

    columns.sort(key=lambda row: (_relation_order(row), int(row["ordinal"])))
    constraints.sort(key=lambda row: (_relation_order(row), str(row["name"])))
    indexes.sort(key=lambda row: (_relation_order(row), str(row["name"])))

    return {
        "relations": copy.deepcopy(relations),
        "columns": copy.deepcopy(columns),
        "constraints": copy.deepcopy(constraints),
        "indexes": copy.deepcopy(indexes),
    }


def serialize_envelope(envelope: Mapping[str, Any]) -> bytes:
    """Serialize exactly as UTF-8 JSON with sorted keys, separators, newline."""

    encoded = (
        json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    return encoded


def build_snapshot(
    descriptors: Mapping[str, Any],
    *,
    postgres_major_value: int,
    source_revision: str,
) -> GovernedSchemaSnapshot:
    if postgres_major_value != EXPECTED_POSTGRES_MAJOR:
        raise PostgresMajorMismatch(EXPECTED_POSTGRES_MAJOR, postgres_major_value)
    if source_revision != EXPECTED_ALEMBIC_REVISION:
        raise AlembicRevisionMismatch(EXPECTED_ALEMBIC_REVISION, (source_revision,))
    normalized = normalize_descriptors(descriptors)
    envelope = {
        "contract_version": CONTRACT_VERSION,
        "postgres_major": int(postgres_major_value),
        "source_revision": source_revision,
        "descriptors": normalized,
    }
    digest = hashlib.sha256(serialize_envelope(envelope)).hexdigest()
    return GovernedSchemaSnapshot(
        CONTRACT_VERSION,
        int(postgres_major_value),
        source_revision,
        normalized,
        digest,
    )


def snapshot_from_dict(value: Mapping[str, Any]) -> GovernedSchemaSnapshot:
    if not isinstance(value, Mapping):
        raise InvalidSnapshot("snapshot root must be an object")
    try:
        digest = value["digest"]
        contract_version = value["contract_version"]
        postgres_major_value = value["postgres_major"]
        source_revision = value["source_revision"]
        descriptors = value["descriptors"]
        if not isinstance(digest, str):
            raise InvalidSnapshot("snapshot digest must be a string")
        if not isinstance(contract_version, str):
            raise InvalidSnapshot("snapshot contract version must be a string")
        if type(postgres_major_value) is not int:
            raise InvalidSnapshot("snapshot PostgreSQL major must be an integer")
        if not isinstance(source_revision, str):
            raise InvalidSnapshot("snapshot source revision must be a string")
        if not isinstance(descriptors, Mapping):
            raise InvalidSnapshot("snapshot descriptors must be an object")
        snapshot = build_snapshot(
            descriptors,
            postgres_major_value=postgres_major_value,
            source_revision=source_revision,
        )
        if contract_version != CONTRACT_VERSION:
            raise InvalidSnapshot("unsupported governed-schema contract version")
        if snapshot.digest != digest:
            raise InvalidSnapshot("snapshot digest does not match serialized envelope")
        return snapshot
    except KeyError as exc:
        raise InvalidSnapshot(f"snapshot missing field: {exc.args[0]}") from exc
    except (OverflowError, TypeError, ValueError) as exc:
        raise InvalidSnapshot("snapshot contains malformed field types") from exc


def snapshot_connection(
    connection: Any,
    *,
    source_revision: str,
) -> GovernedSchemaSnapshot:
    observed_major = verify_target_postgres_major(connection)
    return build_snapshot(
        collect_governed_descriptors(connection),
        postgres_major_value=observed_major,
        source_revision=source_revision,
    )


def descriptor_diff(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    max_items: int = 24,
    max_chars: int = 6000,
) -> tuple[str, ...]:
    """Return a bounded, human-readable section/item diff."""

    differences: list[str] = []
    for section in _DESCRIPTOR_SECTIONS:
        left_items = list(left.get(section, []))
        right_items = list(right.get(section, []))
        width = max(len(left_items), len(right_items))
        for index in range(width):
            left_item = left_items[index] if index < len(left_items) else "<missing>"
            right_item = right_items[index] if index < len(right_items) else "<missing>"
            if left_item != right_item:
                differences.append(
                    f"{section}[{index}]: left={_compact(left_item)}; "
                    f"right={_compact(right_item)}"
                )
                if len(differences) >= max_items:
                    return _bound_diff(differences, max_chars)
    return _bound_diff(differences, max_chars)


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _bound_diff(values: Iterable[str], max_chars: int) -> tuple[str, ...]:
    result: list[str] = []
    used = 0
    for value in values:
        if used + len(value) + 1 > max_chars:
            result.append("... descriptor diff truncated ...")
            break
        result.append(value)
        used += len(value) + 1
    return tuple(result)


def compare_snapshots(
    left: GovernedSchemaSnapshot,
    right: GovernedSchemaSnapshot,
) -> ComparisonResult:
    reasons: list[str] = []
    if left.contract_version != right.contract_version:
        reasons.append("contract version mismatch")
    if left.postgres_major != right.postgres_major:
        reasons.append("PostgreSQL major mismatch")
    if left.source_revision != right.source_revision:
        reasons.append("source Alembic revision mismatch")
    if left.digest != right.digest:
        reasons.append("governed digest mismatch")

    left_descriptors = normalize_descriptors(left.descriptors)
    right_descriptors = normalize_descriptors(right.descriptors)
    differences = descriptor_diff(left_descriptors, right_descriptors)
    if differences:
        reasons.append("governed descriptors differ")

    return ComparisonResult(not reasons, tuple(reasons), differences)


def _import_psycopg() -> Any:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ContractError(
            "psycopg is required for PostgreSQL canonicalization"
        ) from exc
    return psycopg


def _validate_disposable_name(name: str) -> None:
    if not name.startswith("codexify_gse_") or not name[len("codexify_gse_") :]:
        raise DisposableTargetRequired(
            "canonicalization requires an explicitly named codexify_gse_ disposable target"
        )
    if not all(char.isalnum() or char == "_" for char in name):
        raise DisposableTargetRequired(
            "disposable target name contains invalid characters"
        )


def _set_source_snapshot_transaction(connection: Any) -> None:
    """Start the exported source snapshot's repeatable-read read-only scope."""

    with connection.cursor() as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")


def _export_source_snapshot(connection: Any) -> str:
    """Export the transaction snapshot used by the separate ``pg_dump`` client."""

    snapshot_id = _text(_scalar(connection, "SELECT pg_export_snapshot()"))
    if not snapshot_id:
        raise ContractError("source PostgreSQL snapshot identifier was empty")
    return snapshot_id


def canonicalize_database(
    source_dsn: str,
    target_dsn: str,
    *,
    target_disposable_name: str,
    carried_source_revision: str | None = None,
    pg_dump_bin: str = "pg_dump",
    psql_bin: str = "psql",
    connect_factory: Callable[[str], Any] | None = None,
    run_command: Callable[..., Any] = subprocess.run,
) -> GovernedSchemaSnapshot:
    """Canonicalize one source into an explicitly disposable target.

    The source connection is used only for catalog reads.  Exactly one
    controlled schema dump and one clean restore are executed; no migration,
    stamp, or manual DDL operation is performed by this function.
    """

    _validate_disposable_name(target_disposable_name)
    psycopg = _import_psycopg() if connect_factory is None else None
    connect = connect_factory or psycopg.connect

    with connect(source_dsn) as source_connection:
        with source_connection.transaction():
            _set_source_snapshot_transaction(source_connection)
            source_snapshot = _export_source_snapshot(source_connection)
            source_metadata = verify_schema_source_metadata(
                source_connection,
                carried_source_revision=carried_source_revision,
            )

            with connect(target_dsn) as target_connection:
                verify_target_postgres_major(target_connection)
                verify_disposable_target_identity(
                    target_connection,
                    expected_database_name=target_disposable_name,
                )
                verify_disposable_target_empty(target_connection)

            dump_command = [
                pg_dump_bin,
                "--schema-only",
                "--no-owner",
                "--no-privileges",
                f"--snapshot={source_snapshot}",
                f"--dbname={source_dsn}",
            ]
            dumped = run_command(
                dump_command,
                check=False,
                capture_output=True,
            )
            if dumped.returncode != 0:
                raise CommandExecutionFailure("pg_dump", int(dumped.returncode))

            restore_command = [
                psql_bin,
                "--no-psqlrc",
                "--set=ON_ERROR_STOP=1",
                "--single-transaction",
                f"--dbname={target_dsn}",
            ]
            restored = run_command(
                restore_command,
                input=dumped.stdout,
                check=False,
                capture_output=True,
            )
            if restored.returncode != 0:
                raise CommandExecutionFailure("psql restore", int(restored.returncode))

    with connect(target_dsn) as target_connection:
        return snapshot_connection(
            target_connection,
            source_revision=source_metadata.alembic_revision,
        )


def _write_snapshot(path: Path, snapshot: GovernedSchemaSnapshot) -> None:
    path.write_bytes(serialize_envelope(snapshot.as_dict()))


def _read_snapshot(path: Path) -> GovernedSchemaSnapshot:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidSnapshot(f"unable to read snapshot: {path.name}") from exc
    if not isinstance(value, Mapping):
        raise InvalidSnapshot("snapshot root must be an object")
    return snapshot_from_dict(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="read source metadata")
    inspect.add_argument("--dsn", required=True)

    snapshot = commands.add_parser(
        "snapshot", help="collect an already canonicalized target"
    )
    snapshot.add_argument("--dsn", required=True)
    snapshot.add_argument("--source-revision", required=True)
    snapshot.add_argument("--output", type=Path, required=True)

    canonicalize = commands.add_parser(
        "canonicalize", help="dump and restore to a disposable target"
    )
    canonicalize.add_argument("--source-dsn", required=True)
    canonicalize.add_argument("--target-dsn", required=True)
    canonicalize.add_argument("--target-disposable-name", required=True)
    canonicalize.add_argument("--carried-source-revision")
    canonicalize.add_argument("--output", type=Path, required=True)

    compare = commands.add_parser("compare", help="compare two snapshot envelopes")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            psycopg = _import_psycopg()
            with psycopg.connect(args.dsn) as connection:
                metadata = verify_source_metadata(connection)
            print(
                json.dumps(
                    {
                        "postgres_major": metadata.postgres_major,
                        "alembic_revision": metadata.alembic_revision,
                    },
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "snapshot":
            psycopg = _import_psycopg()
            with psycopg.connect(args.dsn) as connection:
                snapshot = snapshot_connection(
                    connection,
                    source_revision=args.source_revision,
                )
            _write_snapshot(args.output, snapshot)
            print(json.dumps({"digest": snapshot.digest}, sort_keys=True))
            return 0

        if args.command == "canonicalize":
            snapshot = canonicalize_database(
                args.source_dsn,
                args.target_dsn,
                target_disposable_name=args.target_disposable_name,
                carried_source_revision=args.carried_source_revision,
            )
            _write_snapshot(args.output, snapshot)
            print(json.dumps({"digest": snapshot.digest}, sort_keys=True))
            return 0

        left = _read_snapshot(args.left)
        right = _read_snapshot(args.right)
        result = compare_snapshots(left, right)
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0 if result.equivalent else 1
    except ContractError as exc:
        print(json.dumps({"error": exc.code, "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised through the CLI
    raise SystemExit(main())
