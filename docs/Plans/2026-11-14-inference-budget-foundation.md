# Inference budget foundation and activation gates

Status: **local implementation proposal with default-off bounded runtime integration; not deployed or activated**.
This is an architecture-impacting increment of the November 10 operator policy
proposal. It does not mark that proposal accepted, add a public operator API,
widen Beta/Preview release claims. Source migration metadata is updated without
claiming a live migration or activation.

## Pilot intent and funding assumptions

Per-account allowances are soft reconnaissance thresholds, not paid entitlements.
Provider-specific credits are not interchangeable cash. Anticipated grants are
not available capacity. The repository does not verify balances, expiry or
existing external consumption. No private operator balances or budget plans
are part of this public configuration or seeded into the database.

No real budget rows are seeded. A future operator configuration must separate
an aggregate monthly estimate ceiling from each provider's confirmed funding
envelope. A planning ceiling cannot admit spend above available funding.
Changing a monthly window never replenishes its funding envelope. Configuring
ceilings is not authorization to buy credits.

50/80/100 percent soft signals can inform operators without locking testers out.
Actual allowances and commercial margin targets remain unapproved. Rate/burst
limits, token bounds, monetary ceilings and customer pricing are distinct.

## This increment

`guardian/metering/budget.py` exposes an internal PostgreSQL-only primitive. It
has no route, worker hook, active configuration, provider invocation or cron.
Its three tables are added by `e723ba9046cd`, after `d8a90bf32107`.

- One fixed monthly pool (`provider='*'`) and one provider funding pool are
  locked in deterministic order and charged in one transaction. Pools share an
  operator payer scope. Values are integer USD nanounits, rounded upward.
- Canonical `ChatCompletionAttempt.accepted_account_id` and current thread owner
  must both match. Queue IDs and request headers are not accepted as ownership.
- The attempt ID deduplicates identical reservations; conflicting replays fail.
  Price version, source, effective time, resolved provider/model and token bounds
  form part of the immutable snapshot/digest. There is no backfill.
- A single durable claim permits at most one dispatch. Provider network activity
  must occur only after this transaction commits. Repeated claims do not dispatch.
- Only an unclaimed reservation can be released. Claimed timeout, cancellation,
  crash, partial usage or missing usage retains its entire hold indefinitely.
  No TTL silently invents zero spend. Reconciliation requires separate authority.
- Complete trusted provider usage settles against the original quote once.
  Conflicting terminal evidence fails. A mismatched reported model retains the
  hold instead of applying the wrong quote. Actual estimate overruns are recorded
  honestly; both new reservation and queued claim fail while a pool is over limit.
- Retiring/expiring a window stops future claims but does not erase liabilities or
  prevent settlement. The ledger does not modify sessions, users or transcripts.
- `soft_thresholds` is a pure reporting helper, not an enforcement decision.

No customer-hosted client may supply trusted prices, pool identities, provider
usage, or settlement amounts. Hosting location and inference payer are separate:
self-hosted customers buying managed inference require execution-side accounting
at the operator-owned service. That topology is not implemented in this slice.

## Authority and limits

Alignment: ADR-003 retains request/attempt identity; ADR-005 preserves account
custody; ADR-091 supplies durable accepted-work binding. No change is made to
ADR-112's quarantined connector invocation. This primitive introduces no new
public credential, entitlement or operator mutation authority. A reviewed
architecture decision is still needed for activation/configuration and dispatch
integration. The owner authorized local implementation/testing, not publication
or deployment in this assignment.

The transaction owner is the `BudgetLedger` session factory. Its methods commit
before returning and roll back failures. A database failure is not an admission.
Pool policy is trusted input to this internal API, not yet a validated activated
operator policy revision. Application invariants do not stop a privileged DB
operator from editing rows. The account ID is evidence rather than a cascading foreign key: deleting an
account must not erase its outstanding budget liability, and budget rows must not
block account deletion. A reviewed retention/anonymization policy remains a
pre-rollout gate. Settlement retains normalized content-free usage and provider
response identity alongside its digest; it does not retain prompts or raw responses.

