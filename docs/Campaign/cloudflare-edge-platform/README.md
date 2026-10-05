# Cloudflare Edge Platform Campaign

- Campaign ID: `CLOUDFLARE-EDGE-PLATFORM`
- Campaign status: active; architecture accepted; implementation not started
- Architecture status: **ACCEPTED 2026-10-04 by Resonant Jones** under [ADR-099](../../architecture/adr/099-cloudflare-edge-platform-boundary.md)
- Runtime status: no Cloudflare integration or release claim established
- Cost posture: `ZERO_NON_INFERENCE_SPEND`
- Current release truth: [00 Current State](../../architecture/00-current-state.md)
- Pricing/limits checked: 2026-10-04 against the linked Cloudflare product documentation. Recheck before every integration enables usage.

## Objective

Establish a bounded Cloudflare EdgeNode around Codexify's local-first runtime.
Cloudflare may supply commodity edge capabilities; Guardian, VaultNode,
Postgres, and existing Codexify contracts retain identity, authorization,
routing, canonical state, provenance, and release authority. This Campaign is
an implementation order, not permission to configure Cloudflare or spend.

The governing invariant is `ZERO_NON_INFERENCE_SPEND`: no additional
non-inference infrastructure spend without explicit operator approval.
Inference remains separately governed by existing approved provider budgets.
Free allocations are ceilings to respect, not evidence of guaranteed
availability; usage-based overage requires a Codexify-owned hard guard before
production use. Cloudflare alerts are observability and do not cap spend.

## Service disposition

`ADOPT_NOW` means the product belongs in the intended platform foundation and
may proceed through its listed future slice. It does not mean configured,
deployed, enabled, or supported today. `IMPLEMENT_GATED`, `BENCHMARK_ONLY`,
and `PARK` require the listed gate or demonstrated need. Every row remains
subject to ADR-099 and the zero-spend invariant.

