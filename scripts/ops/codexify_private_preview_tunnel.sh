#!/usr/bin/env bash
set -euo pipefail

# Marker-gated foreground connector for the per-user LaunchAgent. The
# credential JSON is referenced by the external cloudflared config and is
# never copied into the repository or placed in this process's arguments.

PRIVATE_PREVIEW_HOME="${CODEXIFY_PRIVATE_PREVIEW_HOME:-${HOME:?HOME is required}}"
PRIVATE_PREVIEW_ENABLED_MARKER="${CODEXIFY_PRIVATE_PREVIEW_ENABLED_MARKER:-$PRIVATE_PREVIEW_HOME/Library/Application Support/Codexify/private-preview/enabled}"
PRIVATE_PREVIEW_TUNNEL_CONFIG="${CODEXIFY_PRIVATE_PREVIEW_TUNNEL_CONFIG:-$PRIVATE_PREVIEW_HOME/.cloudflared/codexify-private-preview.yml}"
PRIVATE_PREVIEW_CLOUDFLARED="${CODEXIFY_PRIVATE_PREVIEW_CLOUDFLARED:-$(command -v cloudflared || true)}"

if [[ ! -f "$PRIVATE_PREVIEW_ENABLED_MARKER" ]]; then
  exit 0
fi
[[ -x "$PRIVATE_PREVIEW_CLOUDFLARED" ]] || exit 1
[[ -f "$PRIVATE_PREVIEW_TUNNEL_CONFIG" ]] || exit 1

exec "$PRIVATE_PREVIEW_CLOUDFLARED" tunnel \
  --config "$PRIVATE_PREVIEW_TUNNEL_CONFIG" \
  run
