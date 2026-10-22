"""Contract test for the restored UMS revision and purge ORM mappings.

The feature branch carried the *schema* for the ordinary-memory revision and
purge families -- four committed Alembic revisions create ``memory_revisions``,
``memory_review_revisions``, ``memory_lifecycle_revisions``, and
``memory_purge_tombstones`` -- but ``guardian/db/models.py`` defined none of
the matching SQLAlchemy models. Because ``guardian/guardian_api.py`` imports
``guardian.routes.memory_vault`` at module level, and that route pulls in
``guardian.services.memory_vault_mutation`` and
``guardian.services.memory_purge``, the missing names broke
``import codexify.guardian_api`` before any delegated execution could begin.

That failure is recorded as Blocker 2 in
``docs/architecture/proofs/runtime/2026-10-22-guardian-delegation-source-exact-live-proof.md``.

This test proves the restoration is a *parity* restoration, not a new
capability. It is deliberately not a string-presence check: it parses the
accepted Alembic revisions and compares the live ORM metadata against them
column by column, constraint by constraint, and index by index. If the ORM
and the migrations ever diverge, this test fails.

It also proves the restoration introduced no duplicate table registration and
that the memory services which depend on these mappings import cleanly.

No database is required: every assertion here is metadata-level. Real
PostgreSQL behaviour (constraint enforcement, cascade, parity against a
migrated schema) is proven by the four existing migration-parity suites, which
remain the authority for runtime semantics.
"""

from __future__ import annotations

import ast
from pathlib import Path

import sqlalchemy as sa

REPO_ROOT = Path(__file__).resolve().parents[2]

MIGRATION_DIR_CANDIDATES = (
    REPO_ROOT / "guardian" / "db" / "migrations" / "versions",
    REPO_ROOT / "backend" / "migrations" / "versions",
)

#: Accepted revisions that own the four restored relations, by Alembic id.
RESTORED_REVISIONS = {
    "c3d9f4e6a1b2": "memory_revisions",
    "a7c3e91d4b60": "memory_review_revisions",
    "b8e2f4a6c901": "memory_lifecycle_revisions",
    "c7f4a9b2e6d1": "memory_purge_tombstones",
}

#: ORM class -> canonical table it must own.
RESTORED_MODELS = {
    "MemoryRevision": "memory_revisions",
    "MemoryReviewRevision": "memory_review_revisions",
    "MemoryLifecycleRevision": "memory_lifecycle_revisions",
    "MemoryPurgeTombstone": "memory_purge_tombstones",
}


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _model(name: str):
    """Return the ORM class, failing loudly if the mapping is absent.

    Importing inside the test body (rather than at module scope) keeps the
    red baseline a clean assertion failure that names the missing mapping,
    instead of an opaque collection error.
    """
    from guardian.db import models

    assert hasattr(models, name), (
        f"guardian.db.models does not define {name!r}. The accepted UMS ORM "
        "mappings are missing from this branch, so the backend import chain "
        "cannot resolve them."
    )
    return getattr(models, name)


def _migration_dir() -> Path:
    for candidate in MIGRATION_DIR_CANDIDATES:
        if candidate.is_dir():
            return candidate
    raise AssertionError(
        "no migrations/versions directory found at any of: "
        + ", ".join(str(c) for c in MIGRATION_DIR_CANDIDATES)
    )


def _migration_path(revision: str) -> Path:
    matches = sorted(_migration_dir().glob(f"*{revision}*.py"))
    assert matches, f"no migration file found for revision {revision!r}"
    assert len(matches) == 1, (
        f"revision {revision!r} matched multiple migration files: {matches}"
    )
    return matches[0]


def _literal(node: ast.AST) -> str | None:
    """Best-effort literal rendering of a constant AST node."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def _ast_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr
        if isinstance(func, ast.Name):
            return func.id
    return None


def _ast_type_repr(node: ast.AST) -> str:
    """Normalize a migration type expression to the ORM's rendering form."""
    name = _ast_call_name(node)
    if name is None:
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Name):
            return node.id
        return ast.dump(node)
    args = [repr(_literal(a)) for a in node.args]
    kwargs = [f"{kw.arg}={_literal(kw.value)!r}" for kw in node.keywords]
    return f"{name}({', '.join(args + kwargs)})"


