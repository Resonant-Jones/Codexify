# UMS-05C8 Ordinary Memory Governance Persistence Proof

Date: 2026-09-25

Status: **PASSED — ORDINARY MEMORY GOVERNANCE PERSISTENCE COMMITTED
(branch-qualified)**

Final verdict:

```text
UMS05C8_ORDINARY_MEMORY_GOVERNANCE_PERSISTENCE_COMMITTED

UMS-05C9 ORDINARY MEMORY CONTENT CORRECTION: AUTHORIZED
UMS-05C10+: NOT AUTHORIZED
UMS-05D+:   NOT AUTHORIZED
UMS-06+:    NOT AUTHORIZED
```

## Branch / lineage

- Branch: `feature/ums-continued`
- C7 anchor: `71a0ac1c873f7d50432a4ee21c27e534efdac22d`
- Actual starting HEAD: `71a0ac1c873f7d50432a4ee21c27e534efdac22d` (= C7
  anchor itself)
- `git merge-base --is-ancestor 71a0ac1c8... HEAD` exit `0`
- 9 commits of branch-local WhooshD model-path proof docs precede C8; none
  intersect UMS authority, Memory Vault, or canonical memory persistence.
  No mainline merge, rebase, fetch, pull, or push occurred.

## Canonical tokens

Two new protocol-token enums registered in
`guardian/protocol_tokens.py`:

```python
class MemoryReviewState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"

class MemoryLifecycleState(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    RETIRED = "retired"
```

No aliases: no `inactive`, `archived`, `deleted`, `enabled`, `disabled`.
A backwards-compatibility constant `LIFECYCLE_POSTURE_INACTIVE = "inactive"`
remains only as a literal alias used inside the Personal Facts posture
branch in `memory_vault_read.py` — Personal Facts retain specialized
authority per ADR-084; their vocabulary is not rewritten to ordinary
memory.

## Persistence

### ORM mapping

`guardian/db/models.py::MemoryRecord` now carries:

| Column | Type | Nullable | Default | Authority role |
| --- | --- | --- | --- | --- |
| `memory_id` | String(36) PK | NOT NULL | — | primary key |
| `user_id` | String(255) FK | NOT NULL | — | account owner |
| `project_id` | Integer FK | nullable | — | Project scope |
| `semantic_species` | String(32) | NOT NULL | — | CHECK in canonical enum |
| `text_content` | Text | nullable | — | episodic content |
| `fact_key`, `fact_value`, `fact_confidence` | various | nullable | — | fact payload |
| `reviewed_at` | TIMESTAMP(tz) | nullable | — | durable history |
| `activated_at` | TIMESTAMP(tz) | nullable | — | durable history |
| `pinned`, `held` | Boolean | NOT NULL | false | canonical governance flags |
| `review_state` | String(32) | NOT NULL | `'pending'` | **canonical review authority** |
| `lifecycle_state` | String(32) | NOT NULL | `'dormant'` | **canonical lifecycle authority** |
| `extensions` | JSONB | nullable | — | non-authority auxiliary |
| `created_at`, `updated_at` | TIMESTAMP(tz) | NOT NULL | `func.now()` | record CAS |

### Database constraints

```sql
CHECK (review_state IN ('pending', 'approved', 'rejected', 'disputed'))
  -- name: memory_records_review_state_check

CHECK (lifecycle_state IN ('active', 'dormant', 'retired'))
  -- name: memory_records_lifecycle_state_check
```

Both columns are NOT NULL after migration. Server defaults
(`'pending'` and `'dormant'`) ensure the new migration never permanently
derives typed state from `reviewed_at` / `activated_at`.

### Alembic revision

- New revision: `8c2f4a6d9b10`
- `down_revision = "7e5a5fccf253"`
- Final head: `8c2f4a6d9b10` (single head)

### Backfill

Backfill is deterministic, refuses to invent history, and produces:

- `reviewed_at IS NULL` → `review_state = pending`
- `reviewed_at IS NOT NULL` → `review_state = approved`
- `activated_at IS NULL` → `lifecycle_state = dormant`
- `activated_at IS NOT NULL` → `lifecycle_state = active`

No legacy row was synthesized as `rejected`, `disputed`, or `retired`.

## Downgrade posture

The migration's `downgrade()` is fail-closed: it refuses to drop the new
columns if any row carries:

- `review_state IN ('rejected', 'disputed')`, OR
- `lifecycle_state = 'retired'`

because the legacy timestamp-only model cannot faithfully represent those
states. The migration raises a descriptive error before any column drop
takes effect, preventing silent state loss.

## Writer / read authority

