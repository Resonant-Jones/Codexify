# ADR-099: Cloudflare Edge Platform Boundary

- Status: Accepted
- Date: 2026-10-04
- Accepted: 2026-10-04
- Human approver: Resonant Jones
- Governing anchors: ADR-021, ADR-041, ADR-061, ADR-067, ADR-071, ADR-075, ADR-081, ADR-093, ADR-094, and `00-current-state.md`.
- Companion Campaign: [Cloudflare Edge Platform Campaign](../../Campaign/cloudflare-edge-platform/README.md).
- Decision authority: Resonant Jones explicitly accepted this architecture on 2026-10-04. Acceptance covers this boundary only; it authorizes no runtime or Cloudflare configuration work.

## Context

Codexify may use Cloudflare as commodity edge infrastructure around its
local-first runtime. The intended direction is to place a bounded edge layer
between Internet-facing clients and Codexify's governed capability boundary,
not to move Codexify into Cloudflare. A Worker's network position does not
grant it account, Project, Thread, memory, routing, or execution authority.

Cloudflare adoption crosses public and private transport, object storage,
queues and workflows, inference transport, retrieval, browser execution,
realtime media, credentials, privacy, cost, and operator truth. Existing
contracts already assign these semantic domains to Codexify components.
Product-specific adapters must remain subordinate to those contracts and may
not create parallel authority.

### Current truth and evidence boundary

- `docs/architecture/00-current-state.md` remains the short-horizon release
  authority. Local Docker Compose remains the supported Beta path.
- VaultNode remains canonical runtime and audit authority under ADR-041;
  Guardian owns routing, authorization, policy, context, and durable
  provenance. Postgres owns canonical application state. Redis remains the
  current operational queue/lock/task-event coordination surface.
- Object storage is a storage class, not relational or account authority.
  Vector/index stores are derived retrieval state. Connections is a
  control-plane projection, not execution authority.
- No Cloudflare runtime integration or release support is established by
  this ADR. The current absence of each adapter must be confirmed in code
  before an implementation task makes a more specific claim.
- Cloudflare limits and prices in the companion Campaign are external,
  mutable evidence checked on 2026-10-04. Each implementation task must
  recheck the provider's current documentation before enabling usage.

## Decision

### 1. Cloudflare is a subordinate EdgeNode provider

Cloudflare products may provide edge compute, transport, storage, buffering,
temporary coordination, telemetry, external evidence, browser execution,
realtime media, and optional inference behind Codexify-owned interfaces.
Cloudflare is not Guardian, VaultNode, the Codexify identity provider, the
canonical application database, or the release authority.

Conceptual topology:

```text
Client / Internet
        |
        v
Cloudflare EdgeNode capabilities
  Worker / Turnstile / optional DO, Queue, Workflow
  R2 / AI Gateway / Search / Browser Run / Realtime
        |
Workers VPC and separately scoped private transport
        |
        v
Guardian capability boundary
  routing / authorization / policy / provenance
        |
        +--> VaultNode and Postgres
        +--> Redis operational coordination
        +--> approved providers and derived stores
```

The threat model includes honest-but-buggy services, malicious remote
content or peers, compromised edge components, replay and duplicate delivery,
stale policy, quota exhaustion, partial partitions, and metadata exposure.
Cloudflare request identity is not Codexify account identity. VPC/Tunnel
reachability is transport, not capability authorization. Remote edges must
use authenticated, narrowly scoped, idempotent Guardian capabilities and
bounded retries/backpressure; unavailable or ambiguous authority fails
closed. No edge component may address raw LAN, filesystem, database, Redis,
model-server, or operator ports as a substitute for a capability API.

### 2. Canonical authority remains Codexify-owned

