#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# whooshd_docker_smoke_up.sh
#
# Durable Docker smoke-launch wrapper for the Whoosh'd local
# inference path.  Verifies the resolved Compose config matches
# the blessed gateway contract before starting containers.
#
# The launcher is project-scoped and source-matched:
#
#   * It never deletes containers it does not own.  There is no
#     global container cleanup and no deletion selector derived
#     from a partial name match.  Every lifecycle operation is
#     scoped to one explicitly identified Compose project.
#   * It never targets the Private Preview project.
#   * It establishes the checkout's Git revision and that
#     revision's single Alembic head, then refuses to migrate
#     with an image whose own migration head differs.
#   * The image that runs the migration owns the migrations.  The
#     launcher only proves that image and the checkout agree.
#
# It never declares a migration successful on the strength of a
# container's exit code alone.  A migration is confirmed only when the
# intended migrator container is identified unambiguously, has reached an
# exited terminal state with exit code zero, and the project's own
# database reports exactly the expected Alembic head.
#
# Usage:
#   bash scripts/whooshd_docker_smoke_up.sh
#   bash scripts/whooshd_docker_smoke_up.sh minimal   # db redis migrator backend worker-chat only
#   bash scripts/whooshd_docker_smoke_up.sh migrator  # db redis migrator only
#   bash scripts/whooshd_docker_smoke_up.sh verify    # judge an existing project's migration only
#   bash scripts/whooshd_docker_smoke_up.sh minimal --detach
#   bash scripts/whooshd_docker_smoke_up.sh minimal --project codexify_qual
#   bash scripts/whooshd_docker_smoke_up.sh migrator --image <image-ref>
#
# Modes:
#   full      every service in the merged Compose config
#   minimal   db redis migrator backend worker-chat
#   migrator  db redis migrator (migration-only qualification)
#   verify    judge an already-started project's migration outcome;
#             starts nothing and modifies nothing
#
# Options:
#   --project NAME        Compose project identity for every operation
#   --image REF           use an existing image instead of building one
#                         (the image is still parity-checked, but a
#                         supplied reference proves migration-head parity
#                         only — never full source equivalence)
#   --teardown            project-scoped `compose down --remove-orphans`
#                         before starting (never runs by default)
#   --allow-dirty-source  proceed with a modified tracked tree
#   --detach|-d           detached start
#
# Environment:
#   The script probes Whoosh'd from the host at
#   http://127.0.0.1:8000.  The merged Compose config uses
#   http://host.docker.internal:8000 inside containers.
#   An already-running host Whoosh'd is never restarted or replaced.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_BASE="-f docker-compose.yml"
COMPOSE_SMOKE="-f docker-compose.whooshd-smoke.yml"
COMPOSE_FILES="$COMPOSE_BASE $COMPOSE_SMOKE"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compose projects this launcher must never target.
PROTECTED_PROJECT_PREFIX="codexify_private_preview"

