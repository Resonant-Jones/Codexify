# ADR-069: Codexify Beta Runtime Support Boundary

## Status

Accepted.

## Date

2026-08-14

## Human approver

Resonant Jones

## Canonicalization History

- ADR-066 was already allocated before this decision to the Campaign Engine
  Runtime Recovery Contract.
- ADR-067 was already allocated on `main` to Operator-Approved Derived Chroma
  Retirement.
- A duplicate ADR-067 identity was separately identified for reconciliation.
- ADR-068 was intentionally reserved by Resonant Jones for that collision
  repair.
- ADR-069 was explicitly allocated to the Codexify Beta Runtime Support
  Boundary.
- This task does not resolve or renumber any other ADR.
- Future agents must not move ADR-069 backward merely because ADR-068 was
  temporarily absent from one repository revision.

## Context

Codexify's prior release narrative conflated three orthogonal properties —
evidence maturity, support posture, and runtime participation — and treated the
narrow subset of Codexify with the strongest live-proof receipts as if it were
the entirety of the Beta promise. In practice, the supported runtime profile,
the enabled routes, the implemented persona/import/repository/tool surfaces,
and the authority-bounded command-bus surface together describe a coherent
local-first product that is intentionally shipped and supportable, even where
individual evidence receipts are still maturing. Recording that intent in a
governing ADR is necessary so the release boundary, the canonical
Product Architecture Assertion layer, the supported runtime profile, and the
human-readable `00-current-state.md` cannot drift apart silently.

The human architecture decision has already been taken on 2026-08-14 by
Resonant Jones:

- Codexify Beta should represent the coherent Codexify experience intentionally
  shipped and operated, not only the tiny subset with the strongest live-proof
  receipts.
- Evidence maturity must remain distinct from support posture.
- Bounded / conditional Beta support is legitimate where authority and limits
  are explicit.
- TTS / voice execution and federation remain outside Beta.
- Dangerous, unrestricted, or authority-ambiguous execution surfaces remain
  outside Beta.
- Coding Loop, Hosted Rooms, private-preview / DeepSeek, and similar
  near-boundary surfaces may be represented as qualification-pending rather
  than erased from the product model.

ADR-057 previously established the Product Architecture Ontology as the
vocabulary and assertion layer that extends the DLG. ADR-057 was correct at
its acceptance that no canonical posture assertion corpus existed. ADR-069
activates the first bounded canonical posture corpus for present Beta support
without rewriting ADR-057's historical acceptance record.

## Decision

## Definition of Beta

Codexify Beta is the intentionally shipped and supportable local-first product
envelope. Beta is **not** a synonym for production-grade proof maturity. Bugs
and incomplete polish are compatible with Beta. Unknown, unrestricted, or
authority-ambiguous execution surfaces are not compatible with Beta. A Beta
capability may carry `proven-test` or `proven-code-path` evidence where the
architecture decision intentionally accepts that maturity for Beta, while
authority-sensitive, destructive, remote-trust, or multi-user surfaces may
remain qualification-pending regardless of how mature their implementation
appears.

## Release Classes

ADR-069 defines five human-facing release classes used in `00-current-state.md`
and the canonical posture assertions. They are **release interpretations over
the orthogonal Product Architecture Assertion dimensions plus explicit scope,
not a replacement token domain.** The existing assertion schema dimensions
remain canonical:

- `support_posture`
- `runtime_participation`
- `ownership_state`
- `strategy_state`
- `integration_state`
- `evidence_class`
- `assertion_scope`

The five release classes are:

1. **Beta Supported** — intentionally shipped as part of the normal Codexify
   Beta experience and support promise.
2. **Beta Bounded / Conditional** — intentionally part of Beta, but only inside
   an explicit authority, topology, provider, mode, or capability boundary.
3. **Internal** — real operational substrate or operator / developer mechanism
   that may support Beta behavior but is not itself a public / user-facing
   release promise.
