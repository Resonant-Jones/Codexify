100%. This audit is campaign-worthy—because it’s not “fix a bug,” it’s “define the contract of the world.” 🧭

And the single-user-first decision is a power move. It lets you harden sovereignty + safety without drowning in multi-tenant complexity.

Single-user-first, but not naïve

Think of it like this:
 • Single-user is an identity model (“one principal, local machine, local vault”).
 • Multi-tenant is a deployment topology (hosted service, many principals).

You can absolutely build the identity model first, then later add topology as an optional layer. That’s the clean path.

Also: your “valuable + not valuable” paradox is real. When everyone can self-host, the value shifts from “license” to:
 • distribution & updates
 • ops simplicity
 • trust & verification
 • curated flows/plugins
 • hosted convenience for non-nerds

So you don’t have to decide “SaaS empire” today. You just need to avoid painting yourself into a corner. 🧱

⸻

Campaign: CAMPAIGN_2026_02_16_SINGLE_USER_SECURITY_BASELINE

Goal

Convert the security audit into a single-user sovereignty baseline:
 • minimal egress by default
 • explicit opt-ins for anything leaving the machine
 • remove “accidental multi-tenant” footguns (like trusting headers)
 • unify config sources so security posture is predictable

Definition of Done
 • Local-first defaults are enforced at runtime.
 • “Single user” identity is explicit and non-spoofable.
 • Federation/egress routes are gated behind explicit configuration.
 • Config coherence: one settings system is authoritative (or strict startup assertion prevents conflicting use).
 • Full backend test suite passes.

⸻

Campaign Task Index 

Phase 1 — Sovereignty locks (highest ROI)
 1. TASK-2026-02-16-001_single_user_identity_contract
 • Replace “default user” + header-trust with a single-user principal derived server-side.
 • Reject X-User-Id except in explicit dev/test mode.
 2. TASK-2026-02-16-002_lock_down_egress_by_default
 • Enforce explicit opt-in for any cloud provider usage (OpenAI/Groq/Elevenlabs/federation/webhooks).
 • Add an allowlist / “local-only mode” gate that fails closed.
 3. TASK-2026-02-16-003_namespace_vector_retrieval_single_user
 • Even single-user needs namespace boundaries (thread/project) to prevent cross-context leakage.
 • Add namespace metadata + filter support in vector store queries.

Phase 2 — Coherence & operability
 4. TASK-2026-02-16-004_config_unification_or_startup_assertions
 • Reduce dual settings systems or add strict checks so they can’t disagree silently.
 5. TASK-2026-02-16-005_federation_guardrails
 • Federation endpoints off by default.
 • If enabled: auth + signed trust policy (even for single-user deployments, because “phone sharing” and “LAN peers” exist).

Phase 3 — Cleanup that prevents future drift
 6. TASK-2026-02-16-006_plugin_loader_consolidation
 7. TASK-2026-02-16-007_docs_alignment_for_security_posture
 8. TASK-2026-02-16-008_outbox_delivery_safety_review (optional; more “platform” than single-user)

⸻

Codexify Task Prompt (Task 001)

Here’s the first atomic task prompt, runner-ready.

<Codexify>

Context:

You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
 1. Perform the described edit only in the specified files.
 2. Run the appropriate test suite based on what was modified:
• Backend-only changes:
 • Run: pytest -v
 3. If tests pass (or relevant checks succeed):
 • Stage modified files with git add.
 • Commit with the provided message.
 4. Output:
 • Summary of what changed (files + functions).
 • Test results.
 • Git commit hash.

⸻

🧩 Task Description

TASK-2026-02-16-001_single_user_identity_contract

Intent: Codexify is single-user-first. Server-side identity must be explicit and not spoofable. Client-provided X-User-Id must not be trusted in production paths.

