#!/usr/bin/env bash
set -euo pipefail

# Live, bounded Postgres + durable-media recovery proof for the private-preview
# Compose project. Backup artifacts are sensitive and remain outside Git.

SCRIPT_VERSION="3"
PROJECT_NAME="codexify_private_preview"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ENV_FILE="${PRIVATE_PREVIEW_ENV_FILE:-${REPO_ROOT}/.env.private-preview}"
BACKUP_ROOT_INPUT="${CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR:-}"
SOURCE_VOLUME="${PROJECT_NAME}_pg_data"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
RESTORE_POSTGRES_USER="codexify_restore"
RESTORE_POSTGRES_DB="codexify_restore"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

STATE_DIR="${HOME}/Library/Application Support/Codexify/private-preview"
RECONCILER_TARGET="gui/$(id -u)/com.resonant.codexify-private-preview"
TEMP_INVENTORY=""
ORIGINAL_INVENTORY=""
ORIGINAL_RUNNING_IDS=()
WRITER_IDS=()

CHECKPOINT_DIR=""
CHECKPOINT_ID=""
RESTORE_CONTAINER=""
RESTORE_VOLUME=""
RESTORE_CONTAINER_ID=""
RESTORE_VOLUME_IDENTITY=""
RESTORE_MEDIA_DIR=""
TEMP_CONFIG_JSON=""
TEMP_BASELINE_STATUS=""
SOURCE_FROZEN=0
SOURCE_RESTARTED=0
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
  printf '%s\n' "${sql}" | docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "${container_name}" sh -lc \
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
  printf '%s\n' "${generated_sql}" | docker exec -i -e PGOPTIONS='-c default_transaction_read_only=on' "${container_name}" sh -lc \
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

