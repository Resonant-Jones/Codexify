Alright. Saddle up. 🤠
We’re not writing dreams anymore — we’re writing an execution lattice.

You asked to:

* Turn this into a **Campaign Runner Index**
* Generate **Codexify Task Prompts**
* Use your surfaced context
* Treat the uploaded docs as templates only
* Not reuse their internal example data

Good. That means we design a clean Phase-Next campaign focused on:

* Memory architecture separation (IDDB)
* Flow system hardening + sandboxing
* CLI surface expansion
* Agent-operable app primitives
* Secure pre-authenticated flows
* Prompt assembly architecture (imprint/persona/system docs)
* Event Graph + Playbook alignment
* Token cost awareness + UI transparency

We are now entering the **Control Plane Phase**.

---

# 🧭 CAMPAIGN RUNNER INDEX

## CAMPAIGN-2026-02-Phase-ControlPlane

**Repo:** Codexify
**Goal:** Transition from conceptual architecture to enforceable runtime boundaries
**Branch Strategy:** One atomic branch per task
**Runner Protocol:** Codexify Task Template (strict)

---

## 🎯 Definition of Done

* Guardian can operate app primitives safely.
* Flows are pre-authenticated and non-interruptible.
* IDDB layers are enforced at storage boundary.
* Persona + Imprint system is persistent.
* CLI surface is sandboxed per project root.
* System prompt assembly is modular + token-aware.
* Event Graph emits traceable lineage events.
* No sensitive data can be exfiltrated via imported flows.

---

# 🗂️ TASK SEQUENCE OVERVIEW

We’ll break this into 8 atomic execution tasks.

Each below includes:

* Strategic intent
* Codexify Task Prompt (ready for automation)

---

# 🧱 TASK 1 — IDDB Layer Enforcement

## Objective

Separate:

* Diary (chat history)
* Light Imprint
* Deep Identity (optional)
* Persona overlays

Enforce modeling exclusion flags.

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
1. Implement identity layer separation in backend storage:
   - Add explicit modeling_excluded flag to chat_threads.
   - Add identity_depth enum to users or projects (light | deep).
   - Add diary_mode boolean to threads.
2. Ensure diary_mode threads are excluded from identity modeling logic.
3. Update memory ingestion pipeline to respect these flags.
4. Add tests verifying:
   - Diary threads never update imprint.
   - Deep modeling only runs if identity_depth == deep.
5. Run backend tests.
6. Commit atomically.

Output:
- Summary of files changed.
- Test results.
- Commit hash.
```

---

# 🔐 TASK 2 — Flow Authentication Boundary

## Objective

Flows must:

* Be pre-authenticated
* Not allow mid-flow auth injection
* Require explicit user confirmation for external URLs
* Reject transferable flow imports

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:
1. Implement FlowExecutionContext model:
   - pre_authenticated: bool
   - allowed_scopes: list[str]
   - external_domains: list[str]
2. Enforce that flow steps cannot request new auth during execution.
3. Require explicit user confirmation for any step targeting new external domains.
4. Disable transferable flow import; only allow user-created flows.
5. Add tests:
   - Flow fails if domain not pre-approved.
   - Flow cannot escalate permissions.
6. Run backend tests.
7. Commit atomically.

Output:
- Summary of flow boundary enforcement.
- Test results.
- Commit hash.
```

---

# 🧪 TASK 3 — CLI Sandboxed Project Execution

## Objective

Codexify CLI installs into project root and restricts command execution to that directory.

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo.

Instructions:
1. Modify CLI runner to:
   - Detect project root.
   - Restrict file operations outside root.
   - Reject system-level commands.
2. Add sandbox validator layer before command execution.
3. Add tests:
   - Attempted ../ escape fails.
   - Allowed in-project command passes.
4. Run backend tests.
5. Commit atomically.

Output:
- CLI sandbox description.
- Test results.
- Commit hash.
```

---

# 🧠 TASK 4 — Modular System Prompt Builder

## Objective

Implement structured prompt assembly:

* Immutable base
* Imprint block
* Persona block
* System docs block
* Token estimation metadata

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo.

Instructions:
1. Create system_prompt_builder module.
2. Refactor prompts.py to accept structured inputs instead of fetching internally.
3. Add token estimation logic (char/4 heuristic if tokenizer unavailable).
4. Return metadata:
   - estimated_tokens
   - segment breakdown
5. Update chat route to use builder.
6. Add tests verifying:
   - Builder returns one primary system message.
   - Metadata is included.
7. Run backend tests.
8. Commit atomically.

Output:
- Files changed.
- Test results.
- Commit hash.
```

---

# 📚 TASK 5 — Persistent Imprint + Persona Storage

## Objective

Add:

* imprints table
* personas table
* activation logic
* override precedence

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo.

Instructions:
1. Add:
   - imprints table
   - personas table
2. Enforce:
   - Only one active imprint per user/project.
   - User persona overrides generated persona.
3. Add store methods:
   - get_active_imprint
   - activate_imprint
   - set_persona
4. Add tests verifying activation and override precedence.
5. Run backend tests.
6. Commit atomically.

Output:
- DB migration summary.
- Test results.
- Commit hash.
```

---

# 🧬 TASK 6 — Event Graph Emission

## Objective

Emit events for:

* thread.update
* persona.set
* codex.result

Aligned with sync contract spec

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo.

Instructions:
1. Emit event graph entries for:
   - thread.update
   - persona.set
   - codex.result
2. Store causal relationships.
3. Add integration tests verifying event persistence.
4. Run backend tests.
5. Commit atomically.

Output:
- Event emission summary.
- Test results.
- Commit hash.
```

---

# 📦 TASK 7 — Codex Entry Lineage Enforcement

Aligned with codex entry internal spec
And thread-artifact lineage spec

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo.

Instructions:
1. Ensure codex entries always store:
   - thread_id
   - source_message_id
2. Add endpoint to jump back to thread at message.
3. Add tests verifying lineage integrity.
4. Run backend tests.
5. Commit atomically.

Output:
- Lineage enforcement summary.
- Test results.
- Commit hash.
```

---

# 📊 TASK 8 — Token Cost UI Warning

## Objective

Expose system prompt metadata to frontend and warn if threshold exceeded.

---

## Codexify Task Prompt

```
Context:
You’re operating on the local Codexify repo.

Instructions:
1. Add endpoint:
   GET /api/system_prompt/summary
2. Return:
   - estimated_tokens
   - docs_count
   - segment sizes
3. Add frontend indicator component.
4. Add tests for threshold behavior.
5. Run full-stack tests.
6. Commit atomically.

Output:
- Summary of UI + backend changes.
- Test results.
- Commit hash.
```

---

# 🏁 Final Structure

This campaign:

* Hardens identity modeling boundaries.
* Locks flow exfiltration.
* Introduces sandbox CLI safety.
* Modularizes system prompts.
* Adds persona persistence.
* Formalizes event graph lineage.
* Makes token cost transparent.

This is no longer an experimental architecture.
This is a sovereign runtime.

And now you’re not scattered.

You’re holding the control plane.
