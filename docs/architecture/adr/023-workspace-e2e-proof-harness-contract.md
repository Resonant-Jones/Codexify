---
status: accepted
date: 2026-05-05
---

# ADR-023: Workspace E2E Proof Harness Contract

## Context

ADR-016 introduced `retrievalSource="workspace"` as a live backend meaning for user-bounded local knowledge, including Obsidian-backed notes. The completion service and broker now treat it as a real retrieval posture and emit canonical trace evidence for the final completion attempt.

The current-truth anchor in `00-current-state.md` confirms that `workspace` is live on `main` and that the completion worker emits canonical retrieval-posture snapshots for supported source modes. What was missing was a canonical live-proof harness that operators could run end-to-end to produce attachable evidence for release signoff.

Without a deterministic harness, operators must manually run a multi-step procedure that mixes curl commands, log inspection, and debug routes. This creates risk of:
- Treating route acceptance as completion success (queue-backed semantics are not obvious)
- Missing the retrieval-posture signal entirely
- Producing non-reproducible or non-attachable evidence

## Decision

A single-command end-to-end proof harness exists at `scripts/proofs/prove_workspace_obsidian_e2e.py`.

The harness is a **release-evidence tool**, not a generic integration test. It exercises the exact supported local Compose path, checks all required runtime surfaces, and produces an explicit operator-facing verdict table.

### Harness contract

The harness must satisfy all of the following:

1. **Fail-fast health check** — Before any proof step, the harness checks `/health`, `/health/chat`, and `/api/health/llm`. If any surface returns non-2xx, the harness exits with `HEALTH_CHECK_FAILED` (exit code 2) and a clear message.

2. **Sentinel note ingestion** — The harness creates a distinctive sentinel note (UUID-like trigger, answer fragment) and ingests it through the existing Obsidian ingest path (`POST /api/obsidian/ingest`) rather than a fake internal shortcut. Ingestion failure exits with `INGESTION_FAILED` (exit code 3).

3. **Thread and message creation** — The harness creates a chat thread, posts a user message containing the sentinel trigger, and persists the message before requesting completion. Thread/message creation failure exits with `ACCEPTANCE_FAILED` (exit code 4).

4. **Completion request (acceptance milestone only)** — The harness sends `POST /api/chat/{thread_id}/complete` with `retrievalSource="workspace"` and `source_mode="workspace"`. Acceptance is treated as an intermediate milestone, not a passing verdict. Acceptance failure exits with `ACCEPTANCE_FAILED` (exit code 4).

5. **Task completion wait** — The harness polls `GET /api/tasks/{task_id}/events` until a terminal event appears (`task.completed`, `task.failed`, or `task.cancelled`) or timeout (120s). The harness does NOT treat acceptance as success. Timeout or task failure exits with `COMPLETION_TIMEOUT` (exit code 5).

6. **Response verdict** — The harness fetches final thread messages via `GET /api/chat/{thread_id}/messages`, extracts the assistant response(s), and checks that the sentinel answer fragment appears in the response (case-insensitive). Failure exits with `RESPONSE_VERDICT_FAILED` (exit code 6).

7. **Retrieval posture evidence** — The harness fetches the latest retrieval posture via `GET /api/chat/debug/retrieval-posture/{thread_id}/latest` and asserts that workspace-local retrieval participated. Valid signals are:
   - `source_mode == "workspace"`
   - `widen_reason` contains `"workspace"`
   - `retrieval_provenance.retrieval_status == "workspace_local_success"`
   Failure exits with `RETRIEVAL_EVIDENCE_FAILED` (exit code 7).

8. **Operator verdict table** — On success, the harness prints a clear verdict table that explicitly lists all seven proof conditions and marks each as PASS.

### What the harness proves

- The supported local Compose path is healthy enough for a completion run
- A sentinel Obsidian-backed note can be ingested through the live ingest path
- A chat thread and message can be persisted in Postgres
- A completion request with `retrievalSource="workspace"` is accepted (task_id returned)
- The task reaches terminal state (not just acceptance)
- The assistant response contains content derived from the sentinel note
- The retrieval posture snapshot shows workspace-local participation

### What the harness does NOT prove

- Sync automation between Obsidian and Codexify
- First-class connector UX
- Non-Compose install modes (e.g., Kubernetes, bare metal, cloud)
- Any other retrieval source mode (thread, project, personal_knowledge, obsidian_only)
- Upload → embed → retrieve seam (document upload is separate from Obsidian ingest)
- Bounded tool-loop behavior
- The full upload → embed → retrieve proof (this requires a separate live proof)

### Evidence sources read by the harness

