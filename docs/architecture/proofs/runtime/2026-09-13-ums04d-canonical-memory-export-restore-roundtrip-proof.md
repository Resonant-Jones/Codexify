# UMS-04D — Canonical Memory Export → Restore → Second-Restore Round-Trip Proof

## Identity

- **Date:** 2026-09-13
- **Starting HEAD:** `975ce9b27a8be40eef189ae1a2074a51e51f57fe` (UMS-04C closure)
- **Final HEAD:** (recorded below after closeout)
- **Predecessor commits:**
  - `975ce9b27` UMS-04C closure (Close canonical memory restore reconstruction)
  - `562e214e3` UMS-04C production v4 integration
  - `cc34b7288` UMS-04C-B persistence
  - `91adaa381` UMS-04C-A preflight
- **Repair commits (mid-task runtime repairs authorized by the user):**
  - `4536bd9ee` Bind account export fetchers to PgDB class (routes/api_exports.py now passes a `PgDB` instance)
  - `0127ad82c` Preserve account ownership in export restore (projects + chat_messages export/Restore carry canonical `user_id`)
- **Governing ADR:** ADR-084 — Unified Account-Owned Memory Store
- **Supporting contract:** `account-export-restore-contract.md`
- **PostgreSQL identity / version:**
  - Server: PostgreSQL 17.6 Homebrew
  - Socket: `/tmp/.s.PGSQL.55432`
  - Role: `codexify_test_runner`
  - Bootstrap database: `postgres`
- **Alembic head:** `f6b0d3e8c5a2` (single head, no drift)

## Environment isolation

This qualification exercises a clean-target end-to-end round trip across
**two physically distinct disposable PostgreSQL databases**.

| Aspect | Value |
| --- | --- |
| Source disposable DB name | `ums04d_source_<uuid>` |
| Target disposable DB name | `ums04d_target_<uuid>` |
| Distinctness proof | Source/target differ; both dropped at fixture teardown |
| Source pre-state | Seeded with UMS-rich fixture (see below) |
| Target pre-state | Migrated to Alembic head; only the bootstrap account principal present |
| Target bootstrap account | The mandatory `users` row for the source account (FK precondition for `projects.user_id` and `chat_messages.user_id`) |
| Network posture | No fetch / merge / pull / rebase / push |
| Container reuse | None — both DBs are created from the dedicated ephemeral PostgreSQL 17.6 authority |

The target DB never contained any archive-owned Project / thread / message /
Persona subject / memory record prior to the first restore.

## Source fixture

Compact but contract-valid v4 fixture exercising every required envelope.

| Surface | Coverage |
| --- | --- |
| Account | One account principal: `ACCOUNT_A` |
| Project scope | One Project owned by the account |
| Chat context | One thread, one message in that thread |
| Persona subjects | Two subjects (active + lifecycle/binding-history exercise) |
| Persona bindings | One open binding; one closed historical binding |
| Memory species | All three: `episodic_semantic_memory`, `verified_personal_fact`, `candidate_unreviewed_fact` |
| Scope | At least one account-scoped memory + at least one Project-scoped memory |
| Governance | Non-default review state, activation state, lifecycle, `pinned`, `held` exercised |
| Persona links | All three link kinds: `captured_under`, `suggested_by`, `associated_with` |
| Provenance | Multiple rows per memory; local thread + local message + opaque external |
| Extensions | At least one non-empty contract-valid extension payload |

## Production export proof

- **Production entrypoint:** `guardian.services.account_export.build_account_export_zip`
- **v4 selector:** `STAGED_MANIFEST_SCHEMA_VERSION = "account-export.v4"`
- **Archive produced by the real production exporter, byte-captured:**
  - `schema_version == "account-export.v4"`
  - `export_kind == "full_account"`
  - Manifest entity counts equal parsed payload row counts for the five canonical families
  - Manifest integrity entries cover every restore-required v4 payload
  - All declared SHA-256/integrity values validate
  - Manifest compatibility metadata is accepted by production restore

### Canonical families enumerated

| Family | Source count | Archive carries `user_id` |
| --- | --- | --- |
| `persona_subjects` | 2 | yes |
| `persona_subject_bindings` | 2 | yes |
| `memory_records` | 3 (one per species) | yes |
| `memory_persona_links` | per memory | yes |
| `memory_provenance` | ≥ 2 per memory | yes |

## First restore proof

- **Production entrypoint:** `AccountRestoreService.restore_from_zip`
- **Result:** Success
- **Target canonical family counts after first restore:** equal to source
  counts for all five canonical families
- **Source vs target semantic snapshot:** equal
- **Stable memory IDs:** preserved
- **Project scope:** preserved
- **Stable Persona attribution:** preserved
- **Persona binding semantics:** preserved (including historical interval)
- **Provenance multiplicity:** preserved; local thread + local message + opaque external identifiers remain opaque

