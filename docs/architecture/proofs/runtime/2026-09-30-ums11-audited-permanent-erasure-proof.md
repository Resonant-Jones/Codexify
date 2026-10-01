# UMS-11 — Audited Permanent Erasure and Resurrection Suppression

**Status:** CLOSED
**Slice:** `UMS-11` — destructive lifecycle / privacy / canonical erasure / portability
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-30
**ADR impact:** Aligned with ADR-084. No new ADR. ADR-084 and contract §12 already own permanent erasure and resurrection suppression; this slice implements accepted architecture and does not change what purge means.
**Class:** Canonical erasure / privacy / durable suppression / transactional proof / account-isolation proof

---

## 1. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `fc1bd41c994a576837108afef9b48773bc4dc077` |
| Revalidation commit | `fc1bd41c9` (ancestor, and the starting tip) |
| C10B-W commit | `464195477c5c3c2d2a1b4fdc356bf12f7ddb2dd0` (ancestor) |
| Alembic head before | `b8e2f4a6c901` (single head) |
| New migration revision | `c7f4a9b2e6d1` |
| Migration parent | `b8e2f4a6c901` |
| Alembic head after | `c7f4a9b2e6d1` (single head) |
| Opening index | empty |
| Untracked posture | only preserved `.precommit_cache/` / `.precommit_home/` entries |
| Push count | `0` |

No merge, rebase, fetch, pull, reset, or cherry-pick was performed.

## 2. Revalidation authority

```text
UMS-11 was the sole admitted foundational successor.
UMS-06/07/08/09/10 remain PARKED.
No C11 was created.
```

The 2026-09-30 revalidation produced `UMS_FOUNDATIONAL_GAP_REMAINS` with the
exact gap *audited permanent erasure + import-resurrection suppression*.
UMS-11 closes it. UMS-12 remains blocked pending the proof/release gate and was
**not** begun.

`MemoryRecallGrant` (UMS-07) remains architecture-specified and unbuilt. That is
correct and unchanged: ADR-084 gates release only on erasure and re-import
suppression.

---

## 3. Schema

Migration `c7f4a9b2e6d1_add_memory_purge_tombstones`, descending from
`b8e2f4a6c901`.

```text
memory_purge_tombstones
├── purge_receipt_id            String(36)   PK, server-authored
├── user_id                     String(255)  NOT NULL, FK users.id ON DELETE CASCADE
├── purged_record_fingerprint   String(128)  NOT NULL
├── source_system               String(32)   NULL
├── source_entity_kind          String(32)   NULL
├── source_atom_fingerprint     String(128)  NULL
├── purged_at                   TIMESTAMPTZ  NOT NULL, server_default now()
└── suppress_reimport           Boolean      NOT NULL, server_default true
```

Constraints and indexes:

| Name | Kind | Purpose |
|---|---|---|
| `pk_memory_purge_tombstones` | PK | stable receipt identity |
| `uq_memory_purge_tombstones_account_record` | UNIQUE `(user_id, purged_record_fingerprint)` | one suppression per erased record per account; makes idempotent retry provable |
| `fk_memory_purge_tombstones_user` | FK → `users.id` CASCADE | suppression never outlives the account |
| `memory_purge_tombstones_suppress_reimport_check` | CHECK | `suppress_reimport` is structurally incapable of becoming false |
| `memory_purge_tombstones_source_system_check` | CHECK | typed source vocabulary |
| `memory_purge_tombstones_source_entity_kind_check` | CHECK | typed source-kind vocabulary |
| `ix_memory_purge_tombstones_user_id` | index | account-scoped lookup |
| `uq_memory_purge_tombstones_account_source_atom` | UNIQUE partial `(user_id, source_atom_fingerprint) WHERE source_atom_fingerprint IS NOT NULL` | a source atom is suppressed at most once per account, while NULLs stay unconstrained |

### 3.1 Why there is no `memory_id`

A tombstone deliberately has **no** composite foreign key to `memory_records`
and stores no canonical `memory_id`. The purge that writes a tombstone deletes
its parent row, so a parent foreign key would be unsatisfiable by construction.
Identity is carried by a versioned domain-separated digest instead.

### 3.2 No-content audit

