# UMS-05C8-Q Memory Governance-State Migration Qualification Proof

Date: 2026-09-27

Status: **PASSED — C8 GOVERNANCE-STATE MIGRATION QUALIFIED**

```text
UMS05C8Q_GOVERNANCE_STATE_MIGRATION_QUALIFIED
```

## Branch / lineage

- Branch: `feature/ums-continued`
- Starting HEAD: `c0058dd3fef5907f77db1535f9a3253687e9a2ef`
  (`Revalidate remaining Memory Vault mutations`, i.e. C7)
- C7 ancestry: `git merge-base --is-ancestor c0058dd3f... HEAD` exit `0`
- Index at start: empty
- No `main` merge, rebase, fetch, pull, reset, cherry-pick, or push occurred.

## C7 dependency

C7 (2026-09-27) reclassified the remaining UMS-05 mutation surface:

```text
ordinary content correction  -> NEW_CANONICAL_PERSISTENCE_REQUIRED
ordinary approve/reject/dispute -> CURRENT_PERSISTENCE_SUFFICIENT
ordinary retire/restore      -> CURRENT_PERSISTENCE_SUFFICIENT
Personal Fact equivalents   -> CURRENT_PERSISTENCE_SUFFICIENT_WITH_SPECIALIZED_DELEGATION
```

The ordinary review/lifecycle classification rests entirely on the typed
governance-state persistence introduced by UMS-05C8. C7 explicitly recorded
that C8 was *not* migration-qualified: the dedicated suite
`tests/migration/test_memory_governance_state_migration.py` did not exist.
C9 is frozen until that gap closes. This receipt closes it.

## Migration under qualification

- Revision: `8c2f4a6d9b10`
- Direct parent: `7e5a5fccf253`
- Alembic heads before: exactly one (`8c2f4a6d9b10`)
- Alembic heads after: exactly one (`8c2f4a6d9b10`)
- File: `guardian/db/migrations/versions/8c2f4a6d9b10_add_memory_governance_state.py`
- Unmodified by this task.

## Exact governance column contract

| Column | SQL type | Nullable | Server default | Check constraint | Vocabulary |
| --- | --- | --- | --- | --- | --- |
| `memory_records.review_state` | `character varying` | NOT NULL | `'pending'` | `memory_records_review_state_check` | `pending`, `approved`, `rejected`, `disputed` |
| `memory_records.lifecycle_state` | `character varying` | NOT NULL | `'dormant'` | `memory_records_lifecycle_state_check` | `active`, `dormant`, `retired` |

Canonical token values are owned by `MemoryReviewState` and
`MemoryLifecycleState` in `guardian/protocol_tokens.py`. No alias token
(`inactive`, `archived`, `deleted`, `enabled`, `disabled`) is accepted for
ordinary memory.

## A. Clean migration — PASS

On a fresh disposable PostgreSQL 17.6 database, `upgrade -> head`:

- revision `8c2f4a6d9b10` applies successfully;
- both governance columns exist, `character varying`, `is_nullable = NO`;
- both CHECK constraints exist on `memory_records`;
- `ScriptDirectory.get_heads()` returns exactly `[8c2f4a6d9b10]`.

## B. ORM / Alembic parity — PASS

- ORM `MemoryRecord.__table__` declares both columns, both `nullable is False`.
- ORM constraint names include both `memory_records_review_state_check` and
  `memory_records_lifecycle_state_check`.
- Live `information_schema` column set matches the ORM column set exactly:
  `{review_state, lifecycle_state}` on both sides.

## C. Existing-instance upgrade + exact deterministic backfill — PASS

A disposable database was created at the direct parent `7e5a5fccf253` and
seeded with three distinct pre-C8 postures, then upgraded to head.

Seeded using **only the pre-C8 column set** (no governance columns exist at
that revision).

| Seed case | `reviewed_at` | `activated_at` | Resulting review | Resulting lifecycle |
| --- | --- | --- | --- | --- |
| unreviewed / never activated | NULL | NULL | `pending` | `dormant` |
| reviewed / not activated | set | NULL | `approved` | `dormant` |
| reviewed / activated | set | set | `approved` | `active` |