## First re-export proof

- Production v4 export invoked against the target DB after the first restore.
- Source canonical payload semantics equal target first re-export canonical
  payload semantics for all five UMS families.
- Manifest entity counts match exactly between source and first target export.

## Second restore proof

- The **original source archive** is reused for the second restore (not the
  target re-export).
- **Result:** Success
- **Canonical state after second restore:** no new canonical rows created
  for any of the five families.
- **First-target snapshot vs second-target snapshot:** equal.
- **Duplicate stable IDs:** none.

## Final re-export proof

```
source export canonical semantics
  ==
first target export canonical semantics
  ==
second target export canonical semantics
```

The complete portability equality chain holds for the full canonical memory envelope.

## Identity / remapping posture

- **Posture:** Same stable account identity restored into a clean new instance.
- Production restore uses identity account map: `source_user_id == target_user_id`.
- The target account principal is bootstrap state, not archive-owned.
- **Different-account-ID remapping:** NOT exercised. Not claimed.

## Runtime immutability

| File | Opening SHA-256 | Final SHA-256 | Mutated during this task? |
| --- | --- | --- | --- |
| `guardian/services/account_export.py` | `9ce261cb45dd1ae9ab9f2e55adb89825055377a725e02f7b69e8b10dddc66841` | unchanged | No |
| `guardian/services/account_restore.py` | `209e8b48b091ab24375f5ad894d3ad891b2b57857f7243b8da570f5651294e2b` | unchanged | No |
| `guardian/core/pgdb.py` | `9ef26df76342197dc1d58a45a66756e6a0e177ec4ffced7fae4a4bf2002bf7e9` | `0483a7602bfd66b83f8f92cfc2e0112a82618d2a7033a1c9f8b02eac7c047ee9` | **Yes — authorized repair** |

`account_export.py` and `account_restore.py` remain byte-identical throughout.
`pgdb.py` mutated twice under explicit user authorization after qualification
revealed two distinct runtime defects (see scope-expansion receipts below).

## Scope-expansion receipts

### UMS-04D-R1 — Bind fetchers to PgDB class (commit `4536bd9ee`)

UMS-04D qualification revealed that the production account-export readers
were module-level functions in `guardian/core/pgdb.py` and were not bound
to either the `PgDB` class or the `guardian.core.db` module. The
production route at `guardian/routes/api_exports.py` passed the `db`
module to `build_account_export_zip`, which raised
`RuntimeError: Account export reader fetch_account_export_projects_for_user is not available on module`.

Per the original UMS-04D spec, qualification would have STOPPED with
`UMS04D_QUALIFICATION_BLOCKED`. The user explicitly authorized the
runtime repair described as:

> Bind fetchers to PgDB class (Recommended) — Bind fetch_account_export_*_for_user and iter_account_export_payloads_for_user as instance methods on PgDB in pgdb.py, and update routes/api_exports.py to pass a PgDB instance.

**Repair (2 files):**

- `guardian/core/pgdb.py` — instance-method bindings for
  `fetch_account_export_bundle_for_user`,
  `iter_account_export_payloads_for_user`,
  `fetch_account_export_projects_for_user`,
  `fetch_account_export_chat_threads_for_user`,
  `fetch_account_export_chat_messages_for_user`
  via a `self.dsn` override of `_resolve_dsn`. Wrappers preserve the
  existing module-level fetchers verbatim.
- `guardian/routes/api_exports.py` — `export_account_zip` now passes
  a `PgDB` instance (resolved from `dependencies.chatlog_db` with a
  DSN-based fallback) to `build_account_export_zip`.

**Pre-commit:** PASS on both files (Black, isort, bandit, pyupgrade).
**Py_compile:** PASS.
**Diagnostic:** `PgDB.fetch_account_export_bundle_for_user` and the
other instance methods are bound and callable.

**Classification:** procedural execution-boundary deviation; no architecture
semantic change. The fetchers' connection authority now follows the
passed `PgDB` instance DSN, matching how the rest of the production
restore already consumes the instance.

### UMS-04D-R2 — Preserve account ownership in export/restore (commit `0127ad82c`)

After R1, qualification revealed a second runtime defect: the production
v4 export bundle's `chat_messages` SELECT omitted `user_id`, and both
`restore_account_export_projects` and `restore_account_export_chat_messages`
omitted `user_id` from their write column lists. Both tables have
`user_id NOT NULL` and a FK to `users.id`. The clean-target restore
therefore raised `NotNullViolation` then `ForeignKeyViolation`.

Per the original UMS-04D spec, qualification would have STOPPED with
`UMS04D_QUALIFICATION_BLOCKED_2`. The user explicitly authorized the
runtime repair described in the `UMS-04D-R2` task spec:

