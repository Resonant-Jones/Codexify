# Guardian Coding Claim Schema — PR Integration Qualification

- **Date:** 2026-10-29
- **Disposition:** **GO** for operator PR review
- **Release posture:** HOLD (unchanged)

This receipt qualifies the **pull-request candidate** that integrates the proven
Guardian coding-worker claim and heartbeat schema into current remote main. It
is PR-specific qualification evidence. The integration receipt it builds on is
preserved unchanged and remains the authoritative record of the isolated
integration:

- `2026-10-28-guardian-coding-claim-schema-integration-proof.md`

**Scope is persistence only.** Nothing here qualifies coding-worker execution,
liveness, retry, recovery, takeover, or any supported runtime.

## 1. References

| | |
|---|---|
| Remote base (`origin/main` as evaluated) | `577848cd9afb7b7ad100a2d4751caf39a9c90430` |
| Original integration commit | `6725dca91468e1c0bec4bbc40fc0a1641aff36ad` |
| Source integration branch | `integrate/guardian-coding-claim-schema-20261028` |
| PR branch | `integrate/guardian-coding-claim-schema-pr-20261028` |

### The pinned remote base advanced twice during this task

The task pinned `origin/main` at `766ddf2075a1e277f0c780792290736a9cc13198`.
During the work `origin/main` advanced twice, and each advance was checked
rather than assumed:

| Advance | New base | Nature | Overlap with validated paths |
|---|---|---|---|
| 1st | `c37309e03ab05294320a81aeb08dc5f66627697d` | 1 documentation file (`2026-10-28-read-state-main-head-merge-proof.md`) | none |
| 2nd | `577848cd9afb7b7ad100a2d4751caf39a9c90430` | 3 documentation files (ADR-105, the ADR index, one knowledge-graph node) | none |

Both were **forward advances, not history rewrites**: the pinned
`766ddf20…` is an ancestor of `577848cd…`. Neither advance touched a
migration, the ORM, a test, or any of the six authorized integration paths.

The candidate was re-pinned onto the newest remote main so that the pull
request's diff is computed against a current base and shows exactly the eight
authorized paths. The first candidate (based on `c37309e03…`) was never pushed
and had no upstream; it was discarded and rebuilt rather than left stale.

Local main's previously unpublished commits (`f4111901…`) are published
upstream, so nothing that was at risk of being lost remains at risk. The
requirement to preserve them independently of this PR is satisfied by their
publication rather than by any action taken here.

No branch was reset, rebased, or overwritten; local main was not modified.

## 2. Merged file list

The candidate was built with a history-preserving merge, not a cherry-pick:

```
git merge --no-commit --no-ff integrate/guardian-coding-claim-schema-20261028
-> Automatic merge went well; stopped before committing as requested
```

Verified at that point:

- `HEAD` remained `577848cd…`
- `MERGE_HEAD` was `6725dca91…`
- **Zero unresolved conflicts**
- Exactly the six original integration paths staged, and nothing else

The six files are **byte-identical** to the isolated integration commit
`6725dca91…`:

```
docs/architecture/proofs/runtime/2026-10-28-guardian-coding-claim-schema-integration-proof.md
guardian/db/migrations/versions/c8e42a91d307_merge_guardian_coding_claim_and_main_heads.py
guardian/db/migrations/versions/d86f2a4b1c90_coding_run_claim_heartbeat.py
guardian/db/migrations/versions/e42c7d0b9135_coding_run_worker_ownership.py
guardian/db/models.py
tests/migration/test_guardian_coding_claim_schema_merge.py
```

**No independent feature-branch worker changes were imported** — no
`guardian/workers`, `guardian/agents`, route, provider, or credential file
appears in the merge. **No local-main-only documentation commits were
imported.** The only `models.py` delta is the `AgentRun` ownership and
heartbeat declaration.

## 3. Read-state regression-contract correction

`tests/migration/test_read_state_main_head_merge.py` asserted that
`3a91d7c4e8b2` **is** the head of the whole graph. That was true while
`3a91d7c4e8b2` was the last mergepoint, and it became false the moment the
Guardian Coding branch was correctly joined above it. The assertion was
correcting the graph's shape, not the read-state merge's behaviour.

Before correction, the file failed 5 of its 6 cases on the merged tree. The
correction changes **only** the historical-head assumptions:

**Graph assertion** — now establishes that the graph has exactly one head,
that `3a91d7c4e8b2` belongs to that head's ancestry, that it still joins its
two original parents, and that neither parent was rewritten. It uses
`ScriptDirectory` lineage traversal and does **not** hardcode `c8e42a91d307`
as the permanent expected head:

```python
heads = script.get_heads()
assert len(heads) == 1, f"expected exactly one head, got {heads}"
lineage = {revision.revision
           for revision in script.walk_revisions(head=heads[0])}
assert MERGE_REVISION in lineage
```

