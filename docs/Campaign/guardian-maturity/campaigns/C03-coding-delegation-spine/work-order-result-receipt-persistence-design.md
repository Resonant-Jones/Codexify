# Work-Order Result Receipt — Persistence Seam Design

## Status

**C03 campaign design — docs-only.** This document defines the proposed persistence seam for future `WorkOrderResultReceipt` storage. It prepares a future implementation task (C03-T012). It does not implement storage, migrations, routes, artifact creation, coding-agent execution, Pi/Coder invocation, or public release support.

The governing release-truth authority remains [`docs/architecture/00-current-state.md`](../../../architecture/00-current-state.md).

## Purpose

Design the storage model, migration plan, create/read route contracts, validation rules, linkage rules, integrity hash design, redaction design, and export/restore behavior for future immutable work-order result receipts before any implementation begins.

## Scope

- Future persistence of `WorkOrderResultReceipt` records.
- Future create/read route contracts at design level.
- Future `latest_receipt_id` linkage at design level.
- Integrity hash, redaction, and export/restore design.

## Non-Goals

- No schema migration in this task.
- No model implementation in this task.
- No route implementation in this task.
- No artifact implementation.
- No worker orchestration.
- No coding-agent execution.
- No public release claim.

## Proposed Persistence Model

### Table: `work_order_result_receipts`

| Column | Type | Nullable | Source of Truth | Purpose | Export/Restore |
|--------|------|----------|-----------------|---------|----------------|
| `receipt_id` | `String(64)` (UUID hex) | No | Generated at creation | Primary identity | Must be stable; remap if IDs use DB-internal refs |
| `work_order_id` | `String(64)` | No | Supplied from route param | Links receipt to work order | Must follow work-order ID remapping |
| `command_run_id` | `String(64)` | Yes (null for manual notes) | Supplied from request or `latest_run_id` | Links receipt to observed CommandRun | Must follow command-run ID remapping; null if manual |
| `receipt_kind` | `String(32)` | No | Supplied from request | `command_run_observation`, `pi_harness_observation`, `manual_operator_note` | Preserved as-is |
| `observed_command_id` | `String(512)` | No | Copied from CommandRun | The command_id that was executed | Preserved as-is |
| `observed_run_status` | `String(32)` | No | Copied from CommandRun | Status at observation time | Preserved as-is |
| `observed_result_summary` | `Text` | No | Summarized from CommandRun `result_json.body` | Human-readable result summary | Preserved as-is |
| `observed_error_text` | `Text` | Yes | Copied from CommandRun `error_text` | Error at observation time | Preserved as-is |
| `created_at` | `TIMESTAMP(tz)` | No | Server timestamp | When receipt was created | Preserved; may need TZ normalization |
| `created_by` | `String(255)` | No | Auth subject | Who created the receipt | Preserved as-is |
| `source_thread_id` | `String(128)` | Yes | Copied from work order | Source thread lineage | Must follow thread ID remapping |
| `source_message_id` | `String(128)` | Yes | Copied from work order | Source message lineage | Must follow message ID remapping |
| `provenance_json` | `JSONB` | No | Assembled at creation | Structured provenance metadata | Preserved as-is |
| `redaction_summary_json` | `JSONB` | No | Assembled at creation | What was redacted from observation | Preserved as-is |
| `integrity_hash` | `String(64)` | No | Computed at creation | SHA-256 hash of canonical payload | Recomputed on restore; must match |
| `schema_version` | `Integer` | No | Hardcoded constant | Schema version for migration | Preserved as-is |

**Optional columns:**

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `artifact_ids_json` | `JSONB` | Yes | Referenced artifact IDs (not created by receipt) |
| `review_state` | `String(32)` | Yes | `unreviewed`, `accepted`, `rejected`, `superseded` |
| `operator_note` | `Text` | Yes | Free-text operator annotation |
| `supersedes_receipt_id` | `String(64)` | Yes | Self-reference for receipt versioning |

## Proposed Relationships