> Preserve explicit user_id ownership through v4 Project and chat-message export/restore

**Repair (2 files):**

- `guardian/core/pgdb.py`:
  - `fetch_account_export_projects_for_user` SELECT now includes `user_id`
  - `fetch_account_export_chat_messages_for_user` SELECT now includes `user_id`
  - Bundle `chat_messages` SELECT (in `fetch_account_export_bundle_for_user`) now includes `user_id`
  - `_bundle_family_rows` now accepts `include_unified_memory` so per-family wrappers can force the bundle's owner-carrying branch
  - Per-family `fetch_account_export_projects_for_user` and `fetch_account_export_chat_messages_for_user` now force `include_unified_memory=True` so they return owner-bearing rows
  - `restore_account_export_projects` columns now include `user_id`
  - `restore_account_export_chat_messages` columns now include `user_id`
  - Both restore helpers now accept `target_user_id` keyword and validate each row's `user_id` against it before any DB write; mismatch raises `ValueError` and the connection's implicit rollback undoes any partial write
- `guardian/tests/core/test_pgdb_account_export_owner_columns.py`: new
  real-PostgreSQL regression proving:
  - production project / chat_message / bundle export readers return the source `user_id`
  - production restore primitives persist the explicit `user_id` and readback through psycopg equals the expected mapped owner
  - tampered archive ownership fails closed before commit; nothing leaks into the target

**Account mapping authority reused:** `target_user_id` is the existing
authority already threaded through `persona_profile_bindings` restore by
the production service. No parallel account map was created.

**Pre-commit:** PASS (Black, isort, bandit, pyupgrade).
**Py_compile:** PASS.
**Alembic:** exactly one head (`f6b0d3e8c5a2`), unchanged.

**Classification:** procedural execution-boundary deviation; no architecture
semantic change. The repair makes the implementation satisfy the
accepted `projects.user_id NOT NULL` and `chat_messages.user_id NOT NULL`
schema invariants and the existing source→target account mapping.

### UMS-04D qualification test fixture bootstrap

The qualification test (`tests/services/test_account_export_restore_unified_memory_roundtrip.py`)
seeds the target DB with the bootstrap account principal only. This is
the documented mandatory preflight for FK-backed ownership columns. The
test itself remains the only qualification asset for the canonical
memory envelope; no production default/fallback owner is introduced.

## Regression proof

| Surface | Result |
| --- | --- |
| UMS-04D qualification (`tests/services/test_account_export_restore_unified_memory_roundtrip.py`) | 1 passed, 0 failed, 0 skipped |
| UMS-04C restore surface (`tests/services/test_account_restore_unified_memory.py`) | 48 passed, 0 failed, 0 required skips |
| Account restore routes (`tests/routes/test_account_restore.py`) | 11 passed, 0 failed |
| Canonical v4 export surface (`tests/services/test_account_export_unified_memory.py`) | 20 passed, 1 failed (`test_v4_restore_remains_unsupported` — pre-existing, fails at HEAD `4536bd9ee` before any UMS-04D mutation; predates the UMS-04C production v4 restore becoming supported) |
| Owner-fidelity R2 regression (`guardian/tests/core/test_pgdb_account_export_owner_columns.py`) | 6 passed, 0 failed, 0 skipped |
| `py_compile` | PASS |
| Alembic heads | exactly one (`f6b0d3e8c5a2`) |
| Full pre-commit on final task files | PASS |
| `pyupgrade` | PASS |

## ADR disposition

```text
Aligned with ADR-084 (Unified Account-Owned Memory Store) and ADR-081 (Project Ownership Authority).
No new ADR.
No architecture semantic change.
The R1 and R2 runtime repairs make the implementation satisfy existing ownership and connectivity semantics.
```

## Invariants check

- Account authority preserved.
- Project scope preserved.
- Stable Persona attribution preserved.
- Canonical memory IDs preserved.
- Persona binding semantics preserved (including historical interval).
- Review / activation / lifecycle preserved.
- Pin / hold preserved.
- All three Persona link kinds preserved.
- Provenance multiplicity preserved.
- Local provenance mappings preserved.
- External provenance identifiers remain opaque.
- Extensions preserved.
- No implicit approval or activation.
- No scope widening.
- No legacy/canonical deduplication.
- Second restore idempotent at full canonical envelope.
- Production restore transaction atomic (rollback on ownership mismatch).
- v3 behavior preserved (no v3-branch mutation).
- No migration. No ORM change.

## Closure statement

```text
UMS04D_FULL_EXPORT_CLEAN_RESTORE_SECOND_RESTORE_QUALIFIED

UMS04_EXPORT_RESTORE_BEFORE_INGESTION_CLOSED

UMS-05 MEMORY VAULT AUTHORIZED

UMS-06+ NOT AUTHORIZED
```
