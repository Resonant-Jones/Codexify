# Bounded metering: launch coverage and phased review

Status: local implementation, default off; no deployment or credential changes.
This is source integration review plus local tests, not an inventory of current
live processes or a production qualification receipt.

## Launch and authority coverage

Main API `guardian/guardian_api.py` mounts canonical chat, simple/API chat,
media and voice routers. Admission authority is the canonical accepted-account
binding, not a UI-selected provider, account string, or imported chat content.

| Surface / launch path | Configured bounded mode | Evidence / remaining limit |
| --- | --- | --- |
| Canonical chat completion → queue → `chat_completion_service._execute_completion_attempt` → shared router → pinned OpenAI text call | **Guarded**: atomic reserve/claim, exact final model and quote, raw-usage settlement; unknown liability retained | PostgreSQL and mocked dispatch evidence from prior phase. Budget admission is after queue acceptance, before provider spend. Narrow text-only contract, not tools/media/streaming. |
| Direct shared cloud adapters, including custom provider URLs | **Denied** without accepted context; with context only the exact qualified OpenAI endpoint/payload can dispatch | Final cloud HTTP guard does not infer authority from hostname or alias. |
| Simple chat legacy Groq path via `core.dependencies._groq_complete` | **Denied** before its retry-capable HTTP helper | Added explicit guard after integration review found this separate entry. Existing route may echo fallback after denial, not successful inference. |
| Legacy OpenAI/Groq/Gemini/MiniMax adapters; memory chat/embeddings; research SDK wrappers | **Denied** before calls / generator iteration / client exports | No secondary SDK call can inherit a chat reservation. These operations are not newly metered. Optional externally installed `memoryos` package remains a separate provenance gate. |
| Media route → ImageGenRouter → OpenAI image adapter | **Denied** | Route reachability inspected; no image price/model contract approved. |
| Voice routes → voice client → local service → OpenAI/Deepgram STT or Google/ElevenLabs/Deepgram TTS | **Denied** at named cloud operation, including Deepgram chunks | Local/mock providers remain available subject to existing configuration. MiniMax TTS remains an unimplemented scaffold. |
| Voice client → configured remote voice service | **Denied** before forwarding | Independent service credentials/configuration cannot be trusted by the caller's budget guard, even with loopback URL. No silent exemption based on destination name. |
| In-process local embedding/model compute | **Unchanged**, not billed by this ledger | Local execution is distinct from paid API spend. Model downloads and infrastructure costs are not API-inference metering. |
| “Local” compatible HTTP routes / Whoosh'd sidecars | **Outside proof** | Configurable endpoints/sidecars may proxy paid providers; a local label or loopback address does not prove payer ownership or zero cost. |
| Agent orchestration → Codex CLI/app-server executor; plugins/TTS plugin invoke | **Out of process / outside proof** | Separate authentication, process environment and spend authority; no claim that this in-process ledger bounds them. |
| Customer-funded BYOK through legacy named-cloud adapters | **Denied conservatively** | No secure credential-to-payer binding exists here. Supplying a key does not prove customer funding. Separate local paths are unchanged, not granted a BYOK exemption. |
| Same operator key/project used by another process, deployment, CLI or customer | **Outside proof** | Must isolate credentials or enforce at a server-owned gateway before a project-wide ceiling claim. Self-host reports cannot authorize or settle operator funds. |
| Reading account content, exporting, ordinary provider OAuth configuration | **Not inference-budget gated** by this patch | Existing auth/security policies remain. No database access is granted by a reservation. |

## Resolved import-order defect

The initial quarantine work imported BudgetLedger eagerly through runtime. This
cycled through DB models → TTS package → provider guard imports while runtime
was partially initialized. Optional-provider imports swallowed the exception,
so Deepgram silently disappeared depending on test import order. This was a real
integration defect, not merely an unreliable assertion.

The ledger is now imported lazily only when constructing a DB-backed accepted
context. Its annotation is type-only with deferred evaluation. Fresh-interpreter
regressions import runtime, DB models or Deepgram first and assert actual provider
registration. Network sockets are denied inside those child interpreters.

## Reviewable phases

1. **One inactive implementation PR:** ledger/schema, bounded dispatch,
   quarantine, import-order fix, tests and scope documentation together. Do not
   activate an intermediate foundation-only commit. Review migration and account
   custody, money units, quote/model truth, unknown liability, replay behavior,
   import graph and local/BYOK compatibility. Reconcile with current main in an
   isolated branch and run required CI before merge. No published PR yet.
2. **Operator credential boundary and rollout proof:** inventory actual processes
   and deployed imports; isolate the operator-funded provider project/credential
   to qualified dispatch or enforce via an owned gateway. Decide how external
   executors/local proxies and legitimate BYOK are separated. Add trusted payer
   identity and reconciliation operations rather than inferring from keys/URLs.
3. **Pilot activation:** verified available funding and expiry, actual approved
   provider quote/model, fresh backup/restore and migration rehearsal, concurrent
   reservation canary, two-account isolation and failure/unknown-usage tests,
   clean rollback, operator-visible exposure/soft thresholds. Never count the
   anticipated grant before confirmation. No commercial margin claim without
   revenue, overhead and observed cost evidence.

The package is reviewable as inactive engineering work. It is not yet a complete
project-wide monthly spending protection or a ready-to-enable production pilot.
