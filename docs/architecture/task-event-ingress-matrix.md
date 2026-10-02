# Task-Event Ingress Matrix

## Status and authority

- Status: Accepted architectural contract; implementation/integration separately scoped.
- Date: 2026-10-02.
- Lane: architecture-impact; initial documentation draft with separately
  scoped snapshot-reader implementation/proof in the isolated continuation.
- Evidence baseline: PR #848, `codex/prove-public-ingress-auth-boundary`,
  `590e9ac9f11b4a5f7fa8b153ee0a76074eff04ff`.
- Acceptance owner: Resonant Jones.
- Snapshot implementation/proof: adopted prerequisite at
  `a352c088a0d9fd68edabf28ae53dbbf40f80595d` on the isolated
  `codex/adopt-agent-coding-snapshot-readback` branch. Fresh destination
  validation: 121 passed, including 71 PostgreSQL cases; see the
  [snapshot proof](./proofs/2026-10-02-agent-coding-snapshot-readback-proof.md).
  PR #848 itself is untouched.
- PR #848 and release/public-ingress qualification: unchanged; HOLD.

This is the canonical accepted location for the task-family ingress decision.
It records accepted dispositions and their proof obligations. The
agent/coding investigation and selected snapshot proof resolve that row to
`MOVE`; the destination is dedicated snapshots, not dedicated SSE.
Resonant Jones accepted the six-family contract on 2026-10-02, as recorded in
the acceptance packet at `3cc1aed8808467cf22169ba38ad98e92e4351450`
(`docs/architecture/pr848-ingress-acceptance-and-integration-plan.md`).
Acceptance settles intended ingress; documentation, route existence, and
historical use cannot substitute for runtime qualification.

[00 Current State](./00-current-state.md) remains release authority.
[ADR-091](./adr/091-durable-chat-completion-attempt-authority.md) governs chat
completion attempt-to-thread authority.
[ADR-092](./adr/092-credential-purpose-and-mixed-principal-authentication-boundary.md)
governs credential purposes, principal separation, and remote mixed-principal
rejection. This contract does not reinterpret or supersede either ADR.

No ADR number is allocated here. ADR-096 is already the
[adaptive sidebar decision](./adr/096-adaptive-application-sidebar-posture-and-shell-boundary.md).
The current mainline index was inspected at
`56463fd967730cc6ad7da5078b83daa6e10546a0`; any subsequent ADR creation must
reinspect the then-current [ADR index](./adr/adr-index.md) and numbered files
for collisions rather than reserve a number from this snapshot.

## Decision question

Which task families intentionally belong on
`GET /api/tasks/{task_id}/events` at remote/public ingress, and which existing
durable authority governs each admitted family?

A producer publishing into a shared Redis event stream does not establish
generic HTTP admission. A frontend accepting an arbitrary observed task ID
does not establish a supported family. The PR #848 P1 is an over-broad
authorization assumption: preserving every historical transport consumer
would require authority machinery before proving that consumer belongs on
the public surface.

## Disposition semantics

| Disposition | Meaning after architectural acceptance |
| --- | --- |
| `KEEP` | Intentionally admit the family on generic public SSE, using its existing durable authority and a qualified principal lane. |
| `MOVE` | Use the named dedicated resource surface; generic compatibility is unnecessary. The word does not assert that a runtime migration has happened or that the destination is qualified. |
| `QUARANTINE` | Exclude this family from generic public task SSE. Existing internal transport or separately governed feature routes retain their own boundaries. |
| `PROVE` | The ingress decision remains unresolved. Candidate ownership or route presence is insufficient; no new generic admission is authorized. |

These are document labels, not newly registered runtime tokens. The selected
snapshot-reader task applies canonical ownership to both local and remote
snapshot callers; memory-only/operator-only snapshot compatibility is excluded.
Existing local credential behavior and local legacy dedicated SSE are preserved.
This creates no new local generic-SSE contract and does not reinterpret ADR-092.

## Canonical ingress matrix

Admission and denial proof IDs below refer to the obligations in the next
section. The initial draft inspected test sources only. The
agent/coding investigation at `39a0d4867b245fa40fffa141a82b7ba08eb4dd8c`
(`docs/architecture/proofs/2026-10-02-agent-coding-ingress-contract-investigation.md`)
subsequently ran six focused existing checks and a synthetic mounted-router
counterexample; neither establishes live public-ingress qualification.
The subsequent [snapshot reader proof](./proofs/2026-10-02-agent-coding-snapshot-readback-proof.md)
uses actual account dependencies and disposable PostgreSQL to qualify the
bounded destination on the adopted prerequisite branch; release/public-ingress HOLD remains.

