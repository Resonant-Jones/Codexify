
TASK 5 — Persistent Imprint + Persona Storage (DB + Activation + Precedence)

Objective

Persist and enforce the memory-aware persona system’s configuration state in the backend by introducing durable storage for:

- Imprint_Zero (Light identity imprint)
- Persona definitions / masks
- Activation state (which imprint/persona is active)
- Resolution precedence rules (what wins when multiple sources exist)

This task makes persona/imprint selection a first-class backend contract rather than a transient UI state.

Scope

Backend-only for this task.
Do not modify frontend UI.
Do not implement new prompt assembly logic (Task 4).
Do not implement diary/identity modeling enforcement (Task 1).
Do not implement flow permissions (Task 2).

Correctness Invariants (Must Hold)

1) Single Active Imprint Per Scope
- At most one imprint is active per (user_id, project_id) scope.

2) Deterministic Persona Resolution
- Persona selection resolution must be deterministic and test-covered.

3) Clear Precedence Rules
Define and enforce precedence in code (documented and tested):

Persona precedence (highest → lowest):
1) Explicit persona specified on the request (runtime override)
2) User-selected active persona for the current (user_id, project_id)
3) Project default persona (if supported)
4) System default persona

Imprint precedence (highest → lowest):
1) Active imprint for (user_id, project_id)
2) User default imprint
3) System default imprint

4) No Silent Cross-Scope Bleed
- Activating a persona/imprint for one project must not affect other projects.

Data Model

Choose the minimal schema compatible with current storage conventions.

A) Imprints
- imprint_id (pk)
- user_id
- project_id (nullable)
- name
- content (text/json) — the actual imprint prompt block
- is_active (bool)
- created_at
- updated_at

Constraints:
- Unique active constraint for (user_id, project_id) where is_active=true.

B) Personas
- persona_id (pk)
- user_id
- project_id (nullable)
- name
- content (text/json) — persona prompt block / descriptor
- is_active (bool)
- created_at
- updated_at

Constraints:
- Unique active constraint for (user_id, project_id) where is_active=true.

C) Optional: Defaults
If the repo already models user/project defaults elsewhere, use that instead of adding new tables.
If not, keep defaults implicit (system default) and only store active selections.

Files Likely Affected

This change belongs in backend storage + models + routes/services that resolve persona/imprint.
Likely locations include:

- guardian/core/db.py (or equivalent DB layer)
- guardian/core/storage.py
- guardian/core/user_manager.py (if user scoped)
- guardian/routes/* (only if activation endpoints exist)
- migration tooling (alembic or existing system)

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Add Database Tables + Migration
- Add tables for imprints and personas per the Data Model above.
- Implement the unique active constraint for each (user_id, project_id).
- Create/extend migrations using the repo’s existing tooling.

2) Implement Store/Repository Methods
Add repository methods (names can vary to match conventions) that provide:

Imprints:
- create_imprint(user_id, project_id, name, content)
- list_imprints(user_id, project_id)
- get_active_imprint(user_id, project_id)
- activate_imprint(user_id, project_id, imprint_id)
  - must deactivate any previously active imprint in the same scope atomically

Personas:
- create_persona(user_id, project_id, name, content)
- list_personas(user_id, project_id)
- get_active_persona(user_id, project_id)
- activate_persona(user_id, project_id, persona_id)
  - must deactivate any previously active persona in the same scope atomically

3) Implement Resolution Functions (Deterministic)
Add pure functions (or service methods) used by request handlers:

- resolve_persona(user_id, project_id, requested_persona_id|name|None) -> Persona
- resolve_imprint(user_id, project_id) -> Imprint

They must implement the precedence rules documented above.

4) Wire Into Existing Generation Path (Backend)
- Update the backend generation entrypoint so it resolves persona + imprint via the repository.
- Do not change prompt assembly formatting; just provide the blocks to existing assembly (Task 4 handles formatting).

5) Tests (Required)
Add backend tests that fail before and pass after:

- Only one active imprint exists per scope after activation (previous deactivated).
- Only one active persona exists per scope after activation.
- Activating in project A does not affect project B.
- resolve_persona respects precedence:
  - explicit request override beats active persona
  - active persona beats system default
- resolve_imprint respects precedence and scope.

6) Validation
Run backend tests:

pytest -v

7) Commit
Stage only modified files.
Commit message:

"Persist personas and imprints with activation + deterministic resolution"

Output (Required)

- Summary of schema/migration changes.
- List of modified files.
- Backend test results summary.
- Git commit hash.

Constraints

- Do not add frontend UI.
- Do not implement prompt builder changes (Task 4).
- Do not alter diary modeling rules (Task 1).
- Do not add flow permission logic (Task 2).

This task makes persona + imprint selection durable and non-spooky across sessions.

---

Execution Notes (2026-02-16)

- Extended imprint repository API in `guardian/cognition/imprints/store.py`:
  - added `create_imprint`, `list_imprints`
  - expanded activation API to support both:
    - legacy `activate_imprint(imprint_id)`
    - scoped `activate_imprint(user_id, project_id, imprint_id)`
  - scoped activation now explicitly validates scope and supersedes prior active rows atomically
- Extended persona repository API in `guardian/cognition/personas/store.py`:
  - added `create_persona`, `list_personas`, `get_persona_by_id`, `activate_persona`
  - refactored `set_persona` to create + activate through the scoped activation path
  - scoped activation validates scope and deactivates prior active rows atomically
- Added deterministic precedence resolver module `guardian/cognition/identity_resolution.py`:
  - `resolve_persona(...)` precedence:
    1) explicit request override
    2) active scope persona
    3) project-default/user-default persona (`project_id=None`)
    4) system default
  - `resolve_imprint(...)` precedence:
    1) active scope imprint
    2) user default imprint (`project_id=None`)
    3) system default
- Wired resolution into generation path via `guardian/cognition/system_prompt_builder.py`:
  - prompt assembly now consumes resolved persona/imprint outputs instead of direct active-only lookups
- Added tests in `tests/system_prompt/test_identity_resolution.py` covering:
  - single-active-per-scope behavior for imprints/personas
  - no cross-project activation bleed
  - persona precedence (explicit override > active > system default)
  - imprint precedence (scope > user default > system default)
