# Module Header + Secondary Pill-Nav Canon v1

> Classification: design canon
> Status: binding for first-party module-class surfaces
> Audience: first-party contributors, design-system maintainers, and UI-generating agents
> Scope: module identity, action-zone structure, local navigation, surface hierarchy, and presentation enforcement for module-class tools inside Codexify
> Interpretation rule: If this document conflicts with the Codexify UI token canon or structural layout canon, those canon documents win

## Purpose

This document defines the binding structural contract for **module-class interfaces** inside Codexify.

Its purpose is to prevent drift in how tool-like surfaces are introduced, composed, and extended.

Without this contract, modules accumulate:

* oversized headers
* explanatory banner creep
* duplicated identity strips
* pane labels that describe implementation instead of behavior
* secondary controls that dominate the primary work surface

This canon exists to stop that decay before it becomes the house style.

---

## Core Law

Every module-class surface must follow this order:

```text
Module Header
Action Zone
Content Surface
```

Optional local navigation may appear through **Secondary Pill-Nav** when the module genuinely requires internal section or mode switching.

Anything that places additional structural bands between those layers must justify itself against this canon.

Default assumption: it does **not** justify itself.

---

## Canonical Terms

### Codexify Navigational Dock

The global application navigation surface.

This is product-level navigation.
It is not module navigation.

### Module Header

The compact identity band for a module-class surface.

It establishes:

* what this tool is
* what broad purpose it serves
* minimal current state or actions

It does **not** exist to narrate implementation constraints at length.

### Action Zone

The immediate control strip below the Module Header.

It establishes:

* what the user can do next
* which local mode or section is active
* which high-value actions are immediately available

### Secondary Pill-Nav

A module-scoped pill navigation surface used for local sections, modes, or views within a single module.

It is visually related to the Codexify Navigational Dock, but it is:

* lighter
* local in scope
* subordinate in visual authority

### Content Surface

The primary working region of the module.

This is where real work begins.

---

## Module Header Contract

Every module-class surface must begin with a Module Header.

### Required contents

* module title
* short descriptor

### Optional contents

* compact state chip
* compact right-side actions
* one minimal status indicator

### Prohibited contents

* long explanatory paragraphs
* setup essays
* diagnostics dumps
* pane labels
* repeated internal mode labels
* implementation-language controls such as “Show Utility Pane”

### Rules

* The descriptor must be one line when possible.
* The Module Header must remain vertically compact.
* The Module Header must not become a hero section.
* The Module Header must not repeat information better expressed in contextual helper text, tooltips, or content-level microcopy.

### Design intent

The Module Header is a nameplate, not a lecture.

---

## Action Zone Contract

The Action Zone must sit immediately beneath the Module Header.

### Allowed contents

* Secondary Pill-Nav
* local mode switches
* save/reset/import/export actions
* context-specific toggles
* compact stateful actions

### Prohibited contents

* long guidance paragraphs
* duplicate title/identity blocks
* full diagnostics payloads
* secondary pane headers
* passive filler sections

### Rules

* The Action Zone must be compact.
* The Action Zone must remain operational.
* The Action Zone must not turn into a second header.
* The Action Zone must reduce distance between user intent and control use.

### Design intent

The Action Zone is where the hand lands.

---

## Secondary Pill-Nav Contract

Secondary Pill-Nav is optional.

It should appear only when a module has enough internal structure to require local movement.

### Valid use cases

* section switching
* local mode switching
* scoped views inside one module
* editor subsections
* tightly related internal surfaces

### Invalid use cases

* app-wide route navigation
* branding
* passive status display
* dumping unrelated actions into a pill group
* compensating for weak information architecture

### Required characteristics

* visually related to the Codexify Navigational Dock
* lower visual mass than the global dock
* clearly local in scope
* concise labels
* obvious selected state
* token-governed styling only

### Prohibited characteristics

* acting like a second app navbar
* mixing unrelated actions and navigation in one pill row
* carrying verbose labels
* turning into a generic control shelf

### Design intent

Secondary Pill-Nav is an instrument strip, not a parade float.

---

## Content Surface Contract

After the Module Header and Action Zone, the content surface must begin immediately.

### Rules

* real content must start without crossing additional structural ceremony
* unnecessary pane labels are forbidden
* repeated identity strips are forbidden
* repeated explanation bands are forbidden
* content-region scrolling is preferred over stacked pre-content chrome
* only the content surface should scroll unless a different behavior is explicitly justified