| Family | Intended consumer | Canonical ingress/readback surface | Task/resource identifier | Allowed principal lane | Durable authority source | Admission proof | Denial proof | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Chat completion | Ordinary chat and eligible Hosted Room owner/guest clients | Generic `GET /api/tasks/{task_id}/events` | Exact `ChatCompletionAttempt.backend_task_id`; resolves canonical `thread_id`. Request IDs and message IDs remain distinct. | Authenticated account or eligible purpose-scoped Hosted Room guest; existing local principal behavior preserved. Remote operator credentials grant no thread access. | PostgreSQL completion attempt -> canonical thread; account ownership or current room/invitation/participant eligibility. | C+; existing focused test sources, live qualification pending. | C-; existing pre-Redis denial test sources, credential P2 repair and live qualification pending. | `KEEP` |
| Agent/coding | Account Coding Loop viewer and Action Center for consistent thread-backed account-coding runs. Operator-only shapes remain separately governed. | Dedicated `/api/chat/{thread_id}/coding-runs`, `/api/agents/runs/{run_id}/coding`, owner-filtered run snapshots and thread lists. Dedicated public agent SSE is quarantined; generic task SSE is outside the intentional contract. | Exact durable `AgentRun.run_id` -> `AgentDeployment` -> canonical source thread. Queue, coding, and attempt IDs remain correlation identities. | Existing account-session reader lane only. Operator creation grants no account read entitlement by implication; no guest or generic admission. | Surviving PostgreSQL thread owned by the authenticated account; run/deployment/source thread IDs agree, with consistent typed coding/account metadata. No memory, metadata-only, threadless, or deleted-resource fallback. | A+ qualified in mounted-router/disposable-PostgreSQL proof on the adopted prerequisite branch; browser/deployed ingress unqualified. | A- snapshot denial and public dedicated-SSE quarantine proven in the same bounded suite. Generic exclusion remains PR #848 follow-up. | `MOVE` |
| Delegation | Authorized delegation operator | Dedicated `GET /api/delegations/{delegation_id}/events` | Durable `DelegationJob.delegation_id` -> `task_id`. Optional thread/project fields are context, not account ownership. | Existing operator lane under `require_operator_auth`; account and guest credentials cannot inherit it. | PostgreSQL delegation job plus the existing operator route contract. No new account ownership is inferred. | D+; existing route/service test sources; destination HTTP qualification pending. | D- required at the mounted route and generic ingress. | `MOVE` |
| Account import | Importing account's status/readback client | Dedicated `GET /api/imports/openai-account/{job_id}` with owner-scoped polling | `OpenAIAccountImportJob.id` / API `job_id`; no assumed generic backend task ID equivalence. | Authenticated owning account; any existing additional route key remains a separate gate, not ownership. | PostgreSQL import job queried by both job ID and canonical account ID. | I+; existing service readback test source and browser polling code; HTTP qualification pending. | I-; cross-account service denial source; generic exclusion and mounted-route denial proof pending. | `MOVE` |
| Voice turn outer task | Voice-turn submitter; internal voice route/worker event exchange | Existing `POST /api/voice/turn` request/response and durable message readback; no generic public task-SSE entitlement | Outer `VoiceTurnTask.task_id` stays internal transport identity. Canonical messages/thread govern later message readback. | No principal admitted for the outer task on generic public SSE. Existing voice-route authentication is separate and is not qualified by this matrix. | No sufficient durable outer task -> resource authorization binding. Request thread metadata, Redis dedupe, queue payload, and worker completion metadata are not substitutes. | V+ required to preserve the existing voice interaction without generic SSE. | V- required for generic exclusion before Redis. | `QUARANTINE` |
| Warmup | Internal startup/system worker and operator diagnostics | Internal queue/events and separately governed diagnostics; no generic public task-SSE surface | `WarmupTask.task_id` is operational transport identity, not an account resource grant. | No principal admitted for warmup on generic public SSE. Operator credentials do not create an unimplemented public warmup reader. | No durable public user-resource authority. Startup enqueue and Redis event existence are operational evidence only. | W+ required to preserve internal operation without generic ingress. | W- required for generic exclusion before Redis. | `QUARANTINE` |

Unknown families remain outside generic admission. A later family requires an
explicit consumer/surface decision and proof; it cannot inherit access from
a familiar task ID shape, event type, or caller-supplied family label.

## Admission and denial proof obligations