| Cloudflare product | Disposition and planned Codexify role | Authority classification | Free allocation / current cost posture (checked 2026-10-04) | Can usage exceed free into billing? | Codexify hard guard? | Secret class / allowed data sensitivity | Current state | Required proof / owning slice |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Workers | **ADOPT_NOW** — public HTTP edge adapter, normalization, correlation, admission, cacheable public output, service bindings, webhook ingress | Transient request execution only; no identity or policy authority | Free: 100,000 requests/day and 10 ms CPU/invocation; excess free requests/CPU fail with quota errors; Workers Paid is at least $5/month | No automatic Free overage; Paid plan adds usage billing | Yes: fail closed for security routes; never bypass edge on quota exhaustion | Worker secrets server-side; public/cache-safe data only by default | Not integrated | Deploy/health/correlation, secret isolation, quota failure and logs; CE-01 |
| Workers VPC | **ADOPT_NOW** — private path from Worker to one governed Guardian capability | Transport only | Free during open beta as of 2026-10-04; standard Workers plan pricing applies to requests/compute; beta APIs/terms may change | VPC itself is free during beta; Worker compute can bill on Paid plan | Yes before any billable or private access | Service credential/capability; no raw database, Redis, LAN, filesystem, model, or operator access | Not integrated | Reach only a single bounded capability; prove network isolation; CE-02 |
| Cloudflare Tunnel | **ADOPT_NOW** — separately scoped private transport endpoint for the capability bridge | Transport only | Existing Tunnel pricing/plan and topology must be rechecked; no current tunnel mutation authorized | Plan/feature-dependent | Yes; separate tunnel/service boundary, explicit route allowlist | Tunnel secret and server-held Guardian auth; private capability payload only | No Workers VPC integration established | Prove only intended endpoint reachable; existing ingress unchanged; CE-02 |
| R2 | **ADOPT_NOW** — remote binary/object tier behind existing object-storage abstraction | Object bytes only; Postgres owns metadata/owner/lifecycle/provenance | Standard tier: 10 GB-month, 1M Class A and 10M Class B ops/month included; internet egress free | Yes: storage/operations have usage-priced overage | **Required before live traffic**; explicit class-level capacity/quota and spend posture | Scoped service credentials; approved binary classes only; no authority in locators | No adapter | Hash/reference/readback/delete, owner checks, failure isolation and capacity guard; CE-03 |
| AI Gateway | **ADOPT_NOW** — inference transport telemetry under Guardian routing | Transport/telemetry only; no route or credential authority | Core gateway features free; Free persistent log capacity is limited. BYOK preferred. Unified Billing requires prepaid credits and has a 5% credit purchase fee. Spend limits are available but eventually consistent | Inference provider is billed under its own approved budget with BYOK; Unified Billing spends Cloudflare credits | Yes: enforce BYOK/credential-required path, prevent fallback, apply existing inference limits; Cloudflare spend limits are defense-in-depth, not a hard cap | Provider key remains Guardian/server-side; disable private payload logging by default | No integration | Same selected provider/model; sanitized correlation, no payload logs, no fallback; CE-04 |
| Workers Logs / Cloudflare Observability | **ADOPT_NOW** — edge failure, latency, quota and transport visibility | Telemetry only; not Codexify audit/completion truth | Workers Logs Free allocation: 200,000 log events/day, 3-day retention; plan and service limits can change | Paid plans/extra log features can bill | Yes for paid sink/features and volume guard where usage can bill | Minimized operational metadata; never raw secrets or private prompts by default | No integration | Correlation with canonical attempt, minimization, retention and failure visibility; CE-01/02 |
| Turnstile | **ADOPT_NOW** — bot/admission signal for future public unauthenticated forms | Admission evidence only; not authentication or authorization | Free plan; unlimited challenges and up to 20 widgets | No metered challenge overage on Free; Enterprise features are separately priced | No usage meter guard; token verification and admission policy are mandatory | Public sitekey; server-only secret; challenge metadata only | No integration | Server-side Siteverify; invalid, expired and replay rejection; no login substitution; CE-05 |
| Queues | **IMPLEMENT_GATED** — buffer edge-originated retryable non-chat work | Transport/work admission; no completion truth | Workers Free: 10,000 operations/day; Paid includes 1M/month then $0.40/million | Yes on Paid plan | Yes before Paid use; remain inside Free quota and fail closed | Queue messages carry opaque IDs/minimum metadata; no secrets/private payload by default | No integration; Redis remains chat queue | One justified non-chat workload; enqueue/retry/idempotency/dead-letter/terminal reconciliation; CE-07 |
| Workflows | **IMPLEMENT_GATED** — durable orchestration for naturally edge-owned process | Edge workflow execution state only | Workers Free: 3,000 steps/day, 1 GB-month state; shares Workers request and CPU limits | Yes on Paid plan/overage | Yes; usage bound before enablement | Minimized, scoped workflow input; no credentials in durable state | No integration | One edge-owned lifecycle; restart/retry/idempotency and Guardian reconciliation; CE-08 |
| Durable Objects | **IMPLEMENT_GATED** — temporary presence/session/rate coordination where needed | Coordination only; SQLite-backed storage only on Free | Free: 100,000 requests/day, 5M rows read/day, 100K rows written/day, 5 GB total SQLite; Free limits fail closed | Yes on Paid plan; paid storage/compute dimensions | Yes for paid usage; retain only temporary state and set bounds | Opaque session IDs and minimized ephemeral state | No integration | Demonstrated edge coordination need; expiry, replay and partition behavior; CE-09 |
| Hyperdrive | **IMPLEMENT_GATED** — optional connection pooling for a proven bounded Worker-to-DB use | Connection pooling, not authorization or a database API policy | Workers Free: 100,000 database statements/day; excess Free operations fail | Yes on Paid plan; origin database may have separate charges | Yes before paid or direct DB access; default to Guardian API | DB credential stays in Cloudflare/server secret store; only approved query surface | No integration | Show Guardian API is insufficient; prove query scope, fresh auth reads and quota failure; no slice assigned until justified |
| KV | **IMPLEMENT_GATED** — edge cache/public config/temporary non-security lookup | Non-authoritative cache/config only | Free: 100,000 reads/day, 1,000 writes/day, 1 GB; excess Free operations fail | Yes on Paid plan | Yes for paid use; no security decision may rely on stale cache | Public or low-sensitivity non-security metadata only | No integration | TTL/invalidation, stale-read safety, outage behavior and no authority reads; separate task if justified |
| Browser Run | **IMPLEMENT_GATED** — screenshot, rendering, extraction and bounded browser utility provider | Untrusted execution output; Browser Host ownership remains separate | Free: 10 browser-minutes/day and 3 concurrent Browser Sessions | Yes on Paid: 10 hours/month included then $0.09/hour; concurrent browsers also billed above plan allocation | Yes before paid; enforce task/time/concurrency bounds | No secrets/private account data by default; public web content is untrusted | No integration | Provider-neutral browser capability, close/session limits, output provenance and isolation; CE-10 |
| Workers AI | **IMPLEMENT_GATED** — one utility-inference class through provider governance | Inference output only; Guardian owns route and authority | Free: 10,000 neurons/day; excess Free fails. Workers Paid starts at $5/month; usage above allocation costs per-model rate (published baseline $0.011/1,000 neurons) | Yes on Paid; some models require Paid | Yes; require explicit approved inference budget/model and no hidden call | No secret exposure; approved/minimized input class only | No integration | Provider identity, actual model, budget/failure policy and route proof; CE-12 |
| AI Search | **IMPLEMENT_GATED** — derived index/search provider or benchmark, never memory authority | Derived retrieval only | As of 2026-10-04: 5M ingestion tokens/month, 10 GB-month, 1,000 semantic and 1,000 full-text queries included. GA 2026-10-01; usage billing starts 2026-11-01; overage rates published | Yes after included amounts; billing starts Nov 1, 2026 | **Required before production ingestion/query**; explicit quota and corpus boundary | Benchmark corpus must be non-sensitive; no private account content by default | Not integrated | Recall/ranking/provenance/latency/filtering/OCR/cost compare; no promotion to memory authority; CE-11 |
| Web Search API (Ceramic / Exa / Linkup) | **IMPLEMENT_GATED** — Guardian-routed external Web `search` provider | Untrusted external evidence only | Usage-priced through AI Gateway credits at provider list rates: Ceramic $0.25/1K, Exa $7/1K, Linkup $5/1K requests; BYOK bills provider directly | Yes; live search is not zero-cost | **Required before live requests**; disabled by default under zero-spend policy | Query and response may contain sensitive material; minimize/redact; results are untrusted | No integration | Canonical result shape, source/provider provenance, local/global scope, disabled-cost proof; CE-06 |
| Vectorize | **BENCHMARK_ONLY** — edge vector-search/retrieval comparison | Derived index only | Current included/overage allocation must be rechecked before any workload; no spend assumed | Product/plan-dependent | Yes before non-benchmark production use | Non-sensitive benchmark corpus only | No integration | Demonstrate material retrieval or latency advantage; no parallel production index by default; future evaluation |
| D1 | **BENCHMARK_ONLY** — isolated edge-owned dataset experiment only | Isolated edge data; no canonical app-table mirror | Workers Free includes daily row quotas; Paid overage is usage-priced; verify exact current values for any benchmark | Yes on Paid | Yes before any persistent workload beyond bounded experiment | Synthetic or explicitly non-sensitive data | No integration | Prove actual edge-owned domain need and non-overlap with Postgres; no slice assigned |
| Workers Analytics Engine | **BENCHMARK_ONLY** — edge telemetry query experiment | Telemetry only; no audit authority | Cloudflare published Free allocations of 100K writes/day and 10K read queries/day; as of 2026-10-04 provider states it is not yet billing | Provider says future billing is planned; can change | Recheck billing start and enforce budget before production dependence | Minimized telemetry, no private prompts/secrets | No integration | Compare an actual operator query against current surfaces and quantify operational value; CE-13 |
| Realtime SFU/TURN | **PARK** — future voice/video/session media transport when product demand exists | Media transport/session state only | First 1,000 GB egress/month free, then $0.05/GB | Yes | Yes before exceeding free allocation; no service until product need | Media is sensitive; explicit consent, retention and session policy required | No integration | Product use case, media privacy, session identity separation, and cost guard; CE-14 |
| Email Routing | **PARK** — inbound mailbox only when a concrete intake/support use exists | Transport into governed ingestion; email is untrusted input | Inbound Email Routing currently free; recheck terms and downstream delivery costs | Cloudflare routing itself is free under current terms; downstream processing can cost | Guard downstream execution/processing; never treat mail as commands | Incoming content is untrusted; isolate attachments and sender evidence | No integration | Identified mailbox owner and governed ingestion path; separate future task |
| Arbitrary-recipient Email Sending | **PARK** — future outbound notification adapter | Delivery only; no user or approval authority | Workers Paid required ($5/month minimum); current included allowance is 3,000 outbound/month then $0.35/1,000 | Yes / requires Paid | Yes and explicit operator approval | Server-held sending credentials; minimize message content | No integration | Separate provider/identity/retry/consent contract and spend approval; no current slice |
| Containers | **PARK** — disposable processor/MCP/converter only if a workload proves need | Isolated compute, not execution authority | Workers Paid required ($5/month minimum) plus usage-based compute/storage/egress after included amounts | Yes | Yes; require task-specific budget and sandbox/credential boundary | No ambient credentials; untrusted input isolation | No integration | Concrete workload, resource isolation and ADR-077 alignment; no current slice |
| R2 Data Catalog / Pipelines / specialized data products | **PARK** — future analytics/data-lake workload | Derived analytics state only | Product-specific included allocations and usage prices; no allocation assumed here | Likely product/usage dependent; recheck before any use | Yes before creation or traffic | Only governed analytics corpus; no authority promotion | No integration | Named workload and owner; separate cost and data-governance review |

