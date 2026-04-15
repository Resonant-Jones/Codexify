# Module Surface Checklist

> Classification: implementation checklist
> Status: operational
> Scope: first-party module-class surfaces inside Codexify
> Parent documents:
>
> * Module Header + Secondary Pill-Nav Canon v1
> * Native Presentation SDK Contract v1
>   Use this checklist during design, implementation, review, and cleanup of any module-class tool surface.

## Purpose

This checklist turns the module canon into a fast implementation gate.

Use it when:

* building a new first-party module
* redesigning an existing module-like surface
* reviewing whether a surface is drifting into settings-page density
* validating that a module still feels native inside Codexify

This checklist is not a substitute for the parent canon.
It is the practical inspection pass.

---

## 1. Surface Classification

Before doing anything else, confirm the surface is actually a **module-class** surface.

### Confirm all of the following

* [ ] The surface has a distinct tool identity
* [ ] The surface has a clear primary task
* [ ] The surface has local actions or modes
* [ ] The surface has enough internal structure to justify a Module Header
* [ ] The surface is not better classified as chat, viewer, gallery, companion surface, or inline utility

### Stop if any of the following are true

* [ ] This is really app-wide navigation
* [ ] This is really a passive viewer
* [ ] This is really a chat stream
* [ ] This is really a small utility widget
* [ ] This is being forced into module form just because modules look nice

---

## 2. Module Header Check

A valid module starts with a compact Module Header.

### Required

* [ ] Title is present
* [ ] Descriptor is short
* [ ] Header reads like module identity, not documentation

### Check for violations

* [ ] No long explanatory paragraph under the title
* [ ] No oversized disclaimer text
* [ ] No pane labels masquerading as header content
* [ ] No repeated internal mode labels
* [ ] No implementation-language controls like `Show Utility Pane`

### Quality test

* [ ] A user can understand what the module is within one glance
* [ ] The header does not consume unnecessary vertical space
* [ ] The header feels like a nameplate, not a hero banner

---

## 3. Action Zone Check

The Action Zone must appear immediately after the Module Header.

### Required

* [ ] Immediate actions are visible beneath the header
* [ ] Local controls feel operational
* [ ] The user can see what to do next without scrolling

### Check for violations

* [ ] No second fake header
* [ ] No long instructional copy inside the Action Zone
* [ ] No stacked administration bands before work begins
* [ ] No duplicated identity blocks in the Action Zone

### Quality test

* [ ] The hand naturally lands here after the header
* [ ] Save/reset/mode controls are easy to find
* [ ] The Action Zone is compact, not ceremonial

---

## 4. Secondary Pill-Nav Check

Only use Secondary Pill-Nav when the surface genuinely needs local section or mode navigation.

### Use it only if true

* [ ] The module has meaningful internal sections or modes
* [ ] Those sections are local to the module
* [ ] A pill-nav pattern improves clarity over simpler controls

### Check for violations

* [ ] Not being used for app-wide route navigation
* [ ] Not overloaded with unrelated actions
* [ ] Labels are concise
* [ ] Selected state is obvious
* [ ] It does not visually impersonate the Codexify Navigational Dock

### Quality test

* [ ] It feels like a local instrument strip
* [ ] It helps orientation instead of adding chrome
* [ ] It is lighter than the global dock in visual mass

---

## 5. Content Surface Check

After the Action Zone, real work must begin immediately.

### Required

* [ ] Main content starts right away
* [ ] The primary task is visible early
* [ ] The user reaches actual work without crossing stacked bureaucracy

### Check for violations

* [ ] No extra pane-title bands before content
* [ ] No duplicate summary cards that restate the same truth
* [ ] No support slab parked above the real work surface
* [ ] No content buried beneath administrative furniture

### Quality test

* [ ] The first screenful is mostly work, not chrome
* [ ] The primary task is obvious
* [ ] The eye lands on one clear focal area

---

## 6. Supporting Surface Check

Supporting surfaces must stay secondary.

Examples:

* profiles
* diagnostics
* inspector panels
* utilities
* comparison panels

### Required

* [ ] Supporting surfaces are subordinate to the main task
* [ ] They are reachable without dominating the page
* [ ] Their default presentation does not bury the primary content