The test function was renamed to
`test_merge_revision_is_in_the_single_head_ancestry_and_parents_both_branches`
because its former name asserted an ownership of the global head that is no
longer true and should not appear to remain true.

**Historical migration exercises** — the three `command.upgrade(config, "head")`
calls now target `MERGE_REVISION` (`3a91d7c4e8b2`), because their purpose is to
establish *that historical revision's* specific schema and downgrade behaviour,
not the current global head.

**Retained unchanged:**

- the explicit assertion that the historical upgrade reaches `MERGE_REVISION`
  (`assert _current_heads(engine) == {MERGE_REVISION}`)
- the downgrade target (`command.downgrade(config, UNIFIED_MAIN_REVISION)`) and
  its two-parent head assertion
- every database behaviour assertion: Saved Widget preservation, automatic-memory
  consent preservation, direct-message read cursors, account and participant
  authority, and the historical downgrade / re-upgrade round trip
- the graph-only no-DDL proof for the historical merge file

The historical migration files themselves were not changed. The current
combined head remains the responsibility of
`test_guardian_coding_claim_schema_merge.py`.

Net diff: **22 insertions, 5 deletions** in that one file.

## 4. Combined Alembic graph

```
$ python -m alembic -c backend/alembic.ini heads
c8e42a91d307 (head)
```

- **Exactly one head.**
- **131 reachable revisions**, no duplicate revision identifiers, **no missing
  parents**.
- All of `7f2c9e1a4b63`, `3a91d7c4e8b2`, `b3c8d1e5f7a2`, `a6b9d2e4f701`,
  `c59e4d1a28f0`, `f0d7c4b2a198`, `e42c7d0b9135`, `d86f2a4b1c90` and
  `c8e42a91d307` are reachable from that head.
- The new mergepoint declares
  `down_revision = ('3a91d7c4e8b2', 'd86f2a4b1c90')` and its
  `upgrade()`/`downgrade()` bodies are empty — **zero schema operations**, no
  duplicated DDL.
- The two Guardian Coding migrations are unchanged from `6725dca91…`.
- The Saved Widget, consent, read-cursor and read-state-merge migrations are
  **unchanged** from the remote base.

## 5. PostgreSQL isolation

- **Instance:** host-native **PostgreSQL 16.2** — not a container
- **data_directory:** `/Volumes/Dev_SSD/Codexify-main/.scratch/pgdata_pg16`,
  verified beneath the approved scratch root *before* any database was created
- **`listen_addresses`:** `127.0.0.1` — loopback only
- **Proof role:** `postgres`, superuser
- **Proof lock `127.0.0.1:59177`:** free before the run
- **Import origins:** `guardian`, `guardian.core.saved_widget_store` and
  `guardian.db.models` all resolved inside the PR candidate worktree
- **Application / production / Private Preview database:** never targeted
- **Docker:** not used, not restarted, no volumes modified

## 6. Test totals

```
python -m pytest -o addopts="" -v -rs \
  tests/migration/test_read_state_main_head_merge.py \
  tests/migration/test_guardian_coding_claim_schema_merge.py \
  tests/migration/test_direct_message_read_cursor_migration.py \
  tests/db/test_saved_widget_storage_migration.py \
  tests/db/test_automatic_memory_consent_migration.py
```

```
34 passed, 53 warnings in 70.16s (0:01:10)
```

| File | Passed |
|---|---|
| `test_read_state_main_head_merge.py` | 6 |
| `test_guardian_coding_claim_schema_merge.py` | 11 |
| `test_direct_message_read_cursor_migration.py` | 1 |
| `test_saved_widget_storage_migration.py` | 9 |
| `test_automatic_memory_consent_migration.py` | 7 |

- **Passed: 34 · Failed: 0 · Errors: 0 · Skipped: 0**

Zero database skips is measured, not assumed: no `SKIPPED` line and no
`N skipped` summary appeared in the run.

**Identified inherited failures:** none within the five required files. The
known historical canonical-head assertions live in other files
(`test_alembic_revision_uniqueness.py`,
`test_agent_extension_schema_consistency.py`,
`test_d6_compatibility_bridge.py`); they expect the historical revision
`2e865c4a9b10` as the graph head and were left unchanged by this task, as
required.

## 7. Upgrade-path revalidation

Three disposable databases on the PR candidate, each read back afterwards:

| Starting point | Result |
|---|---|
| `3a91d7c4e8b2` (mainline head) | **PASS** — `alembic_version = c8e42a91d307` |
| `d86f2a4b1c90` (coding-worker head) | **PASS** — `alembic_version = c8e42a91d307` |
| `f0d7c4b2a198` (historical shared parent) | **PASS** — `alembic_version = c8e42a91d307` |