## Cost and authority gates

1. No Cloudflare resource, paid plan, billing credit, or provider key is
   created or enabled by this Campaign document.
2. For any Free capability, record the relevant request, CPU, storage,
   operation, retention, and concurrency ceilings. Treat provider quota
   errors as failures; do not silently retry through a paid surface.
3. For any usage-based product, the owning task must define a Codexify-owned
   hard guard with a safe exhausted state before live production use. A
   dashboard alert, estimate, or payment-method absence is not a guard.
4. Inference cost remains a separate budget domain. BYOK preserves provider
   credential ownership; AI Gateway Unified Billing, credits, Workers AI
   overages, and provider fallback are never enabled implicitly.
5. Web Search live use is disabled by default. Tests must use mocks or
   provider-disabled configuration until the operator explicitly approves
   the applicable spend and policy.
6. For private user content, record data class, owner/scope, retention,
   deletion/export behavior, and retrieval eligibility before sending it to
   Cloudflare. Public infrastructure does not make private data public-safe.
7. Every task rechecks official product docs. The figures below are snapshots,
   not enduring guarantees. In particular, AI Search billing starts
   2026-11-01; its published included amounts and overage schedule have been
   noted in advance of that start date.

## Dependency order

```text
CE-01 Workers EdgeNode
  |
  v
CE-02 private Guardian capability bridge
  |\
  | +--> CE-03 R2 object adapter
  | +--> CE-04 AI Gateway transport
  | +--> CE-05 Turnstile admission
  | +--> CE-06 gated Web Search provider
  +----> CE-07 one non-chat Queue workload
           |
           v
         CE-08 edge-owned Workflow
           |
           +--> CE-09 Durable Object only if needed
           +--> CE-10 Browser Run provider
           +--> CE-11 AI Search benchmark
           +--> CE-12 Workers AI provider
           +--> CE-13 Analytics Engine evaluation

CE-14 Realtime media waits for product demand.
```