This change belongs in:
 • guardian/core/dependencies.py
 • guardian/routes/memory.py
 • guardian/routes/channels.py
 • guardian/routes/personal_facts.py
 • (any other routes that accept/consume X-User-Id directly, but keep scope tight: only update call sites found via ripgrep)

Edits:
 1. Introduce a single-user principal helper (server-derived):
 • In guardian/core/dependencies.py, add a function like:
 • get_single_user_id() that returns a stable user id (e.g. "local") or derives from a configured value (e.g. CODEXIFY_SINGLE_USER_ID).
 • Ensure this is used in request contexts instead of trusting headers.
 2. Deprecate header-trust:
 • In the routes listed above, replace any use of X-User-Id as the authoritative user with server-derived get_single_user_id().
 • Allow X-User-Id only in tests/dev mode if needed, but it must be gated behind an explicit DEBUG/LOCAL_DEV flag and never be the default behavior.
 3. Add/adjust tests:
 • Update existing route tests to reflect the single-user principal behavior.
 • Add at least one test ensuring X-User-Id does not override the server-derived user id in non-debug mode.

Commands:
 • Search for header trust sites:
 • rg -n \"X-User-Id\" guardian/routes guardian/core -S
 • Run tests:
 • pytest -v

Commit:

git add guardian/core/dependencies.py guardian/routes/memory.py guardian/routes/channels.py guardian/routes/personal_facts.py
git commit -m "Security: enforce server-derived single-user identity (no X-User-Id trust)"

⸻

✅ Expected Output
 • Confirmation of code changes.
 • Passing pytest -v summary.
 • Git commit hash.

</Codexify>

⸻


# CAMPAIGN_2026_02_16_HARDENING_SECURITY.md

This file is the **canonical source of truth** for the security hardening campaign. All task artifacts, mapping, and campaign state must be derived from this file.

---

## Activation / Invocation

After completing each task, Codex must:
1. Return to this campaign file before starting the next task.
2. Ensure the corresponding artifact file exists under `docs/tasks/TASK_2026_02_16_<NN>_<slug>.md` (create if missing, using the campaign’s naming convention).
3. For every task, use a two-phase commit:
   - **Commit A:** All code and test changes.
   - **Commit B:** All documentation: the task artifact file and updates to the "Final Mapping (authoritative)" section in this campaign file.

---

## Metadata

- **Campaign ID:** CAMPAIGN_2026_02_16_HARDENING_SECURITY
- **Canonical:** This file (`docs/Campaign/CAMPAIGN_2026_02_16_HARDENING_SECURITY.md`)
- **Scope:** Security hardening for single-user-first, local-sovereignty baseline.
- **Start Date:** 2026-02-16
- **Status:** In progress

## Goal

Establish a hardened, predictable security baseline for single-user deployments:
- Minimal egress by default
- Explicit opt-ins for any external communication
- Remove accidental multi-tenant footguns (e.g., trusting headers)
- Unify config so security posture is predictable

## Definition of Done

- Local-first defaults are enforced at runtime
- “Single user” identity is explicit and non-spoofable
- Federation/egress routes are gated behind explicit configuration
- Config coherence: one settings system is authoritative (or strict startup assertion prevents conflicting use)
- Full backend test suite passes

---

## Task Index

| # | Task Name | Artifact Path |
|---|-----------|--------------|
| 1 | Single User Identity Contract | docs/tasks/TASK_2026_02_16_01_single_user_identity_contract.md |
| 2 | Lock Down Egress by Default | docs/tasks/TASK_2026_02_16_02_lock_down_egress_by_default.md |
| 3 | Namespace Vector Retrieval Single User | docs/tasks/TASK_2026_02_16_03_namespace_vector_retrieval_single_user.md |
| 4 | Config Unification or Startup Assertions | docs/tasks/TASK_2026_02_16_04_config_unification_or_startup_assertions.md |
| 5 | Federation Guardrails | docs/tasks/TASK_2026_02_16_05_federation_guardrails.md |
| 6 | Plugin Loader Consolidation | docs/tasks/TASK_2026_02_16_06_plugin_loader_consolidation.md |
| 7 | Docs Alignment for Security Posture | docs/tasks/TASK_2026_02_16_07_docs_alignment_for_security_posture.md |
| 8 | Outbox Delivery Safety Review | docs/tasks/TASK_2026_02_16_08_outbox_delivery_safety_review.md |

