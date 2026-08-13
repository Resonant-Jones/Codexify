# Account-observability migration compatibility proof

## Result

**GO**

The historical `b2c3d4e5f6a7` account-observability migration-content drift is
repaired: the migration file is restored byte-identical to the original
applied body, and a forward compatibility-normalization migration
(`9d4c2a7e1b6f`) converges clean, already-canonical, and backup-derived
preserved-tester schemas onto one canonical ADR-049 shape at one single
Alembic head. No preserved tester mutation occurred, no manual stamp was used,
and every persisted identity value survived.

## Baseline

- Branch: `main`
- Pre-task HEAD: `6eb21f463770fd1ef492de36aa4272c6d50f5e8b`
- Carried dirty-state inventory (prerequisite d6 work):
  - `guardian/threadspace/__init__.py` (blob `21d8f08cc06fd74f52c14cee58e2d49648c0e3d6`)
  - `guardian/threadspace/membership_tokens.py` (blob `8c332eb68dae5c558a0f47a53c48132ab2c2893a`)
  - `guardian/db/migrations/versions/d6f7a8b9c0d1_add_threadspace_node_membership.py` (blob `d02f5bfa629948f5e134ef9bb9e827cf2679250b`)
  - `guardian/db/migrations/versions/8f3c1a7d2e6b_merge_d6f7a8b9c0d1_compatibility.py` (metadata-only merge)
  - `tests/migration/test_d6_compatibility_bridge.py`
  - `tests/migration/test_alembic_revision_uniqueness.py` (modified to expect the d6 merge head)
  - `docs/architecture/proofs/2026-08-13-d6f7a8b9c0d1-compatibility-bridge-proof.md` (result `NEXT_PROOF_NEEDED`)
- Pre-repair Alembic graph: one head `8f3c1a7d2e6b` (metadata-only merge of `d6f7a8b9c0d1` and `6e2b9c4a7d1f`).

All carried prerequisites verified byte-identical to the completed proof.

## Historical migration-content drift

- Revision ID: `b2c3d4e5f6a7`
- Original commit/blob: `d2559f3b6d07156c0e139925d6ba256127d9690f` /
  `c6671615e786778a6d11c6554e2a1cdd6bef8719`
- Rewritten commit/blob: `f0bc85df86f148e635fdf19132311fd04ba1695f` /
  `3d9456c7235ae651f9057f93299abcb03205d33b`
- Exact classification:
  `already-applied migration body changed without revision identity change`

The same Alembic revision ID was edited in Git instead of being followed by a
new revision, so databases legitimately applied one body for `b2c3d4e5f6a7`
while current source carried a different body under the same identity.

## ADR impact

- Classification: `Aligned with existing ADR(s)`
- Governing ADR: ADR-049 Admin Account Observability and Invite Attribution
- Reason: The task does not change the accepted account-observability model.
  It repairs historical migration identity and brings old physical schemas
  forward to the already-accepted model. No new ADR was required.

## Schema-difference matrix

Four account-observability tables, compared across A (historical `b2` body),
B (pre-repair canonical body), C (current `models.py`), and D (ADR-049):

| Aspect | A: Historical | B: Pre-repair canonical | C: models.py / D: ADR-049 |
| --- | --- | --- | --- |
| `invite_links` PK | `id` | `invite_id` | `invite_id` |
| `guest_identities` PK | `id` | `guest_id` | `guest_id` |
| `presence_sessions` PK | `id` | `presence_session_id` | `presence_session_id` |
| `invite_links.created_by_user_id` nullability | NULL allowed | NOT NULL | NOT NULL |
| `invite_links.created_by_user_id` FK ondelete | SET NULL | RESTRICT | RESTRICT |
| FK targets on guest/metadata/presence | `<table>.id` | `<table>.<canonical_pk>` | canonical PK columns |
| FK constraint names | `fk_account_observability_*_id` suffix form | `fk_account_observability_*` canonical form | canonical names |
| `region_code` width | `VARCHAR(32)` | `VARCHAR(64)` | `VARCHAR(64)` |
| invite status check name | `ck_account_observability_invite_links_status` | `account_observability_invite_status_check` | same |
| invite lifecycle check name | `ck_account_observability_invite_links_lifecycle_timestamps` | `account_observability_invite_lifecycle_check` | same |
| exactly-one-subject check | OR-form XOR | `<>`-form XOR | same |
| country-code check | length only | length + uppercase | same |
| attribution value checks | absent | `attribution_method_check` + `attribution_confidence_check` | same |
| attribution consistency check | includes `prior_guest_id` in all-NULL arm | omits it | same |
| unique token representation | unique INDEX | UNIQUE CONSTRAINT | UNIQUE CONSTRAINT |
| geo index | `(started_at, country_code, region_code)` | `(last_seen_at, country_code, region_code)` | same |
| metadata acquisition index | present (`ix_..._acquisition_invite`) | absent | absent |

