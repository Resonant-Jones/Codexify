TASK 1 — IDDB Layer Enforcement (Control Plane Phase)

Objective

Formally enforce Identity Data Database (IDDB) separation at the storage and modeling boundary.

This task converts conceptual identity-layer separation into enforceable backend guarantees.

Scope

This task is backend-only.
Do not modify frontend code in this task.
Do not implement deep identity logic beyond flag gating.

Target Outcomes

- Diary threads are structurally prevented from contributing to identity modeling.
- Identity depth (light | deep) is persisted and enforced.
- Modeling exclusion is explicit, queryable, and test-covered.
- No silent promotion of diary content into imprint layers.

Files Likely Affected

This change belongs in backend identity + thread storage layers. Likely locations include:

- guardian/core/storage.py
- guardian/core/user_manager.py
- guardian/routes/chat.py
- any identity modeling or imprint-related module
- database schema / migration layer

If schema changes are required, create a proper migration.

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1. Database Schema Changes
   - Add `modeling_excluded BOOLEAN DEFAULT FALSE` to chat_threads.
   - Add `diary_mode BOOLEAN DEFAULT FALSE` to chat_threads.
   - Add `identity_depth TEXT CHECK (identity_depth IN ('light','deep')) DEFAULT 'light'` to users or projects (choose the correct boundary and document why).
   - Create migration if schema tooling exists.

2. Identity Modeling Enforcement
   - Update imprint / identity modeling pipeline to:
     - Ignore threads where diary_mode == TRUE.
     - Ignore threads where modeling_excluded == TRUE.
     - Only allow deep modeling logic if identity_depth == 'deep'.
   - Ensure light mode cannot accidentally persist deep identity traits.

3. Explicit Guard Rails
   - Add explicit guard clause in modeling entrypoint:
     - If diary_mode → abort modeling.
     - If modeling_excluded → abort modeling.
     - If identity_depth != 'deep' → prevent deep summarization.

4. Tests (Required)
   Add backend tests verifying:

   - Diary thread does not update imprint store.
   - modeling_excluded thread does not update imprint store.
   - identity_depth='light' prevents deep modeling execution.
   - identity_depth='deep' allows deep modeling path.

   Tests must fail before implementation and pass after.

5. Validation

   Run backend test suite:

   pytest -v

   Confirm no regressions in unrelated modules.

6. Commit

   Stage only modified files.
   Commit message:

   "Enforce IDDB layer separation with diary + identity_depth guards"

Output (Required)

- Summary of schema changes.
- List of modified files.
- Backend test results summary.
- Git commit hash.

Constraints

- Do not implement new persona logic in this task.
- Do not refactor prompt builder in this task.
- Do not modify event graph logic.
- Do not add frontend flags.

This task establishes the storage-level sovereignty boundary before higher-layer features are built.

---

Execution Notes (2026-02-16)

- Added explicit `chat_threads.diary_mode` and `chat_threads.modeling_excluded` schema/model support while preserving legacy `is_diary` and `exclude_from_identity` compatibility.
- Added persisted `projects.identity_depth` (`light|deep`) and wired backend lookup via `get_project_identity_depth`.
- Enforced identity modeling guardrails in imprint routes:
  - abort when diary/modeling-excluded flags are set
  - abort deep identity modeling requests unless project identity depth is `deep`
- Added deep-mode guard in chat completion route so `depth_mode=deep` downgrades to `normal` unless project identity depth is `deep`.
- Added/updated tests covering diary exclusion, modeling exclusion, and deep-mode gating behavior.
