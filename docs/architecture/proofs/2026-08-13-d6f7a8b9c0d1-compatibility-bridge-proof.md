# d6f7a8b9c0d1 compatibility-bridge proof

## Result

**NEXT_PROOF_NEEDED**

The d6 lineage repair itself is complete and correct: the historical migration
and its Python dependency were restored byte-for-byte, the metadata-only merge
was added, the final graph has exactly one head, a clean disposable database
reaches that head, and a backup-derived `d6f7a8b9c0d1` database reaches the same
head with no data loss. However, schema convergence fails: the backup-derived
`d6` database carries an `account_observability` schema that differs materially
from the clean database's `account_observability` schema. The metadata-only
merge reconciles the ThreadSpace branch but not this second divergence, so the
task's convergence acceptance criterion is not met.

## Metadata

- Task date/time: 2026-08-13 (afternoon, `-04:00`)
- Branch: `codex/repair-migrator-dependency-boot`
- Pre-task HEAD: `7496a4bfc46a0e748395b21f08b3e84dbadb27d6`
- Tested commit / worktree state: same HEAD, clean at start
- Pre-repair canonical Alembic head: `6e2b9c4a7d1f`
- Final head: `8f3c1a7d2e6b`

## Historical restoration identities

All three files were restored from historical Git commit
`fc96df36e3b33afb5d053c39086310da21084e8e`
("Add ThreadSpace node membership persistence"; rebased twin
`9a4422427814e04d434562f2862c070c19c7db11`). Byte identity was verified with
`git hash-object`.

| Path | Historical blob SHA | Restored blob SHA | Byte-identity verdict |
| --- | --- | --- | --- |
| `guardian/threadspace/__init__.py` | `21d8f08cc06fd74f52c14cee58e2d49648c0e3d6` | `21d8f08cc06fd74f52c14cee58e2d49648c0e3d6` | IDENTICAL |
| `guardian/threadspace/membership_tokens.py` | `8c332eb68dae5c558a0f47a53c48132ab2c2893a` | `8c332eb68dae5c558a0f47a53c48132ab2c2893a` | IDENTICAL |
| `guardian/db/migrations/versions/d6f7a8b9c0d1_add_threadspace_node_membership.py` | `d02f5bfa629948f5e134ef9bb9e827cf2679250b` | `d02f5bfa629948f5e134ef9bb9e827cf2679250b` | IDENTICAL |

## Historical dependency finding

The historical d6 migration has a load-time import:

```python
from guardian.threadspace.membership_tokens import (
    INVITATION_STATES,
    MEMBERSHIP_LIFECYCLE_STATES,
    NODE_MEMBERSHIP_ROLES,
    NODE_STATUSES,
)
```

`guardian/threadspace/membership_tokens.py` and its package initializer were
created on the same unmerged feature lineage and are absent from current
ancestry. Restoring the migration alone produced
`ModuleNotFoundError: No module named 'guardian.threadspace.membership_tokens'`
and broke Alembic graph loading and `tests/migration/test_alembic_revision_uniqueness.py`.
Restoring the two token files makes the migration loadable.

The token module is Enum/frozenset/validation vocabulary only. It introduces no
routes, models, workers, provider behavior, subsystem registration, or runtime
registration. Nothing in the current runtime imports `guardian.threadspace`
except the restored migration. Its restoration does NOT activate ThreadSpace as
a runtime feature.

## Graph before restoration

- Current canonical head: `6e2b9c4a7d1f` (single head).
- `d6f7a8b9c0d1` absent from the current migration graph.

## Graph after dependency restoration

Restoring the three files made Alembic load both branches:

```text
6e2b9c4a7d1f (head)   current sibling branch
d6f7a8b9c0d1 (head)   restored historical branch
```

Both share `c1a2b3c4d5e6` as the branch point, matching the audited topology.

## Final graph

Added `guardian/db/migrations/versions/8f3c1a7d2e6b_merge_d6f7a8b9c0d1_compatibility.py`
(a metadata-only merge: `upgrade()` and `downgrade()` are both `pass`).

- `revision = "8f3c1a7d2e6b"`
- `down_revision = ("d6f7a8b9c0d1", "6e2b9c4a7d1f")`
- `branch_labels = None`, `depends_on = None`
- Merge parents: `d6f7a8b9c0d1` and `6e2b9c4a7d1f`
- Final head count: exactly one — `8f3c1a7d2e6b (head) (mergepoint)`

## Static validation

