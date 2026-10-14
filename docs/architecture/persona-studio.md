# Persona Studio Architecture

Purpose: describe the production Persona Studio composition, local draft flow,
and authority boundary without treating configuration UI as runtime proof.

Last updated: 2026-10-14

Source anchors:

- `frontend/src/components/persona/layout/AppShell.tsx`
- `frontend/src/features/personaStudio/PersonaStudioPage.tsx`
- `frontend/src/features/personaStudio/PersonaPreviewPanel.tsx`
- `frontend/src/features/personaStudio/personaStudioStore.ts`
- `frontend/src/features/personaStudio/personaStudioApi.ts`
- `docs/architecture/adr/082-persona-profile-manifest-and-binding-authority.md`

## Purpose and Scope

The Lens Editor is a non-conversational configuration surface for a Lens. A
Lens changes the authored approach and configuration Guardian works under; it
is not a separate autonomous agent and does not replace Guardian, which
remains the primary runtime and assistant authority.

It keeps broad browser-local drafts while the backend persists the canonical
typed authored manifest, immutable positive revisions, and a server-owned
account binding under ADR-082.

Only a coherent backend-returned manifest/revision establishes saved Persona
truth. Browser localStorage provides draft/cache continuity and selection; it
does not establish canonical saved authority. The current runtime-bearing
projection remains limited to name, system prompt, model provider, model ID,
and temperature. Broad authored fields remain requested/inert until separately
implemented and proven enforcement seams exist.

The Lens Editor is not a chat, memory-writing, thread/history, provider-runtime,
or authority-granting surface.

## Naming Layers

Product language is **Lens**: the nav entry, page, frames, and form sections.
Internal implementation remains **Persona** — `personaStudio` module,
`PersonaStudioPage`, `persona-studio-*` test IDs, `/persona-studio` route — and
is not a simplification target. Canonical authority remains **Persona Profile**
(`PersonaProfileManifest`, `PersonaProfileBinding`, ADR-082).

## Current Implementation Status

| Surface | Status now | Meaning |
|---|---|---|
| AppShell route | runtime-active | `/persona-studio` is a first-class shell view; AppShell owns Dock, scene, theme, and route wrapper. |
| V2 workspace | frontend-active | `PersonaStudioPage` directly owns two canonical FrameCards: Lens Assistant and Lens Editor. |
| Build | frontend-local | A pure deterministic configurator mutates recognized fields in the selected local draft only, and expands the Advanced disclosure when it changes an advanced section. |
| Test | frontend-local preview | Existing deterministic, draft-aware preview is ephemeral and non-threaded. |
| Default path | frontend-active | Lens identity, Behavior / Instructions, and Voice are the common authoring surface. |
| Advanced disclosure | frontend-active | Model, Capabilities, Retrieval, Activation & Bindings, Manifest, and Effective are reachable behind one explicit disclosure without losing values. |
| Form / Manifest | frontend-local | Two views over the same authored draft; Manifest JSON is strict and excludes revision/bindings/credentials. |
| Effective | observational | Requested values can be inspected; no authoritative effective-config resolver is present. |
| Profile persistence | backend-active | Account-scoped full manifests and immutable revisions establish acknowledged baselines. |
| Bindings | server-owned | Account binding is separate from portable manifest content and has no V2 editor. |
| Runtime application | five-field only | Broad voice, capabilities, retrieval, and permissions remain non-executing. |

## Where It Lives in the Shell

The Lens Editor is a sibling AppShell view alongside Guardian, Dashboard,
Documents, Gallery, and Settings. It appears in AppShell navigation as `Lens`.

- Route: `/persona-studio`
- Nav entry: Lens
- Shell entry: AppShell navigation
- Route containment: AppShell renders `PersonaStudioPage` directly, without an
  outer FrameCard.

The page itself renders the two production FrameCards. AppShell remains the
only owner of global Dock, wallpaper/gradient, theme, and shell tokens.

## V2 UI Structure

```text
AppShell scene + Dock
└── /persona-studio route (nav entry: Lens)
    └── PersonaStudioPage
        ├── FrameCard: Lens Assistant
        │   ├── Build — deterministic local draft edits
        │   └── Test — embedded ephemeral preview
        └── FrameCard: Lens Editor
            ├── profile / acknowledgement actions
            ├── Lens identity
            ├── Behavior / Instructions
            ├── Voice
            └── Advanced disclosure
                ├── Model, Capabilities, Retrieval, Activation & Bindings
                └── Manifest | Effective
```

