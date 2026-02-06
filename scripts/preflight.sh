#!/usr/bin/env bash
set -u

status=0

log() {
  printf "%s\n" "$*"
}

ok() {
  log "[PASS] $*"
}

warn() {
  log "[WARN] $*"
}

fail() {
  log "[FAIL] $*"
  status=1
}

check_cmd() {
  local name="$1"
  local hint="$2"
  if command -v "$name" >/dev/null 2>&1; then
    ok "$name found"
    return 0
  fi
  fail "$name missing"
  log "  Remediation: $hint"
  return 1
}

log "Codexify preflight (macOS + zsh)"
log "Repo: $(pwd)"
log ""

check_cmd "python" "brew install python"

if command -v python >/dev/null 2>&1; then
  log "python --version: $(python --version 2>&1)"
  log "python -m pip --version: $(python -m pip --version 2>&1)"
else
  fail "python not available; cannot verify pip or pytest"
fi

if [ -n "${VIRTUAL_ENV:-}" ]; then
  ok "venv active: $VIRTUAL_ENV"
else
  warn "venv not active"
  log "  Remediation: python -m venv .venv && source .venv/bin/activate"
fi

if python -m pytest --version >/dev/null 2>&1; then
  ok "pytest importable"
else
  fail "pytest missing"
  log "  Remediation: python -m pip install -r requirements.txt"
  log "  Or: python -m pip install pytest"
fi

check_cmd "node" "brew install node"
if command -v node >/dev/null 2>&1; then
  log "node --version: $(node --version 2>&1)"
fi

if command -v pnpm >/dev/null 2>&1; then
  ok "pnpm found"
  log "pnpm --version: $(pnpm --version 2>&1)"
else
  warn "pnpm missing"
  log "  Remediation: corepack enable && corepack prepare pnpm@9.12.1 --activate"
fi

if command -v npm >/dev/null 2>&1; then
  ok "npm found"
  log "npm --version: $(npm --version 2>&1)"
else
  fail "npm missing"
  log "  Remediation: brew install node"
fi

if command -v docker >/dev/null 2>&1; then
  ok "docker found"
  log "docker --version: $(docker --version 2>&1)"
else
  fail "docker missing"
  log "  Remediation: brew install --cask docker"
fi

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    ok "docker compose found"
    log "docker compose version: $(docker compose version 2>&1)"
  else
    fail "docker compose missing"
    log "  Remediation: upgrade Docker Desktop or install docker-compose-plugin"
  fi
fi

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  dirty="$(git status --porcelain -uall)"
  if [ -z "$dirty" ]; then
    ok "working tree clean"
  else
    fail "working tree dirty"
    log "$dirty"
  fi
else
  warn "not in a git repo; skipping clean-tree check"
fi

log ""
if [ "$status" -eq 0 ]; then
  log "Preflight result: PASS"
else
  log "Preflight result: FAIL"
fi

exit "$status"
