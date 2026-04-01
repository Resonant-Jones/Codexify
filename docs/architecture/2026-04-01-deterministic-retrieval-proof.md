# 2026-04-01 Deterministic Retrieval Proof

## Scope

This artifact records a deterministic retrieval proof for Codexify that is
anchored in backend/runtime seams and trace state, not assistant prose.

- Validation source of truth: repo-backed `pytest` seams in this checkout
- Proven through code-path evidence:
  - `ContextBroker.assemble(...)`
  - `GET /chat/debug/rag-trace/{thread_id}/latest`
- Proven properties:
  - active thread is searched first
  - `source_mode=project` widens only within the current project for the same user
  - `source_mode=personal_knowledge` widens across projects only for the same user
  - local evidence outranks broader evidence when sufficient
  - no cross-user widening
  - empty retrieval state remains truthful when no evidence exists
- Out of scope:
  - browser-driven completion against a live multi-project embedding corpus
  - full upload -> embed -> retrieve proof in a live browser session
  - redesign of source selector UX or diagnostics UI

## Deterministic Retrieval Matrix

The proof corpus uses distinctive sentinel phrases so the tests can assert on
retrieval evidence and trace state without reading assistant output.

| test_case_id | project_id / label | thread_id / label | artifact / source identifier | sentinel phrase | query | source_mode | expected widening behavior | expected top hit(s) | expected excluded hit(s) | expected empty-state behavior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `project-local-success` | Project A / `project-a` | `1` / active thread | `project-a-thread-1.md` | `aurora-lattice-sentinel-alpha` | `aurora-lattice-sentinel-alpha` | `project` | active thread only; no widening | `aurora-lattice-sentinel-alpha` | `frontend-rim-bezel-sentinel-beta`, `static-cinder-sentinel-decoy`, `cross-user-phantom-sentinel-omega` | n/a |
| `personal-knowledge-widening-success` | Project B / `project-b` | `3` / same-user cross-project thread | `project-b-thread-3.md` | `frontend-rim-bezel-sentinel-beta` | `frontend-rim-bezel-sentinel-beta` | `personal_knowledge` | widen beyond the current project, but only for the same user | `frontend-rim-bezel-sentinel-beta` | `aurora-lattice-sentinel-alpha`, `static-cinder-sentinel-decoy`, `cross-user-phantom-sentinel-omega` | n/a |
| `truthful-empty-result` | Project A / `project-a` | `1` / active thread | `project-a-thread-1.md` | `void-horizon-sentinel-zeta` | `void-horizon-sentinel-zeta` | `project` | same-project widening attempted, but no evidence materialized | none | `aurora-lattice-sentinel-alpha`, `frontend-rim-bezel-sentinel-beta`, `static-cinder-sentinel-decoy`, `cross-user-phantom-sentinel-omega` | empty `semantic` list and empty trace `documents` list |
| `no-cross-user-bleed` | Project A / `project-a` | `1` / active thread | `cross-user-thread-6.md` is excluded | `cross-user-phantom-sentinel-omega` | `cross-user-phantom-sentinel-omega` | `personal_knowledge` | same-user widening only; user-2 evidence is never searched | none | `cross-user-phantom-sentinel-omega` (present only in another user’s corpus, but never surfaced) | empty `semantic` list and empty trace `documents` list |

## Backend / Runtime Seams Proven

### `tests/core/test_context_broker_source_mode.py`

This is the primary deterministic proof seam.

- `test_deterministic_retrieval_matrix_proves_boundary_model`
  - asserts `source_mode`
  - asserts `widen_reason`
  - asserts thread identity and project identity in trace state
  - asserts top hit ordering through returned semantic evidence
  - asserts excluded sentinel phrases do not appear
  - asserts the namespace search order:
    - active thread first
    - current project only for `project`
    - same-user widening across projects for `personal_knowledge`
    - no cross-user namespace widening
- Existing focused tests in the same file still prove:
  - same-project widening for `project`
  - cross-project widening for `personal_knowledge`
  - strong local evidence suppresses widening

### `tests/routes/test_chat_profile_trace.py`

This proves the latest trace retrieval seam preserves trace identity and empty
state truthfully.

- completed candidate traces preserve `thread_id`, `project_id`, `depth_mode`,
  `source_mode`, and `widen_reason`
- empty trace retrieval returns a truthful empty structure and remains
  thread-bound

### Runtime trace payload

The broker trace now carries the retrieval identity directly:

- `thread_id`
- `project_id`
- `depth_mode`
- `source_mode`
- `widen_reason`
- `documents` with score/title/snippet

That makes the trace inspectable from evidence, not inferred from answer text.

## What Remains Unproven Live

- Full browser-driven completion against a live multi-project embedding corpus
- The same matrix proven above, but on a live current-`main` runtime with real
  persisted embeddings
- Any UI behavior beyond the route trace payload itself

## Test Command

```bash
pytest -v \
  tests/core/test_context_broker_source_mode.py \
  tests/routes/test_chat_profile_trace.py
```

## Result

The retrieval boundary model is now deterministic at the backend seam:

- active thread first
- project widening stays project-local for the same user
- personal knowledge widening expands only within the same user
- cross-user evidence is excluded
- empty retrieval stays empty instead of fabricating a hit