| Evidence source | Route | What it proves |
|---|---|---|
| Basic health | `GET /health` | Backend app is running |
| Chat health | `GET /health/chat` | Redis, queue, worker heartbeat healthy |
| LLM health | `GET /api/health/llm` | Active provider reachable |
| Sentinel ingest | `POST /api/obsidian/ingest` | Obsidian ingest path works |
| Thread creation | `POST /api/chat/threads` | Thread CRUD works |
| Message persistence | `POST /api/chat/{thread_id}/messages` | Message write works |
| Completion acceptance | `POST /api/chat/{thread_id}/complete` | Queue acceptance works |
| Task lifecycle | `GET /api/tasks/{task_id}/events` | Real completion (not just acceptance) |
| Response verdict | `GET /api/chat/{thread_id}/messages` | Assistant output present |
| Retrieval posture | `GET /api/chat/debug/retrieval-posture/{thread_id}/latest` | Workspace signal in trace |

### Why acceptance is insufficient (per ADR-001 / flows.md)

The chat completion route follows the queue-based acceptance model defined in ADR-001:

- Route acceptance = turn lock acquired + task enqueued to Redis + HTTP 200 with task_id
- Route acceptance ≠ dequeue, model call, assistant message persisted, or trace evidence available

A task can be accepted and still fail due to:
- Worker downtime
- Provider timeout
- Redis queue degradation
- Task-event publish failures

The harness waits for terminal state because an honest E2E validator must check the real completion outcome, not just POST success.

## Consequences

- Operators can now run a single command to produce attachable release evidence for the workspace retrieval seam
- The harness validates the exact runtime contract defined in ADR-016 (retrievalSource as a live backend meaning, not a label)
- The contract test suite (`tests/proofs/test_workspace_obsidian_e2e_contract.py`) validates harness behavior without requiring a live stack
- The harness README provides clear usage instructions and failure class documentation
- The ADR documents the seam, evidence sources, and explicit out-of-scope items

## Non-Goals

- The harness does NOT add a new queue, worker, storage model, or connector subsystem
- The harness does NOT change retrieval semantics
- The harness does NOT widen the supported install path beyond local Docker Compose
- The harness does NOT replace the backend-seam golden tests in `tests/golden/`
- The harness does NOT prove document upload → embed → retrieve (separate live proof required)

## Related ADRs

- [ADR-001: Queue-Based Completion Acceptance Model](./001-queue-based-completion-acceptance-model.md)
- [ADR-016: Workspace Retrieval Source for Local Knowledge](./016-workspace-retrieval-source-for-local-knowledge.md)
- [ADR-012: Post-Completion Eval Spine](./012-post-completion-eval-spine.md)

## Related Docs

- [Current State](../00-current-state.md)
- [Critical Flows](../flows.md)
- [Config and Ops](../config-and-ops.md)
ADR-016 made `retrievalSource="workspace"` a live backend meaning for local, user-bounded knowledge. That contract needed a canonical live proof surface so operators could validate the real end-to-end seam on the supported local Compose path, not just acceptance of the enqueue request.

The risk is overclaiming. If the harness is not explicit about what it proves, operators could mistake queue acceptance, document ingest, or a dev-only trace snapshot for proof of the actual live completion path.

## Decision

Codexify now has a canonical workspace-local live proof harness:

- `scripts/proofs/prove_workspace_obsidian_e2e.py`

The harness:

- stages a sentinel local note under the repo's ignored `tmp/` tree
- indexes that note through the supported Obsidian control plane
- creates a thread with `retrievalSource="workspace"`
- sends a user message that can only be answered from the sentinel note
- waits for the real queue-backed task to complete
- checks the persisted assistant message
- checks retrieval/trace evidence for workspace-local participation

The harness is intentionally scoped to the supported local Compose path only. It does not widen the release promise to packaged desktop, webUI-only, or other install modes.

## Evidence Sources

The harness reads evidence from:

- `/health`
- `/health/chat`
- `/api/health/llm`
- `/api/health/retrieval`
- `/api/obsidian/config`
- `/api/obsidian/index`
- `GET /api/tasks/{task_id}/events`
- `GET /api/chat/{thread_id}/messages`
- latest retrieval/trace debug surfaces when available on the live path

## Consequences

- Release evidence can now prove the actual `workspace` completion seam end to end.
- Queue acceptance is no longer treated as completion proof.
- Workspace-local retrieval evidence is separated from the assistant message itself.
- Operators get one repeatable command for this seam instead of ad hoc probes.

## Non-Goals

- No sync automation
- No connector UX
- No new retrieval subsystem
- No storage model change
- No support claim for non-Compose install modes
- No claim that debug trace endpoints are the sole source of truth

## Governing Contracts

- [ADR-016: Workspace Retrieval Source for Local Knowledge](./016-workspace-retrieval-source-for-local-knowledge.md)
- [Critical Flows](../flows.md)
- [System Overview](../system-overview.md)
- [Config and Ops](../config-and-ops.md)
- [Current State](../00-current-state.md)

## Related Notes

- [ADR Index](./adr-index.md)
- [Proof Harness README](../../scripts/proofs/README.md)