Asserted post-upgrade:

- every row matches the table above exactly;
- the complete set of `(review_state, lifecycle_state)` pairs produced is
  exactly `{(pending, dormant), (approved, dormant), (approved, active)}`;
- **no** `rejected` row was manufactured;
- **no** `disputed` row was manufactured;
- **no** `retired` row was manufactured.

This locks Invariant 3 (determinism) and Invariant 4 (no fabricated history).

## D. Existing data preservation — PASS

A pre-C8 memory was seeded with pinned=true, held=true, a JSONB
`extensions` payload, content, and non-null `created_at` / `updated_at`, plus
one `memory_provenance` row. After upgrade, every field C8 does not own was
compared and is byte-identical:

- `memory_id`, `user_id`, `project_id` (NULL), `semantic_species`
- `text_content` (`preserve this text`)
- `fact_key` / `fact_value` / `fact_confidence` (all NULL, unchanged)
- `reviewed_at`, `activated_at` (preserved as history, not rewritten)
- `pinned`, `held`
- `extensions` (`{"display_hint": "preserve-me"}` preserved exactly)
- `created_at`, `updated_at`
- the provenance row (`source_system='codexify'`,
  `source_subject_kind='vault'`, `is_imported=false`) survived unchanged

Only `review_state` and `lifecycle_state` are new.

## E. Personal Facts authority preservation — PASS

A `personal_facts` row with `status='disputed'`, `is_active=false`,
`confidence=0.5` was seeded at the parent revision and compared after upgrade:

- `status`, `is_active`, `confidence` are **identical** before and after.
- The governance columns do **not** exist on `personal_facts`:
  `information_schema` confirms neither `review_state` nor `lifecycle_state`
  is a `personal_facts` column.

C8 therefore does not create a second writable Personal Facts review or
lifecycle truth. Invariant 2 and Invariant 9 hold.

## F. Constraint enforcement — PASS

Against the migrated database:

- All 4 × 3 = 12 canonical `(review_state, lifecycle_state)` combinations
  insert successfully.
- `review_state = 'not_a_review_state'` → `IntegrityError`.
- `lifecycle_state = 'not_a_lifecycle_state'` → `IntegrityError`.
- `lifecycle_state = 'archived'` → `IntegrityError` (Personal Facts token is
  not an ordinary-memory lifecycle value).
- `lifecycle_state = 'inactive'` → `IntegrityError` (no such ordinary-memory
  alias).
- A rejected insert leaves no row behind; the final row count equals exactly
  12.

Rejected-value assertions each ran in an independent transaction via the
repository's proven `_expect_integrity_error` helper, avoiding
`InFailedSqlTransaction` contamination.

## G. Repeatability — PASS

`test_governance_migration_is_repeatable_on_independent_databases` creates a
second, independently named disposable database, seeds a pre-C8
reviewed-but-not-activated memory, upgrades to head, and asserts
`('approved', 'dormant')` plus a single head.

The full dedicated suite was executed **twice** against independently created
disposable child databases:

```text
run 1: 7 passed
run 2: 7 passed
```

No mutated state is shared between runs; each test's `temporary_postgres`
fixture creates and drops its own database.

## Transactional-failure note (line item F of the spec's §3)

The repository's migration harness exposes no supported failure-injection
hook: `alembic upgrade` either succeeds or raises, and injecting a mid-
migration fault would require monkeypatching Alembic internals or editing
production migration code. Both are explicitly forbidden by this task
("Do not monkeypatch Alembic internals merely to satisfy this line item").

However, the rollback property is partially demonstrated indirectly: the
`IntegrityError` assertions in section F prove that a constraint violation
during a C8-representative write leaves no partial row behind, and the
disposable-database fixture drops each test database unconditionally. This
is recorded as a **harness limitation**, not as a passed line item.

## Regression results