| Relationship | Type | Delete | Cascade | Rationale |
|-------------|------|--------|---------|-----------|
| `work_order_id → coding_work_orders.work_order_id` | Soft reference | Restrict | None | Work orders may be archived; receipts should survive as historical records |
| `command_run_id → command_runs.run_id` | Soft reference | Restrict | None | CommandRun records may age out; receipts carry observed summary independently |
| `supersedes_receipt_id → work_order_result_receipts.receipt_id` | Soft reference | Set null | None | Receipt versioning; superseded receipt may be deleted without breaking the superseding receipt |
| `coding_work_orders.latest_receipt_id → work_order_result_receipts.receipt_id` | Soft reference | Set null | None | Pointer from work order to its most recent receipt |

**Rationale for soft references over hard foreign keys**: Receipts are immutable historical records. Hard FKs would prevent deleting old work orders or CommandRuns that receipts reference. Soft references with application-level validation preserve referential integrity at creation time while allowing historical records to outlive their referenced entities.

## Immutability and Update Policy

1. **Receipts are immutable after creation.** No update route exists for receipt payload fields.

2. **Review state may be mutable** if the design chooses to store it on the receipt row. If mutable, only `review_state` and `operator_note` are updateable — observed result fields (`observed_command_id`, `observed_run_status`, `observed_result_summary`, `observed_error_text`) must never change after creation.

3. **Alternative**: Model review as a separate `work_order_receipt_reviews` table with append-only semantics. This preserves receipt immutability while allowing review state to evolve.

4. **`supersedes_receipt_id`** allows a newer receipt to reference an older one. The older receipt remains immutable; the newer receipt carries the supersession reference.

5. **`latest_receipt_id` on the work order** may be updated to point to the most recent receipt. This is a pointer update, not a receipt mutation.

## Receipt Creation Contract

### Proposed Route

`POST /api/coding/work-orders/{work_order_id}/receipts`

### Request Body (Candidate)

```json
{
  "receipt_kind": "command_run_observation",
  "command_run_id": "run_...",       // optional; defaults to work_order.latest_run_id
  "operator_note": "Reviewed result"
}
```

### Creation Behavior

1. Validate work order exists (404 if not).
2. Validate auth/ownership (403 if unauthorized).
3. Resolve `command_run_id`: use request field if supplied, otherwise `work_order.latest_run_id`.
4. If no `command_run_id` and `receipt_kind` is `command_run_observation`, return 404 `work_order_receipt_source_run_not_found`.
5. If `command_run_id` is supplied, validate it exists (404 if not).
6. Validate the CommandRun is linked to the work order or safely linkable (C03-T006 semantics).
7. Fetch CommandRun data (`command_id`, `status`, `result_json`, `error_text`).
8. Assemble receipt payload — copy observed fields, summarize result, record provenance.
9. Compute integrity hash over canonical payload fields.
10. Assemble redaction summary.
11. Write receipt row (immutable, one transaction).
12. Optionally update `work_order.latest_receipt_id` (in same or separate transaction — see open questions).
13. Return 201 with receipt payload.

### Safety Rules

- Receipt creation must not execute a command.
- Receipt creation must not call Pi/Coder.
- Receipt creation must not mutate files.
- Receipt creation must not mark work order complete.
- Receipt creation must not expose raw args, secrets, prompts, credentials, or hidden runtime data.

### Candidate Error Codes (Docs-Only)

| Error | Meaning |
|-------|---------|
| `work_order_not_found` | Work order does not exist |
| `work_order_receipt_source_run_not_found` | No CommandRun to observe (no `latest_run_id` and no supplied `command_run_id`) |
| `work_order_receipt_source_run_unlinked` | Supplied `command_run_id` is not linked to this work order |
| `work_order_receipt_invalid_state` | Receipt kind requires a CommandRun but work order or run state doesn't support observation |
| `work_order_receipt_creation_blocked` | Receipt creation blocked by validation or redaction safety |

## Receipt Readback Contract

### Proposed Routes

