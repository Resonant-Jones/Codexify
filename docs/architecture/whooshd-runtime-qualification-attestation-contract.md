Purpose: Define the future, bounded evidence boundary required to determine whether the exact Whoosh'd execution target serving a request still matches a previously qualified proof identity. This is architecture reconciliation only; it does not add an attestation producer, consumer, capability projection, or release claim.
Last updated: 2026-08-09
Source anchors:
- docs/architecture/whooshd-model-tool-capability-boundary.md
- docs/architecture/provider-capability-contract.md
- docs/architecture/provider-tool-turn-boundary-contract.md
- docs/architecture/whooshd-control-plane-v1.md
- docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-strict-structured-tool-qualification-proof.md
- guardian/providers/whooshd_control_plane.py
- guardian/providers/whooshd_tool_adapter.py
- guardian/providers/whooshd_sidecar.py
- guardian/core/ai_router.py
- guardian/core/chat_completion_service.py
- Whoosh'd ref e191798be3a290b291e0878eac8309d8b6ce7130 (ResonantConstructs/Whoosh'd)

# Whoosh'd Runtime Qualification Attestation Contract

## Purpose

Define the evidence boundary that answers one deliberately narrow question:

> Is the exact execution target serving this request materially identical to
> the target that passed a recorded qualification proof?

This boundary prevents a future capability projection from treating the alias
`gemma-4-12b-it-qat-4bit` plus `mlx_vlm` as sufficient evidence when the
served artifact, runtime implementation, tokenizer, template, or structured
decoder may have changed.

## Scope

This is a docs-only, architecture-impact reconciliation for Stage 2F. It
defines the future producer, consumer, comparison, and invalidation boundary
for a Whoosh'd local-runtime qualification attestation. It does not:

- modify Whoosh'd `RuntimeProvenance` or any control-plane payload;
- add a Codexify parser, digest, qualification record, persistence, token, or
  capability producer;
- change `ModelCapability.TOOLS`, `RuntimeModel.supports_tools`, or
  `MlxVlmAdapter.supports_tools`;
- expose Guardian tools, change ordinary `task.tools`, or alter Stage 1
  advertised-subset authority; or
- claim a release-qualified or currently advertised tool capability.

## Current Truth

Stage 2D qualified one exact local target under strict structured generation:
the public alias `gemma-4-12b-it-qat-4bit`, the resolved
`mlx-community/gemma-4-12B-it-qat-4bit` artifact, `mlx_vlm`, MLX-VLM 0.6.2,
llguidance 1.7.6, the recorded tokenizer/template identity, and the recorded
strict JSON-Schema proof conditions. The proof receipt is human/audit evidence
for that identity; it is not live runtime authority.

Stage 2E is a latent Codexify transport for the same alias. Its guard checks
the current response provenance for the requested, advertised, and resolved
alias; `mlx_vlm`; `mlx-vlm`; `authoritative_registry`; `managed_sidecar`; and
non-streaming execution. Those checks are necessary containment, but they do
not establish the complete Stage 2D proof identity.

Whoosh'd currently owns local execution and routes each request through a
`RuntimeResolution`. Its `RuntimeResolution.provenance()` builds bounded
`whooshd.runtime.v1` metadata from route selection, adapter identity, and
per-request context. The current `MlxVlmAdapter` starts or probes an MLX-VLM
sidecar and forwards a sanitized request; it reports only configured model
metadata and health to its own `RuntimeModel` surface.

The actual MLX-VLM serving process holds the loaded model path, model object,
processor/tokenizer, inferred tool parser, package version, and structured
decoder integration at model-load/generation time. Its current health snapshot
can report loaded-model and loaded-parser labels, but it does not produce the
complete bounded qualification identity described here. Codexify cannot and
must not reconstruct those process-local facts from its configuration or by
cross-process filesystem/package inspection.

## Not Yet True

- There is no canonical `RuntimeQualificationAttestation` object or digest.
- No per-response provenance carries a reference to an attestation.
- No runtime endpoint, inventory surface, or health response proves the exact
  MLX-VLM package/build, llguidance version, tokenizer identity, template
  fingerprint, tool-parser/template fingerprint, or artifact revision.
