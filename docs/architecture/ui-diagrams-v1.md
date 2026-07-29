# Codexify UI Diagrams v1

## 1. Title and purpose

This document is the first-pass UI diagram pack derived only from the validated UI canon source set. It maps Codexify's presentation-side architecture for tokens, layout, rendering surfaces, and diagnostics-facing conceptual layers without asserting backend or runtime topology.

## 2. Source set used

- `/docs/dev/ARTIFACT1—UI-Token-Constitution.md`
- `/docs/dev/ARTIFACT1B—CODEXIFY-STRUCTURAL-LAYOUT-SPECIFICATION.md`
- `/docs/dev/ARTIFACT3—Codexify-UI-Rendering-Protocol.md`
- `/docs/dev/ARTIFACT4—COGNITIVE-DIAGNOSTICS-CANON.md`
- `/docs/dev/ARTIFACT7--CODEXIFY-PERCEPTUAL-STACK-SPEC.md`

## 3. Interpretation constraints

- These diagrams describe UI canon and presentation structure, not current backend/runtime topology.
- These diagrams are derived from the validated UI canon only.
- Runtime disagreements must be resolved against the runtime KB, not this document.
- Quarantined legacy docs and implementation guesswork were not used.

## 4. Diagram legend

- `token`: canonical UI variable controlling color, spacing, radius, geometry, or sizing.
- `layout frame`: structural containment layer that positions views and cards.
- `rendering surface`: allowed visual category used to present content, such as glass, panel, chip, or frame.
- `diagnostic surface`: opt-in UI region that exposes cognition or retrieval state.
- `conceptual layer`: a named interpretive layer used to explain UI-facing cognition flow, not runtime deployment.

## 5. Diagram 1: UI Token Hierarchy (high confidence)

This diagram shows the explicit token layers and the constraint path from AppShell-level token injection to visible UI surfaces.

```mermaid
flowchart TD
    A["AppShell global token injection"] --> B["Root tokens<br/>scene, color, radius, shell, glass geometry"]
    B --> C["Layout tokens<br/>view and container overrides"]
    B --> D["Legacy semantic aliases<br/>--radius, --gutter, --board-edge"]
    C --> E["Component tokens<br/>cards, chips, inputs, modals, glass components"]
    D --> E
    E --> F["Visible surfaces<br/>glass cards, panels, chips, inputs, modals"]
    B --> G["Token law"]
    C --> G
    E --> G
    G --> H["Constraints on visible surfaces"]
    H --> I["No inline colors or magic numbers"]
    H --> J["No independent radius, blur, or shadow systems"]
    H --> K["Responsive change via token overrides only"]
```

**Evidence notes**

Primary sources:
- `ARTIFACT1` sections II-VIII
- `ARTIFACT3` sections 0-4 and 9

Conservative assumptions:
- "Foundational token layer" is represented as AppShell-injected root tokens because the canon explicitly roots token injection there.
- "Semantic token layer" is represented through layout overrides plus legacy semantic aliases because the canon defines precedence and fallback layers but does not publish a larger design-system taxonomy.

Explicit exclusions:
- No invented sub-taxonomy for typography, motion, or state tokens beyond what the canon names.
- No code-component tree or implementation ownership mapping.

## 6. Diagram 2: Structural Layout Model (high confidence)

This diagram shows the immutable shell-to-view containment model and the major sanctioned layout regions.

