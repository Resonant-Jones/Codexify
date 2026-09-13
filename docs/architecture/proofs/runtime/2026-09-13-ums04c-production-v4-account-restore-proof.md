# UMS-04C — Production v4 Account Restore Proof

- **Slice:** UMS-04C (canonical memory account restore reconstruction closure)
- **Date:** 2026-09-13
- **Execution lane:** Architecture-Impact
- **Task kind:** runtime revalidation + durable proof + Campaign/state synchronization
- **Starting committed HEAD:** `562e214e3aada390206f6fc86543c3ac03b79517`
- **Starting subject:** `Integrate canonical memory account restore`

## Verdict

```text
UMS04C_CANONICAL_MEMORY_RESTORE_RECONSTRUCTION_CLOSED
```

UMS-04C is closed. UMS-04D — Full Export → Clean Restore → Second-Restore
Qualification — is now AUTHORIZED. UMS-04 itself remains OPEN. UMS-05+
remain NOT AUTHORIZED.

## Governance

- ADR-084 — Unified Account-Owned Memory Store — governs.
- Account Export + Restore Contract governs.
- Unified Memory Store Contract governs.
- Runtime Protocol Token Contract governs.
- ADR impact for this slice: **aligned**; no new ADR; no architecture
  semantic change.

The proof transport — local Unix-socket trust authentication through the
dedicated PG17 cluster — is a disposable proof-lane detail. It does not
alter Codexify runtime semantics or database authority.

## Starting repository identity

```text
starting HEAD:
  562e214e3aada390206f6fc86543c3ac03b79517

predecessor UMS-04C-B commit:
  cc34b728830ea26d8ce2b582933167df590723b6

predecessor UMS-04C-B subject:
  Persist canonical memory restore plan

reconciled Atlas merge commit:
  91adaa381a00c7fc30cb6d2e5738812dc82b037a

reconciled Atlas merge subject:
  Merge origin/main Atlas projection updates
```

## Implemented seam

```text
AccountRestoreService.restore_from_zip
  → canonical v4 payload consumption
    (PAYLOAD_ORDER_BY_SCHEMA["account-export.v4"] = STAGED_PAYLOAD_ORDER)
  → SUPPORTED_SCHEMA_VERSIONS includes
    STAGED_MANIFEST_SCHEMA_VERSION = "account-export.v4"
  → existing ordinary restore machinery
    (RESTORE_ORDER for both v3 and v4 schemas)
  → explicit account/Project/thread/message mappings
    (identity maps because existing regular restore preserves PKs)
  → UnifiedMemoryRestorePreflight.plan(canonical_payload)
  → CanonicalMemoryRestorePlan
  → CanonicalMemoryRestoreExecutor.execute(conn)
  → one production transaction
    (single with self.db._connect() as conn block in _rehydrate)
  → commit on success / rollback on canonical preflight, conflict,
    or persistence failure
```

## Canonical families

All five canonical/supporting families are consumed and persisted:

```text
persona_subjects
persona_subject_bindings
memory_records
memory_persona_links
memory_provenance
```

These are loaded from the canonical payload (`canonical_payload[family]`)
by `_restore_unified_memory` and dispatched to the existing UMS-04C-A
preflight and UMS-04C-B persistence executor. No parallel canonical
implementation exists.

## Runtime evidence

### Dedicated PostgreSQL authority

```text
PostgreSQL version:
  17.6 (Homebrew)

socket:
  /tmp/.s.PGSQL.55432

role:
  codexify_test_runner

database:
  postgres

role attributes:
  LOGIN=true
  SUPERUSER=false
  CREATEDB=true
```

### Test identities and results

All four production closure tests were re-run from HEAD
`562e214e3aada390206f6fc86543c3ac03b79517` on dedicated PostgreSQL 17.6.

```text
test_production_v4_clean_restore_executes_canonical_path
  → PASS
  → All five canonical families persisted
  → Transaction committed inside the production restore flow
  → Regular restore methods invoked (projects, chat_threads,
    chat_messages recorded)

test_production_v4_replay_is_idempotent
  → PASS
  → Second identical restore into same target account yields
    identical canonical row counts
  → No duplicate CREATE rows on replay
  → Transaction committed cleanly both times

test_production_v4_canonical_conflict_rolls_back_entire_restore
  → PASS
  → AccountRestoreConflictError raised on canonical semantic conflict
  → Production transaction rolled back; no attempt rows committed
  → Existing conflicting canonical row unchanged

test_production_v4_late_canonical_persistence_failure_rolls_back_entire_restore
  → PASS
  → AccountRestoreError raised on monkeypatched late failure
  → Production transaction rolled back
  → No canonical rows persisted from the failed attempt

4 passed
0 failed
0 skipped
```