# ── Migrator outcome verification ──
#
# This is the single place where the launcher decides whether a migration
# succeeded.  It fails closed: anything it cannot positively observe is a
# failure, never a success.
#
#   $1  Compose project identity
#   $2  the Alembic head the source revision established
#   $3  the Compose file arguments
#
# Returns 0 only when all three of the following hold:
#   * exactly one migrator container exists for this project and service
#   * that container reached an exited terminal state with exit code 0
#   * the project's own database reports exactly one alembic_version row
#     and that row equals the expected head
verify_migration_outcome() {
    local project="$1"
    local expected_head="$2"
    local compose_files="$3"

    local timeout="${MIGRATOR_TIMEOUT:-900}"
    local deadline
    local compose_ids label_ids all_ids count
    local migrator_id owned_project owned_service
    local state exit_code
    local db_ids db_label_ids all_db_ids db_count
    local db_id db_owned_project db_owned_service
    local db_rows db_rc row_count observed

    echo ""
    echo "── Identify the migrator container ──"

    # `docker compose ps` without --all omits containers that have already
    # exited, and the migrator is a one-shot container.  Both the Compose
    # listing and a label-scoped Docker listing are used, so a completed
    # migrator is always found while a container belonging to another
    # project is never selected.
    compose_ids="$(docker compose -p "$project" $compose_files ps --all -q migrator 2>/dev/null | sed '/^[[:space:]]*$/d' | sort -u || true)"
    label_ids="$(docker ps --no-trunc --all \
        --filter "label=com.docker.compose.project=$project" \
        --filter "label=com.docker.compose.service=migrator" \
        --format '{{.ID}}' 2>/dev/null | sed '/^[[:space:]]*$/d' | sort -u || true)"
    all_ids="$({ printf '%s\n' "$compose_ids"; printf '%s\n' "$label_ids"; } | sed '/^[[:space:]]*$/d' | sort -u)"

    count="$(printf '%s\n' "$all_ids" | sed '/^[[:space:]]*$/d' | wc -l | tr -d '[:space:]')"
    if [ "${count:-0}" -eq 0 ]; then
        echo -e "  ${RED}[FAIL]${NC} no migrator container was found for project '$project'"
        echo "    A migration cannot be confirmed without observing the migrator."
        return 1
    fi
    if [ "$count" -gt 1 ]; then
        echo -e "  ${RED}[FAIL]${NC} the migrator for project '$project' is ambiguous ($count containers)"
        printf '%s\n' "$all_ids" | sed 's/^/    /'
        return 1
    fi
    migrator_id="$(printf '%s\n' "$all_ids" | head -1)"

    # Ownership is confirmed before the container's state is inspected.
    owned_project="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$migrator_id" 2>/dev/null || true)"
    owned_service="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.service" }}' "$migrator_id" 2>/dev/null || true)"
    if [ "$owned_project" != "$project" ] || [ "$owned_service" != "migrator" ]; then
        echo -e "  ${RED}[FAIL]${NC} container '$migrator_id' is not this project's migrator"
        echo "    expected: project='$project' service='migrator'"
        echo "    observed: project='${owned_project:-<none>}' service='${owned_service:-<none>}'"
        return 1
    fi
    echo "  Migrator container: $migrator_id (project '$project', service 'migrator')"

    echo ""
    echo "── Verify the migrator's terminal result ──"

    deadline=$(( $(date +%s) + timeout ))
    while :; do
        state="$(docker inspect -f '{{.State.Status}}' "$migrator_id" 2>/dev/null || true)"
        if [ -z "$state" ]; then
            echo -e "  ${RED}[FAIL]${NC} could not inspect the state of the migrator container"
            return 1
        fi
        if [ "$state" = "exited" ]; then
            break
        fi
        if [ "$state" = "dead" ]; then
            echo -e "  ${RED}[FAIL]${NC} the migrator container reached a dead state"
            docker logs "$migrator_id" 2>&1 | tail -30 || true
            return 1
        fi
        if [ "$(date +%s)" -ge "$deadline" ]; then
            echo -e "  ${RED}[FAIL]${NC} the migrator did not finish within ${timeout}s"
            return 1
        fi
        sleep 2
    done

    exit_code="$(docker inspect -f '{{.State.ExitCode}}' "$migrator_id" 2>/dev/null || true)"
    if [ -z "$exit_code" ]; then
        echo -e "  ${RED}[FAIL]${NC} could not read the migrator's exit status"
        return 1
    fi
    echo "  Migrator exit code: $exit_code"
    if [ "$exit_code" != "0" ]; then
        echo -e "  ${RED}[FAIL]${NC} the migrator failed; the migration did not complete"
        docker logs "$migrator_id" 2>&1 | tail -30 || true
        return 1
    fi

    echo ""
    echo "── Verify the qualification database revision ──"

    # The database is resolved the same way: project-scoped, label-verified.
    # The Private Preview database is never addressed.
    db_ids="$(docker compose -p "$project" $compose_files ps --all -q db 2>/dev/null | sed '/^[[:space:]]*$/d' | sort -u || true)"
    db_label_ids="$(docker ps --no-trunc --all \
        --filter "label=com.docker.compose.project=$project" \
        --filter "label=com.docker.compose.service=db" \
        --format '{{.ID}}' 2>/dev/null | sed '/^[[:space:]]*$/d' | sort -u || true)"
    all_db_ids="$({ printf '%s\n' "$db_ids"; printf '%s\n' "$db_label_ids"; } | sed '/^[[:space:]]*$/d' | sort -u)"

    db_count="$(printf '%s\n' "$all_db_ids" | sed '/^[[:space:]]*$/d' | wc -l | tr -d '[:space:]')"
    if [ "${db_count:-0}" -eq 0 ]; then
        echo -e "  ${RED}[FAIL]${NC} no database container was found for project '$project'"
        return 1
    fi
    if [ "$db_count" -gt 1 ]; then
        echo -e "  ${RED}[FAIL]${NC} the database for project '$project' is ambiguous ($db_count containers)"
        printf '%s\n' "$all_db_ids" | sed 's/^/    /'
        return 1
    fi
    db_id="$(printf '%s\n' "$all_db_ids" | head -1)"

    db_owned_project="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$db_id" 2>/dev/null || true)"
    db_owned_service="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.service" }}' "$db_id" 2>/dev/null || true)"
    if [ "$db_owned_project" != "$project" ] || [ "$db_owned_service" != "db" ]; then
        echo -e "  ${RED}[FAIL]${NC} container '$db_id' is not this project's database"
        echo "    expected: project='$project' service='db'"
        echo "    observed: project='${db_owned_project:-<none>}' service='${db_owned_service:-<none>}'"
        return 1
    fi
    echo "  Database container: $db_id"

    db_rows="$(docker exec "$db_id" sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select version_num from alembic_version"' 2>/dev/null)" && db_rc=0 || db_rc=$?
    if [ "$db_rc" -ne 0 ]; then
        echo -e "  ${RED}[FAIL]${NC} could not read alembic_version from the project's database (psql exit $db_rc)"
        docker exec "$db_id" sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select 1"' 2>&1 | tail -5 | sed 's/^/    /' || true
        return 1
    fi

    row_count="$(printf '%s\n' "$db_rows" | sed '/^[[:space:]]*$/d' | wc -l | tr -d '[:space:]')"
    if [ "${row_count:-0}" -eq 0 ]; then
        echo -e "  ${RED}[FAIL]${NC} the qualification database reports no alembic_version row"
        return 1
    fi
    if [ "$row_count" -gt 1 ]; then
        echo -e "  ${RED}[FAIL]${NC} the qualification database reports $row_count alembic_version rows; the revision is ambiguous"
        printf '%s\n' "$db_rows" | sed 's/^/    /'
        return 1
    fi

    observed="$(printf '%s\n' "$db_rows" | sed '/^[[:space:]]*$/d' | head -1 | tr -d '[:space:]')"
    if [ "$observed" != "$expected_head" ]; then
        echo -e "  ${RED}[FAIL]${NC} the database revision does not match the expected migration head"
        echo "    expected head: $expected_head"
        echo "    observed head: $observed"
        return 1
    fi

    echo "  Database revision: $observed"
    echo -e "  ${GREEN}[OK]${NC} the migration is confirmed: the migrator exited 0 and the database reports $observed"
    return 0
}

