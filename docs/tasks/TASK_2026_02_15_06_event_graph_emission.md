TASK 6 — Event Graph Emission
Objective

Emit events for:

thread.update

persona.set

codex.result

Aligned with sync contract spec

sync-contract

Codexify Task Prompt
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

TASK 6 — Event Graph Emission (Auditable Lineage + Sync-Contract Alignment)

Objective

Implement first-class Event Graph emission so key system actions produce durable, queryable, causally linked events.

This task establishes the minimal audit + lineage substrate required for:
- provenance (“why did you say/do that?”)
- sync replication
- deterministic replay/debugging

Events required (v1):
- thread.update
- persona.set
- codex.result

Align with the existing sync contract event set.

Scope

Backend-only for this task.
Do not modify frontend UI.
Do not implement new flows or permissions here.
Do not change prompt assembly logic (Task 4).
Do not change persona/imprint storage logic (Task 5), except to emit events from those code paths.

Correctness / Audit Invariants (Must Hold)

1) Durable, Queryable Persistence
- Every emitted event must be persisted to the primary DB (or the repo’s canonical storage) with an indexed lookup path.

2) Idempotent Upsert
- Emitting the same logical event twice must not create duplicates.
- Event writes must support an idempotency key.

3) Causal Linkage
- Events must support parent/causal references so downstream artifacts can be traced back to their origin.

4) Minimal PII / Sensitive Content
- Event payloads must avoid storing raw sensitive text by default.
- Prefer references (thread_id, message_id, codex_entry_id) over copying content.

Event Model

Implement an event table/model consistent with repo conventions.

Required fields:
- event_id (pk)
- event_type (string)
- occurred_at (timestamp)
- actor_user_id (nullable)
- project_id (nullable)
- thread_id (nullable)
- entity_type (nullable)  # e.g. 'thread' | 'persona' | 'codex'
- entity_id (nullable)
- idempotency_key (string, unique)
- parent_event_id (nullable)
- payload_json (json/text)  # small, structured payload; references only

Indexes (minimum):
- (event_type, occurred_at)
- (thread_id, occurred_at)
- (entity_type, entity_id)
- unique(idempotency_key)

Idempotency Key Rules

Define stable keys per event type:

- thread.update:
  idempotency_key = "thread.update:{thread_id}:{message_id or revision_id}"

- persona.set:
  idempotency_key = "persona.set:{user_id}:{project_id}:{persona_id}:{activated_at_iso}"
  (If activation time is not stable, use a monotonic revision integer instead.)

- codex.result:
  idempotency_key = "codex.result:{codex_entry_id}:{source_thread_id}:{source_message_id}"

Causal Linkage Rules

- persona.set events may optionally parent the most recent thread.update in that thread (if applicable).
- codex.result must parent the thread.update (or message event) that produced the codex entry.

If the codebase does not have message-level events yet:
- parent codex.result to the most recent thread.update for the source thread.

Where To Emit

1) thread.update
- Emit when:
  - a message is appended
  - a thread is edited/renamed
  - thread mode toggles (diary etc.)

2) persona.set
- Emit when:
  - active persona changes
  - active imprint changes (optional: imprint.set as future event, but in this task keep persona.set only unless the repo already differentiates)

3) codex.result
- Emit when:
  - a codex entry is created
  - a codex entry is updated with new lineage-relevant fields

Files Likely Affected

This change belongs in backend persistence + orchestrator/service layers.
Likely locations include:
- guardian/core/db.py and/or guardian/core/storage.py
- guardian/core/orchestrator/* (if orchestration emits)
- guardian/routes/* (where these actions occur)
- any existing event graph module (if present)
- migration tooling

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Add Event Persistence Model + Migration
- Add an events table/model with the required fields.
- Add indexes and unique idempotency constraint.
- Create a migration using repo conventions.

2) Implement EventWriter API
- Add an EventWriter with:
  - emit_event(event_type, actor_user_id, project_id, thread_id, entity_type, entity_id, payload, parent_event_id, idempotency_key) -> event_id
  - must upsert by idempotency_key

3) Wire Event Emission into Code Paths
- Identify where thread updates occur; emit thread.update with stable idempotency_key.
- Identify where persona activation occurs; emit persona.set.
- Identify where codex entries are created; emit codex.result and parent it appropriately.

4) Enforce Small Payloads
- Ensure payload_json contains references and metadata only.
- Do not store full message bodies in events.

5) Tests (Required)
Add backend tests that fail before and pass after:

- Emitting the same event twice (same idempotency_key) results in a single stored row.
- thread.update events are persisted and queryable by thread_id.
- persona.set event is emitted on persona activation.
- codex.result event is emitted on codex entry creation.
- codex.result stores parent_event_id or has a resolvable parent reference.

6) Validation
Run backend tests:

pytest -v

7) Commit
Stage only modified files.
Commit message:

"Emit event graph entries for thread/persona/codex with idempotent linkage"

Output (Required)

- Summary of schema changes + indexes.
- List of modified files.
- Backend test results summary.
- Git commit hash.

Constraints

- Do not add UI.
- Do not add new event types beyond the three required (unless existing code already has a compatible superset).
- Do not store raw sensitive message content in event payloads.
- Do not modify flow permission logic.

This task establishes the audit + lineage backbone for provenance and sync.