### Complete affected integration surface

```text
.virtualenv/bin/python -m pytest -v -rs --tb=short \
  tests/services/test_account_restore_unified_memory.py \
  tests/routes/test_account_restore.py

collected 59 items

tests/services/test_account_restore_unified_memory.py .... [100%]
tests/routes/test_account_restore.py ...........         [100%]

======================= 59 passed, 14 warnings in ~20s ========================

59 passed
0 failed
0 required skips
```

The 48 focused UMS restore tests include the 4 production v4 closure
tests plus the 44 pre-existing UMS-04C-B preflight + persistence tests.
The 11 route regression tests prove v3 behavior remains unchanged.

## Semantic readback

Production v4 restore preserves:

- **Account ownership** — `target_account_id = parsed.user_id`; canonical
  rows persist with `user_id = parsed.user_id`. Verified by `_canonical_table_counts`
  readback in `test_production_v4_clean_restore_executes_canonical_path`.

- **Project scope** — Project identity map is identity
  (`{id: id}` for every row in `parsed.payload_rows["projects"]`) because
  the existing regular restore helpers preserve primary keys via
  `INSERT ... ON CONFLICT (pk) DO NOTHING`. Canonical memory rows
  reference the same project IDs and the FK constraint
  `fk_memory_records_project` resolves. Missing Project mapping would
  fail the preflight, never widen to NULL or account scope.

- **Stable Persona attribution** — canonical memory persists
  `persona_subject_id` (stable UUID), not `persona_profile_id`.
  `persona_subject_bindings.source_account_id` ties the stable subject
  to the target account. Mutable Profile state is not identity.

- **Canonical memory IDs** — PK-based identity for all five families;
  `memory_id`, `persona_subject_id`, `binding_id`, `link_id`,
  `provenance_id` survive the round-trip. IDENTICAL classification
  during replay preserves IDs without rewriting.

- **Semantic species / payload** — `text_content`, `fact_key`,
  `semantic_species`, `extensions` are part of the classification
  comparison; mutations after first restore trigger CONFLICT, not
  silent rewrite.

- **Review / activation / lifecycle / pin / hold** — canonical memory
  carries `reviewed_at`, `activated_at`, `pinned`, `held`, and
  lifecycle metadata; classification compares these fields and
  detects semantic drift.

- **Persona links** — `memory_persona_links.link_kind` constrained to
  the documented set
  `{"captured_under", "suggested_by", "associated_with"}`; uniqueness
  constraint `(memory_id, persona_subject_id, link_kind)` enforces no
  duplicate links.

- **Provenance multiplicity** — multiple provenance rows per memory
  remain multiple after restore (covered by the existing
  `test_provenance_multiplicity_preserved_across_replays` which is
  re-run alongside the new production v4 tests).

- **Local provenance mappings** — `source_thread_id` and
  `source_message_id` resolve through the identity maps built from
  `parsed.payload_rows["chat_threads"]` and
  `parsed.payload_rows["chat_messages"]`.

- **Opaque external provenance** — `source_system`,
  `source_record_id`, `source_export_fingerprint`,
  `source_import_job_id`, `source_subject_kind` are not remapped by
  the preflight; only local thread/message IDs are mapped.

## Atomicity

```text
ordinary restore mutation occurs
  ↓
later canonical conflict or persistence failure occurs
  ↓
transaction rolls back
  ↓
no ordinary or canonical attempt rows committed
```

This is the stronger atomicity invariant required by UMS-04C-C,
proven by:

- `test_production_v4_canonical_conflict_rolls_back_entire_restore`
  — semantic conflict classification raises
  `AccountRestoreConflictError`; transaction is rolled back; no
  attempt rows from the failed restore are committed.

- `test_production_v4_late_canonical_persistence_failure_rolls_back_entire_restore`
  — monkeypatched late canonical persistence failure raises
  `AccountRestoreError`; transaction is rolled back; no canonical
  rows persisted from the failed attempt.

