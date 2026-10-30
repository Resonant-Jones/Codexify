# Guardian Coding Worker Claim & Heartbeat Schema — Integration Proof

- **Date:** 2026-10-28
- **Disposition:** **GO** for operator integration review
- **Release posture:** HOLD (unchanged)

This receipt qualifies **schema only**: the durable coding-worker ownership and
claim-scoped heartbeat columns on `agent_runs`, carried from the Guardian
delegation feature branch into the latest mainline, joined by one explicit
Alembic mergepoint.

It does **not** qualify worker execution, liveness, retry, recovery, takeover,
or any supported runtime. Those remain separate, dependent slices.

## 1. Evaluated identities

| | |
|---|---|
| Main at start of work | `4791f219d1b872a7d55384767f5c8ba2df5f3060` |
| Feature source branch | `feature/guardian-delegation-acceptance-axis` |
| Feature source tip | `7b4b0bab44bf2fd3894eb310d8c2ef48d406325f` |
| Integration branch | `integrate/guardian-coding-claim-schema-20261028` |

Both refs were verified with `git rev-parse` before any work began and matched
their expected values exactly. The feature branch and its worktree were not
modified, reset, or rebased.

During the work `main` advanced to `bf57a0fd289e2ef770e43cbbd60b0fea463e79ad`
(three further read-state documentation commits). `4791f219d…` remains an
ancestor of that tip, so the evaluated base is still valid and nothing was
rewritten. Those three commits touch no migration, no ORM, and none of the
files this integration changes.

Promotion of this candidate will therefore be a **merge, not a fast-forward**.

## 2. Exact model changes

`guardian/db/models.py`, class `AgentRun` only. Three columns were added after
`worktree_path`:

```python
coding_worker_instance_id: Mapped[str | None] = mapped_column(String(64))
coding_worker_claim_id: Mapped[str | None] = mapped_column(String(64))
coding_worker_last_heartbeat_at: Mapped[datetime | None] = mapped_column(
    TIMESTAMP(timezone=True)
)
```

and three constraints to `AgentRun.__table_args__`:

```python
CheckConstraint(
    "(coding_worker_instance_id IS NULL AND coding_worker_claim_id IS NULL) OR "
    "(coding_worker_instance_id IS NOT NULL AND "
    "coding_worker_claim_id IS NOT NULL)",
    name="agent_runs_coding_worker_ownership_check",
),
CheckConstraint(
    "coding_worker_last_heartbeat_at IS NULL OR "
    "(coding_worker_instance_id IS NOT NULL AND "
    "coding_worker_claim_id IS NOT NULL)",
    name="agent_runs_coding_worker_heartbeat_ownership_check",
),
UniqueConstraint(
    "coding_worker_claim_id",
    name="uq_agent_runs_coding_worker_claim_id",
),
```

The feature branch's `guardian/db/models.py` is **older** than mainline: it
lacks mainline's `DirectMessageReadCursor`, the automatic-collection consent
columns on `UserSettings`, and newer memory-revision documentation. Its file
was therefore **not** copied. Only the three fields and three constraints above
were carried across.

Verified declaration surface:

- `agent_runs` columns: mainline's 16 baseline columns **plus exactly these
  three**, and nothing else.
- `agent_runs` constraints: mainline's three baseline constraints **plus
  exactly these three**, and nothing else.
- All three new columns are nullable, so historical ownership-unknown rows stay
  valid.
- None of the three is a foreign key, so none can become an account,
  principal, or credential authority.

The fields remain subordinate **execution evidence**. They are not account
identities, credential authorities, leases, expiry decisions, or worker-takeover
permissions, and no model-controlled action gains execution permission.

## 3. Original migration identities

Both feature migrations were carried across **byte-identical**; they were not
reparented, renamed, squashed, or regenerated.

| File | Git blob | sha256 |
|---|---|---|
| `e42c7d0b9135_coding_run_worker_ownership.py` | `403cf5663d80ab68c2a51961575ff56748f7d0ad` | `8b5415399ea57194638aa0c287535098bbdfe05bdf9e223a801889f0552694a5` |
| `d86f2a4b1c90_coding_run_claim_heartbeat.py` | `d8cf1e4341d40a24eebed8140cf64ee2026e8add` | `e2bdc837e37b90c405072e3cb9d0891d45e7669b7fb2d7713b4ec53c68ee67e6` |