4. **Qualification Pending** — intended or plausible Beta surface with
   implementation present, but a specifically named proof / authority /
   operational gate remains open.
5. **Out of Beta** — explicitly excluded from the present Beta promise.

ADR-069 does **not** add the five strings as new Product Architecture
Assertion schema enums. The existing orthogonal dimensions already encode
the underlying state; the five classes are human-facing release
interpretations.

## Evidence vs Support Doctrine

ADR-069 establishes the following doctrine explicitly:

- `supported` does not mean `proven-live-runtime`.
- `proven-live-runtime` does not automatically mean `supported`.
- Evidence maturity and support posture are orthogonal.
- A Beta capability may carry `proven-test` or `proven-code-path` evidence
  where the architecture decision intentionally accepts that maturity for
  Beta.
- A capability requiring stronger evidence because of authority, destructive
  behavior, remote trust, or multi-user semantics may remain
  qualification-pending even when the code path is mature.
- Future promotion or demotion of any capability must update canonical
  posture assertions and `00-current-state.md`.
- A change to the meaning of the release classes themselves requires ADR-level
  review.

## Canonical Authority Hierarchy

The release boundary must follow this hierarchy:

1. Accepted ADRs define durable release doctrine and semantics.
2. Canonical Product Architecture Assertions record temporal support /
   runtime / integration posture for stable architecture concepts.
3. Supported profiles (`config/supported_profiles/*.yaml`) constrain actual
   runtime exposure, topology, and provider posture.
4. `00-current-state.md` is the human-readable current release interpretation
   and active blocker surface.
5. Proofs, tests, and code provide evidence and must not silently redefine
   support posture.

If these disagree, the conflict must be surfaced and reconciled. No source
silently chooses whichever source is more convenient.

## Current Beta Envelope

The intended current Beta envelope is the union of the surfaces below. If the
required pre-read reveals a direct current-code contradiction, the
architecture decision in this ADR is preserved and the contradicted surface is
classified as Qualification Pending with the exact gap documented.

### Beta Supported

**A. Local runtime and lifecycle**

- Local Docker Compose runtime.
- Local-only default provider posture (`CODEXIFY_LOCAL_ONLY_MODE=true`,
  `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`).
- Whoosh'd / local inference on the supported local profile.
- Core startup / migration lifecycle.
- Queue-backed chat completion lifecycle.
- Durable thread / message / task persistence.
- Supported health and runtime diagnostics.

**B. Digital Cognitive Workspace core**

- Ordinary chat.
- Threads and durable conversation history.
- Projects.
- Project / thread / workspace navigation.
- Documents and media ingestion on currently implemented supported formats.
- Embedding and private retrieval / RAG.
- Workspace-scoped retrieval.
- Obsidian / local workspace ingestion and retrieval.
- Bounded verified personal-facts / personalization behavior already used by
  ordinary chat.
- Core settings that configure currently supported runtime behavior.

**C. Identity and ownership**

- Codexify-native identity / authentication boundaries.
- Account-scoped ownership behavior already required by supported workspace
  surfaces.
- Migration / upgrade behavior already part of the supported local lifecycle.
- Operator-visible health / configuration truth required to run the
  self-hosted node.

**D. Operator experience**

- Dashboard / admin / health surfaces that truthfully expose supported runtime
  state.
- Model inventory / readiness surfaces.
- Queue / worker / runtime diagnostic visibility where the UI reflects real
  Guardian state.
- Unrestricted control-plane mutation is not promoted merely because
  diagnostic UI exists.

### Beta Bounded / Conditional

**A. Persona Studio**

The bounded Persona Studio core is Beta Bounded / Conditional:

- profile creation / editing
- profile persistence
- profile selection
- application of supported persona / profile configuration to ordinary chat

Excluded from this promotion:

