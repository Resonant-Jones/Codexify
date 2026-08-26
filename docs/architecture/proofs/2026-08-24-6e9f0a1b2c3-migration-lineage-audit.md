# `6e9f0a1b2c3` Migration Lineage Audit

Audit date: 2026-08-24

## Result

**LINEAGE IDENTIFIED**

`6e9f0a1b2c3` is a legitimate deployed GitHub Watchdog migration from a
reachable but unmerged local feature lineage. Its exact body is recoverable,
and the qualifying Postgres schema matches its material effects. The live
stamp is truthful. No repair was performed by this audit.

## Audit metadata

| Item | Result |
| --- | --- |
| Worktree | `/private/tmp/codexify-google-drive-knowledge` |
| Branch | `codex/implement-google-drive-knowledge-connection` |
| Pre-task HEAD | `096d2e0a0fd6ef64f476c88f0cecc639e7a38fe6` |
| Audit-base gate | passed: blocker commit is an ancestor of `HEAD` |
| Database identity | qualifying local Compose Postgres service `db` |
| Live `alembic_version` rows | exactly `6e9f0a1b2c3` |
| Alembic script location | `guardian/db/migrations` |
| Migration directory | `guardian/db/migrations/versions` |
| Current base / head | `984a47e3bc2c` / `d2e3f4a5b6c7` |
| Current graph revisions | 88 |

The current graph has one head. Its complete branch-point inventory is:

```text
384dde1f793c, 62127ee9a537, 9f3d2b1a7c4e, a1b2c3d4e5f6,
a7c9d1e2f3b4, c1a2b3c4d5e6, c6b2fdd401a9, c7a253a50757,
e3f2a1b4c5d6, e5f6a7b8c9d0, e9a4c1b8d2f7, f2564d429cda,
f2b3c4d5e6f8, f9a1b2c3d4e5
```

Its complete merge-point inventory is:

```text
7a6b5c4d3e2f, 83c2f0bb0dfa, 8f3c1a7d2e6b, a236f7192e15,
b3c4d5e6f7a8, b6a7c8d9e0f1, b7c1d9e0f2a3, c7a253a50757,
d0e1f2a3b4c6, d4b7f1a9c3e2, d4e5f6a7b8c9, d9f1a2b3c4e5,
e3f2a1b4c5d6, e4f5a6b7c8d9, e9a4c1b8d2f7, f8ab1c2d3e4f
```

## Current-checkout and reachable-history search

The current-checkout search found `6e9f0a1b2c3` only in the prior blocker
proof. There is no matching current migration, Guardian implementation, or
backend implementation source.

Reachable-history `git log --all -S` and `-G` searches both identify commit
`c0cef2be3c6c9c72883e490274d7d78cb6c73a51`. Full path history contains one
change event: the historical file addition in that commit. Reflog inspection
identifies the Watchdog feature lineage; no tag or remote-tracking branch
contains it. An unreachable-commit content search found no extra occurrence.

## Historical revision identity

| Item | Value |
| --- | --- |
| Filename | `6e9f0a1b2c3_add_github_watchdog_review_dispatches.py` |
| Path | `guardian/db/migrations/versions/6e9f0a1b2c3_add_github_watchdog_review_dispatches.py` |
| Revision / parent | `6e9f0a1b2c3` / `5d8e9f0a1b2c` |
| `branch_labels` / `depends_on` | `None` / `None` |
| Introducing commit | `c0cef2be3c6c9c72883e490274d7d78cb6c73a51` — `Dispatch GitHub Watchdog reviews` |
| Blob SHA | `041cf25e22fbf8696eb21c82be6fe58f1dcba5ef` |
| Last reachable commit carrying same blob | `c9ba45643dbb3bb8ff4f726841288f56c5a72ae4` — `Prove tester user authentication` |

The exact recoverable historical chain is:

```text
1c0a2b3c4d5e
  -> 2a6b7c8d9e0f delivery receipts  (1827f45ea69b392af09bfde9a798068bc23edaf3)
  -> 3b7c8d9e0f1a review attempts   (ad674e7826360fe8cc055badcc117f86a3831cf3)
  -> 4c7d8e9f0a1b input snapshots   (9c5f22f48379a6c87af9a4d8ae24e9976aa05af8)
  -> 5d8e9f0a1b2c review results    (1666cde8b35b1918f4378ab3518f6bdb4dcfe0ba)
  -> 6e9f0a1b2c3 review dispatches (041cf25e22fbf8696eb21c82be6fe58f1dcba5ef)
```

## Historical migration effects

The recovered `6e` body uses only Alembic and SQLAlchemy imports. `upgrade()`
creates `github_watchdog_review_dispatches` with sixteen bounded columns,
three named CHECK constraints, three named `RESTRICT` foreign keys, a primary
key, a unique constraint, and
`ix_github_watchdog_review_dispatches_state`. `downgrade()` drops that index
and table.

The predecessors create delivery receipts, review attempts, input snapshots,
and review results. `5d8e9f0a1b2c` also replaces the attempts-state CHECK
constraint. No operation touches the current Notion table namespace.

## Lost-reachability event

