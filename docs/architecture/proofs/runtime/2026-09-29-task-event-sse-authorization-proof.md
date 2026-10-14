# Task-Event SSE Authorization Proof — 2026-09-29

## Result

**PASS for the focused route authorization code and test surface.** This is not
a live private-preview or public-ingress proof. The full public-ingress
authentication boundary remains `HOLD`.

## Baseline and implementation

- Branch: `codex/enforce-mixed-principal-boundary`
- Baseline: `d56d9df7dc3a75530388d3d68eaa30169276b08a`
- Implementation commit: `88a596661`
- Route: `GET /api/tasks/{task_id}/events`
- Handler: `guardian.guardian_api.stream_task_events`

The path parameter is the queue-facing `backend_task_id`. The route resolves
only `ChatCompletionAttempt.backend_task_id`, takes the durable `thread_id`,
and passes it with the authenticated principal to `require_thread_read_access`.
It does not look up by `request_id` or use request/event metadata as authority.

## Admission order

1. Reject incompatible principal credential presence through the existing
   `reject_mixed_principal_credentials` boundary.
2. Resolve an existing principal lane: exact remote account session, local
   request-user/API-key behavior, or purpose-scoped Hosted Room guest session.
   A remote operator session or raw operator API key does not resolve a user
   principal.
3. Query the durable attempt by exact `backend_task_id`.
4. Authorize its canonical `thread_id` with `require_thread_read_access`.
5. Only after those checks return the existing SSE response; the generator
   then reads Redis.

An absent attempt returns HTTP 404 before Redis. Account cross-thread access
keeps the shared policy's HTTP 403 denial; Hosted Room guest lifecycle, room,
or thread mismatch keeps its HTTP 401 denial. No denied request gets an SSE
response body. Missing or empty Redis data after an authorized attempt remains
transport behavior; no event is synthesized from Postgres.

## Focused matrix

The focused route tests prove:

- canonical thread owner can subscribe and existing event framing/payloads are
  preserved;
- another account is denied even with the exact backend task ID, with zero
  Redis reads and no event/thread/turn disclosure;
- the Hosted Room backing-thread owner can read its task stream;
- an active same-room guest can read the eligible task stream without becoming
  the canonical thread owner;
- removed, wrong-room, wrong-thread, malformed, and wrong-purpose guest access
  fails before Redis;
- anonymous, invalid account, remote operator-session, and raw operator-key
  requests fail before attempt lookup; mixed account/guest presence returns
  HTTP 400 before lookup;
- unknown and Redis-only backend task IDs return HTTP 404 without Redis reads;
- using a valid `request_id` as the path value does not match the attempt and
  returns HTTP 404;
- a spoofed `X-User-Id` does not override the authenticated remote account;
- `Last-Event-ID` reconnect cursors are passed to Redis only after the same
  authorization decision.

## Validation

Commands and results:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_task_event_stream_authorization.py \
  tests/routes/test_chat_task_events_lifecycle.py
19 passed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_mixed_principal_boundary.py \
  tests/identity/test_identity_boundary_contract.py \
  tests/identity/test_account_purpose_strict_migration.py \
  tests/identity/test_operator_session_boundary.py \
  tests/identity/test_operator_route_auth_migration.py \
  tests/identity/test_account_observability_service_capability.py \
  tests/identity/test_websocket_account_session_purpose.py \
  tests/identity/test_thread_read_access.py \
  tests/identity/test_task_event_stream_authorization.py
265 passed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/core/test_chat_completion_attempt_persistence.py \
  tests/core/test_chat_completion_enqueue_service.py \
  tests/routes/test_chat_routes.py \
  guardian/tests/routes/test_hosted_rooms.py \
  guardian/tests/routes/test_hosted_room_guest.py \
  tests/routes/test_chat_task_events_lifecycle.py
294 passed, 3 xpassed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_operator_route_auth_migration.py
16 passed