- TTS / voice execution
- unsupported permission authoring
- unsupported retrieval-policy execution
- claims that preview UI equals enforcement
- any future Studio feature that lacks a current implementation seam

Persona Studio being Beta must not implicitly make every control visible in
Studio Beta-supported.

**B. Import / continuity entry surfaces**

Currently implemented and bounded:

- OpenAI / ChatGPT export import
- Task Prompt Archive
- owner-scoped retry / recovery behavior already implemented
- account export / restore only to the exact extent supported by the existing
  contract and implementation

Not claimed:

- every historical corpus, provider export format, or migration shape.

**C. Repository intelligence**

On the supported local single-user path:

- repository candidate discovery
- explicit repository import
- account / Project `RepositoryBinding`
- direct Project-bound repository search
- ordinary-chat repository search exposure only when Guardian resolves exactly
  one valid active binding and existing authority checks pass

The model must not gain authority from supplying Project ID, repository root,
binding ID, account ID, cwd, mount path, credentials, or equivalent
authority-bearing data.

Remote / multi-user / Hosted-Room repository authority remains outside this
bounded Beta claim.

**D. Bounded Guardian tool execution**

Beta supports allowlisted, Guardian-authorized bounded tool execution for
explicitly supported capabilities. At minimum:

- read-only health capability
- bounded Project repository search where current eligibility / authority
  checks pass

Preserve:

- advertised-subset authority gate
- Guardian-owned execution authority
- exact capability eligibility
- bounded command count
- continuation / persistence semantics
- provider capability checks

Do not promote:

- arbitrary tools
- arbitrary write operations
- generic shell / filesystem execution
- recursive multi-command agents
- public Command Bus HTTP
- generic `/tools` or `/api/tools` exposure

**E. MCP / extensibility**

The public MCP extension posture may be described as part of Beta only as a
bounded extension interface.

Not claimed:

- every MCP server is trusted
- every plugin is supported
- plugin SDK internals are public Beta API
- arbitrary plugin execution bypasses Guardian policy
- a general plugin marketplace is released

**F. Desktop / Tauri client**

If current `main` still contains the functioning local desktop / Tauri
presentation layer, classify it as Beta Bounded / Conditional when used as a
client of the same supported local Guardian node.

Not claimed:

- packaged production desktop distribution
- auto-update support
- an independent desktop persistence / runtime authority
- a separate release topology not currently proven

### Internal

The following remain explicitly internal:

- direct Command Bus HTTP / control-plane API
- plugin SDK internals
- generic tools / API tools surfaces currently marked internal / quarantined
- developer-only diagnostics
- unsafe operator mutation surfaces
- implementation / control-plane mechanisms that support Beta behavior
  without being user-facing promises

## Qualification-Pending Doctrine

At minimum:

- **Coding Loop** — open gate: adapter execution plus terminal durable result
  plus source-thread readback on the claimed profile.
- **Hosted Rooms** — open gate: clean supported / tester startup plus owner /
  guest live semantic proof after migration repair.
- **DeepSeek / private-preview provider lane** — open gate: required
  credentials, authenticated provider-specific persisted runtime proof, and
  explicit supported-profile promotion.
- **Browser side-panel / Browser Host release surface** — open gate: whichever
  current host / auth / release proof remains open after reading current
  `main`.
- Any desktop packaging behavior not covered by the bounded local-client
  claim.

Qualification-pending surfaces must name the specific remaining gate rather
than only saying "not supported."

### Out of Beta

Explicitly excluded from the present Beta promise:

- TTS / voice execution
- federation
- unrestricted autonomous / recursive agent execution
- arbitrary write-capability tool use
- generic shell / filesystem execution through ordinary Beta chat
- public Command Bus exposure
- generic cron / unattended automation
- generic connectors without separate qualification
- graph-write / Neo4j-derived-write behavior where the supported path remains
  flagged off or quarantined
- remote / multi-user repository execution not covered by a separately
  accepted authority contract and live proof