## Restored historical migration identity

- Expected historical blob: `c6671615e786778a6d11c6554e2a1cdd6bef8719`
- Final blob: `c6671615e786778a6d11c6554e2a1cdd6bef8719`
- Equality verdict: IDENTICAL (byte-for-byte, no modernization, no
  compatibility logic added, not conditional)

## Normalization migration

- Revision: `9d4c2a7e1b6f`
- Parent (`down_revision`): `8f3c1a7d2e6b`
- Recognized shapes: `historical_v1`, `canonical_v2`, `unknown_or_mixed`
- Behavior:
  - `historical_v1` → explicit normalization (renames + widen + constraint
    swap + index swap, preserving all identity values)
  - `canonical_v2` → verified no-op (no account-observability DDL emitted)
  - `unknown_or_mixed` → fail closed before any schema mutation
- Fail-closed preflight: rejects `created_by_user_id IS NULL` rows before
  tightening NOT NULL; rejects lowercase country codes before enforcing the
  uppercase rule
- Downgrade posture: forward-only; `downgrade()` raises a migration-only
  error before mutation rather than lying about reverse transformation

## Path A: clean-start proof

- Empty Postgres → upgraded through restored historical `b2` → current
  lineage → d6 branch → merge `8f3c1a7d2e6b` → normalize `9d4c2a7e1b6f`.
- Result: one final head `9d4c2a7e1b6f`; canonical ADR-049 schema;
  ThreadSpace tables present; second `upgrade heads` is a no-op.
- Evidence: `A_clean_start.json` (final_version `9d4c2a7e1b6f`,
  `governed_tables_present: true`).

## Path B: already-canonical upgrade proof

- Disposable DB created with the pre-repair canonical `b2` body (blob
  `3d9456c7235ae651f9057f93299abcb03205d33b` from commit
  `f0bc85df86f148e635fdf19132311fd04ba1695f`), upgraded to the merge head,
  then normalized.
- Result: classifier `canonical_v2`; normalization emitted no DDL; final
  head `9d4c2a7e1b6f`; schema signature identical to Path A.
- Evidence: `B_already_canonical.json`.

## Path C: backup-derived tester upgrade proof

- Preserved volume `codexify_tester_pg_data` mounted read-only, copied to a
  uniquely-scoped ephemeral volume, isolated Postgres started against only
  the copy.
- Pre-upgrade source revision: `d6f7a8b9c0d1` (verified).
- Account-observability classifier pre-upgrade: `historical_v1` (verified via
  the historical schema signature: PK `id`/`id`/`id`, `region_code
  VARCHAR(32)`).
- Upgraded through current sibling migrations → `8f3c1a7d2e6b` →
  `9d4c2a7e1b6f`.
- Result: no missing-revision error; no manual stamp; no data fabrication;
  final head `9d4c2a7e1b6f`; canonical account-observability shape;
  second upgrade is a no-op.
- Evidence: `C_backup_derived.json`.

## Three-way schema convergence

Normalized schema signatures (columns, types, lengths, nullability, PKs,
FKs with target/delete behavior, check semantics, unique semantics, indexes):

- `schema_A == schema_B == schema_C` → **MATCH**

PostgreSQL OID-derived auto-generated `_not_null` constraint names
(`2200_18304_1_not_null`) are representation noise and are normalized away;
nullability is captured semantically via `is_nullable`. All semantically
material attributes are compared and match.

