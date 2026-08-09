Purpose: Define the architecture by which Codexify determines whether one exact Whoosh'd model target is qualified to participate in the canonical Guardian tool-turn protocol.
Last updated: 2026-08-09
Source anchors:
- docs/architecture/provider-tool-turn-boundary-contract.md
- docs/architecture/provider-capability-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/whooshd-model-profiles.md
- docs/architecture/whooshd-control-plane-v1.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/runtime-protocol-token-contract.md
- docs/architecture/canonical-token-philosophy.md
- guardian/core/whooshd_model_profiles.py
- guardian/providers/whooshd_sidecar.py
- guardian/providers/whooshd_control_plane.py
- guardian/core/ai_router.py
- guardian/core/chat_completion_service.py
- Whoosh'd ref e191798be3a290b291e0878eac8309d8b6ce7130 (ResonantConstructs/Whoosh'd)

## Purpose

Define the per-model tool-capability qualification boundary so that Codexify
can truthfully distinguish "this exact Whoosh'd model target is qualified to
participate in Guardian's bounded tool loop" from "Whoosh'd can serialize a
tool-shaped request."

The contract applies because Whoosh'd is a single Codexify provider identity
that can serve many materially different model/runtime/template targets. A
single provider-level capability boolean is architecturally insufficient.

## Scope

This contract is an architecture reconciliation and capability-boundary
definition. It does not implement Whoosh'd tool calling. It does not change
Codexify runtime, provider routing, or production code. It does not add
canonical runtime tokens. It does not modify Whoosh'd source.

## Current Truth

### What is true now

- Whoosh'd is one provider identity (`provider = whooshd`) from Codexify's
  perspective.
- Whoosh'd can route requests to multiple runtime engines: `mlx_lm`,
  `mlx_lm_server`, `mlx_vlm`, `llama_cpp`.
- Model format (`gguf`, `mlx`, `safetensors`) is distinct from runtime engine.
- Whoosh'd model lifecycle distinguishes `candidate`, `registered`,
  `compatible`, `advertisable`, and `runnable` states.
- `ModelCapability.TOOLS` exists in Whoosh'd contracts as an enum value.
- `ModelInfo.capabilities` carries a list of `ModelCapability` values in
  Whoosh'd API responses.
- `ChatCompletionRequest` accepts `tools`, `tool_choice`, and
  `parallel_tool_calls` fields in the ingress request schema.
- `BackendChatRequest` can forward `tools`, `tool_choice`, and
  `parallel_tool_calls` to backend adapters through the backend request policy.
- `http_forwarding.py` can serialize tool-related fields in forwarded request
  bodies.
- `InferenceAdapter` exposes `supports_streaming` but does not currently
  expose an equivalent canonical `supports_tools` contract.
- `backend_request_policy.py` explicitly states: adapter extension support is
  serialization capability, not proof that every installed backend version
  implements a feature.
- Stage 2A defines the canonical provider-neutral Codexify tool-turn
  boundary.
- Stage 2B proves one native provider (DeepSeek) against that boundary.
- Stage 1 remains Guardian's pre-execution authority gate.

### What is NOT yet proven

- `ModelCapability.TOOLS` has not been proven to mean "this exact target is
  qualified for Guardian tool use."
- A `runnable` model is not proven to be tool-capable merely because it
  can generate text.
- `llama.cpp` runtime tool-calling support is a transport capability;
  it does not prove every GGUF model is semantically competent for tool use.
- `mlx_lm`/`mlx_lm_server`/`mlx_vlm` transport capability is a separate
  question from exact model/template competence.
- File format alone does not establish tool semantics.
- No canonical qualification evidence or invalidation contract exists.

## Terminology

- **Provider identity**: `whooshd` — the single Codexify `provider` field value.
- **Runtime engine**: The inference execution engine (`llama_cpp`, `mlx_lm`,
  `mlx_lm_server`, `mlx_vlm`).
- **Model target**: An exact combination of model artifact (revision/hash/
  quantization), runtime engine, adapter, chat template, and tokenizer.
- **Tool-qualified**: An exact model target has current evidence proving it can
  participate in the canonical bounded tool loop.
- **Tool-eligible**: A tool-qualified target is also currently runnable and
  healthy.

## Existing Whoosh'd Lifecycle

From the Whoosh'd source (ref `e191798be3a290b291e0878eac8309d8b6ce7130`),
the model lifecycle states relevant to this contract are:

| State | Meaning | Tool-qualified? |
|---|---|---|
| `candidate` | Ingested or discovered, not yet registered | No |
| `registered` | Registered in the model registry | No |
| `compatible` | Passed adapter-compatibility validation | No |
| `advertisable` | Eligible for inventory advertisement | No |
| `runnable` | Currently warm/healthy enough to serve | No |

None of these existing lifecycle states implies tool qualification. Tool
qualification is a separate evidence-based layer above the existing lifecycle.
The contract does not create a new Whoosh'd lifecycle state.

## Existing Capability Surfaces

### ModelCapability.TOOLS

`ModelCapability.TOOLS` is an enum value in `whooshd/contracts.py`. It sits
alongside `CHAT`, `STREAMING`, `JSON`, `EMBEDDINGS`, `REASONING`, and `VISION`.

Current semantics (by code inspection):

- **Where populated**: Not currently populated by any adapter or registry
  loader visible in the current Whoosh'd checkout. The capability list on
  `ModelInfo` is initialized with a default of an empty list.
- **Not statically declared** in registry entries — `RegistryModelEntry` has no
  `capabilities` field.
- **Not inferred** by the resolver or inventory — resolution results carry
  `runtime` hints but no capability data.
- **Not runtime-evidenced** by any adapter — adapters expose `supports_streaming`
  but no `supports_tools` contract.
- **Not consumed** by any Codexify component for routing, advertisement, or
  authorization.

Assessment: `ModelCapability.TOOLS` is currently defined vocabulary awaiting a
producer. It is not populated, not proven, and not consumed. It is safe to
designate as the future public projection of a proven per-model qualification
because no existing producer or consumer would need to change.

### InferenceAdapter

`InferenceAdapter` (Protocol) exposes:

- `kind` — runtime kind identifier (e.g., `"llama_cpp"`, `"mlx_lm_server"`)
- `supports_streaming` — boolean
- No `supports_tools` or tool-transport contract

A future adapter extension should add a tool-transport contract so the
adapter registry can truthfully populate `ModelCapability.TOOLS` from
evidence.

### ModelInfo

`ModelInfo.capabilities: list[ModelCapability]` is the public API projection.
It is exposed via `GET /models` and `GET /v1/models`. When `TOOLS` is
eventually populated, Codexify's whooshd sidecar health probes and catalog
endpoints can read it from `/v1/models`.

## Provider vs Runtime vs Model Target

This contract normatively separates three layers beneath the Whoosh'd provider
identity:

1. **Provider** (`whooshd`): the API surface reachable at
   `http://host.docker.internal:8000`. One provider identity.

2. **Runtime engine** (`llama_cpp`, `mlx_lm_server`, etc.): the inference
   execution backend. Different engines have different tool-transport
   capabilities. Engine capabilities are NOT model capabilities.

3. **Model target**: the exact combination of artifact, quant, engine, adapter,
   chat template, and tokenizer. Tool qualification attaches HERE, not at the
   provider or engine level.

Codexify must route to `whooshd` → `exact model alias/public id` → `effective
capability view for that target`. No new provider identities are created.

## Tool Transport Capability

Tool transport is the ability of a runtime engine + adapter pairing to
correctly forward the canonical tool protocol tokens (tools, tool_choice,
tool messages) to the underlying inference layer and return structured
results.

### Whoosh'd API representation capability

Confirmed: Whoosh'd's API contracts can represent `tools`, `tool_choice`,
`parallel_tool_calls`, `tool_calls` on messages, and `tool_call_id` on
messages. The backend request policy forwards these fields when present.

### Serialization is not transport qualification

Per `backend_request_policy.py`: "Provider extensions are serialization
capabilities, not a claim that every installed backend version implements
them."

This contract normatively restates this: the presence of tool-shaped fields
in request schemas and forwarding infrastructure does not establish that any
particular model target can produce valid tool calls.

### Transport modes

Three conceptual modes, aligned with the Stage 2A contract:

- **Native**: the runtime/model exposes a genuine native tool/function-call
  path. The adapter forwards the canonical protocol tokens to the native
  runtime interface. Example: llama.cpp server's OpenAI-compatible
  `/v1/chat/completions` with `tools`.

- **Structured**: the runtime can constrain or validate output sufficiently to
  produce one schema-valid bounded tool decision even without a native
  function-call primitive. A structured path must have explicit parse/schema
  constraints, not merely "prompt the model to return JSON."

- **Unavailable**: no reliable transport is proven.