The relation contains **no** content-bearing column. The export-side field
allowlist is an allowlist, so this is enforced on both the persistence and the
serialization boundary. Absent: memory text, old/new revision text, evidence
excerpt, `source_record_id`, Project name, Persona name, prompt, embedding, and
extensions JSON.

### 3.3 No fabrication

```text
existing canonical memories:
  tombstone rows fabricated = 0
purge receipts fabricated   = 0
```

No pre-existing memory is given invented suppression history, because no
pre-existing memory was purged. Personal Facts, every other UMS relation, and
all existing account-export schema meanings are untouched.

### 3.4 Fingerprint algorithms

Centralized in `guardian/services/memory_purge.py` and imported (never
reimplemented) by export/restore, so the three layers cannot drift.

| Purpose | Version | Shape |
|---|---|---|
| purged-record fingerprint | `v1` | `v1:<sha256 hex>` over the canonical memory identity |
| source-atom fingerprint | `v1` | `v1:<sha256 hex>` over `(source_system, source_entity_kind, source_atom_identity)` |
| confirmation token | `v1` | `v1:<sha256 hex>` over the whole preview envelope |

Each field is **length-prefixed** before hashing. This is not cosmetic: a naive
separator-join let a caller-controlled identity shift a field boundary and
produce a colliding digest for a different tuple, which would have let two
different source atoms share one suppression entry. The test that proved the
collision is retained in `tests/services/test_memory_purge.py`.

The confirmation token is a **target confirmation** mechanism, not
authentication. The authenticated account principal remains the authority
boundary; a caller who cannot authenticate never reaches the check.

---

## 4. Preview

`MemoryPurgeService.preview_purge` is read-only and account-scoped. It reports:

```text
memory_id, record_fingerprint, current updated_at (CAS)
content_revision_count, review_revision_count, lifecycle_revision_count
provenance_count, persona_link_count
derived_state_count
suppression_fingerprint_available, suppression_ambiguity
confirmation_token
```

- Reports **counts and identity only** — no content, no hidden unrelated
  records, no raw queue payloads, no vector bodies, no secrets. Proof
  artifacts and tests use synthetic content.
- The token binds the canonical identity, the current CAS token, the record
  fingerprint, and **every** linked-state count that will be destroyed, so any
  change to the destructive target invalidates it.
- A missing and a cross-account target share one indistinguishable 404.

---

## 5. Canonical purge

`MemoryPurgeService.purge` targets exactly one `memory_records` row inside the
authenticated account boundary. There is no bulk, Project-wide, or account-wide
purge.

Ordering — nothing destructive begins until all of it passes:

1. lock the canonical row (`SELECT ... FOR UPDATE`), proving account ownership;
2. validate the supplied CAS;
3. recompute the current preview envelope;
4. validate the confirmation token against that envelope;
5. derive minimal tombstone values (failing closed on ambiguity);
6. insert exactly one tombstone and flush;
7. remove every canonical child; then the parent;
8. commit.

The row lock serializes purge against content correction, review transition,
lifecycle transition, Persona attribution, pin, and hold. A competing mutation
either finishes first and invalidates this CAS/confirmation, or waits and then
observes the row gone.

### 5.1 Independent post-purge readback

After a purge of a memory carrying one row in every child family, all of the
following were confirmed absent by separate readback:

```text
memory_records               absent
memory_revisions             absent
memory_review_revisions      absent
memory_lifecycle_revisions   absent
memory_provenance            absent
memory_persona_links         absent
```

### 5.2 Atomicity

Within one PostgreSQL transaction the tombstone and the canonical deletion
commit together. Both of these are impossible across a commit boundary:

```text
content absent + no tombstone
tombstone committed + canonical content still present
```

### 5.3 Idempotent retry

A retry presenting the original identity derives the record fingerprint from
the requested memory id and looks up the account's tombstones. On a match it
returns the original `purge_receipt_id` and `purged_at` with
`already_purged=true`, creating no second tombstone, no second receipt
identity, no synthetic content, and no history. A cross-account retry has no
matching tombstone and receives the plain 404, so one account's erasure is
never another account's information.

---

## 6. Derived-state fan-out matrix

Each category was inspected, not assumed.