| Route | Purpose |
|-------|---------|
| `GET /api/coding/work-orders/{work_order_id}/receipts/{receipt_id}` | Read a specific receipt |
| `GET /api/coding/work-orders/{work_order_id}/receipts` | List receipts for a work order (paginated) |
| `GET /api/coding/work-orders/{work_order_id}/latest-receipt` | Resolve `latest_receipt_id` to full receipt payload (analogous to `latest-run`) |

### Readback Behavior

- Preserve auth/ownership boundary.
- Expose receipt payload, provenance, redaction summary.
- Do not expose raw args, secrets, prompts, credentials, or hidden runtime data.
- Do not include artifact payloads inline unless a future artifact contract permits it.
- Do not imply work-order completion.

## `latest_receipt_id` Linkage Policy

1. When receipt creation succeeds, the work order **may** update `latest_receipt_id` to the new receipt's ID.
2. Updating `latest_receipt_id` does not alter work-order status.
3. `latest_receipt_id` points to receipt identity, not CommandRun identity.
4. Idempotent receipt creation must not create duplicate receipts for the same canonical source.
5. Failed receipt creation must not mutate `latest_receipt_id`.
6. If receipt creation and `latest_receipt_id` update are in separate transactions, the pointer may briefly lag behind the receipt. Prefer same-transaction if consistency is critical.

## Integrity Hash Design

### Canonical Payload Fields (Included in Hash)

`receipt_id`, `work_order_id`, `command_run_id` (or empty string if null), `receipt_kind`, `observed_command_id`, `observed_run_status`, `observed_result_summary`, `observed_error_text` (or empty string if null), `created_at`, `created_by`, `source_thread_id` (or empty string if null), `source_message_id` (or empty string if null), `schema_version`.

### Fields Excluded from Hash

`review_state`, `operator_note`, `artifact_ids_json`, `supersedes_receipt_id` — these are mutable or optional metadata.

### Algorithm

SHA-256 over canonical JSON. JSON keys sorted lexicographically. No whitespace. UTF-8 encoding.

### Export/Restore

- Restore must recompute integrity hash from restored payload.
- If integrity hash does not match after restore, the receipt is flagged as `integrity_mismatch` in the restore manifest.
- Receipts with mismatched hashes should still be imported but marked for review.

## Redaction Design

### What Must Never Be Copied Into a Receipt

- Raw unredacted command arguments
- API keys, credentials, tokens, passwords
- System prompts, hidden prompts, persona data
- Raw `result_json` in full (summarize instead)
- Internal runtime metadata not intended for operator visibility

### `args_redacted` Representation

The receipt does **not** copy `args_redacted` from CommandRun. The receipt's `observed_result_summary` is a human-readable summary, not a raw dump.

### Result Summary

`observed_result_summary` is summarized from `result_json.body`. For simple results (e.g., `{"status": "ok"}`), a direct string representation may be acceptable. For complex results, a summary template (e.g., "Health check passed: status=ok, service=core") is preferred.

### When to Block Receipt Creation

Block receipt creation if:
- `result_json` contains fields that cannot be safely summarized
- `redaction_summary_json` cannot accurately describe what was excluded
- The CommandRun's `args_redacted` indicates sensitive data was present and cannot be verified as redacted in the summary

## Export/Restore Design

### Receipts in Export Manifest

Receipts appear as a top-level collection in the export manifest, keyed by `receipt_id`:

```json
{
  "receipts": {
    "receipt_abc123": { /* full receipt payload */ }
  }
}
```

### Relationship Payload

Each receipt carries its `work_order_id` and `command_run_id` as exported values. The restore process must remap these references using the export manifest's ID mapping table.

### Stable Receipt IDs

Receipt IDs should be UUIDs generated at creation time. They should not depend on database-internal sequences that may collide across export/restore.

### Broken References

If a receipt's `work_order_id` or `command_run_id` cannot be resolved after restore, the receipt must:
- Still be imported (historical record)
- Flagged with `restore_reference_broken` in the restore manifest
- Not be silently dropped

### Integrity Validation After Restore

- Recompute integrity hash from restored payload.
- Compare with stored hash.
- Flag mismatches.

## Migration Plan (Design Only)

