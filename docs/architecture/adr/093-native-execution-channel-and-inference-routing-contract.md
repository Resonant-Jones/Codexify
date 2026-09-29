# ADR-093: Native Execution Channel and Inference Routing Contract

- Status: Proposed
- Date: 2026-09-26

## Context

ADR-048 established Pi, Codex, and Claude as peer execution systems under Guardian. Its authority and identity boundaries remain correct, but a fixed three-channel enumeration is too narrow as the long-term architecture for a meta-harness. First-party vendor harnesses now expose more than one useful process, SDK, protocol, or hosted-agent surface, while model and provider routes can cross harness boundaries.

This proposal generalizes the catalog of execution channels without claiming that any external harness is integrated or supported by Codexify. The companion [Execution Channel Capability Matrix](../execution-channel-capability-matrix.md) records the official external documentation reviewed on 2026-09-26. External documentation is evidence about vendor surfaces, not evidence of Codexify runtime support.

The current release and support boundary remains [00 Current State](../00-current-state.md). Codexify does not yet have a generalized execution-channel registry, per-turn channel switching, a canonical composer selector, an Auto router for native harnesses, or an entitlement/funding router.

## Governing decisions and relationship

- [ADR-048: Guardian Three-Channel Delegation Topology](ADR-048-guardian-three-channel-delegation-topology.md) is Accepted and remains the governing authority boundary. Guardian owns routing and authorization; execution channels remain peers; model/provider identity stays separate from channel identity; native harnesses retain their internal strategy within delegated authority; evidence does not become authority; and Pi is not a universal broker. This proposal extends the channel catalog and selection vocabulary. It does not rewrite or supersede ADR-048.
- [ADR-037: Campaign Runner Pi Provider Broker](037-campaign-runner-pi-provider-broker.md) remains Proposed. It states a module-specific preference for Pi as the lightweight provider-broker seam when available and expressly does not require Pi globally. Its Proposed status does not override Accepted ADR-048. This proposal treats Pi as one first-class peer channel and does not alter ADR-037 or its status.
- [ADR-068: Campaign Engine Live Role Execution Contract](068-campaign-engine-live-role-execution-contract.md) remains the current live-role boundary. Any future Campaign Engine use of a generalized channel identity requires a separately authorized schema/runtime change and, where needed, an ADR-068 amendment.
- The [Provider Capability Contract](../provider-capability-contract.md) remains a planning contract. This proposal extends its vocabulary to execution channels and channel-route compatibility without creating a runtime registry.

## Decision

Codexify should use four independent identity dimensions when it delegates an agent turn:

### Execution Channel

An **execution channel** is the agent runtime or harness that owns the delegated agent loop and its native execution strategy. Candidate canonical channel IDs are:

- codex
- claude
- qwen-code
- minimax-code
- gemini-cli
- zcode
- mistral-vibe
- deepseek-harness
- pi

The channel is not inferred from the selected model, provider, authentication method, or funding source. A channel may support several inference routes and models.

### Inference Route

An **inference route** identifies the provider, endpoint, or local runtime that supplies inference inside a selected execution channel. Examples include OpenAI API, Anthropic API, MiniMax, Alibaba ModelStudio, DeepSeek, Z.ai, Mistral, Whoosh'd, Ollama, and another compatible endpoint.

The route identity should identify the configured service/profile sufficiently to explain where inference was sent. It must not contain credentials. A compatible API shape alone does not prove that every capability of a native harness works with that endpoint.

### Model Identity

A **model identity** is the exact normalized model tag used for inference where the route or harness exposes it. It remains a separate value from both execution channel and inference route. If a harness changes models during one turn, the provenance record preserves the actual model used for each relevant inference call or route transition rather than reporting only the originally requested model.

### Funding / Entitlement Route

A **funding / entitlement route** records how access to the selected inference or managed runtime is authorized and paid. The minimum conceptual vocabulary is:

- user_native_entitlement
- user_byok
- codexify_included
- codexify_metered
- local_self_hosted