| Surface | Current UMS state exists? | Purge action | Evidence |
|---|---|---|---|
| Canonical memory (`memory_records`) | yes | delete | PostgreSQL readback |
| Content revisions (`memory_revisions`) | yes | delete | PostgreSQL readback |
| Review revisions (`memory_review_revisions`) | yes | delete | PostgreSQL readback |
| Lifecycle revisions (`memory_lifecycle_revisions`) | yes | delete | PostgreSQL readback |
| Provenance (`memory_provenance`) | yes | delete | PostgreSQL readback |
| Persona links (`memory_persona_links`) | yes | delete | PostgreSQL readback |
| Vector / embedding | **NONE** | none | `guardian/vector_store.py`, `guardian/embedding_engine.py`, and `guardian/embeddings/` never reference `memory_records` or `memory_id` |
| Summaries | **NONE** | none | no UMS summary relation exists |
| Heat / ranking projection | **NOT UMS** | none | the only `heat_score` column belongs to `imprints` (cognition), which is not a canonical memory relation and is not keyed to `memory_records` |
| Cache | **NONE** | none | no UMS memory cache or projection table; no in-service vault cache |
| Queue / retry payload | **NONE** | none | no `memory_id` appears anywhere under `guardian/queue/` or `guardian/cognition/` |
| Working export artifacts | none under app control | none | archives previously downloaded by a user are outside Codexify's control |
| Graph-derived memory state | **NONE** | none | no graph-derived canonical memory state exists |

```text
UMS VECTOR PURGE OBLIGATION: NONE - NO CURRENT DERIVED STATE
QUEUED PURGE FAN-OUT: NONE
```

No generic queue scanner, vector-deletion framework, or graph-erasure
subsystem was created for projections that do not exist. Building one would be
architecture expansion, which Campaign governance has frozen.

Legacy `memory_entries` is **not** UMS: it is the separate silo table owned by
`guardian/core/db.py`, it is in `OMITTED_FAMILIES`, and ordinary-memory purge
does not touch it. Deleting it would be generic-deleting a different subsystem
because its name contains "memory".

---

## 7. Resurrection suppression

`MemoryPurgeService.source_atom_suppression_status` is provider-neutral and
account-scoped. The caller supplies canonical *raw* source identity; the
service normalizes it, computes the versioned fingerprint, and performs the
account-scoped lookup. Stored fingerprints are never a caller-facing input and
never leave the service.

```text
outcome: suppressed_previously_purged | allowed
```

`suppressed_previously_purged` is deliberately distinct from deduplication: a
suppressed atom is **never created**, not merely skipped as a duplicate.
Proven: same account + same atom suppressed; different account unaffected;
different atom allowed; different source system is a different identity;
retry deterministic.

### 7.1 Fail-closed on ambiguous import origin

Import-origin identity is derived from `memory_provenance` before that row is
deleted. A record that is demonstrably import-origin but cannot yield exactly
one safe deterministic source-atom identity **fails closed before deletion**,
and the record survives untouched. Two cases are refused:

- import-origin provenance lacking a stable source identity; and
- one canonical record fed by several distinct import atoms, which a
  single-fingerprint minimal tombstone cannot represent.

Erasing in either case would leave automatic resurrection possible while
claiming the record was permanently erased.

A direct/manual record legitimately carries `source_atom_fingerprint = NULL`.

### 7.2 No bypass

There is no `ignore_purge_tombstone`, no force/override/clear/unpurge method,
and no generic bypass flag. The service's public surface is exactly
`preview_purge`, `purge`, and `source_atom_suppression_status`, asserted by
test. No model, Operator, importer, retry, or internal service can clear
suppression.

```text
EXPLICIT REINTRODUCTION UI/FLOW: DEFERRED
SUPPRESSION CLEAR BY MODEL/OPERATOR: IMPOSSIBLE
```

This does not block permanent erasure.

---

## 8. Import boundary

Repository inspection established the canonical-memory writer set exhaustively:

```text
CURRENT CANONICAL IMPORTED-MEMORY WRITER: NONE
UMS-08 REMAINS PARKED
```

`MemoryRecord(` is constructed in exactly two places: `memory_vault_creation.py`
(direct user-authored Vault creation) and `account_restore.py` (restore). No
importer, classifier, adapter, or provider integration creates canonical
`memory_records` rows. `guardian/services/openai_account_import.py` is
account-level import in a different subsystem and does not write canonical
memory.

Consequently:

- no provider-specific suppression wiring was needed, and
- `guardian/services/openai_account_import.py` was **not** modified.