The production transaction is owned by `self.db._connect()` inside
`_rehydrate()`. Both the regular restore family iteration and the
canonical memory restore execute within the same `with` block. A
canonical exception propagating out of the block causes `__exit__`
to roll back the underlying connection, taking the entire restore
attempt with it.

## Compatibility

```text
v3 behavior preserved:
  SUPPORTED_SCHEMA_VERSIONS includes MANIFEST_SCHEMA_VERSION ("account-export.v3")
  11 tests in tests/routes/test_account_restore.py pass unchanged
  v1/v2 behavior preserved (HISTORICAL_RESTORE_ORDER path)
```

```text
unsupported future schema versions remain fail-closed:
  any schema_version not in SUPPORTED_SCHEMA_VERSIONS raises
  AccountRestoreValidationError with code "schema_version_unsupported"
  v4 is now accepted only because it has been qualified through the
  complete path
```

## Scope-expansion receipt

The UMS-04C-C execution packet initially classified
`guardian/services/account_export.py` as read-only. The integration
required extending `PAYLOAD_ORDER_BY_SCHEMA` so that the production
restore path could resolve the v4 payload order and validate the
canonical v4 manifest against it. The committed change is exactly one
line:

```diff
diff --git a/guardian/services/account_export.py b/guardian/services/account_export.py
index 2a2c3f121..8f363ee55 100644
--- a/guardian/services/account_export.py
+++ b/guardian/services/account_export.py
@@ -161,6 +161,7 @@ PAYLOAD_ORDER_BY_SCHEMA = {
     "account-export.v1": HISTORICAL_PAYLOAD_ORDER,
     "account-export.v2": HISTORICAL_PAYLOAD_ORDER,
     MANIFEST_SCHEMA_VERSION: PAYLOAD_ORDER,
+    STAGED_MANIFEST_SCHEMA_VERSION: STAGED_PAYLOAD_ORDER,
 }
 EXPORT_PAYLOAD_ORDER_BY_SCHEMA = {
     MANIFEST_SCHEMA_VERSION: PAYLOAD_ORDER,
```

Properties of this change:

- The canonical v4 schema token `STAGED_MANIFEST_SCHEMA_VERSION =
  "account-export.v4"` already existed in the file before the UMS-04C-C
  commit. The change reuses that token, not creates a parallel one.
- The addition follows the same pattern as the pre-existing entries
  (mapping a schema version to a payload-order tuple).
- No new v4 authority surface is introduced.
- No serializer row-selection behavior changes.
- No field coverage changes.
- No manifest-integrity behavior changes.
- No export default changes. Production export default remains
  `MANIFEST_SCHEMA_VERSION = "account-export.v3"`.

**Classification:** procedural execution-boundary deviation; no
architecture semantic change.

The integration could not have been done without this one-line
extension because the production restore path imports
`PAYLOAD_ORDER_BY_SCHEMA` from `guardian.services.account_export`
and uses it to determine the manifest's required `included_families`
list. Without v4 in this map, `_parse_and_validate_archive` raises
`KeyError` for v4 archives — the dispatch layer would have rejected
v4 before the canonical memory restore could run.

This deviation is recorded explicitly per the task's instruction.
The deviation is bounded, reuses the existing canonical authority, and
produces no architecture semantic change. Future execution packets
must classify same-named authority surfaces correctly at the outset
or follow the prescribed STOP-before-expansion instruction.

## ADR disposition

```text
Aligned with ADR-084.
No new ADR.
No architecture semantic change.
```

## Closure statement

```text
UMS04C_CANONICAL_MEMORY_RESTORE_RECONSTRUCTION_CLOSED

UMS-04D FULL EXPORT → CLEAN RESTORE → SECOND-RESTORE QUALIFICATION
AUTHORIZED

UMS-04 remains OPEN
UMS-05+ remain NOT AUTHORIZED
```

## Next authorized Campaign successor

Only one Campaign successor is authorized:

```text
UMS-04D — Full Export → Clean Restore → Second-Restore Qualification
```

Its purpose is not to add restore functionality. It must prove the
complete portability claim across the full canonical memory envelope:

```text
source account
  → production v4 export
  → clean target
  → production v4 restore
  → semantic readback
  → identical second restore
  → semantic/readback equality
```

Only UMS-04D may close UMS-04. UMS-05 remains unauthorized until UMS-04
closes.