```mermaid
flowchart TD
    A["Viewport"] --> B["Glass skin<br/>full-bleed, behind interactive UI"]
    A --> C["Scene wrapper"]
    C --> D["Desktop/default scene path"]
    D --> D1["Global pill navigation<br/>top-left, logically independent"]
    D --> E["Main content area"]
    E --> F["Single primary layout block per view"]
    F --> G["Primary card structure"]
    G --> H["Outer bezel"]
    H --> I["Frame"]
    I --> J["Rim"]
    J --> K["Surface"]
    F --> L["Optional supporting regions"]
    L --> M["Workspace drawer"]
    L --> N["Sidebar or rail when view blueprint allows it"]
    E --> O["View blueprints"]
    O --> P["Documents<br/>list card plus optional workspace card"]
    O --> Q["Dashboard<br/>thread grid card plus workspace drawer"]
    O --> R["Settings<br/>one primary card with compact full-width dock<br/>and responsive one/two-column tabpanel grid"]
    O --> S["Gallery<br/>single card to inner card to grid"]
    O --> T["Guardian<br/>card-wrapped content with optional sidebar"]
    T --> U["Narrow Guardian drawer<br/>AppShell-owned app destinations<br/>plus SessionSpine-owned thread navigation"]
    C --> V["Narrow Guardian exception"]
    V --> W["Wallpaper or configured gradient"]
    W --> X["Uniform edge chrome<br/>same token on all four sides"]
    X --> Y["Frame-first Guardian primary card<br/>all current interaction content contained"]
    Y --> Z["Navigation-complete drawer projection<br/>no persistent global pill in closed view"]
    Y --> ZA["Compact mobile header"]
    ZA --> ZB["Sidebar trigger"]
    ZA --> ZC["Guardian tools menu"]
    Y --> ZD["Runtime / auth truth notices"]
    Y --> ZE["Transcript durable record layer<br/>internal scroll owner"]
    Y --> ZF["Compact mobile composer pill<br/>attachment/add · authored text · voice · send"]
    ZE --> ZG["Focused composition mode"]
    ZG --> ZH["Projected composer<br/>foreground over lower transcript"]
    ZG --> ZI["Keyboard below settled visible aperture"]
    ZH --> ZJ["Command-only slash draft"]
    ZJ --> ZK["Deterministic frontend registry/parser"]
    ZK --> ZL["Command or value suggestions"]
    ZL --> ZM["Existing configuration callback<br/>draft removed without transcript persistence"]
```

**Evidence notes**

Primary sources:
- `ARTIFACT1B` sections II-XII
- `ARTIFACT1` section IV

Conservative assumptions:
- Supporting panels, rails, and drawers are shown only where the layout spec explicitly permits them.
- View blueprints are included as sanctioned structural examples rather than a routing model.

Explicit exclusions:
- No route graph, navigation flow, or frontend file/component map.
- No runtime meaning assigned to workspace drawers, session rails, or sidebars beyond structural placement.

Guardian/mobile interpretation:
- On narrow Guardian layouts, the optional sidebar may be a
  navigation-complete drawer rather than icon-only or stacked content.
- The drawer is workspace-first by default. Its collapsed/default presentation
  places the Threads / Projects header directly beneath drawer chrome; no
  application destination remains rendered or focusable in that state.
- The Codexify mark in drawer chrome is a disclosure trigger, not a route
  destination. Expanding it inserts the existing AppShell-owned application
  destinations above the stateful Threads / Projects workspace without
  remounting that workspace.
- Escape collapses expanded application navigation and restores focus to the
  mark before a subsequent Escape closes the drawer. Destination selection and
  drawer closure reset the disclosure to its default state.
- AppShell continues to own application routing, while SessionSpine continues
  to own thread/session state.
- This remains presentation-side architecture subordinate to the single
  Guardian primary card; it does not transfer routing ownership into Guardian
  or thread/session ownership into AppShell.
- In the narrow Guardian exception, AppShell omits the persistent global pill
  and its reserved space because the drawer provides the replacement navigation
  path. Desktop Guardian and non-Guardian views retain the default scene path.
- The Guardian primary card fills the settled mobile shell inside a uniform
  token-backed edge-chrome perimeter. The drawer overlays that frame without
  becoming a second shell.
- The narrow Guardian frame uses a compact two-control header:
  - Left: sidebar trigger (navigation-drawer invocation).
  - Right: Guardian tools menu (hamburger/utility-menu control).
  - Displaced header actions remain available through the Guardian tools menu.
  - Runtime-health and authentication-truth notices remain outside the
    utility menu and preserve their exact meaning.
  - The Codexify mark remains inside the drawer.
  - Desktop Guardian retains its existing persistent controls.
