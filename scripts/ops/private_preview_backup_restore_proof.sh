#!/usr/bin/env bash
set -euo pipefail

# Live, bounded Postgres + durable-media recovery proof for the private-preview
# Compose project. Backup artifacts are sensitive and remain outside Git.

SCRIPT_VERSION="1"
PROJECT_NAME="codexify_private_preview"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ENV_FILE="${PRIVATE_PREVIEW_ENV_FILE:-${REPO_ROOT}/.env.private-preview}"
BACKUP_ROOT_INPUT="${CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR:-}"
MEDIA_ROOT="${REPO_ROOT}/data/media"
IMPORT_ROOT="${REPO_ROOT}/data/imports"
SOURCE_VOLUME="${PROJECT_NAME}_pg_data"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
RESTORE_POSTGRES_USER="codexify_restore"
RESTORE_POSTGRES_DB="codexify_restore"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

COMPOSE=(
  docker compose
  --project-directory "${REPO_ROOT}"
  -p "${PROJECT_NAME}"
  --env-file "${ENV_FILE}"
  -f "${REPO_ROOT}/docker-compose.yml"
  -f "${REPO_ROOT}/docker-compose.private-preview.yml"
)

START_SERVICES=(
  backend
  frontend
  worker-chat
  worker-chat-embed
  worker-document-embed
  worker-warmup
  worker-account-import
  private-preview-origin
)

CHECKPOINT_DIR=""
CHECKPOINT_ID=""
RESTORE_CONTAINER=""
RESTORE_VOLUME=""
RESTORE_MEDIA_DIR=""
TEMP_CONFIG_JSON=""
TEMP_BASELINE_STATUS=""
SOURCE_FROZEN=0
SOURCE_RESTARTED=0
SOURCE_DB_CONTAINER_EXISTED_BEFORE=0
CHECKPOINT_HAS_BACKUP=0
RESTORE_CONTAINER_REMOVED=0
RESTORE_VOLUME_REMOVED=0
RESTORE_MEDIA_REMOVED=0
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

wait_for_postgres() {
  local container_name="$1"
  local waited=0
  while ! docker exec "${container_name}" sh -lc \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1'; do
    if (( waited >= 120 )); then
      fail "Postgres did not become ready within 120 seconds: ${container_name}"
      return 1
    fi
    sleep 2
    waited=$((waited + 2))
  done
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
  for expected_table in \
    users projects chat_threads chat_messages media_assets \
    uploaded_documents generated_documents uploaded_images generated_images; do
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
    rows.append(
        {
            "path": item.relative_to(root).as_posix(),
            "sha256": digest.hexdigest(),
        }
    )
with output.open("w", encoding="utf-8", newline="\n") as handle:
    for row in rows:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        handle.write("\n")
os.chmod(output, 0o600)
print(len(rows))
PY
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
        raise SystemExit(f"unsafe checkpoint permissions: {item.name} mode={oct(mode)}")
PY
}

cleanup_restore_resources() {
  if [[ -n "${RESTORE_CONTAINER}" ]]; then
    case "${RESTORE_CONTAINER}" in
      codexify-private-preview-restore-*) ;;
      *) fail "Refusing to remove unexpected restore-container name"; return 1 ;;
    esac
    if docker container inspect "${RESTORE_CONTAINER}" >/dev/null 2>&1; then
      docker rm -f "${RESTORE_CONTAINER}" >/dev/null
    fi
    if ! docker container inspect "${RESTORE_CONTAINER}" >/dev/null 2>&1; then
      RESTORE_CONTAINER_REMOVED=1
    fi
  fi

  if [[ -n "${RESTORE_VOLUME}" ]]; then
    case "${RESTORE_VOLUME}" in
      codexify_private_preview_restore_*) ;;
      *) fail "Refusing to remove unexpected restore-volume name"; return 1 ;;
    esac
    [[ "${RESTORE_VOLUME}" != "${SOURCE_VOLUME}" ]] || {
      fail "Refusing to remove the source Postgres volume"
      return 1
    }
    if docker volume inspect "${RESTORE_VOLUME}" >/dev/null 2>&1; then
      docker volume rm "${RESTORE_VOLUME}" >/dev/null
    fi
    if ! docker volume inspect "${RESTORE_VOLUME}" >/dev/null 2>&1; then
      RESTORE_VOLUME_REMOVED=1
    fi
  fi

  if [[ -n "${RESTORE_MEDIA_DIR}" && -d "${RESTORE_MEDIA_DIR}" ]]; then
    case "${RESTORE_MEDIA_DIR}" in
      "${TMPDIR:-/tmp}"/codexify-private-preview-media-restore.*)
        rm -rf -- "${RESTORE_MEDIA_DIR}"
        ;;
      *)
        fail "Refusing to remove unexpected restore-media path"
        return 1
        ;;
    esac
  fi
  if [[ -n "${RESTORE_MEDIA_DIR}" && ! -e "${RESTORE_MEDIA_DIR}" ]]; then
    RESTORE_MEDIA_REMOVED=1
  fi
}