- No machine-readable qualification record is compared against a live runtime.
- No `ModelCapability.TOOLS` projection consumes a match result.
- Runtime readiness, source registration, alias identity, and `whooshd_version`
  alone are not qualification evidence.

## Terminology

- **Source/model identity**: a managed registration, external source, registry
  entry, configured model alias, or similar source-of-intent record.
- **Resolved execution identity**: the concrete alias, artifact, runtime, and
  adapter selected for one request after routing.
- **Runtime implementation identity**: the Whoosh'd build, adapter semantics,
  serving runtime package, and structured-decoder implementation used to run
  the target.
- **Model protocol identity**: tokenizer implementation/identity, effective
  chat template, effective tool template/parser where distinct, and the
  constrained structured-output mechanism.
- **Qualification proof identity**: the immutable material identity described
  by a successful qualification proof.
- **Runtime qualification attestation**: bounded, current runtime evidence
  originated by Whoosh'd and bound to the loaded resolved target.
- **Request provenance**: bounded, content-free evidence describing the route
  and operational context that served one request.
- **Qualification record**: future Codexify-owned machine-readable policy
  record that names the proof identity it accepts; it is not an inventory.

## Existing RuntimeProvenance Boundary

### Producer and lifecycle

The current producer is Whoosh'd `RuntimeResolution.provenance()` in
`whooshd/routing.py`. It is a request/response provenance constructor, not a
loaded-runtime identity constructor. `whooshd/app.py` attaches its result to
completed non-streaming chat and generate responses after the selected adapter
returns. It builds the streaming value before visible output and serializes it
in `X-Whooshd-Runtime-Provenance`; current stream chunks intentionally keep
their OpenAI-compatible body shape and omit this field. Inventory may also
carry bounded provenance created by `inventory_provenance()`.

The producer synthesizes one payload from the selected `RuntimeResolution`,
the selected adapter, Whoosh'd package version, bounded correlation context,
and per-request execution flags. It is therefore request-scoped evidence of
the route that served work, not a proof that a static configured target is the
one actually loaded with all Stage 2D components.

### Current schema and Codexify consumer

`whooshd.runtime.v1` currently contains:

- `request_id`, `correlation_id`, `codexify_task_id`, `codexify_attempt_id`,
  and `whooshd_request_id`;
- `requested_model_id`, `advertised_model_id`, `resolved_model_id`, and
  optional `backend_reported_model_id`;
- `runtime_kind`, `adapter_name`, `resolution_source`, and `execution_mode`;
- `streaming`, `queued`, `batched`, and optional `model_lifecycle`; and
- optional `whooshd_version`.

Codexify's current consumer is
`guardian.providers.whooshd_control_plane.parse_whooshd_runtime_provenance`,
called by `ai_router` for response bodies and streaming response provenance.
It accepts only the exact v1 schema marker, bounded text, enumerated runtime
kind/source/mode/lifecycle values, and booleans. It projects only its named
fields into `WhooshdRuntimeProvenance`; unknown optional fields are ignored.
Malformed known fields, an unrecognized schema marker, unsafe text, or
unrecognized required enum values cause the entire provenance value to be
unaccepted. Whoosh'd's Pydantic producer is likewise additive and ignores
unknown optional fields.

The payload is content-free operational metadata: it does not include prompts,
completions, endpoint URLs, filesystem paths, process details, credentials, or
dependency inventories. That bounded purpose is correct and must remain true.
It proves route selection and request context today, but cannot currently
attest the artifact revision, quantization, runtime/decoder package builds,
tokenizer, effective template, tool parser, or strict structured protocol
implementation that bound Stage 2D.

## Identity Layers

The following layers are related but must not be merged into a universal model
registry:

