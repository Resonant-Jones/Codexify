#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATE="$REPO_ROOT/config/launchd/com.resonant.codexify-tester.plist.template"
LABEL="com.resonant.codexify-tester"
LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
TARGET="$LAUNCH_AGENT_DIR/$LABEL.plist"
RUNNER_DIR="${HOME}/Library/Application Support/Codexify/tester"
RUNNER="$RUNNER_DIR/codexify_tester_autostart.sh"
STDOUT_PATH="${CODEXIFY_TESTER_LAUNCHD_STDOUT:-/tmp/codexify-tester-autostart.out}"
STDERR_PATH="${CODEXIFY_TESTER_LAUNCHD_STDERR:-/tmp/codexify-tester-autostart.err}"
GUI_DOMAIN="gui/$(id -u)"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ops/install_codexify_tester_launchagent.sh install
  scripts/ops/install_codexify_tester_launchagent.sh uninstall

Install loads a per-user LaunchAgent. It does not enable the Tester stack;
run `make tester-up` separately when you want the stack to persist.
USAGE
}

render_plist() {
  local output="$1"
  sed \
    -e "s|__CODEXIFY_TESTER_RUNNER__|$RUNNER|g" \
    -e "s|__CODEXIFY_REPO_ROOT__|$REPO_ROOT|g" \
    -e "s|__CODEXIFY_TESTER_STDOUT__|$STDOUT_PATH|g" \
    -e "s|__CODEXIFY_TESTER_STDERR__|$STDERR_PATH|g" \
    "$TEMPLATE" > "$output"
}

install_agent() {
  [[ -f "$TEMPLATE" ]] || { echo "Missing LaunchAgent template: $TEMPLATE" >&2; return 1; }
  [[ -f "$REPO_ROOT/scripts/ops/codexify_tester.sh" ]] || { echo "Missing Tester lifecycle script" >&2; return 1; }
  mkdir -p "$LAUNCH_AGENT_DIR"
  mkdir -p "$RUNNER_DIR"
  cp "$REPO_ROOT/scripts/ops/codexify_tester.sh" "$RUNNER"
  chmod 755 "$RUNNER"
  local rendered
  rendered="$(mktemp "${TMPDIR:-/tmp}/codexify-tester.XXXXXX")"
  render_plist "$rendered"
  plutil -lint "$rendered"
  launchctl bootout "$GUI_DOMAIN/$LABEL" 2>/dev/null || true
  cp "$rendered" "$TARGET"
  launchctl bootstrap "$GUI_DOMAIN" "$TARGET"
  launchctl kickstart -k "$GUI_DOMAIN/$LABEL"
  rm -f "$rendered"
  echo "Installed and started $LABEL"
  echo "Plist: $TARGET"
}

uninstall_agent() {
  launchctl bootout "$GUI_DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$TARGET"
  echo "Uninstalled $LABEL"
  echo "Use 'make tester-down' to stop the Tester and clear its desired-up marker."
}

main() {
  case "${1:-}" in
    install)
      install_agent
      ;;
    uninstall)
      uninstall_agent
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
