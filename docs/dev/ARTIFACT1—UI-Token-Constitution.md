CODEXIFY UI TOKEN CONSTITUTION
The Immutable Laws of The Interface

This document defines the canonical, non-negotiable token system that governs every pixel inside Codexify.
Everything that touches the UI — components, layouts, glass, gradients, spacing, radii, shadows, and responsiveness — MUST conform to this specification.

If you hand this to an agent, they will never again guess, improvise, hallucinate, or “kinda follow” the style.
This IS the source of truth.

I. PURPOSE

To establish a universal design language for:

Codexify (Web)

Codexify (Electron)

PulseOS

Mobile (React Native)

Any embedded UI surface (VisionOS, in-app panels, etc.)

These tokens ensure:

Visual consistency

Theming parity

Predictable interaction

Composability

Agent-safe UI generation

II. TOKEN LAYERS

Codexify’s UI is governed by three token layers:

1. Root Tokens (Global Scene Tokens)

Define:
Global architecture, background gradients, wallpaper behavior, color system, baseline radii.

These tokens live at the <html> or AppShell level.

2. Layout Tokens (View & Container Tokens)

Define:
Layouts, cards, glass geometry, spacings, constraints, responsive rules.

Defined at per-view wrappers (documents, gallery, settings, guardian).

3. Component Tokens (Element Tokens)

Define:
Individual element radii, padding, bezels, chips, inputs, modals, cards.

Applied either via CSS variables or component props.

III. ROOT TOKEN SET (Declared in AppShell)

These MUST exist everywhere.

--radius-micro: 12px;             // micro UI: pills, chips, small buttons
--radius-tile: 19px;              // major UI: cards, tiles, panels
--card-radius: 19px;              // explicit pointer for all card-level surfaces

--edge-chrome: 6px;               // PWA safe-area + outer padding
--shell-gap: 16px;                // gap between columns, cards, rows
--viewport-radius: 19px;          // main frame rounding
--page-pad: 0px;                  // view-level padding (overridable)

--card-pad: 12px;                 // internal card padding
--frame: 1.5px;                   // outer frame thickness between bezel + rim

--bezel: 6px;                     // margin between glass → content surface
--rim: 1.5px;                     // inner content rim

Global Colors (Auto-resolved via theme)
--panel-bg
--panel-sheet
--panel-sheet-border
--panel-border
--panel-border-strong
--chip-bg
--text
--muted
--accent
--accent-weak
--accent-strong
--pill-active-text

Legacy Pointer Aliases
--radius: var(--tile-radius);
--board-edge: var(--edge-chrome);
--gutter: var(--shell-gap);

These MUST remain for backward compatibility.

IV. LAYOUT TOKENS (View-Specific Overrides)

Each view can override the following:

--radius
--frame
--bezel
--rim
--gutter
--card-pad

--w
--min-w
--max-w
--h
--min-h
--max-h

--flex
--workspace-w

Rules:

View-level overrides MUST wrap the entire card cluster.

Glass geometry tokens (--bezel, --frame, --rim) MUST NOT be applied directly on internal elements.

Dimension tokens MUST drive layout, not arbitrary widths/heights.

Examples:
Fixed-height card:
{"--h": "560px", "--flex": "0 0 auto"}

Responsive min-height:
{"--min-h": "clamp(520px, 70vh, 900px)"}

2:1 column split:
{"--flex": "2 1 0%"}  // left
{"--flex": "1 1 0%"}  // right

Workspace width:
{"--w": "clamp(16rem, 22vw, 28rem)", "--flex": "0 0 var(--w)"}

V. COMPONENT TOKENS

Every component must respect the following tokens:

Cards
--card-radius
--card-pad
--frame
--bezel
--rim

Chips
--radius-micro
--chip-bg
--muted
--text

Inputs
--radius-micro
--panel-border
--panel-bg
--text

Modals
--card-radius
--panel-bg
--panel-border

Glass Components

RefractiveGlassCard MUST support:

--bezel
--tile-blur
--lip-w
--depth-scale

And MUST NEVER introduce independent blur/radius hard-codings.

VI. COLOR SYSTEM RULES
Tokenized Colors Only

You MUST use:

var(--text)
var(--muted)
var(--accent)
var(--panel-bg)
var(--panel-border)

The following are forbidden:

Inline hex values in components

Tailwind arbitrary colors (bg-[#123])

Un-tokenized alpha RGBA values (unless part of a token definition)

Theme Switching Contracts

All surfaces MUST react correctly to:

resolved === "dark"

resolved === "light"

AppShell already defines colors. No component may override them.

VII. GLASS GEOMETRY RULESET

The glass system is the most fragile part of Codexify’s visual identity.

Core Rules:

--bezel controls the thickness of the glass margin.

--frame controls outer chrome.

--rim controls content inset.

Card wrappers MUST apply glass; inner content MUST NOT apply blur.

No component may introduce its own border radius — rely on tokens.

Correct Pattern
<div class="outer" style="padding: var(--bezel)">
  <div class="frame" style="padding: var(--frame)">
    <div class="rim" style="padding: var(--rim)">
      <content />
    </div>
  </div>
</div>

Incorrect Patterns (Disallowed)

Adding blur directly on content nodes

Using arbitrary pixel paddings

Hardcoding border radii

Applying shadows inconsistent with token rules

VIII. RESPONSIVE TOKEN CONTRACT

All screen-size adjustments MUST be made via token changes, not arbitrary code branches.

Allowed:
if (bp === "lg") return { "--flex": "0 0 50%" }

Forbidden:
style={{ width: bp === "lg" ? 480 : 320 }}   // ❌ No inline breakpoints

IX. DOCUMENT & GALLERY GRID TOKEN RULES
--image-grid-gap
--image-grid-cols
--project-tile-size
--doc-chip-height
--image-tile-size

These define grid spacing + density.
You MUST NOT use Tailwind spacing (gap-4) for these areas.

X. TOKEN MIGRATION PLAN (ALREADY IN APPSHELL)

As written in AppShell:

Extract static tokens → src/theme/tokens.json

Create src/theme/index.ts → exports injectCssVars()

Replace runtime tokens with token injection

Ensure tokens are 1:1 with the CSS variables in this Constitution

XI. ENFORCEMENT RULES (For Agents)

Any component or generated code MUST:

Use ONLY tokenized CSS variables

Use ONLY the radii defined in tokens

Use ONLY spacing defined in --gutter, --card-pad, etc.

NEVER hardcode colors

NEVER introduce new spacing magnitudes

NEVER define new border radii

NEVER attach independent blur/shadow/radius to glass components

ALWAYS wrap content in the glass → frame → rim hierarchy

This Constitution is absolute.

XII. CHANGE GOVERNANCE

To modify tokens:

Open a PR labeled: ui/tokens:update

Must include:

rationale

before/after screenshots

diff of changed tokens

confirmation all components still render correctly

No token modification may bypass review.

END OF FILE
