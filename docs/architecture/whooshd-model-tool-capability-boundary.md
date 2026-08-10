Purpose: Define the architecture by which Codexify determines whether one exact Whoosh'd model target is qualified to participate in the canonical Guardian tool-turn protocol.
Last updated: 2026-08-09
Source anchors:
- docs/architecture/provider-tool-turn-boundary-contract.md
- docs/architecture/provider-capability-contract.md
- docs/architecture/agent-tool-loop-contract.md
- docs/architecture/whooshd-model-profiles.md
- docs/architecture/whooshd-control-plane-v1.md
- docs/architecture/whooshd-runtime-qualification-attestation-contract.md
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
- **Source record identity**: An origin-specific record that contributes model
  identity and evidence. Examples are a managed `RegisteredModel`, an
  external-route `ExternalModelInventoryEntry`, and a configured
  `RegistryModelEntry`. It is not the universal qualification subject.
- **Resolved execution target**: The exact model/runtime target selected after
  source records converge through model/runtime resolution. It binds the
  invocation alias to the artifact, runtime engine, adapter, template, and
  other material execution dimensions available at that seam.
- **Qualification proof identity**: The evidence-bound identity of one resolved
  execution target. It is the comparison key used to decide whether a previous
  qualification receipt is still current.
- **Tool-qualified**: An exact resolved execution target has current evidence proving it can
  participate in the canonical bounded tool loop.
- **Tool-eligible**: A tool-qualified resolved execution target is also currently runnable and
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

## Provider vs Runtime vs Resolved Execution Target

This contract normatively separates three layers beneath the Whoosh'd provider
identity:

1. **Provider** (`whooshd`): the API surface reachable at
   `http://host.docker.internal:8000`. One provider identity.

2. **Runtime engine** (`llama_cpp`, `mlx_lm_server`, etc.): the inference
   execution backend. Different engines have different tool-transport
   capabilities. Engine capabilities are NOT model capabilities.

3. **Resolved execution target**: the exact selected combination of invocation
   alias, source-record evidence, artifact, quant, engine, adapter, chat
   template, and tokenizer. Tool qualification attaches HERE, not at the
   provider or engine level.

Codexify must route to `whooshd` → `exact invocation alias` → `resolved
execution target` → `effective capability view for that target`. No new
provider identities are created.

## Model-Origin Identity and Resolution Convergence

Whoosh'd has several legitimate model-origin surfaces. They carry different
evidence and must not be collapsed into one universal model identity:

- **Managed model-store registration**: `RegisteredModel` is the durable
  model-store representation. Its `model_id`, managed path, detected format,
  candidate lineage, and inspection evidence describe a managed artifact; its
  presence does not make it runnable or tool-qualified.
- **External weight-route inventory**: `ExternalModelInventoryEntry` is the
  read-only representation of a model found through a configured external
  route. Its public `id` (the current external-route public invocation ID),
  `model_id`, route, path, format, runtime hint, and route metadata identify
  that external discovery result. It remains an external-route inventory
  record, not a universal qualification identity.
- **Configured/runtime registry**: `RegistryModelEntry` is the YAML/static
  routing descriptor. Its configured alias, path or repository reference,
  engine, format, modalities, and warm policy contribute configured routing
  evidence; it is not a durable model-store record.
- **Runtime selection**: `routing.RuntimeResolution` is the current runtime
  seam that retains the selected adapter plus requested, advertised, and
  resolved model aliases and the resolution source. It is useful evidence of
  the selected execution path, but it does not yet carry the complete artifact,
  template, tokenizer, parser, or runtime-build identity needed for a
  qualification key.

The conceptual convergence is therefore:

```text
managed model identity --------┐
                               │
external model identity -------┼--> model/runtime resolution
                               │             |
configured model identity -----┘             v
                                     exact resolved target
                                              |
                                              v
                                      tool qualification
                                              |
                                              v
                                     runtime eligibility
                                              |
                                              v
                                       Guardian authority
```

The qualification subject is the **exact resolved execution target selected by
Whoosh'd**. A source record supplies evidence that helps establish that target;
no one source record, including `ExternalModelInventoryEntry.id` (or a future
field named `public_id`), independently defines it. This is a conceptual
clarification only. It creates neither a new runtime target type nor a new
source-of-truth registry.

