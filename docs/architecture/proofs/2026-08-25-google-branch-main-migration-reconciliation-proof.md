# Google qualification branch / current-main migration reconciliation proof

> **Status:** BLOCKED — the preserved backup artifact required for Shape D is
> absent from its exact mandated path, so the checksum-bound backup-derived
> convergence proof cannot be repeated. This is a proof-artifact boundary, not
> a source-graph, disposable-migration, or live-database failure.
>
> **Scope:** branch reconciliation and disposable migration compatibility only.
> No live migration, manual stamp, DDL against the qualifying database, OAuth,
> Google API call, or Google Command Bus invocation occurred.

## Source identity and rebase

| Check | Value |
| --- | --- |
| Worktree | `/private/tmp/codexify-google-drive-main-reconcile` |
| Branch | `codex/implement-google-drive-knowledge-connection` |
| Pre-rebase HEAD | `c9f3f1eb752e207aa552becf2b24bc8ba441e54b` |
| Pre-fetch `origin/main` | `a3d7882b8dfe826bc2f7ce3407e0677e827fcc17` |
| Pre-rebase merge base | `7aae1807492313d4cf10eb7876c3ebde92408819` |
| Pre-rebase `origin/main...HEAD` left/right count | `78 / 13` (behind / ahead) |
| Post-fetch `origin/main` | `a3d7882b8dfe826bc2f7ce3407e0677e827fcc17` |
| Rebased migration-repair commit | `1afccd84550241c42a5214c7218646e3b5d07416` |
| Reconciled source head before this receipt | `1afccd84550241c42a5214c7218646e3b5d07416` |
| Post-rebase merge base | `a3d7882b8dfe826bc2f7ce3407e0677e827fcc17` |
| Final `origin/main...HEAD` left/right count before this receipt | `0 / 13` |

`git merge-base --is-ancestor origin/main HEAD` succeeded after the rebase.
The required pre-rebase repair commit was in ancestry before reconciliation.
A local safety ref, `codex/google-qualification-pre-main-reconcile-20260825`,
continues to point to the original pre-rebase head.

`git rebase origin/main` completed successfully. The bounded conflict
resolutions were:

1. Current main had allocated ADR-073 to the GitHub Watchdog decision, while
   the unmerged Connections decision had used ADR-073; the unmerged decision
   was renumbered to unused ADR-075, preserving both decisions and updating its
   local references.
2. Connections documentation was resolved to refer to ADR-075 while retaining
   current-main Watchdog and Tester routing.
3. `00-current-state.md` retained current-main release truth and the branch's
   bounded local-profile and migration-containment statements.
4. Migration tests were reconciled to the actual canonical sole head rather
   than historical intermediate heads.

No historical migration identity or migration body was rewritten. Google Drive,
Notion, profile-auth, qualification-proof, lineage-audit, and Watchdog repair
outcomes remain in the rebased branch.

## Incoming current-main graph

Before rebase, an archive of `origin/main` reported one Alembic head:

```text
6e9f0a1b2c3
```

`origin/main` contained the five restored Watchdog revisions byte-for-byte,
but did not contain `d2e3f4a5b6c7` or a descendant of it. Its incoming
migration diff from the old merge base consisted of the historical Watchdog
chain; no overlapping Connections or Watchdog DDL was found. Therefore no
post-rebase DDL collision existed.

After rebase, `alembic heads` reported exactly:

```text
9c66e490a42b (head)
```

The graph is **Case A**: `9c66e490a42b` remains the sole head. It merges
`6e9f0a1b2c3` and `d2e3f4a5b6c7`; no additional merge revision was created or
needed. `9c66e490a42b` remains metadata-only (`upgrade(): pass`,
`downgrade(): pass`).

```text
RECONCILED_HEAD=9c66e490a42b
```

## Historical migration preservation

