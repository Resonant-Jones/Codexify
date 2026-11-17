# Accepted account-bound Knowledge read proof

Status: isolated private Command Bus implementation and synthetic proof. Private
Preview chat admission, public provider operations and invocation remain
quarantined. No live provider request, credential provisioning, deployment,
registration change, migration, invitation or release-permission change occurred.
ADR-112 remains the accepted topology; this proof does not change HOLD.

## Implementation boundary

The existing connector owner continues in the isolated
`codex/knowledge-dispatch-proof-20261117` branch. No separate runtime owner was
found in accessible task metadata; the clean worker-binding docs branch at
`7815f7735` contains the accepted ADR, not a competing implementation.

`accepted_knowledge_invoke.execute_accepted_knowledge_read` is a private Python
entry point, with no HTTP route or chat caller. It resolves original accepted
account custody and creates the existing database-backed `CommandBusStore`.
Caller account/actor claims, headers, provenance, idempotency identity, target URL
and work-order linkage do not supply authority. Server-derived actor and lineage
replace them. The trusted caller must supply an explicit server-resolved
permission profile and external policy rules; OAuth consent alone is insufficient.
A profile must authorize the actual account/task/thread, exact read, network and
connector use. Fixed-host external allow rules are mandatory; deny rules prevail.

The existing Command Bus still builds the manifest and evaluates policy,
permissions, idempotency, run persistence, events and readback. The private lane
accepts exactly GitHub/Notion `content_search` and `content_read`, with the existing
GET/read/read-only/safe/no-approval manifest tuple. Missing or altered manifest
entries fail closed. Public invocation semantics and its loopback requirement
remain unchanged. Only the verified in-process path omits the mechanical loopback
base requirement; it retains stricter explicit network/connector/host checks.

The production Preview app still omits provider-operation routes. The private
index now derives exactly four entries from provider-owned route metadata without
mounting routes or modifying public OpenAPI. A metadata parity test compares them
to the existing foreground route manifest. The new synthetic lifecycle tests use
an app with no provider routes; ordinary public invocation remains quarantined.
No generalized ASGI/executor callback or HTTP impersonation was added.

`project_accepted_knowledge_tools` supplies catalog-only accepted-account checks
before a frozen decision exists. It requires explicit trusted policy templates,
current OAuth metadata and both existing opt-ins; it never decrypts credentials.
Its separate binding has no command/hash execution authority. Returned schemas
are detached, selected GitHub repositories are account-scoped hints, and current
connection/ownership is rechecked before advertisement.

`read_accepted_knowledge_result` re-reads a durable completed CommandRun and
revalidates exact custody, connection and current policy immediately before
model delivery. It cannot start provider work, decrypt credentials, accept a
caller-provided result body or finalize an assistant response. Foreign run IDs
are rejected before any event can be added to another account's run. The separate
chat owner must integrate these private interfaces; no active chat caller exists.

## Authority, replay and persistence

`AcceptedKnowledgeRead` freezes exact task evidence and canonical arguments,
then re-resolves persisted original/current account ownership, acceptance,
terminal state, cancellation, accepted deadline, current OAuth generation,
expiry and selected GitHub repository at every execution boundary. Current
placement or queue fields cannot select a new accepting account. Missing,
legacy, conflicting or stale authority fails closed. Publication before the
acceptance acknowledgement remains a distinct pending refusal for a future
bounded retry, not permission to execute.

`oauth_store.read_grant` reads authority metadata without decrypting credentials.
Credential resolution is just in time, bracketed by revalidation, with no
ambient/legacy fallback or automatic refresh. Refresh claims, refresh completion,
reconnection and repository reselection invalidate the old generation. Expired
credentials require a separately governed refresh before a fresh attempt.
Returned argument copies cannot change the accepted hash.

Both ordinary idempotent replay and create-run conflict replay revalidate current
custody, connection authority and policy. The server-derived key includes exact
accepted lineage and connection generation. A new connection cannot replay old
connection evidence. Concurrent duplicate delivery persists one run and sends one
provider request (or one bounded Notion traversal).

Existing CommandRun rows retain canonical auth subject/delegation, argument hash
and server-derived key. Existing created/started/completed/failed/blocked events
carry account/request/task/thread/turn/tool/command/hash/provider/generation
lineage without tokens or caller-supplied provenance. A denied replay appends a
`run.blocked` event with `phase=replay` and returns no result; it does not rewrite
the original execution's completed status. Failures and cancellation persist no
partial provider result. Audit-storage failure prevents provider dispatch and
returns a bounded error. Existing account-owned/operator readback restrictions
remain intact.

## Native transport and deadline proof

The bounded adapter uses a fresh native asynchronous HTTPX client per invocation,
fixed provider origins, TLS verification defaults, no environment proxy, no
redirects, one connection and no shared client/token cache. Each request uses
fresh credential revalidation, current policy checks and a post-response check.
GitHub issue/PR identities must match the selected repository and issue number.
Notion uses the existing bounded page-content projection, validates page/child
UUIDs, limits traversal depth/blocks/requests, and rejects repeated cursors.
Both providers cap raw responses at 1 MiB and preserve bounded output content.

