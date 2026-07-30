#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.soft-serve.yml"
ENV_FILE="${SOFT_SERVE_ENV_FILE:-$REPO_ROOT/config/soft-serve.env}"

compose() {
  local args=(--file "$COMPOSE_FILE")
  if [[ -f "$ENV_FILE" ]]; then
    args+=(--env-file "$ENV_FILE")
  fi
  docker compose "${args[@]}" "$@"
}

usage() {
  cat <<'USAGE'
Usage:
  scripts/ops/soft_serve.sh config
  scripts/ops/soft_serve.sh up
  scripts/ops/soft_serve.sh down
  scripts/ops/soft_serve.sh status
  scripts/ops/soft_serve.sh logs

Commands:
  config  Render and validate the isolated Soft Serve Compose configuration.
  up      Start the optional Soft Serve forge without touching Codexify Compose.
  down    Stop Soft Serve while preserving its configured data directory.
  status  Report the Soft Serve container state and return success only when running.
  logs    Follow the Soft Serve container logs.
USAGE
}

require_admin_key() {
  local key="${SOFT_SERVE_INITIAL_ADMIN_KEYS:-}"
  if [[ -z "$key" && -f "$ENV_FILE" ]]; then
    key="$(sed -n 's/^SOFT_SERVE_INITIAL_ADMIN_KEYS[[:space:]]*=[[:space:]]*//p' "$ENV_FILE" | tail -n 1)"
  fi
  if [[ -z "$key" || "$key" == REPLACE_WITH_* ]]; then
    echo "Soft Serve cannot start: set SOFT_SERVE_INITIAL_ADMIN_KEYS to an Ed25519 authorized_keys line." >&2
    echo "Use $ENV_FILE or export the variable for this invocation." >&2
    return 1
  fi
}

configured_data_dir() {
  local data_dir="${CODEXIFY_SOFT_SERVE_DATA_DIR:-}"
  if [[ -z "$data_dir" && -f "$ENV_FILE" ]]; then
    data_dir="$(sed -n 's/^CODEXIFY_SOFT_SERVE_DATA_DIR[[:space:]]*=[[:space:]]*//p' "$ENV_FILE" | tail -n 1)"
  fi
  printf '%s\n' "${data_dir:-${HOME}/.local/share/codexify/soft-serve}"
}

command_config() {
  compose config
}

command_up() {
  require_admin_key
  compose config --quiet
  mkdir -p "$(configured_data_dir)"
  compose up -d soft-serve
}

command_down() {
  compose down
}

command_status() {
  local container_id state health restarting status
  container_id="$(compose ps -aq soft-serve)"
  if [[ -z "$container_id" ]]; then
    echo "soft-serve: missing"
    return 1
  fi

  IFS='|' read -r state health restarting < <(
    docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}|{{.State.Restarting}}' "$container_id"
  )

  if [[ "$restarting" == "true" ]]; then
    status=restarting
  elif [[ "$state" == "running" && "$health" == "starting" ]]; then
    status=starting
  elif [[ "$state" == "running" && "$health" == "unhealthy" ]]; then
    status=unhealthy
  elif [[ "$state" == "running" ]]; then
    status=running
  elif [[ "$state" == "created" ]]; then
    status=created
  elif [[ "$state" == "exited" ]]; then
    status=exited
  else
    status="${state:-missing}"
  fi

  echo "soft-serve: $status"
  [[ "$status" == "running" ]]
}

command_logs() {
  compose logs -f --tail=200 soft-serve
}

main() {
  local command="${1:-}"
  case "$command" in
    config) command_config ;;
    up) command_up ;;
    down) command_down ;;
    status) command_status ;;
    logs) command_logs ;;
    *) usage >&2; return 2 ;;
  esac
}

main "$@"