TTS / voice and federation are **not** classified as qualification-pending in
this ADR. They are intentionally Out of Beta.

## Promotion and Demotion Rules

Promotion of a surface from one release class to another requires:

- explicit human selection;
- governing ADR or contract alignment where one exists;
- canonical Product Architecture Assertions added or amended with the new
  posture, evidence class, and `assertion_scope`;
- a matching update to `00-current-state.md`;
- supported-profile adjustment where runtime exposure changes;
- evidence class appropriate to the new claim.

Demotion follows the same shape. A change to the meaning of the release
classes themselves requires a new ADR.

## Product Architecture Assertion Relationship

The canonical posture assertion set for present Beta support is recorded in
`docs/knowledge-graph/assertions/codexify-beta-support-posture.v1.json`. That
corpus:

- uses the existing schema dimensions only;
- records honest evidence classes;
- is bounded to current Beta support posture and does not invent a
  repository-wide source-subsystem or relationship corpus;
- references ADR-057 and ADR-069 as governing ADRs;
- uses `codexify:doc:architecture:current-state` as current release authority
  where appropriate;
- records `repository_revision` as the audited pre-change full HEAD SHA.

## Supported Runtime Profile Relationship

Supported runtime profiles (`config/supported_profiles/*.yaml`) remain the
binding surface for runtime exposure. ADR-069 does not modify any profile in
this task. The default `v1-local-core-web-mcp` profile continues to define
the supported Beta:

- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `ALLOW_CLOUD_PROVIDERS=false`
- `LLM_PROVIDER=local`
- public extension: `mcp`
- internal extensions: `command_bus_http`, `plugin_sdk`
- `command_bus` remains `internal_only`
- `tools` and `api_tools` remain `quarantined`
- `voice` and `federation` remain `quarantined`

If a profile change is required for a future release-class move, that change
is a separate task with its own proof.

## Proof / Test Relationship

Proof receipts (`docs/architecture/proofs/`) and tests provide evidence.
They are not independently authorized to redefine the release boundary. A
proof may justify a future promotion; it does not itself perform the
promotion. The Canonical Authority Hierarchy (§4) governs how a proof is
translated into a posture assertion.

## Governing and aligned ADRs

- **ADR-057** (Product Architecture Ontology as a Document Lifecycle Graph
  Extension) — supplies the vocabulary and assertion schema.
- **ADR-061** (Capability-Oriented Mesh Architecture) — supplies the
  capability authorization boundary.
- **ADR-065** (Guardian-Managed Repository Onboarding Boundary) — supplies
  the bounded repository intelligence authority boundary.
- ADR-005 (Runtime Mode and Account Boundary Invariants) — Codexify-native
  identity authority.
- ADR-020 (Guardian Mediated Coding Agent Execution Contract) — coding-agent
  authority boundary.
- ADR-022 (Guardian Intent Spine and Cross-Surface Control Plane) — chat /
  cross-surface dispatch boundary.
- ADR-024 (Context Command and Active Connector Semantics) — connector /
  active-connector boundary.
- ADR-039 (Operator / User Access Boundary) — operator / user distinction.
- ADR-041 (VaultNode Canonical Machine and Audit Authority) and ADR-042
  (Canonical Audit Evidence Contract) — proof / evidence authority.
- ADR-048 (Guardian Three-Channel Delegation Topology) — peer execution
  channel boundary.
- ADR-049 (Admin Account Observability and Invite Attribution) — account
  observability boundary.