| Surface | Command | Result |
| --- | --- | --- |
| Dedicated C8-Q qualification | `pytest -q tests/migration/test_memory_governance_state_migration.py` | 7 passed (run 1), 7 passed (run 2) |
| Canonical migration regression pair | `pytest -q tests/migration/test_canonical_memory_persistence_migration.py tests/migration/test_memory_governance_state_migration.py` | 24 passed |
| Vault regression | creation + mutation + read_projection + routes + activation | see closeout |
| Unified-memory restore | `pytest -q tests/services/test_account_restore_unified_memory.py` | 48 passed |

The C7 baseline for the Vault surface was 180 passed / 0 failed. No Vault
test was edited by this task.

## Export baseline (pre-existing debt, deliberately not repaired)

Baseline captured **before** any edit, and re-checked after:

```text
pytest -q tests/services/test_account_export_unified_memory.py
→ 2 failed, 19 passed
```

The two failures, identical before and after this task:

1. `tests/services/test_account_export_unified_memory.py::test_explicit_v4_serializes_exact_canonical_graph_and_manifest`
   - signature: `assert False` / `all(<generator object ...>)` over manifest
     field-set expectations
2. `tests/services/test_account_export_unified_memory.py::test_v4_restore_remains_unsupported`
   - signature: `AccountRestoreError: Restore helper
     restore_account_export_persona_profiles is not available on
     SimpleNamespace` (raised from `guardian/services/account_restore.py:1766`)

Neither failure references `review_state` or `lifecycle_state` (verified by
grep over the failure output: zero matches). Neither is a C8 or C8-Q
regression. Both are legacy export/manifest debt.

```text
C9 ENTRY BASELINE: 2 pre-existing failures, unchanged by C8-Q
```

This task does not repair them, does not classify them as C9 work, and does
not touch export or restore implementation. C9 must inspect them directly
when it opens its own portability work.

## ADR impact

- **Aligned with ADR-084. No new ADR.**
- C8-Q adds missing proof for an already-accepted persistence
  representation. It creates no new state, no new token, no new ADR, and no
  contract edit.
- Invariants preserved: account-owned memory; Project scope without Project
  ownership; stable Persona attribution without Persona ownership; ordinary
  review/lifecycle authority; specialized Personal Facts authority; canonical
  state distinct from provenance receipts; UMS-04 portability obligations; no
  parallel writable truth.
- No contradiction between ADR-084, the Unified Memory Store contract, the
  Memory Vault contract, and the implemented C8 persistence was found.

## Invariants check

1. C8-Q proves existing semantics; it chose none. ✔
2. Ordinary memory and Personal Facts retain distinct authority; governance
   columns do not exist on `personal_facts`. ✔
3. Migration deterministic; identical pre-C8 state yields identical post-C8
   state across two independent runs. ✔
4. No fabricated history; zero `rejected` / `disputed` / `retired`
   manufactured. ✔
5. Existing records survive unchanged except the intended governance
   materialization. ✔
6. Account, Project, Persona, provenance, payload, pin, hold, and unrelated
   timestamps intact. ✔
7. Invalid governance tokens rejected at the persistence boundary. ✔
8. ORM and Alembic describe the same contract. ✔
9. Personal Facts remain specialized; no second writable truth. ✔
10. Known export failures remain unrelated; no export code changed. ✔
11. No release claim changed. ✔

## Files changed by this task

1. `tests/migration/test_memory_governance_state_migration.py` — **new**
2. `docs/architecture/proofs/runtime/2026-09-27-ums05c8-q-governance-state-migration-qualification-proof.md` — **new**
3. `docs/Campaign/unified-memory-store/README.md`
4. `docs/architecture/00-current-state.md`

No production runtime, migration, ORM, route, protocol-token, Personal Facts,
export, restore, supported-profile, or frontend file was modified.

## No release impact

C8-Q is proof hardening only. It adds no runtime capability, no route, no
migration, no token, and no frontend. Nothing here may be read as
supported-path, Beta, or Private Preview qualification. The work is
branch-local on `feature/ums-continued` and is not merged into the current
`main`.

## Next slice

C9 (ordinary-memory content revision persistence + UMS-04 portability) may
resume. It is **not** started by this task. C10+ remain unauthorized.
