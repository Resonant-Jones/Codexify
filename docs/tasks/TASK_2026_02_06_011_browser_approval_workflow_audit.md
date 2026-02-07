TASK-2026-02-06-011 — Browser Approval Workflow + Audit

**Goal:** Dangerous ops require explicit approval + reasons.

**Deliverables:**

* `guardian/browser/approval.py`
* routes:

  * list approvals
  * approve/deny with reason
* migrations:

  * `browser_approvals`
  * `browser_audit_log`

**Approval required for:**

* `evaluate`
* cookie set/get
* navigation to non-allowlisted domains (if you allow “ask to approve” mode)

**Tests:**

* blocked op creates approval request
* approval transitions enforced (no double-approve)
* audit log always written

---

# TASK-2026-02-06-011_browser_approval_workflow_audit: Browser Approval Workflow + Audit

- **Task-ID:** TASK-2026-02-06-011_browser_approval_workflow_audit
- **Campaign:** CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- **Branch (expected):** `campaign/2026-02-06/guardian-parity-control-plane`
- **Commit mode:** two-phase (Commit A = implementation, Commit B = docs finalize + mapping)

## Goal
Add an explicit **approval workflow** for dangerous browser operations, and an **audit log** for all browser actions. Any blocked operation must create an approval request, and no dangerous op may execute without approval.

## Background
We’re adding a browser-control surface. Some operations are high-risk (exfiltration, account takeover, navigation to hostile domains). These must be gated behind explicit approval with a human-readable reason.

## Scope
### In-scope
- An approval request lifecycle: `PENDING -> APPROVED|DENIED` (no double-approve / double-deny).
- Approval is required for:
  - `evaluate`
  - cookie set/get
  - navigation to non-allowlisted domains (when running in “ask to approve” mode)
- Audit log entry is written for **every** browser action attempt (allowed, blocked, approved/denied).
- Minimal API routes:
  - list approvals
  - approve/deny with reason
- DB persistence via migrations:
  - `browser_approvals`
  - `browser_audit_log`
- Tests proving:
  - blocked op creates approval request
  - transitions enforced
  - audit log always written

### Out-of-scope
- UI for approvals (CLI/manual curl is enough).
- Complex domain allowlisting UX (just enforce an allowlist check and create approval request when violated).
- Full RBAC policy engine.

## Allowed files (STRICT)
Only modify/add within the paths below.

### Implementation (Commit A)
- `guardian/browser/approval.py`
- `guardian/browser/__init__.py`
- `guardian/routes/browser.py` *(create if missing)*
- `guardian/routes/__init__.py` *(only if needed to register the route module)*
- `guardian/db/models/browser_approvals.py` *(create if missing)*
- `guardian/db/models/__init__.py` *(only if needed to expose models)*
- `guardian/db/migrations/versions/*_browser_approvals*.py`
- `guardian/db/migrations/versions/*_browser_audit_log*.py`
- `guardian/tests/realtime/test_browser_approval_workflow.py` *(create or update)*

### Docs (Commit B)
- `docs/tasks/TASK_2026_02_06_011_browser_approval_workflow_audit.md`
- `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md`

If you need to touch anything else, STOP and update this Allowed Files list first.

## Dependencies / prereqs
Run these first and record results in the “Commands run + key outputs” section.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# clean tree check
git status --porcelain -uall

# confirm python env
python --version
python -m pytest --version || true

# optional: show current alembic heads (if alembic is present)
python -m alembic heads || true
```

## Command checklist
Execute in order. Copy/paste commands exactly.

### 1) Recon: locate existing browser surfaces
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

rg -n "browser" guardian | head
rg -n "allowlist|allow list|domain" guardian | head
rg -n "audit" guardian/db guardian/routes guardian/browser || true
rg -n "approval" guardian || true

# locate router registration patterns
rg -n "include_router\(" guardian | head
rg -n "APIRouter\(" guardian/routes | head
```

### 2) Implement approval + audit primitives (allowed files only)
Implementation requirements:
- Provide a small, explicit API in `guardian/browser/approval.py` (names can vary, but must support):
  - create approval request
  - approve/deny with reason
  - check whether an operation is approved
  - write audit entries
- Enforce idempotence/transition rules: pending-only transitions.
- Ensure every action attempt writes an audit log entry.

### 3) Add routes for listing + approving/denying
Routes must:
- Require auth (reuse existing API key dependency pattern)
- Expose list + approve/deny (with reason)

### 4) Add DB models + migrations
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# If alembic is configured, generate a new migration (name can vary)
python -m alembic revision --autogenerate -m "browser approvals and audit log" || true