| Layer | Authority | Role | Not sufficient because |
| --- | --- | --- | --- |
| Source/model identity | Whoosh'd registry, source records, and configuration | States intended source and public alias | It can diverge from the loaded process. |
| Resolved execution identity | Whoosh'd router and selected adapter | States the route selected for this request | It lacks material loaded-component fingerprints. |
| Runtime implementation identity | Whoosh'd serving runtime and adapter boundary | States code/packages that performed inference | A version label alone cannot identify model protocol. |
| Model protocol identity | Loaded MLX-VLM processor/tokenizer/template/parser | States how the model receives and constrains turns | It cannot be inferred safely from a public alias. |
| Qualification proof identity | Qualification evidence and future qualification record | States what was proven | It is historical, not proof of current serving state. |
| Request provenance | Whoosh'd response boundary | Ties a request to route and operational context | It is not yet a full qualification attestation. |

## Qualification Proof Identity

The Stage 2D proof identifies an exact resolved target, not a provider family
or a source registry row. Its immutable identity comprises the material
dimensions that can affect strict structured tool-turn behavior. The human
receipt documents the observed proof values and their evidence. A future
machine-readable qualification record must encode the accepted bounded values
or their canonical identity digest, not derive authority from the document.

The proof record must distinguish three facts: the artifact/protocol that was
tested, the transport/protocol behavior that was proven, and the target alias
through which that proof may be requested. An alias may be useful for binding
and diagnosis, but it is never a substitute for the remaining identity.

## Runtime Attestation Identity

The authoritative producer is **Whoosh'd at the actual serving-runtime
boundary**. The component that loads the model and its processor must measure
the component values it can directly observe; Whoosh'd binds that bounded
measurement to its resolved route and emits it. This preserves Whoosh'd's
ownership even where a managed MLX-VLM serving child process is the immediate
holder of the loaded tokenizer/template/package objects.

Codexify is the validating consumer. It may compare received bounded evidence
with a future qualification record, but it must not make configuration intent,
an inventory item, an `MlxVlmAdapter` model string, or a local package probe
stand in for actual execution identity.

An attestation is target-scoped, not provider-wide and not request-created. A
request needs a reference to the already retained attestation for the target
that actually served it.

## Required Attestation Dimensions

The target's qualification match requires the following categories. "Required"
means absent, malformed, unrecognized, or different evidence cannot match;
it does not say every value is currently available.

| Dimension | Qualification role | Current availability | Safe attested representation |
| --- | --- | --- | --- |
| Public invocation alias | Required binding and diagnosis | Per request | Bounded alias, not a path. |
| Resolved model identity | Required | Per request route | Bounded model/repository identifier plus artifact identity. |
| Artifact/snapshot revision or fingerprint | Required | Not currently in provenance; derivable at load from the loaded artifact/manifest | Revision plus bounded manifest/content fingerprint; never a raw path. |
| Quantization/artifact form | Required | Source/config hints exist; not live attested | Normalized quantization descriptor tied to the loaded artifact. |
| Runtime kind | Required | Per request | Canonical runtime-kind value. |
| Adapter identity and semantic build | Required | Name per request; build identity unavailable | Bounded adapter identifier plus version/build or semantic fingerprint. |
| Whoosh'd build | Required when its dispatch/provenance/forwarding behavior is material | Version per request; build identity may be unavailable | Bounded release/build identifier, not a dependency dump. |
| Serving runtime package/version | Required | Present in the serving process, absent from provenance | Package name plus normalized version/build identity. |
| Strict structured decoder/version | Required for strict transport | Present when used by the serving process, absent from provenance | Decoder identifier plus normalized version/build identity. |
| Tokenizer implementation/identity | Required | Present in loaded processor, absent from provenance | Class/implementation identifier plus tokenizer fingerprint where material. |
| Effective chat-template fingerprint | Required | Template is loaded/available in process, absent from provenance | Algorithm-scoped fingerprint only. |
| Effective tool template/parser fingerprint | Required when distinct from chat-template behavior | Parser label may be observable; fingerprint absent | Parser identifier plus fingerprint, or explicit absence if non-material. |
| Structured transport mode and mechanism | Required | Stage 2E request mode is known to Codexify; serving implementation identity is not attested | Canonical mechanism/profile identifier and version. |
| Qualification schema/protocol version | Required when it defines the proven grammar or ModelTurn semantics | Proof-record data today | Bounded schema/protocol identifier. |

