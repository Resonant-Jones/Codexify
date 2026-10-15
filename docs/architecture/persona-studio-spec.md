# Product Spec — Lens Editor

## Architecture Status

[ADR-082](./adr/082-persona-profile-manifest-and-binding-authority.md) governs Persona Studio persistence and authority. The canonical authored object is the typed `PersonaProfileManifest`; JSON is a serialization format, not an authority source. Browser localStorage and a database JSON blob are not authority sources.

`PersonaProfileManifest` records requested configuration. A separate, server-owned `PersonaProfileBinding` records server-derived or server-validated account, Project, participant, connection, activation, and environment mappings. Imports cannot self-assign bindings, credentials, or execution permission.

Current code-path scope remains narrower: Studio maintains a broad browser-local draft, while backend persistence and system-profile resolution carry only name, system prompt, model provider, model ID, and temperature. Broader fields are authored intent, not current runtime enforcement or release support.

## Naming Layers

This surface uses three deliberately different vocabularies. They are not
inconsistent with each other.

| Layer | Vocabulary | Examples |
|---|---|---|
| Product language | **Lens** | Nav entry `Lens`, page `Lens Editor`, frames `Lens Assistant` / `Lens Editor`, form section `Lens identity` |
| Internal implementation | **Persona** (unchanged) | `personaStudio` module tree, `PersonaStudioPage`, `persona-studio-*` test IDs, `personaStudioStore`, `personaStudioApi` |
| Canonical authority | **Persona Profile** (unchanged) | `PersonaProfileManifest`, `PersonaProfileBinding`, ADR-082 |

Internal identifiers remain Persona until a structural change justifies
renaming them. They are implementation detail, not product vocabulary, and
they are not accessibility surface. Accessibility labels and user-facing copy
are product language and must use Lens.

## 1. Overview

The Lens Editor is a non-conversational configuration interface for defining, editing, inspecting, and locally testing a Lens. A Lens changes the authored approach and configuration Guardian works under; it is not a separate autonomous agent and does not replace Guardian. It may configure model behavior, voice, prompt, requested capabilities, and retrieval intent, but saving remains neither runtime execution nor an authority grant.

The Lens Editor does not maintain chat history, write memory, act as normal conversation, or create runtime authority.

Its default path is the common authoring loop; implementation mechanics are
disclosed on request. See §4.4.

## 2. Core Principles

- The Lens Editor is configuration; Runtime Chat is execution; memory, Project, connection, and binding systems retain their own authority.
- Guardian remains the primary runtime and assistant authority. A Lens shapes how Guardian approaches work and never becomes a second agent.
- Build receipts and Test transcripts are local, ephemeral UI state, not conversation objects or message persistence.
- Manifest owns authored intent; Binding is server-owned environmental state; requested configuration is not effective configuration.
- Editing, saving, validating, importing, exporting, Build, and Test do not write memory, infer durable traits, or execute runtime behavior.
- The default editor shows the common authoring path. Implementation mechanics stay behind an explicit disclosure, and hiding a control never removes a value or an editing capability.

## 3. Core Entities

### 3.1 PersonaProfileManifest

ADR-082 owns the exact typed contract. V2's writable JSON projection contains selected profile identity/schema version plus authored identity, prompt, model, voice, capabilities, and retrieval fields. It does not make revisions, credentials, Project authority, grants, or Binding records editable.

The stable profile identity and immutable revision are distinct. `apiVersion` describes schema compatibility; a backend acknowledgement establishes the positive revision. A valid manifest request is not a provider, connector, capability, or execution grant.

### 3.2 PersonaProfileBinding

The server separately owns profile-to-environment binding records. They may contain server-derived account references and server-validated Project, participant, connection, activation, or environment mappings. This does not replace authority held by the owning account, Project, Connections, capability, or runtime-support system.

### 3.3 Studio-Only State

Studio retains a selected local draft, dirty/saved comparison state, local Build receipts and field highlights, Manifest text-buffer validation state, and an ephemeral Test transcript. None is a new persistence or runtime contract.

## 4. V2 User Experience

### 4.1 Layout

