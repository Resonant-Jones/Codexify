# Profile and OpenAI import source migration convergence

This is local source and disposable PostgreSQL evidence. It is not a live
Preview migration, Business-history import, provider call, or release qualification.

## Exact inputs and bounded resolution

- Published draft #1093: `dd32cc8ce0a1c6216783dcbce66ffce3c84f56e6`.
- Current main: `1435cfa210fe3166326c5b2d0af58ea16511ae42`, including merged
  #1097 (`d1f5e677ef65f9e303d5b943461e4e11cdd80fe1`).
- No competing profile-convergence descendant or open PR was found at refresh.
- `a3f8c2d6e901` still joins `e723ba9046cd` and `f3a9c7d2b8e1`.
  `a64c358e2241` still descends from `e723ba9046cd`.
- New no-DDL `b7e6c4a29013` joins those two published heads. The graph has
  147 revisions and one head. All 146 published migration bodies are frozen
  by SHA-256 in the migration test fixture; no revision is reparented or stamped.
- Local Git integration retains main's unrelated merged work. Only three
  conflicts required resolution: current-state prose (retain newer audit and
  distinguish dated receipts), generated qualification registry (regenerate
  against combined ancestry), and the GitHub credential historical test
  (retain main's single-lineage assertion and original schema proof).

## Authority and invariants

ADR-058/064/079/088/092 govern the existing account/session and greeting module;
this reconciliation changes no product contract. The chosen greeting remains
explicit, nullable, and separate from display name and identifiers. Account
presentation and explicit workspace-unique state are preserved.

ADR-076/081 and the OpenAI import Project routing contract retain structural
General and canonical account ownership. Explicit selected source plus exact
full group ID determines placement. Labels cannot adopt an existing Project;
different sources/accounts remain isolated, and archived/deleted mappings fail
closed. No historical conversation is reassigned or real import run.

Qualification inputs, run receipts, statuses, freshness, and release HOLD are
unchanged. The generated registry reflects combined source deltas only.

## Validation

The owned Unix-socket-only PostgreSQL rehearsal upgrades empty, historical
main `e723ba9046cd`, current main `a64c358e2241`, and historical Preview
`f3a9c7d2b8e1` stores through real Alembic operations. Synthetic rows cover
explicit greeting, display name, account/workspace preferences, wallpaper bytes,
accepted-account custody and main's existing source/Project/tombstone bindings.
Tests compare row digests before/after, verify neutral NULL rather than inferred
names/custody, exercise the real source/Group-ID resolver and immutability/owner
constraints, and repeat the final upgrade as a no-op.

Local results:

- Focused PostgreSQL/graph/custody and existing #1097 staged-worker proof:
  **27 passed**, one SQLite row-locking case skipped (its PostgreSQL variant
  passed). This includes the canonical migration smoke test.
- Migration inventory, identity/profile, import service and related historical
  contracts: **1,126 passed**, 33 optional fixture skips, 65 deselections
  (integration selection plus six existing Docker-only normalization fixtures).
  These exclusions do not replace the explicit real-upgrade/routing proof above.
- Architecture/qualification: **631 passed** before commit, with the exact-HEAD
  registry check deferred until the final local commit. The generated source
  deltas are 72 / 236 paths; evidence and release authority are unchanged.
- Full Web CI test configuration: **2,588 passed**, one skipped. Extension:
  **84 passed**. Cached dependencies match the unchanged lockfile; test caches
  belong to this candidate. No installation or downloads were required.
- TypeScript is **not green**: the candidate has 117 diagnostics versus 119 on
  exact current main with the same dependencies/configuration. File/code
  categories match; the AppShell prop diagnostic still has the same underlying
  missing `ingestionEnabled` property. Two unused-name diagnostics disappear.
  No unrelated TypeScript repair is included.
- Scoped Black, Ruff fatal checks and Git whitespace checks passed. PostgreSQL
  servers stopped cleanly. OS network denial applied throughout; all Python
  socket/DNS audit reports record zero unexpected network attempts.

Initial architecture/Web attempts failed on unmaterialized LFS fixture pointers;
the extension first lacked parent-config dependency links. Supplying unchanged
cached bytes/links resolved these environment failures without product edits.
Those superseded logs are retained outside source. Hosted CI is not run for this
unpublished candidate. No live schema or current runtime position was inspected.