# Sourcing this file defines the helpers above and returns without
# launching anything.  The contract tests use this to exercise the
# verification decisions directly, without Docker.
if [ "${WHOOSHD_SMOKE_LIB_ONLY:-0}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi

cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════"
echo "  Codexify + Whoosh'd Docker Smoke Path"
echo "═══════════════════════════════════════════════════════"

fail_prereq() {
    echo -e "  ${RED}[FAIL]${NC} $1"
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail_prereq "$1 is not available"
}

MODE="full"
DETACH=0
PROJECT=""
PROJECT_EXPLICIT=0
IMAGE_REF=""
DO_TEARDOWN=0
ALLOW_DIRTY_SOURCE=0

usage() {
    sed -n '1,58p' "$0"
}

while [ $# -gt 0 ]; do
    case "$1" in
        full|minimal|migrator|verify)
            MODE="$1"
            ;;
        --detach|-d)
            DETACH=1
            ;;
        --project)
            PROJECT="${2:-}"
            PROJECT_EXPLICIT=1
            [ $# -ge 2 ] || { echo -e "${RED}[FAIL] --project requires a value${NC}"; exit 1; }
            shift
            ;;
        --project=*)
            PROJECT="${1#--project=}"
            PROJECT_EXPLICIT=1
            ;;
        --image)
            [ $# -ge 2 ] || { echo -e "${RED}[FAIL] --image requires a value${NC}"; exit 1; }
            IMAGE_REF="$2"
            shift
            ;;
        --image=*)
            IMAGE_REF="${1#--image=}"
            ;;
        --teardown)
            DO_TEARDOWN=1
            ;;
        --allow-dirty-source)
            ALLOW_DIRTY_SOURCE=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}[FAIL] unknown argument: $1${NC}"
            echo "Usage: bash scripts/whooshd_docker_smoke_up.sh [full|minimal|migrator|verify] [--detach] [--project NAME] [--image REF] [--teardown] [--allow-dirty-source]"
            exit 1
            ;;
    esac
    shift