- The transcript is the durable record layer and remains the internal vertical
  scroll owner. The AppShell document does not become the chat scroll owner.
- In record mode, the compact header and runtime/auth truth remain stable, the
  transcript occupies the record layer, and the composer rests at the lower
  frame edge.
- In focused composition mode, the frame and compact header remain stable while
  the existing composer projects over the lower transcript and the existing
  settled-viewport system places it above the keyboard aperture.
- Successful authored-message submission enters the user turn into the durable
  record, then blurs the composer, permits keyboard dismissal, and restores the
  full record aperture. It does not prove assistant completion.
- Failed submission preserves the authored draft and composer availability.
- The narrow composer is one compact pill whose direct interaction surface
  retains attachment/add, authored text, supported voice, and send. Persistent
  project, provider, model, mode, and retrieval selectors are absent from this
  narrow contract.
- A command-only `/<command> [value]` draft enters a deterministic frontend
  branch: slash-prefix detection, bounded command/value suggestions, invocation
  of an existing configuration callback, then command-draft removal without
  transcript persistence. The bounded registry currently projects `/project`,
  `/provider`, `/model`, `/mode`, and `/retrieval` because those controls exist;
  `/profile` remains absent until a canonical Composer profile control exists.
- Unknown slash text, escaped `//` text, embedded slash prose, and ordinary
  authored text remain on the existing message-send branch. Runtime execution
  stays outside the command branch; no Guardian reasoning, prompt, backend
  route, or command bus parses these commands.
- Existing runtime availability, authorization, compatibility, and disabled
  states remain authoritative. Desktop composer behavior and visible selectors
  remain unchanged.
- Documents/Gallery mobile-shell redesign remain unimplemented and outside
  this diagram update.

Narrow Guardian drawer states:

```text
Default workspace state
├── drawer chrome
│   ├── Codexify navigation trigger
│   └── close drawer
├── Threads / Projects header
└── workspace content

Expanded application-navigation state
├── drawer chrome
│   ├── Codexify navigation trigger, expanded
│   └── close drawer
├── application destinations
├── Threads / Projects header
└── workspace content
```

These states are presentation-side only. Desktop Guardian retains its current
persistent sidebar and navigation presentation.

Narrow Guardian interaction modes:

```mermaid
flowchart TD
    A["Record mode"] --> A1["Compact header"]
    A --> A2["Runtime and authentication truth"]
    A --> A3["Transcript durable record"]
    A --> A4["Composer at lower frame edge"]

    B["Focused composition mode"] --> B1["Stable frame"]
    B --> B2["Stable compact header"]
    B --> B3["Transcript record beneath"]
    B --> B4["Projected composer"]
    B --> B5["Keyboard below settled visible aperture"]

    C["Successful authored-message submit"] --> C1["User message enters durable record"]
    C --> C2["Composer blurs"]
    C --> C3["Keyboard dismisses"]
    C --> C4["Transcript returns to full aperture"]

    D["Rejected authored-message submit"] --> D1["Draft remains"]
    D --> D2["Composer remains available"]
    D --> D3["No record-mode success claim"]

    E["Command-only slash draft"] --> E1["Deterministic frontend parser"]
    E1 --> E2["Command or value suggestions"]
    E2 --> E3["Existing configuration callback"]
    E3 --> E4["Draft removed without transcript persistence"]

    F["Ordinary authored text"] --> F1["Existing send boundary"]
    F1 --> F2["Persisted user message"]
    F2 --> F3["Existing completion flow"]
```

## 7. Diagram 3: Rendering / Surface Composition Model (high confidence)

This diagram shows how layout containers, token precedence, and permitted surfaces combine to produce rendered UI.