- Focused bridge + uniqueness tests: `11 passed`
  (`tests/migration/test_d6_compatibility_bridge.py` = 10,
  `tests/migration/test_alembic_revision_uniqueness.py` = 1).
- Full migration suite `tests/migration`: `100 passed, 29 skipped` (DB-integration
  tests skip without `TEST_DATABASE_URL`; no failures).
- The bridge test pins the three blob SHAs, d6 metadata, token vocabulary
  rendering, merge parents, merge no-op shape, single head, and forward ancestry
  from both branches to `8f3c1a7d2e6b`.

## Clean-start proof

- Isolated Compose project: `codexify_d6_bridge_clean_proof` (fresh volumes).
- Migrator result: success; no manual intervention, no `alembic stamp`.
- Final revision: `8f3c1a7d2e6b`.
- Second `upgrade heads`: no-op (no `Running upgrade` lines).
- Schema: 101 tables, including `threadspace_nodes`,
  `threadspace_membership_invitations`, `threadspace_membership_grants`,
  `repository_bindings`, `users`, `chat_messages`, and `hosted_rooms`.

## d6 backup-derived upgrade proof

- Source preserved tester revision: `d6f7a8b9c0d1` (read via an isolated copy).
- Backup: `pg_dump --format=custom --no-owner --no-privileges` from a read-only
  copy of the preserved volume into `/tmp/codexify-d6-compatibility-proof.dump`
  (outside the worktree, mode 0600).
  - Size: 134,429,097 bytes.
  - SHA-256: `057c8c92fa7ca50217cede92a907669024b264cd175cd25d9b99c5ab95b0e847`.
- Isolated restore project: `codexify_d6_bridge_upgrade_proof` (fresh volumes).
- Clone revision before upgrade: `d6f7a8b9c0d1`.
- Migrator result: success. Exactly two migrations executed:
  `6e2b9c4a7d1f` (add `repository_bindings`) then `8f3c1a7d2e6b` (merge no-op).
  No missing-revision error, no import error, no stamp.
- Final revision: `8f3c1a7d2e6b`.
- Second `upgrade heads`: no-op.
- Historical ThreadSpace effects present in the clone before upgrade:
  `threadspace_nodes` (5 columns), `threadspace_membership_invitations` (15),
  `threadspace_membership_grants` (18), including the partial unique index
  `uq_threadspace_membership_grants_node_subject_non_revoked`.

## Schema convergence

**FAILED.**

Normalized schema signatures (schema-only `pg_dump --no-owner --no-privileges`,
SHA-256):

- Clean-start schema: `0fff8b325806da59b28d8d08a8528a1026c2d74c6a1314e40db9cac039e9b0c7`
- d6-derived schema: `0b7c1ad1123131f19e052e61f939b7965aefec7c56626962e3558a1f0cfd63dc`

The two databases have the same Alembic revision (`8f3c1a7d2e6b`) but do NOT have
equivalent schemas. The material (semantic) divergence is confined to the
`account_observability` domain (4 tables). Direct catalog comparison shows:

| Object | Clean (current lineage) | d6-derived clone (historical) |
| --- | --- | --- |
| `account_observability_guest_identities` PK | `guest_id` | `id` |
| `account_observability_invite_links` PK | `invite_id` | `id` |
| `account_observability_presence_sessions` PK | `presence_session_id` | `id` |
| `account_observability_presence_sessions.region_code` | `varchar(64)` | `varchar(32)` |
| check-constraint / FK / index names | current names | legacy names (e.g. `ck_account_observability_*`, `ix_account_observability_*_at`) |

The historical `account_observability` migration (`b2c3d4e5f6a7`) is NOT an
ancestor of the d6 feature branch (`fc96df36...`), yet the preserved database
contains an `account_observability` schema that differs from what the current
lineage produces. The two branches therefore diverge beyond the ThreadSpace
branch: the `account_observability` schema was rewritten on the current lineage
after the preserved database was migrated. The metadata-only merge reconciles
the ThreadSpace branch but not this second divergence.

A secondary, semantically-neutral difference also appears: pg_dump renders the
same `= ANY (ARRAY[...])` check constraints as `ARRAY[...]::text[]` on the clean
database versus element-cast `ARRAY[(...)::text, ...]` on the clone (166 check
constraints across ~60 tables). The allowed values are identical; this is a
stored-expression rendering difference, not a semantic difference. It is noted
here for completeness but is not the blocking conflict.

## Data preservation

Bounded pre/post row counts on the d6-derived clone (canonical tables):

