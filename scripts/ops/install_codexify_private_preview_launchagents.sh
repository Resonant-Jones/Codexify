#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRIVATE_PREVIEW_HOME="${HOME:?HOME is required}"
LAUNCH_AGENT_DIR="$PRIVATE_PREVIEW_HOME/Library/LaunchAgents"
RUNNER_DIR="$PRIVATE_PREVIEW_HOME/Library/Application Support/Codexify/private-preview"
STACK_RUNNER="$RUNNER_DIR/codexify_private_preview_autostart.sh"
TUNNEL_RUNNER="$RUNNER_DIR/codexify_private_preview_tunnel.sh"
STACK_TEMPLATE="$REPO_ROOT/config/launchd/com.resonant.codexify-private-preview.plist.template"
TUNNEL_TEMPLATE="$REPO_ROOT/config/launchd/com.resonant.codexify-private-preview-tunnel.plist.template"
STACK_LABEL="com.resonant.codexify-private-preview"
TUNNEL_LABEL="com.resonant.codexify-private-preview-tunnel"
STACK_TARGET="$LAUNCH_AGENT_DIR/$STACK_LABEL.plist"
TUNNEL_TARGET="$LAUNCH_AGENT_DIR/$TUNNEL_LABEL.plist"
STATE_MARKER="$RUNNER_DIR/enabled"
TUNNEL_CONFIG="${CODEXIFY_PRIVATE_PREVIEW_TUNNEL_CONFIG:-$PRIVATE_PREVIEW_HOME/.cloudflared/codexify-private-preview.yml}"
CLOUDFLARED_BIN="$(command -v cloudflared || true)"
STDOUT_PATH="${CODEXIFY_PRIVATE_PREVIEW_LAUNCHD_STDOUT:-/tmp/codexify-private-preview-autostart.out}"
STDERR_PATH="${CODEXIFY_PRIVATE_PREVIEW_LAUNCHD_STDERR:-/tmp/codexify-private-preview-autostart.err}"
TUNNEL_LOG_PATH="${CODEXIFY_PRIVATE_PREVIEW_TUNNEL_LOG:-$PRIVATE_PREVIEW_HOME/Library/Logs/codexify-private-preview-tunnel.log}"
GUI_DOMAIN="gui/$(id -u)"
STACK_RENDERED=""
TUNNEL_RENDERED=""

cleanup_rendered() {
  [[ -z "$STACK_RENDERED" ]] || rm -f "$STACK_RENDERED"
  [[ -z "$TUNNEL_RENDERED" ]] || rm -f "$TUNNEL_RENDERED"
}

trap cleanup_rendered EXIT

usage() {
  cat <<'USAGE'
Usage:
  scripts/ops/install_codexify_private_preview_launchagents.sh install
  scripts/ops/install_codexify_private_preview_launchagents.sh uninstall

Install loads per-user LaunchAgents for private-preview reconciliation and
the existing named cloudflared tunnel. It does not enable the preview;
run `make private-preview-up` separately.
USAGE
}

render_stack_plist() {
  local output="$1"
  sed \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_RUNNER__|$STACK_RUNNER|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_REPO_ROOT__|$REPO_ROOT|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_HOME__|$PRIVATE_PREVIEW_HOME|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_STDOUT__|$STDOUT_PATH|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_STDERR__|$STDERR_PATH|g" \
    "$STACK_TEMPLATE" > "$output"
}

render_tunnel_plist() {
  local output="$1"
  sed \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_TUNNEL_RUNNER__|$TUNNEL_RUNNER|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_HOME__|$PRIVATE_PREVIEW_HOME|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_ENABLED_MARKER__|$STATE_MARKER|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_TUNNEL_CONFIG__|$TUNNEL_CONFIG|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_CLOUDFLARED__|$CLOUDFLARED_BIN|g" \
    -e "s|__CODEXIFY_PRIVATE_PREVIEW_TUNNEL_LOG__|$TUNNEL_LOG_PATH|g" \
    "$TUNNEL_TEMPLATE" > "$output"
}