Read back on the migrated database:

- `agent_runs.coding_worker_instance_id`, `.coding_worker_claim_id`,
  `.coding_worker_last_heartbeat_at` — present
- `agent_runs_coding_worker_ownership_check` — present
- `agent_runs_coding_worker_heartbeat_ownership_check` — present
- `uq_agent_runs_coding_worker_claim_id` — present
- `saved_widgets`, `saved_widget_revisions` — present
- `user_settings.automatic_memory_suggestions` — present
- `direct_message_read_cursors` — present

Ownership pairing, claim uniqueness, heartbeat-requires-ownership and nullable
historical ownership are proven behaviourally in
`test_guardian_coding_claim_schema_merge.py`, where each refusal is asserted
against the **named** constraint rather than merely against an
`IntegrityError`.

## 8. Database cleanup

- Disposable path databases dropped: **3 of 3**
- Disposable test databases: dropped by their fixture teardown
- Residue matching `codexify_coding_claim*`, `codexify_read_merge*`,
  `codexify_saved_widget*`, `codexify_consent*` or `mergehead_*`: **0**
- Databases belonging to other Codexify sessions on the shared scratch cluster
  were left untouched

## 9. Invariant checks

| Invariant | Result |
|---|---|
| `AgentRun` remains the canonical execution-state authority | Held — PostgreSQL remains the authority; the change is additive on the existing table |
| Worker claim identity is not account identity | Held — plain nullable `String(64)`, no foreign key, no account/principal/credential semantics |
| Heartbeat evidence never grants retry, takeover, or recovery authority | Held — nullable timestamp with a check that only requires an owner to exist |
| Historical ownership-unknown records remain valid | Held — all three columns nullable; proven by the focused test's historical-row case |
| Migration history is never rewritten | Held — every pre-existing revision byte-identical; one new empty mergepoint added |
| Saved Widget, consent, and read-cursor authorities unchanged | Held — original migrations byte-identical and read back present after upgrade |
| The historical merge test verifies historical behaviour, not permanent head ownership | Held — corrected to ancestry traversal; the historical revision is never assumed to be the global head |
| Schema proof does not imply coding-agent execution readiness | Held — no execution claim is made anywhere in this receipt |

## 10. Unrun validation and worker-runtime limitations

**Not run here:** a full repository-wide `pytest -v`. The inherited baseline
for this tree shape is recorded on `main` in
`2026-10-28-read-state-main-head-merge-proof.md` (244 failed, 9041 passed,
114 skipped, 35 xfailed, 11 xpassed, 37 errors; 279 FAILED/ERROR node ids
failing on both trees). Re-running it here would add wall-clock noise rather
than signal, since that work records that concurrent suites on one machine
produce artefacts. **Full backend qualification is not claimed.**

**Worker-runtime limitations.** This PR qualifies **persistence only**. It
proves nothing about:

- durable acceptance writing the ownership record atomically with the
  `queued -> running` transition
- claim-scoped heartbeat renewal by the recorded owner
- restart recovery or reconciliation of runs whose worker disappeared
- automatic retry, and whether a heartbeat gap should ever trigger one
- preventive isolation and the operator quarantine route
- terminal fencing against a stale owner
- a fully authorized coding dispatch from Guardian Chat: provider and
  credential binding, account identity, repository selection, permissions, and
  worker recovery
- qualification on the current supported deployment — the Docker engine on
  this host is still unavailable (the engine socket accepts connections and
  then returns zero bytes), so there is **no supported-Compose qualification
  and no browser qualification** here

## 11. ADR impact

**No new ADR is required.** The implementation preserves the existing accepted
ownership, execution-evidence, and migration contracts and is aligned with
Accepted ADR-020, ADR-069, ADR-081, ADR-094 and ADR-104. The read-state
correction weakens no contract: it replaces an assertion that a historical
revision permanently owns the global head with an assertion that it remains
inside the single head's ancestry — which is the contract that was always
intended. No authority change was discovered.
`00-current-state.md` was not modified.

## 12. Disposition

**GO** for operator PR review.

Every mandatory gate passed: the candidate is based on the verified remote
main; the six original integration files are byte-identical to `6725dca91…`;
the historical read-state test keeps its original behavioural coverage and now
verifies ancestry instead of permanent head ownership; all five required test
files pass with zero failures, zero errors and zero skips; all three upgrade
paths reach `c8e42a91d307`; the combined graph has exactly one head with no
duplicate or missing revisions; disposable databases are removed with zero
residue; and a durable PR qualification receipt accompanies the change.

The pull request was opened for review and **not merged**. No branch protection
was bypassed, local main was not modified, and nothing was released.

**Release posture remains HOLD.**
