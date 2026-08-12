# ADR-064: Orthogonal UI Material Personalization

## Status

Accepted

## Date

2026-08-01

## Canonicalization History

This Accepted ADR was originally stored as ADR-055. It is independent from
ThreadSpace ↔ WhisperMesh despite their shared former number. Phase 4B retained
ThreadSpace ↔ WhisperMesh as ADR-055 and independently allocated Orthogonal UI
Material Personalization as ADR-064.

Only the numeric identity and path changed. Accepted posture and the
2026-08-01 date remain unchanged, as do the material-axis, persistence and
migration, accessibility, and non-goal doctrine. Former ADR-055 Orthogonal UI
references remain historical evidence.

## Scope and evidence posture

This is an architecture-impacting, docs-only decision. It governs the
semantics and future implementation boundaries of Codexify appearance
personalization. It does not implement a control, change persistence, alter
rendering, or widen the current release promise.

The decision is grounded in code-path evidence from the Paper Tone
implementation lineage, the associated light and dark material review, and
the UI token and structural design canon. Those evidence sources establish
design semantics; they are not, by themselves, release or runtime proof.

## Context

Codexify's Appearance controls previously exposed two independent material
axes: Surface Depth and Surface Warmth. Surface Warmth used a signed range to
move material bias from cool to warm across light and dark themes.

A later implementation introduced an accepted light-mode-only Paper Tone
control with a progression from Neutral through Ivory, Cream, Parchment, and
Legal. That implementation reused `cfy.surfaceWarmth` and replaced the
previous warmth derivation rather than adding a separate finish axis. As a
result, a single stored value came to represent two different visual
transformations:

- chromatic temperature or illumination bias; and
- light-mode paper substrate or aging finish.

That replacement made the material system less expressive. Cool white and
porcelain-like light surfaces were no longer represented, and dark material
territories such as graphite, slate, titanium, cool gray-green, amber, umber,
and rust-adjacent warmth were no longer available through the former signed
mapping. Negative legacy warmth values were flattened to neutral, and dark
mode stopped consuming the warmth mapping.

The architectural correction is additive. Paper Tone remains accepted and
useful. Surface Temperature is restored as an independent cross-theme axis,
and Surface Depth remains independent from both.

## Decision

Codexify material personalization is multidimensional and additive. Each
appearance control has one stable visual responsibility, and each axis is
derived through token-driven, accessibility-bounded material semantics.

The canonical model consists of:

1. Theme polarity: Light, Dark, or System resolution.
2. Surface Depth: cross-theme density, lightness, and material weight.
3. Surface Temperature: signed cross-theme cool-to-warm material bias.
4. Paper Tone: light-mode-only paper substrate or finish.
5. Accent Color: selection, action, focus, and user identity signaling.
6. Background Treatment: wallpaper depth, fade, and environmental
   relationship.

Paper Tone must not replace Surface Temperature. Surface Depth must not become
a hue control. Accent Color and Background Treatment must not become hidden
material-temperature controls.

## Decision drivers

- Preserve distinct visual transformations instead of collapsing nearby
  concepts into one scalar.
- Retain the accepted Paper Tone feature while restoring cool-to-warm
  material expression across both theme polarities.
- Keep Appearance state understandable, inspectable, and migratable.
- Preserve token-driven rendering and the existing UI token and structural
  design canon.
- Allow substantial user variation without making one fixed palette the
  source of Codexify's identity.
- Protect contrast, semantic status colors, focus visibility, and content
  legibility at every material extreme.
- Keep the future implementation additive, reversible, and separately
  testable.

## Invariants

- Paper Tone remains an accepted feature and remains light-mode-only.
- Surface Temperature and Paper Tone remain separate concepts and separate
  responsibilities.
- Light and dark modes may both support bounded cool and warm material bias.
- Surface Depth applies to both themes and controls density, lightness, and
  perceived material weight only.
- Surface Depth does not implicitly determine hue or paper aging.
- Accent Color remains an interaction, state, and identity signal rather than
  a replacement material engine.
- Background Treatment remains independent from surface temperature and paper
  finish.
- A personalization control represents one stable visual transformation.
- Existing semantic status colors remain protected.
- User material choices remain bounded by contrast and legibility.
- Persistence keys must not be silently reused for different visual
  semantics.
- No future implementation may claim that this ADR itself restored a slider,
  migration, or runtime behavior.

## Material-axis model

