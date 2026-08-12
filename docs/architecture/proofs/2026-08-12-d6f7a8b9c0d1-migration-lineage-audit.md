# `d6f7a8b9c0d1` migration-lineage audit

## Result

**LINEAGE IDENTIFIED**

`d6f7a8b9c0d1` was a legitimate Alembic migration created on a locally
reachable feature lineage. That lineage never merged into the ancestry of the
current audit tip. The preserved tester database contains the migration's
physical schema effects and its `alembic_version` row is truthful. The database
is therefore **divergent** from the current migration graph, not incorrectly
stamped.

This is a forensic finding only. No repair was performed.

## Audit metadata

- Audit time: `2026-08-12T19:06:41-04:00`
- Branch: `codex/audit-atlas-room-surfaces`
- Pre-task and audited HEAD: `9f03fc4384aa421700e04643199ea511bd04973a`
  (`Record Hosted Room owner guest live proof`)
- Blocked-proof prerequisite: `9f03fc4384aa421700e04643199ea511bd04973a`
  is an ancestor of the audit tip (the tip itself)
- Tester Compose project: `codexify_tester`
- Preserved Postgres volume: `codexify_tester_pg_data`
- Preserved database revision rows: exactly one row,
  `d6f7a8b9c0d1`
- Current Alembic head set: exactly one head, `6e2b9c4a7d1f`
- ADR impact: **No ADR impact - forensic audit only**

At audit time no `codexify_tester` container was running, while the named
volume remained present. Database evidence below was collected by mounting the
preserved volume read-only, copying it to a uniquely scoped temporary Docker
volume, starting isolated Postgres against only that copy, and issuing bounded
`SELECT` and catalog queries. The temporary container and copy were removed
after inspection. The preserved volume was not started, written, reset, or
deleted.

## Governing contracts and authority

Postgres remains the canonical state owner for this evidence. Git and Alembic
source establish migration identity and graph ancestry; catalog queries against
the isolated database copy establish physical schema state. Neither source is
substituted for the other. The existing-instance upgrade proofs require exact
schema/lineage reconciliation; a manual version-table edit is not upgrade
proof. No accepted ADR was found that authorizes removal of this historical
upgrade path or reclassifies applied tester data as disposable.

## Current Alembic graph

`backend/alembic.ini` resolves its script location to:

`guardian/db/migrations`

The current directory contains 83 revisions and resolves as one connected DAG:

- Base revision: `984a47e3bc2c`
- Head: `6e2b9c4a7d1f`
- Branch points:
  `384dde1f793c`, `62127ee9a537`, `9f3d2b1a7c4e`,
  `a1b2c3d4e5f6`, `a7c9d1e2f3b4`, `c6b2fdd401a9`,
  `c7a253a50757`, `e3f2a1b4c5d6`, `e5f6a7b8c9d0`,
  `e9a4c1b8d2f7`, `f2564d429cda`, `f2b3c4d5e6f8`, and
  `f9a1b2c3d4e5`
- Merge points:
  `7a6b5c4d3e2f`, `83c2f0bb0dfa`, `a236f7192e15`,
  `b3c4d5e6f7a8`, `b6a7c8d9e0f1`, `b7c1d9e0f2a3`,
  `c7a253a50757`, `d0e1f2a3b4c6`, `d4b7f1a9c3e2`,
  `d4e5f6a7b8c9`, `d9f1a2b3c4e5`, `e3f2a1b4c5d6`,
  `e4f5a6b7c8d9`, `e9a4c1b8d2f7`, and `f8ab1c2d3e4f`

The current terminal segment relevant to this audit is:

```text
d0e1f2a3b4c6
        |
c1a2b3c4d5e6  add email login alias to users
        |
6e2b9c4a7d1f  add repository bindings (current head)
```

The current migration directory contains neither a filename nor migration
source defining `d6f7a8b9c0d1`. A current-checkout content search finds the ID
only in the prior blocked Hosted Room proof artifact, not in executable
migration source.

## Historical revision identity

- Historical path:
  `guardian/db/migrations/versions/d6f7a8b9c0d1_add_threadspace_node_membership.py`
- `revision`: `d6f7a8b9c0d1`
- Final relevant `down_revision`: `c1a2b3c4d5e6`
- `branch_labels`: `None`
- `depends_on`: `None`
- Introducing commit:
  `fc96df36e3b33afb5d053c39086310da21084e8e`
  (`Add ThreadSpace node membership persistence`)
- Introducing parent: `209d00661964a3abaf8ac08557cfe48aeb75db33`
- Rebased twin carrying the same migration identity and implementation:
  `9a4422427814e04d434562f2862c070c19c7db11`
  (`Add ThreadSpace node membership persistence`)

The upgrade creates:

1. `threadspace_nodes` (5 columns), with its primary key, node-status and
   nonblank-name checks.