Quoted USD estimates are not provider invoice totals or credit consumption.
External API usage, other nodes and uninstrumented paths are not covered. True
financial hard-cap guarantees require provider-side hard controls and complete
trusted ingress. A measured overrun proves the adapter's assumed upper bound was
wrong; the ledger records it and blocks further claims, but cannot undo that cost.

## Required before any claim of safe enforcement

1. Accept a bounded operator configuration/activation/retention contract, including
   actor audit and immutable policy revisions. Populate only confirmed funding,
   reconcile external consumption and provider-specific grant expiry.
2. Resolve the actual adapter/model before reserving. The inspected AI router
   normalizes some requested OpenAI model names to its configured default;
   pricing the Composer selection alone is insufficient. Add actual dispatch
   normalization and provider-reported alias tests at the integration seam.
3. Wire an exact bounded text-only route through admission, durable queue intent,
   claim and settlement. Recheck actual payload/output limits and current policy
   before network activity. Include retries, rescues, fallback and tool loops or
   reject them in enforcement mode. Do not let the observe-only fail-open hook
   stand in for admission. Unbounded or unpriced classes must fail closed.
4. Add durable recovery/reconciliation authority and content-free audit receipts;
   prove no ambiguous attempt can be repeated or released after a crash.
5. Run full repository CI and complete clean migration-chain rehearsal plus live
   backup/restore rehearsal. New-table roundtrip is narrower than all-migrations
   proof. Review independent security/accounting findings and account lifecycle.
6. Activate shadow comparison first, then an explicitly authorized controlled
   canary. Verify two-account isolation and continued history/export access.

## Verification scope

`tests/metering/test_inference_budget.py` uses an explicit disposable PostgreSQL
URL, creates a random schema and drops only that schema. It covers parallel pool
admission, single claim, replay conflicts, unknown liability, settlement overrun,
account custody, pool scope, quote provenance, model mismatch, expiry and the
new migration's table roundtrip. Existing metering/admin tests remain relevant.
See the task completion receipt for exact commands/counts. No live requests,
real-user probing, provider spending, production migration or deployment ran.

### Local verification receipt, 2026-11-14

- `pytest tests/metering tests/routes/test_metering_admin.py -x`: **19 passed**,
  one warning. New PostgreSQL cases ran, not skipped, using native PostgreSQL
  16.15 in a newly initialized socket-only disposable instance. Each test used
  a random isolated schema. No Docker daemon or production database was used.
- Full Alembic `upgrade head` in a separate empty disposable database reached
  `e723ba9046cd`; downgrade of only this revision to `d8a90bf32107` and re-upgrade
  succeeded. `alembic heads` returned one head. No policy rows were seeded.
- Ruff passed for the new service, tokens, migration and tests. Ruff on the full
  pre-existing `models.py` still reports its two unchanged unused metering-enum
  imports near line 38; this increment does not hide that baseline issue.
- `git diff --check` passed. Full repository CI, actual provider dispatch and
  frontend/live verification were not run.
- Independent source review found a claim-after-overrun defect; it was fixed
  and regression-tested. Review also prompted normalized settlement evidence
  and removal of the account-deletion-blocking foreign key. Follow-up source
  review found no further material issue within this bounded foundation, not
  a certification of future runtime integration.


## Second increment: bounded runtime integration

The foundation now has a default-off integration in the shared chat completion
service and actual provider HTTP choke point. **The preceding foundation-only
limitations do not mean this second increment is unwired; its remaining limits
are listed here.** Nothing was enabled in a real configuration.

`CODEXIFY_BOUNDED_OPENAI_BUDGET_JSON`, absent by default, accepts an exact object:
`mode` (only `enforce`), `payer_scope`, `monthly_window`, `funding_window`,
`max_output_tokens`, and `quote` with the foundation's provenance/rates. Optional
`account_allowances` maps canonical account IDs to positive USD-nanounit soft
thresholds. Unknown keys, malformed configuration and missing prices fail closed
for cloud inference. No budgets are created and no future grants are added.
There is deliberately no customer billing or public configuration mutation API.