CE-03 through CE-06 can proceed independently after CE-02 when each owning
adapter and spend gate is self-contained. CE-07 is independently gated on a
real non-chat workload and CE-08 depends on its handoff/idempotency contract.
CE-09 requires a demonstrated coordination need after the earlier boundary
work. CE-10 through CE-13 are optional independent evaluations once the base
edge and capability boundaries exist. CE-14 is demand-driven, not a required
predecessor to Campaign closure.

## Atomic future slices

All entries below are deferred. Each needs a separate task dispatch with
scope, changed-file allowlist, current external limit review, and proof plan.
CE-01 is the next eligible slice after ADR-099 acceptance, but has not been
authorized or started by this acceptance task.

| Slice | Scope and dependency | Required proof / stop condition |
| --- | --- | --- |
| **CE-01 — Edge foundation** | One minimal Worker as EdgeNode; first implementation slice | Deploy and health; correlation ID; secret handling; logs; fail-closed quota behavior; no Guardian authority migration. No R2, Queue, AI, database, or runtime changes beyond the slice. |
| **CE-02 — Private capability bridge** | One Workers VPC/private Tunnel path to one narrow Guardian health/capability endpoint; depends on CE-01 | Worker can reach only the bounded service; prove private/public access policy; arbitrary private network access is unavailable; Guardian authentication remains authoritative. |
| **CE-03 — R2 object-storage adapter** | One binary artifact class behind existing object-storage abstraction; depends on CE-02 | Postgres metadata/ownership, stable locator and content hash, readback/delete lifecycle, R2 failure does not corrupt canonical metadata, application capacity guard. |
| **CE-04 — AI Gateway transport** | Route one existing cloud inference provider through AI Gateway; depends on CE-02 | Same Guardian-selected provider/model; BYOK; payload logging disabled; safe telemetry; no Cloudflare fallback/routing override; legible failure. |
| **CE-05 — Edge admission** | Apply Turnstile to one public unauthenticated/admission surface; depends on CE-02 and an identified surface | Server-side token verification; reject replay/invalid token; preserve authentication and authorization boundaries; never attach to ordinary authenticated local chat. |
| **CE-06 — External Web Search adapter** | Cloudflare Web Search behind ADR-021 Guardian retrieval; depends on CE-02 and separate cost policy | Mock/provider-disabled tests prove result shape, provider/source provenance, router integration, local/global scope and disabled-cost posture. Live requests require separate explicit spend approval. |
| **CE-07 — Edge async lane** | One non-chat workload on Queues; depends on CE-02 and a demonstrated workload | Enqueue acceptance, retry, duplicate/idempotency behavior, terminal outcome, Guardian reconciliation, and failure isolation. Do not change Redis chat semantics. |
| **CE-08 — Durable edge workflow** | One naturally edge-owned multi-step process; depends on CE-07 | Restart/retry/timeout behavior, external side-effect idempotency, cancellation/terminal outcome, and Guardian reconciliation. Do not duplicate Campaign Engine or Flow Builder. |
| **CE-09 — Durable Object coordination** | One temporary edge-coordination use, only when CE-01–08 reveal a real need | Presence/session/rate state expires and cannot become account or Project authority; prove duplicate, partition and eviction behavior. If no need exists, close as `PARK`. |
| **CE-10 — Browser Run provider** | Bounded provider-neutral browser utility; depends on CE-02 | Browser Host authority remains distinct; task/time/concurrency bounds; close sessions; untrusted output and source provenance; Free allocation or approved hard cost guard. |
| **CE-11 — AI Search retrieval benchmark** | Safe non-sensitive benchmark corpus; depends on retrieval baseline and CE-02 | Compare recall, ranking, provenance, latency, filtering, OCR/multimodal capability, operations and cost against Codexify retrieval. No promotion to user memory. |
| **CE-12 — Workers AI utility provider** | One utility-inference class via normal provider governance; depends on provider baseline | Requested/actual provider and model; approved inference budget; isolated failure policy; no hidden Worker call or route bypass. |
| **CE-13 — Edge analytics evaluation** | Compare Analytics Engine with Codexify operator/audit surfaces; depends on CE-01 telemetry baseline | Demonstrate a useful edge-specific query or removed operational burden, data minimization and current billing posture. Otherwise close as `BENCHMARK_ONLY`/`PARK`. |
| **CE-14 — Realtime media** | Evaluate SFU/TURN only when ThreadSpace/live voice/video has a concrete product need | Consent, identity/session ownership, retention, failure modes and cost guard; compare managed Realtime before operating custom TURN/SFU. If no demand, remain `PARK`. |

