#!/usr/bin/env bash
set -euo pipefail

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|True|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if is_truthy "${CODEXIFY_DISABLE_EMBEDDINGS:-false}"; then
  echo "[embed-model] embeddings disabled; skipping model bootstrap"
else
  python -m guardian.scripts.ensure_embed_model
fi

if [ "$#" -eq 0 ]; then
  echo "[backend-entrypoint] no command provided" >&2
  exit 1
fi

exec "$@"