The following are **informational only** for a qualification comparison unless a
future proof explicitly makes one material: request/correlation IDs, queue and
batch flags, current lifecycle/readiness, host/port, source-resolution label,
backend-reported model label, context limit, metrics, and timestamps. They may
explain a request but cannot preserve qualification after a required component
is unknown or changed.

## Safe/Bounded Representation

Attestation values must be machine-comparable but disclose no raw model paths,
prompts, completions, credentials, environment variables, user identity,
arbitrary dependency dumps, template/tokenizer text, weights, lockfiles,
process IDs, endpoint URLs, or timestamps.

Safe values include bounded public aliases and repository labels, normalized
runtime/package/parser names and versions, artifact revision labels, declared
quantization descriptors, fixed-size fingerprints, a bounded build identifier,
and a schema/version marker. A template or tokenizer fingerprint establishes
identity without returning content. A private artifact may use an
algorithm-scoped fingerprint and an opaque local artifact label rather than
its source path.

## Computation Lifecycle

The recommended lifecycle is:

```text
target initialization or successful reload
        -> serving runtime measures loaded components
        -> Whoosh'd normalizes bounded components
        -> canonical attestation identity is derived
        -> attestation is retained with the loaded resolved target
        -> each response carries only the current target reference
        -> Codexify compares it to a qualification record
```

This fits the current architecture better than per-request reconstruction. The
MLX-VLM serving process already loads the model and processor and keeps them in
its runtime cache; it can observe the tokenizer/template/parser at that
lifecycle point. Whoosh'd's managed `MlxVlmAdapter` already has a warmup and
health lifecycle, while `RuntimeResolution` is the existing route-binding
seam. A future producer should bridge the serving-process measurement into
that owned Whoosh'd boundary once per successful load/reload, not cause
Codexify to read another process's files.

Recompute after every successful target load, reload, process restart, model
switch, or material runtime initialization change. A failed/incomplete
measurement is not reusable proof; it is insufficient evidence. Per request,
the cost should be bounded lookup and serialization of a retained reference,
not filesystem scanning, dependency inspection, template hashing, or model
weight hashing.

## Attestation Canonicalization

The recommended representation is **structured bounded fields plus a
deterministic digest**. Structured fields allow safe mismatch diagnosis; a
digest makes compact equality and stale-proof detection deterministic. Either
alone is insufficient: fields alone make comparison/evolution fragile, while
an opaque digest alone prevents useful operator truth.

The attestation schema must define:

- an independent attestation schema/version marker;
- a fixed, named set of required proof-key fields and their normalized forms;
- deterministic field ordering and explicit handling of arrays/maps;
- explicit distinction among absent, `unknown`, and an observed value;
- a named/versioned digest algorithm and canonical serialization;
- exclusion of raw paths, timestamps, request/correlation IDs, prompts, and
  all other request-specific values from the identity digest; and
- a rule that unsupported or future required fields never collapse into a
  matching digest by omission.

No digest primitive is selected here. The current architecture has no
canonical attestation-digest algorithm, so choosing one is an implementation
task with a versioned schema decision. A qualification record and attestation
may compare structured fields as well as the digest; disagreement between
them is insufficient evidence, not a convenience fallback.

## RuntimeProvenance Integration Decision

**Decision: `RuntimeProvenance` should reference a separate,
target-scoped runtime qualification attestation.** It must not absorb all
proof-key material as ordinary request provenance, and a new parallel runtime
registry is not justified.

The separate object belongs with the loaded target inside Whoosh'd and is the
single source of current runtime identity. Existing `RuntimeProvenance` is the
right response carrier because it already binds the request to the actual
`RuntimeResolution`, is content-free, and is available in non-streaming bodies
and before streaming output. An additive optional reference can carry a
bounded attestation schema marker, deterministic identity digest, and safe
summary/binding fields without reclassifying every response field as static
proof identity.

The future operator surface may expose the same retained attestation summary
through an existing Whoosh'd inventory/health/control-plane read surface, but
that view must read the attached loaded-target object. It may not become a
second source of target truth.

## Versioning and Compatibility