## Priority

- **Priority A — edge foundation:** Workers, Workers VPC/private transport,
  R2, AI Gateway, observability, and Turnstile. All remain future,
  independently gated changes.
- **Priority B — governed capabilities:** Web Search, Queues, Workflows, and
  Browser Run.
- **Priority C — Cloudflare-specific experiments:** Durable Objects, AI
  Search, Workers AI, and Analytics Engine.
- **Priority D — product-demand or paid workloads:** Realtime, Email Routing,
  arbitrary-recipient Email Sending, Containers, and specialized data
  products.

## Campaign stopping condition

The Campaign closes when the bounded Worker is proven; VaultNode is reachable
only through governed private capabilities; the chosen object tier keeps
canonical metadata elsewhere; AI Gateway provides useful inference telemetry
without taking routing authority; relevant public admission surfaces have
appropriate Turnstile protection; external Web Search is available only
behind explicit spend policy; at least one justified non-chat Queue/Workflow
path is proven; optional products have a demonstrated use or an explicit
`PARK`/`BENCHMARK_ONLY` disposition; and there is no unresolved parallel
authority or uncontrolled non-inference spend path.

The Campaign does not require every Cloudflare product. A deliberate
`PARK`/`BENCHMARK_ONLY` close is valid. Architecture acceptance, implementation
completion, live proof, deployment qualification, Beta support, and release
claims remain separate decisions.

