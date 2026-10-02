# ADR-095: Codexify System Surface Design Language

- Status: Accepted
- Date: 2026-10-02

## Context

Codexify's workspace can be personalized while retaining its structural and
interaction canon. System-owned communication has a different responsibility:
the user must be able to recognize when Codexify is speaking, understand the
message's state, and distinguish that state from both the user's environment
and Guardian's conversational voice.

Without a shared presentation contract, setup flows, runtime notices,
permission prompts, confirmations, security messages, and other system-owned
surfaces can acquire unrelated styling. The existing token-driven UI canon
and [ADR-064: Orthogonal UI Material Personalization](064-orthogonal-ui-material-personalization.md)
provide the governing material and accessibility model, but do not define this
system-authored presentation category.

This decision is presentation architecture only. It does not establish that a
notification mechanism or any particular system-message runtime exists.

## Decision

Codexify establishes **System Surface** as a sanctioned presentation category
for Codexify-authored communication that presents system state, requests
consequential user input, or provides system-owned setup or administrative
information.

The governing distinction is:

> Workspace UI is the user's environment. System Surface UI is Codexify
> speaking as Codexify.

Workspace/content surfaces remain the user's environment and continue to use
the personalization model in ADR-064. Guardian conversational surfaces remain
Guardian's conversational voice; reporting an error or status does not, by
itself, make a Guardian message a System Surface or grant it system-authorship
styling.

System Surface uses a recognizable, controlled glass/material treatment,
stable message hierarchy, canonical Codexify authorship mark, and protected
semantic state roles. It supports required theme and accessibility adaptation
but has a narrower personalization envelope than ordinary workspace UI.
Semantic status meaning remains independent of wallpaper, Paper Tone, Surface
Temperature, Accent Color, and other user material choices.

The detailed implementation-facing presentation rules are in the
[System Surface Design Contract](../design/system-surface-design-contract.md).
That contract treats presentation labels as design vocabulary; it does not
create runtime protocol tokens or prescribe notification lifecycle behavior.

## Relationship to ADR-064

This decision aligns with and does not supersede ADR-064. ADR-064 continues to
govern ordinary workspace material personalization, its independent axes,
token-driven rendering, and accessibility boundaries. System Surface applies
those same token and accessibility laws while constraining environmental and
personalization influence enough to preserve Codexify authorship and semantic
state recognition.

This ADR adds no appearance axis, CSS variable, token definition, persistence
key, migration, or implementation rule that overrides ADR-064.

## Invariants

- System Surface remains distinguishable from workspace/content and Guardian
  conversational surfaces.
- The canonical Codexify mark identifies system authorship; a separate
  semantic glyph and label communicate message state.
- System Surface retains Codexify's glass/material family while using a more
  controlled material envelope than ordinary workspace UI.
- Semantic status roles remain protected from user personalization and are
  never communicated by color alone.
- Geometry, color, blur, depth, typography, controls, and responsive behavior
  remain governed by shared canonical UI tokens.
- Presentation vocabulary does not create runtime tokens or notification
  semantics.
- This decision changes no supported-runtime or release claim.

## Scope and evidence posture

This ADR establishes a documented presentation contract. It makes no claim
about implementation, notification delivery, persistence, priority,
read/unread state, routing, push, background workers, or a notification center.
It governs presentation semantics, not whether any particular notification
mechanism exists.

The decision does not change [00 Current State](../00-current-state.md), runtime
behavior, onboarding implementation, or supported release posture.

## Non-goals

- Implementing or restyling frontend components, onboarding, or notifications.
- Defining notification persistence, delivery, routing, priority, read/unread
  semantics, events, or background processing.
- Creating a notification center, push notifications, backend models, or
  protocol tokens.
- Changing workspace personalization behavior, CSS variables, or canonical
  token definitions.
- Replacing Codexify brand assets or claiming new runtime or release support.
