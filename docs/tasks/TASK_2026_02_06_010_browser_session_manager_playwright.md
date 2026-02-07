# TASK-2026-02-06-010 — Browser Session Manager (Playwright)

- **Task-ID:** TASK-2026-02-06-010_browser_session_manager_playwright
- **Goal:** Controlled browser contexts with persisted profiles (minimal, testable, and policy-gated).

## Objective

Add a minimal “browser session manager” layer for Playwright that can:

- create/get/list/close sessions
- persist per-session user-data directories under `STORAGE_BASE_PATH/browser_profiles/`
- enforce security guardrails (URL allowlist, max sessions, TTL)
- expose a tiny command surface (`navigate`, `screenshot`, `click`, `type`, `content`) via a minimal bridge abstraction

## Non-goals

- No full agent browsing automation or multi-step workflows.
- No complex DOM tooling. Keep the bridge minimal and explicit.
- No UI work.

---

# Deterministic Execution Constraints (Runner_Protocol)

## Allowed files (STRICT)

Only edit/create files in this allowlist:

- `guardian/browser/session_manager.py` (new or existing)
- `guardian/browser/cdp_bridge.py` (new or existing)
- `guardian/browser/__init__.py` (if needed for exports; optional)
- `guardian/core/config.py` (only if required to add env-backed config keys)
- `guardian/tests/test_browser_session_manager.py` (new)
- `guardian/tests/test_browser_allowlist.py` (new, optional—can combine into one test file)

Docs updates allowed only in Commit B:

- `docs/tasks/TASK_2026_02_06_010_browser_session_manager_playwright.md`
- `docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md` **and/or**
  `docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md` (whichever contains this task mapping)

**Do not touch** any other files.

## Commit mode

Two-phase:

- **Commit A:** implementation + tests only
- **Commit B:** docs finalize + campaign mapping update

## Dependencies / Prereqs (run exactly)

From repo root:

```bash
git status --porcelain -uall
python --version
pytest --version

Optional sanity (only if Playwright is already part of your env):

python -c "import playwright; print('playwright import ok')"

If Playwright is not installed, do not add dependencies in this task. Instead:
 • write code defensively
 • mark tests to skip when Playwright import/launch is unavailable (deterministically)

⸻

Implementation Plan

Required behavior

SessionManager

Create BrowserSessionManager with:
 • Storage path: profiles live at:
 • STORAGE_BASE_PATH/browser_profiles/<session_id>/
 • Session identity: session_id is a unique string (uuid is fine).
 • State: track created_at, last_used_at, and expires_at (TTL).
 • Limits:
 • BROWSER_MAX_SESSIONS (default small, e.g. 2)
 • BROWSER_SESSION_TTL_SECONDS (default e.g. 900)
 • Allowlist:
 • BROWSER_URL_ALLOWLIST (comma-separated hostnames or suffix patterns)
 • Block anything not matching allowlist with a clear exception.

Minimal bridge (cdp_bridge)

Expose a tiny interface used by SessionManager. Keep it intentionally boring:
 • navigate(url: str) -> None
 • screenshot(path: str | None = None) -> bytes (bytes preferred; optional file write)
 • click(selector: str) -> None
 • type(selector: str, text: str, clear: bool = False) -> None
 • content() -> str

Implementation can wrap a Playwright Page, not actual CDP. The name is fine; abstraction is the key.

Security rules
 • Validate URL host against allowlist before navigating.
 • Enforce max sessions at create time.
 • TTL expiration should close the underlying browser context and delete it from the active registry.
 • Ensure “close session” is idempotent.

⸻

Command Checklist (copy/paste runnable)

1) Locate existing patterns (no edits yet)

rg -n "STORAGE_BASE_PATH|storage_base_path" guardian | head -n 50
rg -n "Playwright|playwright|chromium|browser" guardian | head -n 50
rg -n "ALLOWLIST|allowlist|URL_ALLOWLIST|domain allow" guardian | head -n 50

2) Implement session manager + bridge (allowed files only)

After edits:

python -m compileall guardian/browser/session_manager.py guardian/browser/cdp_bridge.py
git status --porcelain -uall

3) Add tests

Write tests that are deterministic and do not require external services.
If Playwright cannot be imported/launched, tests must skip with a clear reason.

Run:

pytest -q guardian/tests/test_browser_session_manager.py -q
# if you split tests:
pytest -q guardian/tests/test_browser_allowlist.py -q
pytest -q

4) Pre-commit sanity

git diff --stat
git status --porcelain -uall


⸻

Expected Outputs (success signals)
 • pytest exits 0 (with allowable skips if Playwright unavailable).
 • Tests cover:
 • session lifecycle (create/get/list/close)
 • TTL expiration closes session
 • allowlist blocks forbidden domains
 • max sessions enforcement
 • git status --porcelain -uall shows only allowed-file changes.

⸻

Rollback / Cleanup

To abandon changes:

git restore --staged --worktree -- guardian/browser/session_manager.py guardian/browser/cdp_bridge.py guardian/browser/__init__.py guardian/core/config.py guardian/tests/test_browser_session_manager.py guardian/tests/test_browser_allowlist.py
git status --porcelain -uall

If new files were created and you want them gone:

git clean -fd -- guardian/browser guardian/tests
git status --porcelain -uall


⸻

Commit Plan

Commit A (implementation + tests)

Stage only implementation + tests:

git add \
  guardian/browser/session_manager.py \
  guardian/browser/cdp_bridge.py \
  guardian/browser/__init__.py \
  guardian/core/config.py \
  guardian/tests/test_browser_session_manager.py \
  guardian/tests/test_browser_allowlist.py

git status --porcelain -uall
git commit --no-verify -m "TASK-2026-02-06-010_browser_session_manager_playwright: add session manager + allowlist + TTL"
git log -1 --oneline

Record resulting hash as Commit A.

Commit B (docs finalize + mapping)

Update this task artifact with:
 • commands run + results
 • a short summary of changes
 • Commit A hash
 • final git status --porcelain -uall output

Update campaign mapping line to:
 • TASK-2026-02-06-010_browser_session_manager_playwright -> [78b83ad1, d2814e97]

Then:

git add \
  docs/tasks/TASK_2026_02_06_010_browser_session_manager_playwright.md \
  docs/Campaign/CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git status --porcelain -uall
git commit --no-verify -m "TASK-2026-02-06-010_browser_session_manager_playwright: docs finalize + mapping"
git log -1 --oneline

Record resulting hash as Commit B.

⸻

Notes / Guardrails
 • Keep Playwright usage minimal and behind the bridge.
 • Prefer predictable exceptions with clear messages:
 • allowlist violation
 • session limit exceeded
 • session not found
 • session expired
 • Avoid adding new dependencies or wiring routes in this task.

---

## Execution Summary (Commit B)

- Commands run:
  - `git status --porcelain -uall`
  - `python --version`
  - `pytest --version`
  - `python -c "import playwright; print('playwright import ok')"` (failed: `ModuleNotFoundError`)
  - `rg -n "STORAGE_BASE_PATH|storage_base_path" guardian | head -n 50`
  - `rg -n "Playwright|playwright|chromium|browser" guardian | head -n 50`
  - `rg -n "ALLOWLIST|allowlist|URL_ALLOWLIST|domain allow" guardian | head -n 50`
  - `python -m compileall guardian/browser/session_manager.py guardian/browser/cdp_bridge.py`
  - `pytest -q guardian/tests/test_browser_session_manager.py -q`
  - `pytest -q guardian/tests/test_browser_allowlist.py -q`
  - `pytest -q`
- Key results:
  - Playwright is not installed locally; implementation is defensive and import-gated.
  - Browser session manager and bridge added under `guardian/browser/`.
  - Full test suite run completed with exit code `0`.
- Files changed in Commit A:
  - `guardian/browser/session_manager.py`
  - `guardian/browser/cdp_bridge.py`
  - `guardian/browser/__init__.py`
  - `guardian/tests/test_browser_session_manager.py`
  - `guardian/tests/test_browser_allowlist.py`
- Commit A: `78b83ad1`
- Campaign mapping line:
  - `TASK-2026-02-06-010_browser_session_manager_playwright -> [78b83ad1, d2814e97]`