### Identity layers

| Layer | Current examples | Qualification role |
| --- | --- | --- |
| Source record identity | `RegisteredModel.model_id`; external inventory `id`/`model_id`/route; configured `RegistryModelEntry` alias | Supplies provenance and source-specific artifact/routing evidence. |
| Resolved execution target identity | `RuntimeResolution` aliases, resolution source, selected adapter/runtime; resolved artifact/template details where available | Defines which concrete execution path is under evaluation. |
| Qualification proof identity | A receipt binding the full material target dimensions listed below | Determines whether a previous proof is applicable or stale. |

This distinction permits heterogeneous managed, external, and configured model
origins to use one qualification system without pretending that they are the
same inventory population.

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

## Exact Resolved-Target Qualification

Tool qualification requires evidence that the exact resolved execution target
— including its specific artifact, quant, tokenizer, runtime, adapter, and
chat template — can:

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

## Qualification Evidence and Proof Identity

A future qualification receipt must bind strongly enough to detect material
target drift. At minimum, its proof identity must record, or explicitly mark
as unavailable:

| Dimension | Required evidence posture | Current implementation gap |
| --- | --- | --- |
| Public invocation alias | The exact alias used on the request. | `RuntimeResolution` retains requested/advertised/resolved aliases. |
| Model origin/source kind | `managed`, `external`, `configured/static`, or another supported source. | Current provenance records a resolution source, but no canonical qualification source-kind field exists. |
| Artifact/model identity | Managed `model_id`, external `model_id`, configured repository/path, or equivalent immutable artifact identifier. | No universal artifact-identity field is carried through runtime provenance. |
| Artifact location | Exact managed path, external resolved path, or configured path where that path is material. | Runtime provenance does not retain a path; path handling differs by origin. |
| Revision or hash | Upstream revision, immutable manifest/hash, or artifact hashes when available. | No runtime receipt field or invalidation mechanism exists. |
| Quantization | Exact quant/variant where applicable. | Registry/inventory metadata may have it, but the runtime/provenance seam does not bind it universally. |
| Runtime/engine and adapter | Exact runtime kind, adapter kind/name, and execution mode. | Current runtime provenance carries these values, but no qualification receipt consumes them. |
| Runtime version/build | Runtime binary/package/build evidence sufficient to detect behavioral drift. | Whoosh'd version alone is insufficient; the adapter/upstream runtime build is not uniformly captured. |
| Tokenizer identity | Tokenizer artifact, revision, or content hash when tokenization is material. | No canonical runtime provenance field exists. |
| Chat-template identity | Template name/revision/hash, including any tool-format rendering behavior. | No canonical runtime provenance field exists. |
| Tool parser/template identity | Native parser version or strict structured parser/template identity. | `InferenceAdapter` has no tool-transport/parser contract. |
| Structured grammar/parser identity | Grammar/schema/parser identifier when structured transport is used. | No current grammar/parser or receipt field exists. |
| Transport mode | The exact `native` or `strict structured` path actually tested. | No transport-mode enum or producer exists. |
| Qualification result and time | Pass/fail/degraded result, Stage 2A contract version, proof timestamp, and receipt provenance. | No qualification persistence or producer exists. |

These are evidence requirements, not a demand that every current runtime type
already expose every dimension. Missing dimensions are explicit implementation
gaps; this task does not add a data structure, persistence schema, token, or
runtime field to fill them.

## Qualification Invalidation

Tool qualification must not silently survive material changes to the resolved
execution target or its proof identity. Prior evidence is considered stale
when any of the following change:

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
- Qualification attaches to an exact resolved execution target, not the
  provider name or any one source inventory record.
- `ExternalModelInventoryEntry` remains an external-route inventory
  representation; its public ID is never the universal qualification target.
- `RegisteredModel` remains a managed model-store representation.
- Managed, external, and configured source records may contribute evidence but
  do not create separate model-capability systems.
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

### Local inventory receipt — 2026-08-09

Read-only inspection used the local Whoosh'd checkout
`/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` at
`e191798be3a290b291e0878eac8309d8b6ce7130` (branch
`codex/cwc-007-control-error-contract`). The checkout has an unrelated
untracked `.venv311/`; it was not modified. Current `GET /v1/models` and
`GET /models` at `127.0.0.1:8000` advertise exactly one non-stub local model:

| Evidence | Observed value |
| --- | --- |
| Public invocation alias | `gemma-4-12b-it-qat-4bit` |
| Source origin | `configured/static`; the running inventory reports `resolution_source: authoritative_registry` and the local configuration is a `RegistryModelEntry`. |
| Underlying artifact/model identity | `mlx-community/gemma-4-12B-it-qat-4bit`, evidenced by the installed artifact directory and the Codexify model profile. |
| Exact artifact identity | MLX/safetensors snapshot: `model-00001-of-00003.safetensors`, `model-00002-of-00003.safetensors`, and `model-00003-of-00003.safetensors`, with `model.safetensors.index.json` at `/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit`. This is not a GGUF artifact. |
| Quantization | `QAT 4-bit`, as named by the configured alias and display name. |
| Resolved configured path | `/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit` |
| Runtime / adapter | `mlx_vlm` / `MlxVlmAdapter` (`adapter_name: mlx-vlm`, `execution_mode: managed_sidecar`). |
| Current status | Advertised by the authoritative registry, but `GET /models` reports `loaded: false` and the model provenance reports `model_lifecycle: unloaded`. `GET /health` is ready with no active model; this is inventory/readiness evidence, not an inference or tool proof. |
| Template evidence | The installed `chat_template.jinja` contains `tool_calls`, `tool_responses`, `tool_call_id`, `<|tool_call>`, and `<|tool_response>` handling. Its observed SHA-256 is `36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0`. |
| Tool-parser evidence | The current `MlxVlmAdapter.list_models()` reports `supports_tools=False`; no Whoosh'd native tool parser or strict structured parser is presently exposed. The template alone is not parser or qualification evidence. |

The inspected configured model registry, current endpoint inventory, model-store
code, external-route code, model resolver, routing seam, adapters, and their
managed/external resolution tests establish origin and selection vocabulary.
They do not establish an actual local `llama_cpp` execution target: no GGUF
file was found under the current documented weight roots, and the repository's
Qwen GGUF configuration is an example/validated configuration whose referenced
`models/gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf` is absent from this machine.

### Pinned Stage 2D target

Stage 2D will qualify **only**:

```text
gemma-4-12b-it-qat-4bit
using: mlx_vlm / MlxVlmAdapter
with: mlx-community/gemma-4-12B-it-qat-4bit,
      model-00001-of-00003.safetensors + model-00002-of-00003.safetensors
      + model-00003-of-00003.safetensors (QAT 4-bit)
through: the recorded MLX-VLM JSON-Schema grammar transport (qualified only
         for the exact proof identity)
```

**Qualification status: qualified for the exact recorded proof identity only.**
The target is pinned because it is the
only exact local model/runtime combination currently advertised by Whoosh'd,
has a configured deterministic invocation alias and resolved artifact path,
and its installed template has concrete tool-turn rendering evidence. It is
not the ideal small native `llama_cpp` proof target; no actual local GGUF path
is currently advertised or present. Selecting a hypothetical Qwen or "any
GGUF" would substitute configuration/examples for local model truth.

### Stage 2D qualification receipt — 2026-08-09

The local live proof is recorded in
[`2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-strict-structured-tool-qualification-proof.md`](proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-strict-structured-tool-qualification-proof.md).
It proved a generation-time MLX-VLM JSON-Schema grammar constraint and passed
the bounded semantic fixture for the exact recorded Gemma artifact, MLX-VLM
0.6.2, llguidance 1.7.6, tokenizer/template, and schema identity. No schema
weakening occurred.

This result means only: the exact Stage 2D proof identity for
`gemma-4-12b-it-qat-4bit` demonstrated the semantic behavior required for a
future strict-structured Whoosh'd tool transport under the recorded
runtime/template identity. It does not say Whoosh'd, MLX, MLX-VLM, Gemma, or
`MlxVlmAdapter` supports tools generally; it does not populate
`ModelCapability.TOOLS`, change `MlxVlmAdapter.supports_tools`, expose a
Guardian capability, grant command authority, or implement production
transport. A separate authorized, identity-pinned implementation slice must
consume this evidence while preserving the Stage 1 advertised-subset gate.

### Stage 2E implementation status — 2026-08-09