---

## Final Mapping (authoritative)

| Task Artifact | Commit Hash (Code/Tests) | Commit Hash (Docs/Mapping) |
|--------------|--------------------------|---------------------------|
| TASK_2026_02_16_01_single_user_identity_contract.md | `10322d4a091d340353de6b61f984954da2a10318` | `4f74c22e19027b7afccd9eb69bcd3d66e2394be8` |
| TASK_2026_02_16_02_lock_down_egress_by_default.md   | `6841529bec1f1bb575d082b866cd1a1842a96ea3` | `2091b4d829132ca49954e6a9b2753f57ec640db9` |
| TASK_2026_02_16_03_namespace_vector_retrieval_single_user.md | `a30da6248d36cb4ec7e3ce78e2adfe33248f8626` | `<this-commit>` |
| TASK_2026_02_16_04_config_unification_or_startup_assertions.md | `<hash-a4>` | `<hash-b4>` |
| TASK_2026_02_16_05_federation_guardrails.md | `<hash-a5>` | `<hash-b5>` |
| TASK_2026_02_16_06_plugin_loader_consolidation.md | `<hash-a6>` | `<hash-b6>` |
| TASK_2026_02_16_07_docs_alignment_for_security_posture.md | `<hash-a7>` | `<hash-b7>` |
| TASK_2026_02_16_08_outbox_delivery_safety_review.md | `<hash-a8>` | `<hash-b8>` |

---

## Codexify Task Prompts

---

### Task 1: Single User Identity Contract

**This change belongs in `guardian/core/dependencies.py`, `guardian/routes/memory.py`, `guardian/routes/channels.py`, `guardian/routes/personal_facts.py`.**

**Files expected to change:**
- guardian/core/dependencies.py
- guardian/routes/memory.py
- guardian/routes/channels.py
- guardian/routes/personal_facts.py
- (any other files found to use or trust X-User-Id directly; restrict scope to those found via `rg -n "X-User-Id" guardian/routes guardian/core -S`)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/core/dependencies.py guardian/routes/memory.py guardian/routes/channels.py guardian/routes/personal_facts.py
git commit -m "Security: enforce server-derived single-user identity (no X-User-Id trust)"
```

**Expected Output:**
- Confirmation of code changes and affected functions
- Passing pytest -v summary
- Git commit hash

---

### Task 2: Lock Down Egress by Default

**This change belongs in `guardian/core/config.py`, `guardian/core/egress.py`, and any egress-related route or provider files (OpenAI, Groq, Elevenlabs, federation, webhooks).**

**Files expected to change:**
- guardian/core/config.py
- guardian/core/egress.py
- guardian/routes/federation.py
- guardian/routes/webhooks.py
- guardian/providers/openai.py
- guardian/providers/groq.py
- guardian/providers/elevenlabs.py
- (determine exact egress points with `rg -n "openai|groq|elevenlabs|federat|webhook" guardian/`)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/core/config.py guardian/core/egress.py guardian/routes/federation.py guardian/routes/webhooks.py guardian/providers/openai.py guardian/providers/groq.py guardian/providers/elevenlabs.py
git commit -m "Security: enforce explicit opt-in for all egress; add allowlist/local-only mode"
```

**Expected Output:**
- Egress is denied by default unless explicitly configured
- Passing pytest -v summary
- Git commit hash

---

### Task 3: Namespace Vector Retrieval Single User

**This change belongs in `guardian/core/vector_store.py` and any routes or services that perform vector retrieval (e.g., `guardian/routes/memory.py`, `guardian/routes/documents.py`).**