| IDs | Required evidence and current limits |
| --- | --- |
| C+ / C- | Owning account, Hosted Room owner, and eligible guest can read the exact durable attempt's thread stream. Cross-account, cross-room, inactive guest, wrong-purpose, mixed-principal, unknown, request-ID-as-task-ID, and Redis-only requests fail before event consumption. Reconnect repeats current authentication and resource checks. Existing sources: [task-event authorization tests](../../tests/identity/test_task_event_stream_authorization.py), [thread access tests](../../tests/identity/test_thread_read_access.py), and [historical focused proof](./proofs/runtime/2026-09-29-task-event-sse-authorization-proof.md). Those sources do not close the outstanding JWT classification, malformed/deep payload, or invitation-exchange P2s. |
| A+ / A- | The investigation at `39a0d4867` (`docs/architecture/proofs/2026-10-02-agent-coding-ingress-contract-investigation.md`) found no intentional generic-SSE need. Resonant Jones selected the narrower snapshot-only contract; the [snapshot proof](./proofs/2026-10-02-agent-coding-snapshot-readback-proof.md) exercises real account dependencies and PostgreSQL authority for owner admission, cross-account/wrong-lane denial, null/deleted/ambiguous authority denial, and zero event reads. Dedicated public SSE returns 404 before lookup/Redis rather than becoming an authorized destination. The row is `MOVE` to snapshots. Generic exclusion, browser behavior, full startup/schema, and deployed/public ingress qualification remain separate gates. |
| D+ / D- | Authenticate the existing operator lane, resolve the durable delegation job, and read only its mapped stream. Reject account, guest, mixed, missing, and wrong-purpose credentials before lookup; reject unknown jobs before Redis. Do not invent operator-to-operator tenant isolation absent an existing authority contract. Verify generic ingress exclusion independently. Sources: [delegation routes](../../guardian/routes/delegations.py) and [route test sources](../../tests/routes/test_delegations_routes.py). |
| I+ / I- | Owner can poll queued/running/terminal job state and recover through durable readback without generic task SSE. Another account gets the existing existence-hiding denial; guest/operator credentials do not become the owner. Verify the real mounted dependencies and generic exclusion. [Account-import test sources](../../tests/rag/test_openai_export_account_import.py) include account A readback and account B service denial; they do not prove public route admission. |
| V+ / V- | Preserve voice submission, terminal response, message reload/readback, timeout, and dedupe behavior without attaching generic task SSE. Reject outer voice task IDs on generic ingress before Redis regardless of event existence or possession. [Voice route test sources](../../tests/routes/test_voice_routes.py) cover the request/response flow; they do not establish safe remote voice-route ownership or generic public SSE entitlement. |
| W+ / W- | Startup/internal warmup still enqueues, executes, and reports internally. Generic public requests for a warmup ID are rejected before Redis for every otherwise eligible reader. [Warmup worker test sources](../../guardian/tests/workers/test_warmup_worker.py) exercise internal publication; they are not public ingress proof. |

Admission requires both principal authentication and resource authorization.
For a family moved to dedicated readback, its denial proof must cover both the
destination's resource boundary and generic exclusion. For quarantined
families, successful internal execution proves no public admission.

## Producer and consumer evidence

- **Chat:** [shared acceptance](../../guardian/core/chat_completion_service.py),
  [task-event authorization](../../guardian/core/task_event_access.py), and
  [canonical thread policy](../../guardian/core/thread_access.py) compose
  ADR-091 authority. The generic route consumes Redis only after authorization.
- **Agent/coding:** [agent event publisher](../../guardian/agents/events.py)
  fans out using `run_id`. [Agent routes](../../guardian/routes/agent_orchestration.py)
  create durable runs. At the original PR baseline, dedicated SSE lacked
  ownership checks; the adopted snapshot prerequisite quarantines public SSE.
  [AgentStore](../../guardian/agents/store.py) now has a dedicated account
  snapshot policy using canonical thread ownership and consistent run lineage.
  Internal store helpers and local legacy SSE are not account-read authority.
- **Delegation:** the dedicated operator router loads the durable job and
  bridges its task ID to Redis. Shared transport does not require shared ingress.
- **Import:** [account import service](../../guardian/services/openai_account_import.py)
  scopes durable queries by `job_id` and `user_id`.
  [Import routes](../../guardian/routes/migration.py) expose owner-bound job
  readback; the [browser coordinator](../../frontend/src/features/imports/accountImportCoordinator.ts)
  polls that job. [Settings](../../frontend/src/features/settings/SettingsView.tsx)
  has a generic SSE attachment for a task ID from legacy upload responses;
  the current legacy upload returns migration statistics. That compatibility
  hook does not establish a canonical staged-import SSE contract.