`whooshd.runtime.v1` can remain valid for an additive optional attestation
reference: Whoosh'd v1 permits additive metadata and Codexify currently ignores
unknown optional fields. The reference itself needs its own versioned schema,
because its field set and canonicalization are qualification semantics rather
than request provenance semantics.

No `whooshd.control.v1` error-contract revision is required merely to add an
optional successful-response provenance reference. A future control-plane
major or explicit feature negotiation is required if an implementation makes
attestation mandatory for all callers, changes existing v1 meaning, or needs a
new authoritative endpoint with incompatible semantics. Old Whoosh'd instances
remain parseable as v1 provenance producers, but their missing attestation must
produce `INSUFFICIENT_EVIDENCE` for qualification—not an assumed match.

## Qualification Receipt vs Runtime Record

The Stage 2D proof receipt remains human-readable/audit evidence: it explains
what was tested, under which conditions, and why an exact identity was
qualified. It is not runtime authority and must not be parsed opportunistically
on completion paths.

A future **machine-readable qualification record** belongs in Codexify's
provider-capability/qualification policy layer, adjacent to the eventual
provider-specific effective-capability records. It should bind a qualification
record ID to the accepted proof identity and attestation schema/digest, the
receipt reference, proof scope, and any permitted transport profile. It owns
Codexify's decision to consume a proven capability; it does not mirror the
Whoosh'd model inventory, readiness, or loaded-target registry.

Whoosh'd owns the live attestation. Codexify owns the accepted qualification
record and comparison. This avoids a second runtime registry while preserving
the authority split.

Conceptually, future effective eligibility requires:

```text
qualification record exists
AND current Whoosh'd attestation matches it
AND runtime readiness allows execution
AND provider/model capability is permitted
AND Guardian request authority permits advertisement
```

## Match / Mismatch / Insufficient Evidence

These are conceptual comparison classifications, not new runtime-protocol
tokens:

| Result | Meaning | Future tool-capability consequence |
| --- | --- | --- |
| `MATCH` | Every required proof-key dimension is attested, recognized, and equal to the qualification record. | Necessary but not sufficient for projection; all other gates still apply. |
| `MISMATCH` | At least one required, recognized attested dimension differs. | Fail closed; no projection. |
| `INSUFFICIENT_EVIDENCE` | A required dimension, attestation reference, schema support, or safe comparison is absent, malformed, unknown, or unrecognized. | Fail closed; no projection. |

Neither `MISMATCH` nor `INSUFFICIENT_EVIDENCE` means model offline, runtime
warming, Guardian command denial, or provider request failure. Conversely,
runtime readiness does not turn insufficient evidence into a match.

## Qualification Invalidation

Qualification becomes stale whenever a material component changes or cannot
be shown to be unchanged. Material changes include:

- resolved model revision, artifact manifest/fingerprint, or quantization;
- runtime kind, adapter identity, or adapter semantic build;
- Whoosh'd dispatch/forwarding build when it participates in proven semantics;
- MLX-VLM or other serving runtime package/build;
- llguidance or other strict structured decoder/parser package/build;
- tokenizer implementation/identity;
- effective chat template or distinct tool template/parser fingerprint; and
- strict structured transport mechanism or qualified schema/protocol version.

An unrelated correlation-header implementation, queue depth, request ID,
readiness transition, host/port, or log-only change does not require
requalification unless it changes one of the proven protocol semantics. The
principle is materiality: invalidate when a change can alter the exact
generation, parsing, or structured-transport behavior the qualification
proved; do not invalidate for diagnostics that cannot.

## Readiness vs Qualification

Readiness answers whether a runtime can accept and execute work now. A
qualification match answers whether the loaded target still equals a proven
identity. They are independent axes:

- a ready runtime can be mismatched or insufficiently attested;
- a matched target can be temporarily unloaded, warming, degraded, or offline;
- source registration/inventory visibility is neither condition; and
- a qualification match does not itself authorize a provider or model
  capability projection.

## Guardian Authority Boundary

Attestation is evidence of serving identity, not a command grant. It does not
expand the Stage 1 advertised-tool subset, create a `task.tools` producer,
authorize a Command Bus invocation, or override policy. Guardian retains
authority to decide whether a capability is advertised and whether a proposed
command is allowed. The Stage 2E transport remains latent and unadvertised
until a separately authorized implementation proves all gates.