### Transport capability is NOT model competence

A runtime engine that can technically forward tools does not guarantee that any
particular model loaded on that engine understands when and how to use the
advertised tools. Transport is necessary but insufficient.

## Exact Model/Template Qualification

Tool qualification requires evidence that the exact model target — including
its specific artifact, quant, tokenizer, and chat template — can:

1. receive one bounded authorized tool advertisement
2. select the correct tool when a test prompt clearly requires it
3. produce arguments satisfying the tool's schema
4. preserve correlation identity across the round trip
5. continue to a final assistant answer after receiving the tool result
6. NOT invent an unadvertised command
7. produce ordinary assistant output when no tool is needed

The minimum qualification proof must be executed against the exact target
identity, not against the runtime engine family or the model family.

## Qualified Capability vs Runtime Readiness

Two distinct concepts:

```
qualified_tool_capability =
    runtime transport compatibility verified
    AND exact model/template protocol qualification evidence exists
    AND that evidence is still valid (not invalidated)

tool_eligible_now =
    qualified_tool_capability
    AND current target/runtime is runnable and sufficiently healthy
```

A model can be tool-qualified but not currently eligible because the runtime
is offline, the model is unloading, or the adapter is degraded. Conversely,
a model can be runnable but not tool-qualified because no evidence exists.

## Qualification Evidence

A future qualification receipt must identify:

- exact public model alias (Whoosh'd model ID)
- runtime engine
- model artifact/revision identity available at runtime
- quantization or variant
- chat template / tool parser identity where relevant
- transport mode tested (native or structured)
- tool protocol version/contract tested (Stage 2A)
- qualification result (pass / fail / degraded)
- proof timestamp
- runtime/engine version evidence sufficient to detect staleness

This contract does not create storage tables or files. It defines the
conceptual evidence shape.

## Qualification Invalidation

Tool qualification must not silently survive material changes to the execution
target. Prior evidence is considered stale when any of the following change:

- model artifact revision (different weight file or HF revision)
- quantization (if behavior may materially differ)
- runtime engine (e.g., switching from `llama_cpp` to `mlx_lm_server`)
- runtime engine version (if tool semantics differ between versions)
- tokenizer (different tokenizer model or version)
- chat template / tool parser (different template or parser version)
- structured-output grammar/parser (if the transport mode depends on it)
- transport mode (if the qualification was proven against native but the
  runtime switches to unstructured)

The conceptual invalidation key is the tuple of identity components above.
No persistence schema is created in this task.

## Guardian Consumption Boundary

For a future Guardian request that requires model-callable tools:

```
provider supports canonical transport (Stage 2A contract)
AND selected Whoosh'd target is tool-qualified for a supported transport
AND target is currently tool-eligible (runnable + healthy)
AND requested canonical capabilities are permitted for the request
⇒ tool definitions may be advertised
```

The Stage 1 advertised-subset gate still applies after the model proposes a
call. Tool qualification does not:

- grant filesystem authority
- grant Command Bus authority
- make all commands available
- bypass user/profile permissions
- bypass project/workspace authority

## Authority Boundary

The Stage 1 gate (`_authorized_tool_command_ids` →
`_execute_bounded_tool_turn_completion`, commit
`ea87dc0e8c6832de49aa663e53ff9c34ac8d5dca`) remains the sole pre-execution
authority seam for every provider, including Whoosh'd.

Tool qualification is a necessary precondition for Guardian to advertise tools
to the model, but qualification is NOT execution authority. The gate applies
separately and afterward for every individual tool turn.

## Native vs Structured Local Transport

Reconciling the Stage 2A transport doctrine with Whoosh'd:

- **Native**: If the runtime exposes an OpenAI-compatible `/v1/chat/completions`
  that natively supports `tools` (as llama.cpp server does), that is a native
  transport. Whoosh'd forwards the tool definitions and the provider-native
  response, and the normalization path produces the canonical provider-neutral
  `NormalizedCompletionOutput`.

- **Structured**: If the runtime does NOT natively support tools (as `mlx_lm`
  may not), a structured transport is still possible if the model can reliably
  produce one schema-valid bounded tool decision within a single generation
  call. This requires explicit output constraint (grammar, JSON schema, or
  equivalent) and qualification proof.

- **Loosely prompted JSON is not a qualifying structured transport.** This
  contract requires explicit parse/schema constraints.

## Failure/Degradation Doctrine

If the exact selected Whoosh'd target is not proven tool-eligible, Codexify
must not silently advertise execution-bearing tools and hope the model follows
the protocol. The following are separate routing-policy decisions deferred to
future implementation tasks:

- selecting another tool-qualified model
- falling back to ordinary (non-tool) chat completion
- asking the user to choose a model
- routing to a cloud provider

## Cross-Provider Relationship

DeepSeek (Stage 2B): one relatively homogeneous provider-native transport
implementation has been test-proven against the canonical semantic boundary.

Whoosh'd (this contract): a provider boundary containing heterogeneous
model/runtime targets. Tool transport qualification occurs below the provider
identity at the exact target/runtime/template boundary. All qualified paths
normalize to the same Codexify semantic tool-turn contract.

## Invariants

- Whoosh'd remains one provider identity.
- Model format (GGUF, MLX) is not tool capability.
- Runtime engine (llama_cpp, mlx_lm) is not exact-model tool capability.
- Request-schema support is not tool qualification.
- Forwarding tools is not proof the target can use them.
- `runnable` does not imply tool-qualified.
- Qualification attaches to an exact execution target, not the provider name.
- Exact-model qualification must be evidence-backed.
- A hardcoded model-family allowlist is not the architecture.
- Native and strict structured transport may satisfy the same canonical
  semantic contract.
- Loosely prompted free-form JSON does not qualify as a safe structured
  transport.
- Model qualification does not grant Guardian command authority.
- Stage 1 remains the command authority gate.
- Provider capability records describe ability, not permission.
- No tool is exposed to ordinary chat in this task.
- No Whoosh'd code is changed.
- No Codexify runtime code is changed.
- No new canonical protocol tokens are created.
- No new model lifecycle state is created.
- No release-support claim is widened.

## Non-Goals

- No Whoosh'd runtime changes.
- No Codexify provider changes.
- No tool advertisement.
- No effective capability resolver implementation.
- No GGUF or MLX tool implementation.
- No llama.cpp or MLX server changes.
- No chat-template implementation.
- No structured-output parser.
- No new model registry.
- No provider identity proliferation.
- No hardcoded model allowlist.
- No routing/fallback implementation.
- No Command Bus or Agent Tool Loop changes.
- No runtime proof or release qualification.

## Deferred Questions

- Exact upstream llama.cpp tool-calling semantics including per-model chat
  template support for tools, GBNF grammar integration, and structured-output.
  (Verified at high level: llama.cpp server supports `tools` through its
  OpenAI-compatible endpoint with per-model chat templates; exact model-specific
  compatibility requires Stage 2D proof.)
- Exact upstream MLX-LM tool-calling support, if any.
  (Verified at high level: MLX-LM focuses on text generation; native tool
  calling may require structured-output/grammar approaches; exact capability
  requires Stage 2D proof.)
- Whoosh'd `InferenceAdapter` tool-transport contract shape.
- `WhooshdRuntimeProvenance` extension for tool-turn metadata.
- Codexify-side `whooshd_model_profile` tool-capability extension.
- Cross-repo `WHOOSHD_MODEL_REGISTRY` tool qualification field schema.
- Qualification receipt storage and staleness detection mechanism.

Each question requires a separate architecture-impact slice.

## Recommended First Implementation Proof (Stage 2D)

Based on current reconnaissance:

- **Runtime**: `llama_cpp` (via Whoosh'd's `LlamaCppAdapter`)
- **Transport mode**: Native (OpenAI-compatible `/v1/chat/completions` with
  `tools`)
- **Model target**: The smallest available GGUF model proven to have a
  compatible chat template, such as a small Qwen 2.5 or Gemma family GGUF
  available in the current local weight store at
  `/Volumes/Dev_SSD/whooshd/model-weights`.
- **Rationale**: llama.cpp server is the most mature local runtime for native
  tool calling. It has the strongest upstream evidence of OpenAI-compatible
  tool support, an existing Whoosh'd adapter (`LlamaCppAdapter`), and a
  straightforward path through HTTP forwarding. A small GGUF model minimizes
  memory pressure and cold-start time for the proof. The exact target should
  be the one available model at the current install that has the clearest
  upstream tool-calling documentation.
- **Not claimed**: that this proof generalizes to all GGUF models, all
  llama.cpp-served models, or all Whoosh'd targets. It is the narrowest
  useful first local tool-transport proof.

Stage 2D should be a separate implementation task with its own explicit
architecture-impact authorization. This contract does not implement it.