There is no deletion, revision reuse, or body rewrite event. The five-node
chain was added on the local feature lineage rooted at common commit
`e7c7fd140731fafecdcce94525d2e1a77641a0b5`. It remains reachable through
`codex/define-github-watchdog-control-plane` and descendant
`codex/diagnose-tester-fresh-chroma-failure`, but neither the qualifying
checkout nor `origin/main` contains it.

The continuity break is the absence of a merge from that deployed feature
lineage into canonical history, not a later deletion commit.

## Historical artifact evidence

Before the prior reconciliation task rebuilt the tagged runtime image, the
local migrator reported `6e9f0a1b2c3` as its head. The rebuilt current image
is `sha256:ee3f3fbecbdc20ace36b00b1ce239266a000c303fe797da13e19d0cb469c3d6a`
and reports `d2e3f4a5b6c7`.

No separately identifiable old image digest remains locally tagged or
available for extraction, and no packaged migration bundle was found under
`backend/` or `guardian/`. Git blob identity and physical schema are the
authoritative identity evidence.

## Live physical schema evidence

Read-only metadata confirms all five historical tables: delivery receipts,
review attempts, input snapshots, review results, and review dispatches. The
dispatch table has the exact recovered sixteen columns, types/lengths,
nullability, defaults, three named CHECK constraints, three named `RESTRICT`
foreign keys, primary key, unique constraint, and state index. Its three
referenced parent tables exist.

The predecessor attempts-state CHECK has the post-`5d` values
`blocked_policy`, `blocked_runtime_policy`, `completed`, `failed`, `prepared`,
`running`, and `superseded`. The current sibling
`notion_connection_credentials` table is absent. No application-row contents
were read or emitted.

## Schema versus stamp

**DATABASE_STAMP_TRUTHFUL**

The exact terminal `6e` table contract and predecessor chain effects exist
physically. The live database is at the end of the historical Watchdog fork
and is missing the independent current Notion sibling migration.

## Migration loadability/dependencies

The exact `6e` blob executed in an isolated module namespace against the
current source environment without calling `upgrade()` or touching a database.
It loaded successfully. Its imports (`alembic`, `sqlalchemy`, and typing) are
available; no runtime/provider module is missing.

## Root-cause classification

**C. Revision belonged to an unmerged but deployed branch.**

## Exact graph relationship

```text
historical deployed branch:
1c0a2b3c4d5e -> 2a6b7c8d9e0f -> 3b7c8d9e0f1a -> 4c7d8e9f0a1b
-> 5d8e9f0a1b2c -> 6e9f0a1b2c3

current canonical branch:
1c0a2b3c4d5e -> d2e3f4a5b6c7
```

Current history is missing the five historical nodes and their metadata merge
with `d2`. The historical and current effects use distinct Watchdog and Notion
namespaces; no conflicting table or constraint name was found.

## Repair recommendation

**Repair Class B — Restore historical node plus metadata compatibility merge.**

A separately authorized repair task should restore the five listed historical
files byte-for-byte and add one metadata-only merge with
`down_revision = ('6e9f0a1b2c3', 'd2e3f4a5b6c7')`. It must add no semantic DDL
and must not synthesize a replacement `6e` body.

Before any live migration, that task must prove clean, historical-fork, and
current-sibling disposable databases converge to one head; prove preservation
on a backup-derived copy; then use only the canonical migrator in a separately
authorized live migration window.

## Data-preservation posture

The existing backup remains present, nonempty, and unchanged by this audit:

```text
/tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql
307135 bytes
sha256 595906e8af288d810bef7cf5719f8b0017c3f6b5b987b21b0b3fa7aae0e75e61
```

This audit makes no transition-preservation claim. A future repair must retain
this backup, take a fresh backup, and prove preservation of users, projects,
threads, messages, documents, Connections/OAuth state, and other canonical
Postgres records on a disposable backup-derived copy before touching the
qualifying database.

## Manual Stamp Safety

**MANUAL STAMP AUTHORIZED: NO**

The stamp is truthful but its full parent lineage is missing from source.
Stamping would skip the independent Notion migration and discard the deployed
compatibility contract.

## Google Drive qualification impact

Google Drive remains blocked at Connections storage readiness. OAuth remains
unattempted, and no Google-provider semantic failure has been established. No
Google OAuth, provider API, connection mutation, or Google Command Bus action
occurred in this audit.

## Validation and scope

| Check | Result |
| --- | --- |
| current Alembic graph commands | passed; one head `d2e3f4a5b6c7` |
| current-source and history search | passed; historical identity recovered |
| historical module load | passed |
| read-only schema inspection | passed; stamp truthful |
| focused migration tests | 14 passed, 1 known stale-head failure |
| full `tests/migration` | 122 passed, 29 skipped, 3 failed |

The full-suite failures are two known stale expected-head assertions
(`9d4c2a7e1b6f` versus actual `d2e3f4a5b6c7`) and one separate OpenAI import
idempotence failure. No test or source was changed by this audit; the latter
was not diagnosed or attributed here and does not change the recovered
identity or schema evidence.

ADR impact: none. This forensic audit follows ADR-031 and the existing
migration-safety doctrine without changing any ADR, runtime semantic,
current-state claim, or release truth.
