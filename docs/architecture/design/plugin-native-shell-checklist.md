# Plugin-Native Shell Checklist

> Classification: implementation checklist
> Status: operational
> Scope: third-party plugins, user-built plugins, and first-party plugin-style surfaces that render inside Codexify with native presentation
> Parent documents:
>
> * Native Presentation SDK Contract v1
> * Module Header + Secondary Pill-Nav Canon v1
>   Use this checklist during design, implementation, review, and cleanup of any plugin-native surface.

## Purpose

This checklist turns the Native Presentation SDK contract into a practical inspection pass.

Use it when:

* building a third-party plugin surface
* designing a user-authored plugin to feel native
* reviewing whether a plugin is drifting into custom-shell chaos
* validating that a plugin uses the host grammar instead of improvising a parallel UI religion

This checklist is not a substitute for the parent contract.
It is the field inspection pass.

---

## 1. Surface Type Check

Before anything else, decide what kind of plugin surface this actually is.

### Confirm one of the following

* [ ] Module
* [ ] Viewer
* [ ] Companion Surface
* [ ] Embedded Utility

### Stop if this is unclear

* [ ] The plugin is mixing multiple surface types without a defined shell
* [ ] The plugin is using a module shell just because it looks prestigious
* [ ] The plugin is inventing a new surface class without approval

### Rule

Do not force every plugin into module form.

A plugin should use the lightest shell that truthfully matches its job.

---

## 2. Shell Ownership Check

A plugin-native surface should inherit the Codexify shell, not replace it.

### Required

* [ ] The plugin accepts the host shell structure
* [ ] The plugin does not create a parallel top-level shell
* [ ] The plugin does not fake app-wide navigation

### Check for violations

* [ ] No custom plugin-owned app header
* [ ] No duplicate global navigation
* [ ] No custom shell frame that competes with Codexify chrome
* [ ] No plugin-level branding strip that behaves like product navigation

### Quality test

* [ ] The plugin feels hosted, not bolted on
* [ ] A user can tell they are still inside Codexify

---

## 3. Module Header Check, if Module Surface

If the plugin is a **module-class** surface, it must use the Module Header contract.

### Required

* [ ] Title is present
* [ ] Descriptor is short
* [ ] Header is compact

### Check for violations

* [ ] No long explanatory text under the title
* [ ] No giant setup paragraph
* [ ] No pane labels inside the header
* [ ] No repeated identity strips

### Quality test

* [ ] The header identifies the tool quickly
* [ ] The header does not waste vertical space
* [ ] The header feels native to Codexify’s module family

---

## 4. Action Zone Check, if Module Surface

If the plugin is a module, the Action Zone must appear immediately beneath the header.

### Required

* [ ] Primary local actions are visible quickly
* [ ] Actions are relevant to the current tool state
* [ ] The user can tell what to do next

### Check for violations

* [ ] No second fake header
* [ ] No long instructional copy in the Action Zone
* [ ] No stacked banner furniture before real work begins

### Quality test

* [ ] The Action Zone feels operational
* [ ] The plugin gets to work quickly

---

## 5. Secondary Pill-Nav Check, if Used

Secondary Pill-Nav is optional.
Use it only when local sections or modes genuinely exist.

### Use only if true

* [ ] The plugin has meaningful internal sections or modes
* [ ] Those sections are local to the plugin
* [ ] A pill-nav improves orientation over simpler controls

### Check for violations

* [ ] Not being used for app navigation
* [ ] Not overloaded with unrelated actions
* [ ] Labels are concise
* [ ] Selected state is obvious
* [ ] It does not visually impersonate the Codexify Navigational Dock

### Quality test

* [ ] It feels local and lighter than the global dock
* [ ] It reads as a host-approved instrument strip

---

## 6. Content Surface Check

After the header and action zone, actual plugin work must begin immediately.

### Required

* [ ] The primary task starts right away
* [ ] The plugin’s main content is visible early
* [ ] The user does not wade through stacked chrome before reaching work

### Check for violations

* [ ] No extra pane-title bands before content
* [ ] No repeated summaries that restate the same truth
* [ ] No support slab parked above the primary task

### Quality test

* [ ] The first screenful is mostly work
* [ ] The plugin has one obvious focal area

---

## 7. Native Slot Usage Check

A plugin should use approved host slots rather than inventing new shell grammar.

### Required slots, when applicable

* [ ] `ModuleHeader`
* [ ] `ActionZone`
* [ ] `ContentSurface`

### Optional slots, when justified

* [ ] `StatusChip`
* [ ] `SecondaryPillNav`
* [ ] `Inspector`
* [ ] `FooterActions`
* [ ] `EmptyState`
* [ ] `LoadingState`
* [ ] `ErrorState`

### Check for violations

* [ ] No replacement shell outside approved slots
* [ ] No slot bypass through ad hoc wrappers
* [ ] No plugin-defined geometry system that fights the shell

### Quality test

* [ ] The plugin fits the host grammar with minimal friction
* [ ] Future theme or shell changes would not break the plugin’s structure

---

## 8. Supporting Surface Check

Supporting surfaces must stay subordinate.

Examples:

* inspector panels
* diagnostics
* metadata drawers
* side utilities
* comparison panels

### Required