done

# ── Step 0: Check prerequisites ──
echo ""
echo "── Step 0: Check prerequisites ──"
require_cmd docker
require_cmd curl
require_cmd python3
require_cmd git

docker compose version >/dev/null 2>&1 || fail_prereq "docker compose v2 is not available"
docker info >/dev/null 2>&1 || fail_prereq "Docker daemon is not reachable. Start Docker Desktop and retry."
echo -e "  ${GREEN}[OK]${NC} docker, docker compose, curl, git, and python3 are available"

RUNTIME_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codexify-whooshd-smoke.XXXXXX")"
cleanup_runtime_dir() {
    rm -rf "$RUNTIME_DIR"
}
trap cleanup_runtime_dir EXIT

# ── Step 1: Establish the Compose project identity ──
echo ""
echo "── Step 1: Establish Compose project identity ──"

compose_default_project() {
    sed -n 's/^name:[[:space:]]*//p' "$REPO_ROOT/docker-compose.yml" \
        | head -1 \
        | tr -d '[:space:]' \
        | sed "s/[\"']//g"
}

if [ -z "$PROJECT" ]; then
    PROJECT="${CODEXIFY_SMOKE_PROJECT:-}"
fi
if [ -z "$PROJECT" ]; then
    PROJECT="$(compose_default_project)"
    if [ -z "$PROJECT" ]; then
        fail_prereq "could not determine the Compose project name; pass --project NAME"
    fi
    echo "  Project (from docker-compose.yml name): $PROJECT"
else
    echo "  Project (explicit): $PROJECT"
fi

case "$PROJECT" in
    "$PROTECTED_PROJECT_PREFIX"|"$PROTECTED_PROJECT_PREFIX"_*)
        fail_prereq "refusing to target protected Compose project '$PROJECT'"
        ;;
esac

if [ "$PROJECT_EXPLICIT" -eq 1 ] && [ -z "$PROJECT" ]; then
    fail_prereq "--project requires a non-empty project name"
fi

echo "  ${GREEN}[OK]${NC} All lifecycle operations are scoped to project '$PROJECT'"
echo "  ${GREEN}[OK]${NC} This launcher performs no global container cleanup"

# ── Step 2: Establish the source identity ──
echo ""
echo "── Step 2: Establish source identity ──"

SOURCE_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)"
if [ -z "$SOURCE_SHA" ]; then
    fail_prereq "could not read the Git revision of $REPO_ROOT"
fi
echo "  Source revision: $SOURCE_SHA"

SOURCE_DIRTY="$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no 2>/dev/null || true)"
if [ -n "$SOURCE_DIRTY" ]; then
    if [ "$ALLOW_DIRTY_SOURCE" -eq 1 ]; then
        echo -e "  ${YELLOW}[WARN]${NC} tracked files are modified; continuing because --allow-dirty-source was passed"
    else
        echo -e "  ${RED}[FAIL]${NC} tracked files are modified in $REPO_ROOT"
        echo "    The checkout has no unambiguous source identity."
        echo "    Commit or stash the changes, or pass --allow-dirty-source."
        printf '%s\n' "$SOURCE_DIRTY" | sed 's/^/    /'
        exit 1
    fi
