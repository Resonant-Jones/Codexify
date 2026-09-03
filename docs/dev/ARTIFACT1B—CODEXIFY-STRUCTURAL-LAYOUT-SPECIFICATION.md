ARTIFACT 1B — CODEXIFY STRUCTURAL LAYOUT SPECIFICATION
The Canonical Blueprint of Every Screen

This document defines the structural skeleton of the Codexify interface:
the permitted arrangements of views, columns, glass surfaces, cards, grids, and panels.

Tokens define the look.
This document defines the shape.

Together, they form the full UI Law of Codexify.

I. PURPOSE

Establish a single, universal structural schema for:

Page layout

Card hierarchy

Glass → Frame → Rim architecture

Column organization

Workspace behavior

Panel density & grid rules

Responsive modes

Every Codexify screen must conform to these structures without exception.

II. CORE LAYOUT PRIMITIVES

Codexify's UI is built from seven structural primitives:

Viewport — the outer frame (full window)

Glass Skin — global refractive layer

Scene Wrapper — center-aligned, padded, radius-governed surface

Pill Menu Bar — floating navigation rail

Main Content Area — flexible layout container

Primary Card — a token-governed glass card

Workspace Drawer — a contextual side panel

Every view is composed using these primitives.

III. GLOBAL STRUCTURE (Immutable)

1. VIEWPORT

The root structure ALWAYS follows:

<html>
  <body>
    <div class="viewport">
      <div class="glass-skin" />
      <div class="scene-wrapper">
        <Navigation />
        <MainContent />
      </div>
    </div>
  </body>
</html>

Requirements:

Width: 100vw

Height: 100vh

Min-width: 608px

Min-height: 548px

Padding: var(--edge-chrome)

Background: gradient or wallpaper (via tokens)

Radius: var(--viewport-radius) (always 19px)

IV. GLASS SKIN ARCHITECTURE

The global glass skin is:

Full bleed

Behind all interactive UI

Rounded to var(--viewport-radius)

Blurred, refractive, tone-matched

Agents MUST NOT:

Add borders to it

Add content inside it

Replace its blur/shadow logic

V. SCENE WRAPPER

The main wrapper inside the viewport:

<div class="scene" style="borderRadius: var(--viewport-radius)">
  <Navigation />
  <MainContent />
</div>

Properties:

Inherits tokens from AppShell

Manages theme class (dark)

MUST apply global tokens (styleVars)

MUST NOT include content padding except --edge-chrome

This is the parent of every view.

VI. NAVIGATION (Pill Menu Bar)

Nesting:

<div class="menu-container">
  <div class="glass-pill">
    <span>Codexify</span>
    <button>Guardian</button>
    <button>Dashboard</button>
    <button>Documents</button>
    <button>Gallery</button>
    <button>Settings</button>
  </div>
</div>

Rules:

Desktop and non-phone profiles retain the top-left pill navigation.

When rendered, navigation always uses the glass component + pill style.

No margins except those uniquely required by visual balance

NEVER alters the main content geometry

Navigation is logically independent (no absolute overlays except pill)

Primary phone-shell rule:

- Guardian, Documents, Gallery, Dashboard, and Settings MUST omit the global
  pill on phone layouts because the shared sidebar drawer is
  navigation-complete.
- The phone path MUST remove the navigation wrapper and its layout reservation;
  hidden or off-screen tabbable controls are not permitted.
- Desktop and tablet/non-phone presentation retain the global pill contract.
- Application routing remains AppShell-owned.

VII. MAIN CONTENT AREA

This is the most important structural contract.

Main structure:
<div class="content">
  <div class="content-inner">
    {ViewRenderer(view)}
  </div>
</div>

Properties:

Flex-column

Flex: 1

Min-height: 0 (prevents overflow collapse)

Must stretch to fill height

Each view MUST be a single primary layout block, not multiple siblings.

Examples of primary blocks:

Documents Block

Gallery Block

Guardian Block

Settings Block

Dashboard Block

VIII. PRIMARY CARD STRUCTURE (Canonical Glass Card)

All cards MUST follow:

<div class="outer" style="padding: var(--bezel)">
  <div class="frame" style="padding: var(--frame)">
    <div class="rim" style="padding: var(--rim)">
      <div class="surface">
        <content />
      </div>
    </div>
  </div>
</div>

Layer Responsibilities:

Outer (bezel)
– sets glass margin
– hosts RefractiveGlassCard backdrop

Frame
– provides chrome border

Rim
– inner translucent ring

Surface
– actual content panel
– applies panel-bg & panel-border
– applies inset shadows
– MUST clip with overflow-hidden and clipPath

Agents MUST NOT disturb this hierarchy.

IX. RESPONSIVE LAYOUT MODES

Codexify defines 5 breakpoint modes:

sm

md

