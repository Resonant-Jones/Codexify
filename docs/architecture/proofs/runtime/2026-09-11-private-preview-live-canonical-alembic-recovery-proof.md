# Private Preview live canonical Alembic recovery proof

Date: 2026-09-11. Lane: architecture-impact. Mode: `EXECUTE`.

## Result and authority

Private Preview PostgreSQL and the complete canonical migration/bootstrap path
are recovered at repository Alembic head `7e5a5fccf253`. Application runtime
recovery remains unproven. This documentation closeout uses retained receipts;
it performs no database, migrator, seed, restore, application, Chroma, or provider
operation and does not rerun the accepted regression gate.

```text
LIVE_DATABASE_RECOVERY_RESULT=PASS
DATABASE_MIGRATION_BOOTSTRAP_RECOVERY_PROVEN=true
APPLICATION_RUNTIME_RECOVERY_PROVEN=false
ADR_IMPACT=ALIGNED_WITH_EXISTING_ADRS
ALEMBIC_PHASE=PASS
POST_ALEMBIC_SEED_PHASE=PASS
COMPLETE_MIGRATOR_CONTRACT=PASS
```

ADR-005 governs account boundaries; ADR-069 separates evidence from support and
release posture; ADR-076 governs account-scoped built-in roles; ADR-081 makes
`projects.user_id` the sole Project ownership authority. ADR-082 governs Persona
Profile binding authority, ADR-084 governs account-owned memory and stable
Persona subjects, and ADR-085/ADR-086 govern the preceding bounded legacy
retirements. No ADR or runtime semantics change in this task. Receipts provide
evidence, not new execution or release authority.

## Repository and preceding proof chain

- Repository: `/Volumes/Dev_SSD/Codexify-main`, local `main` on `VaultNode.local`.
- Live recovery start and qualified seed-repair commit:
  `433e4999f74ce4b34a97bfa1bf711b8dd737e43d`
  (`Make default Project seeding account scoped`).
- Documentation closeout start/test-repair commit:
  `0cdf7618cabd1cc07f976ff188fc19a6db322e6d`.
- Fetched `origin/main`: `cb551de1866715ef421026203ffe2a87cec8aaca`;
  closeout start was ahead 15, behind 4. No merge, rebase, pull, or push.
- Unrelated staged deletions: `docs/DEV_LOG/2026-09-10/Dev Log - 2026-09-10.md`
  and `docs/DEV_LOG/2026-09-11/Dev Log - 2026-09-11.md`.
- Their retained binary-patch SHA-256:
  `4e96d8c7155e327f03f15d311ddfbf03c32dc2d86129e184b4f7a6bb29b7560e`.

The preceding seams remain bounded by their original proofs:

1. [Project-1 partition and retirement](./2026-09-11-private-preview-project-1-partition-retirement-proof.md).
2. [Legacy Persona Profile retirement](./2026-09-11-private-preview-legacy-persona-profile-retirement-proof.md).
3. [Account-scoped seed repair and restored-copy qualification](./2026-09-11-account-scoped-default-project-seed-repair-proof.md).

This receipt continues those results without reopening their authority or
rewriting their historical stop boundaries.

## Retained evidence inventory

Live recovery artifacts remain outside the repository under:

`/Volumes/Dev_SSD/Codexify-preservation/live-canonical-alembic-20260911T194943Z`

The closeout read and compared:

- `recovery-stop-receipt.json` and `artifact-identity.json`;
- `first-migrator.log`, `first-migrator-result.json`, and
  `first-migrator-validation.json`;
- `second-migrator.log` and `second-migrator-result.json`;
- `second-run-idempotence.json` and `existing-project-preservation.json`;
- `pre.json`, `post-first.json`, `post-second.json`, `post-stop-final.json`,
  and `post-stop-final-controls.json`;
- `pre-migration-metadata.json`, `post-migration-metadata.json`, and the two
  retained dump files (read-only hash, size, mode, and format verification).

Final green test evidence is retained at
`/tmp/cfy-head-assertion-proof-20260911/test-results.json` and its
`tests-1.log` through `tests-9.log`. Exact commands and results are transcribed
below so the repository receipt retains the validation summary independently
of the temporary log location. The original interrupted test results and log
paths are also recorded in `recovery-stop-receipt.json`.

## Qualified canonical artifact

