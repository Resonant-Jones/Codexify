# UMS-05C9-W — Ordinary-Memory Content Correction Writer

**Status:** CLOSED
**Slice:** `UMS-05C9-W` — ordinary-memory content correction writer
**Campaign:** Unified Account-Owned Memory Store
**Date:** 2026-09-28
**ADR impact:** ALIGNED WITH ADR-084 — no new ADR
**Class:** Runtime capability (canonical mutation writer) on persistence proven by UMS-05C9

---

## 1. Purpose

UMS-05C7 classified ordinary-memory content correction as `NEW_CANONICAL_PERSISTENCE_REQUIRED`
because `memory_provenance` cannot preserve prior canonical text. UMS-05C9 closed the persistence
and portability half of that gap by adding the `memory_revisions` family and
`account-export.v5`.

UMS-05C9-W closes the remaining half: the **writer**. It adds authenticated direct correction of
canonical ordinary episodic memory, atomically producing, for every changed correction:

1. the new `memory_records.text_content`;
2. exactly one append-only `memory_revisions` row holding the exact prior and resulting text;
3. exactly one existing-format `memory-vault-mutation.v1` receipt;
4. one new database-authored `memory_records.updated_at` CAS token.

This slice does **not** implement review/lifecycle transitions, Personal Fact correction, revision
browsing or a revision read API, retrieval redesign, or any frontend surface.

---

## 2. Lineage

| Field | Value |
|---|---|
| Branch | `feature/ums-continued` |
| Starting HEAD | `6ba33498f5eebc6d0a45b9ddef3a45388bbed595` (UMS-05C9) |
| Alembic head at start | `c3d9f4e6a1b2` (single head) |
| Alembic head at end | `c3d9f4e6a1b2` (single head, unchanged) |
| Migrations created | none |
| Schema change | none |
| Export-schema change | none |
| Push count | `0` |

C9 is the direct parent and is in branch ancestry. No fetch, pull, merge, rebase, reset,
cherry-pick, or push was performed.

---

## 3. Authorized surface

Production edits (2):

- `guardian/services/memory_vault_mutation.py`
- `guardian/routes/memory_vault.py`

Tests (3):

- `tests/services/test_memory_vault_content_correction.py` — new
- `tests/routes/test_memory_vault_content_correction.py` — new
- `tests/routes/test_memory_vault_activation.py` — extended

Documentation (4):

- `docs/architecture/memory-vault-contract.md`
- this proof receipt
- `docs/Campaign/unified-memory-store/README.md`
- `docs/architecture/00-current-state.md`

Read-only: ORM models, migrations, `account_export.py`, `account_restore.py`, `pgdb.py`,
`memory_vault_creation.py`, `memory_vault_read.py`, Personal Facts, retrieval, frontend, the C9
portability suites, and the C8-Q migration suites.

---

## 4. Design decisions

### 4.1 Correction reuses the existing mutation authority

`MemoryVaultMutationService` gains `correct_content(...)`. No second service, no second mutation
authority, no parallel writable truth. Account authority remains constructor-bound via
`authenticated_account_id`; there is no per-call account override.

### 4.2 Validation is a distinct exception class

Three new exception types separate the failure classes the route must map differently:

| Exception | Meaning | Route status |
|---|---|---|
| `MemoryVaultContentCorrectionInvalid` | ordinary request validation (non-string / blank) | `422` |
| `MemoryVaultContentCorrectionUnsupported` | species boundary (not ordinary episodic) | `409` sanitized |
| `MemoryVaultContentCorrectionIntegrityError` | history integrity (gapped or divergent tail) | `409` sanitized |

An earlier iteration mapped blank content to `409` because the validation error shared the
integrity base class; the dedicated `...Invalid` type fixed that without weakening the
`...IntegrityError` posture.

### 4.3 The receipt never carries authored text

The receipt is audit evidence. It records revision identity and sequence only:

```text
action              = "content_correction"
field_name          = "revision_number"
previous_value      = revision_number - 1
new_value           = revision_number
extensions.revision_id
extensions.new_values = { revision_id, revision_number, content_changed: true }
```

Exact prior and resulting text live solely in `memory_revisions.old_text_content` /
`new_text_content`. A receipt is not a revision.

### 4.4 History is validated before it is appended

`_next_revision_number` reads existing revisions in ascending order and fails closed when:

- numbering is not contiguous from `1`; or
- the latest `new_text_content` no longer equals current `memory_records.text_content`.