The suppression authority is proven directly at the provider-neutral service
boundary. No Anthropic adapter was built and no UMS-08 capability was reopened.
Provider-specific supported-user re-import qualification belongs to UMS-12.

---

## 9. Personal Facts boundary

```text
PERSONAL FACT PERMANENT-ERASURE AUTHORITY: NOT REQUIRED BY ORDINARY UMS-11 TARGET
```

Grounds:

1. Contract §12's purge fan-out list does not mention Personal Facts.
2. Contract §3.3 states the ordinary lifecycle writer has no authority over
   Personal Facts, and §3.4 gives them specialized authority through the
   Personal Facts service.
3. `personal_facts` and `personal_fact_evidence` key to `chat_messages`, not to
   `memory_records`; there is **no** foreign key from any Personal Facts
   relation to a canonical `memory_records` row.
4. UMS-11 operates on one exact ordinary `memory_records` row, and the spec's
   allowance for deleting directly linked Personal Fact evidence requires an
   explicit ownership relationship that does not exist.

Stop condition 6 therefore did not trigger.

Stated honestly rather than papered over: `personal_fact_evidence.excerpt` is
content-bearing, and in principle a fact could have been learned from a purged
memory. There is no schema path for ordinary purge to identify or remove it,
and the contract forbids the ordinary writer from touching it. This is a real
boundary of the current architecture, not a claim that no related content can
exist. Erasing such evidence would require a separate, explicitly authorized
Personal Facts erasure path.

---

## 10. Portability

`account-export.v8` is the nine-family canonical UMS graph: the eight v7
families plus `memory_purge_tombstones`.

- v7 retains its exact eight-family meaning; a v7 archive never carries
  tombstones and is not reinterpreted as malformed because v8 exists. v6 and
  earlier are likewise unchanged.
- The production default export schema (`account-export.v3`) is **unchanged**;
  v8 is opt-in. Silently widening the default would have redefined existing
  export behavior for every account, which this slice does not authorize.
- Field set is exact, ordering deterministic by `purge_receipt_id`, and
  `entity_counts` reports the exact tombstone count.
- Export fails closed on: cross-account rows, duplicate receipt identity,
  relaxed `suppress_reimport`, malformed or unrecognised-version fingerprints,
  missing purge time, and any content-bearing field.
- **After purge the erased memory is absent from the archive** — content,
  revisions, review history, lifecycle history, persona links, and provenance
  all leave nothing behind, so an archive is not a surviving copy of what was
  erased.

Restore: stable receipt identity, record fingerprint, and source-atom
fingerprint all survive; `purged_at` is exact; `suppress_reimport` remains
true; replay is idempotent; a same-receipt-id semantic conflict fails closed and
rolls back; a late tombstone-persistence failure rolls the whole restore back.

**Contradiction rule.** A v8 archive fails closed if it carries both a live
canonical memory and a tombstone suppressing that same identity or that same
source atom. The check recomputes the canonical digest from the live row and
compares exactly, so neither side is silently preferred and the tombstone is
never silently dropped.

**Suppression survives restore** — proven at the service boundary, which is the
whole point: an atom purged on the source instance is still suppressed on the
destination.

---

## 11. Routes

Exactly two internal route templates were added:

```text
GET  /api/memory-vault/items/canonical/{memory_id}/purge-preview
POST /api/memory-vault/items/canonical/{memory_id}/purge
```

`POST .../purge` is the only POST on the Memory Vault router, so the
destructive surface is unambiguous.

They are thin adapters. Asserted by test, the route bodies contain no session,
`execute`, `select`, `delete`, fingerprint function, hashlib, or ORM model
reference: no SQL, no row locking, no CAS comparison, no child enumeration, no
fingerprint derivation, no tombstone construction, and no suppression policy.
The request model accepts only `expected_updated_at`, `confirmation_token`,
`reason`, and `request_ref`; caller-supplied account ids, source fingerprints,
purge receipt ids, and cascade controls are never forwarded.

HTTP posture: 401 blank account; 404 missing/cross-account (with the
same-account idempotent-retry exception); 409 stale CAS, stale/wrong
confirmation, ambiguous import-origin identity, or fan-out integrity failure;
422 malformed body. No response leaks SQL, a constraint name, a stored
fingerprint, a plaintext source id, or another account's existence.

