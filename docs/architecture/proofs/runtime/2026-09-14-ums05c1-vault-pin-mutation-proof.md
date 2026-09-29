# UMS-05C1 Memory Vault Pin/Unpin Mutation Spine Proof

Date: 2026-09-14

Status: **PASSED — VAULT PIN CAS RECEIPT COMMITTED**

Final verdict:

```text
UMS05C1_VAULT_PIN_CAS_RECEIPT_COMMITTED
UMS-05C2 VAULT PIN MUTATION API AUTHORIZED
UMS-05D+ NOT AUTHORIZED
UMS-06+ NOT AUTHORIZED
```

## Identity / starting anchor

- Branch: `main`
- Opening HEAD: `bad9b5b5288027cb297285633be93ae3365b7666`
  (`Activate Memory Vault read surface`, UMS-05B3)
- Index at open: empty
- Unrelated dirt preserved: Pi fixture, Scout iOS tree, `.DS_Store` debris

## CAS binding

`memory_records.updated_at` is a persisted `TIMESTAMP(timezone=True)` column
(server default `now()`; ORM `onupdate=func.now()`). Exact timestamp equality
is a safe CAS token because PostgreSQL `timestamptz` stores microsecond
precision and compares by instant.

The service requires a timezone-aware `expected_updated_at`, rejects missing,
naive, and malformed tokens, and on a changed mutation advances the token with
the database-authored `clock_timestamp()` expression (strictly advancing,
never client-supplied). No integer revision column was introduced because the
frozen contract permits binding `updated_at` as the explicit CAS mechanism
when no canonical integer revision seam exists.

## Receipt binding

Each changed mutation appends exactly one `memory_provenance` row using only
the already-qualified frozen provenance vocabulary:

```text
source_system        = "codexify"
source_subject_kind  = "vault"
is_imported          = false
provenance_id        = new canonical UUID
source_record_id     = request_ref (opaque, when provided)
extensions           = memory-vault-mutation.v1 audit payload
```

The receipt stores no full memory content / fact payload. It is audit /
lineage only; `memory_records.pinned` remains the sole pin authority.

## v4 portability confirmation

Account-export/restore qualified field sets include every provenance column
used by the receipt (`provenance_id`, `memory_id`, `user_id`, `source_system`,
`source_record_id`, `source_subject_kind`, `is_imported`, `extensions`,
`created_at`) and support multiple provenance rows. No new export family,
schema, or version is required. The existing UMS-04 round-trip regression
remains green.

## Transaction shape

```text
authenticated account (constructor-supplied, immutable)
  ↓
authorize account-owned canonical memory (FOR UPDATE)
  ↓
compare expected_updated_at
  ↓
no-op check (same pin state → changed=false, no write)
  ↓
changed: CAS UPDATE pinned + clock_timestamp()
  ↓
append one Vault provenance receipt
  ↓
flush + commit (atomic)
  ↓
MemoryVaultReadService canonical readback
```

## Proofs

- Success pin (T1 → T2, `pinned=false → true`, one `pin` receipt).
- Success unpin (T2 → T3, `pinned=true → false`, one `unpin` receipt).
- Stale token → conflict, zero state change, zero receipt.
- Cross-account → not-available, zero state change, zero receipt.
- Missing record → same not-available posture as cross-account.
- No-op (fresh token, same state) → `changed=false`, timestamp unchanged, no
  receipt, canonical readback succeeds.
- Stale no-op (old token, current state) → conflict, not idempotent success.
- Receipt-shape: exact schema/action/audit values, no memory content.
- Atomic rollback: forced receipt flush failure rolls back pin change and
  timestamp; zero partial write.
- Account-scoped and Project-scoped records both mutate; Project scope
  unchanged.
- All other authoritative fields (`user_id`, `project_id`, `semantic_species`,
  content/fact payload, `reviewed_at`, `activated_at`, `held`, `extensions`)
  are byte-for-byte unchanged after mutation.

## Regression results

| Surface | Result |
| --- | --- |
| Focused mutation (`test_memory_vault_mutation.py`, PostgreSQL 17.6) | 11 passed |
| B1/R1 read projection | 24 passed |
| B2/R1 route | 25 passed |
| UMS-04 export/restore round-trip | 1 passed |
| Alembic heads | one head `7e5a5fccf253` |

## Read-file immutability

```text
guardian/services/memory_vault_read.py
  7c12d7dc9836465b4bb4b1f393bf066ce5de3b665aab6ed70051f7d247e843b3
guardian/routes/memory_vault.py
  77178d735d5dc465f9d43b31eaee967356d16996ad6c9d47942e449874d71180
```

Unchanged from opening.

## ADR impact

Aligned with ADR-084 and `memory-vault-contract.md`. No new ADR. No
architecture semantic change. Existing CAS/provenance authority reused; no new
persistence concept.

## Limitations

- No mutation HTTP route; no frontend mutation.
- Pin/unpin only; no hold/release, retire/restore, content, Project, Persona,
  or Personal Facts mutation.
- Pinning remains priority-only; no retrieval widening or ambient-eligibility
  mutation.
- UMS-06+ remain unauthorized.