| Axis | Responsibility | Scope and boundary |
| --- | --- | --- |
| Theme polarity | Selects Light, Dark, or System-resolved polarity. | Establishes the theme context; it does not encode material warmth. |
| Surface Depth | Controls perceived density, lightness, and material weight. | Applies to light and dark themes; it must not implicitly determine hue or paper aging. |
| Surface Temperature | Controls signed cool-to-warm chromatic material bias. | Applies to light and dark themes without changing theme polarity; it remains independent from Paper Tone. |
| Paper Tone | Controls paper substrate or finish from neutral paper through restrained yellowed-paper territory. | Applies only when the resolved theme is light; its stored value may persist in dark mode but must not affect dark rendering. |
| Accent Color | Communicates selection, action, focus, and user identity. | Applies to interaction and state roles; it must not substitute for base material tuning. |
| Background Treatment | Controls wallpaper depth, fade, and environmental relationship. | Applies to the scene/background relationship; it must remain independent from material temperature and paper finish. |

The names used for material territories are descriptive design vocabulary,
not a requirement for hardcoded palette stops. Implementations may use
continuous or otherwise token-governed derivations as long as their observable
semantics preserve these responsibilities.

## Single-responsibility rule for appearance controls

A personalization control must represent one stable visual transformation.
Controls may not silently change semantic purpose merely because another
desired effect is nearby.

The canonical responsibilities are:

- Surface Depth changes density and lightness.
- Surface Temperature changes cool/warm material bias.
- Paper Tone changes light-mode paper finish.
- Accent Color changes interaction and state color.
- Background Treatment changes wallpaper presentation.

A future feature may add a new axis. It must not replace or overload an
established axis without an explicit ADR that supersedes this decision.

## Theme-specific behavior

### Light mode

Light mode is not restricted to neutral white or progressively yellow paper.
The bounded material family may include:

- cool white;
- porcelain;
- neutral white;
- warm white;
- ivory;
- cream;
- parchment; and
- restrained legal-pad yellow.

Surface Temperature makes a white surface cooler or warmer while allowing it
to remain recognizably white. Paper Tone changes the substrate or finish
toward cream, parchment, and restrained yellow paper. The distinction is
intentional:

- Temperature tunes illumination or chromatic material bias.
- Paper Tone tunes paper substrate or aging finish.

Paper Tone may remain stored while dark mode is active, but it must not affect
dark-mode rendering.

### Dark mode

Dark mode is not restricted to OLED black or one neutral slate. Surface
Temperature may express a bounded progression through material territories
including:

- OLED black;
- graphite;
- cool slate;
- titanium;
- cool gray-green;
- neutral charcoal;
- warm charcoal;
- umber; and
- restrained rust or oxidized-metal warmth.

These are descriptive territories, not mandatory hardcoded stops. Dark-mode
endpoints must remain low enough in chroma to read as interface material,
contrast-safe, subordinate to content, recognizably dark mode, and free from
neon or highly saturated full-surface color.

### Visual identity doctrine

Codexify must not depend on one mandatory black, white, green, purple, or
other fixed interface palette for recognition. Durable identity should
primarily come from:

- structural composition;
- FrameCard hierarchy;
- containment and spacing;
- glass and material relationships;
- interaction semantics;
- typography;
- canonical control behavior; and
- accessibility and state language.

Users may create substantially different material environments while still
using the same coherent Codexify interface system. Personalization may follow
personal aesthetic preference, background imagery, environmental lighting,
visual comfort, or task context. Visual obscurity is not a security feature.

## Persistence and migration doctrine

Future implementation must keep these responsibilities separate:

- `cfy.surfaceDepth` — Surface Depth.
- `cfy.surfaceTemperature` — signed Surface Temperature.
- `cfy.lightPaperTone` — light-mode-only Paper Tone.

Semantic key reuse between Surface Temperature and Paper Tone is prohibited.

`cfy.surfaceWarmth` is now a legacy ambiguous key. Depending on version
lineage, its value may represent either the historical signed temperature
control or the newer Paper Tone control. Future migration must explicitly
resolve or quarantine that ambiguity.

Migration doctrine is:

- Do not invent lost cool-temperature values.
- Preserve the currently visible Paper Tone where it is safely identifiable.
- Default restored Surface Temperature to neutral `0` when historical intent
  cannot be proven.
- Separate legacy resolution, persistence writes, and runtime derivation so
  each can be tested independently.
- Do not prescribe an unverified automatic migration algorithm in this ADR.

The migration behavior is future implementation work. This record does not
claim that separate keys or migration already exist.

## Rendering-order contract

The intended conceptual derivation order is:

1. Resolve theme polarity.
2. Select the theme's neutral base material.
3. Apply Surface Temperature.
4. Apply Paper Tone only when the resolved mode is light.
5. Apply Surface Depth.
6. Apply component-role material offsets.
7. Enforce contrast and accessibility constraints.
8. Apply Accent Color only to interaction and state roles where appropriate.

Implementation-level optimization is permitted when the observable semantics
remain equivalent to this order. Paper Tone must never be applied to dark-mode
surfaces, and Accent Color must not become an implicit base-material tint.

## Accessibility boundaries

Personalization may not compromise:

- text contrast;
- focus visibility;
- selected-state recognition;
- disabled-state recognition;
- error, warning, success, or informational semantics;
- legibility of file-type labels and content; or
- minimum discernibility between nested surfaces.

Semantic status colors must not be remapped merely to match a selected
material temperature. Extreme material values must be bounded or corrected to
preserve accessible output. Token derivation, contrast checks, and component
role offsets remain subordinate to these requirements.

## Consequences

Positive consequences:

- Paper finish and cross-theme temperature can evolve independently.
- Cool, neutral, and warm material families remain expressible in both theme
  polarities within bounded accessibility limits.
- Future settings and persistence code can communicate stable semantics.
- Codexify's identity can remain coherent across broad user-configured
  material variation.
- Migration can distinguish known state from ambiguous historical state.

Costs and tradeoffs:

- Appearance state requires one more independent value and more explicit
  derivation boundaries.
- Migration must handle an overloaded legacy key without pretending that
  historical intent is always recoverable.
- Visual proof must cover both themes, axis combinations, and material
  extremes rather than only the neutral default.

## Rejected alternatives

### Keep only Surface Depth and Paper Tone

Rejected because this removes cool/warm material expression and collapses
illumination bias into paper aging.

### Expand Paper Tone to include cool colors

Rejected because a single unsigned substrate control would still combine two
distinct transformations and would make its semantic range harder to reason
about.

### Use separate hardcoded palettes for light and dark mode

Rejected because fixed palettes reduce continuous personalization and
complicate token consistency across themes and components.

### Let Accent Color tint all base materials

Rejected because Accent Color communicates interaction, state, and identity;
it is not the full surface-material domain.

### Restore Surface Warmth and remove Paper Tone

Rejected because Paper Tone provides a distinct and desired light-mode finish
that should remain available.

## Implementation follow-through

The next implementation slice is future work, not current runtime truth. It
should cover:

- restoring signed Surface Temperature state;
- adding a third slider to Appearance settings;
- separating the three persistence keys;
- safely resolving or quarantining the overloaded legacy key;
- restoring bounded cross-theme temperature derivation;
- retaining light-only Paper Tone; and
- adding focused unit and visual proof across both themes and material
  extremes.

That slice must not alter the responsibilities in this ADR, weaken
accessibility boundaries, or widen the release claim without its own
implementation and proof review.

## Non-goals

This ADR does not:

- implement the Surface Temperature slider;
- modify AppShell, SettingsView, Paper Tone utilities, tokens, CSS, or tests;
- change localStorage behavior;
- create a migration;
- alter Paper Tone behavior;
- choose final color endpoints or hardcoded palette values;
- redesign Appearance settings;
- change navigation-glass behavior;
- modify release truth;
- repair unrelated ADR-index formatting or historical numbering; or
- change backend, provider, deployment, queue, worker, or persistence runtime
  behavior.

## Evidence anchors

- `docs/architecture/00-current-state.md` remains the short-horizon release
  truth and is intentionally unchanged by this decision.
- `docs/dev/ARTIFACT1—UI-Token-Constitution.md` governs tokenized color,
  material, semantic-state, and accessibility boundaries.
- `docs/dev/ARTIFACT1B—CODEXIFY-STRUCTURAL-LAYOUT-SPECIFICATION.md` governs
  the structural and containment relationships that personalization must
  preserve.
- `docs/architecture/design/codexify-design-architecture-index.md` is the
  navigation authority for the design-canon lane.
- Commit `d3d71834e12f26cffa108a65982fb605d9682726`, `Refine light-mode paper
  tone controls`, records the Paper Tone implementation lineage, including
  its light-only mapping and legacy `cfy.surfaceWarmth` reuse.
- The corresponding `AppShell`, `SettingsView`, and `paperTone.ts` code-path
  review establishes the distinction between the former signed range and the
  newer light-only finish mapping.
- The associated light/dark visual review is design evidence for preserving
  the wider material range; it is not runtime health, migration proof, or a
  release qualification artifact.

