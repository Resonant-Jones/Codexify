# ADR-098: Public Task-Event Ingress as Chat Completion Readback

## Status and decision authority

Accepted architectural contract, recorded from Resonant Jones's six-family
matrix acceptance on 2026-10-02 at `3cc1aed88`. This ADR records that existing
decision; it does not independently authorize runtime work or release.
The approved finalization task starts at `c6b5e720d`, containing the separately
adopted and qualified snapshot-reader prerequisite.

The number was allocated at execution time after inspecting the ADR index and
numbered files at local/remote-tracking `main`
`56463fd967730cc6ad7da5078b83daa6e10546a0` and the destination baseline. Both
ended at ADR-096, which already governs adaptive sidebar architecture.
[ADR-091](./091-durable-chat-completion-attempt-authority.md) and
[ADR-092](./092-credential-purpose-and-mixed-principal-authentication-boundary.md)
remain unchanged and are not superseded.

## Context

Historical producers share Redis task-event transport. That observation is
not an intentional generic public HTTP reader contract. The original #848 P1
assumed every producer needed durable authorization on that endpoint. The
accepted [ingress matrix](../task-event-ingress-matrix.md) removes that
assumption without manufacturing task-family persistence or dispatch.

The service's HTTP boundary admits a principal and resource together;
PostgreSQL is resource authority. Redis events, queue/task identifiers,
caller-provided ownership hints, and frontend possession are evidence or
transport only. The threat model includes foreign accounts, wrong credential
purposes, untrusted identifiers, stale eligibility, and unavailable durable
state. Scope remains local-first; no new coordinator or federation behavior
is introduced.

## Decision

`GET /api/tasks/{task_id}/events` intentionally admits **chat completions only**.
Authenticate the existing eligible account/local or Hosted Room guest lane,
resolve the exact `ChatCompletionAttempt.backend_task_id`, and authorize the
attempt's canonical thread under ADR-091 and its existing thread/room policy.
Remote operator credentials do not grant chat ownership. Every connection,
including a reconnect with an event cursor, repeats admission.

| Family | Disposition | Authority and surface |
| --- | --- | --- |
| Chat | `KEEP` | Generic SSE through durable completion attempt -> canonical thread; owning account or eligible room guest. |
| Agent/coding | `MOVE` | Dedicated snapshots/thread lists through exact durable run -> deployment -> surviving account-owned canonical thread and consistent typed lineage. Dedicated public agent SSE is quarantined. |
| Delegation | `MOVE` | Existing dedicated operator surface through durable delegation job and the operator contract; no implied account read grant. |
| Account import | `MOVE` | Dedicated durable job readback scoped by job ID and owning account. |
| Voice outer task | `QUARANTINE` | No generic public task-SSE admission. Existing request/response and canonical message readback retain their own gates. |
| Warmup | `QUARANTINE` | Operational/internal transport only; no generic public reader entitlement. |

Unknown, moved, and quarantined family IDs without a durable chat attempt
return non-disclosing 404 before thread or Redis access. No polymorphic table
search, caller family label, request ID, queue UUID, or Redis existence can
produce a generic grant. Durable-state unavailability fails closed.
Family descriptions are architecture labels, not new protocol tokens.

Threadless, deleted, inconsistent, memory-only, metadata-only, or
operator-created agent shapes gain no account-read entitlement by implication.
Their disposition does not authorize additional persistence or an unused
public SSE repair. Dedicated destination qualification remains surface-specific.

## Credential boundary and compatibility

ADR-092 remains the governing principal-purpose rule. Presence inspection may
read the exact account/operator purpose from native two-part tokens or the
claims segment of JWTs to reject mixed lanes **before verification, resource
lookup, or invitation mutation**. This unverified evidence grants no principal
and adds no JWT authentication path. Duplicate/invalid-purpose claims are not
classified. Undecodable payloads and parser recursion failures fail closed
without escaping as parser HTTP 500; presence inspection never grants authentication.
Ordinary signature, expiry, purpose, and session validation remain separate.

Hosted Room invitation exchange runs the existing remote/private-preview
preflight before database access; a mixed request leaves its one-time
invitation unconsumed and creates no participant or session cookie. Invitation
bootstrap capability is not silently reclassified as an account/operator
session. No automatic credential clearing or implicit lane fallback is added.

Local/single-user credential behavior and local legacy agent stream generation
remain unchanged. The latter remains unqualified as public readback. No
schema, migration, queue mapping, worker/provider policy, event payload,
replication, or release-support contract changes follow from this ADR.

## Proof and release boundary

The finalization proof is recorded as a dated follow-up in the
[task-event authorization proof](../proofs/runtime/2026-09-29-task-event-sse-authorization-proof.md).
It must separately demonstrate chat/guest admission, pre-Redis family denial,
JWT mixed-presence rejection, invitation nonconsumption/retry, malformed
credential denial, and preserved local behavior on the evaluated branch.
The [snapshot prerequisite proof](../proofs/2026-10-02-agent-coding-snapshot-readback-proof.md)
retains its separate provenance and ownership scope.

Focused tests, SQLite fixtures, and disposable PostgreSQL do not qualify
deployed/public ingress. PR #848 and public-ingress qualification remain
**HOLD**; [00 Current State](../00-current-state.md) remains release authority.
Push, integrated deployment qualification, merge, and release decisions remain
separate human gates.