Malformed history is never repaired, reordered, or silently renumbered.

### 4.5 Personal Facts are refused, not delegated

`ACTION_CONTENT_CORRECTION` is restricted to
`_CORRECTABLE_SPECIES = MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value`. Any other species
raises `MemoryVaultContentCorrectionUnsupported`. Personal Fact correction remains owned by the
specialized Personal Facts service and its `personal_fact_revisions` family. This slice adds no
delegation, and no trigger was added purely to make the boundary look stronger at the database
layer — the species invariant is enforced in the service.

---

## 5. Atomicity

The correction runs inside one transaction:

1. validate input;
2. load the authorized memory and compare the CAS token;
3. reject unsupported species;
4. if the text is byte-identical to current content, roll back and return the no-op result;
5. validate the existing revision tail and compute the next contiguous number;
6. `UPDATE memory_records ... WHERE memory_id AND user_id AND updated_at == expected_updated_at`
   setting `text_content` and `updated_at = clock_timestamp()` and returning the new token;
7. insert exactly one `memory_revisions` row;
8. insert exactly one receipt;
9. commit;
10. read back through the existing `MemoryVaultReadService` and assert both the content and the
    new token.

Any failure at steps 6–8 rolls the whole transaction back. A stale CAS outranks a no-op: the token
is compared before the text equality check, so a request whose text happens to equal current
content still conflicts when the token is stale.

The CAS token is timezone-aware, database-authored (`func.clock_timestamp()`), and never supplied
by the client.

---

## 6. Exact-text preservation

`content` is validated for type and non-blankness but is **never trimmed**. Blankness is judged
on `value.strip()`; the original unstripped string is what is persisted. Whitespace, leading and
trailing newlines, Unicode, punctuation, and casing survive byte-for-byte. The C9 database CHECK
`old_text_content <> new_text_content` compares exactly, with no trimming and no collation.

---

## 7. Route

```text
PATCH /api/memory-vault/items/canonical/{memory_id}/content
```

`VaultContentCorrectionRequest` extends the existing `_VaultMutationRequest` and adds `content`.

The handler is a **thin adapter**. It performs:

- no SQL;
- no revision-number calculation;
- no CAS comparison;
- no row locking;
- no read-before-write;
- no old/new text comparison;
- no receipt construction.

It delegates wholly to `service.correct_content(...)` and maps exceptions to status codes:

| Condition | Status | Detail |
|---|---|---|
| missing or cross-account memory | `404` | shared indistinguishable unavailable detail |
| blank / non-string content | `422` | `Content must be a non-empty string` |
| stale `expected_updated_at` | `409` | shared stale-write detail |
| unsupported species, integrity failure, or other mutation error | `409` | `Memory content correction unavailable` (sanitized) |

The sanitized 409 exposes no species, SQL, constraint, chain, or content detail.

The endpoint inherits the existing `memory_vault` internal-only posture: the same supported-profile
label, internal-only flag, and profile gating as the rest of the Vault surface. It is excluded from
the public OpenAPI document by that same profile mechanism, and
`tests/routes/test_memory_vault_activation.py` now asserts the new PATCH path is admitted
internally, hidden from OpenAPI, and quarantined in non-admitted profiles.

Failure details are the existing shared strings, so no new message surface was introduced:

| Status | Detail |
|---|---|
| `404` | `Memory not available` |
| `409` (stale CAS) | `Memory changed since it was read` |
| `409` (unsupported/integrity) | `Memory content correction unavailable` |
| `422` | `Content must be a non-empty string` |

### 7.1 Control-plane delta

Route inventory was taken at the opening C9 baseline and again at the close of this slice, rather
than reusing an older hardcoded count.

| Inventory | C9 baseline (`6ba33498`) | C9-W close (`2c21cd0e`) | Delta |
|---|---|---|---|
| Route decorators (methods) | 8 | 9 | **+1** |
| Distinct path templates | 7 | 8 | **+1** |
| New template | — | `/items/canonical/{memory_id}/content` (`PATCH`) | +1 |

The only control-plane delta is the one internal PATCH route on the one new content-correction
path template. No existing Vault path or method was removed, re-pathed, or re-methoded, and no
new feature flag was created.

---

## 8. Regression evidence

All suites run serially against PostgreSQL at `127.0.0.1:5432` (Homebrew 17.6, role
`codexify_test_runner`, disposable child databases). Migration suites are run serially because
parallel disposable-child-DB contention produces spurious errors.

