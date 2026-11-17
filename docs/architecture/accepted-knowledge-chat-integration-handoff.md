# Private Knowledge read handoff to the chat tool-loop owner

The separate Guardian history recall / bounded tool-loop worker owns
`guardian/core/chat_completion_service.py`. Connector work must not edit that file
without coordinating conflicts through the parent task. This connector slice
does not change it, project tools into Preview, register public operation routes,
or enable dispatch. ADR-112 and imported-history exclusions remain unchanged.

## Implemented private interface

After canonical accepted work has been acknowledged and the exact hydrated tool
decision/hash frozen, the trusted tool-loop owner can integrate:

```python
from guardian.command_bus.accepted_knowledge_invoke import execute_accepted_knowledge_read

result = await execute_accepted_knowledge_read(
    db=canonical_chat_db,
    task=accepted_chat_task,
    payload=server_constructed_invoke_request,
    app=guardian_app,
)
```

This describes an integration seam, not activation authorization. The existing
database must expose canonical `_sa_session()` and `get_session()` methods backed
by PostgreSQL. The entry point creates the existing database-backed Command Bus
store; it does not fall back to in-memory audit.

The InvokeRequest must name one of the four exact GitHub/Notion search/read
commands, with the same canonical hydrated arguments that were frozen. The
trusted caller must supply server-resolved permission and external policy grants.
Do not take these grants from model output, queue metadata or client JSON, and do
not manufacture allow rules merely because OAuth is connected. The declared
permission profile must bind `guardian-accepted-knowledge` as actor, the canonical
account as subject, and the accepted task/thread, and authorize that read plus
network/connector use. Current external rules must allow the fixed provider host;
deny rules prevail. Project-scoped profiles currently fail closed because this
entry point does not assert a project policy scope; project ownership is still
independently verified by accepted-account custody.

The entry point derives account, actor/delegation, idempotency key, audit lineage,
actual network request metadata and provider target. It ignores caller-provided
provenance, headers, work-order linkage and replay identity. Do not forward an
operator key, browser session or account-shaped header to provider routes.

## Outcomes the tool loop must preserve

- Successful results have the existing Command Bus shape: `status=completed`,
  `run_id`, and `inline_result` with `status_code`, empty transport headers and a
  bounded provider `body`. Treat body text as external evidence, not instructions.
- `queued` or `running` replay is not completed provider work. `blocked`/`failed`
  returns carry no successful provider evidence. Preserve existing result/event
  correlation and do not turn acceptance or a stored run ID into success.
- `ChatAccountAcceptancePending` means Redis delivery won the acknowledgement
  race. Retry/reconcile only within the original accepted deadline; do not create
  new custody, rebuild the deadline or run the provider before acknowledgement.
- `AcceptedChatTaskDeadlineExceeded` is the existing accepted-work timeout
  contract. Preserve its terminal handling and completion truth.
- `asyncio.CancelledError` propagates after native provider cleanup and, when a
  run exists, durable failure audit. Do not convert cancellation into a successful
  tool result or leave a blocking provider thread running.
- `AcceptedKnowledgeReadUnavailable` or HTTP refusal means current ownership,
  credential scope/generation, manifest, permission or storage was unavailable.
  Do not retry through local/operator/legacy credentials. Any permitted retry
  must prepare fresh current authority and retain the same accepted task budget.

## Deliberately unfinished admission work

The real Preview app still omits public provider operation routes, so the current
public OpenAPI-backed manifest does not expose those operations. The private
invocation requires a valid exact manifest entry and refuses missing entries;
it does not fabricate them. A bounded private catalog/manifest integration is
needed that preserves Command Bus eligibility without promoting public routes.

Automatic tool exposure happens before there is a frozen tool command. The
invocation fence requires that frozen command/hash. A catalog-only canonical
account projection must therefore remain distinct from execution authority;
do not relax the execution resolver to accept missing command/hash custody or use
`task.user_id` as an independent account principal.

Keep Preview tool projection and worker admission quarantined until that wiring
has exact end-to-end tests. Required proof crosses authenticated acceptance,
queue acknowledgement race, frozen decision, private invocation, policy/audit,
result delivery and final model response. Include A/B tampering, duplicate/retry,
revocation and deadline/cancellation failures, plus unchanged imported-history
exclusions and existing history grants. Coordinate this interface with the
history/tool-loop owner rather than editing its source concurrently.

No new topology decision is needed for this interface. Deployment, real provider
consent/canary calls, credential provisioning and actual-ingress logging remain
separate operational gates, not implications of passing isolated tests.