restore_original_service_state() {
  local original_services_file="${CHECKPOINT_DIR}/source-running-services-before.txt"
  local original_service
  local proof_created_db_container
  compose stop >/dev/null 2>&1 || true
  if (( SOURCE_DB_CONTAINER_EXISTED_BEFORE == 0 )); then
    proof_created_db_container="$(compose ps -a -q db 2>/dev/null || true)"
    if [[ -n "${proof_created_db_container}" ]]; then
      docker rm "${proof_created_db_container}" >/dev/null 2>&1 || true
    fi
  fi
  if [[ -f "${original_services_file}" ]]; then
    while IFS= read -r original_service; do
      [[ -n "${original_service}" ]] || continue
      compose up -d --no-deps "${original_service}" >/dev/null 2>&1 || true
    done <"${original_services_file}"
  fi
}

on_exit() {
  local exit_code=$?
  set +e
  if (( RESTORE_CONTAINER_REMOVED == 0 || RESTORE_VOLUME_REMOVED == 0 || RESTORE_MEDIA_REMOVED == 0 )); then
    cleanup_restore_resources >/dev/null 2>&1
  fi
  if (( SOURCE_FROZEN == 1 && SOURCE_RESTARTED == 0 )); then
    restore_original_service_state
  fi
  if (( CHECKPOINT_HAS_BACKUP == 0 )) && [[ -n "${CHECKPOINT_DIR}" && -d "${CHECKPOINT_DIR}" ]]; then
    case "${CHECKPOINT_DIR}" in
      "${BACKUP_ROOT}"/private-preview-*)
        rm -rf -- "${CHECKPOINT_DIR}"
        CHECKPOINT_DIR=""
        CHECKPOINT_ID=""
        ;;
    esac
  elif (( CHECKPOINT_HAS_BACKUP == 1 && (exit_code != 0 || PROOF_SUCCEEDED == 0) )) \
    && [[ -n "${CHECKPOINT_DIR}" && -d "${CHECKPOINT_DIR}" ]]; then
    printf '%s\n' 'conclusion=PRIVATE_PREVIEW_BACKUP_RESTORE_FAILED' \
      >"${CHECKPOINT_DIR}/PROOF_FAILED"
    chmod 600 "${CHECKPOINT_DIR}/PROOF_FAILED"
  fi
  [[ -n "${TEMP_CONFIG_JSON}" ]] && rm -f -- "${TEMP_CONFIG_JSON}"
  [[ -n "${TEMP_BASELINE_STATUS}" ]] && rm -f -- "${TEMP_BASELINE_STATUS}"
  if (( exit_code != 0 || PROOF_SUCCEEDED == 0 )); then
    printf '%s\n' "PRIVATE_PREVIEW_BACKUP_RESTORE_FAILED" >&2
    if [[ -n "${CHECKPOINT_ID}" ]]; then
      printf 'checkpoint_id=%s\n' "${CHECKPOINT_ID}" >&2
    fi
  fi
  exit "${exit_code}"
}
trap on_exit EXIT INT TERM