/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/auth/test_private_preview_access.py
3 passed
```

The runtime-facing tests use deterministic database/Redis instrumentation.
They do not establish live Cloudflare, Tunnel, browser, or private-preview
behavior. Cloudflare Access is unchanged.

## Scope and architecture

Changed runtime files are limited to `guardian/guardian_api.py`,
`guardian/core/dependencies.py`, and the small composition helper
`guardian/core/task_event_access.py`. Tests cover the new route boundary and
update the existing SSE lifecycle fixture to include a durable attempt. The
existing account-session-to-guest negative fixture now uses the canonical
`account_session` purpose; the frozen route-auth assertion records the new
route-specific principal dependency.

No model, migration, queue, Redis event transport, thread-read policy,
WebSocket, frontend, Cloudflare, or public-ingress proof receipt was changed.
The implementation follows ADR-091 durable attempt authority and ADR-092
credential-purpose separation. Global local-first defaults remain unchanged.

## Remaining qualification

This focused route repair does not close the full public-ingress matrix.
Rerun that matrix from the beginning against the repaired runtime with
Cloudflare Access still enabled before considering any Access-free canary.


## PR #848 reconciliation and bounded review follow-up — 2026-10-02

The conflict reconciliation at `6746bbc640fe8241c287a2cce646bc6ab466e5fc`
merges `main` at `b04e0d088e7627f29e4476dcf268ca5f0d78faa5`. It retains
both presence-based mixed-principal rejection and the typed account-session
failure signal from main. Mixed-principal HTTP 400 responses do not carry
`X-Guardian-Auth-Failure: ACCOUNT_SESSION_INVALID`.

The bounded review follow-up gates task-event mixed-principal rejection with
the existing remote/private-preview boundary and offloads synchronous durable
resource authorization from the async SSE event loop. Authorization still
finishes before response construction and Redis consumption. Regression
coverage includes legitimate local guest access with supplemental session
material, single-lane remote guest access, and off-loop authorization queries.

Focused follow-up validation:

```text
/Volumes/Dev_SSD/Codexify-main/.venv/bin/pytest -v \
  tests/identity/test_task_event_stream_authorization.py \
  tests/identity/test_mixed_principal_boundary.py \
  tests/routes/test_chat_task_events_lifecycle.py \
  tests/routes/test_chat_thread_remote_auth.py
34 passed
```

**Merge readiness remains HOLD on the non-chat task-family review finding.**
The generic endpoint has non-chat producers/consumers, while the present
resource guard requires a durable chat completion attempt. Agent runs,
delegation, voice, and warmup need an explicit supported-family inventory and
canonical access/acceptance contract before admitting their streams here.
Neither Redis existence nor caller-supplied task/thread metadata may supply
that missing authority. This follow-up does not introduce such a policy or
claim preserved generic non-chat stream compatibility.

No live deployment, ingress requalification, or Cloudflare mutation occurred.
The original focused proof and public-ingress HOLD remain historically bounded.


## Chat-only finalization candidate — 2026-10-02

This additive record preserves the earlier proofs. The isolated finalization
checkout began clean at `c6b5e720d21dc2dcadc5cf8b5ea7cd8be6b0e67b` on
`codex/finalize-public-ingress-chat-only`. It includes the separately adopted
snapshot-reader prerequisite; it does not rewrite the protected PR #848 head
`590e9ac9f11b4a5f7fa8b153ee0a76074eff04ff`.

The accepted matrix at `3cc1aed8808467cf22169ba38ad98e92e4351450` replaces the
historical assumption that every producer must retain generic-SSE access.
Generic public task SSE admits chat completion attempts only, through ADR-091
attempt-to-thread authority. Agent/coding uses qualified dedicated snapshots;
delegation uses its operator surface; account import uses job readback; voice
is quarantined from generic ingress; warmup remains internal. No new schema,
queue identity mapping, or polymorphic authorization framework is introduced.
The accepted ingress contract was initially allocated as ADR-097 against the
then-current index. Current-main integration introduced a separate ADR-097 for
message-request consent, so the ingress decision is now ADR-098; its contract
content and acceptance are unchanged. ADR-091/092 remain unchanged.

The candidate corrections classify account/operator JWT purpose claims as
unverified presence evidence, catch parser recursion failures, and run Hosted
Room invitation mixed-principal preflight before database access or mutation.
Ordinary credential verification is unchanged. Existing off-loop chat task
authorization remains intact. The generic resolver needs documentation and
regression coverage rather than a new runtime family dispatch.

Focused and adjacent verification on the candidate tree:

```text
PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v \
  tests/identity/test_mixed_principal_boundary.py \
  tests/identity/test_task_event_stream_authorization.py \
  tests/identity/test_task_event_family_authorization.py \
  tests/routes/test_chat_task_events_lifecycle.py \
  tests/identity/test_operator_route_auth_migration.py \
  tests/contracts/test_protocol_tokens.py
