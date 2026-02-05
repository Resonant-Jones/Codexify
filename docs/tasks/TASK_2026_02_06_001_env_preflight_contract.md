# TASK-2026-02-06-001_env_preflight_contract

## Metadata

- Task-ID: TASK-2026-02-06-001_env_preflight_contract
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION
- Task artifact: docs/tasks/TASK_2026_02_06_001_env_preflight_contract.md
- Owner: resonant_jones
- Risk: LOW

## Objective

Define a deterministic environment “contract” for running Codexify + tests (venv + pytest + node/pnpm), so audits and tasks can rely on it.

## Scope

### In-scope

- Document required tools + exact verification commands + exact remediation commands.
- Make it copy/paste runnable on macOS + zsh.

### Out-of-scope

- No broad refactors.
- No CI/CD setup.

## Allowed files (STRICT)

- README.md
- docs/QUICK_REFERENCE.md (if present) OR docs/ (tight: docs/*.md)
- docs/tasks/TASK_2026_02_06_001_env_preflight_contract.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md

## Preconditions (NO GUESSING)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
```

Expected: no output.

Execution plan

Step-by-step commands (copy/paste)

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# Confirm python env + pytest
python --version
python -m pip --version
python -m pytest --version || true

# Confirm node env (adjust to your repo norms)
node --version
pnpm --version || true
npm --version

# Confirm docker tooling if required by tasks
docker --version
docker compose version

Expected results
 • A documented “Environment Contract” section exists in README (or docs reference) listing:
 • required tools
 • exact verify commands
 • exact install/fix commands
 • Future tasks can reference “Environment Contract” rather than rediscovering setup.

Rollback / cleanup

git checkout -- README.md docs/QUICK_REFERENCE.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md docs/tasks/TASK_2026_02_06_001_env_preflight_contract.md

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation)
 • Commit message (EXACT):
 • TASK-2026-02-06-001_env_preflight_contract: define env contract
 • Manual commands:

git status --porcelain -uall
git add README.md docs/QUICK_REFERENCE.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md
git commit --no-verify -m "TASK-2026-02-06-001_env_preflight_contract: define env contract"
git log -1 --oneline
git status --porcelain -uall

Commit B (docs finalize + mapping)
 • Commit message (EXACT):
 • TASK-2026-02-06-001_env_preflight_contract: docs finalize + mapping
 • Manual commands:

git add docs/tasks/TASK_2026_02_06_001_env_preflight_contract.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md
git commit --no-verify -m "TASK-2026-02-06-001_env_preflight_contract: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall

Mapping
 • TASK-2026-02-06-001_env_preflight_contract -> [, ]

Summary (fill after completion)
 • What changed
 • Commands run + outputs captured
 • Final mapping with real hashes

## Summary
- Status: DONE.
- Changes:
  - Added an Environment Contract section to `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/README.md`.
- Commands run:
  - `python --version` → `Python 3.13.9`
  - `python -m pip --version` → `pip 25.3 ... (python 3.13)`
  - `python -m pytest --version` → `No module named pytest`
  - `node --version` → `v22.17.0`
  - `pnpm --version` → `10.13.1`
  - `npm --version` → `10.9.2`
  - `docker --version` → `Docker version 29.2.0`
  - `docker compose version` → `Docker Compose version v5.0.2`
- Commit mode: two-phase.
- Implementation commit: `7ddc7b49`.