### Acceptable patterns

* [ ] Local mode switch
* [ ] Drawer
* [ ] Collapsible region
* [ ] Explicit summon
* [ ] Lower-priority expandable section

### Check for violations

* [ ] No permanent dominant support rail without strong justification
* [ ] No full-width support slab above the primary content
* [ ] No secondary surface stealing the first impression

### Quality test

* [ ] Support tools feel available but quiet
* [ ] The module still works when support surfaces are hidden
* [ ] Prime vertical space belongs to the primary task

---

## 7. Identity Duplication Check

Identity should be established once, then not repeated gratuitously.

### Required

* [ ] Module identity appears once in the Module Header
* [ ] Active object identity is presented compactly when needed

### Check for violations

* [ ] No repeated title blocks
* [ ] No repeated active-state banners
* [ ] No separate cards saying the same thing in slightly different words
* [ ] No “Selection” card and “Active” card that duplicate truth

### Quality test

* [ ] The interface does not stutter the same identity over and over
* [ ] The user can tell what is active without reading three labels

---

## 8. Warning Placement Check

Warnings must live close to the act they affect.

### Required

* [ ] Input-related caveats live near the input path
* [ ] Contextual warnings appear where the user is already looking

### Check for violations

* [ ] No page-wide warning furniture for input-local caveats
* [ ] No oversized disclaimers in the Module Header
* [ ] No warning copy consuming more attention than the task itself

### Quality test

* [ ] The warning appears at the moment it matters
* [ ] The warning helps behavior instead of adding noise

---

## 9. Scroll Behavior Check

Prefer stable header/action anchoring and content-region scrolling.

### Required

* [ ] Header stays stable when possible
* [ ] Action Zone stays stable when possible
* [ ] Content region handles scroll when needed

### Check for violations

* [ ] No avoidable nested scroll traps
* [ ] No stacked pre-content surfaces creating needless vertical churn
* [ ] No confusing scroll prisons caused by administrative wrappers

### Quality test

* [ ] The user feels anchored
* [ ] Work, not chrome, owns the scroll

---

## 10. Token Compliance Check

All module surfaces must obey Codexify token law.

### Required

* [ ] Spacing is tokenized
* [ ] Radii are tokenized
* [ ] Colors are tokenized
* [ ] Surface treatment follows approved shell/card language
* [ ] Layout values follow token-driven rules

### Check for violations

* [ ] No ad hoc radii
* [ ] No arbitrary colors
* [ ] No one-off spacing magnitudes
* [ ] No custom shell grammar that breaks the host language

### Quality test

* [ ] The module feels native without copying blindly
* [ ] The module inherits Codexify law instead of improvising around it

---

## 11. Review Questions

Use these as the fast final gate:

* [ ] Does this surface read as a module rather than a settings dump?
* [ ] Does the user reach meaningful work quickly?
* [ ] Is the Action Zone obvious?
* [ ] Is Secondary Pill-Nav actually justified?
* [ ] Are support surfaces subordinate?
* [ ] Is identity repeated unnecessarily?
* [ ] Are warnings placed where the user actually acts?
* [ ] Does the first screenful feel calm rather than crowded?
* [ ] Does the module remain faithful to token and layout law?
* [ ] Would this surface teach the right habits to future first-party or plugin-native tools?

---

## 12. Failure Conditions

A module fails this checklist if any of the following are true:

* [ ] The first screenful is mostly chrome
* [ ] Header copy is verbose
* [ ] Action Zone is unclear or absent
* [ ] Local nav behaves like a second app navbar
* [ ] Support surfaces dominate by default
* [ ] Identity is repeated across multiple structural bands
* [ ] Warnings are far from the act they govern
* [ ] The module invents its own shell grammar
* [ ] The page feels denser after adding “helpful” structure

If multiple boxes above are true, the surface should be treated as structurally off-course rather than cosmetically unfinished.

---

## Canonical Summary

Use this checklist to confirm that a module-class surface still follows the intended Codexify grammar:

```text
Module Header
Action Zone
Secondary Pill-Nav (when justified)
Content Surface
```

The checklist is simple on purpose.

It exists to catch drift early, before the module turns into a dense little republic of banners, panes, and regret.
