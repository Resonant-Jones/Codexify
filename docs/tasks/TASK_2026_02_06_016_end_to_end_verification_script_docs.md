# TASK-2026-02-06-016_end_to_end_verification_script_docs — End-to-End Verification Script + Docs

- **Task-ID:** TASK-2026-02-06-016_end_to_end_verification_script_docs
- **Campaign:** CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- **Branch:** campaign/2026-02-06/loop-integrity-auth-and-defaults
- **Commit mode:** two-phase (Commit A = implementation, Commit B = docs finalize + campaign mapping)

## Objective
Prove the full stack works end-to-end as a *system* (not just unit tests): auth → API → WS → cron → worker → browser approvals → channel adapters.

## Background / Why
We’ve added multiple “control plane” loops (WS, cron, browser automation, channels). Individually they can test green while the integrated flow is broken (missing router wiring, missing auth headers, wrong env defaults, missing migrations).

This task creates:
1) a minimal reproducible doc, and
2) a deterministic verification script/checklist that can be run on a clean clone.

## Scope
### In-scope
- Minimal docs page describing how to run the control plane end-to-end.
- A script/checklist that can be executed deterministically.
- Minimal helper script(s) *only if required* to keep the checklist copy/paste runnable.

### Out-of-scope
- New features, refactors, UI polish.
- Reworking protocol formats created in earlier tasks.

---

## Allowed files (STRICT)
Only edit/create within these paths:
- `docs/guardian/control-plane.md`
- `scripts/verification/e2e_control_plane_checklist.sh`
- `scripts/verification/README.md`
- This task artifact: `docs/tasks/TASK_2026_02_06_016_end_to_end_verification_script_docs.md`
- Campaign mapping doc(s):
  - `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`
  - `docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md`

If you discover a missing route or wiring that requires code changes, STOP and open a new task (do not expand this task).

---

## Dependencies / Prereqs (run exactly)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# Environment quick check (expected: commands succeed; versions shown)
python --version
node --version
pnpm --version || true

# Backend deps (expected: installs cleanly)
python -m venv venv || true
source venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt

# Frontend deps (expected: installs cleanly)
pnpm --prefix frontend install
```

---

## Command checklist (copy/paste runnable)
### 0) Preflight + clean state
```bash
git status --porcelain -uall
```
**Expected:** empty output.

### 1) Create docs + verification script skeletons
Create (or overwrite) these files with the content specified in this task:
- `docs/guardian/control-plane.md`
- `scripts/verification/e2e_control_plane_checklist.sh`
- `scripts/verification/README.md`

### 2) Verify docs references are actionable
```bash
# quick sanity: files exist
ls -la docs/guardian/control-plane.md scripts/verification/e2e_control_plane_checklist.sh scripts/verification/README.md

# ensure script is executable
chmod +x scripts/verification/e2e_control_plane_checklist.sh

# grep for TODO markers; should be zero or only explicitly permitted TODOs
rg -n "TODO\(|TODO:|TBD" docs/guardian/control-plane.md scripts/verification/README.md scripts/verification/e2e_control_plane_checklist.sh || true
```
**Expected:** files exist; TODO output is empty (preferred) or minimal with a clear reason.

### 3) Run the end-to-end checklist (non-destructive)
```bash
# This script should:
# - print each step
# - run read-only verification where possible
# - fail fast with clear error message
./scripts/verification/e2e_control_plane_checklist.sh
```
**Expected:** script exits 0 on a correctly configured dev setup OR exits non-zero with a single clear remediation message (deterministic failure mode).

### 4) Minimum test gates
```bash
# Backend tests (fast gate)
source venv/bin/activate
pytest -q

# Frontend type/build gate
pnpm --prefix frontend run build
```
**Expected:** both succeed.

### 5) Post-run cleanliness
```bash
git status --porcelain -uall
```
**Expected:** only allowed files are modified.

---

## Verification script requirements (behavioral contract)
The checklist script must:
- Be safe to run multiple times.
- Avoid mutating production-like resources.
- Emit clear step headers and a final PASS/FAIL.
- Use env vars for endpoints/keys, with sane defaults.

Recommended env inputs for the script:
- `GUARDIAN_API_URL` (default `http://localhost:8000`)
- `GUARDIAN_WS_URL` (default `ws://localhost:8000/ws` or whatever the repo uses)
- `GUARDIAN_API_KEY` (required if auth is enforced)

---

## Docs requirements (control-plane.md)
The docs must include:
- **WS connect/auth example** (exact URL + headers/token mechanism)
- **Cron job examples** (create + run + where events show up)
- **Browser approvals lifecycle** (create session → request approval → approve → observe status)
- **Channels pairing flow** (configure adapter → inbound message → outbound response)
- **Env vars list** relevant to the above

Keep it minimal and runnable — no philosophy, no marketing.

---

## Rollback / cleanup
If anything goes sideways during this task:
```bash
# rollback only allowed-file edits
git restore -- docs/guardian/control-plane.md \
  scripts/verification/e2e_control_plane_checklist.sh \
  scripts/verification/README.md \
  docs/tasks/TASK_2026_02_06_016_end_to_end_verification_script_docs.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git status --porcelain -uall
```

---

## Commit plan
### Commit A (implementation)
**Message (exact):**
- `TASK-2026-02-06-016_end_to_end_verification_script_docs: add control plane docs + e2e checklist script`

**Stage + commit (exact):**
```bash
git status --porcelain -uall

git add \
  docs/guardian/control-plane.md \
  scripts/verification/e2e_control_plane_checklist.sh \
  scripts/verification/README.md

git commit --no-verify -m "TASK-2026-02-06-016_end_to_end_verification_script_docs: add control plane docs + e2e checklist script"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
Fill in this task artifact summary + campaign mapping placeholders.

**Message (exact):**
- `TASK-2026-02-06-016_end_to_end_verification_script_docs: docs finalize + mapping`

**Stage + commit (exact):**
```bash
git status --porcelain -uall

git add \
  docs/tasks/TASK_2026_02_06_016_end_to_end_verification_script_docs.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-016_end_to_end_verification_script_docs: docs finalize + mapping"

git log -1 --oneline
```

---

## Campaign mapping line (update during Commit B)
Update the campaign file(s) with the real hashes after both commits exist:
- `TASK-2026-02-06-016_end_to_end_verification_script_docs -> [<commitA>, <commitB>]`

---

## Notes / Summary (fill during execution)
- **Commands run + outcomes:**
  - (paste outputs or short pass/fail notes)
- **Files changed:**
  - (list actual)
- **Gotchas / follow-ups:**
  - (only if discovered; otherwise “none”)

