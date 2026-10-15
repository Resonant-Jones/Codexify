# Persona Studio Design Contract v2

> Classification: design contract
> Status: binding for Persona Studio implementation and redesign work
> Scope: Persona Studio's local workspace hierarchy and interaction boundaries
> Governing product boundary: [ADR-082](../adr/082-persona-profile-manifest-and-binding-authority.md)
> Parent documents: Native Presentation SDK Contract and Module Header / Secondary Pill-Nav Contract. Parent token and structural-layout canon prevail on conflict.

## Purpose

Persona Studio is a configuration-first workspace for an authored Persona
Profile draft. V2 replaces the former Profiles / Editor / Diagnostics rail with
one practical loop:

```text
describe or edit → local draft → inspect or test → explicit Save → acknowledged revision
```

The interface makes draft state and authority boundaries legible without
becoming a settings wall, fake chat product, or environmental-control console.

## Shell and Frame Ownership

`AppShell` owns the Codexify Dock, wallpaper/gradient scene, theme, global
spacing, and route containment. The `/persona-studio` route renders
`PersonaStudioPage` directly; it must not wrap the page in a third `FrameCard`.

`PersonaStudioPage` owns exactly two primary production `FrameCard` surfaces:

```text
Studio Assistant  |  Configuration
```

- Use the real `FrameCard` component and shared design tokens. Do not recreate
  prototype bezel or scene CSS.
- On wide layouts, Assistant is the narrower column and Configuration is the
  wider column. On narrow layouts, they stack without horizontal overflow.
- The visible lower edge terminates in those two FrameCards. There is no
  page-wide footer, notification band, or additional workspace frame.

## Assistant Frame

### Build

Build is a deliberately narrow deterministic local configurator, not a
model-backed assistant. It accepts the approved prototype's recognized text
intents and maps them to typed draft fields only:

- analytical/evidence-led or warmer tone guidance;
- Claude/Anthropic or OpenAI/GPT model selection;
- lower or higher temperature;
- requested web and email permissions;
- voice enable/disable; and
- retrieval enable/disable.

Build returns a compact local receipt with changed field paths. It mutates only
the selected browser draft through the existing draft seam, briefly highlights
the affected Form field/section, and never auto-saves. An unrecognized request
leaves the draft unchanged and says so locally.

Build must not call a provider, normal Guardian chat, tool, retrieval,
connector, memory, or persistence API.

### Test

Test reuses the existing deterministic `PersonaPreviewPanel` against the
current unsaved draft. It is visibly distinct from Build and embedded inside
the Assistant frame without a nested primary card or repeated `Draft Preview`
header.

Test is ephemeral, local-only, draft-aware, and independently clearable. It
must not create a Guardian thread, conversation history, memory write, model
request, tool execution, retrieval, connector call, or saved Persona change.

## Configuration Frame

The Configuration header contains the compact selected-profile menu, state
status, Revert, and Save actions. Duplicate / Save-as-new is a subordinate
profile-menu action.

Status is acknowledgment-bound:

- clean acknowledged draft: `Saved · rev N`;
- dirty acknowledged draft: `Unsaved changes · saved rev N`;
- no acknowledged baseline: `Unsaved draft`.

Save labels remain simply `Save`. The client must not predict a future revision,
including `Save rev N+1`. Revert delegates to the last acknowledged manifest
baseline and does not write the backend.

### Form

Form is one projection of the selected draft. It uses collapsible sections:

1. Identity
2. Behavior / Prompt
3. Model
4. Voice
5. Capabilities
6. Retrieval
7. Activation & Bindings

The old permanent seven-tab editor is retired. Form values are authored
requests until an owning runtime/resolver proves otherwise.

### Manifest

Manifest is editable JSON for the same local authored draft. It includes
`apiVersion`, the selected profile's `profileIdentity`, identity, prompt,
model, voice, capabilities, and retrieval. It does not expose an editable
revision.

Valid JSON updates the same draft; Form edits regenerate its projection.
Invalid JSON remains in the text buffer with an inline error and cannot mutate
the draft. The editor rejects incompatible API versions, another profile
identity, and unknown fields such as bindings, credentials, Project authority,
or runtime grants. YAML import/export is outside V2.

### Effective

Effective is an honest inspection surface, not a simulated environment. It may
show authored/requested values, but must label unavailable provider/model,
connector, Project binding, capability-grant, authorization, health, and
runtime-effectiveness information as `Unavailable to resolve here`, `Not
resolved`, or equivalent neutral language. It must never relabel a persisted
request as effective runtime truth.

### Activation & Bindings

Activation & Bindings explains and observes the ADR-082 boundary. It has no
credential controls, connector grants, Project-pin editor, invocation alias
editor, fake authorization toggles, or fabricated binding state. Portable
manifest data and server-owned environment binding authority remain separate.

## Interaction and Material Rules

- Use existing buttons, inputs, textareas, dropdowns, segmented/pill controls,
  `material-slider`, `var(--shell-gap)`, and FrameCard material.
- AppShell supplies module context; Persona Studio supplies no additional Dock,
  wallpaper, theme controller, scene background, or page-wide footer.
- Configuration actions and profile context stay compact. Repeating profile
  identity in extra cards or bands is prohibited.
- Brief safety copy belongs with active Build/Test work, not a global banner.

## Required Proof Surface

Implementation proof must demonstrate direct AppShell containment and exactly
two V2 primary FrameCards; responsive two-column/stacked presentation; Build
local mutation receipts and highlights without autosave/runtime calls;
ephemeral Test behavior; Form/Manifest round-trip and invalid-manifest
preservation; unresolved Effective wording and non-authoritative Binding
presentation; and acknowledgement-bound Save, failure preservation,
concurrent-edit handling, and Revert behavior.

## ADR Impact

V2 is aligned with ADR-082 and requires no new ADR. It changes presentation
and bounded local interaction only; it does not change PersonaProfileManifest
authority, PersonaProfileBinding authority, persistence, resolver precedence,
runtime capability, identity, memory, or release claims.