# Apply migrations (only if your dev DB is available)
python -m alembic upgrade head || true
```

### 5) Tests
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# run the most relevant test(s) first
python -m pytest -q guardian/tests/realtime/test_browser_approval_workflow.py -q || true

# then run broader suite if reasonable
python -m pytest -q || true
```

## Expected outputs (success signals)
- `git status --porcelain -uall` shows only allowed files modified.
- Tests:
  - `guardian/tests/realtime/test_browser_approval_workflow.py` passes.
  - If broader suite is run, no new regressions introduced.
- When a blocked operation is attempted in code/tests:
  - an approval request is created (`PENDING`)
  - an audit entry is written
  - operation does **not** execute until approved
- Approval transitions are enforced:
  - cannot approve/deny a non-pending request

## Rollback / cleanup
If you need to bail out:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard edits to tracked files
git restore -- \
  guardian/browser/approval.py \
  guardian/browser/__init__.py \
  guardian/routes/browser.py \
  guardian/routes/__init__.py \
  guardian/db/models/browser_approvals.py \
  guardian/db/models/__init__.py \
  guardian/tests/realtime/test_browser_approval_workflow.py \
  docs/tasks/TASK_2026_02_06_011_browser_approval_workflow_audit.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

# remove newly created migration(s) if present (adjust filenames as needed)
ls -1 guardian/db/migrations/versions | rg -n "browser_(approvals|audit)" || true
# rm guardian/db/migrations/versions/<new_migration>.py

git status --porcelain -uall
```

## Commit plan
### Commit A (implementation)
**Message (exact):**
- `TASK-2026-02-06-011_browser_approval_workflow_audit: browser approval workflow + audit log`

**Commands (exact):**
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# stage ONLY allowed implementation files that actually changed
git add \
  guardian/browser/approval.py \
  guardian/browser/__init__.py \
  guardian/routes/browser.py \
  guardian/routes/__init__.py \
  guardian/db/models/browser_approvals.py \
  guardian/db/models/__init__.py \
  guardian/db/migrations/versions/*_browser_approvals*.py \
  guardian/db/migrations/versions/*_browser_audit_log*.py \
  guardian/tests/realtime/test_browser_approval_workflow.py

git commit --no-verify -m "TASK-2026-02-06-011_browser_approval_workflow_audit: browser approval workflow + audit log"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
**Message (exact):**
- `TASK-2026-02-06-011_browser_approval_workflow_audit: docs finalize + mapping`

**Commands (exact):**
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# stage ONLY docs artifacts
git add \
  docs/tasks/TASK_2026_02_06_011_browser_approval_workflow_audit.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md

git commit --no-verify -m "TASK-2026-02-06-011_browser_approval_workflow_audit: docs finalize + mapping"

git log -1 --oneline
```

## Notes / results
(As you execute: paste command outputs, summarize diffs, and fill in the mapping line in the campaign file.)

### Commands run + key outputs
- `git status --porcelain -uall` (clean preflight)
- `python --version` -> `Python 3.13.9`
- `python -m pytest --version || true` -> `No module named pytest` in system python
- `python -m alembic heads || true` -> `No module named alembic` in system python
- `rg -n "browser" guardian | head`
- `rg -n "allowlist|allow list|domain" guardian | head`
- `rg -n "audit" guardian/db guardian/routes guardian/browser || true`
- `rg -n "approval" guardian || true`
- `rg -n "include_router\\(" guardian | head`
- `rg -n "APIRouter\\(" guardian/routes | head`
- `python -m alembic revision --autogenerate -m "browser approvals and audit log" || true` (skipped by missing module)
- `python -m alembic upgrade head || true` (skipped by missing module)
- `python -m pytest -q guardian/tests/realtime/test_browser_approval_workflow.py -q || true` (skipped by missing module)
- `python -m pytest -q || true` (skipped by missing module)
- `pytest -q guardian/tests/realtime/test_browser_approval_workflow.py -q` -> `4 passed`
- `pytest -q || true` -> suite reached `100%` with exit `0`

### Files changed
- `guardian/browser/approval.py`
- `guardian/browser/__init__.py`
- `guardian/routes/browser.py`
- `guardian/db/migrations/versions/b1a2c3d4e5f7_add_browser_approvals_table.py`
- `guardian/db/migrations/versions/c3d4e5f6a7b8_add_browser_audit_log_table.py`
- `guardian/tests/realtime/test_browser_approval_workflow.py`

### Mapping
- `TASK-2026-02-06-011_browser_approval_workflow_audit -> [5e486996, <commitB>]`