| Revision | Before rebase blob SHA | After rebase blob SHA | Result |
| --- | --- | --- | --- |
| `2a6b7c8d9e0f` | `1827f45ea69b392af09bfde9a798068bc23edaf3` | `1827f45ea69b392af09bfde9a798068bc23edaf3` | preserved |
| `3b7c8d9e0f1a` | `ad674e7826360fe8cc055badcc117f86a3831cf3` | `ad674e7826360fe8cc055badcc117f86a3831cf3` | preserved |
| `4c7d8e9f0a1b` | `9c5f22f48379a6c87af9a4d8ae24e9976aa05af8` | `9c5f22f48379a6c87af9a4d8ae24e9976aa05af8` | preserved |
| `5d8e9f0a1b2c` | `1666cde8b35b1918f4378ab3518f6bdb4dcfe0ba` | `1666cde8b35b1918f4378ab3518f6bdb4dcfe0ba` | preserved |
| `6e9f0a1b2c3` | `041cf25e22fbf8696eb21c82be6fe58f1dcba5ef` | `041cf25e22fbf8696eb21c82be6fe58f1dcba5ef` | preserved |

## Disposable convergence

All disposable migrations used an isolated `postgres:15` container named
`codexify-main-reconcile-pg`, bound only to `127.0.0.1:55432`, with no mounted
volume and explicitly named disposable targets. No target could resolve to the
qualifying database.

| Shape | Disposable target / start revision | Result |
| --- | --- | --- |
| A: clean | `codexify_reconcile_clean_20260825` / empty | upgraded to `9c66e490a42b`; all five Watchdog tables and `notion_connection_credentials` present |
| B: historical Watchdog | `codexify_reconcile_watchdog_20260825` / `6e9f0a1b2c3` | Notion table absent at start; upgraded to `9c66e490a42b` with dispatch and Notion tables present |
| C: independent Connections sibling | `codexify_reconcile_connections_20260825` / `d2e3f4a5b6c7` | dispatch table absent at start; upgraded to `9c66e490a42b` with dispatch and Notion tables present |
| Incoming-main state | `6e9f0a1b2c3` | this is the same current-main state as Shape B; `d2e3f4a5b6c7` was additionally exercised because it is the other actual parent of the retained merge |
| D: preserved backup restore | `/tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql` | **not run**: artifact absent, so expected SHA-256 could not be verified and no substitute was used |

The required Shape D source had previously been recorded as:

```text
/tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql
sha256 595906e8af288d810bef7cf5719f8b0017c3f6b5b987b21b0b3fa7aae0e75e61
```

At this reconciliation it was absent from the mandated path, from task-local
temporary locations, and from the host-indexed search. Re-dumping or copying
the live qualifying database would not prove preservation of that exact
artifact, so it was not attempted. Consequently local-user, local-project,
authenticated-principal, and OAuth-row preservation cannot be re-proved for a
fresh backup-derived copy in this receipt.

## Regression evidence

| Surface | Result |
| --- | --- |
| `pytest -v tests/migration` | **165 passed** |
| Auth coherence, Connections catalog/routes, Google Drive, and Google Command Bus registration | **49 passed** |
| Alembic head | exactly one, `9c66e490a42b` |

The full migration suite initially surfaced hard-coded intermediate-head
expectations and round trips that tried to cross current main's intentionally
fail-closed `1c0a2b3c4d5e` downgrade. The narrowed test repair updates
canonical-head assertions to `9c66e490a42b` and keeps focused historical
round-trip tests within their own reversible target. No migration semantics
changed.

An extra broad supported-profile test invocation also reproduced two unrelated
current-main failures in `tests/core/test_supported_profile.py`: the
`v1-whooshd-deepseek-web` profile declares `qwen3.8-27b-4bit` while those
assertions still expect Gemma. This reconciliation leaves that out-of-scope
current-main mismatch unchanged; the required auth-coherence regression passed.

## Live-database containment

The qualifying Postgres container was started only for read-only SQL checks;
no migrator, backend, OAuth flow, or DDL command was run against it.

| Check | Result |
| --- | --- |
| `alembic_version` | `6e9f0a1b2c3` |
| `notion_connection_credentials` | absent |
| `oauth_connections` rows | `0` |
| Live DDL / migration | none |
| Google OAuth | not initiated |

## Outcome

**BLOCKED — the checksum-bound preserved backup required for Shape D is absent
at `/tmp/codexify-google-drive-pre-schema-reconcile-20260824.sql`; therefore
the four-shape reconciliation proof is incomplete despite a zero-behind branch,
one canonical Alembic head, and green clean/Watchdog/Connections-sibling
convergence.**

No ADR or release-truth change is made by this receipt. The live migration
window remains unauthorized. Recover the exact preserved dump (and verify its
recorded SHA-256) before rerunning Shape D and considering the separately
authorized canonical live-migrator gate.