lg

xl

2xl

Rules:

sm/md:

Documents: workspace collapsed

Settings: full-width

Guardian: sidebar icon-only or stacked

Dashboard: single-column priority

lg/xl:

Documents: 50/50 split

Settings: centered primary card with a responsive internal tabpanel grid

Dashboard: workspace drawer allowed

2xl:

Documents: 40/60 split

Dashboard: full multi-column

Agents MUST NOT apply width via hardcoded pixel values based on breakpoints.

Only token changes are allowed.

X. VIEW-BY-VIEW STRUCTURAL BLUEPRINT

Below are the exact permissible layouts.

A. GUARDIAN VIEW
<GuardianChatWithSidebar />

Rules:

Sidebar optional

Content MUST be wrapped in card structure

Height: 100%

No extra wrappers outside token-approved structure

Primary phone navigation projection:

- Guardian, Documents, Gallery, Dashboard, and Settings use one shared mobile
  drawer presentation containing compact Codexify application identity,
  application destinations, and the existing Threads / Projects workspace.
- The shared drawer owns only portal/scrim structure, frame chrome, disclosure,
  destination rendering, focus containment, Escape behavior, and workspace
  placement. It does not own thread, project, DocumentsScope, or Guardian
  session state.
- Guardian opens workspace-first. Its chrome contains the Codexify mark
  disclosure and the independent drawer-close control; with the disclosure
  collapsed, Threads / Projects is the first content directly beneath chrome.
- A primary non-Guardian view opens application-first. Application disclosure
  remains expanded across Documents, Gallery, Dashboard, and Settings
  navigation, while each destination selection still closes the drawer.
- Returning to Guardian collapses application navigation and restores Threads /
  Projects-first ordering. Drawer-open state and application-disclosure state
  remain separate and transient; neither creates a durable preference.
- Activating the Codexify mark expands the existing application destinations
  above Threads / Projects through ordinary layout flow. Threads / Projects and
  its search, selection, and content state remain mounted and visible beneath
  the expanded section.
- Escape dismisses the expanded application destinations first and restores
  focus to the Codexify mark. A subsequent Escape follows the existing
  drawer-close behavior. Closing the drawer does not independently rewrite the
  disclosure priority.
- Application routing and disclosure memory remain owned by AppShell. The
  shared drawer receives only controlled state, bounded destination metadata,
  navigation callbacks, and the existing sidebar workspace as child content.
- Thread and session state remain owned by SessionSpine and continue through
  the existing sidebar and session intent seams.
- The drawer remains subordinate to the active primary frame and MUST
  NOT become a second application shell.
- Every primary phone view becomes one frame-first mobile primary block inside
  the same uniform edge-chrome, bezel, frame, rim, and card-radius law.
- Narrow Guardian keeps its current utility/header controls, runtime notices,
  session rail, transcript or empty state, and composer inside the canonical
  Guardian frame.
- Wallpaper or the configured gradient remains visible around that frame
  through one uniform `--edge-chrome` perimeter on all four sides.
- The drawer remains a subordinate overlay/projection and MUST NOT resize the
  underlying frame.
- Narrow Guardian uses a compact two-control header:
  - The left control owns navigation-drawer invocation (sidebar toggle).
  - The right control owns secondary Guardian tools (utility menu).
  - Displaced header actions (Open Workspace, settings, voice/audio, profile,
    new thread, thread-level actions, and overflow) remain available through
    the Guardian tools utility menu.
  - Runtime-health and authentication-truth notices remain outside the
    utility menu and preserve their exact meaning.
  - The Codexify mark remains inside the drawer.
- Desktop Guardian retains its existing persistent controls (global
  navigation pill, persistent sidebar, Open Workspace, settings/audio/profile
  icons, chat action icons, and runtime-notice positioning).
- This Codexify-mark disclosure contract applies to the shared primary phone
  drawer. Desktop Guardian navigation and its persistent sidebar remain
  unchanged.
- The transcript is the durable record layer and remains the internal vertical
  scroll owner.
- In narrow Guardian only, focusing the composer makes that existing composer a
  foreground interaction projection over the lower transcript. The projection
  may visually occlude record content, but remains inside and subordinate to
  the single Guardian primary card.
- The frame and compact header retain their geometry while the keyboard changes
  the settled visible aperture. The page is not rebuilt around the input, and
  the AppShell document does not become the chat scroll owner.
- Near the latest turn, transcript-only compensation keeps the active subject
  visible above the projected composer. A user reading meaningfully older
  content retains that reading position.
- After the existing authored-message submission promise resolves, the draft
  clears through its existing seam, the composer blurs, the keyboard may
  dismiss, and the full record aperture returns. This boundary proves authored
  message submission only; it does not claim assistant completion.
- A rejected submission preserves the draft and focus availability and does
  not falsely enter record mode.