def _ast_text_repr(node: ast.AST) -> str:
    """Normalize a `sa.text(...)` literal to its SQL string."""
    if isinstance(node, ast.Call) and _ast_call_name(node) == "text":
        if node.args:
            literal = _literal(node.args[0])
            if isinstance(literal, str):
                return literal
    return ast.dump(node)


def _parse_migration(revision: str) -> dict:
    """Extract the accepted table definition from an Alembic revision file."""
    path = _migration_path(revision)
    tree = ast.parse(path.read_text())

    upgrade = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
        ),
        None,
    )
    assert upgrade is not None, f"{path.name} has no upgrade() function"

    definition: dict = {
        "columns": {},
        "pk": set(),
        "unique": set(),
        "check": set(),
        "fk": {},
        "indexes": {},
        "source": path.name,
    }

    for node in ast.walk(upgrade):
        if not isinstance(node, ast.Call):
            continue
        call_name = _ast_call_name(node)

        if call_name == "create_table" and node.args:
            table_name = _literal(node.args[0])
            assert table_name is not None, "create_table table name is not a literal"
            for arg in node.args[1:]:
                kind = _ast_call_name(arg)
                if kind == "Column":
                    column_name = _literal(arg.args[0])
                    assert column_name is not None, "column name is not a literal"
                    type_node = arg.args[1]
                    nullable = True
                    server_default = None
                    for kw in arg.keywords:
                        if kw.arg == "nullable":
                            nullable = bool(_literal(kw.value))
                        elif kw.arg == "server_default":
                            server_default = _ast_text_repr(kw.value)
                    definition["columns"][column_name] = {
                        "type": _ast_type_repr(type_node),
                        "nullable": nullable,
                        "server_default": server_default,
                    }
                elif kind == "PrimaryKeyConstraint":
                    definition["pk"].add(_kwarg(arg, "name"))
                elif kind == "UniqueConstraint":
                    definition["unique"].add(_kwarg(arg, "name"))
                elif kind == "CheckConstraint":
                    definition["check"].add(_kwarg(arg, "name"))
                elif kind == "ForeignKeyConstraint":
                    definition["fk"][_kwarg(arg, "name")] = {
                        "local": _ast_str_list(arg.args[0] if arg.args else None),
                        "remote": _ast_str_list(arg.args[1] if len(arg.args) > 1 else None),
                        "ondelete": _kwarg(arg, "ondelete"),
                    }

        elif call_name == "create_index" and len(node.args) >= 3:
            index_name = _literal(node.args[0])
            table_name = _literal(node.args[1])
            columns = _ast_str_list(node.args[2])
            unique = False
            where = None
            for kw in node.keywords:
                if kw.arg == "unique":
                    unique = bool(_literal(kw.value))
                elif kw.arg == "postgresql_where":
                    where = _ast_text_repr(kw.value)
            definition["indexes"][index_name] = {
                "table": table_name,
                "columns": columns,
                "unique": unique,
                "where": where,
            }

    return definition


