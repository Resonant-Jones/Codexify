# Hosted Room Owner + Invited-Guest Canonical Transcript Live Proof

## 1. Result

`BLOCKED`

The current-tip live proof could not reach the Guardian application. The canonical
`codexify_tester` startup path stopped at its migration prerequisite because the
preserved tester Postgres database records Alembic revision `d6f7a8b9c0d1`, while
the migration graph available at the tested checkout cannot locate that revision.
The migrator exited `1`, the backend remained unavailable, and no product
semantics were exercised.

This is a runtime prerequisite blocker, not evidence that Hosted Room owner/guest
semantics pass or fail. No runtime code, profile, migration, database revision, or
authorization rule was changed to bypass it.

## 2. Audit metadata

| Field | Value |
| --- | --- |
| Proof timestamp | `2026-08-12T21:04:59Z` (`2026-08-12T17:04:59-0400`) |
| Branch | `codex/audit-atlas-room-surfaces` |
| Exact pre-proof HEAD | `145210c22f8e39df84272156513f5aa87d716aac` |
| Pre-proof tip | `145210c22 Enable Hosted Rooms in tester profile` |
| R1 prerequisite | PASS: `d51a1704438f61560175ab2a00417a9fb01cd3c5` is an ancestor of HEAD |
| R1P0 prerequisite | PASS: `145210c22f8e39df84272156513f5aa87d716aac` is an ancestor of HEAD |
| Configured tester profile | `v1-whooshd-deepseek-web`; not observable through live health because backend startup was blocked |
| Compose project | `codexify_tester` |
| Backend loopback endpoint | `http://127.0.0.1:8889` |
| Repository state before proof | clean |
| Tester env gate | `.env.tester` exists, is Git-ignored, and required values passed a key-name-only placeholder check |

## 3. Runtime posture

`make tester-status` initially reported the desired tester state as enabled but
the DB, Neo4j, backend, and frontend as exited. The authorized canonical
`make tester-up` path was run without deleting volumes. DB and Neo4j became
healthy, but the migrator stopped startup:

```text
alembic.script.revision.ResolutionError: No such revision or branch 'd6f7a8b9c0d1'
alembic.util.exc.CommandError: Can't locate revision identified by 'd6f7a8b9c0d1'
[Migrator] ERROR: alembic upgrade failed
```

A bounded read-only query of `alembic_version` returned
`d6f7a8b9c0d1`. A repository search under the current migration, docs, and test
trees found no matching revision. The backend remained in `created` state and
both `/health` and `/openapi.json` returned connection failure (`HTTP 000`).

Consequently:

- backend health was not observable;
- the configured profile name was not confirmed by live health;
- mounted route labels were not observable from the running application; and
- representative owner and guest OpenAPI paths were not observable live.

Static profile content and passing route tests are recorded only as test/config
evidence. They are not substituted for live route posture.

## 4. Proof principal model

The intended principal model remains:

- owner = authenticated Codexify account;
- guest = invitation-backed Hosted Room guest session;
- guest is not claimed as a second Codexify account; and
- this proof is not account-to-account federation.

No owner or guest principal was provisioned because the real auth API was
unavailable.

## 5. Room identity

No disposable Hosted Room was created. Therefore no live Room ID, backing thread
ID, participant count, or participant identities exist for this run.

The governing identity rule remains `HostedRoom.id != ChatThread.id`, with one
Hosted Room referencing one canonical backing thread. That is a documented and
tested contract here, not a live observation from this blocked run.

## 6. Transcript parity evidence

No proof messages were written. There are no owner, guest, or continuation
message IDs to compare across authority projections.

| Proof message | Canonical message ID | Author / participant | Owner observed | Guest observed | Canonical thread ID |
| --- | --- | --- | --- | --- | --- |
| first owner message | not created | not created | BLOCKED | BLOCKED | not created |
| guest message | not created | not created | BLOCKED | BLOCKED | not created |
| second owner message | not created | not created | BLOCKED | BLOCKED | not created |

## 7. Persistence evidence

The only Postgres inspection was the bounded read-only migration prerequisite
query. No Room/message state was queried because no HTTP behavior occurred and
no proof fixtures were created. Canonical `chat_messages` persistence,
single-thread parity, distinct participant provenance, and guest display-name
snapshot retention remain unproven at this tip.

## 8. Lifecycle evidence

No invitation was created or exchanged, so no guest session could be revoked.
Server-enforced post-revocation read denial, write denial, non-persistence, and
owner transcript survival remain unproven.

## Required proof matrix

