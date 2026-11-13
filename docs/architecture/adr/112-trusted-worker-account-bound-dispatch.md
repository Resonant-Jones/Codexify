# ADR-112: Trusted Worker Account-Bound Dispatch

- Status: Accepted architecture decision; implementation pending
- Date / accepted: 2026-11-13
- Decision owner and human approver: Resonant Jones
- Scope: trusted Private Preview GitHub/Notion read-only connector pilot
- Evidence posture: documented-contract and inspected code paths, not runtime proof
- Release posture: HOLD unchanged

## Context and decision

Guardian-verified, account-bound **in-process Command Bus dispatch** is the
selected mechanism for this bounded pilot. A short-lived worker bearer
credential is not required for this trusted topology. Independently deployed
services or machine/network trust boundaries may justify a separately governed
capability later; no credential protocol is selected here.

Acceptance selects architecture, not an implemented dispatcher, sufficient
existing worker authority, deployment permission, or Private Preview
qualification. The operator approved this decision on 2026-11-13 and explicitly
limited this task to documentation and accepted-job prerequisite reconciliation.
ADR-112 was absent from the canonical index and numbered directory at the
inspected `origin/main` revision before allocation.

## Authorities and evidence

| Concern | Authority | What is not sufficient |
| --- | --- | --- |
| Account identity | Guardian's authenticated canonical account at original request acceptance | Operator key, worker/service identity, account-shaped string |
| Accepted work ownership | Canonical persisted account-to-job relationship and unambiguous request/job/attempt identity, resolved server-side | Queue payload, possession of a job ID, connector ID, caller-supplied account |
| Connector permission | Current owner-scoped connection authorization and provider-specific resource permissions | Catalog visibility, configuration presence, previous successful read |
| Execution authority | Guardian's current eligibility decision for that exact accepted attempt and read command, enforced through Command Bus | A previous attempt, a model request, or an audit record alone |

The worker acts **on behalf of** an account. Processing a job does not turn the
worker into an account principal. Queue delivery is evidence of delivery, not
execution authorization. Guardian remains the authorization authority; user
grants and revocations remain authoritative inputs to its decision.

## Required account-binding boundary

Before any connector credentials or protected data are used, Guardian must:

1. Establish authenticated account authority at original request acceptance.
2. Persist and subsequently resolve the authoritative account-to-job relationship
   and exact job/attempt identity. Do not reconstruct ownership from queue fields.
3. Verify original ownership against current canonical account, thread and,
   where relevant, Project ownership. Missing, stale or conflicting authority
   fails closed; current placement alone cannot silently reassign accepted work.
4. Verify current job/attempt eligibility, including acceptance, terminal state,
   cancellation, deadline and retry/duplicate posture.
5. Verify current account eligibility, permitted scope, connector ownership,
   authorization and revocation, provider-specific resource permissions, and the
   exact read-only command and arguments.
6. Preserve a bounded, secret-free account/request/attempt lineage in the existing
   Command Bus run/event/result and authorized readback surfaces.

These checks apply independently at **each execution attempt**, including a
retry. Prior execution is not continuing authority. No account-to-account,
account-to-operator, or ambient service-credential fallback is permitted.
A warm worker must not retain another account's credential, connection selection,
session, SDK cache or execution context when switching accounts.
Credential material stays outside task records, logs and CommandRun provenance.

## Command Bus orchestration is not HTTP execution

The existing Command Bus remains authoritative for manifest/command eligibility,
invocation policy, permission evaluation, idempotency, CommandRun persistence,
events, result provenance and readback authorization. This decision creates no
independent execution or audit pipeline and modifies no public invocation API.

`guardian/command_bus/invoke.py::execute_invoke` accepts `auth_subject` and
validates actor claims relative to it. It does not independently authenticate
that supplied subject. Its internal branch calls
`guardian/command_bus/internal_dispatch.py::execute_internal_command`; ordinary
HTTP-backed commands instead call
`guardian/command_bus/loopback_http_adapter.py::execute_loopback_request`.
Calling `execute_invoke` in-process therefore does **not** remove the second
HTTP authentication boundary for a normal OpenAPI-backed operation.