def _kwarg(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return _literal(kw.value)
    return None


def _ast_str_list(node: ast.AST | None) -> list[str]:
    if isinstance(node, ast.List):
        return [str(_literal(element)) for element in node.elts]
    return []


def _orm_type_repr(col_type) -> str:
    """Normalize an ORM column type to the migration's rendering form."""
    if isinstance(col_type, sa.Text):
        return "Text()"
    if isinstance(col_type, sa.Boolean):
        return "Boolean()"
    if isinstance(col_type, sa.BigInteger):
        return "BigInteger()"
    if isinstance(col_type, sa.Integer):
        return "Integer()"
    if isinstance(col_type, sa.TIMESTAMP):
        return f"TIMESTAMP(timezone={col_type.timezone})"
    if isinstance(col_type, sa.String):
        length = col_type.length
        return f"String({length})" if length is not None else "String()"
    return type(col_type).__name__


def _orm_server_default(col) -> str | None:
    if col.server_default is None:
        return None
    arg = getattr(col.server_default, "arg", None)
    if arg is None:
        return str(col.server_default)
    return str(arg)


def _named(constraints, kind) -> set[str]:
    return {
        c.name
        for c in constraints
        if isinstance(c, kind) and c.name is not None
    }


# ---------------------------------------------------------------------------
# Presence and registration.
# ---------------------------------------------------------------------------


def test_all_four_ums_orm_mappings_are_importable() -> None:
    """The four mappings named in the accepted contract must exist."""
    for name in RESTORED_MODELS:
        model = _model(name)
        assert model.__tablename__ == RESTORED_MODELS[name]


def test_each_mapping_registers_its_canonical_table_exactly_once() -> None:
    """No duplicate table registration may be introduced."""
    from guardian.db.models import Base

    by_table: dict[str, list[str]] = {}
    for mapper in Base.registry.mappers:
        by_table.setdefault(mapper.local_table.name, []).append(mapper.class_.__name__)

    for name, table_name in RESTORED_MODELS.items():
        owners = by_table.get(table_name, [])
        assert owners == [name], (
            f"table {table_name!r} is mapped by {owners!r}; expected exactly "
            f"[{name!r}]"
        )

    # Repo-wide: no table may be claimed by two ORM classes.
    duplicated = {
        table: owners for table, owners in by_table.items() if len(owners) > 1
    }
    assert not duplicated, f"duplicate table registrations: {duplicated}"


def test_restored_families_remain_distinct_relations() -> None:
    """The three revision families and the tombstone stay separate relations."""
    tables = {name: _model(name).__table__ for name in RESTORED_MODELS}
    assert len({id(table) for table in tables.values()}) == 4
    assert len({table.name for table in tables.values()}) == 4


# ---------------------------------------------------------------------------
# ORM / accepted-migration parity.
# ---------------------------------------------------------------------------


def test_orm_metadata_matches_accepted_migrations() -> None:
    """Every restored table must match its accepted Alembic revision exactly."""
    for revision, table_name in RESTORED_REVISIONS.items():
        accepted = _parse_migration(revision)
        model_name = next(
            name for name, expected in RESTORED_MODELS.items() if expected == table_name
        )
        table = _model(model_name).__table__

        # Columns: name, type, nullability, default.
        orm_columns = {c.name: c for c in table.columns}
        assert set(orm_columns) == set(accepted["columns"]), (
            f"{table_name}: ORM columns {sorted(orm_columns)} != "
            f"migration columns {sorted(accepted['columns'])}"
        )
        for column_name, column in orm_columns.items():
            expected = accepted["columns"][column_name]
            assert _orm_type_repr(column.type) == expected["type"], (
                f"{table_name}.{column_name}: ORM type "
                f"{_orm_type_repr(column.type)!r} != migration {expected['type']!r}"
            )
            assert column.nullable is expected["nullable"], (
                f"{table_name}.{column_name}: ORM nullable={column.nullable} != "
                f"migration nullable={expected['nullable']}"
            )
            assert _orm_server_default(column) == expected["server_default"], (
                f"{table_name}.{column_name}: ORM server_default "
                f"{_orm_server_default(column)!r} != migration "
                f"{expected['server_default']!r}"
            )

        # Constraints.
        assert _named(table.constraints, sa.PrimaryKeyConstraint) == accepted["pk"]
        assert _named(table.constraints, sa.UniqueConstraint) == accepted["unique"]
        assert _named(table.constraints, sa.CheckConstraint) == accepted["check"]

        primary_keys = [
            c for c in table.constraints if isinstance(c, sa.PrimaryKeyConstraint)
        ]
        assert len(primary_keys) == 1, (
            f"{table_name}: expected exactly one PrimaryKeyConstraint, got "
            f"{len(primary_keys)}"
        )
        assert table.primary_key is primary_keys[0]

        # Foreign keys, including cascade behaviour and the referenced columns.
        orm_fks = {
            c.name: c
            for c in table.constraints
            if isinstance(c, sa.ForeignKeyConstraint) and c.name is not None
        }
        assert set(orm_fks) == set(accepted["fk"]), (
            f"{table_name}: ORM foreign keys {sorted(orm_fks)} != "
            f"migration foreign keys {sorted(accepted['fk'])}"
        )
        for fk_name, expected in accepted["fk"].items():
            constraint = orm_fks[fk_name]
            local = sorted(element.parent.name for element in constraint.elements)
            remote = sorted(element.target_fullname for element in constraint.elements)
            assert local == sorted(expected["local"]), (
                f"{table_name}.{fk_name}: local columns {local} != "
                f"{sorted(expected['local'])}"
            )
            assert remote == sorted(expected["remote"]), (
                f"{table_name}.{fk_name}: remote columns {remote} != "
                f"{sorted(expected['remote'])}"
            )
            assert constraint.ondelete == expected["ondelete"], (
                f"{table_name}.{fk_name}: ondelete {constraint.ondelete!r} != "
                f"{expected['ondelete']!r}"
            )

        # Indexes, including the partial unique suppression index.
        orm_indexes = {i.name: i for i in table.indexes}
        assert set(orm_indexes) == set(accepted["indexes"]), (
            f"{table_name}: ORM indexes {sorted(orm_indexes)} != "
            f"migration indexes {sorted(accepted['indexes'])}"
        )
        for index_name, expected in accepted["indexes"].items():
            index = orm_indexes[index_name]
            assert [c.name for c in index.columns] == expected["columns"], (
                f"{table_name}.{index_name}: columns "
                f"{[c.name for c in index.columns]} != {expected['columns']}"
            )
            assert bool(index.unique) is expected["unique"], (
                f"{table_name}.{index_name}: unique={index.unique} != "
                f"{expected['unique']}"
            )
            where = index.dialect_options["postgresql"].get("where")
            where_text = str(where) if where is not None else None
            assert where_text == expected["where"], (
                f"{table_name}.{index_name}: partial predicate {where_text!r} != "
                f"{expected['where']!r}"
            )


# ---------------------------------------------------------------------------
# Contract-specific invariants.
# ---------------------------------------------------------------------------


def test_revision_families_keep_independent_ordering() -> None:
    """Each revision family numbers its own sequence, per the contract."""
    unique_names = {
        "MemoryRevision": "uq_memory_revisions_memory_number",
        "MemoryReviewRevision": "uq_memory_review_revisions_memory_number",
        "MemoryLifecycleRevision": "uq_memory_lifecycle_revisions_memory_number",
    }
    seen: set[str] = set()
    for model_name, constraint_name in unique_names.items():
        table = _model(model_name).__table__
        names = _named(table.constraints, sa.UniqueConstraint)
        assert constraint_name in names, (
            f"{model_name}: expected unique constraint {constraint_name!r} in {names}"
        )
        assert names == {constraint_name}, (
            f"{model_name}: revision families must not share ordering "
            f"constraints; found {names}"
        )
        assert constraint_name not in seen
        seen.add(constraint_name)


def test_tombstone_suppression_cannot_be_relaxed() -> None:
    """`suppress_reimport` is pinned true by a CHECK constraint."""
    table = _model("MemoryPurgeTombstone").__table__
    checks = {
        c.name: c
        for c in table.constraints
        if isinstance(c, sa.CheckConstraint) and c.name is not None
    }
    assert "memory_purge_tombstones_suppress_reimport_check" in checks

    column = table.columns["suppress_reimport"]
    assert column.nullable is False
    assert _orm_server_default(column) == "true"


def test_tombstone_stores_no_canonical_memory_identity() -> None:
    """The tombstone is non-content: no canonical memory_id column."""
    table = _model("MemoryPurgeTombstone").__table__
    assert "memory_id" not in table.columns
    assert "purged_record_fingerprint" in table.columns
    assert "source_atom_fingerprint" in table.columns

    # No foreign key may reach memory_records: the parent row is erased.
    for constraint in table.constraints:
        if isinstance(constraint, sa.ForeignKeyConstraint):
            targets = [
                element.target_fullname for element in constraint.elements
            ]
            assert not any(
                target.startswith("memory_records.") for target in targets
            ), f"purge tombstone must not reference memory_records: {targets}"


def test_dependent_memory_services_import_cleanly() -> None:
    """The services that consume these mappings must import."""
    import guardian.services.account_restore  # noqa: F401
    import guardian.services.memory_purge  # noqa: F401
    import guardian.services.memory_vault_creation  # noqa: F401
    import guardian.services.memory_vault_mutation  # noqa: F401
    import guardian.services.memory_vault_read  # noqa: F401


def test_memory_vault_route_imports_cleanly() -> None:
    """The backend import chain that previously broke must now resolve."""
    from guardian.routes import memory_vault  # noqa: F401

    assert hasattr(memory_vault, "router")