Each request has a total 15-second cap shortened by accepted work deadline and
credential expiry. A 100-ms monitoring interval rechecks authority while I/O is
pending. Native cancellation is awaited and streams/clients close before the
operation unwinds; no blocking provider request is abandoned in a thread.
Parent cancellation persists failure and re-raises cancellation. Accepted work
expiry propagates the existing `AcceptedChatTaskDeadlineExceeded` contract and
records its canonical failure code, preserving task terminal handling.

Synchronous authority reads run outside the event loop with a 2-second await
bound. The private PostgreSQL session wrapper applies transaction-local
1-second statement and lock limits; no global database setting changes.
A timed-out authority read cannot dispatch provider I/O. Pool acquisition or
underlying driver cleanup may outlive a cancelled await; this is not a claim
that Python can kill a blocked database thread. Provider socket cleanup and
no-result behavior are proven independently, including a real row-lock refusal.

Revocation cannot retract a request already sent to a provider. Once observed,
this path cancels pending I/O, starts no subsequent request, and suppresses the
result. There is no database lock spanning provider I/O and no claim of an atomic
network transaction with revocation. Post-response checks close observed stale
results; provider-specific external revocation/consent still needs an authorized
canary.

## Current catalog/admission proof

The follow-on rehearsal passed **138 PostgreSQL tests, zero skips**, including
18 new catalog/delivery cases. Each of the four reads traverses accepted custody
before a frozen command, policy-filtered catalog projection, the existing frozen
decision, private Command Bus execution and durable result revalidation. Negative
cases cover pending acknowledgement, no/foreign/denied policy, account/thread/
Project changes, cancellation, terminal state, Preview removal, connection or
flag changes during projection, cross-account run IDs, pending/unknown results,
revocation before delivery and mutable-schema isolation. Synthetic provider
responses only; this is not full HTTP/Redis/chat/model or live-provider proof.

The final synthetic PostgreSQL receipt binds staged tree
`43b0c4b87b5eecdd23ecbe26872eba47164ba99a` at base `f8fca4292`.
The cluster reached `d8a90bf32107` with 145 tables, rejected all six custody
mutations and was stopped and removed. Receipts are in
`dispatch-admission-20261117/`. Focused unit/transport/custody tests passed 78 cases;
the broader Command Bus/public/internal/custody/admission/logging regression
passed **250 tests**. An initial six ephemeral-socket tests failed under sandbox bind restrictions,
then the unchanged suite passed with the required local socket access.
The final architecture/evidence suite passed **890 tests** with temporary Git
worktree metadata access; scoped Ruff and diff whitespace checks passed.

## Earlier transport evidence

- Real PostgreSQL suite: **120 passed, zero skips**, including private entry-point
  execution for all four operations, durable audit via a new store instance,
  duplicate deliveries, A/B isolation, revocation/cancellation failures, row-lock
  timeout, pending acceptance, audit failure, and existing owned readback tests.
- Broader Command Bus/public/internal/provider/admission/logging regressions:
  **289 passed** before the final deadline classification adjustment.
- Final private transport plus existing accepted-loopback deadline tests:
  **50 passed**, including native synthetic socket EOF/cleanup for both provider
  paths under deadline, parent cancellation and observed revocation.
- Architecture/evidence suite: 888 passed with two sandbox Git-metadata failures;
  the unchanged regeneration module then passed all 15 tests with the needed
  disposable-worktree access. An earlier run encountered unhydrated LFS JSON
  pointers; 278 tracked fixtures were hydrated from cache without source edits.
  These environment failures and receipts are retained, not counted as passes.
- Native tests use uniquely allocated ephemeral loopback listeners and synthetic
  HTTP; they prove socket cancellation, not real-provider TLS/DNS/consent.
- Fresh synthetic PostgreSQL 16.15 migration reaches `d8a90bf32107`, 145 tables;
  six prohibited custody mutations are rejected. Private Unix socket, no TCP;
  cluster stopped and removed. This is not a restored live-backup proof.

The real-PG receipt binds staged tree
`7ae4560d3498a9d29760ac4b4e67515d850476a7`. The later change preserves canonical
accepted-deadline classification and was covered by the 50-test final batch.
Task-local receipts and runnable rehearsal are in `dispatch-transport-20261117/`.
Earlier custody/fence receipts remain under `dispatch-proof-20261117/` and
`dispatch-fence-20261117/`. One earlier fence-test isolation defect was repaired:
OAuth tombstones lack a user FK, so the guarded disposable reset explicitly clears
OAuth tables; it now also clears CommandRun rows/events. No production schema or
test expectation was weakened.

## Remaining gates

Full exact-final-revision CI, scope review and source integration remain required.
This private path is not active chat admission: the chat owner must supply
trusted policy resolution and connect the catalog/invoke/delivery interfaces,
preserve worker acknowledgement retry handling and prove final model/transcript
completion. The existing frozen attempt supports one command/hash, not an
arbitrary multi-step loop; coordinate canonical checkpoint changes separately.
Imported-history exposure remains excluded. No new architecture decision is
required for the implemented ADR-112 path; it does not authorize broader commands.

Operational gates remain separate: actual-ingress logging proof (including
cloudflared management/tail sinks and managed-edge visibility), fresh restored
backup/migration/rollback rehearsal for the exact deployment, named deployment
owner/window, backend-only secrets and encryption-key custody, exact provider
registration/permission verification, and a designated consent/read/disconnect/
revocation canary. Source/unit/synthetic database proof does not establish any of
those operational outcomes. Setup and invocation stay disabled pending their
respective gates.