## External references

Official Cloudflare documentation checked 2026-10-04:

- [Workers pricing and platform limits](https://developers.cloudflare.com/workers/platform/pricing/) and [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- [Workers VPC pricing](https://developers.cloudflare.com/workers-vpc/reference/pricing/) and [VPC service model](https://developers.cloudflare.com/workers-vpc/)
- [Email Service pricing](https://developers.cloudflare.com/email-service/platform/pricing/)
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [Queues pricing](https://developers.cloudflare.com/queues/platform/pricing/)
- [Workflows pricing](https://developers.cloudflare.com/workflows/platform/pricing/)
- [Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- [Hyperdrive pricing](https://developers.cloudflare.com/hyperdrive/platform/pricing/)
- [AI Gateway pricing](https://developers.cloudflare.com/ai-gateway/reference/pricing/), [Unified Billing](https://developers.cloudflare.com/ai-gateway/features/unified-billing/), [limits](https://developers.cloudflare.com/ai-gateway/reference/limits/), and [spend limits](https://developers.cloudflare.com/ai-gateway/features/spend-limits/)
- [Web Search providers and current request rates](https://developers.cloudflare.com/web-search/providers/)
- [AI Search limits and pricing](https://developers.cloudflare.com/ai-search/platform/limits-pricing/) and [2026-10-01 GA notice](https://developers.cloudflare.com/changelog/product/ai-search/)
- [Browser Run pricing](https://developers.cloudflare.com/browser-run/pricing/)
- [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Turnstile plans](https://developers.cloudflare.com/turnstile/plans/)
- [Realtime SFU pricing](https://developers.cloudflare.com/realtime/sfu/platform/pricing/)
- [Workers Analytics Engine pricing](https://developers.cloudflare.com/analytics/analytics-engine/pricing/)

These links support the dated provider facts, not Codexify integration,
authorization, reliability, or release claims. Verify availability, rates,
limits, billing start dates, and plan requirements again before each slice.
