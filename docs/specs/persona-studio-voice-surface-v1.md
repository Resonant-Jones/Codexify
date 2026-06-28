# Persona Studio Voice Surface V1

## Purpose

Define the implementation-facing contract for the Persona Studio Voice surface and the bounded Studio Guide V1 helper.

This spec is a surface-boundary contract. It does not claim broader release support than the current Codexify truth surface. `docs/architecture/00-current-state.md` remains authoritative for current supported-path reality.

## Current-State Guardrail

Codexify is in local-first beta hardening on `main`.

The currently supported path remains the local Docker Compose stack with local-only provider posture. This spec may define future-safe response shapes for multiple providers, but those shapes are not by themselves proof that multiple cloud providers are presently supported in the release promise.

## Scope

This contract covers:

- Persona Studio ownership of voice selection and binding
- Provider-view ownership of provider-native voice creation and asset management
- Studio Guide V1 as a bounded drafting helper
- Canonical example payloads for provider discovery and ephemeral preview

This contract does not implement routes, frontend components, provider adapters, or persistence.

## Persona Studio Boundary

Persona Studio is a configuration surface.

It is:

- not chat
- not memory-bearing
- not a thread/history surface
- not a provider-specific voice lab
- not a durable audio asset management surface

### Persona Studio owns

Persona Studio owns the common-path configuration steps required to bind a usable voice to a persona draft:

- provider selection
- preset voice selection
- generic runtime voice controls
- preview
- persona binding
- truthful capability and availability readback

### Generic runtime voice controls allowed in Persona Studio

Only portable controls that can be represented honestly across providers belong here:

- speed
- style or delivery preset when exposed as a portable control
- interruptibility if voice runtime semantics require it
- other generic runtime-facing controls that do not collapse into vendor-specific tuning

If a control is provider-native and cannot be normalized truthfully, it must stay out of Persona Studio V1.

## Provider-View Boundary

Provider-specific advanced views own provider-native voice creation and provider asset management.

### Provider views own

- cloning
- reference audio upload or recording
- provider-native voice generation
- provider asset management
- provider-auth/account state
- provider-native tuning knobs that do not normalize honestly

### Provider-view output contract

Provider views may create or manage voice assets, but Persona Studio V1 only consumes provider-exposed selectable voices and generic capability truth. Persona Studio must not require inline provider-native creation steps to complete the common path.

## Studio Guide Boundary

Studio Guide V1 is a bounded drafting helper attached to Persona Studio draft editing.

It is:

- bounded
- deterministic or rules-driven in V1
- draft-state aware
- sparse and event-driven

It is not:

- chat
- memory-bearing
- a threaded assistant
- an autosave surface
- a silent rewriting engine

### Studio Guide may

- inspect current unsaved draft state
- surface missing or contradictory instructions
- propose compact edits
- ask a short clarifying question tied to the current draft

### Studio Guide may not

- create chat history
- persist conversational state
- write memory
- autosave edits
- silently mutate persona fields
- behave like a general assistant surface

## Canonical Discovery Contract

Persona Studio Voice V1 depends on read-only discovery surfaces plus an ephemeral preview action.

The canonical discovery surface includes:

1. provider registry response
2. per-provider capability response
3. per-provider selectable voice list response
4. ephemeral preview response

These payloads must be stable, explicit, and fail-soft.

## Canonical Response Semantics

### Provider classification

Each provider must be classified explicitly:

- `local`
- `cloud`

Do not infer classification from label text or from the presence of credentials.

### Availability truth

Each provider response must expose current usability truth without inventing success:

- `available`
- `degraded`
- `unavailable`

Definitions:

- `available`: provider is usable now for the surfaced capability
- `degraded`: provider exists but some required dependency, feature, or capability is missing
- `unavailable`: provider exists in the registry but is not currently usable

### Capability flags

Capabilities must be explicit booleans, not inferred from missing fields:

- `presetVoices`
- `cloning`
- `promptDefinedVoice`
- `preview`

### Selectable voices

The selectable voice list must include only voices Persona Studio can bind directly in V1.

Do not include:

- raw provider asset inventories that require provider-native editing
- draft-only provider artifacts that cannot be bound yet
- hidden or internal-only voice assets

## Canonical Payload Notes

The example payloads in:

- `docs/specs/examples/persona-studio-voice-providers.example.json`
- `docs/specs/examples/persona-studio-voice-preview.example.json`

are normative examples for shape and semantics.

## Degraded and Unavailable States

Frontend behavior must fail soft when the backend returns incomplete provider capability or voice availability truth.

### Degraded examples

Examples of truthful degraded states:

- provider is registered but credentials are missing
- provider is reachable but preview is unsupported
- provider exists but preset voice inventory is temporarily unavailable
- provider exists but only provider-native generation is available, so Persona Studio has no selectable voices

### Unavailable examples

Examples of truthful unavailable states:

- provider registry entry exists but the adapter is disabled
- provider requires a service not running in the current environment
- provider is outside the current supported local-only posture and intentionally exposed as unavailable or omitted

## Preview Contract

Preview is an explicit ephemeral action used to validate a selected preset voice and generic runtime settings.

### Preview must be

- immediate-play oriented
- non-persistent
- unlinked from chat history
- unlinked from message ids
- unlinked from persona save/write state

### Preview must not

- create chat history entries
- attach durable audio assets to message history
- mutate persona state
- pretend success when the provider does not support preview

## Ownership Summary

### Persona Studio owns

- provider selector
- preset voice selector
- generic runtime voice settings
- preview action
- voice binding summary for the current draft

### Provider views own

- cloning workflows
- reference-audio flows
- provider-native voice generation
- provider asset lifecycle management

### Studio Guide owns

- bounded draft guidance only

## Implementation Notes

### One-local / multi-cloud policy

The contract must support a registry shape that can describe one local provider and multiple cloud-capable providers without forcing the frontend to change structure.

Current release truth is still local-only. Therefore:

- the supported path may expose exactly one usable local provider
- cloud providers may be absent
- cloud providers may appear as degraded or unavailable
- example multi-provider payloads are contract examples, not present-tense release proof

### Fail-soft frontend behavior

Persona Studio must remain structurally stable when discovery data is incomplete.

The frontend should:

- render provider rows even when some are degraded
- show truthful availability reasons
- render empty or unavailable preset states without collapsing the panel
- keep advanced provider workflows behind the provider-view CTA

The frontend must not:

- invent provider capabilities
- hide degraded truth behind generic success language
- replace missing voice lists with misleading fake presets

### Preview is ephemeral

Preview validates a possible binding but does not commit one.

Preview:

- may return immediately playable media metadata
- may reflect current selected provider, selected voice, and generic runtime options
- must not write persona state or durable chat-linked media state

## Out of Scope for V1

- inline voice cloning in Persona Studio
- inline reference-audio upload in Persona Studio
- inline provider-native voice generation in Persona Studio
- conversational Studio Guide behavior
- memory-bearing Studio Guide behavior
- autosave or silent draft mutation by Studio Guide

## Acceptance Notes For Downstream Tasks

Downstream backend and frontend tasks should treat these examples and boundaries as the contract anchor for:

- provider discovery routes
- capability readback routes
- selectable-voice routes
- ephemeral preview route shape
- Persona Studio Voice panel layout stability
- bounded Studio Guide behavior