Both blob ids were verified against
`feature/guardian-delegation-acceptance-axis`. Parentage is unchanged:

```
f0d7c4b2a198  ->  e42c7d0b9135  ->  d86f2a4b1c90
```

`e42c7d0b9135` adds the two nullable ownership columns, the paired ownership
check, and the claim-id unique constraint. `d86f2a4b1c90` adds the nullable
heartbeat column and the heartbeat-requires-ownership check. Neither backfills
historical rows, alters the run-status vocabulary, or touches credential or
account data.

## 4. The mergepoint

- **Path:** `guardian/db/migrations/versions/c8e42a91d307_merge_guardian_coding_claim_and_main_heads.py`
- **Revision:** `c8e42a91d307`
- **down_revision:** `("3a91d7c4e8b2", "d86f2a4b1c90")`
- **upgrade / downgrade bodies:** empty

Generated with Alembic's dedicated merge operation (`alembic.command.merge`),
not `revision --merge`. `backend/alembic.ini` was **not** modified: the
`file_template` override was applied to the in-memory `Config` object so the
authorized filename was produced exactly.

The revision id `c8e42a91d307` was confirmed unused before generation. The
mergepoint contains no schema operation of any kind — it is graph-only and
duplicates nothing from either parent.

## 5. Resulting Alembic head

```
$ python -m alembic -c backend/alembic.ini heads
c8e42a91d307 (head)
```

- **Exactly one head.** Head count: 1.
- Migration files: 131 (mainline's 128, plus the two feature migrations and the
  mergepoint).
- Lineage: 131 revisions, **no duplicate revision identifiers**, no missing
  parent.
- Convergence:
  `3a91d7c4e8b2, d86f2a4b1c90 -> c8e42a91d307 (head) (mergepoint)`.
- All of `3a91d7c4e8b2` (previous mainline head), `d86f2a4b1c90` (feature head),
  `e42c7d0b9135`, `f0d7c4b2a198` (shared parent), `7f2c9e1a4b63` (Saved Widget /
  consent mergepoint), `b3c8d1e5f7a2` (read cursor), `a6b9d2e4f701`, and
  `c59e4d1a28f0` remain reachable from the single head.

## 6. PostgreSQL isolation

- **Instance:** host-native **PostgreSQL 16.2** — not a container
- **data_directory:** `/Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16`,
  verified to sit beneath the approved scratch root *before* any database was
  created; the prover refuses to run otherwise
- **`listen_addresses`:** `127.0.0.1` — loopback only
- **Proof role:** `postgres`, superuser
- **Disposable databases:** uniquely named per path
  (`codexify_coding_claim_<label>_<hex>`), each dropped after use
- **Application / production / Private Preview database:** never targeted
- **Docker:** not used, not restarted, no volumes modified

## 7. Three upgrade paths

Each path used its own disposable database, upgraded to the combined head, and
read `alembic_version` back:

| Path | Starting point | Result |
|---|---|---|
| A | `3a91d7c4e8b2` (existing main head) | **PASS** — `alembic_version = c8e42a91d307` |
| B | `d86f2a4b1c90` (coding-worker feature head) | **PASS** — `alembic_version = c8e42a91d307` |
| C | `f0d7c4b2a198` (historical shared parent) | **PASS** — `alembic_version = c8e42a91d307` |

All three disposable databases were dropped afterwards (3 of 3).

## 8. Constraint and schema readback

On a migrated database:

| Object | Result |
|---|---|
| `agent_runs.coding_worker_instance_id` | present |
| `agent_runs.coding_worker_claim_id` | present |
| `agent_runs.coding_worker_last_heartbeat_at` | present |
| `agent_runs_coding_worker_ownership_check` | present |
| `agent_runs_coding_worker_heartbeat_ownership_check` | present |
| `uq_agent_runs_coding_worker_claim_id` | present |
| `saved_widgets` table | present |
| `saved_widget_revisions` table | present |
| `user_settings.automatic_memory_suggestions` | present |
| `direct_message_read_cursors` table | present |

Behavioural enforcement, proven against the live database:

- **Ownership is paired.** Inserting only `coding_worker_instance_id`, or only
  `coding_worker_claim_id`, is rejected by
  `agent_runs_coding_worker_ownership_check`. Both present is accepted.