The future bounded implementation must connect verified accepted-work authority
to the provider's existing ownership/scope/revocation checks without laundering a
shared operator key into an account session, bypassing route-specific
authorization, or dropping Command Bus/network policy. The current internal
command dispatch is a mechanical precedent, not an authorization grant for all
provider calls. This ADR does not select a generalized ASGI dispatch framework,
new internal authentication protocol, or bearer-token mechanism.

## Accepted-job prerequisite reconciliation

Inspected base: `origin/main` at
`a01a3400549596692930eb54544d3af7501d2d55` (2026-11-13).
These are **code-inspection findings**, not tests or live execution receipts.

**Overall classification: PARTIAL.** The accepted-chat lifecycle has useful
canonical persisted request/attempt/thread binding, but no sufficient complete
Preview connector execution authorization boundary is established. The legacy
GitHub sync path is specifically a **GAP**, not the authority to reuse.

| Source and exact anchor | Finding | Missing authority or checks |
| --- | --- | --- |
| `guardian/routes/chat.py::chat_complete`; `guardian/core/chat_completion_service.py::enqueue_chat_completion` | Authenticated chat acceptance supplies account scope and checks thread access; the enqueue path commits a `ChatCompletionAttempt` before Redis and marks acceptance after enqueue. | This establishes a source path to inspect, not an authorization grant for every queue task or connector. Acceptance-record failure is explicitly handled; row existence alone is not accepted eligibility. Publication precedes accepted_at, so the subsequent implementation must handle that race without assuming atomic acceptance. |
| `guardian/db/models.py::ChatCompletionAttempt`; `guardian/core/db.py::create_chat_completion_attempt`, `mark_chat_completion_attempt_accepted` | PARTIAL canonical candidate: request ID, unique backend task ID, thread ID, turn ID, accepted timestamp, terminal/completion state, deadline/lock snapshot and frozen tool decision. | No direct persisted accepting-account/principal field or connector grant. Account ownership is currently reached through the thread; original-account custody and ownership-change/conflict handling must be demonstrated rather than inferred from a current join. No new table is authorized here. |
| `guardian/core/db.py::_accepted_tool_attempt`, `get_chat_tool_checkpoint`, `freeze_chat_tool_decision` | Checks exact request/task/thread/turn and compares current `ChatThread.user_id` to supplied account; locks the attempt and freezes first command/argument hash. | This helper itself does not check accepted_at, terminal eligibility, deadline, current account status or connector permission/revocation. Comparing a supplied account to a row is not independent original-account proof. |
| `guardian/workers/chat_worker.py::_attempt_matches_task`, `_run_chat_task`; `guardian/core/chat_completion_service.py` tool loop | Existing worker terminal/deadline handling and checkpoint correlation are reusable evidence. | Tuple matcher omits user ID. Queue task identity fields are not account authority. There is no general connector authorizer combining canonical account resolution, live eligibility and provider scope at dispatch. Unbound/direct tasks cannot inherit this pilot authority; no reachable authentication bypass is claimed. |
| `guardian/routes/connectors.py::_schedule_github_sync`, `_run_github_sync`, `connector_sync`; `guardian/db/models.py::ConnectorConfig`, `ConnectorRun` | GAP for accepted account-bound work: in-memory scheduled task, run created as execution begins; run records config/status/timestamps. Existing GitHub sync uses ambient `GITHUB_TOKEN` and writes raw documents. | Neither config nor run records canonical accepting account, prior accepted request/attempt or invocation-scoped connector authorization. This is a distinct legacy ingestion owner, not the read-only pilot job authority. |
| `guardian/connections/notion/router.py::_configured_client`, read routes; `guardian/connections/notion/credentials.py`; `guardian/connections/notion/service.py` | Foreground account-session routes resolve account-owned credential access and bounded provider reads. | No separate authoritative background accepted-job binding; HTTP session authorization cannot simply be skipped in-process. Credential configuration is not job authority. |
| `guardian/command_bus/contracts.py::InvokeRequest`; `guardian/command_bus/invoke.py::execute_invoke`; `guardian/db/models.py::CommandRun`; `guardian/routes/command_bus.py` | Command Bus records subject/actor, arguments hash and idempotency; route readback is subject-bound. | Audit of a supplied subject does not prove the upstream account acceptance. Invocation metadata is not a new accepted-job ownership authority. |