These labels are provenance and future billing context. They do not grant execution authority, define pricing, or identify an execution channel. This ADR defines no pricing, subscription, credit, or billing schema.

## Many-to-many compatibility

The architecture rejects both equations:

- one provider equals one harness;
- one harness equals one provider.

A channel may support multiple inference routes. A provider or model may be usable through multiple channels. For example, an operator-configured MiniMax route can be used by a compatible client such as Claude Code, while Qwen Code documents configuration for multiple inference services. The selected channel remains the harness that owns the agent loop; the route and model are recorded independently.

Compatibility is not a Cartesian product of channels, providers, and models. The future resolver evaluates explicit capability evidence for the requested task and current environment. A candidate binding is eligible only when declared and verified capability evidence, authentication and entitlement posture, environment posture, and policy jointly produce the required effective capabilities.

## Capability contract extension

The Provider Capability Contract should distinguish these capability domains:

1. **Provider/model capabilities:** inference and model features attributed to a route and, where required, a specific model.
2. **Execution-channel capabilities:** native loop, tool, event, session, permission, workspace, and execution features provided by a harness.
3. **Channel × inference-route compatibility:** evidence that a named channel, route, and optional model combination can operate together, including any feature limitations.
4. **Authentication and entitlement posture:** supported credential source/type, required account or entitlement, scope, and validity posture. Secret values remain outside capability and provenance records.
5. **Environment posture:** operating system, process/runtime version, local or remote placement, workspace availability, network posture, and sandbox/policy constraints relevant to the combination.

Each domain preserves the existing state distinction:

- **declared**: advertised by a vendor, route, or adapter;
- **verified**: checked by Codexify with identified evidence and a bounded verification scope;
- **effective**: usable for this task after policy, credentials/entitlement, environment, and task requirements are applied.

Only effective capabilities may satisfy routing requirements. Vendor declarations do not become Codexify verification. Codexify verification of one channel version, route, model, or environment does not automatically prove another combination. Evidence should be versioned or time-bound and reconsidered when a relevant component changes.

This is a planning extension to the existing contract. It does not create a runtime registry, discovery service, health check, UI, composer behavior, billing path, or adapter.

## Composer selection semantics

### Default Auto selection

The ordinary composer uses selection_mode = auto. Users are not required to understand the harness catalog. Guardian resolves an eligible execution channel using effective capabilities, task requirements, policy, user preferences, credentials and entitlement, environment, and available channel-route compatibility evidence.

After resolution, Codexify makes the actual channel and inference route inspectable in turn provenance. Auto is a constrained resolution mode, not permission to invent capability or bypass policy. If no eligible combination exists, resolution fails closed or asks the user to revise the request under future routing policy.

### Advanced explicit selection

An advanced user may set selection_mode = explicit and choose a specific execution channel. That choice is a routing constraint. Codexify must execute through that channel or report that the requested channel is unavailable or incompatible.

Codexify must not silently substitute another execution system or emulate the requested harness through a different provider. Future policy may fail closed or ask the user to change the channel. Model selection remains a separate composer dimension wherever the chosen channel supports multiple effective models; the exposed model choices are filtered by effective channel-route-model compatibility.

## Thread continuity and provenance

The Codexify Thread remains the authoritative conversation identity across channel switches. Guardian retains authority for the thread, tasks, user-visible timeline, authorization, result acceptance, and durable Codexify provenance.

Native session identifiers, including Codex thread/session IDs, Claude session IDs, Qwen session IDs, MiniMax session IDs, and other harness-native IDs, are subordinate execution-lineage records. They do not replace, rename, fork, transfer, or take ownership of the Codexify Thread.

A channel adapter may resume its own native session only when that channel is selected again and the native session is compatible, available, and authorized. A switch to a different channel receives a bounded Codexify context and retrieval packet. Opaque native state from the previous harness is not portable and must not be represented as inherited by the new harness.

