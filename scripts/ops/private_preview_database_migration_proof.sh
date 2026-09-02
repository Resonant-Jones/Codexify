#!/usr/bin/env bash
set -euo pipefail

# Live, bounded proof for advancing the preserved private-preview PostgreSQL
# database through the repository's canonical Alembic migrator.  Dumps,
# manifests, and logs are intentionally kept outside Git.

SCRIPT_VERSION="1"
PROJECT_NAME="codexify_private_preview"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ENV_FILE="${PRIVATE_PREVIEW_ENV_FILE:-${REPO_ROOT}/.env.private-preview}"
BACKUP_ROOT_INPUT="${CODEXIFY_PRIVATE_PREVIEW_MIGRATION_BACKUP_DIR:-}"
MEDIA_ROOT="${REPO_ROOT}/data/media"
IMPORT_ROOT="${REPO_ROOT}/data/imports"
SOURCE_VOLUME="${PROJECT_NAME}_pg_data"
SOURCE_REVISION="6e2b9c4a7d1f"
TARGET_REVISION="f41493d13761"
RESTORE_IMAGE="postgres:15"
RESTORE_DB_NAME="codexify_restore"
RESTORE_DB_USER="codexify_restore"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
[[ -n "${PYTHON_BIN}" && -x "${PYTHON_BIN}" ]] || {
  printf 'ERROR: python3 is required\n' >&2
  exit 1
}

COMPOSE=(
  docker compose
  --project-directory "${REPO_ROOT}"
  -p "${PROJECT_NAME}"
  --env-file "${ENV_FILE}"
  -f "${REPO_ROOT}/docker-compose.yml"
  -f "${REPO_ROOT}/docker-compose.private-preview.yml"
)

ALL_PREVIEW_SERVICES=(
  db
  backend
  worker-chat
  worker-watchdog-review
  worker-coding
  worker-voice
  worker-chat-embed
  worker-document-embed
  worker-warmup
  worker-account-import
  frontend
  private-preview-origin
  redis
  neo4j
  graph-init
  tts
)

CHECKPOINT_DIR=""
CHECKPOINT_ID=""
BACKUP_ROOT=""
SOURCE_DB_CONTAINER=""
SOURCE_DB_CONTAINER_EXISTED_BEFORE=0
SOURCE_FROZEN=0
SOURCE_MIGRATION_STARTED=0
SOURCE_RUNTIME_RESTORED=0
CHECKPOINT_HAS_BACKUP=0
DISPOSABLE_CONTAINER=""
DISPOSABLE_VOLUME=""
SOURCE_MIGRATOR_CONTAINER=""
SOURCE_NOOP_MIGRATOR_CONTAINER=""
DISPOSABLE_MIGRATOR_CONTAINER=""
BASELINE_STATUS_FILE=""
DISPOSABLE_MIGRATION_REHEARSAL=0
DISPOSABLE_CONTAINER_REMOVED=0
DISPOSABLE_VOLUME_REMOVED=0
PROOF_SUCCEEDED=0

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

sha256_file() {
  local file_path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${file_path}" | awk '{print $1}'
  else
    shasum -a 256 "${file_path}" | awk '{print $1}'
  fi
}

file_size_bytes() {
  local file_path="$1"
  if stat -f '%z' "${file_path}" >/dev/null 2>&1; then
    stat -f '%z' "${file_path}"
  else
    stat -c '%s' "${file_path}"
  fi
}

compose() {
  "${COMPOSE[@]}" "$@"
}

container_query() {
  local container_name="$1"
  local sql="$2"
  printf '%s\n' "${sql}" | docker exec -i "${container_name}" sh -lc \
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtX'
}

container_query_stdin() {
  local container_name="$1"
  docker exec -i "${container_name}" sh -lc \
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtX'
}

wait_for_postgres() {
  local container_name="$1"
  local waited=0
  while ! docker exec "${container_name}" sh -lc \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1'; do
    if (( waited >= 120 )); then
      fail "Postgres did not become ready within 120 seconds"
      return 1
    fi
    sleep 2
    waited=$((waited + 2))
  done
}

validate_migration_graph() {
  "${PYTHON_BIN}" - "${REPO_ROOT}" "${SOURCE_REVISION}" "${TARGET_REVISION}" <<'PY'
import ast
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
source = sys.argv[2]
target = sys.argv[3]
versions_dir = root / "guardian" / "db" / "migrations" / "versions"

def assignment(tree, name):
    for node in tree.body:
        candidate = node.value if isinstance(node, ast.AnnAssign) else node
        if isinstance(candidate, ast.Assign):
            targets = candidate.targets
            value = candidate.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if any(isinstance(item, ast.Name) and item.id == name for item in targets):
            return ast.literal_eval(value)
    return None

def parents(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (tuple, list)):
        return [item for item in value if isinstance(item, str)]
    raise ValueError(f"unsupported down_revision value: {value!r}")

nodes = {}
sources = {}
parse_errors = []
for path in sorted(versions_dir.glob("*.py")):
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        revision = assignment(tree, "revision")
        if not isinstance(revision, str):
            continue
        if revision in nodes:
            raise SystemExit(f"duplicate revision id: {revision}")
        nodes[revision] = parents(assignment(tree, "down_revision"))
        sources[revision] = text
    except SystemExit:
        raise
    except Exception as exc:
        parse_errors.append(f"{path.name}: {exc}")

if parse_errors:
    raise SystemExit("migration parse errors: " + "; ".join(parse_errors))
if source not in nodes:
    raise SystemExit(f"source revision is absent: {source}")
if target not in nodes:
    raise SystemExit(f"target revision is absent: {target}")

missing = sorted({parent for values in nodes.values() for parent in values if parent not in nodes})
if missing:
    raise SystemExit("migration graph has missing parents: " + ",".join(missing))

expected_paths = [
    (source, "8f3c1a7d2e6b", "9d4c2a7e1b6f", "1c0a2b3c4d5e", "d2e3f4a5b6c7", "9c66e490a42b", target),
    (source, "8f3c1a7d2e6b", "9d4c2a7e1b6f", "1c0a2b3c4d5e", "2a6b7c8d9e0f", "3b7c8d9e0f1a", "4c7d8e9f0a1b", "5d8e9f0a1b2c", "6e9f0a1b2c3", "9c66e490a42b", target),
]
for path in expected_paths:
    for child, parent in zip(path[1:], path[:-1]):
        if parent not in nodes[child]:
            raise SystemExit(f"unexpected migration edge: {parent} -> {child}")

required = {revision for path in expected_paths for revision in path}
if required - set(nodes):
    raise SystemExit("required migration nodes are absent")
for revision in sorted(required):
    if re.search(r"\bdepends_on\s*:\s*[^=]+\b(?!None)", sources[revision]):
        # The exact assignment is checked below; this guard only keeps the
        # failure message bounded if a migration starts using dependencies.
        value = assignment(ast.parse(sources[revision]), "depends_on")
        if value is not None:
            raise SystemExit(f"unsupported depends_on in required path: {revision}")
    if re.search(r"\balembic_version\b|\b(?:alembic\.command\.)?stamp\s*\(", sources[revision], re.IGNORECASE):
        raise SystemExit(f"manual migration-ledger operation in required path: {revision}")

heads = sorted(revision for revision in nodes if not any(revision in values for values in nodes.values()))
if target not in heads:
    raise SystemExit(f"target revision is not a repository head: {target}")

print("migration_graph=PASS")
print("migration_graph_nodes=" + str(len(nodes)))
print("migration_graph_heads=" + ",".join(heads))
print("migration_path_1=" + "->".join(expected_paths[0]))
print("migration_path_2=" + "->".join(expected_paths[1]))
print("migration_path_merge=8f3c1a7d2e6b")
PY
}