[[ -n "${BACKUP_ROOT_INPUT}" ]] || fail "CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR is required"
[[ "${BACKUP_ROOT_INPUT}" = /* ]] || fail "Backup directory must be absolute"
[[ -f "${ENV_FILE}" ]] || fail "Private-preview env file is missing"
[[ -d "${MEDIA_ROOT}" ]] || fail "Durable media root is missing"
[[ -d "${IMPORT_ROOT}" ]] || fail "Private import staging root is missing"

umask 077
BACKUP_ROOT="$("${PYTHON_BIN}" - "${BACKUP_ROOT_INPUT}" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).resolve(strict=False))
PY
)"
case "${BACKUP_ROOT}/" in
  "${REPO_ROOT}/"*) fail "Backup directory resolves inside the repository" ;;
esac
case "${BACKUP_ROOT}" in
  /|/Volumes|/Volumes/Dev_SSD)
    fail "Backup directory resolves to an unsafe broad root"
    ;;
esac
mkdir -p -- "${BACKUP_ROOT}"
chmod 700 "${BACKUP_ROOT}"
[[ -w "${BACKUP_ROOT}" ]] || fail "Backup directory is not writable"

TEMP_CONFIG_JSON="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview-config.XXXXXX.json")"
TEMP_BASELINE_STATUS="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview-git-status.XXXXXX")"
chmod 600 "${TEMP_CONFIG_JSON}" "${TEMP_BASELINE_STATUS}"
git -C "${REPO_ROOT}" status --porcelain=v1 --untracked-files=all >"${TEMP_BASELINE_STATUS}"

compose config --format json >"${TEMP_CONFIG_JSON}"
"${PYTHON_BIN}" - "${TEMP_CONFIG_JSON}" <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
services = config.get("services", {})
for service_name in ("backend", "worker-chat", "worker-coding"):
    environment = services.get(service_name, {}).get("environment", {})
    write_enabled = str(environment.get("CODEXIFY_ENABLE_GRAPH_WRITES", "false")).strip().lower()
    backend = str(environment.get("CODEXIFY_GRAPH_BACKEND", "noop")).strip().lower()
    if write_enabled in {"1", "true", "yes", "on"} or backend != "noop":
        raise SystemExit(f"graph-write posture is enabled for {service_name}")

ports = []
for service_name, service in services.items():
    for port in service.get("ports") or []:
        ports.append(
            (
                service_name,
                str(port.get("host_ip") or ""),
                int(port["published"]),
                int(port["target"]),
            )
        )
if ports != [("private-preview-origin", "127.0.0.1", 8081, 8080)]:
    raise SystemExit("private-preview port topology does not match the bounded proof")
print("graph_write_gate=PASS")
print("preview_port_contract=PASS")
PY

if lsof -nP -iTCP:8081 -sTCP:LISTEN >/dev/null 2>&1; then
  current_origin_id="$(compose ps -q private-preview-origin 2>/dev/null || true)"
  [[ -n "${current_origin_id}" ]] || fail "Port 8081 is occupied outside the private-preview project"
fi

docker volume inspect "${SOURCE_VOLUME}" >/dev/null
SOURCE_VOLUME_IDENTITY_BEFORE="$(docker volume inspect "${SOURCE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}')"
if [[ -n "$(compose ps -a -q db 2>/dev/null || true)" ]]; then
  SOURCE_DB_CONTAINER_EXISTED_BEFORE=1
fi

CHECKPOINT_TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
SOURCE_GIT_COMMIT="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
CHECKPOINT_ID="private-preview-${CHECKPOINT_TIMESTAMP}-${SOURCE_GIT_COMMIT:0:12}"
CHECKPOINT_DIR="${BACKUP_ROOT}/${CHECKPOINT_ID}"
mkdir "${CHECKPOINT_DIR}"
chmod 700 "${CHECKPOINT_DIR}"

SOURCE_RUNNING_SERVICES="${CHECKPOINT_DIR}/source-running-services-before.txt"
compose ps --status running --services | LC_ALL=C sort >"${SOURCE_RUNNING_SERVICES}"
chmod 600 "${SOURCE_RUNNING_SERVICES}"
SOURCE_RUNNING_COUNT="$(wc -l <"${SOURCE_RUNNING_SERVICES}" | tr -d '[:space:]')"

log "checkpoint_created=PASS"
log "checkpoint_location=outside_repository"
log "source_running_service_count=${SOURCE_RUNNING_COUNT}"

compose stop
SOURCE_FROZEN=1
compose up -d --no-deps db
SOURCE_DB_CONTAINER="$(compose ps -q db)"
[[ -n "${SOURCE_DB_CONTAINER}" ]] || fail "Source db container was not created"
wait_for_postgres "${SOURCE_DB_CONTAINER}"

RUNNING_AFTER_FREEZE="$(compose ps --status running --services | LC_ALL=C sort)"
[[ "${RUNNING_AFTER_FREEZE}" == "db" ]] || fail "Application writers remain active after freeze"

SOURCE_DB_MOUNT="$(docker inspect "${SOURCE_DB_CONTAINER}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}')"
[[ "${SOURCE_DB_MOUNT}" == "${SOURCE_VOLUME}|true" ]] || fail "Source db is not mounted to the expected pg_data volume"

INCOMPLETE_IMPORT_COUNT="$(container_query "${SOURCE_DB_CONTAINER}" "
  SELECT count(*)
  FROM openai_account_import_jobs
  WHERE status IN ('receiving', 'queued', 'running');
")"
[[ "${INCOMPLETE_IMPORT_COUNT}" == "0" ]] || fail "An incomplete account-import job requires staging data"

IMPORT_STAGING_FILE_COUNT="$(find "${IMPORT_ROOT}" -type f -print0 | "${PYTHON_BIN}" -c 'import sys; print(sys.stdin.buffer.read().count(b"\0"))')"

SOURCE_ALEMBIC_FILE="${CHECKPOINT_DIR}/source-alembic-revision.txt"
container_query "${SOURCE_DB_CONTAINER}" "SELECT version_num FROM alembic_version ORDER BY version_num;" >"${SOURCE_ALEMBIC_FILE}"
chmod 600 "${SOURCE_ALEMBIC_FILE}"
SOURCE_ALEMBIC_REVISION="$(tr '\n' ',' <"${SOURCE_ALEMBIC_FILE}" | sed 's/,$//')"
REPO_ALEMBIC_REVISION="$("${PYTHON_BIN}" -m alembic -c "${REPO_ROOT}/backend/alembic.ini" heads | awk '{print $1}' | paste -sd, -)"
[[ "${SOURCE_ALEMBIC_REVISION}" == "${REPO_ALEMBIC_REVISION}" ]] || fail \
  "Source Alembic revision ${SOURCE_ALEMBIC_REVISION} differs from repository head ${REPO_ALEMBIC_REVISION}"

SOURCE_TABLE_COUNTS="${CHECKPOINT_DIR}/source-table-counts.tsv"
capture_table_counts "${SOURCE_DB_CONTAINER}" "${SOURCE_TABLE_COUNTS}"
require_expected_tables "${SOURCE_TABLE_COUNTS}"
SOURCE_TABLE_COUNT="$(wc -l <"${SOURCE_TABLE_COUNTS}" | tr -d '[:space:]')"

POSTGRES_DUMP="${CHECKPOINT_DIR}/postgres.dump"
docker exec "${SOURCE_DB_CONTAINER}" sh -lc \
  'exec pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  >"${POSTGRES_DUMP}"
chmod 600 "${POSTGRES_DUMP}"
[[ -s "${POSTGRES_DUMP}" ]] || fail "Postgres dump is empty"
CHECKPOINT_HAS_BACKUP=1
POSTGRES_DUMP_SHA256="$(sha256_file "${POSTGRES_DUMP}")"
POSTGRES_DUMP_SIZE="$(file_size_bytes "${POSTGRES_DUMP}")"

SOURCE_MEDIA_MANIFEST="${CHECKPOINT_DIR}/media-source-manifest.jsonl"
SOURCE_MEDIA_FILE_COUNT="$(capture_media_manifest "${MEDIA_ROOT}" "${SOURCE_MEDIA_MANIFEST}")"
SOURCE_MEDIA_MANIFEST_SHA256="$(sha256_file "${SOURCE_MEDIA_MANIFEST}")"
MEDIA_ARCHIVE="${CHECKPOINT_DIR}/media.tar"
tar -C "${MEDIA_ROOT}" -cf "${MEDIA_ARCHIVE}" .
chmod 600 "${MEDIA_ARCHIVE}"
MEDIA_ARCHIVE_SHA256="$(sha256_file "${MEDIA_ARCHIVE}")"
MEDIA_ARCHIVE_SIZE="$(file_size_bytes "${MEDIA_ARCHIVE}")"

RESTORE_SUFFIX="$(printf '%s' "${CHECKPOINT_TIMESTAMP}-${SOURCE_GIT_COMMIT}-$$" | shasum -a 256 | cut -c1-12)"
RESTORE_CONTAINER="codexify-private-preview-restore-${RESTORE_SUFFIX}"
RESTORE_VOLUME="codexify_private_preview_restore_${RESTORE_SUFFIX}"
[[ -n "${RESTORE_POSTGRES_USER}" ]] || fail "Restore Postgres user is empty"
[[ -n "${RESTORE_POSTGRES_DB}" ]] || fail "Restore Postgres database is empty"
docker volume create \
  --label codexify.proof=private-preview-backup-restore \
  --label "codexify.checkpoint=${CHECKPOINT_ID}" \
  "${RESTORE_VOLUME}" >/dev/null
docker run -d \
  --name "${RESTORE_CONTAINER}" \
  --label codexify.proof=private-preview-backup-restore \
  --label "codexify.checkpoint=${CHECKPOINT_ID}" \
  --network none \
  --mount "type=volume,source=${RESTORE_VOLUME},target=/var/lib/postgresql/data" \
  -e "POSTGRES_USER=${RESTORE_POSTGRES_USER}" \
  -e "POSTGRES_DB=${RESTORE_POSTGRES_DB}" \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  postgres:15 >/dev/null
wait_for_postgres "${RESTORE_CONTAINER}"

RESTORE_PORTS="$(docker inspect "${RESTORE_CONTAINER}" --format '{{json .HostConfig.PortBindings}}')"
RESTORE_NETWORK_MODE="$(docker inspect "${RESTORE_CONTAINER}" --format '{{.HostConfig.NetworkMode}}')"
RESTORE_DB_MOUNT="$(docker inspect "${RESTORE_CONTAINER}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}')"
[[ "${RESTORE_PORTS}" == "{}" || "${RESTORE_PORTS}" == "null" ]] || fail "Restore container published a host port"
[[ "${RESTORE_NETWORK_MODE}" == "none" ]] || fail "Restore container is not network-isolated"
[[ "${RESTORE_DB_MOUNT}" == "${RESTORE_VOLUME}|true" ]] || fail "Restore container does not use only its proof volume"
[[ "${RESTORE_DB_MOUNT}" != "${SOURCE_VOLUME}|true" ]] || fail "Restore container reused the source volume"

PG_RESTORE_LOG="${CHECKPOINT_DIR}/pg-restore.stderr.log"
docker exec -i "${RESTORE_CONTAINER}" sh -lc \
  'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  <"${POSTGRES_DUMP}" 2>"${PG_RESTORE_LOG}"
chmod 600 "${PG_RESTORE_LOG}"

RESTORE_ALEMBIC_FILE="${CHECKPOINT_DIR}/restore-alembic-revision.txt"
container_query "${RESTORE_CONTAINER}" "SELECT version_num FROM alembic_version ORDER BY version_num;" >"${RESTORE_ALEMBIC_FILE}"
chmod 600 "${RESTORE_ALEMBIC_FILE}"
cmp -s "${SOURCE_ALEMBIC_FILE}" "${RESTORE_ALEMBIC_FILE}" || fail "Restored Alembic revision differs"

RESTORE_TABLE_COUNTS="${CHECKPOINT_DIR}/restore-table-counts.tsv"
capture_table_counts "${RESTORE_CONTAINER}" "${RESTORE_TABLE_COUNTS}"
require_expected_tables "${RESTORE_TABLE_COUNTS}"
cmp -s "${SOURCE_TABLE_COUNTS}" "${RESTORE_TABLE_COUNTS}" || fail "Restored table counts differ"

RELATIONAL_CHECKS_FILE="${CHECKPOINT_DIR}/restore-relational-checks.tsv"
container_query "${RESTORE_CONTAINER}" "
  SELECT 'projects_users', count(*) FROM projects p LEFT JOIN users u ON u.id = p.user_id WHERE u.id IS NULL
  UNION ALL SELECT 'chat_threads_users', count(*) FROM chat_threads t LEFT JOIN users u ON u.id = t.user_id WHERE u.id IS NULL
  UNION ALL SELECT 'chat_threads_projects', count(*) FROM chat_threads t LEFT JOIN projects p ON p.id = t.project_id WHERE t.project_id IS NOT NULL AND p.id IS NULL
  UNION ALL SELECT 'chat_messages_threads', count(*) FROM chat_messages m LEFT JOIN chat_threads t ON t.id = m.thread_id WHERE t.id IS NULL
  UNION ALL SELECT 'chat_messages_users', count(*) FROM chat_messages m LEFT JOIN users u ON u.id = m.user_id WHERE u.id IS NULL
  UNION ALL SELECT 'media_assets_projects', count(*) FROM media_assets a LEFT JOIN projects p ON p.id = a.project_id WHERE p.id IS NULL
  UNION ALL SELECT 'media_assets_threads', count(*) FROM media_assets a LEFT JOIN chat_threads t ON t.id = a.thread_id WHERE a.thread_id IS NOT NULL AND t.id IS NULL
  UNION ALL SELECT 'uploaded_documents_users', count(*) FROM uploaded_documents d LEFT JOIN users u ON u.id = d.user_id WHERE u.id IS NULL
  UNION ALL SELECT 'uploaded_documents_projects', count(*) FROM uploaded_documents d LEFT JOIN projects p ON p.id = d.project_id WHERE d.project_id IS NOT NULL AND p.id IS NULL
  UNION ALL SELECT 'uploaded_documents_threads', count(*) FROM uploaded_documents d LEFT JOIN chat_threads t ON t.id = d.thread_id WHERE d.thread_id IS NOT NULL AND t.id IS NULL
  UNION ALL SELECT 'uploaded_documents_assets', count(*) FROM uploaded_documents d LEFT JOIN media_assets a ON a.id = d.asset_id WHERE d.asset_id IS NOT NULL AND a.id IS NULL
  UNION ALL SELECT 'generated_documents_projects', count(*) FROM generated_documents d LEFT JOIN projects p ON p.id = d.project_id WHERE p.id IS NULL
  UNION ALL SELECT 'generated_documents_threads', count(*) FROM generated_documents d LEFT JOIN chat_threads t ON t.id = d.thread_id WHERE d.thread_id IS NOT NULL AND t.id IS NULL
  UNION ALL SELECT 'uploaded_images_projects', count(*) FROM uploaded_images i LEFT JOIN projects p ON p.id = i.project_id WHERE p.id IS NULL
  UNION ALL SELECT 'uploaded_images_threads', count(*) FROM uploaded_images i LEFT JOIN chat_threads t ON t.id = i.thread_id WHERE i.thread_id IS NOT NULL AND t.id IS NULL
  UNION ALL SELECT 'uploaded_images_assets', count(*) FROM uploaded_images i LEFT JOIN media_assets a ON a.id = i.asset_id WHERE i.asset_id IS NOT NULL AND a.id IS NULL
  UNION ALL SELECT 'generated_images_projects', count(*) FROM generated_images i LEFT JOIN projects p ON p.id = i.project_id WHERE p.id IS NULL
  UNION ALL SELECT 'generated_images_threads', count(*) FROM generated_images i LEFT JOIN chat_threads t ON t.id = i.thread_id WHERE i.thread_id IS NOT NULL AND t.id IS NULL
  UNION ALL SELECT 'generated_images_assets', count(*) FROM generated_images i LEFT JOIN media_assets a ON a.id = i.asset_id WHERE i.asset_id IS NOT NULL AND a.id IS NULL
  UNION ALL SELECT 'unvalidated_foreign_keys', count(*) FROM pg_constraint WHERE contype = 'f' AND NOT convalidated
  ORDER BY 1;
" >"${RELATIONAL_CHECKS_FILE}"
chmod 600 "${RELATIONAL_CHECKS_FILE}"
awk -F '|' '$2 != 0 { exit 1 }' "${RELATIONAL_CHECKS_FILE}" || fail "Restored relational checks found orphaned rows"

RESTORE_MEDIA_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codexify-private-preview-media-restore.XXXXXX")"
chmod 700 "${RESTORE_MEDIA_DIR}"
tar -C "${RESTORE_MEDIA_DIR}" -xf "${MEDIA_ARCHIVE}"
RESTORE_MEDIA_MANIFEST="${CHECKPOINT_DIR}/media-restore-manifest.jsonl"
RESTORE_MEDIA_FILE_COUNT="$(capture_media_manifest "${RESTORE_MEDIA_DIR}" "${RESTORE_MEDIA_MANIFEST}")"
RESTORE_MEDIA_MANIFEST_SHA256="$(sha256_file "${RESTORE_MEDIA_MANIFEST}")"
[[ "${SOURCE_MEDIA_FILE_COUNT}" == "${RESTORE_MEDIA_FILE_COUNT}" ]] || fail "Restored media file count differs"
cmp -s "${SOURCE_MEDIA_MANIFEST}" "${RESTORE_MEDIA_MANIFEST}" || fail "Restored media file hashes differ"
[[ "${SOURCE_MEDIA_MANIFEST_SHA256}" == "${RESTORE_MEDIA_MANIFEST_SHA256}" ]] || fail "Restored media manifest digest differs"

SOURCE_TABLE_COUNTS_AFTER="${CHECKPOINT_DIR}/source-table-counts-after.tsv"
capture_table_counts "${SOURCE_DB_CONTAINER}" "${SOURCE_TABLE_COUNTS_AFTER}"
cmp -s "${SOURCE_TABLE_COUNTS}" "${SOURCE_TABLE_COUNTS_AFTER}" || fail "Source database changed during proof"

SOURCE_MEDIA_MANIFEST_AFTER="${CHECKPOINT_DIR}/media-source-manifest-after.jsonl"
SOURCE_MEDIA_FILE_COUNT_AFTER="$(capture_media_manifest "${MEDIA_ROOT}" "${SOURCE_MEDIA_MANIFEST_AFTER}")"
cmp -s "${SOURCE_MEDIA_MANIFEST}" "${SOURCE_MEDIA_MANIFEST_AFTER}" || fail "Source media changed during proof"
[[ "${SOURCE_MEDIA_FILE_COUNT}" == "${SOURCE_MEDIA_FILE_COUNT_AFTER}" ]] || fail "Source media file count changed"

docker volume inspect "${SOURCE_VOLUME}" >/dev/null
SOURCE_VOLUME_IDENTITY_AFTER="$(docker volume inspect "${SOURCE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}')"
[[ "${SOURCE_VOLUME_IDENTITY_BEFORE}" == "${SOURCE_VOLUME_IDENTITY_AFTER}" ]] || fail "Source pg_data volume identity changed"

CURRENT_GIT_STATUS="${CHECKPOINT_DIR}/git-status-after-proof.txt"
git -C "${REPO_ROOT}" status --porcelain=v1 --untracked-files=all >"${CURRENT_GIT_STATUS}"
chmod 600 "${CURRENT_GIT_STATUS}"
cmp -s "${TEMP_BASELINE_STATUS}" "${CURRENT_GIT_STATUS}" || fail "Repository state changed during live proof"

cleanup_restore_resources
(( RESTORE_CONTAINER_REMOVED == 1 )) || fail "Restore container teardown was not confirmed"
(( RESTORE_VOLUME_REMOVED == 1 )) || fail "Restore volume teardown was not confirmed"
(( RESTORE_MEDIA_REMOVED == 1 )) || fail "Restore media directory teardown was not confirmed"

compose up -d "${START_SERVICES[@]}"

SOURCE_DB_CONTAINER="$(compose ps -q db)"
SOURCE_BACKEND_CONTAINER="$(compose ps -q backend)"
[[ -n "${SOURCE_DB_CONTAINER}" && -n "${SOURCE_BACKEND_CONTAINER}" ]] || fail "Required source containers are missing after restart"
wait_for_postgres "${SOURCE_DB_CONTAINER}"

waited=0
while [[ "$(docker inspect "${SOURCE_BACKEND_CONTAINER}" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}')" != "healthy" ]]; do
  if (( waited >= 180 )); then
    fail "Backend did not become healthy within 180 seconds"
  fi
  sleep 3
  waited=$((waited + 3))
done

PRIVATE_PREVIEW_BASE_URL=http://127.0.0.1:8081 \
PRIVATE_PREVIEW_ENV_FILE="${ENV_FILE}" \
  bash "${REPO_ROOT}/scripts/private_preview_validate.sh" reachability

SOURCE_RESTARTED=1

SCRIPT_BLOB_SHA1="$(git -C "${REPO_ROOT}" hash-object "${BASH_SOURCE[0]}")"
TABLE_COUNTS_SHA256="$(sha256_file "${SOURCE_TABLE_COUNTS}")"
RELATIONAL_CHECKS_SHA256="$(sha256_file "${RELATIONAL_CHECKS_FILE}")"
MANIFEST_FILE="${CHECKPOINT_DIR}/checkpoint-manifest.txt"
cat >"${MANIFEST_FILE}" <<MANIFEST
manifest_version=1
checkpoint_timestamp=${CHECKPOINT_TIMESTAMP}
source_git_commit=${SOURCE_GIT_COMMIT}
compose_project=${PROJECT_NAME}
supported_profile=v1-whooshd-deepseek-web
source_volume_name=${SOURCE_VOLUME}
source_alembic_revision=${SOURCE_ALEMBIC_REVISION}
repository_alembic_revision=${REPO_ALEMBIC_REVISION}
postgres_dump_filename=postgres.dump
postgres_dump_sha256=${POSTGRES_DUMP_SHA256}
postgres_dump_size_bytes=${POSTGRES_DUMP_SIZE}
postgres_table_count=${SOURCE_TABLE_COUNT}
postgres_table_counts_sha256=${TABLE_COUNTS_SHA256}
media_archive_filename=media.tar
media_archive_sha256=${MEDIA_ARCHIVE_SHA256}
media_archive_size_bytes=${MEDIA_ARCHIVE_SIZE}
media_manifest_sha256=${SOURCE_MEDIA_MANIFEST_SHA256}
media_file_count=${SOURCE_MEDIA_FILE_COUNT}
import_staging_file_count=${IMPORT_STAGING_FILE_COUNT}
incomplete_import_job_count=${INCOMPLETE_IMPORT_COUNT}
relational_checks_sha256=${RELATIONAL_CHECKS_SHA256}
proof_script_version=${SCRIPT_VERSION}
proof_script_blob_sha1=${SCRIPT_BLOB_SHA1}
conclusion=PRIVATE_PREVIEW_BACKUP_RESTORE_PROVEN

[postgres_table_counts]
$(cat "${SOURCE_TABLE_COUNTS}")
MANIFEST
chmod 600 "${MANIFEST_FILE}"

find "${CHECKPOINT_DIR}" -type d -exec chmod 700 {} +
find "${CHECKPOINT_DIR}" -type f -exec chmod 600 {} +
validate_checkpoint_permissions "${CHECKPOINT_DIR}"

PROOF_SUCCEEDED=1
log "postgres_dump=PASS"
log "postgres_restore=PASS"
log "alembic_equality=PASS"
log "table_count_equality=PASS"
log "relational_integrity=PASS"
log "media_file_count=${SOURCE_MEDIA_FILE_COUNT}"
log "media_restore_equality=PASS"
log "source_volume_identity=UNCHANGED"
log "source_media_integrity=UNCHANGED"
log "disposable_container_removed=PASS"
log "disposable_volume_removed=PASS"
log "disposable_media_restore_removed=PASS"
log "preview_restart_reachability=PASS"
log "retained_checkpoint=PASS"
log "checkpoint_id=${CHECKPOINT_ID}"
log "postgres_dump_size_bytes=${POSTGRES_DUMP_SIZE}"
log "postgres_dump_sha256=${POSTGRES_DUMP_SHA256}"
log "media_archive_size_bytes=${MEDIA_ARCHIVE_SIZE}"
log "media_archive_sha256=${MEDIA_ARCHIVE_SHA256}"
log "media_manifest_sha256=${SOURCE_MEDIA_MANIFEST_SHA256}"
log "source_alembic_revision=${SOURCE_ALEMBIC_REVISION}"
log "source_public_table_count=${SOURCE_TABLE_COUNT}"
log "PRIVATE_PREVIEW_BACKUP_RESTORE_PROVEN"
