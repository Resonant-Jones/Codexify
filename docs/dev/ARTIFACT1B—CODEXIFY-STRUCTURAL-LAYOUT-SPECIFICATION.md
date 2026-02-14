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

Always sticks to top-left

Always uses glass component + pill style

No margins except those uniquely required by visual balance

NEVER alters the main content geometry

Navigation is logically independent (no absolute overlays except pill)

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

Settings: left card centered, right stays empty

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

Session Pill Rail (implemented):

Placement:

Directly below the Guardian header and above the message region/composer rail.

Responsibilities:

Tabs are session-layer state only (not global app navigation).

Left side is a horizontally scrollable tab-pill strip (open tabs + active tab).

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
+-------------+
| SettingsCard |
+-------------+

Rules:

Card is centered in large screens

Full-width in small screens

NEVER add additional columns

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