### Design intent

Users should reach work quickly.

---

## Hierarchy Rules

### Rule 1: Identity appears once

The module identity should be established once in the Module Header.

Do not restate it in:

* utility headers
* repeated summary panels
* duplicate section banners
* redundant active-state blocks

### Rule 2: Secondary surfaces must remain secondary

Supporting surfaces such as:

* profiles
* diagnostics
* inspectors
* utility views
* comparison panels

must not consume prime vertical space by default.

They should prefer:

* local mode switching
* drawers
* collapsible regions
* explicit summons
* contextual reveals

### Rule 3: Explanation must move closer to the act

Warnings or caveats that matter during input should live near the input path.

Do not spend the primary header budget on interaction-local warnings.

### Rule 4: Actions must precede bureaucracy

A user should reach meaningful controls and content quickly.
Administrative framing must not dominate the first screenful.

### Rule 5: Local controls stay local

Global navigation, module navigation, and contextual actions must remain distinct.

---

## Surface Classification Rule

Not every surface is a module.

This canon applies only to **module-class tools**.

### Module-class surfaces may use

* Module Header
* Action Zone
* optional Secondary Pill-Nav
* Content Surface

### Non-module surfaces should use their own surface grammar

Examples:

* chat
* gallery grid
* viewer
* passive inspector
* workspace companion surface

Do not force every screen into module costume.

---

## Uniformity Rule

If a surface is a module, it must **look recognizably like a module**.

Uniformity does not mean cloning every header blindly.

Uniformity means:

* same structural order
* same slot logic
* same token discipline
* same hierarchy law
* same visual family of module identity and local control presentation

This rule exists so native tools and future plugins feel related without feeling copy-pasted.

---

## Persona Studio Application

Persona Studio is a flagship module-class surface and must follow this canon.

### Required structure

* Module Header
* Action Zone
* Content Surface

### Header guidance

Use:

* `Persona Studio`
* one short descriptor, such as:

  * `Build and tune runtime personas.`

Do not use:

* multi-line implementation disclaimers in the header
* oversized configuration-only explanations in the header

### Action Zone guidance

Place here:

* local sections via Secondary Pill-Nav
* Profiles / Diagnostics mode switch
* save/reset actions
* compact draft state

### Content guidance

Begin immediately with:

* preview harness
* compact profile summary
* active section editor
* truth summary / expandable matrix

### Boundary rule

Persona Studio remains configuration-first.
It must not silently become a persisted chat surface.

---

## Preview Composer Warning Rule

For ephemeral preview surfaces:

* input-related warnings belong in or near the composer
* no-memory reminders belong in the input path, not the Module Header
* stronger reminder language should appear when the user expresses memory intent
* warnings should support the task, not dominate the page chrome

---

## Prohibited Patterns

The following are explicitly disallowed for module-class surfaces unless a future canon amendment permits them:

* giant explanatory paragraphs under module titles
* implementation-language buttons like `Show Utility Pane`
* extra pane title bands before content begins
* repeated active-profile identity panels
* stacked status strips that delay arrival at content
* module-local nav that visually impersonates the global dock
* new ad hoc header systems outside the shared shell logic
* token violations in spacing, radii, color, or surface treatment

---

## Enforcement Standard

A module-class surface fails this canon when any of the following are true:

* the first screenful is mostly chrome rather than work
* identity is repeated in more than one structural band
* a secondary surface feels primary by default
* explanatory copy consumes more visual weight than action controls
* a user cannot immediately identify the module’s action zone
* local navigation is confused with app navigation
* the surface introduces new layout grammar outside token/canon rules

---

## Amendment Rule

Changes to this canon should be rare and explicit.

Any revision should include:

* rationale
* before/after screenshots
* examples from at least one first-party module
* statement of plugin-shell impact
* confirmation of token and layout canon compliance

This document is not a suggestion layer.
It is a containment field.

---

## Canonical Summary

A module-class surface inside Codexify must follow this grammar:

```text
Codexify Navigational Dock
Module Header
Action Zone
Secondary Pill-Nav (when needed)
Content Surface
```

The goal is not ornamental consistency.

The goal is structural clarity:

* modules look like modules
* local navigation looks local
* content begins quickly
* support surfaces stay subordinate
* future plugins inherit a native shell instead of inventing one
