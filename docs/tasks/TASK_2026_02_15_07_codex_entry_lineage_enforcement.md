TASK 7 — Codex Entry Lineage Enforcement (Thread↔Artifact Provenance + Jump-To-Source)

Objective

Enforce provenance guarantees for Codex Entries so every shareable artifact is traceable back to its originating thread and message(s).

This task establishes:
- mandatory lineage fields on codex entries
- queryable lineage integrity constraints
- a backend endpoint to navigate from a codex entry back to its source location in the originating thread (“jump to source”)

This is required for trust, auditability, and “why did you say that?” style provenance.

Scope

Backend-only for this task.
Do not modify frontend UI.
Do not change event graph logic (Task 6) except to ensure lineage fields used by codex.result remain present.
Do not implement new retrieval logic.

Correctness Invariants (Must Hold)

1) Mandatory Lineage
- Every codex entry MUST have:
  - source_thread_id
  - source_message_id (or source_message_ids if multi-span is already supported)

2) Referential Integrity
- source_thread_id must reference an existing thread.
- source_message_id must reference an existing message in that thread (or a stable message identifier scheme used by the repo).

3) No Orphan Codex Entries
- Creating a codex entry without lineage must fail closed.

4) Stable Jump Target
- The system must provide a deterministic “jump target” for a codex entry:
  - thread_id
  - message_id
  - optional: message_index / anchor if the UI uses an index-based jump

Data Model

Use the repo’s existing codex entry storage model.
If any of the following fields are missing, add them via schema migration:

- codex_entries.source_thread_id (TEXT/UUID, required)
- codex_entries.source_message_id (TEXT/UUID, required)

Optional (only if already supported elsewhere):
- codex_entries.source_message_ids (JSON/TEXT)
- codex_entries.source_span (JSON)  # for multi-message ranges

If the codebase currently stores lineage only in metadata JSON, promote the required fields to first-class columns so they are indexable and enforceable.

Indexes (minimum)
- (source_thread_id)
- (source_thread_id, source_message_id)

API Contract

Add a backend endpoint to resolve provenance:

GET /api/codex/{codex_entry_id}/source

Response:
- codex_entry_id
- source_thread_id
- source_message_id
- optional: message_index (if computable)
- optional: source_excerpt (short, non-sensitive preview; max 200 chars; omit if risky)

Rules:
- Do not return the full message body by default.
- Prefer references; excerpt is optional and must be bounded.

Where To Enforce

1) Codex Entry Creation Path
- When a codex entry is created from a thread/message, enforce presence of lineage fields.
- If a legacy path creates codex entries without lineage, either:
  - block it, or
  - require callers to supply lineage.

2) Codex Entry Update Path
- If lineage fields are missing on legacy entries, add a guarded migration strategy:
  - Do NOT guess lineage.
  - Leave legacy entries as-is but mark them as legacy (lineage_missing=true) ONLY if unavoidable.
  - New entries must always include lineage.

Files Likely Affected

This change belongs in codex entry persistence + routes.
Likely locations include:
- guardian/core/storage.py
- guardian/core/db.py
- guardian/routes/codex.py (or equivalent)
- guardian/routes/chat.py (if codex entries are created there)
- migration tooling
- backend tests

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Schema Enforcement
- Ensure codex entries have first-class required lineage columns:
  - source_thread_id
  - source_message_id
- Add indexes:
  - (source_thread_id)
  - (source_thread_id, source_message_id)
- Create a migration using repo conventions.

2) Enforce Lineage at Write Time
- Update codex entry creation logic so it fails closed if lineage is missing.
- Ensure any helper function creating codex entries requires lineage params.

3) Implement Jump-To-Source Endpoint
- Add endpoint: GET /api/codex/{codex_entry_id}/source
- Return source references as specified.
- If message index is used by the UI and is computable from storage, include it; otherwise omit.

4) Tests (Required)
Add backend tests that fail before and pass after:

- Creating a codex entry without source_thread_id/source_message_id fails.
- Creating a codex entry with valid lineage succeeds.
- /api/codex/{id}/source returns expected thread_id + message_id.
- Referential integrity: invalid thread_id or message_id is rejected (or returns 404 if enforcing at read-time).

5) Validation
Run backend tests:

pytest -v

6) Commit
Stage only modified files.
Commit message:

"Enforce codex entry lineage and add jump-to-source endpoint"

Output (Required)

- Summary of schema changes + indexes.
- List of modified files.
- Backend test results summary.
- Git commit hash.

Constraints

- Do not add frontend UI.
- Do not store full message bodies in the provenance endpoint response.
- Do not modify event graph schema (Task 6).
- Do not implement new flow logic.

This task makes Codex Entries trustworthy, auditable artifacts rather than detached notes.