The desktop grid intentionally gives Lens Editor more width than Lens
Assistant; narrow viewports stack the two surfaces. No page-wide
status/footer band is rendered. Profile state, Revert, Save, and
Duplicate-as-new live in the Lens Editor action area.

Lens identity and Behavior / Instructions open by default. Voice is a
user-intent-level preference kept on the common path but collapsed. Model,
Capabilities, Retrieval, Activation & Bindings, Manifest, and Effective sit
behind one explicit Advanced disclosure. This replaces the retired top-level
Identity/Model/Voice/Prompt/Tools/Retrieval/Truth Matrix tab row.

The disclosure is presentation reduction only: no field, value, or editing
capability is removed. Build expands it automatically when a recognized change
targets an advanced section, so an applied value is never hidden.

## Local State and Persistence Flow

The frontend draft shape keeps identity, model, voice, prompt, tool/permission,
and retrieval fields. The store exposes `selectedProfile`, `savedRevision`,
`isDirty`, `updateSelectedProfile`, `saveSelectedProfile`,
`saveSelectedProfileAsNew`, and `resetSelectedProfile`.

1. The store loads recoverable local drafts/cache or seed drafts.
2. Account-scoped profile hydration supplies acknowledged manifests and saved
   revisions when available.
3. Form, valid Manifest JSON, and Build all invoke the same local draft update
   seam. None persists automatically.
4. Save submits the writable V1 authored manifest without a predicted revision.
5. A successful backend acknowledgement alone advances the saved baseline and
   displayed revision. A failed write leaves the draft dirty.
6. Concurrent browser edits made after submission are preserved when an
   acknowledgement arrives.
7. Revert restores the last acknowledged manifest when one exists; with no
   acknowledgement it does not discard the draft.

Build owns only ephemeral transcript/highlight state. Test owns only ephemeral
preview transcript state. Neither state is saved to the Persona manifest,
memory, chat history, or a Guardian thread.

## Manifest, Binding, and Effective Boundaries

The writable manifest projection includes `apiVersion`, `profileIdentity`,
identity, prompt, model, voice, capabilities, and retrieval. It deliberately
excludes `revision`, Binding records, credentials, Project authority,
connector grants, and runtime grants.

Valid JSON updates the selected local draft. Invalid JSON, unknown fields, an
incompatible API version, or a mismatched profile identity stays in the editor
buffer and does not corrupt the draft.

`PersonaProfileBinding` remains server-owned environmental authority. The
Activation & Bindings section is observational because no authoritative Binding
editor exists in this surface.

The Effective projection does not simulate availability, provider health,
connector authorization, connector health, Project bindings, capability grants,
or runtime effect. Where no resolver exists, it says so explicitly. Requested
is not effective.

## Runtime and Authority Limits

The current runtime seam can carry only:

- name;
- system prompt;
- model provider;
- model ID; and
- temperature.

Saving, reverting, validating, Build, Test, and inspecting a Persona Profile do
not invoke a model, normal Guardian chat, tool, retrieval, connector, TTS,
memory mutation, capability grant, or binding change. Selection in Studio does
not bind a thread or alter active runtime behavior.

## Proof and Limits

Focused component/store tests prove the page composition, deterministic
local Build behavior including automatic expansion of the Advanced disclosure,
the default path and its reachability guarantee, preview boundary, Manifest
round-trip and rejection, acknowledged revision behavior, failure preservation,
concurrent edits, and Revert. They are mocked/local code-path proof, not
authenticated-browser, live-backend, provider, resolver, or release
qualification.

### Component and State Flow

```mermaid
flowchart LR
    A["Lens form / Manifest / Build"] --> B["selected local draft"]
    B --> C["Test preview\nephemeral"]
    B --> D["explicit Save"]
    D --> E["profile API\nmanifest without revision"]
    E --> F["acknowledged manifest + revision"]
    F --> G["saved baseline / Revert"]
    H["server-owned Binding"] -. "not editable here" .-> B
    I["runtime resolver\nfive fields only"] -. "not resolved by V2" .-> B
```

## Deferred Work

V2 does not add model-backed configuration, Binding persistence/editor,
effective-config resolution, project pins, `@persona` aliases, connector
grants, capability enforcement, retrieval execution, YAML import/export, or
legacy-component cleanup. Those require separate authority, runtime, and proof
work before they can affect a product or release claim.