2. `threadspace_membership_invitations` (15 columns), with user/node foreign
   keys, the issuer-scoped idempotency unique constraint, role/state/lifecycle
   and timestamp-order checks, and three lookup indexes.
3. `threadspace_membership_grants` (18 columns), with user/node/invitation
   foreign keys, source-invitation uniqueness, role/lifecycle/source and
   timestamp-order checks, three lookup indexes, and the partial unique index
   enforcing one non-revoked grant per node and subject.

The downgrade drops the grant indexes and table, then the invitation indexes
and table, then the node table.

### Relevant rewrite history

On a separate rebased feature lineage, commit
`e51282e8fa2c2353706f8717b3534999f6d9514f` (`Point ThreadSpace membership
migration at current revision`) changed `down_revision` from
`c1a2b3c4d5e6` to `d0e1f2a3b4c6`. Commit
`ac42f617f5f10cc691e0d39da803cc35d07c8d1f` (`Restore remote login by email
alias`) restored the email-alias migration and changed the historical
migration back to `c1a2b3c4d5e6`. The preserved schema includes the
`users.email` effect, so its physical state agrees with the final `c1 -> d6`
form.

An all-ref deletion search found no commit deleting the historical migration
path. An exhaustive `git rev-list --all` plus `git grep` search found the file
in the introducing commit, its rebased twin, and descendants on locally
reachable feature/recovery branches. No other migration source found in that
search declares `d6f7a8b9c0d1` as its `down_revision`; there is no known
descendant or merge connector after `d6`.

## Root cause classification

**C. Migration belonged to a branch never merged into current ancestry.**

Evidence:

- `fc96df36...` is not an ancestor of the audit HEAD.
- The audit HEAD is not an ancestor of `fc96df36...`.
- Their merge base is
  `c6e80ae7d95497cde72b25c977ef4c2248401fb6` (`Merge pull request #673 from
  Resonant-Jones/codex/restore-adr-055-governance`).
- The first commit on the current side after that common ancestor is
  `747e8b65769db80ff3c695843585108b52283214` (`Merge pull request #672 from
  Resonant-Jones/codex/establish-browser-campaign`).
- The first commit on the feature side is
  `43b531c606db5d1b9db6764eeed94c9772abfcb9` (`Fix local runtime preset
  settings loading`); `d6` was introduced later on that side.
- No deletion commit exists because the current line never contained the
  migration. The first current-side commit did not delete or rewrite it, and
  therefore is not a migration-breaking change in isolation.
- No migration tests/docs in current ancestry supplied a replacement path for
  databases already stamped at `d6`.

Consequently there is no exact "commit that deleted reachability." Reachability
from a `d6` database to current HEAD was never established in current ancestry.
The operational break surfaced when a database previously migrated with the
feature lineage was reused with the current checkout. This classification does
not speculate about why the feature branch was not merged.

Git history fully explains the revision's source and loss of reachability, so
the conditional old-image/bundle search was not required. This audit makes no
claim about the exact image digest that originally ran the migration.

## Preserved database schema evidence

The isolated-copy query returned exactly:

```text
alembic_version
----------------
d6f7a8b9c0d1
```

All three historical tables are present. Catalog inspection found all 38
historical columns, all 35 associated primary-key, foreign-key, unique, and
check constraints, and all 12 associated indexes (including indexes backing
the primary/unique constraints). In particular, the partial non-revoked
node/subject grant uniqueness rule is present.

Bounded adjacent-state checks found:

- `users.email` is present, matching preceding revision `c1a2b3c4d5e6`.
- Hosted Room actor/provenance columns
  `chat_messages.hosted_room_participant_id` and
  `chat_messages.sender_display_name_snapshot` are present.
- `repository_bindings` is absent, so current head `6e2b9c4a7d1f` has not been
  applied.

Bounded row counts, collected only to establish preservation risk, were:

| Relation | Rows |
| --- | ---: |
| `users` | 18 |
| `projects` | 3 |
| `chat_threads` | 5,061 |
| `chat_messages` | 112,507 |
| `uploaded_documents` | 0 |
| `hosted_rooms` | 1 |
| `hosted_room_invites` | 1 |
| `hosted_room_participants` | 3 |
| `threadspace_nodes` | 0 |
| `threadspace_membership_invitations` | 0 |
| `threadspace_membership_grants` | 0 |

No application row bodies were dumped.

## Schema-versus-stamp conclusion

1. The `d6f7a8b9c0d1` upgrade effects are present in full.
2. No migration descendant of `d6` is known. The current sibling head's
   `repository_bindings` effect is absent.
3. The database appears genuinely migrated through `d6f7a8b9c0d1`.
4. The `alembic_version` row is **truthful**.
5. The schema is **divergent** from the current graph: both known lines share
   `c1a2b3c4d5e6`, after which the preserved database took the historical `d6`
   branch and current source took the `6e2b9c4a7d1f` branch.

