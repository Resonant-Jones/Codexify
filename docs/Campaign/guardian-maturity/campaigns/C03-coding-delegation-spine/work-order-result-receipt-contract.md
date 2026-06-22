# Work-Order Result Receipt Contract

## Status

**C03 campaign contract — docs-only.** This document defines future receipt semantics for work-order-linked command runs. It does not implement receipt persistence, artifact creation, work-order completion, coding-agent execution, Pi/Coder invocation, or public release support.

The governing release-truth authority remains [`docs/architecture/00-current-state.md`](../../../architecture/00-current-state.md).

## Purpose

Define the bounded semantics, candidate fields, safety boundaries, provenance obligations, and implementation sequence for durable work-order result receipts before any receipt implementation begins.

A receipt is an **immutable observation record** that captures what was observed about a CommandRun result linked to a coding work order. It is not an execution artifact, not a result artifact, and not a work-order completion signal.

## Scope

- Future work-order result receipts derived from linked CommandRun records.
- Receipt creation, readback, and lineage rules.
- `latest_receipt_id` semantics once receipts exist.
- Candidate field vocabulary and token domains for future schema work.

## Non-Goals

- No receipt implementation (persistence, routes, schemas, migrations).
- No artifact implementation.
- No receipt readback implementation.
- No work-order status transitions.
- No coding-agent execution.
- No Pi/Coder invocation.
- No worker orchestration.
- No public release claim.
- No canonical runtime token registration — candidate tokens only.

## Canonical Terms

| Term | Meaning |
|------|---------|
| `WorkOrderResultReceipt` | An immutable observation record summarizing a CommandRun result for a specific work order. |
| `CommandRun` | A durable command bus execution record identified by `run_id`. |
| `latest_run_id` | The work-order field pointing to the most recent linked CommandRun (proven in C03-T006). |
| `latest_receipt_id` | The work-order field pointing to the most recent receipt (field exists, never populated). |
| `Result pointer` | `latest_run_id` alone — the work order points to a run but embeds no result data. |
| `Result receipt` | A receipt record summarizing an observed command result. |
| `Result artifact` | A durable output produced by command execution (e.g., patch file, generated document, test output). |
| `Coding-agent artifact` | A result artifact produced by a coding-agent execution (Pi/Coder or equivalent). |
| `Receipt creation` | The act of recording an immutable observation of a CommandRun result. |
| `Receipt readback` | Reading a previously created receipt by its `receipt_id` or by work-order reference. |

## Current Truth

| Surface | Status | Source |
|---------|--------|--------|
| Work-order latest-run readback | Proven — `GET /api/coding/work-orders/{id}/latest-run` | C03-T009 |
| CommandRun durable result | Proven — `result_json` in Postgres, readable via `GET /api/guardian/commands/runs/{run_id}` | C03-T008 |
| CommandRun durable error | Proven — `error_text` in Postgres, readable | C03-T008 |
| `latest_receipt_id` field | Present on `CodingWorkOrder` model, never populated | C03-T003 |
| Receipt model | Not present | C03-T007 |
| Receipt route | Not present | C03-T007 |
| Artifact model | Not present (Pi module has `PiInvocationArtifact` but not linked to work orders) | C03-T007 |
| Artifact route | Not present | C03-T007 |
| Work-order completion | Not tied to CommandRun completion — status is independent | C03-T003, C03-T006 |

## Receipt Semantics

1. **A receipt is an immutable observation record.** It captures what was observed at the time of creation. It does not change when the underlying CommandRun or work order changes.

2. **A receipt points to one work order.** The `work_order_id` field is required and validated.

3. **A receipt may point to one CommandRun.** The `command_run_id` field is optional — receipts may exist for manual observations without a linked run.

4. **A receipt captures observed command status/result/error metadata.** It summarizes, not replaces, the durable CommandRun data.

5. **A receipt does not execute anything.** Receipt creation is a read-then-write observation operation. It does not invoke command bus, Pi/Coder, shell, git, or external harnesses.

6. **A receipt does not mutate repository state.** No file writes, git operations, or external mutations.

7. **A receipt does not create an artifact.** Artifacts are separate entities. A receipt may reference artifact IDs but does not create them.

8. **A receipt does not mark the work order complete.** Work-order status transitions are a separate contract. A receipt observes; it does not conclude.

9. **A receipt is distinct from a CommandRun.** The CommandRun is the execution record. The receipt is an observation of that execution. They are separate identities.

10. **A receipt is distinct from a result artifact.** A result artifact is output produced by execution. A receipt observes that output.

11. **A receipt is distinct from a Pi/Coder harness receipt.** `PiInvocationReceipt` exists in the Pi module for future Pi/Coder integration. Work-order receipts are a separate domain.

## Minimum Future Receipt Fields (Candidate Only)

These are candidate fields for a future receipt schema. They do not constitute a migration or schema change.

### Required Candidate Fields

| Field | Type | Meaning |
|-------|------|---------|
| `receipt_id` | string (UUID) | Unique receipt identity |
| `work_order_id` | string (FK reference) | The work order this receipt observes |
| `command_run_id` | string | The CommandRun this receipt observes (optional) |
| `receipt_kind` | string | One of the candidate receipt kind tokens |
| `observed_command_id` | string | The command_id from the observed CommandRun |
| `observed_run_status` | string | The status from the observed CommandRun |
| `observed_result_summary` | string | Human-readable summary of the observed result |
| `observed_error_text` | string | Nullable error text from observed CommandRun |
| `created_at` | timestamp | When the receipt was created |
| `created_by` | string | Actor who created the receipt |
| `source_thread_id` | string | Source thread lineage (nullable) |
| `source_message_id` | string | Source message lineage (nullable) |
| `provenance` | JSON | Structured provenance metadata |
| `integrity_hash` | string | Cryptographic hash of receipt contents |
| `schema_version` | int | Receipt schema version for migration compatibility |