Internal-only posture is unchanged: the router stays flag-gated behind
`CODEXIFY_ENABLE_MEMORY_VAULT_ROUTES` with `core_surface=False`. No public
Beta surface was widened and no frontend route was added.

---

## 12. Backup and external-copy truth

UMS-11 proves deletion of canonical content and all content-bearing child
state from current state under Codexify's direct control, in the same
transaction as its suppression tombstone.

It does **not** claim, and no claim is made, that it erases:

- external user backups,
- previously downloaded account-export archives,
- filesystem snapshots outside the application's immediate control, or
- remote systems Codexify does not control.

Restoring an archive restores suppression; it does not retroactively erase the
source instance's other copies.

---

## 13. Two defects the tests caught

Recorded because both were real and both were fixed before commit.

1. **Delimiter-injection collision in the source-atom digest.** Fields were
   joined with a bare `\x1f`, so `("openai", "importer", "a\x1fb")` and
   `("openai", "importer\x1fa", "b")` produced an identical digest — directly
   contradicting the field-boundary guarantee in the code's own docstring. A
   collision would let two different source atoms share one suppression entry.
   Fixed by length-prefixing every field before hashing. The regression test is
   retained.

2. **Cross-account preview leaked a posture instead of returning 404.**
   `preview_purge` never checked whether the loaded target was `None` before
   computing the envelope, so a missing or cross-account target raised
   `AttributeError` internally and surfaced as a 409 rather than the
   indistinguishable 404. Fixed by raising `MemoryPurgeNotAvailable`, matching
   `purge`. This was an information-posture bug, not a data-access one.

A third, smaller defect: `purged_at` was missing from the shared
timestamp-normalization set in `_executor_row_equals`, so an idempotent replay
compared a session-timezone `datetime` against the archive's UTC-offset string
and reported its own prior write as a semantic conflict. Fixed by adding
`purged_at` to that set, which is the correct location for the fix.

---

## 14. Regression results

All PostgreSQL-backed suites ran against real disposable databases
(`TEST_DATABASE_URL=postgresql://localhost/postgres`, the local PostgreSQL 17
instance; the Compose service host `db` is not resolvable from the host shell).

| Suite | Collected | Result |
|---|---|---|
| `tests/migration/test_memory_purge_tombstone_migration.py` (new) | 10 | 10 passed, 0 failed |
| `tests/services/test_memory_purge.py` (new) | 24 | 24 passed, 0 failed |
| `tests/routes/test_memory_vault_purge.py` (new) | 18 | 18 passed, 0 failed |
| `tests/services/test_account_export_memory_purge_tombstones.py` (new) | 19 | 19 passed, 0 failed |
| `tests/services/test_account_restore_memory_purge_tombstones.py` (new) | 19 | 19 passed, 0 failed |
| **New UMS-11 tests** | **90** | **90 passed, 0 failed** |
| UMS migration regression (governance, revision, review, lifecycle, purge — 5 files, serial) | 56 | 56 passed, 0 failed |
| UMS portability regression (content / review / lifecycle export+restore, unified restore, round-trip — 8 files) | 157 | 157 passed, 0 failed |
| Memory Vault sweep (activation, creation, mutation, read projection, lifecycle, correction, review, purge, base routes — 11 files) | 359 | 359 passed, 0 failed |
| Alembic head | — | exactly one, `c7f4a9b2e6d1` |

Total: **662 test executions, 0 failed, 0 unexpected errors.**

### 14.1 Environment posture

Two environment facts, recorded so the numbers above are reproducible rather
than mysterious:

- `TEST_DATABASE_URL` was pointed at the local PostgreSQL 17 instance
  (`postgresql://localhost/postgres`). The `.env` default targets the Compose
  service host `db`, which is not resolvable from the host shell, so the
  disposable-database fixtures would otherwise skip rather than run.
- `STORAGE_BASE_PATH` was pointed at a workspace directory. The default
  pytest path resolves to a `/tmp` subdirectory, which this sandbox does not
  permit writing to; four `test_memory_vault_activation.py` tests import the
  full application and were erroring at storage construction for that reason
  alone. With the path redirected they pass.

Neither substitution hides a failure. Both are environment bindings, not
assertion changes, and both suites pass under them.

### 14.2 Prior-slice test updated, and why