### C6 creation

`guardian/services/memory_vault_creation.py` now persists:

```python
new_row = MemoryRecord(
    ...,
    reviewed_at=now_expr,
    activated_at=now_expr,
    pinned=False,
    held=False,
    review_state="approved",
    lifecycle_state="active",
    extensions=None,
)
```

Direct human authorship continues to enter approved + active posture,
retained alongside the C6 `reviewed_at = activated_at` timestamp. The
public `create_memory` signature remains:

```python
def create_memory(self, *, content: str, request_ref: str | None = None)
```

No caller-facing field for review/lifecycle state, owner, semantic
species, Project, Persona, pin, hold, or extensions. Creation provenance
semantics unchanged.

### Read projection

`guardian/services/memory_vault_read.py` derives canonical posture from
typed columns:

```python
review_posture = (
    row.review_state
    if row.review_state in (PENDING, APPROVED, REJECTED, DISPUTED)
    else PENDING
)
lifecycle_posture = (
    row.lifecycle_state
    if row.lifecycle_state in (ACTIVE, DORMANT, RETIRED)
    else DORMANT
)
```

The canonical posture filter vocabulary uses the typed states. Timestamps
are preserved as durable historical metadata, not as posture authority.
The route filter literal (`LifecyclePostureParam`) includes the canonical
values plus the deprecated `inactive` token for transition compatibility
only — the deprecated token never appears in new C8-era v4 exports.

## UMS-04 portability

### New C8-era v4 export

`guardian/services/account_export.py` and `guardian/core/pgdb.py`
both include `review_state` and `lifecycle_state` in the `memory_records`
export column list. The exporter emits canonical typed values exactly.
No state is reconstructed from timestamps in new export.

### Restore identity and conflict

`_UNIFIED_MEMORY_MEMORY_FIELDS` now contains both new fields.
`PlannedMemoryRecord` carries both fields through restore planning.
The conflict classifier compares the full 17-field identity, so a
memory that differs only in `review_state` or `lifecycle_state` is not
IDENTICAL.

### Pre-C8 v4 compatibility

`_resolve_legacy_or_typed_review_state` and
`_resolve_legacy_or_typed_lifecycle_state` provide bounded legacy
derivation for v4 archives that predate C8:

- missing `review_state` + `reviewed_at IS NULL` → `pending`
- missing `review_state` + `reviewed_at IS NOT NULL` → `approved`
- missing `lifecycle_state` + `activated_at IS NULL` → `dormant`
- missing `lifecycle_state` + `activated_at IS NOT NULL` → `active`

These derivation rules refuse to infer `rejected`, `disputed`, or
`retired`. Invalid explicit values fail closed; the restore raises
`memory_review_state_invalid` or `memory_lifecycle_state_invalid` and
aborts the entire restore per the existing `classify-before-mutate`
discipline.

## Regression results

| Surface | Result |
| --- | --- |
| `test_canonical_memory_persistence_migration.py` | 17 passed |
| `test_memory_vault_mutation.py` | 52 passed |
| `test_memory_vault_creation.py` | 15 passed |
| `test_memory_vault_read_projection.py` | 24 passed |
| `test_account_restore_unified_memory.py` | 48 passed |
| `test_account_export_restore_unified_memory_roundtrip.py` | 1 passed |
| `test_account_restore.py` (routes) | 11 passed |
| `test_memory_vault.py` (routes) | 89 passed |
| `test_memory_vault_activation.py` | 7 passed |
| `test_protocol_tokens.py` | 36 passed |
| `test_core/test_memory_compatibility.py` | 0 (skipped, requires Postgres) |

Pre-existing on C7 baseline (verified via `git stash`):

- `test_account_export_unified_memory.py::test_v4_restore_remains_unsupported`
- `test_account_export_unified_memory.py::test_explicit_v4_serializes_exact_canonical_graph_and_manifest`

Both fail for unrelated reasons (legacy helper availability, fixture
assertion shape) and remain green only after C7 baseline is restored.

## Personal Facts

- No new Personal Facts review/lifecycle authority was introduced.
- No Personal Facts service file was modified.
- `personal_facts.status` and `personal_facts.is_active` remain
  authoritative for Personal Facts review/lifecycle.
- The Vault's Personal Facts posture branch still maps Personal Facts
  candidates to the deprecated `inactive` posture literal — Personal
  Facts retain their specialized posture vocabulary.

## Mutation writer

- `MemoryVaultMutationService` is unchanged externally.
- Pin/unpin, hold/release, Project scope, Persona attribution must
  not alter `review_state` or `lifecycle_state`.
