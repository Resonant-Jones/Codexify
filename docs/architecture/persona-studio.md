Purpose: Document Persona Studio as it exists in the shell today so readers can understand the page structure, local state flow, and boundary limits without reading implementation code first.
Last updated: 2026-09-04
Source anchors:
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/features/personaStudio/PersonaStudioPage.tsx
- frontend/src/features/personaStudio/personaStudioStore.ts
- guardian/cognition/system_profiles/manifest.py
- guardian/cognition/system_profiles/store.py
- guardian/cognition/system_profiles/resolver.py
- guardian/routes/persona_profiles.py
- guardian/db/models.py
- guardian/db/migrations/versions/c3d9e1f4a6b8_persist_persona_profile_manifest_binding.py
- frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx
- frontend/src/features/personaStudio/__tests__/PersonaStudioPage.persistence.test.tsx
- docs/architecture/persona-studio-spec.md
- docs/architecture/adr/082-persona-profile-manifest-and-binding-authority.md

# Persona Studio Architecture

## Purpose and Scope

Persona Studio is a non-conversational configuration surface for persona and
profile settings. It keeps a broad browser-local draft while the backend now
persists the canonical typed Persona Profile manifest, immutable revisions,
and a server-owned account binding under ADR-082.

The current frontend still uses the five-field compatibility API rather than
the full canonical manifest write contract. Consequently, broad browser fields
remain local unless another canonical API client authors them, and only the
existing five-field projection is runtime-active.

Persona Studio is:

- not a chat surface
- not a memory-writing surface
- not a thread/history surface
- not a runtime assistant session

## Current Implementation Status

| Surface | Status now | Meaning |
|---|---|---|
| AppShell navigation entry and route | runtime-active | `AppShell` exposes `/persona-studio` as a first-class shell view and renders the page inside a `FrameCard`. |
| Three-panel layout | runtime-active | The page renders left Profiles, center Editor, and right Diagnostics panels. |
| Profile list | hybrid local/backend | Seed drafts and localStorage provide the fallback; the frontend also loads the request account's backend profiles and merges their five compatibility fields. |
| Editor draft state | frontend-local | The selected profile draft is mutated in browser state and persisted to localStorage. |
| Diagnostics panel | frontend-local preview | The panel renders a JSON config preview plus a synthetic debug log derived from the current draft. |
| Save / Save As New | compatibility persistence | The frontend updates local state and sends only name, system prompt, model provider, model ID, and temperature. The backend creates an account binding and immutable manifest revision or appends one substantive revision. |
| Reset | frontend-local | Reset restores the last local saved/seed state; it does not write the backend. |
| Canonical manifest persistence | backend-active | Strict V1 manifests, immutable revisions, and server-owned account bindings are durable and account-scoped. |
| Runtime profile application | five-field only | A thread may resolve its owning account's current profile projection. Voice, capabilities, retrieval, and other broad fields remain inert. |

### Presentational, Frontend-Local, Runtime-Bound

| Category | Current contents |
|---|---|
| Presentational | Shell nav entry, route switch, frame wrapper, three panels, tabs, form controls, badges, diagnostics card |
| Frontend-local state | Seed profiles, selected profile, active tab, editable broad drafts, diagnostics, and localStorage persistence |
| Backend persistence | Account-scoped registry rows, server-owned bindings, immutable manifest revisions, and the current five-field projection |
| Runtime-bound behavior | Only name, system prompt, model provider, model ID, and temperature may flow from the current manifest projection for a thread owned by the same account |

### What Is Not Yet Wired

- No frontend adoption of the canonical full-manifest write contract
- No thread-to-immutable-revision binding
- No live application of voice, capability, retrieval, connector, or other
  broad manifest settings
- No import/export/delete flow in the current page
- No server-driven diagnostics feed or validation loop
- No Effective Config resolver or inspection endpoint

### Do Not Assume

- Do not assume the current frontend Save sends the broad local draft; it sends
  only the five compatibility fields
- Do not assume Reset changes live assistant behavior
- Do not assume selecting a Studio profile changes an active thread or binds a
  manifest revision
- Do not assume Generation Top K and Retrieval Top K are interchangeable
- Do not assume persisted voice, capability, retrieval, or permission-shaped
  requests grant authority or affect runtime

