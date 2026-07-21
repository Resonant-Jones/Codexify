#!/usr/bin/env bash
set -euo pipefail

# Codexify friends-and-family Tester lifecycle.
#
# The desired-state marker is intentionally separate from Docker state. The
# launch agent starts the stack at login only when the marker exists. `down`
# removes the marker before stopping Compose, so an intentional shutdown is
# not resurrected by launchd.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${CODEXIFY_TESTER_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

TESTER_PROJECT="${CODEXIFY_TESTER_PROJECT_NAME:-codexify_tester}"
TESTER_ENV_FILE="${CODEXIFY_TESTER_ENV_FILE:-$REPO_ROOT/.env.tester}"
TESTER_STATE_DIR="${CODEXIFY_TESTER_STATE_DIR:-${HOME}/Library/Application Support/Codexify/tester}"
TESTER_ENABLED_MARKER="$TESTER_STATE_DIR/enabled"
TESTER_DOCKER_WAIT_SECONDS="${CODEXIFY_TESTER_DOCKER_WAIT_SECONDS:-300}"

COMPOSE_FILES=(
  --env-file "$TESTER_ENV_FILE"
  -p "$TESTER_PROJECT"
  -f "$REPO_ROOT/docker-compose.yml"
  -f "$REPO_ROOT/docker-compose.tester.yml"
)

usage() {
  cat <<'USAGE'
Usage:
  scripts/ops/codexify_tester.sh up
  scripts/ops/codexify_tester.sh down
  scripts/ops/codexify_tester.sh status
  scripts/ops/codexify_tester.sh auto-start

Commands:
  up          Persist the desired-up state and start the isolated Tester stack.
  down        Clear the desired-up state, then stop the stack without deleting volumes.
  status      Show desired state, Compose state, and the local health endpoints.
  auto-start  Start at login only when the desired-up marker exists.

The macOS LaunchAgent calls `auto-start`. Use `down` for an intentional stop;
raw `docker compose down` cannot be distinguished from an unexpected stop by
launchd.
USAGE
}

compose() {
  docker compose "${COMPOSE_FILES[@]}" "$@"
}

require_env_file() {
  if [[ ! -f "$TESTER_ENV_FILE" ]]; then
    echo "Tester env file not found: $TESTER_ENV_FILE" >&2
    echo "Create it from .env.tester.example and populate the required secrets." >&2
    return 1
  fi
}

validate_compose() {
  compose config --quiet
}

set_desired_up() {
  mkdir -p "$TESTER_STATE_DIR"
  local marker_tmp="$TESTER_ENABLED_MARKER.tmp.$$"
  : > "$marker_tmp"
  mv -f "$marker_tmp" "$TESTER_ENABLED_MARKER"
}

clear_desired_up() {
  rm -f "$TESTER_ENABLED_MARKER"
}

desired_up() {
  [[ -f "$TESTER_ENABLED_MARKER" ]]
}

wait_for_docker() {
  local waited=0
  while ! docker info >/dev/null 2>&1; do
    if ! desired_up; then
      echo "Tester auto-start cancelled: desired-up marker was removed."
      return 0
    fi
    if (( waited >= TESTER_DOCKER_WAIT_SECONDS )); then
      echo "Docker Desktop was not ready after ${TESTER_DOCKER_WAIT_SECONDS}s." >&2
      return 1
    fi
    sleep 5
    waited=$((waited + 5))
  done
}

start_stack() {
  compose up -d \
    backend \
    frontend \
    worker-chat \
    worker-chat-embed \
    worker-document-embed \
    worker-warmup \
    tailscale-codexify-test
}

health_check() {
  local endpoint="$1"
  curl -fsS --max-time 5 "$endpoint"
}

command_up() {
  require_env_file
  validate_compose
  set_desired_up
  wait_for_docker
  if ! desired_up; then
    echo "Tester start cancelled: desired-up marker was removed."
    return 0
  fi
  start_stack
  echo "Codexify Tester is enabled and starting."
  echo "Open the configured Tailscale FQDN from .env.tester."
}

command_down() {
  # Clear intent first. If Compose takes time or fails, launchd still knows
  # that this was an intentional operator shutdown.
  clear_desired_up
  if [[ ! -f "$TESTER_ENV_FILE" ]]; then
    echo "Tester desired-up state cleared; env file is absent, so Compose was not invoked."
    return 0
  fi
  compose down
  echo "Codexify Tester is disabled and stopped. Volumes were preserved."
}

command_status() {
  require_env_file
  if desired_up; then
    echo "desired_state=enabled"
  else
    echo "desired_state=disabled"
  fi
  echo "state_marker=$TESTER_ENABLED_MARKER"
  echo "project=$TESTER_PROJECT"
  echo "env_file=$TESTER_ENV_FILE"

  if docker info >/dev/null 2>&1; then
    compose ps
  else
    echo "docker=unavailable"
    return 0
  fi

  echo "--- backend health ---"
  health_check "http://127.0.0.1:8889/health" || true
  echo
  echo "--- chat health ---"
  health_check "http://127.0.0.1:8889/health/chat" || true
  echo
}

command_auto_start() {
  if ! desired_up; then
    echo "Codexify Tester auto-start skipped: desired-up marker is absent."
    return 0
  fi
  require_env_file
  validate_compose
  wait_for_docker
  if ! desired_up; then
    return 0
  fi
  start_stack
  echo "Codexify Tester auto-start completed."
}

main() {
  local command="${1:-}"
  case "$command" in
    up)
      command_up
      ;;
    down)
      command_down
      ;;
    status)
      command_status
      ;;
    auto-start)
      command_auto_start
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage >&2
      return 2
      ;;
  esac
}

main "$@"