The route is an AppShell sibling view. AppShell owns Dock, scene, theme, and global shell tokens. The Lens Editor renders exactly two canonical `FrameCard` surfaces:

```text
Lens Assistant  |  Lens Editor
```

Lens Editor is wider on desktop; the surfaces stack at narrow width without horizontal overflow. There is no third outer frame and no full-width page footer/status panel.

### 4.2 Lens Assistant

Build is deterministic local configuration, not a model-backed assistant. It recognizes approved prototype mappings for analytic/warmer behavior, Anthropic/Claude or OpenAI/GPT model choice, higher/lower temperature, requested web/email permissions, voice on/off, and retrieval on/off. Recognized changes apply to the selected draft only, show a local receipt, and highlight affected Form fields/sections. Unrecognized text leaves the draft unchanged. Build never auto-saves or calls a provider, normal chat, tool, retrieval, connector, or memory surface.

Test reuses the deterministic draft-aware preview engine. It remains local, ephemeral, non-threaded, and independently clearable. It must not create a Guardian thread, chat history, memory write, provider request, tool call, retrieval execution, connector call, or persisted Persona mutation. Its embedded layout must not create another primary frame or duplicate heading.

### 4.3 Lens Editor

The Lens Editor header has the compact profile selector, acknowledgement state, Revert, Save, and a subordinate Duplicate-as-new action. Status states are `Saved · rev N` for a clean acknowledged draft, `Unsaved changes · saved rev N` for a dirty acknowledged draft, and `Unsaved draft` with no acknowledged baseline. The client never predicts a future revision; Save remains `Save`, not `Save rev N+1`.

The header carries no projection tab row. The draft is always presented as the Lens form first; the Manifest and Effective inspections are reached through the Advanced disclosure (§4.4).

#### Form

Form contains collapsible Lens identity, Behavior / Instructions, Voice, Model, Capabilities, Retrieval, and Activation & Bindings sections. It replaces the retired permanent seven-tab editor. Generation Top K and Retrieval Top K remain separate authored parameters.

### 4.4 Default Path and Advanced Disclosure

The default Lens authoring path is the common intent an author reaches for when shaping how Guardian should approach work:

- **Lens identity** — portable name and description.
- **Behavior / Instructions** — authored system prompt, style notes, directives.
- **Voice** — requested voice preference; a user-intent-level setting, kept on the common path and collapsed rather than disclosed.

Implementation-oriented mechanics sit behind a single explicit **Advanced** disclosure at the end of the form. Opening it reveals, without removing anything:

- Model — requested provider/model and detailed tuning.
- Capabilities — requested permissions and tool lists.
- Retrieval — retrieval tuning.
- Activation & Bindings — the non-portable Binding boundary.
- The **Manifest** and **Effective** inspections.

This is presentation reduction, not schema reduction. Every disclosed field keeps its prior value, definition, and editing behavior, and all advanced controls remain reachable from the same draft.

Disclosure is not a hiding rule Build may violate: when Build or a change-link targets a section inside the disclosure, the disclosure expands automatically so an applied value is never hidden behind a collapsed region.

### 4.5 Manifest

Manifest is editable JSON for the writable authored shape. Form edits regenerate the JSON projection; valid JSON changes update the same draft. Invalid JSON remains in the local buffer with an inline validation error and cannot corrupt the draft. The editor rejects mismatched `apiVersion`, another profile identity, revision fields, bindings, credentials, Project authority, runtime grants, and unknown fields. YAML import/export remains deferred.

### 4.6 Effective

Effective may inspect authored/requested values only. Until an authoritative resolver exists, provider/model availability, connector authorization/health, Project bindings, capability grants, and runtime effect must be labelled `Not resolved`, `Unavailable to resolve here`, or equivalent neutral wording. The view must not fabricate availability, authorization, or runtime truth.

### 4.7 Activation & Bindings

This section preserves the non-portable Binding boundary. It has no Project-pin editor, `@persona` alias editor, connector grant control, credential field, or fake authorization toggle unless a later authorized task provides an authoritative production seam.

## 5. Save, Validation, and Test Behavior