- **One claim, one acceptance.** A second row with the same non-null
  `coding_worker_claim_id` is rejected by `uq_agent_runs_coding_worker_claim_id`.
  NULL claim ids stay distinct.
- **A heartbeat requires an owner.** A heartbeat without ownership is rejected
  by `agent_runs_coding_worker_heartbeat_ownership_check`. With an owner
  present, the same heartbeat is accepted.
- **Historical rows stay valid.** Rows with all three fields NULL insert and
  read back successfully.

Each refusal was asserted against the **named** constraint, not merely against
an `IntegrityError`, so a rejection by some other constraint cannot make these
checks pass.

## 9. Test totals

### Focused contract

```
python -m pytest -o addopts="" -v -rs \
  tests/migration/test_guardian_coding_claim_schema_merge.py
```

```
11 passed, 9 warnings in 45.39s
```

- **Passed: 11 · Failed: 0 · Errors: 0 · Skipped: 0**

Zero database skips is measured, not assumed: no `SKIPPED` line and no
`N skipped` summary appeared in the run. The file covers the single head, both
branch ancestries, the historical identities of both original migrations, the
preservation of mainline migration history, the new ORM columns, the three
constraint behaviours, historical-row validity, and the absence of new retry,
recovery, or account authority. It does not duplicate the feature branch's
worker-execution contract suites.

### Narrow existing migration and ORM tests, against a same-base control

The same set was run on the candidate and on a detached control worktree at the
identical base commit `4791f219d…`:

```
tests/migration/test_governed_schema_equivalence.py
tests/migration/test_agent_extension_schema_consistency.py
tests/migration/test_alembic_psycopg3_driver_normalization.py
tests/routes/test_agent_orchestration_request_user.py
tests/core/test_supported_profile_quarantine.py
```

| Tree | Result |
|---|---|
| Candidate | 1 failed, 110 passed |
| Same-base control (`4791f219d`) | 1 failed, 110 passed |

The failure sets are identical: one case,
`tests/migration/test_agent_extension_schema_consistency.py::test_agent_extension_schema_chain_merges_and_tables_exist`,
which asserts `set(script.get_heads()) == {CANONICAL_HEAD_REVISION}` where
`CANONICAL_HEAD_REVISION` is the historical `2e865c4a9b10`. It fails on the
candidate with `assert {'c8e42a91d307'} == {'2e865c4a9b10'}` and fails
identically on the same-base control.

This is an **inherited** failure, not a regression: it is the historical
canonical-head assertion class, already tracked as a separate bounded cleanup.
It was deliberately **not** changed here. `agent_runs` is not one of the six
governed relations, so the governed-schema-equivalence surface is unaffected.

### Graph-sensitive migration tests, against a same-base control

The three migration tests that assert a canonical head — the class this
integration most directly affects — were run on the candidate and on a
detached control worktree at the identical base commit `4791f219d…`:

```
tests/migration/test_alembic_revision_uniqueness.py
tests/migration/test_agent_extension_schema_consistency.py
tests/migration/test_d6_compatibility_bridge.py
```

| Tree | Result |
|---|---|
| Candidate | 3 failed, 12 passed |
| Same-base control (`4791f219d`) | 3 failed, 12 passed |

The failure sets are identical — the same three cases, all of which assert the
historical canonical revision `2e865c4a9b10` as the head:

- `test_alembic_revision_uniqueness.py::test_alembic_revision_ids_are_unique_and_hosted_room_lineage_is_preserved`
- `test_agent_extension_schema_consistency.py::test_agent_extension_schema_chain_merges_and_tables_exist`
- `test_d6_compatibility_bridge.py::test_final_graph_has_exactly_one_head`

All three fail on the same-base control exactly as they fail on the candidate.
They are **inherited**, and were deliberately **not** changed: the task
specification requires that historical migration-head assertions not be
silently altered.

### Broader backend gate

A full backend `pytest -v` run was **not** completed here. The machine was
carrying a load average above 25 from concurrent sibling sessions, and a
background run of the whole `tests/migration/` directory was lost mid-flight
before it could finish; that partial run is **not** characterised as a result.

The inherited baseline for this tree is already recorded on `main` in
`2026-10-28-read-state-main-head-merge-proof.md`, which ran the identical
invocation to completion against a same-tree baseline:

