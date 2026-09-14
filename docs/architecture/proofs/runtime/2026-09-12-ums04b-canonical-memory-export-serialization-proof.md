# UMS-04B — Canonical Memory Account-Export Serialization Proof

- **Slice:** UMS-04B (canonical memory account-export serialization closure)
- **Date:** 2026-09-12
- **Execution lane:** Architecture-Impact
- **Task kind:** source recovery + commit-authoritative formatter normalization + runtime requalification + Campaign closeout + bounded commit
- **Starting committed HEAD:** `7cf0439dab03f17f2a13a3d04ac587be2961e837`
- **Starting subject:** `Repair account restore test fakes`

## Verdict

```text
UMS04B_CANONICAL_MEMORY_EXPORT_SERIALIZATION_CLOSED
```

UMS-04B is closed. UMS-04 remains OPEN. UMS-04C canonical memory
restore reconstruction is now AUTHORIZED TO START. UMS-04D and UMS-05+
remain NOT AUTHORIZED.

## Governance

- ADR-084 — Unified Account-Owned Memory Store — governs.
- Account Export + Restore Contract governs.
- Unified Memory Store Contract governs.
- Runtime Protocol Token Contract governs.
- ADR impact for this slice: **aligned**; no new ADR; no accepted
  architecture semantic change.

The proof transport — local Unix-socket trust authentication through
the dedicated PG17 cluster — is a disposable proof-lane detail. It
does not alter Codexify runtime semantics or database authority.

## Starting repository identity

```text
starting HEAD:
  7cf0439dab03f17f2a13a3d04ac587be2961e837
```

## Recovery history

The UMS-04B source was recovered exactly from Git objects after an
aborted commit and an accidental `git restore --staged --worktree`
loss. The three proof-bearing blobs (`pgdb.py`,
`account_export.py`, `test_account_export_unified_memory.py`) had
been staged with `git add` immediately before the failed commit, so
their full file contents were present in the Git object database as
unreachable blobs. `git fsck --full --unreachable --no-reflogs`
enumerated 4816 unreachable blobs; the loop hashed each one and
matched the three known historical SHA-256 values exactly.

No manual reconstruction occurred. The recovered bytes are the
exact original implementation that previously passed PostgreSQL
qualification.

The recovered blobs were then restored to the working tree and
normalized through the repository's commit-authoritative pre-commit
formatter chain.

## Commit-authoritative formatter

```text
Black:
  psf/black
  revision: 26.5.1
  hook id: black
  args: --line-length=88

isort:
  pycqa/isort
  revision: 5.12.0
  hook id: isort
  args: --profile=black --line-length=88

configured order:
  Black → isort
```

Formatter convergence (3 cycles total; the final cycle was clean):

```text
cycle 1:
  Black: reformatted pgdb.py
  isort: modified pgdb.py and focused test
cycle 2:
  Black: PASS
  isort: PASS
cycle 3 (stability):
  Black: PASS
  isort: PASS
```

Semantic equivalence against the recovered implementation was proven
by import-set multiset comparison and `ast.dump(include_attributes=False)`
multiset comparison of every non-import top-level statement for all
three files. The only differences are whitespace, parenthesization,
line-wrapping, and import ordering/grouping — exactly the kind of
changes Black and isort are designed to perform.

```text
SEMANTIC_EQUIVALENCE=PASS
```

## Exact PostgreSQL-qualified hook-stable hashes

These are the bytes that passed PostgreSQL qualification on the
dedicated PG17 cluster. They are also the bytes that the actual
pre-commit Black and isort hooks leave unchanged, and the bytes that
are bound to the committed implementation/test paths.

```text
guardian/core/pgdb.py
9ef26df76342197dc1d58a45a66756e6a0e177ec4ffced7fae4a4bf2002bf7e9

guardian/services/account_export.py
c85fd95fbfe39d584607d37c400bde4ed9bb623b14758d90f0e22f9b3014a137

tests/services/test_account_export_unified_memory.py
eb0d33344e5eaf6f628c3c8cbca7fd13b9b58d5462bcf969285576a11185f460
```

## Export posture

- `account-export.v4` is internal/non-public.
- ordinary/default `account-export.v3` preserved.
- no public HTTP v4 selector.
- production v4 restore is not implemented.
- unsupported v4 restore remains fail-closed.

Exact v4 UMS/supporting families:

```text
persona_subjects
persona_subject_bindings
memory_records
memory_persona_links
memory_provenance
```

Other v4 implementation characteristics:

- deterministic serialization;
- manifest entity-count and integrity coverage;
- pre-ZIP account/referential closure validation;
- account-filtered PostgreSQL reads.

## PostgreSQL proof authority

Post-format qualification used the dedicated PostgreSQL 17 cluster
through its local Unix socket under trust authentication. This is
NOT TCP/SCRAM. No password was required, requested, or recorded.

```text
cluster:               /Users/resonant_jones/.codexify-test-postgres/ums04b-pg17
PostgreSQL:            17.6 Homebrew
port:                  55432
socket directory:      /tmp
socket:                /tmp/.s.PGSQL.55432
transport:             dedicated local Unix socket under trust authentication

current_user:          codexify_test_runner
current_database:      postgres

role:
  rolcanlogin  = true   (LOGIN)
  rolsuper     = false  (NOSUPERUSER)
  rolcreatedb  = true   (CREATEDB)

disposable CREATE DATABASE / DROP DATABASE probe: PASS
```