Evidence: `convergence.json` verdict `schema_signatures_match`.

## Data preservation

Path C pre/post bounded row counts (canonical tables):

| Table | Pre | Post | Delta |
| --- | ---: | ---: | ---: |
| `users` | 18 | 18 | 0 |
| `projects` | 3 | 3 | 0 |
| `chat_threads` | 5,061 | 5,061 | 0 |
| `chat_messages` | 112,507 | 112,507 | 0 |
| `uploaded_documents` | 0 | 0 | 0 |
| `hosted_rooms` | 1 | 1 | 0 |
| `hosted_room_invites` | 1 | 1 | 0 |
| `hosted_room_participants` | 3 | 3 | 0 |
| `threadspace_nodes` | 0 | 0 | 0 |
| `threadspace_membership_invitations` | 0 | 0 | 0 |
| `threadspace_membership_grants` | 0 | 0 | 0 |
| `account_observability_invite_links` | 0 | 0 | 0 |
| `account_observability_guest_identities` | 0 | 0 | 0 |
| `account_observability_account_metadata` | 14 | 14 | 0 |
| `account_observability_presence_sessions` | 0 | 0 | 0 |
| `repository_bindings` | (absent) | 0 | 0 |

- Identity preservation: `identity_preserved: true` — PK-column values
  survive the `id → invite_id` / `id → guest_id` /
  `id → presence_session_id` renames (the three ID-keyed tables were empty
  in the preserved DB; the 14 `account_observability_account_metadata`
  rows keyed by `user_id` survived untouched).
- FK integrity: all four governed tables' FK constraints `VALIDATE
  CONSTRAINT` cleanly; canonical FK names all present; canonical PK names
  all present; orphan checks all zero.
- No message contents, usernames, tokens, or private telemetry values were
  emitted into this proof artifact.

## Preserved tester safety

- Mounted read-only (`:ro`) only for copying.
- No stamp, no upgrade, no downgrade, no DDL, no DML, no restart against the
  source database, no volume deletion.
- Final read of the preserved `alembic_version` (fresh read-only copy after
  all operations): `d6f7a8b9c0d1`.

## Manual stamp posture

Manual stamping remains prohibited and was not used at any point.

## Separate migrator-driver defect

The canonical `run_migrator.py` psycopg2/psycopg3 driver incompatibility
(`postgresql://` maps to psycopg2 which is absent from the runtime image)
remains a separate, pre-existing defect. For disposable schema proof only,
the `postgresql+psycopg://` driver-qualified scheme (the repository's own
supported `GUARDIAN_DATABASE_URL` scheme) was supplied ephemerally; no
repository file was changed. The proof result does not claim canonical
supported migrator boot is repaired.

## Hosted Room impact

- Migration/schema convergence is proven (all three paths reach one head
  with identical canonical schema).
- No Hosted Room live semantics were exercised.
- Preserved-environment startup remains a later, separately authorized task.

## Release impact

No beta support expansion. This is a migration-history repair; it does not
widen the supported release surface.

## Validation

- Focused migration tests: `22 passed`
  (`test_d6_compatibility_bridge.py`,
  `test_account_observability_compatibility_normalization.py`,
  `test_alembic_revision_uniqueness.py`)
- Full migration suite `tests/migration`: `111 passed, 29 skipped`
- Account-observability regressions: `93 passed`
  (`tests/db/test_account_observability_models.py`,
  `tests/account_observability`,
  `tests/routes/test_account_observability_invites.py`,
  `tests/routes/test_auth_invite_attribution.py`,
  `tests/privacy/test_account_observability_presence_privacy.py`)
- Alembic graph: exactly one head, `9d4c2a7e1b6f`.
- `make docs` / docs validation: pass (recorded in closeout).
- `git diff --check`: clean.

## Limits and non-goals honored

- No mutation of the preserved tester DB.
- No Hosted Room replay.
- No tester runtime restart.
- No psycopg2/psycopg3 migrator repair.
- No seed-default repair.
- No account-observability runtime change.
- No model change, no route change, no privacy-policy change.
- No ADR rewrite.
- No generalized historical migration sweep.
- No unrelated cleanup.
- No release-support expansion.