### Optional Candidate Fields

| Field | Type | Meaning |
|-------|------|---------|
| `artifact_ids` | list[string] | Referenced artifact IDs (not created by receipt) |
| `review_state` | string | One of the candidate review state tokens |
| `operator_note` | string | Free-text operator annotation |
| `redaction_summary` | JSON | Summary of what was redacted from the observation |

## Candidate Token Vocabulary (Docs-Only)

These are candidate contract tokens. They are not runtime tokens. Runtime tokenization must be a separate architecture-impact implementation task if repeated in code.

### Candidate Receipt Kinds

| Token | Meaning |
|-------|---------|
| `command_run_observation` | Receipt observing a CommandRun result |
| `pi_harness_observation` | Receipt observing a Pi/Coder harness result |
| `manual_operator_note` | Receipt created manually by an operator without a linked run |

### Candidate Review States

| Token | Meaning |
|-------|---------|
| `unreviewed` | Default state — no operator review yet |
| `accepted` | Operator accepted the observed result |
| `rejected` | Operator rejected the observed result |
| `superseded` | A newer receipt supersedes this one |

### Candidate Receipt Creation States

| Token | Meaning |
|-------|---------|
| `created` | Receipt successfully created |
| `failed` | Receipt creation failed |
| `blocked` | Receipt creation blocked by validation |

## Provenance and Export/Restore Obligations

A future receipt must preserve:

1. **Work-order identity.** The `work_order_id` must survive export/restore. If work-order IDs are remapped during restore, receipts must follow the remapping.

2. **CommandRun identity.** The `command_run_id` pointer must be resolvable after restore. If CommandRun records are not exported, receipts must still carry the observed summary so the observation is not lost.

3. **Source thread/message lineage.** When available from the work order, `source_thread_id` and `source_message_id` must be preserved. These anchor the receipt back to the originating conversation.

4. **Actor/auth subject.** `created_by` must preserve who created the receipt.

5. **Created timestamp.** `created_at` must preserve when the receipt was created.

6. **Redaction posture.** The `redaction_summary` must describe what was redacted from the observation.

7. **Semantic equivalence under export/restore.** The receipt's meaning must not change even if local database IDs are remapped. Integrity hashes should be recomputable from the receipt's semantic content, not from DB-internal IDs.

## Safety Boundaries

1. **Receipt creation must not execute a command.** It is a read-then-write observation. No command bus invocation.

2. **Receipt creation must not call Pi/Coder.** Receipts are work-order domain; Pi/Coder is a separate execution domain.

3. **Receipt creation must not mutate files.** No file writes, git operations, or repository changes.

4. **Receipt creation must not imply completion.** Work-order status is a separate contract. A receipt observes; it does not conclude.

5. **Receipt creation must not expose raw args, secrets, prompts, credentials, or hidden runtime data.** Only redacted/summarized data from the CommandRun's already-redacted fields.

6. **Receipt creation must fail closed if the work-order/run relationship cannot be validated.** Work order must exist. CommandRun must exist if referenced. No silent creation of orphan receipts.

## Minimal Future Implementation Path

After this contract is accepted:

1. **C03-T011**: Design work-order result receipt persistence seam (schema proposal, storage model, migration plan — docs-only)
2. **C03-T012**: Implement work-order result receipt persistence (model, migration, create route)
3. **C03-T013**: Add work-order result receipt readback (GET route by receipt_id or by work_order_id)
4. **C03-T014**: Link `latest_receipt_id` after receipt creation proof (populate the existing field)
5. **C03-T015**: Frontend/operator display of receipts (UI task, blocked until backend truth exists)

These are candidate task names only — full tasks must be scoped and accepted separately.

## Open Questions

1. **Should receipts be stored in a new table or as command-run metadata?** Separate table preserves immutability and work-order domain separation. Command-run metadata is simpler but conflates execution with observation.

2. **Should receipt creation be automatic after linked CommandRun completion or explicit operator action?** Automatic is convenient but risks creating receipts for failed runs. Explicit gives operator control but adds a step.

3. **Should failed CommandRuns receive receipts?** A receipt observing a failed run is valid — it records the failure. The receipt kind and observed fields distinguish success from failure.

4. **Should receipts ever affect work-order status?** No. Receipts observe; they do not conclude. Work-order status transitions are a separate contract.

5. **How should redaction summaries be represented?** A structured JSON field listing which CommandRun fields were summarized or excluded from the receipt.

6. **How should receipt integrity hashes be computed?** Hash of the receipt's semantic content fields (receipt_id, work_order_id, command_run_id, receipt_kind, observed_*, created_at, created_by, schema_version), excluding mutable metadata like review_state.

7. **How should export/restore remap receipt references?** Receipts must carry their work_order_id and command_run_id as exported values. Restore must remap references using the export manifest's ID mapping table.

## Release Boundary

This contract does not widen the release promise. `docs/architecture/00-current-state.md` remains authoritative. No receipt implementation exists. No receipt route exists. No `latest_receipt_id` population exists. This contract defines future semantics only.