Image ID:
`sha256:a45b2fe1959f87574780512eece31274369a34315bc99e97c959befbce71ed12`.

The retained source/image qualification established byte equivalence with the
seed-repair source and a sole repository/image Alembic head `7e5a5fccf253`.

| Source/image file | SHA-256 |
| --- | --- |
| `backend/scripts/seed_defaults.py` | `edc5f9fc831b5295a159a10eb5315a5e319bcda28582cacc13dfaca065bd5a6b` |
| `backend/scripts/docker/run_migrator.py` | `225d6cd2fc71cb5577a71db9b23ee48f67edd073f99390de133553803f8e8db6` |

Both live runs used that image, zero mounts, and the exact canonical entrypoint
`/app/backend/scripts/docker/run_migrator.py`. Its required ordering is:

```text
python -m alembic --raiseerr -c /app/backend/alembic.ini upgrade heads
  -> python /app/backend/scripts/seed_defaults.py
  -> [Migrator] Done
```

Both subprocesses must succeed. Reaching the Alembic revision alone is not the
complete recovery contract.

## Immediate pre/post preservation artifacts

Both files are PostgreSQL custom-format archives (`PGDMP`), retained mode
`0400`. Retained metadata records `pg_dump`, `pg_restore --list`, and full
archive decoding each exiting zero. This closeout independently read their
bytes to verify hashes, sizes, signatures, and read-only modes; it performed no
restore, database connection, or new backup operation.

| Boundary | Exact path | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Immediate pre-live migration | `/Volumes/Dev_SSD/Codexify-preservation/live-canonical-alembic-20260911T194943Z/pre-migration.dump` | 3338690 | `b855d2a006965583c48bbaf72a99a32438fbf47f5f144791b79accff5576348e` |
| Post-live migration | `/Volumes/Dev_SSD/Codexify-preservation/live-canonical-alembic-20260911T194943Z/post-migration.dump` | 3361105 | `bef8bcaa92ec2386efcd2106151ba9793e51d18da09769e22505a2326c09e7f9` |

## First complete live migrator

The live source began at `d4e0f2a5b7c9`, after the two preceding retirements.
Container `codexify-live-qualified-migrator-first-20260911t194943z` ran from
`2026-09-11T19:51:24.100565+00:00` to
`2026-09-11T19:51:32.088346+00:00`.

- Complete migrator/container exit: 0; seed exit: 0.
- Final live revision: `7e5a5fccf253`.
- Seed summary: accounts 5; existing Generals 3; promotions 0; creations 2.
- Log SHA-256:
  `831210f33fbca5e6b5b34f1dc3094f34c47057d8e8e756eaf894f1c7c78373e5`.
- First post-migrator readback: `post-first.json`.
- Ordered bounded Project snapshot SHA-256:
  `7adc4ebd1a3263caeb9807d4ec9d89fd69c6a4cc92eb5adc38245cc56f813dca`.

The initial log parser recorded `seed_complete=false` because the image redacts
the generic completion line. `first-migrator-validation.json` corrects that
interpretation: the retained account-scoped seed summary, `check=True` seed
subprocess, `[Migrator] Done`, exit zero, and database readback prove successful
seed completion. This was a verification-parser issue, not a seed failure.

## Project and account preservation

Post-seed authority remains `projects.user_id`, with structural General identity
scoped by `user_id + system_role`, not global display name. Existing General
IDs 6, 7, 8 were retained; new account-owned General IDs 9, 10 were created.
There are five canonical non-`local` accounts, five structural Generals, and
eight total Projects. Ownerless Projects, `local` Generals, invalid owners,
missing Generals, duplicate Generals, and post-migration thread/Project owner
mismatches are all zero.

Canonical account and replacement-Project ownership were preserved. The normal
migration performed one disclosed, rehearsed legacy reconciliation: Project 3
changed from `local` to its single proven canonical owner. The original
zero-owner-change conflict was surfaced before execution; the user directed
continuation with that bounded reconciliation. Therefore total existing-owner
changes are **one**, expected legacy changes **one**, canonical-owner changes
**zero**, and unexpected owner changes **zero**. This must not be reported as
zero total owner changes.