| Service | Permitted state or role | Canonical Codexify authority |
| --- | --- | --- |
| Workers | Transient request handling and public edge adaptation | No |
| Workers VPC / Tunnel | Private capability transport | No |
| R2 | Binary/object bytes | No relational, account, ownership, or lifecycle authority |
| KV | Cache and non-security-critical configuration | No identity, permissions, ownership, credentials, messages, or memory |
| D1 | Isolated edge-owned data, if later justified | No existing canonical application domain |
| Durable Objects | Temporary/distributed edge coordination | No Project, account, conversation, memory, or permanent permission authority |
| Queues | Message transport and work admission | No completion or ownership truth by itself |
| Workflows | Edge-owned workflow execution state | No Guardian or application authority |
| Hyperdrive | Bounded connection pooling if approved | No independent database authorization or routing authority |
| AI Gateway | Inference transport and telemetry | No provider/model selection, credential ownership, or Guardian routing authority |
| Web Search | External web evidence | No canonical state; results remain untrusted evidence |
| AI Search / Vectorize | Derived retrieval indexes | No canonical memory or document authority |
| Browser Run | Bounded browser execution | No Browser Host ownership or trust promotion |
| Workers AI | Optional inference output | No hidden routing or durable mutation authority |
| Realtime SFU/TURN | Media transport and temporary session state | No conversation identity, ownership, or durable history |
| Workers Analytics Engine / Logs | Operational telemetry | No audit authority or canonical completion truth |

Postgres remains authoritative for canonical metadata, ownership,
relationships, lifecycle, and provenance. R2 object existence or a locator
does not grant access. Signed object URLs, if separately approved, must be
scoped and expiring. Queue receipt is not task ownership, acceptance is not
completion, Workflow state is not Campaign Engine state, and Durable Object
identity is not account or Project identity. Promotion of any Cloudflare
store into an existing canonical Codexify domain requires a new architecture
decision before implementation.

### 3. Retrieval and inference remain under Guardian policy

Local retrieval and request scope remain governed by ADR-004, ADR-021, and
applicable memory/document contracts. Cloudflare Web Search is an external
`Web search` provider behind Guardian's retrieval/router boundary. It remains
disabled by default under the zero-non-inference-spend posture. Returned
pages and snippets are untrusted evidence, never instructions or canonical
state; preserve source URL, selected provider, request lineage, and existing
provenance. External search may not silently broaden account, Project, or
Thread scope.

AI Search and Vectorize are derived retrieval providers. Private Codexify
account knowledge is not uploaded by default. Any later user-content use must
prove explicit scope, account isolation, provenance, deletion, export/restore,
failure behavior, and a spend guard before production traffic.

Guardian remains the canonical inference router under ADR-093 and
ADR-094. AI Gateway may observe or transport the provider/model route Guardian
selected; it does not select or substitute that route, authorize a credential,
or change execution placement. Initial AI Gateway use is BYOK where compatible,
with payload logging disabled by default for private Guardian traffic and
sanitized request/attempt metadata used only when safe. Unified Billing is
disabled by default. Workers AI is an optional governed provider and must
enter through existing provider/capability/routing policy; no arbitrary
Worker may make an invisible inference call or mutate Guardian semantics.

### 4. Queue and workflow semantics remain separated

Cloudflare Queues may buffer edge-originated, retryable non-chat work after a
separate implementation task defines its event contract, idempotency key,
backpressure, dead-letter/terminal outcomes, and Guardian reconciliation.
Queues do not replace Redis chat-completion semantics, including turn
ownership, cancellation, task events, heartbeats, acceptance, and transcript
integrity. A queue message alone proves neither execution nor completion.

Cloudflare Workflows may orchestrate processes naturally owned by the edge,
such as webhook validation and external synchronization. They do not replace
Codexify Campaign Engine, Flow Builder, cron authority, or chat worker
semantics. Durable Objects may coordinate temporary edge sessions, presence,
or rate state only where a demonstrated use case exists. Durable edge state
does not become durable Codexify application authority.

### 5. `ZERO_NON_INFERENCE_SPEND` is a campaign invariant

The campaign posture is `ZERO_NON_INFERENCE_SPEND`: no additional
non-inference infrastructure spend is acceptable unless an operator
explicitly approves a posture change.

1. A Free allocation may be used only when excess usage fails closed or
   Codexify can reliably remain inside it. Security-critical edge routes
   fail closed on quota exhaustion; they do not bypass the Worker.
2. Any product with automatic usage-based overage requires a Codexify-owned
   quota/capacity guard before production use. Cloudflare billing alerts are
   observability, not a hard spending limit.
3. A payment method or existing Cloudflare account does not authorize
   billable usage. Paid-later adapters may be implemented only behind a
   disabled capability gate.
4. Moving away from the zero-dollar non-inference posture requires explicit
   operator approval. Do not add a generic billing subsystem in this ADR.
5. Inference spend is separately governed by already approved provider
   budgets. This separation does not permit a hidden inference route or
   Cloudflare Unified Billing fallback.
