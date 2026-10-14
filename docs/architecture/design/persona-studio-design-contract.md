# Lens Editor Design Contract

> Classification: design contract
> Status: binding for Lens Editor implementation and redesign work
> Scope: the Lens Editor's local workspace hierarchy and interaction boundaries
> Governing product boundary: [ADR-082](../adr/082-persona-profile-manifest-and-binding-authority.md)
> Parent documents: Native Presentation SDK Contract and Module Header / Secondary Pill-Nav Contract. Parent token and structural-layout canon prevail on conflict.

## Naming Layers

| Layer | Vocabulary | Examples |
|---|---|---|
| Product language | **Lens** | Nav entry `Lens`, page `Lens Editor`, frames `Lens Assistant` / `Lens Editor` |
| Internal implementation | **Persona** (unchanged) | `personaStudio` module, `PersonaStudioPage`, `persona-studio-*` test IDs, `/persona-studio` route |
| Canonical authority | **Persona Profile** (unchanged) | `PersonaProfileManifest`, `PersonaProfileBinding`, ADR-082 |

User-facing copy and accessibility labels are product language and use Lens.
Internal identifiers stay Persona until a structural change justifies them;
they are not a simplification target.

## Purpose

The Lens Editor is a configuration-first workspace for an authored Lens draft.
It replaces the former Profiles / Editor / Diagnostics rail with one practical
loop:

```text
describe or edit → local draft → inspect or test → explicit Save → acknowledged revision
```

The interface makes draft state and authority boundaries legible without
becoming a settings wall, fake chat product, or environmental-control console.

Its default path is the common authoring intent. Implementation mechanics are
disclosed on request rather than presented alongside it.

## Shell and Frame Ownership

`AppShell` owns the Codexify Dock, wallpaper/gradient scene, theme, global
spacing, and route containment. The `/persona-studio` route renders
`PersonaStudioPage` directly; it must not wrap the page in a third `FrameCard`.

`PersonaStudioPage` owns exactly two primary production `FrameCard` surfaces:

```text
Lens Assistant  |  Lens Editor
```

- Use the real `FrameCard` component and shared design tokens. Do not recreate
  prototype bezel or scene CSS.
- On wide layouts, Lens Assistant is the narrower column and Lens Editor is the
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

When a recognized change targets a section inside the Advanced disclosure, the
disclosure expands automatically. Build must never apply a value into a region
the author cannot currently see.

Build must not call a provider, normal Guardian chat, tool, retrieval,
connector, memory, or persistence API.

### Test

Test reuses the existing deterministic `PersonaPreviewPanel` against the
current unsaved draft. It is visibly distinct from Build and embedded inside
the Lens Assistant frame without a nested primary card or repeated `Draft
Preview` header.

Test is ephemeral, local-only, draft-aware, and independently clearable. It
must not create a Guardian thread, conversation history, memory write, model
request, tool execution, retrieval, connector call, or saved Lens change.

## Lens Editor Frame

The Lens Editor header contains the compact selected-profile menu, state
status, Revert, and Save actions. Duplicate / Save-as-new is a subordinate
profile-menu action.

Status is acknowledgment-bound:

- clean acknowledged draft: `Saved · rev N`;
- dirty acknowledged draft: `Unsaved changes · saved rev N`;
- no acknowledged baseline: `Unsaved draft`.

Save labels remain simply `Save`. The client must not predict a future revision,
including `Save rev N+1`. Revert delegates to the last acknowledged manifest
baseline and does not write the backend.

The header carries no projection tab row. The draft is presented as the Lens
form first; Manifest and Effective are reached through the Advanced disclosure.

### Default Path

The default Lens authoring path is the common intent an author reaches for
when shaping how Guardian should approach work:

1. Lens identity
2. Behavior / Instructions
3. Voice

Lens identity and Behavior / Instructions open by default. Voice is a
user-intent-level preference and stays on the common path, collapsed rather
than disclosed.

### Advanced Disclosure

Implementation-oriented mechanics sit behind a single explicit **Advanced**
disclosure at the end of the form. Opening it reveals, without removing
anything:

- Model — requested provider/model and detailed tuning;
- Capabilities — requested permissions and tool lists;
- Retrieval — retrieval tuning;
- Activation & Bindings — the non-portable Binding boundary;
- the **Manifest** and **Effective** inspections.

The disclosure is presentation reduction, not schema reduction. Every disclosed
field keeps its prior value, definition, and editing behavior, and all
advanced controls remain reachable from the same draft.

The disclosure uses an explicit `aria-expanded` toggle. It must be
state-independent of the draft: a Lens with advanced values set must not
surface them by default any more than a default Lens does.

### Manifest

Manifest is editable JSON for the same local authored draft. It includes
`apiVersion`, the selected profile's `profileIdentity`, identity, prompt,
model, voice, capabilities, and retrieval. It does not expose an editable
revision.

Valid JSON updates the same draft; Form edits regenerate its projection.
Invalid JSON remains in the text buffer with an inline error and cannot mutate
the draft. The editor rejects incompatible API versions, another profile
identity, and unknown fields such as bindings, credentials, Project authority,
or runtime grants. YAML import/export is out of scope.

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
- AppShell supplies module context; the Lens Editor supplies no additional Dock,
  wallpaper, theme controller, scene background, or page-wide footer.
- Lens Editor actions and profile context stay compact. Repeating profile
  identity in extra cards or bands is prohibited.
- Brief safety copy belongs with active Build/Test work, not a global banner.
- Progressive disclosure changes what is shown by default. It must not change
  what is stored, what is editable, or what any owning system treats as granted.

## Required Proof Surface

Implementation proof must demonstrate direct AppShell containment and exactly
two primary FrameCards; responsive two-column/stacked presentation; Build
local mutation receipts and highlights without autosave/runtime calls;
Build expanding the Advanced disclosure when it changes an advanced section;
ephemeral Test behavior; Manifest round-trip and invalid-manifest
preservation; unresolved Effective wording and non-authoritative Binding
presentation; acknowledgement-bound Save, failure preservation,
concurrent-edit handling, and Revert behavior; and that the Advanced
disclosure restores full editing capability without changing stored values.

## ADR Impact

The Lens Editor is aligned with ADR-082 and requires no new ADR. It changes
presentation and bounded local interaction only; it does not change
PersonaProfileManifest authority, PersonaProfileBinding authority, persistence,
resolver precedence, runtime capability, identity, memory, or release claims.

Guardian remains the primary runtime and assistant authority. A Lens shapes how
Guardian approaches work; it is not a separate autonomous agent.
