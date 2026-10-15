#!/usr/bin/env bash
set -euo pipefail

# Private-preview lifecycle and desired-state reconciliation.
#
# Docker owns long-running container recovery through `unless-stopped`. The
# per-user LaunchAgent calls `auto-start` at login and on a bounded interval so
# an accidentally removed/stopped Compose project is reconciled while the
# desired-up marker exists. `down` clears that marker before stopping anything.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${CODEXIFY_PRIVATE_PREVIEW_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PRIVATE_PREVIEW_PROJECT="${CODEXIFY_PRIVATE_PREVIEW_PROJECT_NAME:-codexify_private_preview}"
PRIVATE_PREVIEW_ENV_FILE="${CODEXIFY_PRIVATE_PREVIEW_ENV_FILE:-$REPO_ROOT/.env.private-preview}"
PRIVATE_PREVIEW_HOME="${CODEXIFY_PRIVATE_PREVIEW_HOME:-${HOME:?HOME is required}}"
PRIVATE_PREVIEW_STATE_DIR="${CODEXIFY_PRIVATE_PREVIEW_STATE_DIR:-$PRIVATE_PREVIEW_HOME/Library/Application Support/Codexify/private-preview}"
PRIVATE_PREVIEW_ENABLED_MARKER="$PRIVATE_PREVIEW_STATE_DIR/enabled"
PRIVATE_PREVIEW_DOCKER_WAIT_ATTEMPTS="${CODEXIFY_PRIVATE_PREVIEW_DOCKER_WAIT_ATTEMPTS:-60}"
PRIVATE_PREVIEW_DOCKER_WAIT_SECONDS="${CODEXIFY_PRIVATE_PREVIEW_DOCKER_WAIT_SECONDS:-5}"
PRIVATE_PREVIEW_TUNNEL_LABEL="${CODEXIFY_PRIVATE_PREVIEW_TUNNEL_LABEL:-com.resonant.codexify-private-preview-tunnel}"
PRIVATE_PREVIEW_TUNNEL_PLIST="$PRIVATE_PREVIEW_HOME/Library/LaunchAgents/$PRIVATE_PREVIEW_TUNNEL_LABEL.plist"
PRIVATE_PREVIEW_GUI_DOMAIN="gui/$(id -u)"

COMPOSE_FILES=(
  --project-directory "$REPO_ROOT"
  --env-file "$PRIVATE_PREVIEW_ENV_FILE"
  -p "$PRIVATE_PREVIEW_PROJECT"
  -f "$REPO_ROOT/docker-compose.yml"
  -f "$REPO_ROOT/docker-compose.private-preview.yml"
)

usage() {
  cat <<'USAGE'
Usage:
  scripts/ops/codexify_private_preview.sh up
  scripts/ops/codexify_private_preview.sh down
  scripts/ops/codexify_private_preview.sh status
  scripts/ops/codexify_private_preview.sh auto-start

Commands:
  up          Enable desired-up state and start the private-preview stack.
  down        Clear desired-up state, stop the stack, and stop the tunnel.
  status      Show desired state, Compose state, and local health endpoints.
  auto-start  Reconcile the stack at login/interval while desired-up is set.

Use `down` for an intentional shutdown. It preserves all Compose volumes.
Raw `docker compose stop` or `down` leaves desired-up enabled and may be
reconciled by the LaunchAgent.
USAGE
}

compose() {
  docker compose "${COMPOSE_FILES[@]}" "$@"
}

require_env_file() {
  if [[ ! -f "$PRIVATE_PREVIEW_ENV_FILE" ]]; then
    echo "Private-preview env file not found: $PRIVATE_PREVIEW_ENV_FILE" >&2
    echo "Create it from .env.private-preview.example and populate the required secrets." >&2
    return 1
  fi
}

validate_compose() {
  compose config --quiet
}

set_desired_up() {
  mkdir -p "$PRIVATE_PREVIEW_STATE_DIR"
  local marker_tmp="$PRIVATE_PREVIEW_ENABLED_MARKER.tmp.$$"
  : > "$marker_tmp"
  mv -f "$marker_tmp" "$PRIVATE_PREVIEW_ENABLED_MARKER"
}

clear_desired_up() {
  rm -f "$PRIVATE_PREVIEW_ENABLED_MARKER"
}

desired_up() {
  [[ -f "$PRIVATE_PREVIEW_ENABLED_MARKER" ]]
}