| Table | Pre-upgrade | Post-upgrade |
| --- | ---: | ---: |
| `users` | 18 | 18 |
| `projects` | 3 | 3 |
| `chat_threads` | 5,061 | 5,061 |
| `chat_messages` | 112,507 | 112,507 |
| `uploaded_documents` | 0 | 0 |
| `generated_documents` | 0 | 0 |
| `threadspace_nodes` | 0 | 0 |
| `threadspace_membership_invitations` | 0 | 0 |
| `threadspace_membership_grants` | 0 | 0 |
| `hosted_rooms` | 1 | 1 |
| `hosted_room_invites` | 1 | 1 |
| `hosted_room_participants` | 3 | 3 |
| `repository_bindings` | (absent) | 0 |

No unexplained decrease, no missing canonical table, all three ThreadSpace
tables survive. Foreign-key integrity: 113 FK constraints present; bounded
orphan checks for `chat_messages.thread_id` and `chat_messages.user_id` both
return 0 orphans. No user/message content was inspected or emitted.

## Preserved tester safety

- No stamp.
- No upgrade.
- No downgrade.
- No DDL.
- No DML.
- No restart against the source database.
- No volume deletion of the preserved source.
- The preserved volume was mounted read-only (`:ro`) only for copying; all
  reads and the backup were performed against an isolated copy. Final read of
  the preserved `alembic_version` (fresh read-only copy after all operations):
  `d6f7a8b9c0d1`.

## Manual-stamp posture

Manual stamping remains prohibited and was not used at any point.

## Hosted Room impact

- Migration graph repair: proven for the ThreadSpace/d6 branch (clean-start and
  backup-derived d6 upgrades both reach `8f3c1a7d2e6b`), but schema convergence
  is NOT proven because of the `account_observability` divergence.
- The prior Hosted Room result remains BLOCKED, not failed.
- No Hosted Room live semantics were re-proven in this task.
- Mutation/startup of the preserved tester environment requires a separate
  proof task.

## Release impact

This does not widen the supported beta surface. The restored ThreadSpace token
module is a migration-loading dependency, not an activated runtime feature.

## Pre-existing migrator boot defect (psycopg2/psycopg3)

While running the disposable proofs, the canonical `run_migrator.py` failed with
`ModuleNotFoundError: No module named 'psycopg2'`: the Compose topology supplies
`DATABASE_URL` in driver-neutral `postgresql://` form, which SQLAlchemy maps to
the psycopg2 dialect, but the runtime image ships only psycopg v3 (3.3.4). This
is a pre-existing defect unrelated to the d6 repair; a separate unmerged fix
exists (`cb35d4e80`, branch `codex/alembic-psycopg3-runtime-driver-20260812`,
proof `2026-08-12-alembic-psycopg3-driver-normalization-proof.md`). For this
task's disposable proofs only, `DATABASE_URL` was overridden to the repository's
own supported `postgresql+psycopg://` scheme (the same scheme already used for
`GUARDIAN_DATABASE_URL`) via an ephemeral `/tmp` Compose override. No repository
file was changed. A side effect is that `seed_defaults.py` (whose `_is_pg()`
check does not recognize the `+psycopg` suffix) fell back to its SQLite path and
did not seed the default project — this did not affect the migration proof and
kept the d6 clone free of seed-induced mutation.

## Exact conflict (next-proof-needed)

The metadata-only merge assumption is disproven. The preserved database's
`account_observability` schema (PK columns `id`/`id`/`id`,
`region_code varchar(32)`, legacy constraint/FK/index names) diverges from the
current lineage's `account_observability` schema (PK columns
`guest_id`/`invite_id`/`presence_session_id`, `region_code varchar(64)`, current
names). Reaching schema convergence would require either rewriting the current
`account_observability` migration(s) or adding destructive compensating DDL —
both prohibited by this task and both potentially ADR-impacting (they change
accepted schema meaning and could drop/reinterpret historical data). This must
be designed and authorized as a separate architecture-impact task.

## Next task recommendation

Authorize a separate architecture-impact task to design an
`account_observability` compatibility-normalization that reconciles the
historical `account_observability` schema with the current lineage without
manual stamping or silent data loss, then re-run the full clean-start +
backup-derived d6 convergence proof. The d6/ThreadSpace restoration and the
metadata-only merge from this task are prerequisite inputs.

## Limitations

- No Room owner/guest replay in this task.
- No broader release qualification.
- No claim about other unknown historical migration branches beyond the tested
  d6 lineage and the identified `account_observability` divergence.