Save and Duplicate-as-new use the existing manifest persistence seam. Submitted writable manifests omit revision. Successful backend acknowledgement establishes the new baseline/revision; failed requests leave the draft dirty. Concurrent local edits are not silently erased. Revert restores the last acknowledged manifest when available and does not write the backend.

V2 validates writable-manifest shape and identity/schema coherence. It does not invent environment validation: provider selection is not availability, configuration is not connector authorization or health, and requested capability is not effective capability.

The current Test system is deterministic preview, not voice/retrieval/tool execution. It has no memory writes, chat history, authority grant, or runtime execution merely because a draft is inspected or tested.

## 6. Runtime Integration and Execution Boundary

### 6.1 Current Compatible Projection

The existing runtime-bearing persistence seam can project only name, system prompt, model provider, model ID, and temperature. The remaining manifest fields stay non-executing until each has a separately implemented, authorized, and proven enforcement seam.

### 6.2 Requested Versus Effective Application

The intended path is not UI-to-runtime: Manifest records requested configuration; Binding supplies server-derived or server-validated environment references; owning systems determine availability and policy denials; and runtime/support policy determines the narrow effective configuration that may reach a runtime. No effective-configuration endpoint or full resolver exists today.

### 6.3 Strict Isolation

The Lens Editor must never, merely by editing, saving, importing, exporting, validating, testing, or inspecting a profile, write memory stores, modify thread history or create conversation records, invoke a model/tool/retrieval/connector, change provider health, or grant new authority.

## 7. Observability Requirements

Effective distinguishes requested values from unavailable unresolved environment state. It does not claim available, denied, or effective runtime configuration without an owning resolver/evidence source. Draft-vs-saved state and transient Build highlights are sufficient inspection surfaces.

## 8. Critical UX Rules

- No normal Guardian chat UI, conversation threading, or hidden assistant presence in the editor.
- Keep generation and retrieval parameters semantically separate.
- Make unsaved state visible in the Lens Editor header, not a page footer.
- Use actual FrameCard material and AppShell scene ownership; do not port the prototype's simulated shell or environmental claims.
- Progressive disclosure must not remove capability. A collapsed or undisclosed control keeps its value and stays reachable.
- Never apply an authored change into a region the author cannot see; expand the disclosure when a Build change targets it.

## 9. Non-Goals

This surface does not implement model-backed configuration, a new backend endpoint, Binding persistence/editor, Project pins, `@persona` aliases, connector grants, provider health resolution, capability enforcement, retrieval execution, voice runtime enforcement, YAML import/export, new identity/memory behavior, global Dock/FrameCard/token redesign, legacy-component cleanup, or release promotion.

## 10. Future Extensions

Potential future work includes individually authorized effective-config resolution, Binding editing, import/export, history/rollback, Project scope, and runtime enforcement. Each requires its own authority, execution, and proof contract.

## 11. Naming

Product language presented to users:

- Feature: Lens Editor
- Nav entry: Lens
- Left workspace: Lens Assistant
- Right workspace: Lens Editor
- Local modes: Build / Test, plus the Advanced disclosure and its Manifest / Effective inspections

Deliberately unchanged:

- Canonical authority: `PersonaProfileManifest`, `PersonaProfileBinding`, ADR-082.
- Internal implementation: `personaStudio` module tree, `PersonaStudioPage`, `persona-studio-*` test IDs, and the `/persona-studio` route.

Internal Persona naming is not product vocabulary and is not a simplification target. It changes only when a structural change requires it, not to make identifiers cosmetically consistent.

## 12. Definition of Done

The presentation is complete when AppShell directly contains the page and the page renders exactly two primary FrameCards; Build/Test retain local-only non-authoritative behavior; Lens identity, Behavior / Instructions, and Voice form the default path; Model, Capabilities, Retrieval, Activation & Bindings, Manifest, and Effective are reachable through one explicit Advanced disclosure without losing any value or editing capability; Build expands that disclosure when it changes something inside it; Manifest and Binding stay separate; acknowledgement/revision semantics remain intact; and no runtime, identity, memory, connector, or release claim is inferred from editor interaction.