wait_for_docker() {
  local attempt
  for attempt in $(seq 1 "$PRIVATE_PREVIEW_DOCKER_WAIT_ATTEMPTS"); do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    if ! desired_up; then
      echo "Private-preview auto-start cancelled: desired-up marker was removed."
      return 0
    fi
    sleep "$PRIVATE_PREVIEW_DOCKER_WAIT_SECONDS"
  done
  echo "Docker Desktop was not ready after ${PRIVATE_PREVIEW_DOCKER_WAIT_ATTEMPTS} attempts." >&2
  return 1
}

start_stack() {
  local build_mode="${1:-no}"
  if [[ "$build_mode" == "yes" ]]; then
    compose up -d --build
  else
    compose up -d
  fi
}

start_tunnel() {
  local target="$PRIVATE_PREVIEW_GUI_DOMAIN/$PRIVATE_PREVIEW_TUNNEL_LABEL"
  if ! launchctl print "$PRIVATE_PREVIEW_GUI_DOMAIN/$PRIVATE_PREVIEW_TUNNEL_LABEL" >/dev/null 2>&1; then
    if [[ -f "$PRIVATE_PREVIEW_TUNNEL_PLIST" ]]; then
      launchctl bootstrap "$PRIVATE_PREVIEW_GUI_DOMAIN" "$PRIVATE_PREVIEW_TUNNEL_PLIST" 2>/dev/null || true
    fi
  fi
  local service_state
  service_state="$(launchctl print "$target" 2>/dev/null || true)"
  if [[ "$service_state" != *"state = running"* ]]; then
    launchctl kickstart -k "$target" 2>/dev/null || true
  fi
}

stop_tunnel() {
  # Unloading the user agent is deterministic where launchctl kill may be
  # rejected for a service owned by the per-user launchd domain.
  launchctl bootout "$PRIVATE_PREVIEW_GUI_DOMAIN/$PRIVATE_PREVIEW_TUNNEL_LABEL" 2>/dev/null || true
}

health_check() {
  local endpoint="$1"
  curl -fsS --max-time 5 "$endpoint"
}

report_health() {
  local endpoint="$1"
  local expected_prefix="$2"
  local payload
  if ! payload="$(health_check "$endpoint")"; then
    echo "health=unreachable endpoint=$endpoint"
    return 1
  fi
  printf '%s\n' "$payload"
    case "$payload" in
    "$expected_prefix"*)
      return 0
      ;;
    *)
      echo "health=degraded endpoint=$endpoint"
      return 1
    ;;
  esac
}

command_up() {
  require_env_file
  validate_compose
  set_desired_up
  wait_for_docker
  if ! desired_up; then
    echo "Private-preview start cancelled: desired-up marker was removed."
    return 0
  fi
  start_stack yes
  # The tunnel LaunchAgent is marker-gated and may have been unloaded by the
  # previous intentional `down`; start_tunnel re-bootstraps it when installed.
  start_tunnel
  echo "Codexify private preview is enabled and starting."
}

command_down() {
  # Clear intent first. If Compose takes time or fails, launchd still knows
  # that this was an intentional operator shutdown.
  clear_desired_up
  stop_tunnel
  if [[ ! -f "$PRIVATE_PREVIEW_ENV_FILE" ]]; then
    echo "Private-preview desired-up state cleared; env file is absent, so Compose was not invoked."
    return 0
  fi
  compose stop
  echo "Codexify private preview is disabled and stopped. Volumes were preserved."
}

command_status() {
  local requirements_failed=0
  require_env_file
  if desired_up; then
    echo "desired_state=enabled"
  else
    echo "desired_state=disabled"
  fi
  echo "state_marker=$PRIVATE_PREVIEW_ENABLED_MARKER"
  echo "project=$PRIVATE_PREVIEW_PROJECT"
  echo "env_file=$PRIVATE_PREVIEW_ENV_FILE"

  if docker info >/dev/null 2>&1; then
    compose ps --all
  else
    echo "docker=unavailable"
    return 0
  fi

  echo "--- origin health ---"
  report_health "http://127.0.0.1:8081/health" '{"status":"ok"' || requirements_failed=1
  echo
  echo "--- chat health ---"
  report_health "http://127.0.0.1:8081/health/chat" '{"ok":true' || requirements_failed=1
  echo

  if (( requirements_failed )); then
    echo "private_preview_status=degraded" >&2
    return 1
  fi
  echo "private_preview_status=healthy"
}

command_auto_start() {
  if ! desired_up; then
    echo "Codexify private-preview auto-start skipped: desired-up marker is absent."
    return 0
  fi
  require_env_file
  validate_compose
  wait_for_docker
  if ! desired_up; then
    return 0
  fi
  start_stack no
  start_tunnel
  echo "Codexify private-preview auto-start reconciliation completed."
}

main() {
  case "${1:-}" in
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