**Files expected to change:**
- guardian/core/vector_store.py
- guardian/routes/memory.py
- guardian/routes/documents.py
- (use `rg -n "vector|namespace" guardian/` to find all relevant locations)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/core/vector_store.py guardian/routes/memory.py guardian/routes/documents.py
git commit -m "Security: add namespace metadata and filtering to vector store queries"
```

**Expected Output:**
- Namespace boundaries enforced in vector queries
- Passing pytest -v summary
- Git commit hash

---

### Task 4: Config Unification or Startup Assertions

**This change belongs in `guardian/core/config.py` and the main application startup (likely `main.py` or `guardian/app.py`).**

**Files expected to change:**
- guardian/core/config.py
- guardian/app.py (or main.py, as discovered)
- (find all config entrypoints via `rg -n "config|settings" guardian/`)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/core/config.py guardian/app.py
git commit -m "Security: unify configuration or add strict startup assertions for config coherence"
```

**Expected Output:**
- Single authoritative config system or startup assertion if incoherence is detected
- Passing pytest -v summary
- Git commit hash

---

### Task 5: Federation Guardrails

**This change belongs in `guardian/routes/federation.py`, `guardian/core/config.py`, and any federation-related authentication utilities.**

**Files expected to change:**
- guardian/routes/federation.py
- guardian/core/config.py
- guardian/core/auth.py (if federation trust policy is enforced here)
- (find federation endpoints using `rg -n "federat" guardian/`)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/routes/federation.py guardian/core/config.py guardian/core/auth.py
git commit -m "Security: federation endpoints off by default; require signed trust policy and auth if enabled"
```

**Expected Output:**
- Federation endpoints are disabled by default; enabling requires config and signed policy
- Passing pytest -v summary
- Git commit hash

---

### Task 6: Plugin Loader Consolidation

**This change belongs in `guardian/core/plugins.py` and any plugin loading call sites (e.g., `guardian/app.py`, `guardian/routes/plugins.py`).**

**Files expected to change:**
- guardian/core/plugins.py
- guardian/app.py
- guardian/routes/plugins.py
- (find plugin loader sites with `rg -n "plugin" guardian/`)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/core/plugins.py guardian/app.py guardian/routes/plugins.py
git commit -m "Security: consolidate plugin loader logic to a single entrypoint"
```

**Expected Output:**
- Plugin loader logic is unified and hardened
- Passing pytest -v summary
- Git commit hash

---

### Task 7: Docs Alignment for Security Posture

**This change belongs in the documentation under `docs/`, specifically `docs/SECURITY.md`, `docs/CONFIGURATION.md`, and any other docs referencing security defaults.**

**Files expected to change:**
- docs/SECURITY.md
- docs/CONFIGURATION.md
- (use `rg -n "security|egress|user|federat|plugin" docs/` to find all relevant docs)

**Test commands:**
- No tests apply (docs-only)

**Git commands:**
```sh
git add docs/SECURITY.md docs/CONFIGURATION.md
git commit -m "Docs: align documentation with new security posture and defaults"
```

**Expected Output:**
- Documentation reflects new security defaults and configuration
- Git commit hash

---

### Task 8: Outbox Delivery Safety Review

**This change belongs in `guardian/core/outbox.py` and any outbox delivery or retry logic (e.g., `guardian/routes/outbox.py`).**

**Files expected to change:**
- guardian/core/outbox.py
- guardian/routes/outbox.py
- (use `rg -n "outbox|deliver" guardian/` to locate all relevant logic)

**Test commands:**
- `pytest -v`

**Git commands:**
```sh
git add guardian/core/outbox.py guardian/routes/outbox.py
git commit -m "Security: review and harden outbox delivery logic for single-user safety"
```

**Expected Output:**
- Outbox delivery logic reviewed and hardened
- Passing pytest -v summary
- Git commit hash

---
