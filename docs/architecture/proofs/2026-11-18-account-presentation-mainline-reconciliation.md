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

## Publication continuation

Main was rechecked at the same145e8cbf1 base. Root explicitly selected this
profile candidate for publication before the independent draft voice PR1091;
that PR and its1b6c8d9e2f40 migration are unchanged and excluded. Any subsequent
main advance still requires a fresh overlap and migration-graph check.

The repository-wide head assertion audit confirms the GitHub credential test
expects a3f while retaining its original parent, upgrade/downgrade and schema
assertions. Historical merge tests retain their lineage and single-head proofs.
A broader PostgreSQL run exposed a pinned message-request fixture using today's
UserProfile ORM before the nullable greeting column exists. The fixture now
applies the original d2 migration's DDL, matching its existing local-node-marker
compatibility pattern, without changing its pinned revision, schema assertions
or the Alembic ledger. No production migration or service was changed by this
test correction.

The publication migration-contract rerun passed341 tests, with27 optional skips
and63 deselections (57 integration cases plus the six Docker-only cases). It
includes the full fresh/main/Preview convergence matrix and the corrected
historical consent/concurrency proof. It used a newly initialized owned Unix-only
PostgreSQL16 cluster, recorded zero unexpected network attempts and stopped the
server cleanly. No live or already-populated root database was used.

Six existing account-observability fixtures clear supplied database URLs and
start TCP/Docker, so they are not run in the Unix-only proof. The separate import
qualification integration case expects an already-migrated root database; the
broad attempt failed during schema verification before creating an import job.
It is outside this reconciliation proof and is not rerun. Superseded failed
environment runs remain in the local evidence directory; full CI and a clean
full-app TypeScript check are not claimed.

## Broad frontend CI repair,2026-11-19

Hosted Frontend Quality job135219137855 exposed25 failed tests and an asset-menu
suite import failure. Exact main19e6a3b9 was merged non-destructively into this
branch with no conflicts or migration changes. An exact-main frontend snapshot
using the same lockfile, dependency versions, Vitest configuration and broad
`pnpm run test` command passed2493 app tests (one existing skip) and84 Chrome
extension tests. Its first attempt lacked the unchanged shared corpus fixture;
that snapshot omission was supplied from main before the successful comparison.
There were no unrelated baseline frontend failures in the completed comparison.

Two narrow product repairs preserve existing presentation behavior. Account
readiness/saving now disables only account appearance controls, leaving the
interface-only Feed Layout, file colors and Advanced Appearance disclosure
usable. Bundled demo wallpaper uses a same-origin static fetch without account
credentials or redirects, followed by the existing validated account upload;
foreign origins and old-account responses remain rejected. No binary format,
preference allowlist, workspace-unique semantics or authentication scope expands.

Renderer/control fixtures now supply explicit account state rather than legacy
browser preferences. They retain material keyboard/accessibility, independent
axes, contrast, hierarchy and wallpaper-scene assertions; account wallpaper
actions assert the shared writer and absence of localStorage writes. The missing
asset-menu mock dependency is isolated at its wallpaper hook. Blank/missing names
remain neutral; the older expectation that explicitly chosen "You" is a
placeholder is superseded by the existing authored-name contract and coverage.
The real controller additionally proves credential-free static retrieval,
foreign-origin refusal and stale-account response suppression. No test exclusion,
CI script or Vitest configuration was changed.

The repaired broad frontend command passed2511 app tests (one existing skip)
and84 extension tests; lint and the unchanged production build command passed.
Local baseline and candidate used Node22 with two bounded workers and OS network
denial; hosted CI uses Node20. Profile/authentication plus real PostgreSQL proofs
passed756 tests with one unrelated integration case deselected by the existing
CI `not integration` selection. The unfiltered attempt exposed that legacy
bootstrap fixture's NULL persona-owner seed against today's non-null schema;
it is not changed here. All three convergence paths and the historical consent
proof ran, with zero unexpected network attempts and clean owned-server shutdown.
TypeScript remains at120 inherited candidate diagnostics versus128 on main;
full-app typecheck, current-head hosted CI and live qualification are not claimed
by these local results. No live Preview, migration history, voice, Bio or tour
operation was performed.

## Combined main worker fix, 2026-11-19

Main `078c685329b0283196072582453e57a05703a357` contains merged worker-image
PR1094 at `0e003a0315b3b3c676b9d017f45524e4e9ecd192`. It adds no migration.
Merge `d31491f6534a44b9a77e1bd9bb2d81f3833de5a5` retains both parents: the
published profile candidate71920 and current main078c. No remote history or
other worktree was rewritten. The only conflict was the generated qualification
registry. It was regenerated using the complete merged tree and both parents'
ancestry, then checked against the actual merge commit, rather than selecting
either published projection. The resulting reason counts are68/204, compared
with67/203 on the profile branch and64/182 on main. Qualification status,
freshness and backing receipts are unchanged; no surface is promoted.

The migration graph remains145 revisions at a3f, with both published branches'
IDs, parents and bodies preserved. All142 main migration bodies remain
hash-identical. The unchanged fresh/main/Preview PostgreSQL convergence and
profile/authentication run passed756 tests (one unrelated integration case
deselected by CI's existing selection), with zero network attempts and clean
owned-server shutdown. Separate worker/router tests passed55 with zero network
attempts. Architecture and qualification passed632; the broad frontend command
passed2511 app tests (one existing skip) plus84 Chrome extension tests. The
frontend tree is byte-identical to71920; its inherited TypeScript limitation
is unchanged and is not relabeled green.

An optional expanded run passed839 pytest cases but failed its strict network
guard. Isolation identified38 blocked DNS attempts in existing image-service
fixtures; their separate83-case run also failed that guard. No request escaped
the Python/OS network denial, no provider transport executed, and these runs
are not counted as network-free proof. The required profile/migration run and
the separate55-case worker/router run use independent zero-attempt receipts.
No unrelated image-service fixture or product behavior was changed to hide this
limitation. The task-owned main-078c evidence directory retains all results;
exact final-head hosted CI is assessed separately. No live operation, provider
call, spending/billing activation, ready transition, PR merge or deployment occurs
in this reconciliation task.