146 passed (recorded in the combined run below)
```

Coverage includes non-chat producer IDs denied before thread/Redis lookup,
JWT mixed-lane rejection before verification, mounted generic-SSE rejection,
real stdlib C and Python JSON scanners, invalid/duplicate/deep payloads,
invitation non-consumption and successful same-invitation retry, and unchanged
local supplemental-credential behavior. Invitation persistence checks use the
existing SQLite fixture; producer/resource tests use deterministic database
and Redis instrumentation. These are bounded tests, not live ingress proof.
A parseable deep payload can provide presence evidence; inspection never
confers authentication. Actual parser recursion failures return no purpose.

The initial combined command additionally ran `tests/architecture`:
`509 passed, 31 failed, 37 errors`. Of these, the focused suites contributed
146 passes and architecture contributed 363 passes. Four unhydrated canonical
Git LFS fixtures caused 29 failures and 37 errors. Restoring their cached,
SHA-256-verified canonical objects resolved those environmental failures:
all 166 tests across the eight affected architecture modules passed.
Hydration changes no Git source blobs.

Two DLG validation failures remain. The Architecture KB node's recorded
content hash already mismatches README bytes at the frozen `c6b5e720d`
baseline. The ADR-index node's recorded hash needs synchronization with this
candidate's ADR-098 entry. Both metadata files are outside the finalization
allowlist. The task explicitly requires stopping on an unrelated pre-existing
validation defect; no metadata correction has been applied. A two-line
content-hash-only patch was prepared for scope review. Finalization is paused
at this gate, uncommitted; full architecture and integrated prerequisite
qualification have not been completed on this candidate tree.

Documentation validation passed before this follow-up; rerun it and diff
checks after final documentation edits. Changed legacy files retain only the
five already-existing unused-import lint findings; no lint cleanup is claimed.
No public-ingress live matrix, deployment, Cloudflare change, push, or merge
occurred. Public-ingress and PR #848 remain **HOLD**.


## Approved DLG prerequisite and integrated qualification — 2026-10-02

This follow-up supersedes the stopped-gate status above without replacing its
historical evidence. The human-approved proof-prerequisite packet authorized
exactly two derived metadata hash replacements. `git apply --stat` reported
two files, two insertions, and two deletions; `git apply --check` passed.
The frozen patch matched a reconstructed hash-only diff byte-for-byte before
application, and each replacement matches SHA-256 of its canonical source.

| Derived metadata path | Canonical source | Classification |
| --- | --- | --- |
| `docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json` | `docs/architecture/README.md` | Pre-existing mismatch at `c6b5e720d`; source README unchanged by this candidate. |
| `docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json` | `docs/architecture/adr/adr-index.md` | Parent-induced update for the already-approved ADR-098 index entry. |

Exact inspected replacements:

- `docs/knowledge-graph/nodes/codexify:doc:architecture:kb-entrypoint.json`: `d5649213e80957592204001dd2165ac22ee6c3dfd03ed634ec6eb17c9357eef2` -> `ee7c45fb2664345156b0bdb4cd5b43a9dadf8fefa9ff9dd418711c42cb732457`.
- `docs/knowledge-graph/nodes/codexify:doc:architecture:adr-index.json`: `23fcc455c3edb9ffb2c7a0865208e7983ee468c9dfd15b4de37c611f868bfd6c` -> `1ea4ff7a006a9158d535acb4892e7598e6fe6ffd80a2247f70a6a3467efb30b5`.

No canonical source was changed to manufacture a match. No broader node or
generated-graph regeneration, freshness rewrite, authority change, or runtime
edit accompanied this repair. All ten pre-existing candidate file hashes
matched the inspection receipt immediately after application. The runtime,
tests, ADR entry, index, and chat contract remained byte-unchanged throughout
the historical qualification window. Integration later renumbered the
accepted ingress ADR from 097 to 098 to avoid a current-main collision; this
proof receives only this additive execution record.

Fresh integrated command, from the isolated worktree root:

```bash
AGENT_SNAPSHOT_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:54429/agent_snapshot_proof \
PYTHONDONTWRITEBYTECODE=1 /Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -v \
  tests/identity/test_mixed_principal_boundary.py \
  tests/identity/test_task_event_stream_authorization.py \
  tests/identity/test_task_event_family_authorization.py \
  tests/routes/test_chat_task_events_lifecycle.py \
  guardian/tests/routes/test_hosted_room_guest.py \
  tests/identity/test_operator_route_auth_migration.py \
  tests/contracts/test_protocol_tokens.py \
  tests/architecture \
  tests/integration/test_agent_coding_snapshot_readback_postgres.py \
  guardian/tests/routes/test_agent_orchestration_events.py \
  tests/identity/test_account_purpose_strict_migration.py