validate_static_inputs() {
  local env_mode
  [[ -n "${BACKUP_ROOT_INPUT}" ]] || fail "CODEXIFY_PRIVATE_PREVIEW_MIGRATION_BACKUP_DIR is required"
  [[ "${BACKUP_ROOT_INPUT}" = /* ]] || fail "Migration backup directory must be absolute"
  [[ -f "${ENV_FILE}" ]] || fail "Private-preview env file is missing"
  [[ -d "${MEDIA_ROOT}" ]] || fail "Durable media root is missing"
  [[ -d "${IMPORT_ROOT}" ]] || fail "Private import staging root is missing"
  [[ -f "${REPO_ROOT}/docker-compose.yml" ]] || fail "Base Compose file is missing"
  [[ -f "${REPO_ROOT}/docker-compose.private-preview.yml" ]] || fail "Private preview Compose overlay is missing"
  env_mode="$(${PYTHON_BIN} - "${ENV_FILE}" <<'PY'
import stat
import sys
from pathlib import Path
print(oct(stat.S_IMODE(Path(sys.argv[1]).stat().st_mode)))
PY
)"
  [[ "${env_mode}" = "0o600" ]] || \
    fail "Private-preview env file must be owner-readable only"
  "${PYTHON_BIN}" - "${REPO_ROOT}" "${BACKUP_ROOT_INPUT}" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve(strict=True)
requested = Path(sys.argv[2]).expanduser().resolve(strict=False)
if requested == repo or repo in requested.parents:
    raise SystemExit("migration backup directory resolves inside the repository")
if requested in {Path("/"), Path("/Volumes"), Path("/Volumes/Dev_SSD")}:
    raise SystemExit("migration backup directory resolves to an unsafe broad root")
overlay = (repo / "docker-compose.private-preview.yml").read_text(encoding="utf-8")
required = '127.0.0.1:${CODEXIFY_PREVIEW_PORT:-8081}:8080'
if required not in overlay:
    raise SystemExit("private-preview overlay is not loopback-only")
PY
}

validate_backup_destination() {
  BACKUP_ROOT="$(${PYTHON_BIN} - "${BACKUP_ROOT_INPUT}" <<'PY'
import sys
from pathlib import Path
print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
)"
  case "${BACKUP_ROOT}/" in
    "${REPO_ROOT}/"*) fail "Migration backup directory resolves inside the repository" ;;
  esac
  case "${BACKUP_ROOT}" in
    /|/Volumes|/Volumes/Dev_SSD) fail "Migration backup directory resolves to an unsafe broad root" ;;
  esac
  mkdir -p -- "${BACKUP_ROOT}"
  chmod 700 "${BACKUP_ROOT}"
  [[ -w "${BACKUP_ROOT}" ]] || fail "Migration backup directory is not writable"
}

capture_table_counts() {
  local container_name="$1"
  local output_file="$2"
  local generated_sql
  generated_sql="$(container_query "${container_name}" "
    SELECT format(
      'SELECT %L || chr(9) || count(*)::text FROM %I.%I;',
      table_name,
      table_schema,
      table_name
    )
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name;
  ")"
  [[ -n "${generated_sql}" ]] || fail "No public tables were discovered"
  printf '%s\n' "${generated_sql}" | docker exec -i "${container_name}" sh -lc \
    'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtX' \
    >"${output_file}"
  chmod 600 "${output_file}"
}

require_expected_tables() {
  local counts_file="$1"
  local expected_table
  for expected_table in users projects chat_threads chat_messages media_assets uploaded_documents generated_documents uploaded_images generated_images; do
    awk -F '\t' -v expected="${expected_table}" '$1 == expected { found=1 } END { exit found ? 0 : 1 }' \
      "${counts_file}" || fail "Required table is missing: ${expected_table}"
  done
}

capture_media_manifest() {
  local root_dir="$1"
  local output_file="$2"
  "${PYTHON_BIN}" - "${root_dir}" "${output_file}" <<'PY'
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
output = Path(sys.argv[2])
rows = []
for item in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
    mode = item.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise SystemExit("media tree contains a symbolic link")
    if stat.S_ISDIR(mode):
        continue
    if not stat.S_ISREG(mode):
        raise SystemExit("media tree contains a non-regular file")
    digest = hashlib.sha256()
    with item.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    rows.append({"path": item.relative_to(root).as_posix(), "sha256": digest.hexdigest()})
with output.open("w", encoding="utf-8", newline="\n") as handle:
    for row in rows:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        handle.write("\n")
os.chmod(output, 0o600)
print(len(rows))
PY
}

capture_family_counts() {
  local counts_file="$1"
  local output_file="$2"
  "${PYTHON_BIN}" - "${counts_file}" "${output_file}" <<'PY'
import sys
from pathlib import Path

counts = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if not line:
        continue
    table, value = line.split("\t", 1)
    counts[table] = int(value)

families = {
    "users": ("users",),
    "projects": ("projects",),
    "chat_threads": ("chat_threads",),
    "chat_messages": ("chat_messages",),
    "documents": ("uploaded_documents", "generated_documents", "raw_documents"),
    "images_media": ("uploaded_images", "generated_images", "media_assets", "media_aliases"),
    "hosted_room": tuple(name for name in counts if name.startswith("hosted_room")),
    "account_observability": tuple(name for name in counts if name.startswith("account_observability_")),
    "threadspace": tuple(name for name in counts if name.startswith("threadspace_")),
}
with Path(sys.argv[2]).open("w", encoding="utf-8", newline="\n") as handle:
    for family, tables in families.items():
        handle.write(f"{family}\t{sum(counts.get(table, 0) for table in tables)}\n")
    for family in sorted(set(counts) - {table for tables in families.values() for table in tables}):
        handle.write(f"table:{family}\t{counts[family]}\n")
PY
  chmod 600 "${output_file}"
}

compare_table_counts() {
  local before_file="$1"
  local after_file="$2"
  "${PYTHON_BIN}" - "${before_file}" "${after_file}" <<'PY'
import sys
from pathlib import Path

def read(path):
    result = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line:
            table, value = line.split("\t", 1)
            result[table] = int(value)
    return result

before = read(sys.argv[1])
after = read(sys.argv[2])
missing = sorted(set(before) - set(after))
changed = sorted((table, before[table], after[table]) for table in before if table in after and before[table] != after[table])
if missing:
    raise SystemExit("pre-migration tables missing after migration: " + ",".join(missing))
if changed:
    rendered = ",".join(f"{table}:{old}->{new}" for table, old, new in changed)
    raise SystemExit("canonical table counts changed: " + rendered)
print(f"common_table_count={len(before)}")
print(f"new_table_count={len(set(after) - set(before))}")
PY
}

read_alembic_revision() {
  local container_name="$1"
  local revision
  revision="$(container_query "${container_name}" \
    "SELECT version_num FROM alembic_version ORDER BY version_num;")"
  revision="$(printf '%s' "${revision}" | tr '\n' ',' | sed 's/,$//')"
  printf '%s' "${revision}"
}

run_integrity_checks() {
  local container_name="$1"
  local output_file="$2"
  local unvalidated_fk
  unvalidated_fk="$(container_query "${container_name}" \
    "SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND NOT convalidated;")"
  [[ "${unvalidated_fk}" == "0" ]] || fail "Database has unvalidated foreign-key constraints"

  # Validate every public-schema foreign key with a catalog-driven check.  The
  # distinct dollar-quote tags are intentional: nested dynamic SQL must not
  # terminate the surrounding DO block.
  container_query_stdin "${container_name}" >/dev/null <<'SQL'
DO $integrity$
DECLARE
  fk record;
  orphan_count bigint;
  null_predicate text;
  join_predicate text;
BEGIN
  FOR fk IN
    SELECT
      con.oid,
      con.conrelid,
      con.confrelid,
      con.conkey,
      con.confkey,
      child_ns.nspname AS child_schema,
      child_rel.relname AS child_table,
      parent_ns.nspname AS parent_schema,
      parent_rel.relname AS parent_table
    FROM pg_constraint AS con
    JOIN pg_class AS child_rel ON child_rel.oid = con.conrelid
    JOIN pg_namespace AS child_ns ON child_ns.oid = child_rel.relnamespace
    JOIN pg_class AS parent_rel ON parent_rel.oid = con.confrelid
    JOIN pg_namespace AS parent_ns ON parent_ns.oid = parent_rel.relnamespace
    WHERE con.contype = 'f'
      AND child_ns.nspname = 'public'
      AND parent_ns.nspname = 'public'
  LOOP
    SELECT
      string_agg(format('child.%I IS NOT NULL', child_att.attname), ' AND ' ORDER BY key_map.ord),
      string_agg(format('child.%I IS NOT DISTINCT FROM parent.%I', child_att.attname, parent_att.attname), ' AND ' ORDER BY key_map.ord)
    INTO null_predicate, join_predicate
    FROM unnest(fk.conkey) WITH ORDINALITY AS key_map(attnum, ord)
    JOIN pg_attribute AS child_att
      ON child_att.attrelid = fk.conrelid
     AND child_att.attnum = key_map.attnum
    JOIN unnest(fk.confkey) WITH ORDINALITY AS parent_map(attnum, ord)
      ON parent_map.ord = key_map.ord
    JOIN pg_attribute AS parent_att
      ON parent_att.attrelid = fk.confrelid
     AND parent_att.attnum = parent_map.attnum;

    EXECUTE format(
      'SELECT count(*) FROM %I.%I AS child
        WHERE %s
          AND NOT EXISTS (
            SELECT 1 FROM %I.%I AS parent WHERE %s
          )',
      fk.child_schema,
      fk.child_table,
      null_predicate,
      fk.parent_schema,
      fk.parent_table,
      join_predicate
    ) INTO orphan_count;
    IF orphan_count <> 0 THEN
      RAISE EXCEPTION 'foreign-key integrity check failed';
    END IF;
  END LOOP;
END
$integrity$;
SQL

  # These checks cover the principal application relationships even if a
  # legacy table predates its formal foreign key.  Missing optional tables or
  # columns are recorded as not applicable rather than treated as data loss.
  container_query_stdin "${container_name}" >/dev/null <<'SQL'
DO $semantic$
DECLARE
  relation record;
  orphan_count bigint;
BEGIN
  FOR relation IN
    SELECT * FROM (VALUES
      ('projects', 'user_id', 'users', 'id'),
      ('chat_threads', 'user_id', 'users', 'id'),
      ('chat_threads', 'project_id', 'projects', 'id'),
      ('chat_threads', 'parent_thread_id', 'chat_threads', 'id'),
      ('chat_messages', 'thread_id', 'chat_threads', 'id'),
      ('chat_messages', 'user_id', 'users', 'id'),
      ('repository_bindings', 'project_id', 'projects', 'id'),
      ('hosted_rooms', 'owner_account_id', 'users', 'id'),
      ('hosted_rooms', 'backing_thread_id', 'chat_threads', 'id'),
      ('hosted_room_invites', 'room_id', 'hosted_rooms', 'id'),
      ('hosted_room_participants', 'room_id', 'hosted_rooms', 'id'),
      ('hosted_room_participants', 'invitation_id', 'hosted_room_invites', 'id'),
      ('hosted_room_participants', 'bound_account_id', 'users', 'id'),
      ('media_assets', 'project_id', 'projects', 'id'),
      ('media_assets', 'thread_id', 'chat_threads', 'id'),
      ('uploaded_documents', 'asset_id', 'media_assets', 'id'),
      ('uploaded_documents', 'project_id', 'projects', 'id'),
      ('uploaded_documents', 'thread_id', 'chat_threads', 'id'),
      ('uploaded_documents', 'user_id', 'users', 'id'),
      ('generated_documents', 'project_id', 'projects', 'id'),
      ('generated_documents', 'thread_id', 'chat_threads', 'id'),
      ('uploaded_images', 'asset_id', 'media_assets', 'id'),
      ('uploaded_images', 'project_id', 'projects', 'id'),
      ('uploaded_images', 'thread_id', 'chat_threads', 'id'),
      ('generated_images', 'asset_id', 'media_assets', 'id'),
      ('generated_images', 'project_id', 'projects', 'id'),
      ('generated_images', 'thread_id', 'chat_threads', 'id'),
      ('account_observability_invite_links', 'created_by_user_id', 'users', 'id'),
      ('account_observability_guest_identities', 'first_invite_id', 'account_observability_invite_links', 'invite_id'),
      ('account_observability_account_metadata', 'user_id', 'users', 'id'),
      ('account_observability_account_metadata', 'acquisition_invite_id', 'account_observability_invite_links', 'invite_id'),
      ('account_observability_account_metadata', 'prior_guest_id', 'account_observability_guest_identities', 'guest_id'),
      ('account_observability_presence_sessions', 'user_id', 'users', 'id'),
      ('account_observability_presence_sessions', 'guest_id', 'account_observability_guest_identities', 'guest_id'),
      ('account_observability_presence_sessions', 'invite_id', 'account_observability_invite_links', 'invite_id')
    ) AS relation_values(child_table, child_column, parent_table, parent_column)
  LOOP
    IF to_regclass('public.' || quote_ident(relation.child_table)) IS NULL
       OR to_regclass('public.' || quote_ident(relation.parent_table)) IS NULL
       OR NOT EXISTS (
         SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = relation.child_table
           AND column_name = relation.child_column
       )
       OR NOT EXISTS (
         SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = relation.parent_table
           AND column_name = relation.parent_column
       ) THEN
      CONTINUE;
    END IF;
    EXECUTE format(
      'SELECT count(*) FROM public.%I AS child
        WHERE child.%I IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM public.%I AS parent
            WHERE child.%I IS NOT DISTINCT FROM parent.%I
          )',
      relation.child_table,
      relation.child_column,
      relation.parent_table,
      relation.child_column,
      relation.parent_column
    ) INTO orphan_count;
    IF orphan_count <> 0 THEN
      RAISE EXCEPTION 'semantic relationship integrity check failed';
    END IF;
  END LOOP;
END
$semantic$;
SQL

  printf 'foreign_keys_unvalidated\t%s\nknown_relationships\tPASS\n' "${unvalidated_fk}" >"${output_file}"
  chmod 600 "${output_file}"
}

assert_schema_objects() {
  local container_name="$1"
  local output_file="$2"
  local missing_tables
  local missing_columns
  local missing_constraints
  local missing_indexes

  missing_tables="$(container_query "${container_name}" "
    SELECT required_name
    FROM (VALUES
      ('repository_bindings'),
      ('threadspace_nodes'),
      ('threadspace_membership_invitations'),
      ('threadspace_membership_grants'),
      ('account_observability_invite_links'),
      ('account_observability_guest_identities'),
      ('account_observability_account_metadata'),
      ('account_observability_presence_sessions'),
      ('notion_connection_credentials'),
      ('github_watchdog_delivery_receipts'),
      ('github_watchdog_review_attempts'),
      ('github_watchdog_review_input_snapshots'),
      ('github_watchdog_review_results'),
      ('github_watchdog_review_dispatches')
    ) AS required(required_name)
    WHERE to_regclass('public.' || quote_ident(required_name)) IS NULL
    ORDER BY required_name;
  ")"
  [[ -z "${missing_tables}" ]] || fail "Expected migrated tables are missing"

  missing_columns="$(container_query "${container_name}" "
    SELECT required.table_name || '.' || required.column_name
    FROM (VALUES
      ('chat_threads', 'origin_system'),
      ('projects', 'system_role'),
      ('projects', 'archived_at'),
      ('account_observability_invite_links', 'invite_id'),
      ('account_observability_guest_identities', 'guest_id'),
      ('account_observability_presence_sessions', 'presence_session_id')
    ) AS required(table_name, column_name)
    WHERE NOT EXISTS (
      SELECT 1
      FROM information_schema.columns AS columns
      WHERE columns.table_schema = 'public'
        AND columns.table_name = required.table_name
        AND columns.column_name = required.column_name
    )
    ORDER BY required.table_name, required.column_name;
  ")"
  [[ -z "${missing_columns}" ]] || fail "Expected migrated columns are missing"

  missing_constraints="$(container_query "${container_name}" "
    SELECT required_name
    FROM (VALUES
      ('ck_chat_threads_origin_system_canonical'),
      ('projects_system_role_check'),
      ('account_observability_invite_status_check'),
      ('account_observability_invite_lifecycle_check'),
      ('account_observability_attribution_method_check'),
      ('account_observability_attribution_confidence_check'),
      ('account_observability_attribution_consistency_check'),
      ('account_observability_presence_exactly_one_subject_check'),
      ('account_observability_presence_last_seen_order_check'),
      ('account_observability_presence_ended_order_check'),
      ('account_observability_presence_region_country_check'),
      ('account_observability_presence_country_code_check')
    ) AS required(required_name)
    WHERE NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conname = required.required_name
    )
    ORDER BY required_name;
  ")"
  [[ -z "${missing_constraints}" ]] || fail "Expected migrated constraints are missing"

  missing_indexes="$(container_query "${container_name}" "
    SELECT required_name
    FROM (VALUES
      ('ix_repository_bindings_project_id'),
      ('uq_repository_bindings_one_active_per_project'),
      ('ix_chat_threads_user_origin'),
      ('uq_projects_user_id_system_role'),
      ('ix_account_observability_presence_sessions_user_last_seen_at'),
      ('ix_account_observability_presence_sessions_guest_last_seen_at'),
      ('ix_account_observability_presence_sessions_invite_started_at'),
      ('ix_acct_obs_presence_last_seen_country_region'),
      ('ix_account_observability_guest_identities_first_invite_id')
    ) AS required(required_name)
    WHERE NOT EXISTS (
      SELECT 1 FROM pg_class
      WHERE relkind IN ('i', 'I')
        AND relname = required.required_name
    )
    ORDER BY required_name;
  ")"
  [[ -z "${missing_indexes}" ]] || fail "Expected migrated indexes are missing"

  printf 'expected_tables=PASS\nexpected_columns=PASS\nexpected_constraints=PASS\nexpected_indexes=PASS\n' >"${output_file}"
  chmod 600 "${output_file}"
}

assert_source_volume_mount() {
  local container_name="$1"
  local mount
  mount="$(docker inspect "${container_name}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}')"
  [[ "${mount}" == "${SOURCE_VOLUME}|true" ]] || fail "Source db is not mounted to the expected pg_data volume"
}

assert_no_host_ports() {
  local container_name="$1"
  local bindings
  bindings="$(docker inspect "${container_name}" --format '{{json .HostConfig.PortBindings}}')"
  case "${bindings}" in
    "{}"|"null") ;;
    *) fail "Proof database container published a host port" ;;
  esac
}

assert_source_volume_consumers() {
  local consumer_ids
  local consumer_count
  local consumer_name
  local source_name
  consumer_ids="$(docker ps -q --filter "volume=${SOURCE_VOLUME}")"
  consumer_count="$(printf '%s\n' "${consumer_ids}" | awk 'NF { count++ } END { print count + 0 }')"
  [[ "${consumer_count}" == "1" ]] || fail "Unexpected active source-volume consumer count: ${consumer_count}"
  consumer_name="$(docker inspect "${consumer_ids}" --format '{{.Name}}' | sed 's#^/##')"
  source_name="$(docker inspect "${SOURCE_DB_CONTAINER}" --format '{{.Name}}' | sed 's#^/##')"
  [[ "${consumer_name}" == "${source_name}" ]] || fail "An unexpected active container uses the source Postgres volume"
}

validate_checkpoint_permissions() {
  local checkpoint_dir="$1"
  "${PYTHON_BIN}" - "${checkpoint_dir}" <<'PY'
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
for item in [root, *root.rglob("*")]:
    mode = stat.S_IMODE(item.stat().st_mode)
    expected = 0o700 if item.is_dir() else 0o600
    if mode != expected:
        raise SystemExit(f"unsafe checkpoint permissions for {item.name}: {oct(mode)}")
PY
}

remove_named_container() {
  local container_name="$1"
  local expected_prefix="$2"
  case "${container_name}" in
    "${expected_prefix}"*) ;;
    *) fail "Refusing to remove an unexpected proof container"; return 1 ;;
  esac
  if docker container inspect "${container_name}" >/dev/null 2>&1; then
    docker rm -f "${container_name}" >/dev/null
  fi
  ! docker container inspect "${container_name}" >/dev/null 2>&1
}

remove_named_volume() {
  local volume_name="$1"
  case "${volume_name}" in
    codexify_private_preview_restore_*) ;;
    *) fail "Refusing to remove an unexpected proof volume"; return 1 ;;
  esac
  [[ "${volume_name}" != "${SOURCE_VOLUME}" ]] || {
    fail "Refusing to remove the source Postgres volume"
    return 1
  }
  if docker volume inspect "${volume_name}" >/dev/null 2>&1; then
    docker volume rm "${volume_name}" >/dev/null
  fi
  ! docker volume inspect "${volume_name}" >/dev/null 2>&1
}

cleanup_disposable_resources() {
  local container_ok=1
  local volume_ok=1
  if [[ -n "${DISPOSABLE_CONTAINER}" ]]; then
    remove_named_container "${DISPOSABLE_CONTAINER}" "codexify-private-preview-restore-" || container_ok=0
  fi
  if [[ -n "${DISPOSABLE_VOLUME}" ]]; then
    remove_named_volume "${DISPOSABLE_VOLUME}" || volume_ok=0
  fi
  if (( container_ok == 1 )); then
    DISPOSABLE_CONTAINER_REMOVED=1
  fi
  if (( volume_ok == 1 )); then
    DISPOSABLE_VOLUME_REMOVED=1
  fi
}

cleanup_migrator_containers() {
  if [[ -n "${SOURCE_MIGRATOR_CONTAINER}" ]]; then
    remove_named_container "${SOURCE_MIGRATOR_CONTAINER}" "codexify-private-preview-migration-source-" || true
  fi
  if [[ -n "${SOURCE_NOOP_MIGRATOR_CONTAINER}" ]]; then
    remove_named_container "${SOURCE_NOOP_MIGRATOR_CONTAINER}" "codexify-private-preview-migration-source-noop-" || true
  fi
  if [[ -n "${DISPOSABLE_MIGRATOR_CONTAINER:-}" ]]; then
    remove_named_container "${DISPOSABLE_MIGRATOR_CONTAINER}" "codexify-private-preview-migration-disposable-" || true
  fi
}

remove_proof_created_source_db_container() {
  local db_container_id
  local db_mount
  if (( SOURCE_DB_CONTAINER_EXISTED_BEFORE == 0 )); then
    db_container_id="$(compose ps -a -q db 2>/dev/null || true)"
    if [[ -n "${db_container_id}" ]]; then
      db_mount="$(docker inspect "${db_container_id}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}')"
      if [[ "${db_mount}" == "${SOURCE_VOLUME}|true" ]]; then
        docker rm "${db_container_id}" >/dev/null 2>&1 || true
      fi
    fi
  fi
}

service_was_running() {
  local service_name="$1"
  local services_file="$2"
  grep -Fxq "${service_name}" "${services_file}"
}

service_is_known_preview_service() {
  local service_name="$1"
  case "${service_name}" in
    db|backend|worker-warmup|worker-chat|worker-watchdog-review|worker-coding|worker-voice|worker-account-import|worker-document-embed|worker-chat-embed|frontend|private-preview-origin|redis|neo4j|graph-init|tts)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

assert_no_one_off_writers_before_freeze() {
  local running_services_file="$1"
  local forbidden_service
  for forbidden_service in migrator chatgpt-migrate obsidian-ingest embedding-backfill graph-backfill e2e; do
    if service_was_running "${forbidden_service}" "${running_services_file}"; then
      fail "A one-off writer service was already running: ${forbidden_service}"
    fi
  done
}

wait_for_service_posture() {
  local services_file="$1"
  local service_name
  local container_id
  local health
  local waited
  while IFS= read -r service_name; do
    [[ -n "${service_name}" ]] || continue
    container_id="$(compose ps -q "${service_name}" 2>/dev/null || true)"
    [[ -n "${container_id}" ]] || fail "Previously running service did not return: ${service_name}"
    [[ "$(docker inspect "${container_id}" --format '{{.State.Status}}')" == "running" ]] || \
      fail "Previously running service is not running: ${service_name}"
    health="$(docker inspect "${container_id}" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}')"
    if [[ "${health}" != "none" ]]; then
      waited=0
      while [[ "$(docker inspect "${container_id}" --format '{{.State.Health.Status}}')" != "healthy" ]]; do
        if [[ "$(docker inspect "${container_id}" --format '{{.State.Status}}')" != "running" ]]; then
          fail "Previously running service exited while restoring: ${service_name}"
        fi
        if (( waited >= 180 )); then
          fail "Previously running service did not become healthy: ${service_name}"
        fi
        sleep 3
        waited=$((waited + 3))
      done
    fi
  done <"${services_file}"
}

restore_source_runtime() {
  local services_file="${CHECKPOINT_DIR}/source-running-services-before.txt"
  local service_name
  local db_container_id

  compose stop >/dev/null

  for service_name in "${ALL_PREVIEW_SERVICES[@]}"; do
    if service_was_running "${service_name}" "${services_file}"; then
      compose up -d --no-deps "${service_name}" >/dev/null
    fi
  done

  # Compose may contain an operator-added service.  Restore it only if it was
  # observed running before the proof, and never restore a one-off writer.
  while IFS= read -r service_name; do
    [[ -n "${service_name}" ]] || continue
    if ! service_is_known_preview_service "${service_name}"; then
      case "${service_name}" in
        migrator|chatgpt-migrate|obsidian-ingest|embedding-backfill|graph-backfill|e2e)
          fail "Refusing to restore a one-off writer service: ${service_name}"
          ;;
        *)
          compose up -d --no-deps "${service_name}" >/dev/null
          ;;
      esac
    fi
  done <"${services_file}"

  if ! service_was_running "db" "${services_file}" && (( SOURCE_DB_CONTAINER_EXISTED_BEFORE == 0 )); then
    db_container_id="$(compose ps -a -q db 2>/dev/null || true)"
    if [[ -n "${db_container_id}" ]]; then
      docker inspect "${db_container_id}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}' \
        | grep -Fx "${SOURCE_VOLUME}|true" >/dev/null || fail "Refusing to remove a db container with an unexpected mount"
      docker rm "${db_container_id}" >/dev/null
    fi
  fi

  wait_for_service_posture "${services_file}"
  SOURCE_RUNTIME_RESTORED=1
}

assert_source_frozen() {
  local running_after_freeze
  running_after_freeze="$(compose ps --status running --services | LC_ALL=C sort)"
  [[ "${running_after_freeze}" == "db" ]] || fail "Application writers remain active during the migration window"
  assert_source_volume_consumers
}

capture_source_volume_identity() {
  docker volume inspect "${SOURCE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}|{{.Driver}}'
}

capture_checkpoint_marker() {
  local marker_file="$1"
  shift
  printf '%s\n' "$@" >"${marker_file}"
  chmod 600 "${marker_file}"
}

write_failure_marker() {
  [[ -n "${CHECKPOINT_DIR}" && -d "${CHECKPOINT_DIR}" ]] || return 0
  capture_checkpoint_marker "${CHECKPOINT_DIR}/PROOF_FAILED" \
    "conclusion=PRIVATE_PREVIEW_DATABASE_MIGRATION_FAILED" \
    "source_frozen=$([[ ${SOURCE_FROZEN} == 1 ]] && printf YES || printf NO)" \
    "backup_retained=$([[ ${CHECKPOINT_HAS_BACKUP} == 1 ]] && printf YES || printf NO)" \
    "disposable_rehearsal=$([[ ${DISPOSABLE_MIGRATION_REHEARSAL:-0} == 1 ]] && printf PASS || printf NOT_PROVEN)"
}

check_repository_unchanged() {
  local current_status_file="$1"
  git -C "${REPO_ROOT}" status --porcelain=v1 --untracked-files=all >"${current_status_file}"
  chmod 600 "${current_status_file}"
  cmp -s "${BASELINE_STATUS_FILE}" "${current_status_file}" || fail "Repository state changed during live proof"
}

verify_migration_invariants() {
  local container_name="$1"
  local output_file="$2"
  container_query "${container_name}" "
    SELECT 'chat_threads_origin_invalid', count(*)
    FROM chat_threads
    WHERE origin_system NOT IN ('codexify', 'openai', 'anthropic')
    UNION ALL
    SELECT 'projects_system_role_invalid', count(*)
    FROM projects
    WHERE system_role IS NOT NULL
      AND system_role NOT IN ('general', 'imports')
    UNION ALL
    SELECT 'general_backfill_invalid', count(*)
    FROM projects
    WHERE name = 'General'
      AND system_role IS DISTINCT FROM 'general'
    UNION ALL
    SELECT 'imports_backfill_invalid', count(*)
    FROM projects
    WHERE name = 'Imports'
      AND system_role IS DISTINCT FROM 'imports'
    UNION ALL
    SELECT 'account_observability_null_creator', count(*)
    FROM account_observability_invite_links
    WHERE created_by_user_id IS NULL
    UNION ALL
    SELECT 'account_observability_country_invalid', count(*)
    FROM account_observability_presence_sessions
    WHERE country_code IS NOT NULL
      AND (length(country_code) <> 2 OR country_code <> upper(country_code))
    UNION ALL
    SELECT 'account_observability_presence_subject_invalid', count(*)
    FROM account_observability_presence_sessions
    WHERE (user_id IS NULL) = (guest_id IS NULL)
    ORDER BY 1;
  " >"${output_file}"
  chmod 600 "${output_file}"
  awk -F '|' '$2 != 0 { exit 1 }' "${output_file}" || fail "A deterministic migration invariant failed"
}

capture_schema_signature() {
  local container_name="$1"
  local output_file="$2"
  container_query "${container_name}" "
    WITH objects AS (
      SELECT 'table'::text AS kind, c.relname::text AS object_name, ''::text AS detail
      FROM pg_class AS c
      JOIN pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
      UNION ALL
      SELECT 'column', table_name, column_name
      FROM information_schema.columns
      WHERE table_schema = 'public'
      UNION ALL
      SELECT 'constraint', conrelid::regclass::text, conname
      FROM pg_constraint
      WHERE connamespace = 'public'::regnamespace
      UNION ALL
      SELECT 'index', table_rel.relname, index_rel.relname
      FROM pg_index
      JOIN pg_class AS table_rel ON table_rel.oid = pg_index.indrelid
      JOIN pg_class AS index_rel ON index_rel.oid = pg_index.indexrelid
      JOIN pg_namespace AS n ON n.oid = table_rel.relnamespace
      WHERE n.nspname = 'public'
    )
    SELECT md5(COALESCE(string_agg(kind || chr(9) || object_name || chr(9) || detail, chr(10) ORDER BY kind, object_name, detail), ''))
    FROM objects;
  " >"${output_file}"
  chmod 600 "${output_file}"
}

verify_source_media_unchanged() {
  local after_manifest="${CHECKPOINT_DIR}/media-source-manifest-after-${1}.jsonl"
  local after_count
  local before_count
  after_count="$(capture_media_manifest "${MEDIA_ROOT}" "${after_manifest}")"
  before_count="${SOURCE_MEDIA_FILE_COUNT}"
  [[ "${after_count}" == "${before_count}" ]] || fail "Source media file count changed"
  cmp -s "${SOURCE_MEDIA_MANIFEST}" "${after_manifest}" || fail "Source media manifest changed"
  SOURCE_MEDIA_MANIFEST_AFTER_SHA256="$(sha256_file "${after_manifest}")"
}

create_source_checkpoint() {
  local source_service_file
  local source_service_count
  local source_db_before

  SOURCE_GIT_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
  CHECKPOINT_TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
  CHECKPOINT_ID="private-preview-database-migration-${CHECKPOINT_TIMESTAMP}-${SOURCE_GIT_COMMIT:0:12}"
  CHECKPOINT_DIR="${BACKUP_ROOT}/${CHECKPOINT_ID}"
  [[ ! -e "${CHECKPOINT_DIR}" ]] || fail "Checkpoint directory already exists"
  mkdir "${CHECKPOINT_DIR}"
  chmod 700 "${CHECKPOINT_DIR}"

  source_service_file="${CHECKPOINT_DIR}/source-running-services-before.txt"
  compose ps --status running --services | LC_ALL=C sort >"${source_service_file}"
  chmod 600 "${source_service_file}"
  source_service_count="$(wc -l <"${source_service_file}" | tr -d '[:space:]')"
  SOURCE_RUNNING_SERVICE_COUNT="${source_service_count}"
  assert_no_one_off_writers_before_freeze "${source_service_file}"

  source_db_before="$(compose ps -a -q db 2>/dev/null || true)"
  if [[ -n "${source_db_before}" ]]; then
    SOURCE_DB_CONTAINER_EXISTED_BEFORE=1
  fi

  SOURCE_VOLUME_IDENTITY_BEFORE="$(capture_source_volume_identity)"
  capture_checkpoint_marker "${CHECKPOINT_DIR}/checkpoint-created.txt" \
    "checkpoint_id=${CHECKPOINT_ID}" \
    "source_git_commit=${SOURCE_GIT_COMMIT}" \
    "source_volume_identity_captured=YES" \
    "source_running_service_count=${SOURCE_RUNNING_SERVICE_COUNT}"
}

freeze_source_and_capture_manifest() {
  local source_server_major
  local incomplete_imports
  local current_revision
  local source_mount

  # Mark the source as frozen before issuing stop so the EXIT trap remains
  # fail-closed if Compose stops only part of the service set.
  SOURCE_FROZEN=1
  compose stop >/dev/null
  compose up -d --no-deps db >/dev/null
  SOURCE_DB_CONTAINER="$(compose ps -q db)"
  [[ -n "${SOURCE_DB_CONTAINER}" ]] || fail "Source db container was not created"
  wait_for_postgres "${SOURCE_DB_CONTAINER}"
  source_server_major="$(container_query "${SOURCE_DB_CONTAINER}" \
    "SELECT current_setting('server_version_num')::integer / 10000;")"
  [[ "${source_server_major}" == "15" ]] || fail "Source database is not PostgreSQL 15"
  assert_no_host_ports "${SOURCE_DB_CONTAINER}"
  assert_source_volume_mount "${SOURCE_DB_CONTAINER}"
  assert_source_frozen

  current_revision="$(read_alembic_revision "${SOURCE_DB_CONTAINER}")"
  [[ "${current_revision}" == "${SOURCE_REVISION}" ]] || fail "Source revision is not the expected pre-migration revision"
  SOURCE_REVISION_BEFORE="${current_revision}"

  incomplete_imports="$(container_query "${SOURCE_DB_CONTAINER}" "
    SELECT CASE
      WHEN to_regclass('public.openai_account_import_jobs') IS NULL THEN 0
      ELSE (
        SELECT count(*)
        FROM openai_account_import_jobs
        WHERE status IN ('receiving', 'queued', 'running')
      )
    END;
  ")"
  [[ "${incomplete_imports}" == "0" ]] || fail "An incomplete account-import job makes the checkpoint unsafe"
  INCOMPLETE_IMPORT_COUNT="${incomplete_imports}"

  SOURCE_TABLE_COUNTS="${CHECKPOINT_DIR}/source-table-counts.tsv"
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${SOURCE_TABLE_COUNTS}"
  require_expected_tables "${SOURCE_TABLE_COUNTS}"
  SOURCE_TABLE_COUNT="$(wc -l <"${SOURCE_TABLE_COUNTS}" | tr -d '[:space:]')"
  SOURCE_TABLE_COUNTS_SHA256="$(sha256_file "${SOURCE_TABLE_COUNTS}")"
  capture_family_counts "${SOURCE_TABLE_COUNTS}" "${CHECKPOINT_DIR}/source-family-counts.tsv"
  SOURCE_FAMILY_COUNTS_SHA256="$(sha256_file "${CHECKPOINT_DIR}/source-family-counts.tsv")"
  run_integrity_checks "${SOURCE_DB_CONTAINER}" "${CHECKPOINT_DIR}/source-integrity.tsv"
  SOURCE_INTEGRITY_SHA256="$(sha256_file "${CHECKPOINT_DIR}/source-integrity.tsv")"
  SOURCE_SCHEMA_SIGNATURE="${CHECKPOINT_DIR}/source-schema-signature.txt"
  capture_schema_signature "${SOURCE_DB_CONTAINER}" "${SOURCE_SCHEMA_SIGNATURE}"
  SOURCE_SCHEMA_SIGNATURE_SHA256="$(sha256_file "${SOURCE_SCHEMA_SIGNATURE}")"

  SOURCE_MEDIA_MANIFEST="${CHECKPOINT_DIR}/media-source-manifest.jsonl"
  SOURCE_MEDIA_FILE_COUNT="$(capture_media_manifest "${MEDIA_ROOT}" "${SOURCE_MEDIA_MANIFEST}")"
  SOURCE_MEDIA_MANIFEST_SHA256="$(sha256_file "${SOURCE_MEDIA_MANIFEST}")"

  source_mount="$(capture_source_volume_identity)"
  [[ "${source_mount}" == "${SOURCE_VOLUME_IDENTITY_BEFORE}" ]] || fail "Source volume identity changed before backup"
}

create_pre_migration_backup() {
  local dump_log="${CHECKPOINT_DIR}/pg-dump.log"
  POSTGRES_DUMP="${CHECKPOINT_DIR}/postgres.dump"
  if ! docker exec "${SOURCE_DB_CONTAINER}" sh -lc \
    'exec pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    >"${POSTGRES_DUMP}" 2>"${dump_log}"; then
    chmod 600 "${dump_log}"
    fail "Pre-migration PostgreSQL dump failed"
  fi
  chmod 600 "${POSTGRES_DUMP}" "${dump_log}"
  [[ -s "${POSTGRES_DUMP}" ]] || fail "Pre-migration PostgreSQL dump is empty"
  POSTGRES_DUMP_SIZE="$(file_size_bytes "${POSTGRES_DUMP}")"
  POSTGRES_DUMP_SHA256="$(sha256_file "${POSTGRES_DUMP}")"
  CHECKPOINT_HAS_BACKUP=1
}

migrate_source_and_verify() {
  local starting_revision
  local pre_mutation_counts="${CHECKPOINT_DIR}/source-table-counts-immediately-before-migration.tsv"
  local pre_mutation_schema="${CHECKPOINT_DIR}/source-schema-signature-immediately-before-migration.txt"
  local migration_log="${CHECKPOINT_DIR}/source-migrator.log"
  local post_revision
  local post_counts="${CHECKPOINT_DIR}/source-post-migration-table-counts.tsv"
  local post_families="${CHECKPOINT_DIR}/source-post-migration-family-counts.tsv"
  local post_integrity="${CHECKPOINT_DIR}/source-post-migration-integrity.tsv"
  local post_schema="${CHECKPOINT_DIR}/source-post-migration-schema-signature.txt"
  local post_schema_checks="${CHECKPOINT_DIR}/source-post-migration-schema-checks.txt"
  local post_invariants="${CHECKPOINT_DIR}/source-post-migration-invariants.tsv"

  assert_source_frozen
  wait_for_postgres "${SOURCE_DB_CONTAINER}"
  starting_revision="$(read_alembic_revision "${SOURCE_DB_CONTAINER}")"
  [[ "${starting_revision}" == "${SOURCE_REVISION}" ]] || fail "Source revision changed before source migration"
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${pre_mutation_counts}"
  compare_table_counts "${SOURCE_TABLE_COUNTS}" "${pre_mutation_counts}" >/dev/null
  capture_schema_signature "${SOURCE_DB_CONTAINER}" "${pre_mutation_schema}"
  cmp -s "${SOURCE_SCHEMA_SIGNATURE}" "${pre_mutation_schema}" || fail "Source schema changed before source migration"
  verify_source_media_unchanged "immediately-before-migration"
  [[ "$(capture_source_volume_identity)" == "${SOURCE_VOLUME_IDENTITY_BEFORE}" ]] || fail "Source volume identity changed before source migration"

  SOURCE_MIGRATION_STARTED=1
  SOURCE_MIGRATOR_CONTAINER="codexify-private-preview-migration-source-${CHECKPOINT_TIMESTAMP}"
  if ! compose run --rm --no-deps --name "${SOURCE_MIGRATOR_CONTAINER}" migrator >"${migration_log}" 2>&1; then
    chmod 600 "${migration_log}"
    fail "Source canonical migrator failed; source remains frozen"
  fi
  chmod 600 "${migration_log}"

  post_revision="$(read_alembic_revision "${SOURCE_DB_CONTAINER}")"
  [[ "${post_revision}" == "${TARGET_REVISION}" ]] || fail "Source migration did not reach the target revision"
  wait_for_postgres "${SOURCE_DB_CONTAINER}"
  assert_source_volume_mount "${SOURCE_DB_CONTAINER}"
  assert_no_host_ports "${SOURCE_DB_CONTAINER}"
  assert_source_frozen
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${post_counts}"
  require_expected_tables "${post_counts}"
  compare_table_counts "${SOURCE_TABLE_COUNTS}" "${post_counts}" >/dev/null
  capture_family_counts "${post_counts}" "${post_families}"
  run_integrity_checks "${SOURCE_DB_CONTAINER}" "${post_integrity}"
  assert_schema_objects "${SOURCE_DB_CONTAINER}" "${post_schema_checks}"
  verify_migration_invariants "${SOURCE_DB_CONTAINER}" "${post_invariants}"
  capture_schema_signature "${SOURCE_DB_CONTAINER}" "${post_schema}"
  verify_source_media_unchanged "after-source-migration"
  [[ "$(capture_source_volume_identity)" == "${SOURCE_VOLUME_IDENTITY_BEFORE}" ]] || fail "Source volume identity changed during migration"

  SOURCE_POST_REVISION="${post_revision}"
  SOURCE_POST_COUNTS_SHA256="$(sha256_file "${post_counts}")"
  SOURCE_POST_FAMILIES_SHA256="$(sha256_file "${post_families}")"
  SOURCE_POST_INTEGRITY_SHA256="$(sha256_file "${post_integrity}")"
  SOURCE_POST_SCHEMA_SHA256="$(sha256_file "${post_schema}")"
  SOURCE_POST_SCHEMA_CHECKS_SHA256="$(sha256_file "${post_schema_checks}")"
  SOURCE_POST_INVARIANTS_SHA256="$(sha256_file "${post_invariants}")"
}

run_source_migrator_noop() {
  local before_counts="${CHECKPOINT_DIR}/source-noop-before-table-counts.tsv"
  local before_schema="${CHECKPOINT_DIR}/source-noop-before-schema-signature.txt"
  local noop_log="${CHECKPOINT_DIR}/source-noop-migrator.log"
  local after_counts="${CHECKPOINT_DIR}/source-noop-after-table-counts.tsv"
  local after_schema="${CHECKPOINT_DIR}/source-noop-after-schema-signature.txt"
  local after_revision

  assert_source_frozen
  [[ "$(read_alembic_revision "${SOURCE_DB_CONTAINER}")" == "${TARGET_REVISION}" ]] || fail "Source is not at current head before no-op check"
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${before_counts}"
  capture_schema_signature "${SOURCE_DB_CONTAINER}" "${before_schema}"
  SOURCE_NOOP_MIGRATOR_CONTAINER="codexify-private-preview-migration-source-noop-${CHECKPOINT_TIMESTAMP}"
  if ! compose run --rm --no-deps --name "${SOURCE_NOOP_MIGRATOR_CONTAINER}" migrator >"${noop_log}" 2>&1; then
    chmod 600 "${noop_log}"
    fail "Second canonical migrator invocation failed"
  fi
  chmod 600 "${noop_log}"
  after_revision="$(read_alembic_revision "${SOURCE_DB_CONTAINER}")"
  [[ "${after_revision}" == "${TARGET_REVISION}" ]] || fail "Second migrator changed the Alembic head unexpectedly"
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${after_counts}"
  compare_table_counts "${before_counts}" "${after_counts}" >/dev/null
  capture_schema_signature "${SOURCE_DB_CONTAINER}" "${after_schema}"
  cmp -s "${before_schema}" "${after_schema}" || fail "Second migrator changed the schema at head"
  run_integrity_checks "${SOURCE_DB_CONTAINER}" "${CHECKPOINT_DIR}/source-noop-integrity.tsv"
  verify_source_media_unchanged "after-source-noop"
  assert_source_frozen
  SOURCE_NOOP_REVISION="${after_revision}"
  SOURCE_NOOP_COUNTS_SHA256="$(sha256_file "${after_counts}")"
  SOURCE_NOOP_SCHEMA_SHA256="$(sha256_file "${after_schema}")"
  SOURCE_NOOP_INTEGRITY_SHA256="$(sha256_file "${CHECKPOINT_DIR}/source-noop-integrity.tsv")"
}

write_success_manifest() {
  local manifest_file="${CHECKPOINT_DIR}/checkpoint-manifest.txt"
  local volume_identity_sha256
  local script_sha256
  volume_identity_sha256="$(printf '%s' "${SOURCE_VOLUME_IDENTITY_BEFORE}" | shasum -a 256 | awk '{print $1}')"
  script_sha256="$(sha256_file "${BASH_SOURCE[0]}")"
  {
    printf '%s\n' \
      'manifest_version=1' \
      "checkpoint_id=${CHECKPOINT_ID}" \
      "checkpoint_timestamp=${CHECKPOINT_TIMESTAMP}" \
      "source_git_commit=${SOURCE_GIT_COMMIT}" \
      "compose_project=${PROJECT_NAME}" \
      'private_preview_gate=closed' \
      "source_volume_name=${SOURCE_VOLUME}" \
      "source_volume_identity_sha256=${volume_identity_sha256}" \
      "source_revision=${SOURCE_REVISION_BEFORE}" \
      "target_revision=${TARGET_REVISION}" \
      'migration_graph=PASS' \
      'source_writers_frozen=PASS' \
      "incomplete_import_job_count=${INCOMPLETE_IMPORT_COUNT}" \
      "source_public_table_count=${SOURCE_TABLE_COUNT}" \
      "source_table_counts_sha256=${SOURCE_TABLE_COUNTS_SHA256}" \
      "source_family_counts_sha256=${SOURCE_FAMILY_COUNTS_SHA256}" \
      "source_integrity_sha256=${SOURCE_INTEGRITY_SHA256}" \
      "source_schema_signature_sha256=${SOURCE_SCHEMA_SIGNATURE_SHA256}" \
      'backup_format=postgres_custom' \
      'backup_owner_acl_options=no-owner,no-acl' \
      "postgres_dump_size_bytes=${POSTGRES_DUMP_SIZE}" \
      "postgres_dump_sha256=${POSTGRES_DUMP_SHA256}" \
      'backup_permissions=0600' \
      'backup_restore=PASS' \
      "restore_revision=${RESTORE_ALEMBIC_REVISION}" \
      "restore_table_counts_sha256=${RESTORE_TABLE_COUNTS_SHA256}" \
      "restore_integrity_sha256=${RESTORE_INTEGRITY_SHA256}" \
      'disposable_migration_rehearsal=PASS' \
      "disposable_revision=${DISPOSABLE_POST_REVISION}" \
      "disposable_table_counts_sha256=${DISPOSABLE_POST_COUNTS_SHA256}" \
      "disposable_integrity_sha256=${DISPOSABLE_POST_INTEGRITY_SHA256}" \
      "disposable_schema_checks_sha256=${DISPOSABLE_SCHEMA_CHECKS_SHA256}" \
      "disposable_invariants_sha256=${DISPOSABLE_INVARIANTS_SHA256}" \
      'source_migration=PASS' \
      "source_post_revision=${SOURCE_POST_REVISION}" \
      "source_post_table_counts_sha256=${SOURCE_POST_COUNTS_SHA256}" \
      "source_post_families_sha256=${SOURCE_POST_FAMILIES_SHA256}" \
      "source_post_integrity_sha256=${SOURCE_POST_INTEGRITY_SHA256}" \
      "source_post_schema_sha256=${SOURCE_POST_SCHEMA_SHA256}" \
      "source_post_schema_checks_sha256=${SOURCE_POST_SCHEMA_CHECKS_SHA256}" \
      "source_post_invariants_sha256=${SOURCE_POST_INVARIANTS_SHA256}" \
      "source_media_file_count=${SOURCE_MEDIA_FILE_COUNT}" \
      "source_media_manifest_sha256=${SOURCE_MEDIA_MANIFEST_SHA256}" \
      'source_media_unchanged=PASS' \
      'source_volume_identity=UNCHANGED' \
      'second_migrator=PASS' \
      "second_migrator_revision=${SOURCE_NOOP_REVISION}" \
      "second_migrator_table_counts_sha256=${SOURCE_NOOP_COUNTS_SHA256}" \
      "second_migrator_schema_sha256=${SOURCE_NOOP_SCHEMA_SHA256}" \
      "second_migrator_integrity_sha256=${SOURCE_NOOP_INTEGRITY_SHA256}" \
      'disposable_container_removed=PASS' \
      'disposable_volume_removed=PASS' \
      'retained_pre_migration_backup=PASS' \
      'source_runtime_posture_restored=PASS' \
      'repository_state_unchanged=PASS' \
      "proof_script_sha256=${script_sha256}" \
      'conclusion=PRIVATE_PREVIEW_DATABASE_MIGRATION_PROVEN'
    printf '\n[pre_migration_table_counts]\n'
    sed -n '1,240p' "${SOURCE_TABLE_COUNTS}"
  } >"${manifest_file}"
  chmod 600 "${manifest_file}"
}

on_exit() {
  local exit_code=$?
  set +e

  # Kill only proof-owned one-off containers.  The source is stopped below on
  # failure, and is never restarted by the failure path.
  cleanup_migrator_containers >/dev/null 2>&1
  cleanup_disposable_resources >/dev/null 2>&1

  if (( exit_code != 0 || PROOF_SUCCEEDED == 0 )); then
    if (( SOURCE_FROZEN == 1 )); then
      compose stop >/dev/null 2>&1 || true
      remove_proof_created_source_db_container
    fi
    write_failure_marker
    if [[ -n "${CHECKPOINT_ID}" ]]; then
      printf 'PRIVATE_PREVIEW_DATABASE_MIGRATION_FAILED\ncheckpoint_id=%s\n' \
        "${CHECKPOINT_ID}" >&2
    else
      printf 'PRIVATE_PREVIEW_DATABASE_MIGRATION_FAILED\n' >&2
    fi
    if (( exit_code == 0 )); then
      exit_code=1
    fi
  fi

  if [[ -n "${BASELINE_STATUS_FILE}" ]]; then
    rm -f -- "${BASELINE_STATUS_FILE}"
  fi
  exit "${exit_code}"
}

trap on_exit EXIT INT TERM

main() {
  local restore_suffix
  local source_after_backup_counts
  local source_after_rehearsal_counts
  local source_after_backup_media_label
  local source_after_rehearsal_media_label
  local current_revision

  umask 077
  BASELINE_STATUS_FILE="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview-migration-status.XXXXXX")"
  chmod 600 "${BASELINE_STATUS_FILE}"
  git -C "${REPO_ROOT}" status --short --untracked-files=all >"${BASELINE_STATUS_FILE}"

  # Static lineage and topology gates run before any Docker or filesystem
  # mutation.  The migration graph is intentionally explicit about its two
  # known branches and their merge revision.
  validate_migration_graph
  validate_static_inputs
  validate_backup_destination
  log "static_preflight=PASS"

  docker volume inspect "${SOURCE_VOLUME}" >/dev/null || fail "Source Postgres volume is missing"
  create_source_checkpoint
  log "checkpoint_created=PASS"
  log "source_running_service_count=${SOURCE_RUNNING_SERVICE_COUNT}"

  freeze_source_and_capture_manifest
  log "source_writer_freeze=PASS"
  log "source_revision=${SOURCE_REVISION_BEFORE}"
  log "source_public_table_count=${SOURCE_TABLE_COUNT}"
  log "source_media_file_count=${SOURCE_MEDIA_FILE_COUNT}"

  create_pre_migration_backup
  assert_source_frozen
  source_after_backup_counts="${CHECKPOINT_DIR}/source-table-counts-after-backup.tsv"
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${source_after_backup_counts}"
  compare_table_counts "${SOURCE_TABLE_COUNTS}" "${source_after_backup_counts}" >/dev/null
  source_after_backup_media_label="after-backup"
  verify_source_media_unchanged "${source_after_backup_media_label}"
  [[ "$(capture_source_volume_identity)" == "${SOURCE_VOLUME_IDENTITY_BEFORE}" ]] || fail "Source volume identity changed during backup"
  log "pre_migration_backup=PASS"
  log "pre_migration_backup_size_bytes=${POSTGRES_DUMP_SIZE}"
  log "pre_migration_backup_sha256=${POSTGRES_DUMP_SHA256}"

  restore_suffix="$(printf '%s' "${CHECKPOINT_ID}-$$" | shasum -a 256 | cut -c1-12)"
  create_disposable_restore "${restore_suffix}"
  restore_pre_migration_backup
  log "backup_restore_verification=PASS"
  log "restored_source_revision=${RESTORE_ALEMBIC_REVISION}"

  build_current_migrator
  run_disposable_migration
  log "disposable_migration_revision=${DISPOSABLE_POST_REVISION}"
  log "disposable_migration_schema=PASS"
  log "disposable_migration_integrity=PASS"

  # Recheck the frozen source after all disposable work.  Only now may the
  # internal rehearsal gate become true.
  assert_source_frozen
  source_after_rehearsal_counts="${CHECKPOINT_DIR}/source-table-counts-after-rehearsal.tsv"
  capture_table_counts "${SOURCE_DB_CONTAINER}" "${source_after_rehearsal_counts}"
  compare_table_counts "${SOURCE_TABLE_COUNTS}" "${source_after_rehearsal_counts}" >/dev/null
  source_after_rehearsal_media_label="after-rehearsal"
  verify_source_media_unchanged "${source_after_rehearsal_media_label}"
  [[ "$(capture_source_volume_identity)" == "${SOURCE_VOLUME_IDENTITY_BEFORE}" ]] || fail "Source volume identity changed during rehearsal"
  DISPOSABLE_MIGRATION_REHEARSAL=1
  capture_checkpoint_marker "${CHECKPOINT_DIR}/DISPOSABLE_MIGRATION_REHEARSAL_PASS" \
    'source_backup=PASS' \
    'backup_restore=PASS' \
    'disposable_migration=PASS' \
    'disposable_target_revision=f41493d13761' \
    'disposable_integrity=PASS'
  log "DISPOSABLE_MIGRATION_REHEARSAL=PASS"

  migrate_source_and_verify
  log "source_migration=PASS"
  log "source_post_revision=${SOURCE_POST_REVISION}"
  log "source_post_integrity=PASS"
  log "source_media_unchanged=PASS"
  log "source_volume_identity=UNCHANGED"

  run_source_migrator_noop
  log "second_migrator=PASS"
  log "second_migrator_revision=${SOURCE_NOOP_REVISION}"

  cleanup_disposable_resources
  (( DISPOSABLE_CONTAINER_REMOVED == 1 )) || fail "Disposable restore container teardown was not confirmed"
  (( DISPOSABLE_VOLUME_REMOVED == 1 )) || fail "Disposable restore volume teardown was not confirmed"
  log "disposable_teardown=PASS"

  restore_source_runtime
  [[ "$(capture_source_volume_identity)" == "${SOURCE_VOLUME_IDENTITY_BEFORE}" ]] || fail "Source volume identity changed during runtime restoration"
  current_revision=""
  if service_was_running db "${CHECKPOINT_DIR}/source-running-services-before.txt"; then
    # The db was part of the original posture, so it must still be healthy.
    current_revision="$(read_alembic_revision "${SOURCE_DB_CONTAINER}")"
    [[ "${current_revision}" == "${TARGET_REVISION}" ]] || fail "Restored source db is not at the target revision"
  fi
  log "source_runtime_posture_restored=PASS"

  check_repository_unchanged "${CHECKPOINT_DIR}/git-status-after-proof.txt"
  write_success_manifest
  validate_checkpoint_permissions "${CHECKPOINT_DIR}"

  PROOF_SUCCEEDED=1
  log "retained_pre_migration_backup=PASS"
  log "checkpoint_id=${CHECKPOINT_ID}"
  log "PRIVATE_PREVIEW_DATABASE_MIGRATION_PROVEN"
}

create_disposable_restore() {
  local restore_suffix="$1"
  local restore_ports
  local restore_network_mode
  local restore_mount
  local restore_mount_count

  DISPOSABLE_VOLUME="codexify_private_preview_restore_${restore_suffix}"
  DISPOSABLE_CONTAINER="codexify-private-preview-restore-${restore_suffix}"
  DISPOSABLE_MIGRATOR_CONTAINER="codexify-private-preview-migration-disposable-${restore_suffix}"

  docker volume create \
    --label codexify.proof=private-preview-database-migration \
    --label "codexify.checkpoint=${CHECKPOINT_ID}" \
    "${DISPOSABLE_VOLUME}" >/dev/null
  docker run -d \
    --name "${DISPOSABLE_CONTAINER}" \
    --label codexify.proof=private-preview-database-migration \
    --label "codexify.checkpoint=${CHECKPOINT_ID}" \
    --network none \
    --mount "type=volume,source=${DISPOSABLE_VOLUME},target=/var/lib/postgresql/data" \
    -e POSTGRES_HOST_AUTH_METHOD=trust \
    -e "POSTGRES_DB=${RESTORE_DB_NAME}" \
    -e "POSTGRES_USER=${RESTORE_DB_USER}" \
    "${RESTORE_IMAGE}" >/dev/null
  wait_for_postgres "${DISPOSABLE_CONTAINER}"

  restore_ports="$(docker inspect "${DISPOSABLE_CONTAINER}" --format '{{json .HostConfig.PortBindings}}')"
  restore_network_mode="$(docker inspect "${DISPOSABLE_CONTAINER}" --format '{{.HostConfig.NetworkMode}}')"
  restore_mount="$(docker inspect "${DISPOSABLE_CONTAINER}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}')"
  restore_mount_count="$(docker inspect "${DISPOSABLE_CONTAINER}" --format '{{len .Mounts}}')"
  case "${restore_ports}" in
    "{}"|"null") ;;
    *) fail "Disposable restore container published a host port" ;;
  esac
  [[ "${restore_network_mode}" == "none" ]] || fail "Disposable restore container is not network-isolated"
  [[ "${restore_mount}" == "${DISPOSABLE_VOLUME}|true" ]] || fail "Disposable restore container does not use its proof volume"
  [[ "${restore_mount}" != "${SOURCE_VOLUME}|true" ]] || fail "Disposable restore reused the source volume"
  [[ "${restore_mount_count}" == "1" ]] || fail "Disposable restore container has an unexpected mount set"

  RESTORE_CONTAINER_PORTS="PASS"
  RESTORE_VOLUME_ISOLATION="PASS"
}

restore_pre_migration_backup() {
  local restore_log="${CHECKPOINT_DIR}/restore-verification.log"
  local restore_revision
  local restore_counts="${CHECKPOINT_DIR}/restore-table-counts.tsv"
  local restore_families="${CHECKPOINT_DIR}/restore-family-counts.tsv"
  local restore_integrity="${CHECKPOINT_DIR}/restore-integrity.tsv"

  if ! docker exec -i "${DISPOSABLE_CONTAINER}" sh -lc \
    'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    <"${POSTGRES_DUMP}" > /dev/null 2>"${restore_log}"; then
    chmod 600 "${restore_log}"
    fail "Pre-migration backup restore failed"
  fi
  chmod 600 "${restore_log}"

  restore_revision="$(read_alembic_revision "${DISPOSABLE_CONTAINER}")"
  [[ "${restore_revision}" == "${SOURCE_REVISION}" ]] || fail "Restored database revision is not the expected source revision"
  capture_table_counts "${DISPOSABLE_CONTAINER}" "${restore_counts}"
  require_expected_tables "${restore_counts}"
  compare_table_counts "${SOURCE_TABLE_COUNTS}" "${restore_counts}" >/dev/null
  capture_family_counts "${restore_counts}" "${restore_families}"
  run_integrity_checks "${DISPOSABLE_CONTAINER}" "${restore_integrity}"

  RESTORE_ALEMBIC_REVISION="${restore_revision}"
  RESTORE_TABLE_COUNTS_SHA256="$(sha256_file "${restore_counts}")"
  RESTORE_INTEGRITY_SHA256="$(sha256_file "${restore_integrity}")"
  BACKUP_RESTORE_VERIFIED=1
}

build_current_migrator() {
  local build_log="${CHECKPOINT_DIR}/migrator-image-build.log"
  if ! compose build migrator >"${build_log}" 2>&1; then
    chmod 600 "${build_log}"
    fail "Current repository migrator image build failed"
  fi
  chmod 600 "${build_log}"
  docker image inspect codexify-backend-runtime:latest >/dev/null || fail "Migrator image is unavailable after build"
  MIGRATOR_IMAGE_BUILT=1
}

run_disposable_migration() {
  local migration_log="${CHECKPOINT_DIR}/disposable-migrator.log"
  local restore_dsn="postgresql://${RESTORE_DB_USER}@127.0.0.1:5432/${RESTORE_DB_NAME}"
  local disposable_revision
  local post_counts="${CHECKPOINT_DIR}/disposable-post-migration-table-counts.tsv"
  local post_families="${CHECKPOINT_DIR}/disposable-post-migration-family-counts.tsv"
  local post_integrity="${CHECKPOINT_DIR}/disposable-post-migration-integrity.tsv"
  local schema_checks="${CHECKPOINT_DIR}/disposable-schema-checks.txt"
  local invariant_checks="${CHECKPOINT_DIR}/disposable-migration-invariants.tsv"

  if ! docker run --rm \
    --name "${DISPOSABLE_MIGRATOR_CONTAINER}" \
    --label codexify.proof=private-preview-database-migration \
    --label "codexify.checkpoint=${CHECKPOINT_ID}" \
    --network "container:${DISPOSABLE_CONTAINER}" \
    --entrypoint python \
    -e "DATABASE_URL=${restore_dsn}" \
    -e "GUARDIAN_DATABASE_URL=${restore_dsn}" \
    -e "GUARDIAN_DB_URL=${restore_dsn}" \
    -e "GUARDIAN_DB_DSN=${restore_dsn}" \
    -e "GUARDIAN_CHATLOG_DSN=${restore_dsn}" \
    -e "PGHOST=127.0.0.1" \
    -e "PGPORT=5432" \
    -e "PGUSER=${RESTORE_DB_USER}" \
    -e "PGDATABASE=${RESTORE_DB_NAME}" \
    -e "ALEMBIC_CONFIG=/app/backend/alembic.ini" \
    -e PYTHONPATH=/app \
    -e GUARDIAN_API_KEY=proof-only-not-a-credential \
    -e OPENAI_API_KEY=proof-only-not-a-credential \
    -e CODEXIFY_USE_OPENAI=0 \
    -e LLM_PROVIDER=local \
    -e EMBED_PROVIDER=local \
    -e EMBEDDER_PROVIDER=local \
    codexify-backend-runtime:latest \
    /app/backend/scripts/docker/run_migrator.py >"${migration_log}" 2>&1; then
    chmod 600 "${migration_log}"
    fail "Disposable canonical migrator failed"
  fi
  chmod 600 "${migration_log}"

  disposable_revision="$(read_alembic_revision "${DISPOSABLE_CONTAINER}")"
  [[ "${disposable_revision}" == "${TARGET_REVISION}" ]] || fail "Disposable migration did not reach the target revision"
  capture_table_counts "${DISPOSABLE_CONTAINER}" "${post_counts}"
  require_expected_tables "${post_counts}"
  compare_table_counts "${SOURCE_TABLE_COUNTS}" "${post_counts}" >/dev/null
  capture_family_counts "${post_counts}" "${post_families}"
  run_integrity_checks "${DISPOSABLE_CONTAINER}" "${post_integrity}"
  assert_schema_objects "${DISPOSABLE_CONTAINER}" "${schema_checks}"
  verify_migration_invariants "${DISPOSABLE_CONTAINER}" "${invariant_checks}"

  DISPOSABLE_POST_REVISION="${disposable_revision}"
  DISPOSABLE_POST_COUNTS_SHA256="$(sha256_file "${post_counts}")"
  DISPOSABLE_POST_INTEGRITY_SHA256="$(sha256_file "${post_integrity}")"
  DISPOSABLE_SCHEMA_CHECKS_SHA256="$(sha256_file "${schema_checks}")"
  DISPOSABLE_INVARIANTS_SHA256="$(sha256_file "${invariant_checks}")"
}

main "$@"