## Where It Lives in the Shell

Persona Studio is a top-level AppShell view alongside Guardian, Dashboard, Documents, Gallery, and Settings.

- Route mapping: `/persona-studio`
- Shell entry: the navigation pill in `frontend/src/components/persona/layout/AppShell.tsx`
- Mounted content: `PersonaStudioPage` rendered inside a `FrameCard`

This matters because the page is not nested inside chat or settings as a subpanel. It is a sibling shell surface.

## UI Structure

The page uses a simple three-panel layout:

- Left panel: Profiles
- Center panel: Editor
- Right panel: Diagnostics

The center panel contains six tabs:

- Identity
- Model
- Voice
- Prompt
- Tools
- Retrieval

The Model tab contains generation controls, including `Generation Top K`.

The Retrieval tab contains retrieval controls, including `Retrieval Top K`.

These are separate concepts and must remain separate.

## Data Model

The current screen uses a narrower frontend-facing shape than the broader product spec. The effective profile draft shape is:

```ts
type PersonaStudioLocalState = {
  profiles: PersonaProfileDraft[];
  draftProfilesById: Record<string, PersonaProfileDraft>;
  selectedProfileId: string;
  activeTab: "Identity" | "Model" | "Voice" | "Prompt" | "Tools" | "Retrieval" | "Truth Matrix";
};

type PersonaProfileDraft = {
  id: string;
  name: string;
  description: string;
  isDefault?: boolean;
  config: {
    identity: {
      name: string;
      description: string;
    };
    model: {
      provider: string;
      model: string;
      temperature: number;
      topK: number;
      topP: number;
      maxTokens: number;
    };
    voice: {
      enabled: boolean;
      provider: string;
      voicePreset: string;
      speed: number;
      wakeWord: string;
      interruptible: boolean;
    };
    prompt: {
      systemPrompt: string;
      styleNotes: string;
      directives: string;
    };
    tools: {
      pinnedTools: string[];
      allowedTools: string[];
      skills: string[];
      permissions: {
        web: boolean;
        email: boolean;
        calendar: boolean;
        cli: boolean;
        filesystem: boolean;
      };
    };
    retrieval: {
      enabled: boolean;
      mode: string;
      topK: number;
      rerank: boolean;
    };
  };
};
```

Diagnostics-facing derived state is not a separate persisted contract. It is computed from the selected draft and the local save snapshot:

- `selectedProfile`
- `currentConfig`
- `selectedSavedProfile` from `profiles`
- `seedProfile`
- `isDirty`
- `hasSavedVersion`
- `debugLog`

The backend persistence model is separate:

- `PersonaProfile` is the stable profile registry and current five-field
  compatibility projection, with a positive `current_revision` pointer.
- `PersonaProfileRevision` stores each immutable, self-contained V1 manifest
  snapshot under the unique `(profile_id, revision)` key.
- `PersonaProfileBinding` stores the server-derived owning account only. It is
  not part of the portable manifest.

The V1 manifest can persist identity name/description, prompt systemPrompt,
styleNotes and directives, model provider/model/temperature/topK/topP/maxTokens,
the current voice shape, requested tools/skills/five permission flags, and the
current retrieval shape. Connector references are omitted because no concrete
V1 field shape is defined. Authority-bearing account, Project, participant,
credential, and grant fields are rejected.

## State Flow

1. `readPersonaStudioLocalState()` loads local state from localStorage, or falls
   back to built-in seed profiles if nothing valid exists.
2. The frontend loads account-scoped backend profiles and merges only their
   five compatibility fields into local drafts.
3. `selectedProfileId` chooses the current draft; `activeTab` chooses the
   visible editor subpanel.
4. `updateSelectedProfile()` changes `draftProfilesById`; a `useEffect` persists
   the broad local state to localStorage.
5. Diagnostics and dirty state remain derived in the browser.
6. `saveSelectedProfile()` updates the local saved profile and sends a legacy
   five-field PATCH. `saveSelectedProfileAsNew()` sends the same five-field
   shape through POST.
7. The API derives account identity from `RequestUserScope`; the client cannot
   submit owner authority.
