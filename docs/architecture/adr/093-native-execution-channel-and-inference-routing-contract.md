# ADR-093: Native Execution Channel and Inference Routing Contract

- Status: Accepted
- Date: 2026-09-26
- Accepted: 2026-09-29
- Human approver: Resonant Jones

## Context

ADR-048 established Pi, Codex, and Claude as peer execution systems under Guardian. Its authority and identity boundaries remain correct, but a fixed three-channel enumeration is too narrow as the long-term architecture for a meta-harness. First-party vendor harnesses now expose more than one useful process, SDK, protocol, or hosted-agent surface, while model and provider routes can cross harness boundaries.

This decision generalizes the catalog of execution channels without claiming that any external harness is integrated or supported by Codexify. The companion [Execution Channel Capability Matrix](../execution-channel-capability-matrix.md) records the official external documentation reviewed on 2026-09-26. External documentation is evidence about vendor surfaces, not evidence of Codexify runtime support.

The current release and support boundary remains [00 Current State](../00-current-state.md). Codexify does not yet have a generalized execution-channel registry, per-turn channel switching, a canonical composer selector, an Auto router for native harnesses, or an entitlement/funding router.

## Governing decisions and relationship

- [ADR-048: Guardian Three-Channel Delegation Topology](ADR-048-guardian-three-channel-delegation-topology.md) is Accepted and remains the governing authority boundary. Guardian owns routing and authorization; execution channels remain peers; model/provider identity stays separate from channel identity; native harnesses retain their internal strategy within delegated authority; evidence does not become authority; and Pi is not a universal broker. This decision extends the channel catalog and selection vocabulary. It does not rewrite or supersede ADR-048.
- [ADR-037: Campaign Runner Pi Provider Broker](037-campaign-runner-pi-provider-broker.md) remains Proposed. It states a module-specific preference for Pi as the lightweight provider-broker seam when available and expressly does not require Pi globally. Its Proposed status does not override Accepted ADR-048. This decision treats Pi as one first-class peer channel and does not alter ADR-037 or its status.
- [ADR-068: Campaign Engine Live Role Execution Contract](068-campaign-engine-live-role-execution-contract.md) remains the current live-role boundary. Any future Campaign Engine use of a generalized channel identity requires a separately authorized schema/runtime change and, where needed, an ADR-068 amendment.
- The [Provider Capability Contract](../provider-capability-contract.md) remains a planning contract. This decision extends its vocabulary to execution channels and channel-route compatibility without creating a runtime registry.

## Decision

Codexify is the canonical user-facing GUI and durable interaction surface. Execution harnesses are subordinate engines beneath it; neither a harness process nor its native session owns a Codexify Thread. Guardian remains the authority for routing, authorization, policy, context brokering, result return, and durable provenance.

Each delegated turn resolves four independent identity dimensions plus an independent execution-placement dimension:

### Execution Channel

An **execution channel** (harness) is the agent runtime that owns the delegated agent loop and its native execution strategy within Guardian's bounded authority. Candidate canonical channel IDs are:

- codex
- claude
- qwen-code
- minimax-code
- gemini-cli
- zcode
- mistral-vibe
- deepseek-harness
- pi

Harness identity is independent from provider, model, funding or entitlement route, and execution placement. It is not inferred from any of them. A harness may support several inference routes and models.

### Inference Route

An **inference route** identifies the provider, endpoint, or local runtime that supplies inference inside a selected execution channel. Examples include OpenAI API, Anthropic API, MiniMax, Alibaba ModelStudio, DeepSeek, Z.ai, Mistral, Whoosh'd, Ollama, and another compatible endpoint.

The route identity should identify the configured service/profile sufficiently to explain where inference was sent. It must not contain credentials. A compatible API shape alone does not prove that every capability of a native harness works with that endpoint.

### Model Identity

A **model identity** is the exact normalized model tag used for inference where the route or harness exposes it. Provider and model are resolved for each invocation and may vary independently between turns, including turns on the same harness. Model identity remains separate from both execution channel and inference route. If a harness changes models during one turn, the provenance record preserves the actual model used for each relevant inference call or route transition rather than reporting only the originally requested model.

### Funding / Entitlement Route

A **funding / entitlement route** records how access to the selected inference or managed runtime is authorized and paid. The minimum conceptual vocabulary is:

- user_native_entitlement
- user_byok
- codexify_included
- codexify_metered
- local_self_hosted

These labels are provenance and future billing context. They do not grant execution authority, define pricing, or identify an execution channel. This ADR defines no pricing, subscription, credit, or billing schema.

### Execution Placement

**Execution placement** identifies where the selected harness runs, such as a local device or an authorized remote environment. Placement is resolved independently from harness, provider, model, and funding identity. A placement choice does not itself authorize hosted execution or cross a device, network, workspace, or credential boundary. The selected placement must satisfy the applicable policy, sandbox, capability, and environment posture before dispatch.

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

## Harness selection semantics

Codexify has a configurable `default_harness`. Its initial product default is `pi`. This is a harness preference, not a permanent provider or model identity and not a requirement for Pi to broker other harnesses. Guardian validates the resolved binding against policy, credentials and entitlement, environment, task requirements, and effective channel-route-model capability evidence before dispatch.