Project 2 changed only its description by unwrapping the matching legacy owner
envelope while preserving the exact human description (SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
Project 3 changed only `user_id`; Projects 4, 6, 7, 8 and all other existing
Project fields were preserved. Cross-account Project reassignments were zero.

Project 1 remains absent. The eight repaired thread mappings remain exactly:

| Thread ID | Replacement Project ID |
| --- | --- |
| 1 | 8 |
| 3 | 6 |
| 4 | 6 |
| 5 | 6 |
| 69 | 8 |
| 70 | 7 |
| 71 | 6 |
| 72 | 6 |

Each repaired thread owner equals its replacement Project owner. All 20 affected
message identities, thread associations, and full rows remain unchanged.

| Preserved surface | Count | Unchanged full-row SHA-256 |
| --- | ---: | --- |
| All threads | 72 | `876fe5a8af0cef657e8eac25122346ed0dfcb310cea41d294235a4180cd4dc9f` |
| All messages | 805 | `5f168ad630b026ee0702f5cbd4ec39fd21115800ac8133b132faa3a30d8e9dca` |
| Repaired threads | 8 | `be4ab5affdb49361d2109587493a3ad64804860a50cca731b2e9badcc4ec5c03` |
| Affected messages | 20 | `d201acd44888dfd48905ce6a9b477eee764332bac39bda4ef745198121d8c0bd` |
| Users | 6, including legacy compatibility identity | `032908c8232b6a0e5dd5d3bcf271cf9eaaad59f83ed1574cb941a51e7725399b` |

Profiles `profile-1`, `profile-2`, `profile-3` remain absent. Profile, revision,
and binding counts remain 0/0/0; no retired-profile Persona Subject or subject
binding was recreated. The post-migration FK census checks 17 Project foreign
keys, including the newly introduced memory constraints, with zero orphans.
No thread or message mutation was needed for traversal or seeding.

## Second complete live migrator and idempotence

Container `codexify-live-qualified-migrator-second-20260911t194943z` ran from
`2026-09-11T19:53:50.027198+00:00` to
`2026-09-11T19:53:59.224861+00:00`.

- Complete migrator/container exit: 0; seed exit: 0.
- Alembic remained at `7e5a5fccf253`; the seed phase ran again successfully.
- Seed summary: accounts 5; existing Generals 5; promotions 0; creations 0.
- Log SHA-256:
  `115b51c656fafb667391a8282614a4c2bbc9c66b1c1e97e0c731990305cad3f3`.
- All 119 table manifests are identical between `post-first.json` and
  `post-second.json`; this closeout independently compared those retained files.
- Bounded Project snapshot, all Project row hashes, and Project sequence are
  identical. Snapshot SHA-256 remains
  `7adc4ebd1a3263caeb9807d4ec9d89fd69c6a4cc92eb5adc38245cc56f813dca`.
- Second-run Project inserts/deletes/reassignments/owner changes: 0/0/0/0.

```text
LIVE_CANONICAL_MIGRATOR_FIRST_EXIT=0
LIVE_CANONICAL_MIGRATOR_SECOND_EXIT=0
LIVE_CANONICAL_MIGRATOR_IDEMPOTENCE=PASS
LIVE_SEED_DEFAULTS_ACCOUNT_SCOPED_IDEMPOTENCE=PASS
SECOND_RUN_TABLE_MANIFEST_COUNT=119
SECOND_RUN_TABLE_MANIFESTS_IDENTICAL=true
```

## Interrupted regression gate and separate repair

The database/bootstrap proof was complete before the original regression stop.
The original gate recorded 57 passes and one failure, then stopped before the
remaining Project suites. The failing canonical-memory test upgraded a
**disposable PostgreSQL database** to `head` but expected the older UMS-03D
revision `f6b0d3e8c5a2`; the actual result was correctly `7e5a5fccf253`.
This outdated expectation indicated neither live corruption nor migration
failure. The original receipt remains a historical STOP receipt.

```text
RECOVERY_CLOSEOUT_INITIAL_REGRESSION_GATE=STOP
INITIAL_STOP_REASON=canonical_memory_test_has_stale_head_assertion
REGRESSION_REPAIR_RESULT=PASS
TEST_REPAIR_COMMIT_SHA=0cdf7618cabd1cc07f976ff188fc19a6db322e6d
```

The separate repair changes only
`tests/migration/test_canonical_memory_persistence_migration.py` (six insertions,
one deletion). It retains upgrade to `head`, derives heads through
`ScriptDirectory.from_config(config).get_heads()`, requires exactly one, and
compares the final ledger against that head. Historical revision assertions and
schema/constraint checks remain intact. This is validation maintenance with no
architectural authority or runtime semantic change.

No live recovery replay occurred after the test correction. The repair used
isolated disposable PostgreSQL; this documentation task accepts its green
results at the exact required start commit and reruns no regression tests.

Every command below used prefix `.venv/bin/python -m pytest -v`:

| Retained log | Test path(s) after prefix | Passed |
| --- | --- | ---: |
| `tests-1.log` | `tests/migration/test_canonical_memory_persistence_migration.py::test_fresh_replay_creates_canonical_tables_with_frozen_constraints` | 1 |
| `tests-2.log` | `tests/migration/test_canonical_memory_persistence_migration.py` | 17 |
| `tests-3.log` | `tests/test_seed_defaults_account_scope.py` | 10 |
| `tests-4.log` | `tests/migration/test_project_ownership_runtime_convergence.py` | 5 |
| `tests-5.log` | `tests/migration/test_project_ownership_local_reconciliation.py` | 22 |
| `tests-6.log` | `tests/migration/test_persona_subject_identity_migration.py` | 4 |
| `tests-7.log` | `tests/migration/test_canonical_memory_persistence_migration.py` | 17 |
| `tests-8.log` | `tests/scripts/test_seed_defaults.py tests/core/test_account_projects.py tests/core/test_project_lifecycle.py tests/core/test_project_ownership.py tests/routes/test_project_lifecycle.py` | 31 |
| `tests-9.log` | `tests/migration/test_project_name_scope_migration.py` | 2 |

Logs 3–9 are the complete recovery gate: **91 distinct tests passed**, zero
failures or skips. Logs 1–2 add the separately required targeted test and full
canonical-memory suite (1 + 17), yielding **109 successful required test
executions**, not 109 distinct tests. No live database writes occurred during
the test repair.

## Quiescence and deferred proof boundary

The retained final controls show application writers quiesced: backend/workers
were Created or stopped; frontend and origin were stopped. PostgreSQL, Redis,
and Neo4j were running. The Private Preview launch agent was absent. The
historical desired-up marker was present; this receipt does not claim it was
removed or that desired state was disabled. Final readback recorded zero other
database sessions. These are retained observations, not new runtime probes.

This closeout starts no application, worker, health probe, authenticated route,
provider request, or Chroma operation. Database migration/bootstrap recovery is
proven; backend startup, authenticated route health, worker coherence, chat
completion, Chroma runtime integration, provider runtime, and Private Preview
release readiness remain unproven.

Next separately authorized architecture-impact task: **Start and qualify
Private Preview after database recovery**. Resolve the required Chroma/deployment
prerequisites before restart, then prove backend startup, service health,
authenticated account-scoped reads, worker coherence, and minimum deployed
runtime behavior. This task stops before that qualification.

## Diagram and documentation follow-through

Reviewed all four diagrams in `runtime-diagrams-v1.md`: topology, completion
sequence, storage boundaries, and subsystem ownership. Database version and
bootstrap recovery status change no nodes, process edges, or trust boundaries.
The coarse pack explicitly excludes one-shot bootstrap services and entity-level
schema detail. `RUNTIME_TOPOLOGY_CHANGED=false`; diagram bodies remain unchanged.
Only the 2026-09-11 Diagram Review Marker is updated in diagram governance.

`00-current-state.md` now records completed Project/Persona retirement,
account-scoped seed recovery, final live revision, complete migrator idempotence,
preservation, verified post-backup, and green regression follow-through. It
explicitly separates proven database recovery from unproven application runtime
and release readiness. Existing ADRs and proofs remain unchanged.

Documentation validation for this three-file closeout:

- `git show --stat --oneline 0cdf7618cabd1cc07f976ff188fc19a6db322e6d`:
  PASS, expected one-file test correction; patch also inspected.
- `python3 scripts/validate_docs.py`: PASS.
- `.venv/bin/python scripts/validate_docs.py`: PASS.
- `python3 scripts/check_diagram_freshness.py`: PASS.
- `git diff --check` and `git diff --cached --check`: PASS.

No automated runtime tests apply to these documentation changes. Regression
results above are retained proof, not tests rerun by this closeout. Only this
proof, current state, and the governance marker belong to the task commit;
unrelated staged Dev Log deletions are preserved byte-for-byte.