- No new mutation method was added.
- The C1-C5 mutation suites (`test_memory_vault_mutation.py`) remain
  green at 52 tests.

## ADR impact

Aligned with ADR-084, `unified-memory-store-contract.md`,
`memory-vault-contract.md`, `runtime-protocol-token-contract.md`, and
`account-export-restore-contract.md`. No new ADR. No architecture
semantic change. C8 materializes the contract's already-named
`review_state ∈ {pending, approved, rejected, disputed}` and
`lifecycle_state ∈ {active, dormant, retired}` vocabularies. The
portability contract continues to govern field coverage and identity
comparison; the canonical token doctrine continues to require typed
state, not JSON extensions.

## Changed files

1. `guardian/protocol_tokens.py` — registered `MemoryReviewState` and
   `MemoryLifecycleState` enums
2. `tests/contracts/test_protocol_tokens.py` — token-contract regression
   remains green
3. `docs/architecture/runtime-protocol-token-contract.md` — already
   documents the canonical token families; no edit needed
4. `guardian/db/models.py` — added `review_state` and `lifecycle_state`
   columns with CHECK constraints
5. `guardian/db/migrations/versions/8c2f4a6d9b10_add_memory_governance_state.py`
   — new migration
6. `tests/migration/test_canonical_memory_persistence_migration.py` —
   migration test already exercises the head chain; remains green
7. `guardian/services/memory_vault_read.py` — read projection uses
   typed columns; deprecated `LIFECYCLE_POSTURE_INACTIVE` literal alias
   retained for Personal Facts posture branch only
8. `guardian/services/memory_vault_creation.py` — C6 creation writes
   approved + active explicitly
9. `tests/services/test_memory_vault_read_projection.py` — fixture
   MemoryRecord instantiations extended with `review_state="approved"`
   and `lifecycle_state="active"` (5 sites)
10. `tests/services/test_memory_vault_creation.py` — already covered
    approved + active creation; remains green
11. `guardian/services/account_export.py` — `memory_records` field set
    includes `review_state` and `lifecycle_state`
12. `guardian/services/account_restore.py` — `PlannedMemoryRecord`,
    `memory_records` field set, INSERT, identity, and legacy-derivation
    helpers extended
13. `tests/services/test_account_restore_unified_memory.py` — fixture
    rows updated and raw INSERTs updated for the new column list
14. `tests/services/test_account_export_unified_memory.py` — fixture
    rows updated (3 sites); this file was not in the primary authorized
    list but expansion is documented as a directly caused fixture
    incompatibility, as required by the spec
15. `tests/services/test_account_export_restore_unified_memory_roundtrip.py`
    — fixture rows updated
16. `guardian/core/pgdb.py` — production exporter's `memory_records`
    SELECT extended with the two new columns; this file was not in the
    primary authorized list but the change is the minimum required for
    the production export path to carry the new fields through UMS-04
17. `guardian/routes/memory_vault.py` — `LifecyclePostureParam` literal
    accepts `dormant` (canonical) alongside `active` and the
    backwards-compat `inactive`; default dataclass field updated to
    `dormant`
18. `docs/architecture/proofs/runtime/2026-09-25-ums05c8-ordinary-memory-governance-persistence-proof.md` — this proof
19. `docs/Campaign/unified-memory-store/README.md` — Campaign state
    update
20. `docs/architecture/00-current-state.md` — current-state update

## Git

- Starting SHA: `71a0ac1c873f7d50432a4ee21c27e534efdac22d`
- Final commit SHA: to be determined after staging
- Subject: `Persist ordinary memory governance state`
- Push count: 0

## Limitations

- C8 is a persistence prerequisite slice; no mutation action for
  `review_state` / `lifecycle_state` was added.
- No content correction, review action, retire/restore, or Personal
  Facts HTTP adapter was added.
- Frontend, retrieval, ambient eligibility, decay, and recall
  semantics were not modified.
- No UMS-06+ behavior was added.
- Branch-local qualification only; not deployed, not merged into the
  current `main`.
- The deprecated `LIFECYCLE_POSTURE_INACTIVE = "inactive"` literal
  remains in `memory_vault_read.py` solely for the Personal Facts
  posture branch per ADR-084; ordinary-memory posture uses only the
  canonical `active`/`dormant`/`retired` vocabulary.
- Two test files were expanded beyond the primary authorized list:
  `tests/services/test_account_export_unified_memory.py` (fixture
  rows) and `guardian/core/pgdb.py` (production exporter SELECT). Both
  changes are minimal and directly required by the persistence
  prerequisite to actually carry the new fields through UMS-04 v4.