- `selection_mode = default` uses the configured `default_harness`. This is the ordinary selection mode; the user need not understand the harness catalog. If the configured harness cannot satisfy the invocation, Guardian reports the constraint or asks for a changed selection under an authorized policy. It does not silently replace the configured default with another harness.
- `selection_mode = explicit` uses the specifically requested harness as a binding constraint. Codexify executes through that harness or reports that it is unavailable or incompatible. It must not silently substitute another harness or emulate it through a different provider. The user must change the explicit harness constraint before a different harness can be selected.
- `selection_mode = auto` is optional policy-driven harness selection, not the ordinary mandatory mode. If implemented in a later bounded task, Guardian may choose only among bindings with effective capabilities and valid authority. Auto cannot invent capability, bypass policy, or override an explicit harness constraint. If no eligible binding exists, resolution fails closed or asks the user to revise the request.

Codexify makes the actual harness, inference route, model when exposed, selection mode, and placement inspectable in turn provenance. Provider and model are resolved for the invocation, not inherited as a fixed worker or harness identity. Model choices exposed to users must reflect effective channel-route-model compatibility.

## Thread continuity and provenance

The Codexify Thread remains the authoritative conversation identity across harness switches. Guardian retains authority for the thread, tasks, user-visible timeline, authorization, context brokering, result return and acceptance, and durable Codexify provenance. A harness process may be ephemeral, warm, or persistent; its lifetime cannot create, terminate, or determine the lifetime of the Codexify Thread.

Native session identifiers, including Codex thread/session IDs, Claude session IDs, Qwen session IDs, MiniMax session IDs, and other harness-native IDs, are subordinate execution-lineage records. They do not replace, rename, fork, transfer, or take ownership of the Codexify Thread.

A channel adapter may resume its own native session only when that channel is selected again and the native session is compatible with the resolved binding, available, and authorized. Guardian supplies a bounded Codexify context and retrieval packet when needed, including on a switch to a different harness. Opaque native state from the previous harness is not portable and must not be represented as inherited by the new harness.

For every resolved turn, future provenance records the requested and actual execution channel and version, configured default when `default` was selected, actual inference route, exact normalized model tag when exposed, funding/entitlement route, selection mode, execution placement, relevant capability-evidence references, and subordinate native session lineage when available. If one turn uses multiple routes or models, the record preserves those observed transitions. Credentials and bearer material are never provenance fields. Unavailable identity must remain explicitly unknown and cannot be filled by inference from the model name; an unknown actual route cannot be represented as a fully resolved route.

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

- **Authority owner:** Guardian remains the routing, authorization, policy, context-brokering, result-return, and durable-provenance authority. Channel evidence and provider compatibility do not grant execution authority.
- **Canonical state owner:** Codexify owns the Thread and durable Codexify task/provenance record. Native session history stays owned by its native harness.
- **Trust boundaries:** the user/device boundary to Guardian; the Guardian-to-channel adapter boundary; the execution-placement boundary; and the channel-to-inference route/provider boundary. Credentials remain in their existing user- or operator-authorized stores.
- **Threat posture:** channels and providers may be honest but buggy, malicious, or compromised. Network partitions, duplicate delivery, stale capabilities, and interrupted native sessions are normal failure cases. Future dispatch must correlate idempotently to a Codexify turn, enforce bounded authority at the Guardian/adapter boundary, and fail closed when required identity or effective capability cannot be established.
- **Consistency:** Codexify's canonical thread and turn/event lineage remains authoritative for Codexify conversation history. Native history is channel-local lineage; this decision defines no cross-channel merge or opaque-state portability.
- **Compatibility:** capability evidence must identify the relevant channel/adapter and route/model versions and environment posture. Unsupported protocol or version combinations are ineligible until reverified.

## Consequences

- The long-term architecture can add or retire execution channels without a new ontology for every harness.
- Ordinary selection can use the configured Pi default initially, while explicit selection preserves the user's harness constraint and optional Auto routing remains separately governed.
- Execution, inference, model, and entitlement provenance can be audited independently.
- Compatibility must be proven at the effective binding level; provider presence or API compatibility alone is insufficient.
- Native harness richness can be retained without making every harness a required dependency.
- Acceptance changes no runtime support, release statement, composer, adapter, schema, or billing behavior.

## Non-goals

- Integrating Codex App Server, Claude Agent SDK/Managed Agents, Qwen Code, MiniMax Code, Gemini CLI, ZCode, Mistral Vibe, DeepSeek Harness, or any other new adapter.
- Implementing an execution-channel registry, Auto router, automatic cross-harness substitution, or hosted execution.
- Changing the composer, Campaign Engine, RoleBinding schemas, Guardian runtime, Pi runtime, provider runtime, billing, pricing, subscriptions, or entitlement storage.
- Making external harness availability a Codexify support claim, or redesigning the GUI.
- Editing 00 Current State or changing release claims.

## Review state

Resonant Jones explicitly authorized these semantics and accepted this architecture decision on 2026-09-29. This acceptance authorizes the architecture contract only. It does not authorize new harness adapters, billing, GUI redesign, hosted execution, automatic cross-harness substitution, or other unrelated runtime expansion. Guardian-to-queue-to-coding-worker-to-Pi invocation-scoped binding remains a separate bounded implementation task with its own validation and authority gates.
