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

  # Local trusted-remote overlay must never be tracked or staged. It may carry
  # local/dev session or JWT secrets. The .example file is the only safe,
  # tracked artifact.
  tr_pattern='(^|/)(trusted-remote\.env|.*\.trusted-remote\.env|\.env\.trusted-remote)$'
  tr_example="config/trusted-remote.env.example"
  tr_ok=1

  # Tracked real overlay (any variant name)?
  tracked_real="$(git ls-files | grep -E "$tr_pattern" || true)"
  if [ -n "$tracked_real" ]; then
    fail "trusted-remote env file is tracked but must remain local-only:"
    printf '%s\n' "$tracked_real" | sed 's/^/    /'
    log "  Remediation: git rm --cached <file>"
    tr_ok=0
  fi

  # Staged real overlay?
  staged_real="$(git diff --cached --name-only | grep -E "$tr_pattern" || true)"
  if [ -n "$staged_real" ]; then
    fail "trusted-remote env file is staged but must remain local-only:"
    printf '%s\n' "$staged_real" | sed 's/^/    /'
    log "  Remediation: git restore --staged <file>"
    tr_ok=0
  fi

  # Required safe example must exist.
  if [ ! -f "$tr_example" ]; then
    fail "$tr_example is missing (required placeholder reference)"
    log "  Remediation: recreate it with placeholder values only"
    tr_ok=0
  fi

  # The example must not carry obvious secret-looking values. The matched
  # value is intentionally NOT printed in case it really is a secret.
  if [ -f "$tr_example" ]; then
    secret_hits="$(awk '
      {
        if ($0 ~ /^[[:space:]]*#/) next
        eq = index($0, "=")
        if (!eq) next
        val = substr($0, eq + 1)
        gsub(/[[:space:]]+$/, "", val)
        if (val == "") next
        low = tolower(val)
        if (low ~ /replace|example|invalid|localhost|127\.0\.0\.1|changeme|placeholder|local-dev|your-|todo|xxxxx/) next
        if (val ~ /^eyJ/ || val ~ /^(gho_|ghp_|ghs_|ghu_|ghr_|github_pat_|sk-|xox[bp]-)/ || val ~ /^[A-Za-z0-9_\/+=.-]{32,}$/) {
          print FILENAME ":" FNR ": <redacted value looks like a secret>"
        }
      }' "$tr_example" || true)"
    if [ -n "$secret_hits" ]; then
      fail "$tr_example may contain a real secret-looking value"
      printf '%s\n' "$secret_hits" | sed 's/^/    /'
      log "  Remediation: replace with placeholder values only"
      tr_ok=0
    fi
  fi

  if [ "$tr_ok" -eq 1 ]; then
    ok "trusted-remote env not tracked/staged; example present and placeholder-only"
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