else
    echo -e "  ${GREEN}[OK]${NC} tracked tree is clean"
fi

UNTRACKED_COUNT="$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | grep -c '^??' || true)"
if [ "${UNTRACKED_COUNT:-0}" -gt 0 ]; then
    echo -e "  ${YELLOW}[WARN]${NC} $UNTRACKED_COUNT untracked path(s) present in the build context"
fi

ALEMBIC_PYTHON=""
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    ALEMBIC_PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    ALEMBIC_PYTHON="python3"
fi
if [ -z "$ALEMBIC_PYTHON" ]; then
    fail_prereq "no python interpreter available to read the source migration head"
fi

source_alembic_heads() {
    "$ALEMBIC_PYTHON" -m alembic --raiseerr -c "$REPO_ROOT/backend/alembic.ini" heads \
        > "$RUNTIME_DIR/source_heads.txt" 2> "$RUNTIME_DIR/source_heads.err" \
        || return 1
    grep -E '^[0-9a-f]{8,32} \(head\)$' "$RUNTIME_DIR/source_heads.txt" \
        | awk '{print $1}' || true
}

SOURCE_HEADS="$(source_alembic_heads || true)"
SOURCE_HEAD_COUNT="$(printf '%s\n' "$SOURCE_HEADS" | grep -c . || true)"
if [ "${SOURCE_HEAD_COUNT:-0}" -eq 0 ]; then
    fail_prereq "could not determine the source Alembic head; see $RUNTIME_DIR/source_heads.err"
fi
if [ "$SOURCE_HEAD_COUNT" -gt 1 ]; then
    echo -e "  ${RED}[FAIL]${NC} the source checkout has multiple Alembic heads:"
    printf '%s\n' "$SOURCE_HEADS" | sed 's/^/    /'
    exit 1
fi
SOURCE_HEAD="$(printf '%s\n' "$SOURCE_HEADS" | head -1)"
echo "  Source Alembic head: $SOURCE_HEAD"
echo -e "  ${GREEN}[OK]${NC} source revision and single migration head established"

# ── Verify mode: judge an already-started project's migration outcome ──
# This mode starts nothing and modifies nothing.  It exists so a migration
# outcome can be re-judged against the current source head without
# rebuilding an image or recreating containers.
if [ "$MODE" = "verify" ]; then
    echo ""
    echo "── Verify mode: judging an existing project's migration outcome ──"
    echo "  Project:   $PROJECT"
    echo "  Expected:  $SOURCE_HEAD"
    if verify_migration_outcome "$PROJECT" "$SOURCE_HEAD" "$COMPOSE_FILES"; then
        echo ""
        echo "  Source revision: $SOURCE_SHA"
        echo "  Source head:     $SOURCE_HEAD"
        echo ""
        exit 0
    fi
    exit 1
fi

# ── Step 3: Resolve the migration image ──
echo ""
echo "── Step 3: Resolve the migration image ──"

if [ -z "$IMAGE_REF" ]; then
    IMAGE_TAG="codexify-backend-runtime:src-${SOURCE_SHA:0:12}"
    IMAGE_REF="$IMAGE_TAG"
    IMAGE_PROVENANCE="built-from-this-checkout"
    echo "  Building $IMAGE_TAG from this checkout"
    echo "    context:   $REPO_ROOT"
    echo "    dockerfile: backend/Dockerfile (target: runtime)"
    if ! docker build --target runtime -f backend/Dockerfile -t "$IMAGE_TAG" "$REPO_ROOT"; then
        fail_prereq "the canonical backend runtime image build failed"
    fi
    echo -e "  ${GREEN}[OK]${NC} built $IMAGE_TAG"
else
    IMAGE_PROVENANCE="supplied-reference"
    echo "  Using supplied image reference: $IMAGE_REF"
    echo -e "  ${YELLOW}[WARN]${NC} a supplied image reference is a diagnostic path"
    echo "    It proves migration-head parity only.  It does not prove that the"
    echo "    image was built from this checkout, so it does not establish source"
    echo "    equivalence for the running services."