### Proposed Table DDL (Candidate)

```sql
CREATE TABLE work_order_result_receipts (
    receipt_id VARCHAR(64) PRIMARY KEY,
    work_order_id VARCHAR(64) NOT NULL,
    command_run_id VARCHAR(64),
    receipt_kind VARCHAR(32) NOT NULL,
    observed_command_id VARCHAR(512) NOT NULL,
    observed_run_status VARCHAR(32) NOT NULL,
    observed_result_summary TEXT NOT NULL,
    observed_error_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    source_thread_id VARCHAR(128),
    source_message_id VARCHAR(128),
    provenance_json JSONB NOT NULL DEFAULT '{}',
    redaction_summary_json JSONB NOT NULL DEFAULT '{}',
    integrity_hash VARCHAR(64) NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    artifact_ids_json JSONB,
    review_state VARCHAR(32),
    operator_note TEXT,
    supersedes_receipt_id VARCHAR(64)
);
```

### Proposed Indexes

```sql
CREATE INDEX ix_receipts_work_order_id ON work_order_result_receipts (work_order_id);
CREATE INDEX ix_receipts_command_run_id ON work_order_result_receipts (command_run_id);
CREATE INDEX ix_receipts_created_at ON work_order_result_receipts (created_at);
CREATE UNIQUE INDEX uq_receipt_work_order_source ON work_order_result_receipts (work_order_id, command_run_id, receipt_kind)
    WHERE command_run_id IS NOT NULL;
```

### Uniqueness Constraint

The partial unique index on `(work_order_id, command_run_id, receipt_kind)` prevents duplicate receipts for the same work-order/run/kind combination when a CommandRun is referenced. Manual operator notes (null `command_run_id`) are not deduplicated — each is a distinct observation.

### Backfill Posture

No backfill needed — receipts are new records created after migration. Existing work orders start with `latest_receipt_id = NULL`.

### Rollback Posture

Drop the `work_order_result_receipts` table. Clear `latest_receipt_id` on work orders if populated. No data loss from existing records.

## Minimal Future Implementation Sequence

After this design is accepted:

1. **C03-T012**: Implement receipt persistence — create model, migration, create route
2. **C03-T013**: Add receipt readback — individual, list, and latest-receipt routes
3. **C03-T014**: Link `latest_receipt_id` — update work-order pointer after receipt creation
4. **C03-T015**: Frontend/operator receipt display — blocked until backend truth exists

## Open Questions

1. **Receipt ID format**: UUID hex (`a1b2c3d4...`) vs. prefixed (`rec_a1b2c3d4...`)? Prefer UUID hex for consistency with `run_` prefix pattern, or `rec_` prefix for operator readability.

2. **Nullable `command_run_id`**: Should manual operator notes (no linked run) be supported? Yes — `receipt_kind: manual_operator_note` with null `command_run_id`.

3. **Automatic receipt creation**: Should receipts be created automatically after linked CommandRun completion? Defer to operator decision. Automatic creation risks receipts for failed runs without operator awareness.

4. **Transaction boundary**: Should `latest_receipt_id` update be in the same transaction as receipt creation? Yes — prevents pointer lag.

5. **Mutable review state**: Should review state be on the receipt row or a separate review events table? Separate table preserves receipt immutability. If on receipt row, only `review_state` and `operator_note` are mutable.

6. **Integrity hash includes redaction summary**: Should the hash include `redaction_summary_json`? No — redaction summary is metadata about the observation, not the observation itself. Including it would cause hash changes when redaction policy evolves.

7. **Broken references after restore**: Should receipts with broken work-order references be importable? Yes — as historical records. Flag in restore manifest.

8. **Receipt vs. artifact promotion**: Should a receipt ever promote into an artifact? No — they are distinct domains. An artifact may reference a receipt, but receipts do not become artifacts.

## Release Boundary

This design does not widen the release promise. `docs/architecture/00-current-state.md` remains authoritative. No receipt implementation exists. No migration, route, or `latest_receipt_id` linkage exists. This design defines future semantics only.