`tests/migration/test_memory_lifecycle_revision_persistence_migration.py`
asserted `heads[0] == "b8e2f4a6c901"`. UMS-11 correctly advances the head, so
that terminal-value assertion had to change. It now asserts topology instead:
exactly one head, with the C10B-P revision in its intentional lineage. This
follows the precedent set by C10B-P, which made the same change to the C10A-P
test when it advanced the head. No prior slice's *behavioral* proof was
weakened.

---

## 15. Runtime boundary

```text
PERMANENT CANONICAL CONTENT REMOVED:        YES
CONTENT-BEARING REVISIONS REMOVED:         YES
REVIEW / LIFECYCLE HISTORY RETAINED:        NO
MINIMUM NON-CONTENT TOMBSTONE RETAINED:     YES
TOMBSTONE CONTAINS MEMORY CONTENT:          NO
SAME-ACCOUNT RETRY IDEMPOTENT:              YES
CROSS-ACCOUNT TOMBSTONE DISCLOSURE:         NO
SOURCE-ATOM RESURRECTION SUPPRESSED:        YES
MODEL CAN CLEAR SUPPRESSION:                NO
INFRASTRUCTURE OPERATOR CAN CLEAR:          NO
GENERIC SUPPRESSION BYPASS FLAG:            NO
RETIRED TREATED AS PURGE:                   NO
UMS-08 REACTIVATED:                         NO
ANTHROPIC ADAPTER BUILT:                    NO
PERSONAL FACT AUTHORITY BYPASSED:           NO
PRIOR EXPORT SCHEMA REDEFINED:              NO
TOMBSTONE PORTABILITY PROVEN:               YES
SCHEMA CHANGED:                             YES (one new additive migration)
MIGRATION HEAD CHANGED:                     YES (b8e2f4a6c901 -> c7f4a9b2e6d1)
RETRIEVAL BEHAVIOR CHANGED:                 NO
FRONTEND CHANGED:                           NO
PUBLIC RELEASE CLAIM EXPANDED:              NO
NEW ADR:                                    NO
```

### 15.1 Authorized-file deviation, disclosed

`guardian/core/pgdb.py` was edited although it was not in the task's
authorized-file list. It is the **sole** account-export data authority: the
exporter resolves every per-family reader through the `db` object, and that
object's bundle/iterator/reader functions all live in `pgdb.py`. There is no
supported way to add a canonical export family from
`guardian/services/account_export.py` alone.

Without it, `memory_purge_tombstones` could not be exported at all, and
"suppression survives migration" — half of the gap this slice was admitted to
close — would have been unachievable. The task's Git section explicitly allows
"conditional authorized files only when actually required and documented".

The change is **purely additive**: 43 insertions, 0 deletions, touching exactly
four points — the unified-memory payload order, one bundle `SELECT`, one
iterator payload-order entry, and one reader function. It changes no existing
family, no existing schema-version meaning, and no destructive behavior. The
zero-deletion property is verified in §16.

---

## 16. Staged patch

```text
guardian/db/models.py                                          (modified)
guardian/db/migrations/versions/c7f4a9b2e6d1_*.py             (new)
guardian/services/memory_purge.py                             (new)
guardian/routes/memory_vault.py                                (modified)
guardian/services/account_export.py                            (modified)
guardian/services/account_restore.py                           (modified)
guardian/core/pgdb.py                                          (modified; conditional, §15.1)
tests/migration/test_memory_purge_tombstone_migration.py       (new)
tests/services/test_memory_purge.py                            (new)
tests/routes/test_memory_vault_purge.py                        (new)
tests/services/test_account_export_memory_purge_tombstones.py (new)
tests/services/test_account_restore_memory_purge_tombstones.py (new)
tests/migration/test_memory_lifecycle_revision_persistence_migration.py (modified, §14.2)
docs/architecture/account-export-restore-contract.md           (modified)
docs/architecture/memory-vault-contract.md                     (modified)
docs/architecture/data-and-storage.md                           (modified)
docs/architecture/proofs/runtime/2026-09-30-ums11-*.md          (new)
docs/Campaign/unified-memory-store/README.md                   (modified)
docs/architecture/00-current-state.md                          (modified)
```

`guardian/services/openai_account_import.py` and `guardian/protocol_tokens.py`
were **not** modified: the former because no canonical imported-memory writer
exists (§8), the latter because the purge service owns its own bounded
vocabulary and needed no new shared protocol token.