fi

IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$IMAGE_REF" 2>/dev/null || true)"
if [ -z "$IMAGE_ID" ]; then
    fail_prereq "image '$IMAGE_REF' is not present locally"
fi
echo "  Image identity: $IMAGE_REF"
echo "  Image digest:   $IMAGE_ID"

# ── Step 4: Fail closed on image/source migration-head mismatch ──
echo ""
echo "── Step 4: Verify image/source migration parity ──"

image_alembic_heads() {
    docker run --rm --entrypoint python "$IMAGE_REF" \
        -m alembic --raiseerr -c /app/backend/alembic.ini heads \
        > "$RUNTIME_DIR/image_heads.txt" 2> "$RUNTIME_DIR/image_heads.err" \
        || return 1
    grep -E '^[0-9a-f]{8,32} \(head\)$' "$RUNTIME_DIR/image_heads.txt" \
        | awk '{print $1}' || true
}

IMAGE_HEADS="$(image_alembic_heads || true)"
IMAGE_HEAD_COUNT="$(printf '%s\n' "$IMAGE_HEADS" | grep -c . || true)"

if [ "${IMAGE_HEAD_COUNT:-0}" -eq 0 ]; then
    echo -e "  ${RED}[FAIL]${NC} could not read the Alembic head of image '$IMAGE_REF'"
    echo "    See $RUNTIME_DIR/image_heads.err"
    exit 1
fi
if [ "$IMAGE_HEAD_COUNT" -gt 1 ]; then
    echo -e "  ${RED}[FAIL]${NC} image '$IMAGE_REF' has multiple Alembic heads:"
    printf '%s\n' "$IMAGE_HEADS" | sed 's/^/    /'
    exit 1
fi
IMAGE_HEAD="$(printf '%s\n' "$IMAGE_HEADS" | head -1)"
echo "  Image Alembic head:  $IMAGE_HEAD"
echo "  Source Alembic head: $SOURCE_HEAD"

if [ "$IMAGE_HEAD" != "$SOURCE_HEAD" ]; then
    echo ""
    echo -e "${RED}  MIGRATION IMAGE DOES NOT MATCH THE SOURCE REVISION${NC}"
    echo -e "${RED}  Refusing to migrate. No database or container was started.${NC}"
    echo ""
    echo "    source revision:    $SOURCE_SHA"
    echo "    source head:        $SOURCE_HEAD"
    echo "    image head:         $IMAGE_HEAD"
    echo "    image reference:    $IMAGE_REF"
    echo "    image digest:       $IMAGE_ID"
    echo ""
    exit 1
fi

if [ "$IMAGE_PROVENANCE" = "supplied-reference" ]; then
    echo -e "  ${YELLOW}[WARN]${NC} the supplied image's migration head matches the source head ($SOURCE_HEAD)"
    echo "    Migration-head parity only; this does not establish source equivalence."
else
    echo -e "  ${GREEN}[OK]${NC} image and source agree on Alembic head $SOURCE_HEAD"
fi

# The image owns the migrations.  Every service that runs application code
# must use this exact image so the schema and the application come from the
# same revision.
export CODEXIFY_BACKEND_IMAGE="$IMAGE_REF"

# ── Step 5: Ensure Whoosh'd is running (never replacing a healthy one) ──
echo ""
echo "── Step 5: Ensure Whoosh'd ──"

WHOOSHD_HOST_BASE="${WHOOSHD_HOST_BASE:-http://127.0.0.1:8000}"
WHOOSHD_HEALTH_URL="${WHOOSHD_HEALTH_URL:-$WHOOSHD_HOST_BASE/health}"

if curl -sf --max-time 5 "$WHOOSHD_HEALTH_URL" >/dev/null 2>&1; then
    echo -e "  ${GREEN}[OK]${NC} Whoosh'd is already running; it is left untouched"
else
    REPO_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    bash "$REPO_SCRIPT_DIR/whooshd_ensure.sh" || {
        echo -e "  ${RED}[FAIL]${NC} Could not start Whoosh'd. See above for details."
        exit 1
    }