- Opening the navigation drawer or Guardian tools menu suspends the projection
  and preserves the draft.
- Narrow Guardian uses one compact composer pill. Its direct mobile interaction
  surface retains the existing attachment/add actions, authored text input,
  supported voice action, and send action. It does not retain a persistent
  selector row.
- Advanced project, provider, model, inference-mode, and retrieval
  configuration is available through the bounded deterministic frontend
  commands `/project`, `/provider`, `/model`, `/mode`, and `/retrieval` when
  the corresponding existing control and option set are available. A
  `/profile` command is present only when the Composer already owns a canonical
  profile control and option set.
- The command-only draft grammar is `/<command> [value]`. A recognized command
  invokes the existing configuration callback, clears its command draft, and
  never enters the transcript or authored-message persistence path. Commands
  embedded in prose, unknown slash text, and escaped `//` text remain ordinary
  user-authored text and continue through the existing send boundary.
- Command parsing is a presentation-side, deterministic registry operation. It
  does not invoke Guardian reasoning, prompts, a model, backend routes, or the
  command bus. Existing availability, compatibility, authorization, and
  disabled-state truth surfaces remain authoritative.
- Desktop Guardian retains its existing composer flow, typography, controls,
  visible selectors, and focus behavior.
- Documents mirrors the Guardian phone shell structurally without adopting chat
  content or session behavior. Documents thread/project selection continues to
  update DocumentsScope; Dashboard, Gallery, and Settings thread selection or
  New Chat enters Guardian without mutating DocumentsScope.

Session Pill Rail (implemented):

Placement:

Directly below the Guardian header and above the message region/composer rail.

Responsibilities:

Tabs are session-layer state only (not global app navigation).

Left side is a horizontally scrollable tab-pill strip (open tabs + active tab).

When only one tab exists, the left tab-pill strip is hidden.

Right side is a utility cluster: model picker, New Tab (+), overflow menu.

Rail interactions MUST dispatch SessionSpine intents; rail components MUST NOT mutate tab/session state directly.

B. DOCUMENTS VIEW

2-column split:

+----------------------------------------+-------------+
| DocumentsList (card)                   | Workspace   |
| (var(--flex): docsLayout.listFlex)     | (card)      |
+----------------------------------------+-------------+

Rules:

Left side scrolls

Right side is optional and collapsible

MUST use card structure for BOTH columns

On phone layouts, Documents uses the primary frame-first shell instead of the
desktop split. Its compact frame header summons the shared mobile drawer, and
its document content begins at the same shell depth and edge-chrome boundary as
Guardian. The existing SidebarRoot projection remains authoritative for
DocumentsScope selection and is composed into the shared drawer rather than a
Documents-owned overlay.

C. GALLERY VIEW

Single-column flow:

GalleryCard
  -> InnerCard
      -> Grid

Rules:

Grid MUST be token-controlled (--image-grid-gap, --image-grid-cols)

Images MUST use border: var(--panel-border)

D. DASHBOARD VIEW
+-----------------------------+----------------------+
| Thread Grid (primary card) | Workspace Drawer     |
+-----------------------------+----------------------+

Rules:

Workspace is right-fixed width via --workspace-w

Thread grid MUST use tokenized grid spacing

E. SETTINGS VIEW
+------------------------------------------+
| SettingsCard                             |
| [ compact full-width internal tab dock ] |
| [ responsive tabpanel content grid      ] |
+------------------------------------------+

Rules:

Card is centered in large screens

Full-width in small screens

Settings remains one primary card. Its internal tabpanel content MAY use a
responsive two-column grid on sufficiently wide screens and MUST collapse to
one column on narrow screens. Sections that require additional width MAY span
both internal columns. The tab dock remains inside the single Settings card.

The two internal columns MUST NOT become independent primary cards or separate
navigation contexts. This exception does not permit arbitrary page-level
columns outside the Settings card.

XI. WORKSPACE DRAWER RULES

The workspace drawer:

Is ALWAYS card-structured

Has fixed width defined via tokens (--workspace-w)

Can open from Dashboard, Guardian, or Documents

MUST NOT animate width using arbitrary CSS — only tokens

XII. PROHIBITED STRUCTURAL PATTERNS

Agents MUST NOT:

Add arbitrary div wrappers around primary cards

Add spacing using pixels instead of tokens

Apply border-radius directly on components

Add card shadows outside the token rules

Create new layout patterns not listed in this document

Use fixed widths except via token overrides

Duplicate card hierarchy

Mix Tailwind spacing with token spacing in layout-level elements

XIII. STRUCTURAL CHANGE PROCESS

Any change to these structural rules must:

Be proposed via PR labeled: ui/layout:update

Include diagrams

Include before/after view exports

Include justification for structural changes

END OF FILE