6. AI Gateway Unified Billing remains disabled by default; use BYOK where
   compatible and configure credential-required behavior to prevent
   unintended fallback.
7. Web Search live requests remain disabled by default because search
   providers are usage-priced. Mocked/provider-disabled implementation work
   may precede separate approval for live spend.
8. R2 needs an application-level capacity posture because storage and
   operation usage can exceed included allocations into usage-based billing.
9. AI Search production ingestion/query traffic requires an explicit quota
   posture before use. Its 2026-10-04 included allocations, overage schedule,
   and billing start date are recorded as dated external facts in the
   Campaign; the billing schedule starts 2026-11-01.
10. Revalidate product pricing and limits immediately before each future
    integration enables usage. Estimates and alerting do not prove a hard
    spend ceiling.

### 6. Secrets, privacy, and provenance

- Secrets stay server-side in an owner-scoped secret facility. Never put
  Cloudflare/provider secrets in browser-visible configuration, frontend
  environment, ordinary logs, queue payloads, or durable provenance.
- Guardian account authority stays server-side. Turnstile is an admission
  signal, not login or authorization; verify its token server-side and reject
  invalid, expired, or replayed tokens.
- Minimize Cloudflare log data by default: no raw keys, bearer tokens,
  private prompts, retrieved private documents, or full user messages absent
  a separate explicit governance decision.
- External pages and browser output remain untrusted. Browser Run is not
  trusted merely because Cloudflare executed it and does not replace the
  canonical Browser Host boundary in ADR-054.
- Preserve existing canonical request/object/attempt lineage and provenance
  across transport, storage, search, inference, and execution boundaries.
- Configuration, authorization, enabled state, health/reachability, quota,
  degradation, actual per-request use, selected Cloudflare provider/product,
  canonical correlation, and spend-policy compliance are distinct operator
  facts. Do not compress them into one `connected=true` state. Repeated
  contract-bearing runtime values follow canonical-token discipline.

### 7. Service disposition and execution sequence

The companion Campaign classifies candidate services as `ADOPT_NOW`,
`IMPLEMENT_GATED`, `BENCHMARK_ONLY`, or `PARK`, and defines CE-01 through
CE-14 as deferred, individually authorized implementation slices. Those
labels describe architecture priority, not present implementation or
permission to provision Cloudflare resources. The Campaign completion
condition requires a bounded Worker, private governed capability access,
chosen object tier with canonical metadata elsewhere, useful inference
telemetry without routing transfer, admission protection where needed,
explicitly gated external search, one justified non-chat async path, and no
parallel authority or uncontrolled non-inference spend. Optional products may
close as `PARK` or `BENCHMARK_ONLY` when no demonstrated need exists.

## Governing alignment and consequences

This ADR extends and does not supersede ADR-021 (web retrieval and
untrusted-source boundaries), ADR-041 (VaultNode and audit authority),
ADR-061 (capability-oriented mesh and transport separation), ADR-067
(derived retrieval is noncanonical), ADR-071 (Connections control plane and
credentials), ADR-075 (Web versus Knowledge capability taxonomy), ADR-081
(Project ownership), ADR-093 (execution/inference/model/placement
separation), and ADR-094 (account-scoped credential authority). Where a
service-specific decision touches one of those domains, that governing ADR
continues to own its semantics.

Cloudflare can provide useful edge capabilities without displacing
local-first authority. The tradeoff is an additional provider and trust
boundary with mutable limits, service telemetry, and possible usage billing.
Every future task must preserve the authority matrix, verify current external
facts, identify the exact capability and authorizing actor, state what becomes
durable, and define evidence sufficient to prove completion.

## Non-goals and current-truth boundary

This ADR does not configure Cloudflare, deploy Workers, provision buckets,
queues, workflows, namespaces, or tunnels, add credentials or dependencies,
change routing or runtime behavior, implement service adapters, alter
Docker/Compose/Postgres/Redis, change Browser Host architecture, promote
Cloudflare-backed release support, or change Beta posture. No Cloudflare
integration is claimed to exist. `00-current-state.md` remains the release
and supported-path authority.

## Acceptance record

Resonant Jones accepted this architecture on 2026-10-04. Acceptance freezes
this boundary and the future Campaign sequence. CE-01 is the next eligible
separate implementation slice, but this acceptance does not authorize its
execution. Each runtime slice still requires its own bounded authorization,
current product-limit review, validation, and proof. Acceptance does not prove
implementation or change release status.