```mermaid
flowchart TD
    A["AppShell global tokens"] --> B["Rendering precedence"]
    C["View-level token overrides"] --> B
    D["Component contract tokens"] --> B
    E["Fallback semantic tokens"] --> B
    B --> F["Rendering decision"]
    F --> G["Choose surface category"]
    G --> H["Glass surface<br/>RefractiveGlassCard only"]
    G --> I["Panel surface<br/>panel-bg plus panel-border"]
    G --> J["Chip surface"]
    G --> K["Frame region"]
    F --> L["Choose container geometry"]
    L --> M["Token-driven padding, gap, radius, clamp, flex"]
    M --> N["Layout frame and card hierarchy"]
    H --> O["Composed visible UI surface"]
    I --> O
    J --> O
    K --> O
    N --> O
    O --> P["Validity checks"]
    P --> Q["All values token-derived"]
    P --> R["No manual glass recreation"]
    P --> S["No new visual categories"]
```

**Evidence notes**

Primary sources:
- `ARTIFACT3` sections 0-9
- `ARTIFACT1` sections IV-VIII
- `ARTIFACT1B` section VIII

Conservative assumptions:
- The composition model is synthesized from the rendering precedence stack, decision tree, and canonical card hierarchy to keep the diagram readable.
- Diagnostics overlays are omitted here because the rendering protocol does not define them as a primary rendering branch.

Explicit exclusions:
- No React component tree, prop flow, or renderer internals.
- No runtime event, data, or provider path shown inside the rendering diagram.

## 8. Diagram 4: Diagnostics / Perceptual Stack (moderate confidence)

This diagram shows the UI-facing conceptual relationship between perceptual layers and the diagnostic surfaces that may expose them.

```mermaid
flowchart LR
    A["Primary interaction surfaces<br/>chat and main views"] --> B["Diagnostics access is opt-in"]
    B --> C["Settings → Diagnostics tab<br/>primary home"]
    B --> D["Diagnostics popovers<br/>explicit micro-tools"]
    B --> E["Developer mode surfaces"]
    C --> F["Conceptual diagnostic layers"]
    D --> F
    E --> F
    F --> G["Evidence layer<br/>raw retrieved chunks"]
    F --> H["Context layer<br/>assembled bundle view"]
    F --> I["Trace layer<br/>ranking and selection trace"]
    F --> J["Insight layer<br/>human-readable explanation"]
    K["Perceptual flow"] --> L["Sensory"]
    L --> M["Interpretation"]
    M --> N["Retrieval"]
    N --> O["Assembly"]
    O --> P["Injection"]
    P --> Q["Cognitive operation"]
    Q --> R["Tool invocation"]
    N --> G
    O --> H
    N --> I
    P --> J
    S["Visibility constraints"] --> T["Never inside message stream, composer, sidebar, thread list, or chat overlay"]
    S --> U["No auto-opening or auto-updating diagnostics"]
    S --> V["Developer mode required for sensitive views such as embeddings"]
    C --> S
```

**Evidence notes**

Primary sources:
- `ARTIFACT4` sections 0-5
- `ARTIFACT7` sections 1-4

Conservative assumptions:
- The diagram maps perceptual layers to diagnostic surfaces as a UI-facing conceptual aid; the canon supports both sets but does not provide a single merged visualization.
- Only the diagnostic-relevant perceptual stages are connected to evidence, context, trace, and insight surfaces.

Explicit exclusions:
- No backend observability topology, event bus architecture, or distributed node map.
- No future-only tools from expansion sections are treated as current required surfaces.
- Diagnostics surfaces may render provenance chips and suppression summaries, but they still must not expose raw system prompts, hidden messages, embeddings, or other internal reasoning artifacts.

## 9. Omitted / intentionally excluded areas

- Backend/runtime topology.
- Speculative implementation details not present in the UI canon.
- Future features not defined in the validated UI source set.
- Direct code-component mapping.
- Legacy or quarantined docs.

## 10. Reviewer guidance

This pack is a baseline UI-facing architecture map. Resolve disagreements against the validated UI canon first, not against memory or implementation guesswork.