| Suite | Result |
|---|---|
| `tests/services/test_memory_vault_content_correction.py` | **19 passed** |
| `tests/routes/test_memory_vault_content_correction.py` | **16 passed** |
| `tests/routes/test_memory_vault_activation.py` | **7 passed** |
| `tests/services/test_account_export_memory_revisions.py` + `tests/services/test_account_restore_memory_revisions.py` (C9 portability) | **23 passed** |
| `tests/migration/test_memory_governance_state_migration.py` + `tests/migration/test_memory_revision_persistence_migration.py` (serial) | **17 passed** |
| Serial Vault sweep: creation + mutation + read projection + routes + activation + correction (service) + correction (route) | **215 passed, 0 failed** |

The serial sweep count is the prior 180-test Vault baseline plus the 35 new correction tests
(19 service + 16 route).

An earlier parallel run of the same sweep reported one `ERROR`
(`tests/services/test_memory_vault_creation.py::test_create_memory_initial_provenance_is_vault_scoped`).
Re-running that file alone passed 15/15, and the fully serial sweep passed 215/215. The cause is
disposable-child-database contention, not a code defect.

---

## 9. Derived-retrieval obligation

```text
DERIVED RETRIEVAL UPDATE OBLIGATION: NONE IN CURRENT PATH
```

No embedding or vector index derives from `memory_records.text_content` in the current path.
`guardian/memoryos/` is a separate legacy system and is not a derived index of canonical Vault
content. This slice therefore records **no** obligation to recompute derived representations, and
does not silently leave one unstated.

---

## 10. Invariants check

```text
single mutation authority:                    YES
account authority constructor-bound:         YES
episodic_semantic_memory only writable:      YES
Personal Fact correction delegated:          NO  (refused, stays specialized)
CAS mandatory and timezone-aware:            YES
database-authored CAS token:                 YES
stale CAS outranks no-op:                    YES
no-op creates no revision and no receipt:    YES
no-op leaves CAS unchanged:                  YES
accepted content never trimmed:              YES
blankness judged on stripped form only:      YES
exactly one revision per changed correction: YES
exactly one receipt per changed correction:  YES
receipt contains authored old/new text:      NO
revision tail validated before append:       YES
malformed history repaired:                  NO  (fails closed)
state + revision + receipt + CAS atomic:    YES
route performs SQL / CAS math / locking:     NO
route hidden from public OpenAPI:            YES
new migration created:                       NO
schema change:                               NONE
export-schema change:                        NONE
frontend change:                             NONE
retrieval change:                            NONE
release claim change:                        NONE
```

---

## 11. Runtime boundary

```text
CONTENT-CORRECTION WRITER:             IMPLEMENTED (internal-only, authenticated)
REVIEW / LIFECYCLE WRITERS:            NOT IMPLEMENTED
PERSONAL FACT CORRECTION:              NOT IMPLEMENTED (stays specialized)
REVISION BROWSING / READ API:          NOT IMPLEMENTED
RETRIEVAL REDESIGN:                    NOT IMPLEMENTED
FRONTEND / UI:                         NONE
PUBLIC OPENAPI:                        UNCHANGED
PUBLIC RELEASE CLAIM:                  UNCHANGED
```

---

## 12. Closeout

```text
UMS05C9W_MEMORY_CONTENT_CORRECTION_COMMITTED
```

Campaign transition:

```text
UMS-05C9-W ORDINARY MEMORY CONTENT CORRECTION WRITER: CLOSED
UMS-05C10: OPEN
UMS-05C10A ORDINARY MEMORY REVIEW TRANSITION WRITER:   AUTHORIZED
UMS-05C10B ORDINARY MEMORY LIFECYCLE WRITER:          NOT AUTHORIZED
UMS-05C11+: NOT AUTHORIZED
UMS-05D+:  NOT AUTHORIZED
UMS-06+:   NOT AUTHORIZED
```

`UMS-05C10A` is the sole successor. The review family (`approve`, `reject`, `dispute`) and the
lifecycle family (`retire`, `restore`) are deliberately **not** authorized simultaneously: C7
classified both as persistence-sufficient, but they are separate authorities and splitting them
keeps the blast radius of each slice honest. UMS-05C10A has not been begun.

Gitleaks was skipped narrowly: the sandbox cannot bootstrap the Go toolchain. Every other
executable pre-commit hook ran. `gitleaks` is required at branch integration.