```

Result: **739 passed, 107 warnings, zero failures/errors/skips**, 38.21 seconds.
The port was disposable and is historical, not application configuration.

| Fresh proof surface | Passed |
| --- | --- |
| Four focused ingress suites plus Hosted Room guest routes | 151 |
| Operator migration and protocol-token regressions | 53 |
| Full architecture suite, including the previously affected 166 cases and DLG coherence | 431 |
| Disposable PostgreSQL snapshot authority | 71 |
| Adjacent agent routes | 18 |
| Account-purpose strict migration | 15 |

The adopted snapshot prerequisite's four-module set has 121 passes in this
run: 71 PostgreSQL, 18 routes, 15 account-purpose, plus the 17 operator cases
already counted above. These are overlapping subsets, not additional tests.
The prior 146/166 pass records were not substituted for fresh execution.

The exact two formerly failing DLG tests also passed separately after patch
application. `scripts/knowledge_graph/validate_and_generate_dlg.py validate`
returned success with zero errors and all ten canonical node source hashes
matching. Existing README broken-local-link warnings remain documented debt;
the README is unchanged and no unrelated link cleanup was attempted.
Docs validation and ordinary/staged diff checks form the final closeout gate.
Ruff retains exactly five pre-existing unused-import findings when compared
with the frozen `c6b5e720d` sources; there are no new lint findings.

The four necessary Git LFS fixtures were hydrated from cached canonical
objects verified against their recorded SHA-256 OIDs and sizes. Original
checkout pointer bytes were verified against HEAD after testing; the final
worktree retains canonical hydrated representations to avoid LFS stat noise.
No fixture source delta belongs to either commit. The dedicated tmpfs PostgreSQL container published
only on loopback. Its unique test schemas were all dropped (count zero), and
the container was removed by its recorded, label-verified ID. Application
`DATABASE_URL`, shared services, and shared volumes were not used or changed.

Commit separation is coherent: the independently stale README metadata repair
can be committed alone against the starting source tree. The final parent
commit includes its ADR-index-induced metadata replacement atomically with
the index entry and parent correction. The implementation commit subject is
`Finalize public ingress task authorization`. Commit SHAs are reported in the
execution closeout; no commit attempts to embed its own hash.

ADR-091/092, current-state release truth, the accepted ingress matrix, the
snapshot-reader implementation, and async generic-SSE authorization mount
remain unchanged. No schema, queue mapping, worker, persistence, UI, protocol
token, or deployment change occurred. GitHub still holds the open PR at
`590e9ac9f11b4a5f7fa8b153ee0a76074eff04ff`; all four P1/P2 review threads remain
unresolved there because this local candidate has not been pushed. No thread
was automatically resolved. The local candidate passes this scoped integrated
qualification; deployed/public-ingress qualification and human merge decision
remain **HOLD**. These tests do not establish a deployed ingress, live browser,
Cloudflare, full supported-Compose, or provider execution result.