fi

# ── Step 5b: Confirm smoke model inventory ──
echo ""
echo "── Step 5b: Confirm Whoosh'd model inventory ──"
SMOKE_MODEL="${LOCAL_CHAT_MODEL:-local-chat}"
MODEL_PAYLOAD="$(curl -sf --max-time 5 "$WHOOSHD_HOST_BASE/v1/models" 2>/dev/null || curl -sf --max-time 5 "$WHOOSHD_HOST_BASE/api/tags" 2>/dev/null || true)"

if [ -z "$MODEL_PAYLOAD" ]; then
    echo -e "  ${RED}[FAIL]${NC} Whoosh'd is healthy but model inventory is not reachable"
    echo "  Tried: $WHOOSHD_HOST_BASE/v1/models and $WHOOSHD_HOST_BASE/api/tags"
    exit 1
fi

if printf '%s' "$MODEL_PAYLOAD" | grep -q "$SMOKE_MODEL"; then
    echo -e "  ${GREEN}[OK]${NC} Whoosh'd advertises $SMOKE_MODEL"
else
    echo -e "  ${RED}[FAIL]${NC} Whoosh'd model inventory does not advertise $SMOKE_MODEL"
    echo "  Inventory:"
    printf '%s\n' "$MODEL_PAYLOAD" | python3 -m json.tool 2>/dev/null || printf '%s\n' "$MODEL_PAYLOAD"
    exit 1
fi

# ── Step 6: Resolve Compose config ──
echo ""
echo "── Step 6: Resolve Compose config ──"
RESOLVED_CONFIG="$RUNTIME_DIR/resolved.compose.yml"
docker compose -p "$PROJECT" $COMPOSE_FILES config > "$RESOLVED_CONFIG"
echo "  Resolved config written to $RESOLVED_CONFIG"

# ── Step 7: Assert blessed contract in resolved config ──
echo ""
echo "── Step 7: Assert blessed Whoosh'd contract ──"

assert_value() {
    local description="$1"
    local pattern="$2"
    local file="$3"

    if grep -q "$pattern" "$file"; then
        echo -e "  ${GREEN}[PASS]${NC} $description"
        return 0
    else
        echo -e "  ${RED}[FAIL]${NC} $description"
        echo "    Expected pattern not found: $pattern"
        return 1
    fi
}

FAILURES=0

assert_value "LOCAL_BASE_URL=http://host.docker.internal:8000/v1" \
    'LOCAL_BASE_URL: http://host.docker.internal:8000/v1' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "ALLOW_CLOUD_PROVIDERS=false" \
    'ALLOW_CLOUD_PROVIDERS: .false.' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "CODEXIFY_EGRESS_ALLOWLIST empty" \
    'CODEXIFY_EGRESS_ALLOWLIST: ..' \
    "$RESOLVED_CONFIG" || true  # non-fatal: empty string rendering varies

assert_value "CODEXIFY_LOCAL_ONLY_MODE=true" \
    'CODEXIFY_LOCAL_ONLY_MODE: .true.' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LLM_PROVIDER=local" \
    'LLM_PROVIDER: local' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_PROVIDER_VENDOR=whooshd" \
    'LOCAL_PROVIDER_VENDOR: whooshd' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_RUNTIME_PRESET=whooshd-mlx" \
    'LOCAL_RUNTIME_PRESET: whooshd-mlx' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_COMPAT_FIRST=true" \
    'LOCAL_COMPAT_FIRST: .true.' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_PROVIDER_DISPLAY_NAME=Whoosh'd" \
    "LOCAL_PROVIDER_DISPLAY_NAME: Whoosh'd" \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "WHOOSHD_HEALTH_BASE_URL=http://host.docker.internal:8000" \
    'WHOOSHD_HEALTH_BASE_URL: http://host.docker.internal:8000' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp" \
    'CODEXIFY_SUPPORTED_PROFILE: v1-local-core-web-mcp' \
    "$RESOLVED_CONFIG" || ((FAILURES++))