- ADR-052 (Whoosh'd and Approved DeepSeek Startup Profile) — local inference
  startup profile boundary.
- ADR-053 (Node-Hosted Room Access Boundary) — hosted-room authority boundary.
- ADR-054 (Browser Host Topology and Release Ownership) — browser-host
  topology boundary.
- ADR-055 (ThreadSpace ↔ WhisperMesh Managed-Service Boundary) — managed
  service boundary.
- ADR-056 (Document Lifecycle Graph Control Plane) — DLG identity and
  lifecycle authority.
- ADR-062 (Provider Capability Model Contract) — provider capability model
  doctrine.

## Acceptance record

- Proposed: 2026-08-14
- Accepted: 2026-08-14
- Human approver: Resonant Jones
- Acceptance scope: the canonical Codexify Beta support boundary, the five
  release classes, the evidence-vs-support doctrine, the canonical authority
  hierarchy, and the first canonical posture assertion corpus for present Beta
  support. Acceptance does not modify runtime behavior, the default supported
  profile, the supported provider posture, the persistent store, the migration
  graph, or any authority contract. ADR-057 remains historically valid;
  ADR-069 activates a bounded posture corpus on top of the vocabulary ADR-057
  already accepted.

## Documentation Follow-through

This ADR is accompanied by the ADR index registration, the current-state
release-boundary reconciliation, the Architecture README navigation update,
the Product Architecture Ontology prose reconciliation, the bounded canonical
Beta support-posture assertion corpus, and architecture drift tests. Runtime
implementation, supported-profile changes, complete source-subsystem
inventory, and qualification of pending surfaces are explicitly deferred.

## Related Documents

- [`00-current-state.md`](../00-current-state.md)
- [`adr-index.md`](./adr-index.md)
- [`product-lanes-and-boundaries.md`](../product-lanes-and-boundaries.md)
- [`config/supported_profiles/v1-local-core-web-mcp.yaml`](../../../config/supported_profiles/v1-local-core-web-mcp.yaml)
- [`codexify-beta-support-posture.v1.json`](../../knowledge-graph/assertions/codexify-beta-support-posture.v1.json)
- [`test_beta_release_boundary.py`](../../../tests/architecture/test_beta_release_boundary.py)

## Consequences

### Positive

- Release boundary, posture assertions, supported profile, and current-state
  truth can no longer drift apart silently.
- The five release classes give humans a stable vocabulary for "what is Beta".
- Evidence-vs-support separation prevents the inverse failure modes where
  maturity is treated as authority, or authority is treated as maturity.
- The canonical posture corpus is bounded and reproducible from ontology +
  authority documents.

### Negative

- The canonical posture corpus requires discipline; stale assertions must be
  refreshed when posture changes.
- Five release classes add a small layer of release interpretation on top of
  the orthogonal schema dimensions.

### Neutral

- Runtime behavior is unchanged.
- Repository layout is unchanged.
- The default supported profile is unchanged.
- ADR-057 remains historically valid.

## Non-goals

- No runtime code behavior change.
- No supported-profile schema redesign.
- No runtime profile capability projection generation.
- No automatic release projection tooling.
- No source-subsystem inventory.
- No complete Product Architecture relationship assertion corpus.
- No Coding Loop, Hosted Room, private-preview / DeepSeek, or Browser Host
  promotion in this task.
- No TTS / voice, federation, arbitrary tools, cron / connectors, or
  autonomous agent promotion.

## Explicit Exclusions

TTS / voice execution, federation, unrestricted autonomous or recursive
execution, arbitrary write-capability tools, generic shell or filesystem
mutation, public Command Bus exposure, generic cron or unattended automation,
unqualified connectors, quarantined graph writes, and remote or multi-user
repository execution without separately accepted authority and proof are
explicitly Out of Beta.

## Explicitly deferred work

- Runtime feature implementation.
- Supported-profile schema redesign.
- Runtime profile capability projection generation.
- Automatic release projection tooling.
- Source-subsystem inventory.
- Complete Product Architecture relationship assertion corpus.
- Coding Loop qualification.
- Hosted Room qualification.
- Private-preview / DeepSeek promotion.
- Browser Host promotion.
- TTS / voice.
- Federation.
- Arbitrary tools.
- Cron / connectors / autonomous agent promotion.