```text
                         d6f7a8b9c0d1  preserved DB, missing from current source
                        /
d0e1f2a3b4c6 -> c1a2b3c4d5e6
                        \
                         6e2b9c4a7d1f  current source head, not applied to DB
```

The current checkout supplies no legitimate path from `d6` to `6e2b9c4a7d1f`.
No later merge migration connected the branches, and therefore no connector
was later removed. Restoring only the old source file would make Alembic
recognize `d6`, but it would create two heads rather than a converged upgrade
line. It would not, by itself, provide a terminal revision proving that both
branches have been reconciled. The exact historical file also imports feature
module constants, so restoration requires dependency review rather than a
blind file copy.

## Repair recommendation

**Repair Class B - Add explicit compatibility bridge.**

The next separately authorized task should design and prove a compatibility
lineage that recognizes the immutable applied `d6` node, preserves its existing
schema, applies current-head effects exactly once, and converges historical and
clean current databases on one tested terminal head. That work may require
restoring historical revision metadata together with an explicit merge/bridge;
the exact implementation must be validated against both a clean database and a
backup-derived `d6` database before touching the preserved tester volume.

Repair Class A is insufficient because restoring the node alone leaves two
heads and no convergence. Repair Class C is contradicted by the physical schema
evidence. Repair Class D is not yet necessary because lineage and schema are
recoverable. Repair Class E is unnecessary because the decisive lineage and
schema facts are identified.

## Why manual stamping is not safe

**NOT SAFE.**

Changing `alembic_version` from `d6f7a8b9c0d1` to `6e2b9c4a7d1f` would erase a
truthful record of the applied historical branch while falsely asserting that
the absent `repository_bindings` migration had run. Stamping a common ancestor
would likewise discard evidence and could cause non-idempotent historical DDL
to be replayed. The schema is not merely "close" to current: it has complete
effects from one sibling branch and lacks effects from the other. Only a tested
compatibility traversal may change its version state.

## Data preservation posture

The preserved volume contains canonical tester state: 18 users, 3 projects,
5,061 threads, 112,507 messages, one Hosted Room with one invite and three
participants, plus other Postgres relations not exhaustively enumerated here.
The ThreadSpace tables are empty, but their emptiness does not authorize their
removal or a false stamp. Uploaded-document rows were zero at inspection time;
that bounded result does not substitute for whole-database preservation.

Before any repair attempt, create and verify a restorable full Postgres backup
or supported physical snapshot of the preserved database. Preserve users,
projects, threads, messages, documents, Hosted Room state, the ThreadSpace
schema, and every other canonical Postgres record. Account export alone is not
proven here to cover all of those relations. Perform compatibility proof on a
backup-derived disposable database first; only a separately authorized task
may operate on the preserved tester volume.

## Hosted Room proof impact

The Hosted Room proof remains **BLOCKED** until migration lineage is repaired
and tester startup is re-proven from current source. This audit does not
reinterpret the blocked startup as a Hosted Room semantic failure. Existing
owner/guest test evidence remains separate from the unproven live startup path,
and the Room campaign remains paused at the live-proof gate.

## Invariants preserved

- Existing tester volumes remain intact.
- No preserved database mutation occurred.
- No Alembic stamp occurred.
- No migration upgrade or downgrade occurred.
- No migration file was restored, created, or edited.
- No current migration ID was rewritten.
- No production or tester data was deleted.
- Historical upgrade compatibility is treated as a contract, not cleanup
  debris.
- The current Room campaign remains paused at the live-proof gate.
- Any repair remains evidence-driven and separately tasked.

## Validation

- `alembic -c backend/alembic.ini heads`, `branches`, and verbose history
  inspection: passed; one head, `6e2b9c4a7d1f`, and one base,
  `984a47e3bc2c`.
- Current-checkout filename/content search plus all-locally-reachable Git object
  search: passed; current migration absent and historical source/commits
  identified.
- Preserved-database bounded catalog inspection through an isolated copy:
  passed; original volume remained read-only and intact.
- `.venv/bin/pytest -v tests/test_alembic_config_contract.py
  tests/migration/test_alembic_revision_uniqueness.py`: passed, `2 passed`.
- `make docs PYTHON=.venv/bin/python`: passed; architecture-document validation
  and diagram-freshness validation both passed. Make reported the pre-existing
  duplicate-target warning for `canonical-audit-live-proof-receipt`.
- `git diff --check`: passed.
- Frontend tests: not applicable; no frontend files changed.
- Hosted Room runtime tests: not rerun; no runtime code changed and the live
  proof remains deliberately blocked.

## Exact next task

Authorize a separate **Repair Class B compatibility-bridge implementation and
proof**. Its acceptance criteria must include a verified backup first, clean
database upgrade proof, backup-derived `d6f7a8b9c0d1` traversal to one current
head without replaying applied ThreadSpace DDL, preservation checks for
canonical tester data, and only then a separately approved tester startup
proof. Do not stamp or repair the preserved database as part of this audit.