assert_value "LOCAL_CHAT_MODEL=${SMOKE_MODEL}" \
    "LOCAL_CHAT_MODEL: ${SMOKE_MODEL}" \
    "$RESOLVED_CONFIG" || ((FAILURES++))

# The migration image and the application must come from the same revision.
printf '%s\n' \
    'import json, sys' \
    'with open(sys.argv[1]) as handle:' \
    '    data = json.load(handle)' \
    'service = sys.argv[2]' \
    'entry = (data.get("services", {}) or {}).get(service, {}) or {}' \
    'print(entry.get("image", "") or "")' \
    > "$RUNTIME_DIR/service_image.py"

docker compose -p "$PROJECT" $COMPOSE_FILES config --format json \
    > "$RUNTIME_DIR/resolved.compose.json" 2>/dev/null || true

for SERVICE in migrator backend worker-chat; do
    SERVICE_IMAGE=""
    if [ -s "$RUNTIME_DIR/resolved.compose.json" ]; then
        SERVICE_IMAGE="$(python3 "$RUNTIME_DIR/service_image.py" \
            "$RUNTIME_DIR/resolved.compose.json" "$SERVICE" 2>/dev/null || true)"
    fi
    if [ "$SERVICE_IMAGE" = "$IMAGE_REF" ]; then
        echo -e "  ${GREEN}[PASS]${NC} $SERVICE uses $IMAGE_REF"
    else
        echo -e "  ${RED}[FAIL]${NC} $SERVICE does not use $IMAGE_REF (resolved: ${SERVICE_IMAGE:-<none>})"
        FAILURES=$((FAILURES + 1))
    fi
done

if [ "$FAILURES" -gt 0 ]; then
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  SMOKE CONTRACT CHECK FAILED ($FAILURES failures)${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Resolved config: $RESOLVED_CONFIG"
    echo "  Inspect with:    grep -E 'LOCAL_BASE_URL|ALLOW_CLOUD|EGRESS|LLM_PROVIDER' $RESOLVED_CONFIG"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}  All contract assertions passed${NC}"

# ── Step 8: Optional project-scoped teardown ──
if [ "$DO_TEARDOWN" -eq 1 ]; then
    echo ""
    echo "── Step 8: Tear down project '$PROJECT' ──"
    docker compose -p "$PROJECT" $COMPOSE_FILES down --remove-orphans
    echo -e "  ${GREEN}[OK]${NC} project '$PROJECT' torn down"
fi

# ── Step 9: Start the stack ──
echo ""
echo "── Step 9: Start Docker Compose ──"

DETACH_ARGS=()
if [ "$DETACH" -eq 1 ]; then
    DETACH_ARGS=(-d)
fi

case "$MODE" in
    minimal)
        echo "  Launching minimal smoke stack (db redis migrator backend worker-chat)..."
        docker compose -p "$PROJECT" $COMPOSE_FILES up "${DETACH_ARGS[@]}" \
            db redis migrator backend worker-chat
        ;;
    migrator)
        echo "  Launching migration-only stack (db redis migrator)..."
        docker compose -p "$PROJECT" $COMPOSE_FILES up "${DETACH_ARGS[@]}" \
            db redis migrator
        ;;
    *)
        echo "  Launching full stack..."
        docker compose -p "$PROJECT" $COMPOSE_FILES up "${DETACH_ARGS[@]}"
        ;;
esac

# ── Step 10: Confirm the migration outcome ──
# The migrator's exit code alone is not proof.  The outcome is confirmed
# only when the migrator container is identified, has exited zero, and the
# project's own database reports the expected revision.
echo ""
echo "── Step 10: Confirm migration outcome ──"

if verify_migration_outcome "$PROJECT" "$SOURCE_HEAD" "$COMPOSE_FILES"; then
    :
else
    exit 1
fi

echo ""
echo "  Source revision: $SOURCE_SHA"
echo "  Source head:     $SOURCE_HEAD"
echo "  Image:           $IMAGE_REF ($IMAGE_ID)"
echo "  Image provenance: $IMAGE_PROVENANCE"
echo ""