unload_agent() {
  local label="$1"
  local target="$GUI_DOMAIN/$label"
  if ! launchctl print "$target" >/dev/null 2>&1; then
    return 0
  fi
  launchctl bootout "$target" 2>/dev/null || true
  for _ in $(seq 1 15); do
    if ! launchctl print "$target" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "LaunchAgent did not unload cleanly: $target" >&2
  return 1
}

install_agents() {
  [[ -f "$STACK_TEMPLATE" ]] || { echo "Missing stack LaunchAgent template: $STACK_TEMPLATE" >&2; return 1; }
  [[ -f "$TUNNEL_TEMPLATE" ]] || { echo "Missing tunnel LaunchAgent template: $TUNNEL_TEMPLATE" >&2; return 1; }
  [[ -f "$REPO_ROOT/scripts/ops/codexify_private_preview.sh" ]] || { echo "Missing private-preview lifecycle script" >&2; return 1; }
  [[ -f "$REPO_ROOT/scripts/ops/codexify_private_preview_tunnel.sh" ]] || { echo "Missing private-preview tunnel script" >&2; return 1; }
  [[ -n "$CLOUDFLARED_BIN" && -x "$CLOUDFLARED_BIN" ]] || { echo "cloudflared executable not found" >&2; return 1; }
  [[ -f "$TUNNEL_CONFIG" ]] || { echo "Cloudflare tunnel config not found: $TUNNEL_CONFIG" >&2; return 1; }

  mkdir -p "$LAUNCH_AGENT_DIR" "$RUNNER_DIR"
  cp "$REPO_ROOT/scripts/ops/codexify_private_preview.sh" "$STACK_RUNNER"
  cp "$REPO_ROOT/scripts/ops/codexify_private_preview_tunnel.sh" "$TUNNEL_RUNNER"
  chmod 755 "$STACK_RUNNER" "$TUNNEL_RUNNER"

  STACK_RENDERED="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview.XXXXXX")"
  TUNNEL_RENDERED="$(mktemp "${TMPDIR:-/tmp}/codexify-private-preview-tunnel.XXXXXX")"
  render_stack_plist "$STACK_RENDERED"
  render_tunnel_plist "$TUNNEL_RENDERED"
  plutil -lint "$STACK_RENDERED"
  plutil -lint "$TUNNEL_RENDERED"

  unload_agent "$STACK_LABEL"
  unload_agent "$TUNNEL_LABEL"
  cp "$STACK_RENDERED" "$STACK_TARGET"
  cp "$TUNNEL_RENDERED" "$TUNNEL_TARGET"
  launchctl bootstrap "$GUI_DOMAIN" "$STACK_TARGET"
  launchctl bootstrap "$GUI_DOMAIN" "$TUNNEL_TARGET"
  launchctl kickstart -k "$GUI_DOMAIN/$STACK_LABEL"
  if [[ -f "$STATE_MARKER" ]]; then
    launchctl kickstart -k "$GUI_DOMAIN/$TUNNEL_LABEL"
  fi
  echo "Installed $STACK_LABEL and $TUNNEL_LABEL"
  echo "Use 'make private-preview-up' to enable the stack."
}

uninstall_agents() {
  launchctl bootout "$GUI_DOMAIN/$STACK_LABEL" 2>/dev/null || true
  launchctl bootout "$GUI_DOMAIN/$TUNNEL_LABEL" 2>/dev/null || true
  rm -f "$STACK_TARGET" "$TUNNEL_TARGET"
  echo "Uninstalled $STACK_LABEL and $TUNNEL_LABEL"
  echo "Use 'make private-preview-down' to stop the stack and clear desired-up state."
}

main() {
  case "${1:-}" in
    install)
      install_agents
      ;;
    uninstall)
      uninstall_agents
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