The first supported guard is **only** pinned `gpt-4o-2024-08-06` text chat to
`https://api.openai.com/v1/chat/completions`. Model capability evidence is the
[official GPT-4o model page](https://developers.openai.com/api/docs/models/gpt-4o),
checked 2026-11-14: 128,000 context window and 16,384 maximum output. No provider
price is hard-coded or silently refreshed. This narrow choice is an internal
qualification slice, not an approved commercial model roster.

Reservation occurs at the final HTTP payload **after** router model normalization,
so a requested gpt-4.1 label mapped to the configured default cannot be charged
at the wrong requested-model rate. The actual model must be the pinned snapshot;
unpinned aliases are refused. Reserve the full documented model context ceiling
plus the explicitly capped output, not a guessed token count. Input is separately
bounded to 1,000 plain-role messages and a 128,000-byte serialized payload; that
is a size/abuse guard, not an assertion of exact tokenizer equivalence. Nonfinite
or out-of-range temperature, media, tool-bearing tasks/wire parameters, n>1,
streaming and unrecognized fields are refused before acquiring a hold.

The authenticated accepted request has one stable budget attempt ID, independent
of a newly generated worker attempt ID. Queue redelivery, ambiguous retries and
second tool/model calls cannot obtain a second claim. HTTP redirects are disabled;
the accepted-deadline HTTPX transport also uses its default no-redirect behavior.
Raw provider usage is settled before the legacy text adapter discards its response
envelope. Timeout, transport failure, non-2xx, malformed JSON and failed settlement
retain the hold. No automatic refund or paid retry is implemented.

Admission here happens **after durable queue acceptance but before any protected
paid dispatch**, not in the enqueue transaction proposed on November 10. An
accepted queued task can therefore fail budget admission. Acceptance is not a
promise of execution. This choice allows actual-payload validation and avoids
inventing unverified model/context bounds at enqueue; reservation-at-enqueue UX
and durable handoff/outbox work remain separate. No network is possible through
the guarded route until reserve and claim transactions commit.

Existing admin metering readback gains a separate `bounded_budget` section when
configured, containing current monthly/funding exposure and account soft signals.
Observed settled estimates and unresolved holds remain separate. The legacy
`accounts` section is still observe-only and can show unavailable usage for the
text-returning adapter; do not sum these two projections as separate charges.
This route retains its existing canonical account-admin authorization.

Unconfigured behavior is unchanged. Local inference remains under its existing
policy, even if this cloud-budget configuration is malformed. Other cloud providers
in the shared router are refused in this bounded mode. This is **not** a global
provider-key firewall: separately implemented SDK calls, embeddings, image/audio
services, customer gateways, external uses of the API key and other processes
are outside this proof. Before assigning a project-wide spending ceiling, isolate
this provider credential/project to the covered route or instrument every other
cost-producing path and verify provider-side protections. Hosting location does
not confer trusted settlement authority.

Still not activation-ready: operator policy approval/configuration/funding proof,
full CI, reviewed unknown-liability reconciliation and retention, deployment
backup/restore and two-account live canary remain required. Safe failure can
exhaust available holds after repeated ambiguous failures even when the provider
ultimately charged nothing. That is explicit conservative behavior, not evidence
that credits were consumed. No real provider request was used for qualification.

The runtime additionally binds the actual worker task ID and thread ID to the
durable request binding and includes a SHA-256 digest of the final wire payload
in reservation replay identity. No prompt text is persisted in this digest.
`accepted_at` is **not** an authorization prerequisite: ADR-091 writes that
receipt after publication, and a missing timestamp must not defeat otherwise
valid immutable custody. A dedicated regression covers that case.

The runtime review added preclaim temperature/size validation and tests for
actual timeout, transport error, non-2xx and malformed response, accepted-deadline
transport, and the shared `_execute_completion_attempt` path with the real
`PgDB._sa_session` transaction wrapper. HTTP is mocked throughout: this is local
code-path qualification, not provider consent, billing or deployed behavior.

Final second-increment local suite: **148 passed**, one warning, after the
acceptance-receipt compatibility correction. Command:

```sh
python -m pytest tests/metering tests/routes/test_metering_admin.py \
  tests/core/test_ai_router.py tests/core/test_chat_completion_service.py \
  tests/core/test_cloud_accepted_deadline.py \
  tests/core/test_chat_nonstream_accepted_deadline.py \
  tests/core/test_completion_terminal_integrity.py -x
```

`CODEXIFY_BUDGET_TEST_DATABASE_URL` pointed only to the disposable native
PostgreSQL instance; no opt-in budget cases were skipped. New and changed
metering/admin/test files passed Ruff; `git diff --check` passed. This was not
the entire repository CI suite. The first-increment migration receipt remains
applicable because the second increment did not change the migration/schema.

## Follow-up: spend-path inventory and legacy OpenAI quarantine

Source inventory at local `086a354` (not runtime proof) found independent paid
provider consumers outside `ai_router`. This increment **does not add billing
support** for them. With bounded mode configured, the following legacy OpenAI
entry points now refuse before network dispatch, including when called inside an
accepted chat context; malformed configuration also refuses:

- `guardian/providers/openai_adapter.py`: SDK chat, stream, embeddings.
- `guardian/memoryos/utils.py`: OpenAI memory chat.
- `guardian/memoryos/embedders/openai_embedder.py`: single/batch embeddings.
- `guardian/image_gen/providers/openai.py`: image generation used by media routes.
- `guardian/voice/service.py`: explicitly selected OpenAI transcription.
- `guardian/core/research/Modules/model/openai.py`: legacy completion and client /
  LLM-config exports. This legacy class shadows the SDK class; its usability is
  not established, and this change does not repair or claim it is publicly live.

Default-unconfigured behavior remains unchanged. Cached embeddings can still be
returned without paid work. These guards are deployment-wide and deliberately
**do not infer operator-funded versus BYOK** from a key or client assertion.
An explicit credential/payer boundary is required before exempting BYOK calls.

### Still outside the demonstrated budget boundary

| Surface | Source examples | Status |
| --- | --- | --- |
| Other provider adapters | `guardian/providers/{groq_adapter,groq_client,minimax_adapter,gemini_adapter}.py` | Direct SDK/HTTP spend, not covered by this increment |
| Other helper/memory clients | `guardian/core/groq.py`, `guardian/utils/groq_helpers.py`, GroqClient in `guardian/memoryos/utils.py` | Not covered |
| Other research wrappers | `guardian/core/research/Modules/model/{deepseek,gork,ollama}.py` | Legacy paths/configurable endpoints, reachability not proven |
| Voice | Deepgram STT in `guardian/voice/service.py`; `guardian/tts/providers/{deepgram,elevenlabs,minimax}_provider.py` | Not covered |
| Configurable “local” adapters | local Ollama/OpenAI-compatible chat, embeddings and speech URLs | Naming is not network/payer authority; remote paid endpoint substitution remains outside proof |
| Exported clients and plugins | SDK objects, arbitrary plugins/custom provider code, external workers | Cannot claim coverage from repository call-site guards |
| Same key used elsewhere | another process, deployment, CLI or customer-hosted reporting | No control; isolate operator-funded credentials/project or enforce through a gateway |

Search included Guardian, backend, services, plugins and scripts, using SDK and
HTTP call patterns. This is a reviewable static inventory, **not an exhaustive
runtime call graph or global egress firewall**. Provider aliases, arbitrary
endpoints and new code can introduce spend. No project-wide spending ceiling may be
advertised based on this patch. Managed inference from self-hosted customers
must enter a server-owned credential and admission boundary, not settle costs
from customer-supplied usage.

### Follow-up validation

24 new mocked tests passed for enabled/malformed configurations, inherited chat
context, pre-network denial, and unconfigured SDK behavior. A broader existing
regression run was stopped by execution review after attempting outbound access
to `api.deepseek.com`; it is not claimed as a passing suite. No external provider
call was authorized for this work. Lint on added runtime/tests is clean; existing
legacy research class redefinition and memory utility import violations remain
unchanged. No deployment, activation, provider-key changes or paid usage.

Independent source review confirmed guards precede provider calls and broad
exception handlers. Compatibility caveat: named OpenAI SDK adapters can accept
custom/local endpoints; enforcing this quarantine also disables those adapter
uses, even if locally funded or BYOK. Do not claim every local inference path is
unaffected. The separately named local adapters remain unchanged but need
endpoint and payer validation before any global-cap claim.

## Follow-up: broader named-cloud quarantine (still default-off)

The next increment extends refusal of unqualified spend to Groq SDK/HTTP and
vision helpers, Gemini SDK, MiniMax SDK/HTTP (including Anthropic-flavor paths
and generators), Groq memory chat, legacy Deepseek/Gork completion and client /
configuration exports, Deepgram STT/TTS (including per-chunk dispatch),
ElevenLabs TTS, Google Cloud TTS, and the deprecated standalone Gemini chat
handler. MiniMax TTS is a scaffold with no implemented synthesis call, not a
newly qualified paid route. Shared cloud HTTP now denies without accepted
budget context regardless of provider alias or custom endpoint, closing direct
cloud-adapter calls that did not enter `chat_with_ai`.

This supersedes the prior inventory's “not covered” entries for those named
call sites only. It does not qualify their prices, report them as metered, or
make the earlier local-endpoint/external-process limitations disappear.

There is no authenticated payer/credential binding in these legacy interfaces.
A caller-provided API key is not proof of BYOK. Rather than guess, configured
bounded mode refuses these named-cloud calls even when a customer might fund
them. In-process local inference and separately named local routes remain
unchanged, not certified free of downstream provider spend. Future mixed
funding requires server-owned credential identity and authorization, not secret
comparison, hostname classification, a provider label, or client usage reports.

Memory import caveat: `guardian/core/client_factory.py` imports the top-level
`memoryos` package. That name was absent from the implementation interpreter's
import resolution. Do not assume a different installed/live package contains
these guarded in-repository implementations; verifying module provenance is a
rollout prerequisite.

### Network-isolated regression procedure

`-p tests.support.budget_network_guard` is an opt-in Python DNS/socket tripwire:
it refuses non-loopback destinations and clears environment proxies. It is not
an OS network sandbox and cannot certify subprocess/native SDK networking,
pre-existing sockets or loopback relays. Provider tests use synthetic clients;
no paid call is authorized. The tripwire revealed two existing DeepSeek dispatch
tests lacked a model-index GET mock. They now return synthetic discovery data
while retaining their existing dispatched-payload assertions.

The named-provider/quarantine suite passed 218 cases. A larger combined run
encountered a Deepgram provider-registration failure that passes in isolation;
this test-order interaction is not claimed resolved. The separate core/router/
completion/deadline regression group passed 88 cases with the tripwire enabled.
Independent source review found no material flaw in the new pre-dispatch guards,
and its coverage/test caveats informed this increment.
The separate voice/routes group also passed 47 cases with the tripwire enabled.
These separate-group passes do not erase the combined-order failure above.

## Import-order resolution and launch review

The combined Deepgram registration failure is now resolved: eager runtime ledger
import caused a DB-model/TTS/provider import cycle whose exception was swallowed
by optional imports. Lazy ledger import plus deferred type annotations removes
that cycle. Three fresh-interpreter tests assert registration. The previously
failing combined group passed 210 tests after the fix, without weakening tests.
See `2026-11-14-inference-budget-coverage.md` for the explicit launch/authority
matrix and phased review recommendation. Additional named legacy Groq and remote
voice forwarding gaps found by integration review are denied in configured mode.
Final combined regression on this increment: **362 passed in 20.01s**, covering
provider quarantine, import order, providers, router/completion/deadline, voice
and voice routes under the Python network tripwire. No PostgreSQL migration or
live-provider rerun in this increment; prior isolated ledger/migration evidence
remains separately dated. Targeted runtime/budget/new-test lint is clean;
`guardian/voice/client.py` has a pre-existing unused Optional import.