The explicit test authority URL (the URI form, not conninfo, because
the existing `temporary_postgres` fixture does `urlparse(...)` and
would silently corrupt conninfo strings):

```text
postgresql://codexify_test_runner@/postgres?host=/tmp&port=55432
```

## Runtime proof

Both pytest invocations ran on the exact hook-stable bytes above.
No skips, no failures.

```text
isolated account-isolation seam:
  test:
    tests/services/test_account_export_unified_memory.py::test_postgres_v4_reader_enforces_account_isolation
  1 passed
  0 skipped
  0 failed

complete UMS-04B focused module:
  tests/services/test_account_export_unified_memory.py
  21 passed
  0 skipped
  0 failed
```

Pre-test SHA-256 values and post-test SHA-256 values both equal
the three frozen qualified hashes above. Test execution did not
mutate the proof-bearing files.

## Final closeout proof

All rerun in this final closeout against the exact qualified bytes.

| Gate | Result |
| --- | --- |
| account-export regression gate (`tests/routes/test_account_export.py`, `tests/services/test_account_export_extension_registry.py`, `tests/services/test_account_export_extension_proposals.py`, `tests/services/test_account_export_persona_profiles.py`, `tests/services/test_account_export_extension_bindings.py`) | `31 passed, 2 skipped, 0 failed` |
| account-restore regression gate (`tests/routes/test_account_restore.py`) | `11 passed, 0 failed` |
| `py_compile` on the three qualified files | PASS |
| Alembic topology (`backend/alembic.ini heads`) | exactly one head `f6b0d3e8c5a2` |
| Pre-commit Black stability on the three qualified files | PASS (no modification) |
| Pre-commit isort stability on the three qualified files | PASS (no modification) |
| Implementation-scope inspection | bounded to internal v4 selection, default v3 preservation, five canonical/supporting families, account-filtered reads, deterministic serialization, manifest counts/integrity, pre-ZIP ownership/referential closure, v4 fail-closed posture, and focused tests. No restore implementation, no migration change, no authority change |
| `scripts/validate_docs.py` | PASS |
| Staged cached diff check (`git diff --cached --check`) | PASS |
| Staged pre-commit preflight (six staged paths, `SKIP=mypy`) | PASS; proof-bearing files unchanged |
| Staged implementation/test SHA-256 = PostgreSQL-qualified SHA-256 | PASS |
| Committed implementation/test SHA-256 from HEAD | equal to PostgreSQL-qualified SHA-256 |
| UMS-04B-PG proof ancestry (`git merge-base --is-ancestor 8a0dc98384e844ec44f87088ba381289553bfa28 HEAD`) | PASS |

## Documentation surface updated

```text
docs/Campaign/unified-memory-store/README.md
docs/architecture/00-current-state.md
docs/architecture/proofs/runtime/2026-09-12-ums04b-canonical-memory-export-serialization-proof.md   (this file)
```

No normative architecture contract was modified. The governing
ADR-084, the Account Export + Restore Contract, the Unified Memory
Store Contract, and the Runtime Protocol Token Contract remain
unchanged. The abandoned `2026-09-11` provisional proof receipt was
neutralized during recovery and is not part of committed truth.

## Exclusions

The proof deliberately excluded:

- Private Preview database — not targeted;
- Docker `db:5432` — not used as qualification authority;
- SQLite, mocks, static SQL inspection, skipped PostgreSQL evidence — not substitutes;
- `tests/pi/fixtures/fake_pi_package/package.json` — unrelated existing dirt; remained untouched and unstaged;
- `guardian/watchdog/contracts.py` mypy baseline defect — unrelated; remained untouched;
- v4 restore — not implemented in this slice;
- broader Beta/release qualification — not widened by this slice;
- credential rotation — separate operator cleanup, not in this slice;
- TCP/SCRAM transport — not used for the post-format proof.

## Campaign transition

```text
UMS-04:                                 OPEN
UMS-04A:                                CLOSED
UMS-04B-PG:                             CLOSED
UMS-04B CANONICAL MEMORY EXPORT SERIALIZATION: CLOSED
UMS-04C CANONICAL MEMORY RESTORE RECONSTRUCTION: AUTHORIZED TO START
UMS-04D:                                NOT AUTHORIZED
UMS-05+:                                NOT AUTHORIZED
```

UMS-04 itself closes only after UMS-04D proves full export →
clean restore → second-restore semantic round-trip fidelity and
idempotent replay.

## Deferred work

The next atomic Campaign slice is:

```text
UMS-04C — Canonical Memory Restore Reconstruction
```

After UMS-04C:

```text
UMS-04D — Full Export → Clean Restore → Second-Restore Qualification
```

A separate operator cleanup remains outside this slice:

```text
rotate the dedicated PostgreSQL test-role credential that was exposed in
earlier transient test output
```

And a separate development-tooling debt (parked, not blocking this
slice):

```text
.venv Black/isort versions differ from the commit-authoritative
pre-commit-pinned Black/isort versions. Align the toolchain or pin
the local formatter versions before any future task that derives
qualified bytes outside the pre-commit chain.
```