8. A create transaction writes one registry row, one binding, and revision 1.
   A substantive update locks the profile, appends one revision, and advances
   the projection and current pointer atomically; a no-op appends nothing.
9. A legacy PATCH changes only its five mapped manifest values and preserves
   every unrelated authored field.
10. `resetSelectedProfile()` and `resetAllLocalPersonaStudioData()` affect local
    browser state only.
11. At runtime, `chat_threads.user_id` scopes the backend catalog. A missing or
    foreign owner cannot load another account's profile; built-in and env
    profiles keep their existing behavior.

The practical relationship is:

- browser draft state remains the editor and diagnostics source
- localStorage remains the broad unsaved-draft store
- the canonical backend manifest is durable profile truth
- the binding is server-owned account authority, never manifest content
- immutable revisions preserve authored history
- only the five compatibility fields project into the current runtime seam

## Diagrams

### A. Component Hierarchy

```mermaid
flowchart TD
    A["AppShell"] --> B["Persona Studio nav pill"]
    B --> C["Persona Studio route<br/>/persona-studio"]
    C --> D["FrameCard shell"]
    D --> E["PersonaStudioPage"]
    E --> F["Profiles panel"]
    E --> G["Editor panel"]
    E --> H["Diagnostics panel"]
    G --> I["Identity tab"]
    G --> J["Model tab"]
    G --> K["Voice tab"]
    G --> L["Prompt tab"]
    G --> M["Tools tab"]
    G --> N["Retrieval tab"]
    J --> O["Generation Top K field"]
    N --> P["Retrieval Top K field"]
```

### B. Data Flow

```mermaid
flowchart LR
    A["Seeds + localStorage"] --> B["Broad browser draft"]
    C["Account-scoped profile API"] -->|"five fields"| B
    B --> D["Editor + diagnostics"]
    B -->|"legacy POST/PATCH: five fields"| C
    C --> E["RequestUserScope"]
    E --> F["PersonaProfileBinding<br/>owner account"]
    C --> G["Immutable PersonaProfileRevision<br/>canonical manifest"]
    G --> H["PersonaProfile<br/>current revision + five-field projection"]
    I["chat_threads.user_id"] --> J["Account-scoped backend catalog"]
    H --> J
    J --> K["SystemProfilePayload<br/>five fields only"]
    G -. "voice/capability/retrieval remain inert" .-> L["No runtime seam"]
```

### C. User Interaction Flow

```mermaid
sequenceDiagram
    participant U as User
    participant S as AppShell
    participant P as PersonaStudioPage
    participant T as Local store
    participant L as localStorage
    participant A as Profile API
    participant D as DiagnosticsPanel

    U->>S: Click Persona Studio nav pill
    S->>P: Mount /persona-studio inside FrameCard
    U->>P: Select a profile
    P->>T: setSelectedProfileId()
    T-->>P: selectedProfile and currentConfig update
    U->>P: Edit tab fields
    P->>T: updateSelectedProfile()
    T->>L: persist full local state
    T-->>D: recompute isDirty / hasSavedVersion / debugLog
    D-->>U: effective config preview and save status refresh
    U->>P: Save
    P->>T: saveSelectedProfile() / saveSelectedProfileAsNew()
    T->>L: write updated local snapshot
    T->>A: send five-field compatibility write
    U->>P: Reset
    P->>T: restore local saved/seed draft only
```

## Boundary Rules

Persona Studio does not:

- create chat messages
- create thread history
- write long-term memory
- act as a runtime assistant session
- grant Project, participant, connector, capability, credential, or other
  environmental authority
- apply broad voice, capability, retrieval, connector, or sampling settings to
  live runtime

Saving or validating a profile invokes no model, tool, retrieval, connector,
TTS, or memory mutation. The backend current manifest is account-scoped, but
the Studio remains a configuration surface rather than a second runtime.

## Next-Step Recommendations

Likely next phases, if the surface is promoted beyond local preview, are:

- frontend adoption of the canonical full-manifest API
- YAML/JSON import and export
- richer Project, participant, and logical Connection binding scopes
- immutable thread-to-profile-revision binding
- Effective Config inspection
- individually authorized capability, retrieval, connector, and voice
  enforcement

None of those phases are implemented by this persistence slice; release and
supported-profile posture remain unchanged.
