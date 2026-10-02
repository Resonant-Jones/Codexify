# Codexify System Surface Design Contract

## Status and scope

- Classification: architecture/design contract
- Status: accepted presentation language under [ADR-095](../adr/095-codexify-system-surface-design-language.md)
- Governing material-personalization decision: [ADR-064](../adr/064-orthogonal-ui-material-personalization.md)
- Evidence posture: documented contract
- Scope: presentation semantics and future visual implementation guidance

This document is the design bible for how Codexify communicates as the system.
It does not implement or prove a component, notification mechanism, delivery
path, persistence model, event, routing rule, or release-supported capability.
Existing runtime and protocol truth remains authoritative over presentation.

## 1. Presentation category

**System Surface** is the presentation category for Codexify-authored
communication that presents system state, requests consequential user input,
or provides system-owned setup or administrative information.

The governing rule is:

> Workspace UI is the user's environment. System Surface UI is Codexify
> speaking as Codexify.

These categories describe authorship and purpose. They are distinct from the
lower-level material and rendering choices in the UI canon, such as glass,
panel, chip, or frame. A System Surface still follows canonical rendering,
geometry, and token rules.

| Presentation category | Speaker and purpose | Design boundary |
| --- | --- | --- |
| Workspace/content surface | The user's environment and authored or selected content. | May use the ordinary workspace personalization model governed by ADR-064. |
| Guardian conversational surface | Guardian's conversational voice and interaction. | A reported error or status does not automatically receive Codexify system-authorship styling. |
| System Surface | Codexify speaking about system-owned state, setup, administration, or a consequential request. | Must remain recognizable across personalized workspace environments and preserve the system's authorship and semantic state. |

A message qualifies by its authorship and purpose, not by visual urgency.
Guardian prose does not become a System Surface merely because its subject is
an error, warning, or status. A future presentation may show system-owned
communication in a distinct System Surface, but this contract does not define
how such a message is generated, delivered, or authorized at runtime.

## 2. Eligible uses and restraint

System Surface language is appropriate for:

- onboarding and setup;
- runtime notices;
- warnings and non-fatal intervention;
- errors, failures, and blocked states;
- success and completion notices;
- permission requests;
- security and identity notices;
- destructive confirmations;
- migrations and upgrades;
- authentication or connection state that requires user attention; and
- important results from system-owned background operations.

Not every informational message deserves a System Surface. Routine content,
Guardian prose, project information, ordinary tool output, and low-value
ambient status must not use this category merely to attract attention. Use it
when system authorship or a consequential user decision needs to be clear.

## 3. Recognition invariants

Every System Surface preserves these distinctions:

- **Authorship:** the Codexify mark identifies who is speaking.
- **Message state:** a separate semantic glyph and category label identify
  what happened or what kind of intervention is needed.
- **Content:** the title and explanation state the matter in plain language.
- **Authority:** styling does not grant a permission, establish an action's
  authorization, or make a runtime guess authoritative.
- **Material:** the card belongs to Codexify's glass/material family without
  being absorbed into the personalized workspace environment.

The Codexify mark and the semantic state glyph have different roles and must
never collapse into one icon. For example, the Codexify mark says who is
speaking; a green check says what happened.

## 4. Canonical card anatomy

Keep a stable reading order and hierarchy. A surface may omit inapplicable
regions, but it must not rearrange the message so that authorship, state,
meaning, and action become ambiguous.

1. **System identity/header.** Establishes that Codexify is the speaker.
2. **Codexify mark.** Uses the canonical mark as the visual authorship cue.
3. **Optional dismiss/age/progress metadata.** Shows only applicable metadata
   that is actually available and valid for the containing flow.
4. **Semantic state indicator.** A state glyph communicates informational,
   progression, success, attention, error, or destructive meaning.
5. **Semantic category label.** Names the kind of system communication.
6. **Primary title.** States the main event, condition, or question.
7. **Supporting explanation.** Explains impact, context, and the next useful
   step in concise language.
8. **Optional structured detail/inset.** Makes scope, affected objects,
   consequences, or relevant technical detail inspectable.
9. **Action region.** Groups available actions in a predictable location.
10. **Primary, secondary, and destructive actions as applicable.** Preserves
    the action hierarchy and clear labels.

The header is compact. The message occupies the visual center. Dismissal and
metadata remain quiet. The action region is visually separated from the
explanation without introducing an unrelated panel or competing header.
Responsive reflow may stack or wrap regions while preserving this reading
order and meaning.

### Canonical Codexify mark