The isolated GitHub Knowledge/local Guardian pilot at commit
`8f731fabcb99c87ce29888d0ec0254f196232fd7` is **not this mainline baseline**.
Its account-scoped GitHub credential/read seam, bounded operations and local-only
tool exposure do not prove Preview worker authority or change the classification.
It preserves the remote/multi-user quarantine; no implementation from that branch
is merged by this documentation task. Inspection anchors include `tests/connections/test_notion_connection.py`
(account-scoped setup/read/disconnect and Command Bus registration),
`tests/core/test_chat_completion_service_tool_loop.py` (grant/checkpoint
boundaries), and the isolated pilot
`tests/connections/test_github_read_adapter.py` and
`tests/core/test_knowledge_tool_execution.py`. They do not prove the proposed
Preview binding; no runtime tests were executed for this documentation task.

### Narrow first implementation prerequisite

Reconcile and prove the existing accepted-chat attempt ownership chain as the
pilot's admission source before wiring provider execution: server-resolve the
canonical owner rather than trusting task.user_id, demonstrate original
account-authenticated acceptance and fail closed on missing/conflicting custody,
and combine accepted/terminal/cancel/deadline/current-account eligibility with
exact attempt/command/argument binding. Then recheck the current provider-owned
connection scope and revocation through the Command Bus boundary.

If the existing attempt/thread chain cannot establish original accepting-account
custody, identify the minimum change to that **existing canonical authority** in
a subsequent bounded task; do not manufacture a parallel authority store or
backfill original acceptance from an arbitrary current account string. This ADR
implements neither persistence changes nor that resolver. Standalone legacy
sync jobs are not admitted by this selection.

The remaining implementation trust-boundary question is how the verified
accepted-work context reaches the existing provider authorization checks while
retaining Command Bus policy and avoiding HTTP account impersonation. The
in-process topology is settled; the detailed adapter and proof remain pending.

## Connector and history boundaries

Scope is only trusted Private Preview GitHub/Notion `content_search` and
`content_read`. Preserve their provider-specific execution, credential and
resource-permission owners; the legacy GitHub sync owner remains separate.
No connector writes, repository mutations, ingestion/synchronization, memory or
identity mutations, background scheduling, global connector authorization or
default Beta route promotion are introduced.

This mechanism may be reusable, but permission never follows reuse automatically.
The [history recall contract](../account-history-recall-contract.md) retains its
request-scoped HistoryRecallGrant, canonical account and Project ownership,
per-message provenance classification and imported-history model-exposure
exclusions. This connector decision does **not** activate remote/multi-user
history-recall workers or amend ADR-016/084 consent. Imported-history exposure
remains separately unauthorized.

## Alignment and consequences

- ADR-005 preserves canonical account isolation; ADR-081 preserves independent
  canonical Project and thread ownership, including conflict refusal.
- ADR-024 preserves turn-scoped consultation and user-governed grants.
- ADR-061 keeps transport beneath identity and capability authorization.
- ADR-071 preserves Connections as projection, not a new execution owner.
- ADR-075 preserves bounded Knowledge reads and provider-specific credentials.
- ADR-092 preserves account/operator/service purpose separation.
- ADR-094 supplies invocation-specific revalidation and shared-worker isolation
  principles. Its subject is coding execution credentials; it neither mandates
  connector bearer transport nor grants connector authority.
- ADR-016 and ADR-084 remain unchanged, including import/recall consent.

None of these decisions is superseded. The smaller trusted topology avoids an
unnecessary credential service but requires a carefully proven canonical-state
resolver and isolation boundary. Missing proof continues to deny execution.

## Subsequent implementation proof requirements

These are required future proofs, **not tests executed by this docs task**:

1. Account A executes only its authorized read.
2. Account B cannot reuse A's job or connector.
3. Missing/conflicting job ownership fails closed.
4. Revocation before execution blocks the read.
5. Duplicate delivery cannot duplicate effects or widen authority.
6. Retry revalidates current authority rather than inheriting it.
7. Same-worker sequential A/B work preserves credential/context isolation.
8. CommandRun/events retain truthful account and attempt lineage without secrets.
9. Command Bus manifest, policy and permission checks cannot be bypassed.
10. Imported-history content remains excluded.

No runtime, migration, configuration, test, deployment or release qualification
is established by this decision. HOLD and both release lanes remain unchanged.
