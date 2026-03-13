ARTIFACT 3 — Codexify UI Rendering Protocol

Status: Canonical
Audience: Claude Code High, Codexify Frontend Execution Agents
Purpose: Define the only allowed method for rendering UI in Codexify.
Scope: React (web), React Native, and eventual PulseOS surfaces.

0. Core Rule

ALL Codexify UI MUST derive wholly from the Token Constitution and Geometry Canon.
No inline arbitrary CSS. No magic numbers. No one-off Tailwind values.
All dimensions, radii, colors, borders, and spacing MUST map to a token, and tokens MUST map to the canonical token system injected via AppShell.

If a token does not exist, you do not create a new constant — you create a new token, following the Token Constitution.

1. Rendering Law
1.1 The Token Precedence Stack

Rendering must resolve style values in this order:

Global Tokens injected via injectCssVars() (origin: AppShell)

Local View Overrides (view-level token masks, e.g. Documents, Settings)

Component Contract Tokens (FrameCard, RefractiveGlassCard, Pane components)

Fallback Semantic Tokens (legacy vars: --radius, --gutter, --board-edge)

If a value is needed and cannot be found in (1–4), the system MUST fail and prompt the developer to create a token.

2. Component Rendering Protocol

Every component MUST answer these questions before rendering:

2.1 What tokens does this component consume?

Examples:

--radius-micro

--tile-radius

--panel-bg

--bezel

--frame

--gutter

--card-pad

A component may NOT consume a token that is not declared in AppShell’s unified token layer.

2.2 What geometric constraints does it require?

Each component must define whether it requires:

Fixed width / height

Flexible (grow/shrink)

Clamp floors/ceilings

Responsiveness through breakpoints

Tokens for sizing (--w, --h, --min-h, --flex)

2.3 What surface does it render on?

Surface options:

Glass (RefractiveGlassCard)

Panel (--panel-bg + border)

Chip (--chip-bg)

Frame (inside a glass bezel region)

A component may NOT create a new visual category.

2.4 What is its container?

Containers must use:

padding: var(--board-edge)

gap: var(--gutter)

border-radius: var(--radius) family tokens

3. Layout Protocol
3.1 All layout is token-driven.

Examples:

Grid gap: gap-[var(--gutter)]

Card padding: p-[var(--card-pad)]

Workspace width: width: var(--workspace-w)

Rounded edges: rounded-[var(--radius)]

No numeric literals may be used in Tailwind except:

display utilities (flex/grid)

positioning utilities (absolute, inset-0, etc.)

text utilities (text-sm, text-xs)

z-index utilities

3.2 Clamp Rules

Clamp expressions MUST follow:

clamp(min_px, %vh or %vw, max_px)

Tokens used inside clamp:

--min-h

--card-height

--workspace-w

4. Glass Rendering Protocol

Codexify uses a unified strategy for glass UI, via RefractiveGlassCard.

4.1 Components may not reproduce glass manually.

Only allowed method:

<RefractiveGlassCard
  wallpaperUrl={activeWallpaper}
  intensity={0.006–0.012}
  aberration={0}
  className="rounded-[var(--radius)]"
/>

4.2 Aberration must always be 0.

Codexify design language does not allow chromatic dispersion.

4.3 Bezel Control

--bezel token controls the gap between glass and content.

Allowed values:
4px, 6px, 8px via token override.

Not hard-coded.

5. Panel Rendering Protocol

Panels must use:

background: var(--panel-bg)
border: 1px solid var(--panel-border)
box-shadow:
  inset 0 1px 0 rgba(255,255,255,0.06),
  inset 0 -10px 24px rgba(0,0,0,0.18)
filter: drop-shadow(…)

If a component needs a “panel”, it must either use:

FrameCard, or

“Tile” surface pattern (identical to the panel above)

A component may not write its own panel style.

6. Interaction Protocol

All interactive surfaces must follow:

Use tokens for padding and border-radius.

Hover/focus states must use:

opacity

border-color: var(--accent-weak)

background-color: var(--panel-bg) (for subtle states)

No raw hex values allowed in interaction styling.

7. Typography Protocol

Font is set globally in AppShell:

SF Pro Display, SF Pro Icons, …

Components may only specify:

text-xs, text-sm, text-base

font-medium, font-semibold

No other typography customizations allowed.

8. Breakpoint Protocol

Breakpoints are controlled by:

useBreakpoint() → sm | md | lg | xl | 2xl

Appshell coordinates responsive behavior:

DocumentView scaling

SettingsView width control

Dashboard layout

All components must follow the parent’s responsive contract.

9. Rendering Decision Tree (Mandatory)

Every component MUST evaluate these in order:

1. Which tokens does this component need?
2. What surface is it using? (glass/panel/chip)
3. What container is it inside?
4. What geometry does it require? (flex, fixed, clamp)
5. What breakpoints modify this geometry?
6. How does it integrate with AppShell’s global vars?
7. Are all values token-derived? (If no → REJECT)
8. Does it conflict with an existing design language rule?

If any step fails, the change is invalid and must be redesigned.

10. Example: Fully Valid Codexify Component

Here is the minimal pattern that all new components must follow:

export function ExampleTile({ children }) {
  return (
    <div
      className="rounded-[var(--radius)]"
      style={{
        padding: "var(--board-edge)",
        borderRadius: "var(--card-radius)",
      }}
    >
      <FrameCard
        liquidBezel
        tone="base"
        aberration={0}
        className="rounded-[var(--radius)]"
      >
        <div className="p-[var(--card-pad)]">
          {children}
        </div>
      </FrameCard>
    </div>
  );
}

This component:

Uses no hard-coded CSS numbers

Renders glass via FrameCard

Respectfully inherits tokens from AppShell

Follows Canon exactly