Use the canonical asset:

frontend/src/assets/brands/codexify/codexify-mark.svg

Preserve the canonical asset's proportions and silhouette. The mark identifies Codexify/system authorship, not Guardian's personality,
conversation, or status. Do not replace it with an arbitrary generated
emblem, a locally redrawn approximation, or a severity glyph.

Use a restrained monochrome or system-compatible treatment unless an
explicitly approved brand contract says otherwise. The mark remains visually
separate from warning, error, success, and other semantic state glyphs. Do
not recolor the Codexify mark to carry severity.

## 5. Material language

The reference posture is restrained dark, translucent glass. System Surface
cards remain visibly related to Codexify's glass/material family while
preserving stronger control over translucency than ordinary workspace
surfaces. Dark glass is the reference, not a fixed theme polarity; any theme or
accessibility adaptation must preserve authorship and state hierarchy.

The material should feel official, calm, legible, and system-owned. It may
harmonize with the environment without becoming visually absorbed by it.
Avoid sterile opaque admin-panel styling unless accessibility or platform
constraints require a more opaque fallback.

Apply the material through these principles:

- restrained environmental translucency;
- controlled, token-governed blur;
- a thin material edge or border;
- subtle depth and shadow;
- no highly decorative refraction;
- no wallpaper-dependent semantic meaning; and
- no uncontrolled tint inherited from user material settings.

Translucency is decorative context, never the sole carrier of contrast,
severity, or meaning. The surface must remain readable across varied
workspace backgrounds.

## 6. Personalization boundary

ADR-064 continues to govern ordinary workspace material personalization.
Workspace personalization may substantially alter atmosphere. System Surface
adaptation preserves Codexify authorship, message hierarchy, semantic meaning,
and legibility.

System Surface may adapt to necessary theme, contrast, platform, and
accessibility conditions. It must not inherit arbitrary personalization when
that would weaken its recognition or state meaning. In particular:

- wallpaper, Paper Tone, Surface Temperature, Accent Color, Surface Depth, or
  another personalization axis must not change semantic status meaning;
- user accent color must not replace warning, error, success, or destructive
  semantics;
- environmental tint must not obscure Codexify's authorship cue or the state
  indicator; and
- the System Surface material envelope remains narrower than the ordinary
  workspace envelope.

Adaptation changes presentation only. It does not create or modify
personalization persistence, runtime state, or an appearance-control axis.

## 7. Semantic color roles

Use semantic roles rather than arbitrary literal colors. This contract defines
no palette values or new token names.

| Role | Meaning | Typical localized uses |
| --- | --- | --- |
| Neutral/informational | Information without a success, attention, or failure claim. | State glyph, category label, restrained material detail. |
| Blue action/progression | Ordinary primary action or system progression. Blue is not a severity signal. | Primary action, progress treatment, ordinary progression cue. |
| Green success/completed | A successful or completed result. | State glyph, category label, restrained edge or tint. |
| Yellow attention/caution | Attention, degraded or warming posture, caution, or non-fatal intervention. | State glyph, category label, restrained edge or tint, relevant action. |
| Red error/destructive | Error, blocked or failed state, destructive action, or high-consequence intervention. | State glyph, category label, restrained edge or tint, destructive action. |

Keep semantic color localized. Prefer the state glyph, category label,
restrained edge/glow/tint, and a state-specific action where appropriate. Do
not saturate the entire card green, yellow, or red. Text, labels, icon shape,
and action wording must reinforce color so color is never the only carrier of
meaning.

## 8. Typography hierarchy

Use stable typographic roles, all derived from shared typography tokens:

- **System/brand header:** compact authorship cue.
- **Semantic category label:** short, subordinate, and visually distinct.
- **Primary title:** the strongest message text and first content-level scan
  target.
- **Explanatory body:** readable supporting context and impact.
- **Metadata:** quiet age, progress, or dismissal details when applicable.
- **Structured detail:** legible supporting fields, scope, or affected-object
  descriptions.
- **Actions:** clear, readable control labels with visible hierarchy.

Compact uppercase category labels may include SETUP, RUNTIME NOTICE, RUNTIME
ERROR, TASK COMPLETE, PERMISSION REQUEST, SECURITY, CONFIRMATION, and
MIGRATION. These labels are presentation vocabulary. They are not automatically
runtime protocol tokens, and they do not justify creating a backend token
domain.

## 9. Spacing and geometry

Preserve a compact, predictable card anatomy through relative hierarchy:

- the identity/header row is smaller and quieter than the message title;
- the title is visually separated from the supporting explanation;
- the explanation and optional detail share a clear content grouping;
- the inset detail is subordinate to the title and action region;
- related actions share a group, separated from content; and
- dismiss and metadata controls remain outside the primary action's visual
  competition.

Do not invent isolated pixel values, a parallel styling system, or one-off
component geometry. Radius, padding, gaps, border, blur, shadow, typography,
button geometry, and responsive behavior must come from canonical/shared
tokens and the existing rendering canon.

## 10. Action hierarchy

- Show one visually dominant primary action when a primary action exists.
- Keep secondary actions quieter and easy to distinguish.
- Give destructive actions explicit semantic treatment and clear action text.
- Keep dismissal visually subordinate to a required action.
- Do not disguise required acknowledgement as passive dismissal.
- Prefer labels that name the action and affected scope over vague confirmation
  text.
- Preserve existing authority and permission boundaries; presentation does
  not authorize the action.

## 11. Motion

Motion communicates state or causality, not personality. Appropriate motion
may include controlled appearance or dismissal, progress movement, bounded
success confirmation, and a restrained attention cue when intervention is
needed.

Do not use decorative bouncing, playful personality animation, persistent
pulsing without a semantic reason, or motion that makes system authority feel
conversational or gamified. Honor reduced-motion preferences with an
equivalent static state and clear progress or completion communication.

## 12. Accessibility

Every implementation must provide:

- meaning that is not conveyed by color alone;
- contrast-safe text and actions;
- keyboard-accessible actions and visible focus;
- screen-reader labels for authorship and state icons;
- reduced-motion behavior;
- legibility over varied workspace backgrounds; and
- a sufficiently opaque fallback when translucency compromises readability.

The canonical mark's accessible name must identify Codexify as the speaker.
The state glyph needs a separate accessible label describing the state. Do
not announce the decorative mark as the warning, error, or success itself.

## 13. Responsive behavior

Use the same semantic anatomy on desktop, tablet, and phone. Layouts may reflow,
wrap, or stack actions as space narrows. They must preserve:

- Codexify authorship;
- semantic severity and state;
- action meaning and hierarchy;
- the difference between acknowledgement, action, and dismissal; and
- title-before-explanation reading order.

Responsive changes follow canonical tokens and shared layout behavior; they
must not create a separate phone-only visual language.

## 14. Anti-patterns

Do not use:

- arbitrary toast-library styling;
- one-off local notification palettes;
- user accent color in place of warning, error, success, or destructive
  semantics;
- wallpaper tint to determine status meaning;
- a Guardian avatar as the system-authorship mark;
- the Codexify mark recolored as a severity indicator;
- System Surface for every informational message;
- full-card saturated severity colors;
- bespoke radius, blur, or shadow systems;
- emoji as the sole status glyph;
- decorative animation that competes with message meaning; or
- runtime guesses presented as authoritative system notices.

## 15. Reference examples

These examples are presentation and content illustrations only. They do not
prove that the named runtime, notification, permission, migration, or action
capability exists.

### Success

- Category: TASK COMPLETE
- Title: Response ready
- Supporting explanation: The requested response is ready to review.
- Primary action: View thread
- Secondary action: Dismiss

### Attention

- Category: RUNTIME NOTICE
- Title: Model warming
- Supporting explanation: The selected model is preparing and may take longer
  to respond.
- Primary action: Learn more
- Secondary action: Dismiss

### Error

- Category: RUNTIME ERROR
- Title: Model runtime unavailable
- Supporting explanation: The selected runtime did not become available.
- Primary action: Retry
- Secondary action: Open settings

### Permission

- Category: PERMISSION REQUEST
- Title: Allow filesystem access?
- Structured detail: The explicit filesystem scope being requested.
- Primary action: Allow access
- Secondary action: Not now

### Confirmation

- Category: CONFIRMATION
- Title: Delete this document?
- Structured detail: The affected document and the consequence of the action.
- Primary action: Move to trash
- Secondary action: Cancel

### Migration

- Category: MIGRATION
- Title: Database update required
- Structured detail: Preservation, impact, and relevant recovery information.
- Primary action: Apply update
- Secondary action: Learn more

## 16. Presentation and runtime boundary

This contract defines a visual language, not a notification system. It creates
no notification delivery, persistence, priority, read/unread state, routing,
push behavior, event, background worker, protocol token, or release support.
Future implementations must first establish their own authorized runtime
contracts and must render only evidence-backed system state.