- **Voice:** [voice routes](../../guardian/routes/voice.py) wait internally for
  the terminal task event. [GuardianChat](../../frontend/src/features/chat/GuardianChat.tsx)
  awaits the voice-turn HTTP response and reloads messages. The outer task's
  queue/dedupe/event fields do not establish a durable authorization binding.
- **Warmup:** [startup](../../guardian/guardian_api.py) enqueues system warmup
  and publishes task events; [the worker](../../guardian/workers/warmup_worker.py)
  handles operational work. This proves neither an intentional generic
  public consumer nor a user-resource authority.
- **Generic UI:** the [Command Center drawer](../../frontend/src/features/commandCenter/components/RunDetailDrawer.tsx)
  constructs a generic URL for an observed `taskId`. Its catch-all behavior is
  a consumer-routing seam to reconcile after acceptance, not an authorization
  source or automatic support promise for every observed family.

These are inspected code paths and test sources at the evidence baseline.
Enabled-profile route mounting, external clients, browser interaction, and
live ingress behavior remain unqualified here. The inventory does not declare
that every Redis producer is a supported public API consumer.

## Nodes, trust boundaries, and failure handling

Browsers and external clients request reads; Guardian authenticates and
authorizes; PostgreSQL owns durable resource state; workers execute tasks;
Redis carries queues/events. Client IDs, browser state, event payloads, and
queue metadata cross a trust boundary as evidence, not authority. The threat
model includes unauthorized or malicious readers, credential confusion, and
honest-but-buggy producers under worker, transport, or database failure.

| Failure | Required boundary |
| --- | --- |
| Durable state unavailable or missing | No fallback to Redis, cache, event payload, or ID possession; preserve the existing failure semantics until a scoped implementation defines changes. |
| Credential class conflict | ADR-092 rejection before protected lookup or mutation; a failed lane cannot fall back to another. |
| Ambiguous ID, owner, or family | Fail closed; caller labels, prefix guesses, and lookup order cannot supply authority. |
| Disconnect, reconnect, or revoked eligibility | Re-evaluate current principal and durable eligibility on each new connection; event cursors grant no permission. |
| Dedicated destination or UI migration incomplete | Retain HOLD and report the specific consumer/authority gap; do not reopen generic admission as a compatibility fallback. |

This contract introduces no sync/conflict policy, schema migration, queue
format, event contract, new route, protocol token, or persistence mechanism.

## Acceptance and implementation sequence

1. Architecture acceptance is recorded on 2026-10-02 against source commit
   `39a0d4867b245fa40fffa141a82b7ba08eb4dd8c`, matrix Git blob
   `1134e623a782e4aa3d7534fc40492ae235ee0188`, and packet commit
   `832633a4b95ed2868f3f84f516c6bf569a44303a`. The human decision accepts all six
   dispositions; it does not close PR #848 P1 or authorize runtime execution.
2. The snapshot-reader prerequisite is adopted and qualified on the isolated
   branch at `a352c088a0d9fd68edabf28ae53dbbf40f80595d`, with fresh 121-test
   destination proof and dedicated public-SSE quarantine. Do not repair or qualify unused SSE merely because the route
   exists; a future intentional consumer requires a separate decision/proof.
3. Authorize bounded runtime/consumer changes from the accepted matrix:
   remove accidental generic admission or attachment, retain intentional
   dedicated flows, and repair only their required authority seams. Reconcile
   the old finalization file allowlist before touching additional files.
4. Add persistence only if a family is intentionally required on generic
   public SSE, its user-facing need is proven, and existing durable authority
   is insufficient. Voice/warmup compatibility alone cannot trigger this work.
5. Resume PR #848 finalization, close P1 and the three credential/invitation
   P2s with separate evidence, then undertake separately authorized ingress
   qualification and merge gates.

PR #848 remains HOLD at the reviewed SHA after matrix acceptance. The
earlier proof document and chat runtime contract remain historical/current
authorities within their existing scope; this acceptance does not rewrite
them, clear a review finding, or claim a migration, merge, deployment, or release.

## Documentation validation

The initial architecture-only slice changed this draft and its README pointer;
the investigation refined the row, and the selected snapshot continuation adds
bounded store/routes and focused tests. Run `python3 scripts/validate_docs.py`,
verify local links and all eight required per-family fields, and run
`git diff --check`. Runtime validation for the adopted snapshot prerequisite is specified
in its proof, including PostgreSQL evidence and existing lint limits. Preserve
the clean PR #848 checkout, the prior documentation checkout, and the protected
Simplify pending work when committing the isolated continuation.