* [ ] Supporting surfaces remain secondary to the main plugin task
* [ ] They are available without dominating
* [ ] Their default presentation does not bury primary work

### Acceptable patterns

* [ ] local mode switch
* [ ] drawer
* [ ] collapsible region
* [ ] explicit summon
* [ ] lower-priority expandable section

### Check for violations

* [ ] No permanent support slab above the main work surface
* [ ] No dominant support rail without strong justification
* [ ] No support panel stealing the plugin’s first impression

### Quality test

* [ ] Support tools feel available but quiet
* [ ] The plugin still works when they are hidden

---

## 9. Token Compliance Check

All plugin-native surfaces must obey Codexify token law.

### Required

* [ ] Spacing is tokenized
* [ ] Radii are tokenized
* [ ] Colors are tokenized
* [ ] Layout values are token-driven
* [ ] Surface treatment follows approved host language

### Check for violations

* [ ] No ad hoc radii
* [ ] No arbitrary colors
* [ ] No custom shadow or blur regime fighting host surfaces
* [ ] No plugin-owned spacing scale
* [ ] No custom glass grammar outside approved rules

### Quality test

* [ ] The plugin feels native without being visually cloned
* [ ] The plugin inherits host law instead of improvising around it

---

## 10. State Surface Check

Plugins should use native state treatments for common conditions.

### Required, when applicable

* [ ] Empty state is calm and actionable
* [ ] Loading state preserves structure
* [ ] Error state is explicit without collapsing the whole shell into panic furniture
* [ ] Read-only state remains legible

### Check for violations

* [ ] No plugin-specific chaos styling for basic states
* [ ] No layout jumping on load
* [ ] No giant warning slab for recoverable state

### Quality test

* [ ] State changes feel like Codexify, not like a foreign app embedded in a frame

---

## 11. Warning Placement Check

Warnings should appear where they matter.

### Required

* [ ] Input-related warnings appear near the input path
* [ ] Contextual warnings appear near the relevant act
* [ ] The header is not used as a dumping ground for caveats

### Check for violations

* [ ] No giant warning paragraph in the header
* [ ] No page-wide banner for input-local caveats
* [ ] No warning copy consuming more visual energy than the task

### Quality test

* [ ] The warning shows up at the moment of need
* [ ] It helps behavior instead of adding background noise

---

## 12. Scroll Behavior Check

Prefer stable shell anchors and content-region scroll.

### Required

* [ ] Header stays stable when possible
* [ ] Action Zone stays stable when possible
* [ ] Content region handles scroll when needed

### Check for violations

* [ ] No nested scroll trap created by decorative wrappers
* [ ] No stacked pre-content slabs creating needless vertical churn
* [ ] No scroll prison that makes the plugin feel cramped inside the host

### Quality test

* [ ] The plugin feels anchored and breathable
* [ ] Work owns the scroll, not chrome

---

## 13. Native Feel Check

Ask the final question plainly:

### Does this plugin feel like

* [ ] a native Codexify surface

or like

* [ ] a mini-app awkwardly camping inside Codexify

### Signs it still feels foreign

* [ ] It invents its own top-band grammar
* [ ] It overbrands itself
* [ ] It uses host-incompatible spacing and weight
* [ ] It behaves like a separate product
* [ ] It confuses app navigation and local navigation

### Signs it feels native

* [ ] It fits the shell cleanly
* [ ] It uses the right surface class
* [ ] It reaches work quickly
* [ ] It respects token law
* [ ] It keeps support surfaces subordinate
* [ ] It teaches the same interaction grammar as first-party tools

---

## 14. Review Questions

Use these as the fast final gate:

* [ ] Is the plugin using the right surface class?
* [ ] Is it inheriting the host shell rather than replacing it?
* [ ] If it is a module, does it obey Module Header -> Action Zone -> Content Surface?
* [ ] Is Secondary Pill-Nav actually justified?
* [ ] Are supporting surfaces subordinate?
* [ ] Is the first screenful mostly work rather than chrome?
* [ ] Are warnings placed where the user acts?
* [ ] Does the plugin stay token-safe?
* [ ] Would this plugin survive a future host theming or shell update without drama?
* [ ] Would a user describe it as “part of Codexify” rather than “something embedded inside Codexify”?

---

## 15. Failure Conditions

A plugin-native surface fails this checklist if any of the following are true:

* [ ] It behaves like a separate app inside Codexify
* [ ] It recreates app-level shell structure locally
* [ ] It invents unapproved shell grammar
* [ ] It uses non-token styling
* [ ] Its support surfaces dominate by default
* [ ] It buries work under chrome
* [ ] It confuses global and local navigation
* [ ] It cannot be clearly classified as module, viewer, companion, or utility
* [ ] It feels native only because it copied visual shapes instead of using host rules correctly

If multiple boxes above are true, the plugin is structurally off-course rather than merely unfinished.

---

## Canonical Summary

Use this checklist to confirm that a plugin-native surface fits Codexify without inventing a rival shell.

For module-class plugins, the target grammar remains:

```text
Module Header
Action Zone
Secondary Pill-Nav (when justified)
Content Surface
```

The point is not sameness.

The point is host coherence:

* native enough to belong
* flexible enough to differentiate
* bounded enough not to damage the shell
