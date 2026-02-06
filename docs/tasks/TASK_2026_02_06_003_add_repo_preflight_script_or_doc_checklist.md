
```markdown
# TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist

## Metadata
- Task-ID: TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION
- Task artifact: docs/tasks/TASK_2026_02_06_003_add_repo_preflight_script_or_doc_checklist.md
- Owner: resonant_jones
- Risk: MED

## Objective
Add a single “preflight” entrypoint (script OR docs checklist) that validates the environment and repo invariants before any campaign/task run.

## Scope
### In-scope
- Either:
  - a script (preferred) that prints pass/fail and remediation commands, OR
  - a documented checklist that is copy/paste runnable.
- Must check: python version, venv active/detectable, pytest importable, node tools, docker compose presence (if required).

### Out-of-scope
- No runners or automation.
- No major restructuring.

## Allowed files (STRICT)
- scripts/ (tight: scripts/*.py or scripts/*.sh — pick one)
- README.md
- docs/ (tight: docs/*.md)
- docs/tasks/TASK_2026_02_06_003_add_repo_preflight_script_or_doc_checklist.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md

## Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
```

Execution plan

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# Run preflight (script or documented commands)
<preflight command here>

# Confirm it catches missing pytest (simulate by running outside venv if applicable)
python -m pytest --version || true

Expected results
 • There is ONE canonical preflight command documented in README, e.g.:
 • ./scripts/preflight.sh OR python scripts/preflight.py
 • It prints clear PASS/FAIL signals and remediation commands.

Rollback / cleanup

git checkout -- README.md
git checkout -- scripts
git checkout -- docs

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation)
 • Commit message (EXACT):
 • TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist: add preflight entrypoint
 • Manual commands:

git add scripts README.md docs
git commit --no-verify -m "TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist: add preflight entrypoint"
git log -1 --oneline
git status --porcelain -uall

Commit B (docs finalize + mapping)
 • Commit message (EXACT):
 • TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist: docs finalize + mapping
 • Manual commands:

git add docs/tasks/TASK_2026_02_06_003_add_repo_preflight_script_or_doc_checklist.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_PLAN_ENV_AND_VALIDATION.md
git commit --no-verify -m "TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall

Mapping
 • TASK-2026-02-06-003_add_repo_preflight_script_or_doc_checklist -> [, ]

## Summary
- Status: DONE.
- Changes:
  - Added `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/preflight.sh`.
  - Documented `./scripts/preflight.sh` in `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/README.md`.
- Commands run:
  - `./scripts/preflight.sh` (failed: pytest missing + dirty tree)
  - `python -m pytest --version` → `No module named pytest`
- Commit mode: two-phase.
- Implementation commit: `a859f61a`.