## Operator Truth Surface

Future diagnostics must distinguish proof status from live attestation and
runtime state without exposing sensitive internals. A safe surface should be
able to report, for the resolved public target:

- whether a qualification record exists;
- `MATCH`, `MISMATCH`, or `INSUFFICIENT_EVIDENCE`;
- a bounded reason such as `template_fingerprint_differs` or
  `decoder_version_unavailable`;
- safe expected/observed identifiers or digest prefixes only when policy allows;
- attestation schema/version and the request/response provenance linkage; and
- readiness as a separate state.

It must not show raw paths, templates, tokenizer contents, dependency dumps,
prompts, completions, credentials, or user data. A green readiness indicator
must never imply qualification, and a qualification result must never imply
Guardian authority.

## Cross-Provider Boundary

The provider-neutral capability architecture needs the concept of an effective
qualified capability, not Whoosh'd's local artifact identity model. Whoosh'd
requires detailed runtime attestation because the local stack owns and can
inspect its own serving runtime across a process boundary. A cloud or native
provider may have different trustworthy evidence—such as provider-signed
release/model identities, explicit feature contracts, or provider-specific
proofs—and different lifecycle semantics.

Provider-specific evidence remains below the Guardian semantic tool-turn and
authority boundaries. This contract does not impose MLX-VLM fingerprints,
local filesystem semantics, or Whoosh'd control-plane fields on DeepSeek,
OpenAI, or another provider.

## Invariants

- Whoosh'd remains one provider identity and owns actual local execution
  identity truth.
- Codexify consumes and validates that truth; its configuration is not runtime
  attestation.
- Source registry identity, alias, runtime kind, and Whoosh'd version alone
  are insufficient.
- Attestation is bound to the actual resolved execution target.
- Expensive identity computation occurs at target initialization/reload, never
  by Codexify during a completion request.
- Guardian must not inspect Whoosh'd packages, model files, tokenizer files,
  templates, or Python metadata per request, or infer runtime identity from
  local configuration.
- Missing required evidence and mismatches fail closed.
- Qualification proof, live attestation, readiness, capability projection, and
  Guardian authority remain separate.
- No `ModelCapability.TOOLS` projection, `supports_tools` change, ordinary
  `task.tools` change, Command Bus change, or release-support claim is made by
  this contract.

## Non-Goals

- Implementing an attestation producer, cache, endpoint, or parser.
- Selecting a digest algorithm or writing digest code.
- Creating the machine-readable qualification record or persistence schema.
- Probing a model, loading/restarting a runtime, installing packages, or
  qualifying a second model.
- Adding UI, runtime-protocol tokens, Guardian exposure, provider routing, or
  recursive tool-loop behavior.
- Replacing existing model inventory, model profiles, or Whoosh'd routing.

## Current Gaps

The current local implementation has no authoritative retained object that
binds the loaded MLX-VLM process's artifact revision/quantization, package
versions, tokenizer, template, parser, and strict structured mechanism to the
Whoosh'd `RuntimeResolution`. Codexify's v1 parser also has no attestation
reference field and no qualification-record comparator. The Stage 2D document
contains the historic proof values, but cannot prove that a later request is
served by the same material target.

Until those gaps are closed with separate authorization, Stage 2E's exact
alias/runtime guard remains a necessary transport containment check only. It
cannot authorize a public capability advertisement.

## Recommended Implementation Slice

**Stage 2F.1 — Implement the bounded Whoosh'd attestation producer and
Codexify consumer/validation seam defined here.**

That separately authorized slice should first define the versioned attestation
shape, compute it at successful target initialization/reload from the serving
runtime's directly observable state, retain it with the target, reference it
from the existing `RuntimeProvenance` carrier, extend Codexify's bounded parser,
and prove absent/malformed/mismatched behavior fails closed. It must not add
`ModelCapability.TOOLS`, `supports_tools`, capability advertisement, or
Guardian tool exposure until a later approved qualification-record and
effective-capability projection slice.