capture_membership_digest() {
  local container="$1"
  local destination="$2"
  # Only the digest persists. Stream row identities and selected provenance in deterministic order.
  container_query "${container}" "
    COPY (
      SELECT row FROM (
      SELECT jsonb_build_array('project', id, user_id, system_role)::text AS row
        FROM projects
      UNION ALL
      SELECT jsonb_build_array('thread', id, user_id, project_id, origin_system,
        metadata->'source_thread_id', metadata->'source_conversation_template_id',
        metadata->'source_gizmo_id', metadata->'source_gizmo_type',
        metadata->'openai_project_materialization')::text FROM chat_threads
      UNION ALL
      SELECT jsonb_build_array('message', id, thread_id, user_id)::text FROM chat_messages
      ) AS rows ORDER BY row COLLATE \"C\"
    ) TO STDOUT;
  " | shasum -a 256 | awk '{print $1}' >"${destination}"
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
      [[ -n "${RESTORE_CONTAINER_ID}" &&
        "$(docker container inspect --format '{{.Id}}|{{index .Config.Labels "codexify.checkpoint"}}' "${RESTORE_CONTAINER}")" == "${RESTORE_CONTAINER_ID}|${CHECKPOINT_ID}" ]] || {
        fail "Restore container identity mismatch; leaving it in place"
        return 1
      }
      docker rm -f "${RESTORE_CONTAINER_ID}" >/dev/null || return 1
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
      [[ -n "${RESTORE_VOLUME_IDENTITY}" &&
        "$(docker volume inspect "${RESTORE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}|{{.CreatedAt}}|{{index .Labels "codexify.checkpoint"}}')" == "${RESTORE_VOLUME_IDENTITY}" ]] || {
        fail "Restore volume identity mismatch; leaving it in place"
        return 1
      }
      docker volume rm "${RESTORE_VOLUME}" >/dev/null || return 1
    fi
    if ! docker volume inspect "${RESTORE_VOLUME}" >/dev/null 2>&1; then
      RESTORE_VOLUME_REMOVED=1
    fi
  fi

  if [[ -n "${RESTORE_MEDIA_DIR}" && -d "${RESTORE_MEDIA_DIR}" ]]; then
    case "${RESTORE_MEDIA_DIR}" in
      "${CHECKPOINT_DIR}"/media-restore.*)
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

capture_inventory() {
  local ids
  ids="$(docker ps -aq --no-trunc --filter "label=com.docker.compose.project=${PROJECT_NAME}")" || return 1
  [[ -n "${ids}" ]] || return 1
  # Docker IDs are whitespace-free. Project-wide enumeration includes stopped one-shots.
  docker inspect ${ids} | "${PYTHON_BIN}" -c '
import json, sys
rows = []
for c in json.load(sys.stdin):
    labels = c["Config"]["Labels"]
    h = c["HostConfig"]
    rows.append(dict(id=c["Id"], image=c["Image"], image_ref=c["Config"]["Image"],
        service=labels["com.docker.compose.service"], running=c["State"]["Running"],
        state=c["State"]["Status"], restart=h["RestartPolicy"], mounts=c["Mounts"],
        ports=h["PortBindings"], networks={k: v["NetworkID"] for k,v in c["NetworkSettings"]["Networks"].items()},
        config_files=labels["com.docker.compose.project.config_files"],
        workdir=labels["com.docker.compose.project.working_dir"],
        config_hash=labels["com.docker.compose.config-hash"]))
json.dump(sorted(rows, key=lambda r: r["id"]), sys.stdout, sort_keys=True, indent=2)
'
}

reconciler_quiet() {
  "${PYTHON_BIN}" - "${STATE_DIR}/enabled" "${RECONCILER_TARGET}" <<'PY_RECONCILER'
import os
import re
import subprocess
import sys

marker, target = sys.argv[1:]
if os.path.lexists(marker):
    sys.exit("Preview desired-up is enabled. Establish a reconciler maintenance window before proof")
try:
    result = subprocess.run(
        ["launchctl", "print", target], capture_output=True, text=True, timeout=5, check=True
    )
except subprocess.TimeoutExpired:
    sys.exit("Preview reconciler state check timed out")
except (OSError, subprocess.CalledProcessError):
    sys.exit("Cannot establish Preview reconciler state")

lines = result.stdout.splitlines()
if not lines or lines[0].strip() != target + " = {":
    sys.exit("Unrecognized Preview reconciler response")
states = re.findall(r"^\tstate = ([^\n]+)$", result.stdout, re.MULTILINE)
if re.search(r"^\s*pid\s*=", result.stdout, re.MULTILINE) or states == ["running"]:
    sys.exit("Preview reconciler is in flight")
if states not in (["not running"], ["waiting"]):
    sys.exit("Ambiguous Preview reconciler state")
if os.path.lexists(marker):
    sys.exit("Preview desired-up was enabled during the state check")
PY_RECONCILER
}

verify_serving_checkout() {
  local pin commit status
  pin="$(cat "${STATE_DIR}/serving-source")" || return 1
  [[ "${pin}" = /* ]] || { fail "Invalid serving pin"; return 1; }
  pin="$(cd "${pin}" && pwd -P)" || return 1
  commit="$(git -C "${pin}" rev-parse HEAD)" || return 1
  status="$(git -C "${pin}" status --porcelain --untracked-files=all -- guardian backend frontend config plugins docker docker-compose.yml docker-compose.private-preview.yml docker-compose.private-preview-serving.yml)" || return 1
  [[ "${pin}" == "${SERVING_ROOT}" && "${commit}" == "${SOURCE_GIT_COMMIT}" && -z "${status}" ]] ||
    { fail "Pinned serving source changed or has uncommitted executable files"; return 1; }
}

restore_original_service_state() {
  local id running state failed=0
  for id in "${ORIGINAL_RUNNING_IDS[@]}"; do
    state="$(docker inspect --format '{{.Id}} {{.State.Running}}' "${id}")" || {
      log "restore_missing_container=${id}" >&2
      failed=1
      continue
    }
    running="${state##* }"
    if [[ "${state% *}" != "${id}" ]]; then
      failed=1
    elif [[ "${running}" == false ]]; then
      if docker start "${id}" >/dev/null; then
        log "restored_container=${id}" >&2
      else
        failed=1
      fi
    fi
  done
  capture_inventory >"${CHECKPOINT_DIR}/service-inventory-after.json" || return 1
  cmp -s "${ORIGINAL_INVENTORY}" "${CHECKPOINT_DIR}/service-inventory-after.json" || failed=1
  (( failed == 0 )) || fail "Original inventory could not be restored exactly. Manual recovery required"
}

on_exit() {
  local exit_code=$?
  set +e
  if (( SOURCE_FROZEN == 1 && SOURCE_RESTARTED == 0 )); then
    if restore_original_service_state; then SOURCE_RESTARTED=1; else exit_code=1; fi
  fi
  if (( RESTORE_CONTAINER_REMOVED == 0 || RESTORE_VOLUME_REMOVED == 0 || RESTORE_MEDIA_REMOVED == 0 )); then
    cleanup_restore_resources || exit_code=1
  fi
  if (( SOURCE_FROZEN == 1 )); then
    if ! reconciler_quiet; then
      log "proof_exit_reconciler=unresolved; verify operator reconciliation state before closing maintenance" >&2
      exit_code=1
    fi
    log "proof_exit_restore_container_removed=${RESTORE_CONTAINER_REMOVED} volume_removed=${RESTORE_VOLUME_REMOVED} media_removed=${RESTORE_MEDIA_REMOVED}" >&2
  fi
  if (( CHECKPOINT_HAS_BACKUP == 0 && SOURCE_FROZEN == 0 )) && [[ -n "${CHECKPOINT_DIR}" && -d "${CHECKPOINT_DIR}" ]]; then
    case "${CHECKPOINT_DIR}" in
      "${BACKUP_ROOT}"/private-preview-*)
        rm -rf -- "${CHECKPOINT_DIR}"
        CHECKPOINT_DIR=""
        CHECKPOINT_ID=""
        ;;
    esac
  elif (( exit_code != 0 || PROOF_SUCCEEDED == 0 )) \
    && [[ -n "${CHECKPOINT_DIR}" && -d "${CHECKPOINT_DIR}" ]]; then
    printf '%s\n' 'conclusion=PRIVATE_PREVIEW_BACKUP_RESTORE_FAILED' \
      "source_counts_verified=${SOURCE_COUNTS_VERIFIED:-0}" \
      "source_identity_restored=${SOURCE_RESTARTED}" \
      "preview_health_verified=${PREVIEW_HEALTH_VERIFIED:-0}" \
      >"${CHECKPOINT_DIR}/PROOF_FAILED"
    chmod 600 "${CHECKPOINT_DIR}/PROOF_FAILED"
  fi
  [[ -n "${TEMP_INVENTORY}" ]] && rm -f -- "${TEMP_INVENTORY}"
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
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

[[ -n "${BACKUP_ROOT_INPUT}" ]] || fail "CODEXIFY_PRIVATE_PREVIEW_BACKUP_DIR is required"
[[ "${BACKUP_ROOT_INPUT}" = /* ]] || fail "Backup directory must be absolute"
[[ -f "${ENV_FILE}" ]] || fail "Private-preview env file is missing"

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

"${PYTHON_BIN}" -c 'import subprocess; subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=10, check=True)'
TEMP_INVENTORY="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview-inventory.XXXXXX")"
capture_inventory >"${TEMP_INVENTORY}"
[[ -r "${STATE_DIR}/serving-source" ]] || fail "Pinned serving-source file is missing"
SERVING_ROOT="$(cat "${STATE_DIR}/serving-source")"
[[ "${SERVING_ROOT}" = /* && "${SERVING_ROOT}" != "${REPO_ROOT}" ]] || fail "Expected an absolute pinned serving worktree"
SERVING_ROOT="$(cd "${SERVING_ROOT}" && pwd -P)"
[[ "${SERVING_ROOT}" != "${REPO_ROOT}" ]] || fail "Development checkout cannot serve the proof"
[[ -z "$(git -C "${SERVING_ROOT}" status --porcelain --untracked-files=no)" ]] || fail "Serving checkout has tracked changes"
SOURCE_GIT_COMMIT="$(git -C "${SERVING_ROOT}" rev-parse HEAD)"
verify_serving_checkout || exit 1
SERVING_TREE="$(git -C "${SERVING_ROOT}" rev-parse 'HEAD^{tree}')"
OVERLAYS=("${SERVING_ROOT}/docker-compose.yml" "${SERVING_ROOT}/docker-compose.private-preview.yml" "${SERVING_ROOT}/docker-compose.private-preview-serving.yml")
COMPOSE=(docker compose --project-directory "${REPO_ROOT}" --env-file "${ENV_FILE}" -p "${PROJECT_NAME}")
for overlay in "${OVERLAYS[@]}"; do
  [[ -f "${overlay}" ]] || fail "Missing serving Compose input"
  COMPOSE+=(-f "${overlay}")
done
export CODEXIFY_PRIVATE_PREVIEW_SOURCE_ROOT="${SERVING_ROOT}"
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

EXPECTED_OVERLAYS="$(IFS=,; printf '%s' "${OVERLAYS[*]}")"
SERVICE_HASHES="$(compose config --hash '*')"
verify_serving_inventory() {
  "${PYTHON_BIN}" - "$1" "${EXPECTED_OVERLAYS}" "${REPO_ROOT}" "${SERVING_ROOT}" "${SERVING_TREE:0:9}" "${SERVICE_HASHES}" "${TEMP_CONFIG_JSON}" <<'PY_INVENTORY'
import json, subprocess, sys

path, overlays, workdir, root, tree, hashes, config_path = sys.argv[1:]
effective = json.load(open(config_path))["services"]
rows = json.load(open(path))
config_hashes = dict(line.split() for line in hashes.splitlines())
by_service = {r["service"]: r for r in rows}
if len(by_service) != len(rows):
    sys.exit("Duplicate Preview service containers")
for r in rows:
    if r["state"] not in ("running", "exited", "created"):
        sys.exit("Unsupported container state")
    infrastructure = r["service"] in ("db", "neo4j", "redis")
    if r["running"] and (
        (not infrastructure and r["config_files"] != overlays)
        or r["workdir"] != workdir
        or r["config_hash"] != config_hashes.get(r["service"])
    ):
        sys.exit("Running container configuration does not match pinned Compose inputs")
for service in ("backend", "db", "private-preview-origin"):
    if service not in by_service or not by_service[service]["running"]:
        sys.exit("Required Preview service is not running")
backend, db, origin = (by_service[s] for s in ("backend", "db", "private-preview-origin"))
def host_path(path):
    return path.removeprefix("/host_mnt")

image_ids = {}
for r in rows:
    if not r["running"]:
        continue
    name = r["service"]
    config = effective[name]
    code_image = name == "backend" or r["image_ref"].startswith(
        ("codexify-backend-runtime:", "codexify-worker-coding-runtime:")
    )
    if code_image:
        expected = config.get("image", "")
        if not expected.endswith(":private-preview-tree-" + tree):
            sys.exit(f"{name}: serving overlay image {expected!r} disagrees with pinned checkout tree {tree}")
        if r["image_ref"] != expected:
            sys.exit(f"{name}: running image reference disagrees with serving overlay")
        if expected not in image_ids:
            try:
                image_ids[expected] = subprocess.check_output(
                    ["docker", "image", "inspect", "--format", "{{.Id}}", expected],
                    text=True, timeout=5
                ).strip()
            except (OSError, subprocess.SubprocessError):
                sys.exit(f"{name}: could not verify serving image ID")
        if r["image"] != image_ids[expected]:
            sys.exit(f"{name}: running image ID disagrees with serving overlay")
    actual = {m["Destination"]: m for m in r["mounts"] if m["Type"] == "bind"}
    for mount in config.get("volumes", []):
        if mount["type"] == "bind":
            live = actual.get(mount["target"], {})
            if (
                host_path(live.get("Source", "")) != mount["source"]
                or live.get("RW") != (not mount.get("read_only", False))
            ):
                sys.exit(f"{name}: live bind does not match effective Compose configuration")
if origin["ports"] != {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8081"}]}:
    sys.exit("Live origin port binding mismatch")
if any(r["ports"] for r in rows if r["running"] and r is not origin):
    sys.exit("Unexpected published Preview port")
mounts = {m["Destination"]: m for m in backend["mounts"]}
for name in ("guardian", "backend"):
    mount = mounts.get("/app/" + name, {})
    if mount.get("Source", "").removeprefix("/host_mnt") != root + "/" + name or mount.get("Type") != "bind":
        sys.exit("Backend mount does not match serving pin")
for name in ("media", "imports"):
    mount = mounts.get("/app/data/" + name, {})
    if mount.get("Type") != "bind" or not mount.get("RW"):
        sys.exit("Expected a writable durable data bind")
    print(mount["Source"].removeprefix("/host_mnt"))
print(db["id"])
print(backend["id"])
for r in sorted(rows, key=lambda r: (r["service"] not in ("db", "redis", "neo4j"), r["service"] != "backend", r["service"])):
    if r["running"]:
        print(r["id"])
PY_INVENTORY
}
INVENTORY_SELECTION="$(verify_serving_inventory "${TEMP_INVENTORY}")"
{
  IFS= read -r MEDIA_ROOT
  IFS= read -r IMPORT_ROOT
  IFS= read -r SOURCE_DB_CONTAINER
  IFS= read -r SOURCE_BACKEND_CONTAINER
  while IFS= read -r id; do
    ORIGINAL_RUNNING_IDS+=("${id}")
    if [[ "${id}" != "${SOURCE_DB_CONTAINER}" ]]; then
      WRITER_IDS+=("${id}")
    fi
  done
} <<<"${INVENTORY_SELECTION}"
[[ -d "${MEDIA_ROOT}" && -d "${IMPORT_ROOT}" ]] || fail "Live data binds are unavailable on host"
docker volume inspect "${SOURCE_VOLUME}" >/dev/null
SOURCE_VOLUME_IDENTITY_BEFORE="$(docker volume inspect "${SOURCE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}|{{.CreatedAt}}')"
SOURCE_DB_MOUNT="$(docker inspect "${SOURCE_DB_CONTAINER}" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}|{{.RW}}{{end}}{{end}}')"
[[ "${SOURCE_DB_MOUNT}" == "${SOURCE_VOLUME}|true" ]] || fail "Source db is not mounted to the expected pg_data volume"

POSTGRES_VERSION="$(container_query "${SOURCE_DB_CONTAINER}" 'SHOW server_version;')"
[[ "${POSTGRES_VERSION}" == 15.* ]] || fail "Restore image requires PostgreSQL 15"
LIVE_HEAD="$(container_query "${SOURCE_DB_CONTAINER}" 'SELECT version_num FROM alembic_version ORDER BY version_num;')"
REPO_ALEMBIC_REVISION="$(cd "${SERVING_ROOT}" && "${PYTHON_BIN}" -m alembic -c backend/alembic.ini heads | awk '{print $1}' | paste -sd, -)"
[[ -n "${LIVE_HEAD}" && "${LIVE_HEAD}" == "${REPO_ALEMBIC_REVISION}" ]] || fail "Live Alembic revision differs from serving source"
RESTORE_IMAGE="$(docker inspect "${SOURCE_DB_CONTAINER}" --format '{{.Image}}')"
[[ "${RESTORE_IMAGE}" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "Could not resolve the source PostgreSQL image"
docker image inspect "${RESTORE_IMAGE}" >/dev/null || fail "Source PostgreSQL image is unavailable locally"
DAEMON_MEMORY="$(docker info --format '{{.MemTotal}}')"
DB_BYTES="$(container_query "${SOURCE_DB_CONTAINER}" 'SELECT pg_database_size(current_database());')"
MEDIA_KIB="$("${PYTHON_BIN}" - "${MEDIA_ROOT}" <<'PY_CAPACITY'
import os, stat, sys
from pathlib import Path

total = 0
def fail(error):
    raise error

for root, dirs, files in os.walk(sys.argv[1], onerror=fail):
    for name in dirs + files:
        entry = (Path(root) / name).lstat()
        if not (stat.S_ISDIR(entry.st_mode) or stat.S_ISREG(entry.st_mode)):
            sys.exit("Unsupported entry in durable media")
        total += 4096 + entry.st_size
print((total + 1023) // 1024)
PY_CAPACITY
)"
HOST_KIB="$(df -Pk "${BACKUP_ROOT}" | awk 'END {print $4}')"
GUEST_KIB="$(docker exec "${SOURCE_DB_CONTAINER}" df -Pk /var/lib/postgresql/data | awk 'END {print $4}')"
GUEST_TOTAL_KIB="$(docker exec "${SOURCE_DB_CONTAINER}" df -Pk /var/lib/postgresql/data | awk 'END {print $2}')"
for capacity in "${DAEMON_MEMORY}" "${DB_BYTES}" "${MEDIA_KIB}" "${HOST_KIB}" "${GUEST_KIB}" "${GUEST_TOTAL_KIB}"; do
  [[ "${capacity}" =~ ^[0-9]+$ ]] || fail "Could not measure capacity"
done
log "postgres_version=${POSTGRES_VERSION} source_revision=${SOURCE_GIT_COMMIT} alembic=${LIVE_HEAD}"
log "host_free_kib=${HOST_KIB} guest_free_kib=${GUEST_KIB} guest_total_kib=${GUEST_TOTAL_KIB} daemon_memory_bytes=${DAEMON_MEMORY}"
log "database_bytes=${DB_BYTES} media_estimate_kib=${MEDIA_KIB}"
(( DAEMON_MEMORY >= 4 * 1024 * 1024 * 1024 )) || fail "Docker guest memory allocation below 4 GiB"
(( HOST_KIB > 2 * MEDIA_KIB + 3 * DB_BYTES / 1024 + 1048576 )) || fail "Insufficient host checkpoint capacity"
(( GUEST_KIB > 3 * DB_BYTES / 1024 + 1048576 )) || fail "Insufficient guest restore capacity"
curl -fsS --max-time 5 http://127.0.0.1:8081/ping >/dev/null
reconciler_quiet || exit 1
CHECKPOINT_TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
CHECKPOINT_ID="private-preview-${CHECKPOINT_TIMESTAMP}-${SOURCE_GIT_COMMIT:0:12}"
candidate_dir="${BACKUP_ROOT}/${CHECKPOINT_ID}"
mkdir "${candidate_dir}"
CHECKPOINT_DIR="${candidate_dir}"
ORIGINAL_INVENTORY="${CHECKPOINT_DIR}/service-inventory-before.json"
cp "${TEMP_INVENTORY}" "${ORIGINAL_INVENTORY}"
capture_inventory >"${CHECKPOINT_DIR}/service-inventory-pre-freeze.json"
cmp -s "${ORIGINAL_INVENTORY}" "${CHECKPOINT_DIR}/service-inventory-pre-freeze.json" || fail "Service inventory changed before freeze"
verify_serving_checkout || exit 1
[[ "$(compose config --hash '*')" == "${SERVICE_HASHES}" ]] || fail "Effective Compose configuration changed before freeze"
verify_serving_inventory "${CHECKPOINT_DIR}/service-inventory-pre-freeze.json" >/dev/null || exit 1
reconciler_quiet || exit 1
SOURCE_FROZEN=1
docker stop "${WRITER_IDS[@]}" >/dev/null

assert_quiesced() {
  local running
  reconciler_quiet || return 1
  running="$(docker ps -q --no-trunc --filter "label=com.docker.compose.project=${PROJECT_NAME}")" || return 1
  [[ "${running}" == "${SOURCE_DB_CONTAINER}" ]] || { fail "Application writers remain active"; return 1; }
  [[ "$(container_query "${SOURCE_DB_CONTAINER}" "SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend' AND pid <> pg_backend_pid();")" == 0 ]] || fail "Other PostgreSQL clients remain connected"
}
assert_quiesced

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
[[ "${SOURCE_ALEMBIC_REVISION}" == "${REPO_ALEMBIC_REVISION}" ]] || fail \
  "Source Alembic revision ${SOURCE_ALEMBIC_REVISION} differs from repository head ${REPO_ALEMBIC_REVISION}"

SOURCE_TABLE_COUNTS="${CHECKPOINT_DIR}/source-table-counts.tsv"
capture_table_counts "${SOURCE_DB_CONTAINER}" "${SOURCE_TABLE_COUNTS}"
require_expected_tables "${SOURCE_TABLE_COUNTS}"
capture_membership_digest "${SOURCE_DB_CONTAINER}" "${CHECKPOINT_DIR}/source-membership.sha256"
assert_quiesced
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
if docker container inspect "${RESTORE_CONTAINER}" >/dev/null 2>&1 ||
   docker volume inspect "${RESTORE_VOLUME}" >/dev/null 2>&1; then
  fail "Disposable resource name already exists"
fi
docker volume create \
  --label codexify.proof=private-preview-backup-restore \
  --label "codexify.checkpoint=${CHECKPOINT_ID}" \
  "${RESTORE_VOLUME}" >/dev/null
RESTORE_VOLUME_IDENTITY="$(docker volume inspect "${RESTORE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}|{{.CreatedAt}}|{{index .Labels "codexify.checkpoint"}}')"
[[ "${RESTORE_VOLUME_IDENTITY}" == *"|${CHECKPOINT_ID}" ]] || fail "Disposable volume label mismatch"
RESTORE_CONTAINER_ID="$(
docker run -d \
  --name "${RESTORE_CONTAINER}" \
  --label codexify.proof=private-preview-backup-restore \
  --label "codexify.checkpoint=${CHECKPOINT_ID}" \
  --network none \
  --mount "type=volume,source=${RESTORE_VOLUME},target=/var/lib/postgresql/data" \
  -e "POSTGRES_USER=${RESTORE_POSTGRES_USER}" \
  -e "POSTGRES_DB=${RESTORE_POSTGRES_DB}" \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  --pull never "${RESTORE_IMAGE}"
)"
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

capture_membership_digest "${RESTORE_CONTAINER}" "${CHECKPOINT_DIR}/restore-membership.sha256"
cmp -s "${CHECKPOINT_DIR}/source-membership.sha256" "${CHECKPOINT_DIR}/restore-membership.sha256" || fail "Restored membership or grouping provenance differs"

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

RESTORE_MEDIA_DIR="$(mktemp -d "${CHECKPOINT_DIR}/media-restore.XXXXXX")"
chmod 700 "${RESTORE_MEDIA_DIR}"
tar -C "${RESTORE_MEDIA_DIR}" -xf "${MEDIA_ARCHIVE}"
RESTORE_MEDIA_MANIFEST="${CHECKPOINT_DIR}/media-restore-manifest.jsonl"
RESTORE_MEDIA_FILE_COUNT="$(capture_media_manifest "${RESTORE_MEDIA_DIR}" "${RESTORE_MEDIA_MANIFEST}")"
RESTORE_MEDIA_MANIFEST_SHA256="$(sha256_file "${RESTORE_MEDIA_MANIFEST}")"
[[ "${SOURCE_MEDIA_FILE_COUNT}" == "${RESTORE_MEDIA_FILE_COUNT}" ]] || fail "Restored media file count differs"
cmp -s "${SOURCE_MEDIA_MANIFEST}" "${RESTORE_MEDIA_MANIFEST}" || fail "Restored media file hashes differ"
[[ "${SOURCE_MEDIA_MANIFEST_SHA256}" == "${RESTORE_MEDIA_MANIFEST_SHA256}" ]] || fail "Restored media manifest digest differs"

assert_quiesced
capture_membership_digest "${SOURCE_DB_CONTAINER}" "${CHECKPOINT_DIR}/source-membership-after.sha256"
cmp -s "${CHECKPOINT_DIR}/source-membership.sha256" "${CHECKPOINT_DIR}/source-membership-after.sha256" || fail "Source membership changed during proof"
SOURCE_TABLE_COUNTS_AFTER="${CHECKPOINT_DIR}/source-table-counts-after.tsv"
capture_table_counts "${SOURCE_DB_CONTAINER}" "${SOURCE_TABLE_COUNTS_AFTER}"
cmp -s "${SOURCE_TABLE_COUNTS}" "${SOURCE_TABLE_COUNTS_AFTER}" || fail "Source database changed during proof"

SOURCE_MEDIA_MANIFEST_AFTER="${CHECKPOINT_DIR}/media-source-manifest-after.jsonl"
SOURCE_MEDIA_FILE_COUNT_AFTER="$(capture_media_manifest "${MEDIA_ROOT}" "${SOURCE_MEDIA_MANIFEST_AFTER}")"
cmp -s "${SOURCE_MEDIA_MANIFEST}" "${SOURCE_MEDIA_MANIFEST_AFTER}" || fail "Source media changed during proof"
[[ "${SOURCE_MEDIA_FILE_COUNT}" == "${SOURCE_MEDIA_FILE_COUNT_AFTER}" ]] || fail "Source media file count changed"

docker volume inspect "${SOURCE_VOLUME}" >/dev/null
SOURCE_VOLUME_IDENTITY_AFTER="$(docker volume inspect "${SOURCE_VOLUME}" --format '{{.Name}}|{{.Mountpoint}}|{{.CreatedAt}}')"
[[ "${SOURCE_VOLUME_IDENTITY_BEFORE}" == "${SOURCE_VOLUME_IDENTITY_AFTER}" ]] || fail "Source pg_data volume identity changed"
SOURCE_COUNTS_VERIFIED=1

CURRENT_GIT_STATUS="${CHECKPOINT_DIR}/git-status-after-proof.txt"
git -C "${REPO_ROOT}" status --porcelain=v1 --untracked-files=all >"${CURRENT_GIT_STATUS}"
chmod 600 "${CURRENT_GIT_STATUS}"
cmp -s "${TEMP_BASELINE_STATUS}" "${CURRENT_GIT_STATUS}" || fail "Repository state changed during live proof"

cleanup_restore_resources
(( RESTORE_CONTAINER_REMOVED == 1 )) || fail "Restore container teardown was not confirmed"
(( RESTORE_VOLUME_REMOVED == 1 )) || fail "Restore volume teardown was not confirmed"
(( RESTORE_MEDIA_REMOVED == 1 )) || fail "Restore media directory teardown was not confirmed"

restore_original_service_state
SOURCE_RESTARTED=1
wait_for_postgres "${SOURCE_DB_CONTAINER}"

waited=0
while [[ "$(docker inspect "${SOURCE_BACKEND_CONTAINER}" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}')" != "healthy" ]]; do
  if (( waited >= 180 )); then
    fail "Backend did not become healthy within 180 seconds"
  fi
  sleep 3
  waited=$((waited + 3))
done

curl -fsS --max-time 5 http://127.0.0.1:8081/ping >/dev/null
capture_inventory >"${CHECKPOINT_DIR}/service-inventory-after.json"
cmp -s "${ORIGINAL_INVENTORY}" "${CHECKPOINT_DIR}/service-inventory-after.json" || fail "Service identity drift after recovery"
verify_serving_checkout || exit 1
reconciler_quiet || exit 1
PREVIEW_HEALTH_VERIFIED=1

SOURCE_RESTARTED=1

SCRIPT_BLOB_SHA1="$(git -C "${REPO_ROOT}" hash-object "${BASH_SOURCE[0]}")"
TABLE_COUNTS_SHA256="$(sha256_file "${SOURCE_TABLE_COUNTS}")"
RELATIONAL_CHECKS_SHA256="$(sha256_file "${RELATIONAL_CHECKS_FILE}")"
MANIFEST_FILE="${CHECKPOINT_DIR}/checkpoint-manifest.txt"
cat >"${MANIFEST_FILE}" <<MANIFEST
manifest_version=1
checkpoint_timestamp=${CHECKPOINT_TIMESTAMP}
source_git_commit=${SOURCE_GIT_COMMIT}
postgres_version=${POSTGRES_VERSION}
postgres_image_id=${RESTORE_IMAGE}
source_inventory_sha256=$(sha256_file "${ORIGINAL_INVENTORY}")
source_volume_identity=${SOURCE_VOLUME_IDENTITY_BEFORE}
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
membership_sha256=$(cat "${CHECKPOINT_DIR}/source-membership.sha256")
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