For every resolved turn, future provenance records the actual execution channel and version, actual inference route, exact normalized model tag when exposed, funding/entitlement route, selection mode, relevant capability-evidence references, and subordinate native session lineage when available. If one turn uses multiple routes or models, the record preserves those observed transitions. Credentials and bearer material are never provenance fields. Unavailable identity must remain explicitly unknown and cannot be filled by inference from the model name; an unknown actual route cannot be represented as a fully resolved route.

## Campaign Engine relationship

Campaign Engine orchestrates Codexify Tasks. Future Executor and Evaluator RoleBindings should be able to bind an execution channel independently from an inference route and model, subject to the authority and proof gates in ADR-068.

Conceptual examples are:

- Executor bound to channel codex;
- Executor bound to channel pi with provider deepseek and an independently resolved model;
- Executor bound to channel qwen-code with provider minimax and an independently resolved model.

These examples describe a future relationship only. This ADR changes no Campaign Engine schema, RoleBinding, runtime, or current live-role boundary.

## Pi and native-channel preference

Pi is a first-class execution channel and a compatibility/long-tail harness. It is particularly useful when a provider or model lacks a richer first-party agent runtime, or when Pi's cross-provider capabilities are explicitly desired. Pi is not required to proxy every native harness and is not the universal broker.

As a design preference, when a vendor exposes a mature, supported first-party harness with capabilities materially richer than generic model inference, Codexify should prefer implementing a native execution-channel adapter rather than reproducing that harness through Pi. This preference does not mandate runtime selection. User choice, effective capability evidence, policy, environment, and entitlement still determine whether a native channel is eligible.

This decision preserves current Pi behavior. It does not repair, remove, or change any Pi transport or runtime.

## Authority, failure, and compatibility boundaries

- **Authority owner:** Guardian remains the routing, authorization, policy, and result-return authority. Channel evidence and provider compatibility do not grant execution authority.
- **Canonical state owner:** Codexify owns the Thread and durable Codexify task/provenance record. Native session history stays owned by its native harness.
- **Trust boundaries:** the user/device boundary to Guardian; the Guardian-to-channel adapter boundary; and the channel-to-inference route/provider boundary. Credentials remain in their existing user- or operator-authorized stores.
- **Threat posture:** channels and providers may be honest but buggy, malicious, or compromised. Network partitions, duplicate delivery, stale capabilities, and interrupted native sessions are normal failure cases. Future dispatch must correlate idempotently to a Codexify turn, enforce bounded authority at the Guardian/adapter boundary, and fail closed when required identity or effective capability cannot be established.
- **Consistency:** Codexify's canonical thread and turn/event lineage remains authoritative for Codexify conversation history. Native history is channel-local lineage; this decision defines no cross-channel merge or opaque-state portability.
- **Compatibility:** capability evidence must identify the relevant channel/adapter and route/model versions and environment posture. Unsupported protocol or version combinations are ineligible until reverified.

## Consequences

- The long-term architecture can add or retire execution channels without a new ontology for every harness.
- Composer selection can remain approachable for ordinary users while exposing a separate advanced channel constraint.
- Execution, inference, model, and entitlement provenance can be audited independently.
- Compatibility must be proven at the effective binding level; provider presence or API compatibility alone is insufficient.
- Native harness richness can be retained without making every harness a required dependency.
- This proposal changes no runtime support, release statement, composer, adapter, schema, or billing behavior.

## Non-goals

- Integrating Codex App Server, Claude Agent SDK/Managed Agents, Qwen Code, MiniMax Code, Gemini CLI, ZCode, Mistral Vibe, DeepSeek Harness, or any other new adapter.
- Implementing an execution-channel registry or Auto router.
- Changing the composer, Campaign Engine, RoleBinding schemas, Guardian runtime, Pi runtime, provider runtime, billing, pricing, subscriptions, or entitlement storage.
- Making external harness availability a Codexify support claim.
- Editing 00 Current State or changing release claims.

## Review state

This ADR is Proposed and returned for human review. It is not Accepted on behalf of Resonant Jones. Acceptance and any subsequent implementation require a separate human decision and bounded implementation task.
