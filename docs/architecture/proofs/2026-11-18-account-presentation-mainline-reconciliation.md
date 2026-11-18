# Account presentation and main migration reconciliation

Source/proof candidate,2026-11-18; no live operation or release qualification.
Current main base is145e8cbf11c11566e4fbf16944df3d50cb0c06ce. The existing
profile-owner receipt records a separate Preview module atbf36fa242 with schema
f3a9c7d2b8e1; this task does not refresh that live observation.

## Preserved graph

Main retains the published chain ab71d5ce9604 → c7e4a1b9d602 (accepted-account
custody) → c13f0713a901 (GitHub Knowledge credentials) → d8a90bf32107 (OAuth
custody) → e723ba9046cd (inactive budget ledger). Preview retains ab71d5ce9604 →
d2e7a9b4c1f6 (nullable explicit greeting) → f3a9c7d2b8e1 (account presentation).
New a3f8c2d6e901 joins e723 and f3 with empty upgrade/downgrade bodies. The
combined graph has145 revisions and one head. No published revision, parent,
DDL or migration environment is edited. The branches touch separate fields/
tables; no conflicting DDL was found. Full upgrades, rather than ledger stamps,
apply the missing sibling on either installed branch.

A local SHA256 manifest checks every142 published main migration unchanged;
a committed six-file fixture freezes both post-ab71 branch bodies. The existing
main accepted_account_id model column and immutability trigger are retained.
No voice PR migration, private Bio field, broader settings, Lens or tour change
is included. ADR058/064/079/088/092's existing boundaries remain governing;
this source compatibility join needs no new authority or activation decision.

## Synthetic PostgreSQL proof

The focused migration run passed14 tests. The three end-to-end cases create
separate empty databases in one newly initialized task-owned PostgreSQL16
cluster, bound only to its private Unix socket. They actually execute the full
published history to empty/main e723/Preview f3 and then the new head, without
stamping or bypassing historical DDL.

- Empty install reaches one a3f head with no inferred greeting or presentation row.
- Main's synthetic profiles/display labels and GitHub credential ciphertext stay
  unchanged; new greeting values remain NULL. Existing accepted-account custody
  survives, and its PostgreSQL trigger refuses a different account.
- Preview's chosen greeting, distinct shared/workspace preferences, valid PNG
  wallpaper bytes and original profile/project/thread rows survive. Older
  accepted requests gain NULL custody, never inferred current-owner authority;
  the trigger refuses later promotion into authenticated custody.
- Repeating upgrade head is a no-op for greeting/preferences/custody data.

Raw values are synthetic. Row preservation is checked with SHA256 over canonical
JSON row projections, excluding only the newly added NULL column where needed.
The private wallpaper field participates in that comparison. No runtime backup,
private credentials, signed-in browser, provider model, import job or live DB is
used. OS network policy denies network access except Unix sockets; the Python
socket/DNS audit records zero unexpected network attempts. Disposable databases
are dropped and the owned server stopped.

Early local proof attempts caught test-only DSN interpolation and incomplete
required fixture fields (accent, node FK and integer Project identity). These
were corrected without editing production constraints or migration history.
Their logs are retained as superseded attempts, not labeled green baseline.

## Additional local validation

The ported identity/authentication plus relevant migration aggregate passed754
 tests with6 optional cases skipped. Architecture contracts passed590 tests.
The reviewed Web lifecycle/wallpaper/Guardian welcome suite passed40 tests and
its production build passed under OS network denial. Current-main's frozen
lockfile was installed in the isolated candidate with lifecycle scripts disabled;
one cached package was missing, not a proposed dependency change.

Full app TypeScript checking remains red on inherited diagnostics:128 on exact
main versus120 on this candidate with the same lockfile. No new per-file/error-
code category or new presentation-module diagnostic appeared. This is not a
clean full-app typecheck or CI/release qualification. Separate environment/cache
and fixture failures were resolved and retained in local logs; none were hidden
by disabling tests or changing production migration/authority semantics.

## Scope and remaining gates

This ports only already deployed explicit greeting/presentation behavior and Web
wiring. Blank/cleared greeting is neutral with no identifier/display/browser or
memory fallback. Canonical account scope, stored-session checks, exact native
admission and no-write reads remain intact. The conservative seven-field
appearance contract is unchanged. Private Bio/Guardian approval work and the
separate Scout distribution handoff are outside this candidate.

Qualification projection is refreshed only to describe source impact; previous
status, tested receipts and freshness remain unchanged. Local source/migration
proof is not a reconciled Preview deployment or live authenticated owner receipt.

Root must reconcile any newly merged main head and open migration owner before
publication/merge ordering. A later authorized live rollout must establish exact
current source/image/effective config and work drain, take and restore a verified
backup, rehearse the actual installed lineage, preserve account/preferences/
wallpaper/import/custody data, and retain data-safe rollback. It must not blindly
apply another branch's image, rewrite an installed parent or stamp away history.
No live operation, credential refresh or provider activation is authorized here.