| Proof obligation | Result | Evidence |
| --- | --- | --- |
| current tester profile active | BLOCKED | Backend unavailable; live health HTTP `000` |
| owner Room routes live | BLOCKED | Backend unavailable; live OpenAPI HTTP `000` |
| guest Room routes live | BLOCKED | Backend unavailable; live OpenAPI HTTP `000` |
| owner authenticated | BLOCKED | Login route could not be reached |
| Room created | BLOCKED | No authenticated owner/runtime |
| owner canonical write | BLOCKED | No Room/runtime |
| invitation exchange | BLOCKED | No Room/runtime |
| guest sees owner message | BLOCKED | No guest session/message |
| guest canonical write | BLOCKED | No guest session/runtime |
| owner sees guest message | BLOCKED | No guest message/runtime |
| bilateral continuation | BLOCKED | No Room/runtime |
| Postgres canonicality | BLOCKED | HTTP behavior was not established; no proof messages exist |
| revocation denies guest reads | BLOCKED | No invitation/session exists |
| revocation denies guest writes | BLOCKED | No invitation/session exists |
| transcript survives revocation | BLOCKED | No transcript/revocation exists |

## 9. What this proves

This run proves only the current operational blocker:

- the exact checkout contains both prerequisite commits;
- the ignored tester env prerequisite is present without exposing values;
- the preserved `codexify_tester` database is reachable and reports
  `d6f7a8b9c0d1` as its Alembic revision;
- the current migration graph cannot resolve that revision; and
- the canonical lifecycle therefore cannot start the Guardian backend for the
  requested live proof.

It does not prove same-node owner + invited-guest collaboration, canonical
transcript parity, participant provenance, revocation enforcement, or an
operational Room V0.1 substrate.

## 10. What this does NOT prove

- second authenticated account participation;
- same-node owner + invited-guest Room collaboration;
- owner/guest canonical message parity;
- participant provenance in live persistence;
- guest lifecycle revocation behavior;
- cross-node Room transport;
- federation or Room Protocol;
- personal Guardians;
- multi-thread Rooms;
- Room Workspace;
- Atlas;
- production support;
- default beta support; or
- live frontend guest UX.

## 11. Next implementation seam

The smallest next seam is **a blocker requiring correction**: reconcile the
preserved tester database's Alembic revision lineage with the current canonical
migration graph in a separate, explicitly authorized migration/operations task.
That task must determine the provenance and correct recovery path for
`d6f7a8b9c0d1`; this proof does not authorize stamping, deleting, recreating, or
otherwise mutating migration state.

After that blocker is corrected, rerun this exact current-tip owner/guest live
proof before selecting native guest/join Room frontend or Room Workspace work.

## Validation

- `.venv/bin/pytest -v tests/config/test_whooshd_deepseek_hosted_room_route_posture.py guardian/tests/routes/test_hosted_rooms.py guardian/tests/routes/test_hosted_room_guest.py`
  - PASS: `186 passed`, `45 warnings`.
- Requested literal frontend command from `frontend/`:
  `pnpm vitest run src/features/rooms/__tests__/RoomMode.test.tsx src/features/rooms/__tests__/roomRoute.test.ts`
  - FAIL: the package wrapper runs Vitest from `frontend/src`, so those filters
    resolved with an extra `src/` prefix and no files were found.
- Current repository-equivalent frontend command:
  `pnpm --dir src exec vitest --config vitest.config.ts run features/rooms/__tests__/RoomMode.test.tsx features/rooms/__tests__/roomRoute.test.ts`
  - PASS: `2` files, `14` tests.
- `make docs PYTHON=.venv/bin/python`
  - PASS: architecture-doc validation and diagram freshness validation passed.
- `git diff --check`
  - PASS.
- Bounded proof-artifact secret-pattern scan
  - PASS: no bearer token, Tailscale auth key, Hosted Room session cookie,
    invitation-token field, or serialized token field was found.

## ADR impact and release interpretation

Classification: `Aligned with existing ADR(s) - proof only`.

Governing boundaries are the Room-First Atlas V0.1 Interaction Contract,
ADR-053 (Node-Hosted Room Access Boundary), ADR-005 (Runtime Mode and Account
Boundary Invariants), ADR-003 (Message Identity vs Request Identity), and the
tester supported-profile route posture.

No accepted semantics changed. This blocked run does not widen any release
claim. Hosted Rooms, invited-guest collaboration, Atlas, federation, and related
surfaces remain outside the current supported beta/release promise.

## Disposable residue

No proof owner, Room, invitation, guest session, cookie jar, or message was
created. The canonical startup operation preserved the existing isolated tester
volumes. DB, Neo4j, Redis, and the tester Tailscale sidecar were left running;
application services remained unstarted because the migrator prerequisite
failed.