Stage 2E now implements a latent, Guardian-side transport adapter only for the
exact Stage 2D proof identity: local provider with
`LOCAL_PROVIDER_VENDOR=whooshd`, alias `gemma-4-12b-it-qat-4bit`, and exactly
one canonical tool whose flat, closed input schema is within the recorded
subset. It sends a non-streaming OpenAI-compatible request using strict
`response_format.json_schema` ModelTurn grammar and deterministic sampling
settings. It never sends native `tools`, `tool_choice`, or function-call
fields.

The response parser accepts only one complete JSON ModelTurn object, rejects
prose, fences, alternate shapes, duplicate fields, and repair attempts, and
checks a tool decision's returned runtime provenance before the existing Stage
1 advertised-subset gate can invoke anything. Continuation is ordinary
assistant/user context containing the selected command, arguments, and result;
it carries no provider-native tool-call identifier or new authority. A second
tool decision remains the existing bounded-loop failure.

No-tools local chat remains on its prior stream path. Multiple tools,
unsupported schemas, a non-identity target, malformed output, or provenance
mismatch fail closed; this does not advertise a capability, change
`MlxVlmAdapter.supports_tools`, update a model/profile/registry, or make a
release claim. This implementation consumes the Stage 2D receipt but does not
repeat live runtime proof; the runtime contract still cannot attest the pinned
MLX-VLM package, tokenizer, or template fingerprint per response.

### Stage 2F attestation requirement — 2026-08-09

[`whooshd-runtime-qualification-attestation-contract.md`](./whooshd-runtime-qualification-attestation-contract.md)
defines the remaining runtime-truth boundary. Stage 2E's alias and current
runtime-provenance guard is necessary containment, but it is not sufficient
for final capability advertisement: the current response cannot attest all
material Stage 2D proof-key dimensions, including artifact revision/quant,
runtime and structured-decoder builds, tokenizer identity, and effective
template/parser fingerprints.

Before this target can ever become an effective capability, Whoosh'd must
originate an attestation for the exact resolved execution target and Codexify
must establish a `MATCH` against a future machine-readable qualification
record. Missing or mismatched material evidence must fail closed. This is not
implemented by Stage 2F, does not change `ModelCapability.TOOLS`,
`RuntimeModel.supports_tools`, `MlxVlmAdapter.supports_tools`, ordinary chat,
or Guardian authority, and does not make the latent Stage 2E transport public.

### Stage 2F.1a producer status — 2026-08-09

Stage 2F.1a is implemented in Whoosh'd (read-only from Codexify's view) at
commit `d08e3261d8ed2217b9c258bb783138fc6a06df9f`. The producer now emits a
target-scoped qualification-attestation reference through the existing
`RuntimeProvenance` (`whooshd.runtime.v1`) when complete evidence exists;
incomplete runtimes emit no qualification-grade digest. The producer's
`tokenizer.identity_fingerprint` is computed from the parsed
`tokenizer_config.json` via a documented canonical re-serialization
(sorted keys, compact separators, `ensure_ascii=False`, UTF-8), then
SHA-256, prefixed `sha256:`.

### Stage 2F.1b pause / resume status — 2026-08-09

Stage 2F.1b (the Codexify half of the attestation boundary) paused at the
explicit evidence-completeness gate because the original Stage 2D receipt
did not pin the producer-compatible `tokenizer.identity_fingerprint` value
(it recorded the raw-file SHA only).

The supplemental reconciliation proof
[`2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-tokenizer-identity-reconciliation-proof.md`](proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-tokenizer-identity-reconciliation-proof.md)
now provides that canonical tokenizer identity, with byte-exact reproduction
against the unchanged Stage 2D artifact. The expected
`tokenizer.identity_fingerprint` for the Stage 2D qualified target is
`sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264`.

Stage 2F.1b may now resume, reading **both** the original Stage 2D
proof and the supplemental reconciliation proof, and may then construct
the complete machine-readable qualification record and continue with
the Codexify attestation comparator.

No capability projection exists yet. `ModelCapability.TOOLS`,
`RuntimeModel.supports_tools`, and `MlxVlmAdapter.supports_tools` are
unchanged. No canonical runtime protocol token has been added. No
release-support claim has been widened. Stage 1 remains the sole
command-authority gate.