| Tree | Result |
|---|---|
| Baseline `cd47fd826` | 283 failed, 8419 passed, 114 skipped, 35 xfailed, 11 xpassed, 587 errors (0:46:18) |
| Single-head candidate `889b07af2` | 243 failed, 9015 passed, 114 skipped, 35 xfailed, 11 xpassed, 37 errors (1:16:47) |
| This branch's tree | 244 failed, 9041 passed, 114 skipped, 35 xfailed, 11 xpassed, 37 errors (1:15:15) |

with 279 FAILED/ERROR node ids failing on both trees and only 2 failing on that
branch alone. Those runs also record that executing two suites concurrently on
the same machine produces wall-clock artefacts, so a fresh concurrent run here
would add noise rather than signal. That measurement is attributed to the
read-state work, on the same tree shape, and is reported as the inherited
baseline rather than claimed as a run performed by this task.

**Full backend qualification is therefore not claimed.**

## 10. Database cleanup

- Disposable path databases dropped: 3 of 3
- Disposable focused-test databases: dropped by the fixture teardown
- Residue matching `codexify_coding_claim*`, `mergehead_*`,
  `codexify_saved_widget*`, or `codexify_consent*`: **0**
- Databases belonging to other Codexify sessions sharing the same scratch
  cluster were left untouched

## 11. Unchanged surrounding schema families

The integration is additive and graph-only outside `agent_runs`. Verified
present and unchanged after the merge: the Saved Widget identity and revision
tables with their constraints, the automatic-collection consent columns and
their check constraint on `user_settings`, and the direct-message read-cursor
table. No mainline migration revision was rewritten, and no account, consent,
or Saved Widget authority was duplicated.

## 12. Remaining worker execution and recovery gaps

This slice proves the **persistence** of ownership and heartbeat evidence. It
proves nothing about behaviour. Still open and unproven:

- **Durable acceptance writing the ownership record atomically** with the
  `queued -> running` transition.
- **Claim-scoped heartbeat renewal**, issued by the recorded owner and
  conditional on the database's current owner and claim.
- **Restart recovery / reconciliation** of runs whose worker disappeared.
- **Automatic retry**, and the question of whether a heartbeat gap should ever
  trigger one.
- **Preventive isolation** and the operator quarantine route.
- **Terminal fencing** against a stale owner.
- **A fully authorized coding dispatch experience from Guardian Chat**:
  provider and credential binding, account identity, repository selection,
  permissions, and worker recovery remain open.
- **Qualification on the current supported deployment.** The Docker engine is
  still unavailable on this host (the engine socket accepts connections and
  then returns zero bytes), so every database result here comes from the native
  scratch cluster. There is no supported-Compose qualification and no browser
  qualification.

## 13. ADR impact

**No new ADR is required.** The implementation preserves the existing accepted
ownership, execution-evidence, and migration contracts, and is aligned with
Accepted ADR-020 (Guardian-mediated coding agent execution contract), ADR-069
(Codexify Beta runtime support boundary), ADR-081 (project ownership
authority), ADR-094 (account-scoped execution credential authority), and
ADR-104 (agent run cancellation intent and worker observation).

No authority change was discovered: the new fields are plain nullable
non-foreign-key columns whose constraints enforce pairing and uniqueness only.
They confer no account, credential, execution, retry, or recovery authority.
`00-current-state.md` was not modified during candidate preparation.

## 14. Disposition

**GO** for operator integration review.

Every mandatory gate passed: both refs verified and the base still valid, the
integration isolated from `main`, the feature branch untouched, only the
authorized `AgentRun` semantics integrated, both feature migrations
byte-identical, exactly one empty merge revision added, exactly one Alembic
head, all three upgrade paths reaching that head, both ownership constraints
and the heartbeat constraint proven against a live database, historical rows
still valid, the surrounding mainline schema families intact, focused tests
green with zero database skips, and disposable databases cleaned up.

The only failing cases in the narrow and graph-sensitive suites are the three
inherited historical canonical-head assertions, reproduced identically on the
same-base control at `4791f219d…`, and they were not changed.

This commit exists only on `integrate/guardian-coding-claim-schema-20261028`.
It was **not** pushed, merged to `main`, or otherwise published, and `main` was
not modified. Future mainline promotion must follow the repository's pull
request requirement rather than relying on an administrative protection bypass.

**Release posture remains HOLD.**
