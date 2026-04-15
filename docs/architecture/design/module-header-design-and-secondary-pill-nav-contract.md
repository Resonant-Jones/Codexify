# Module Header + Secondary Pill-Nav Contract v1

> Classification: UI/design canon
> Scope: Module identity, header structure, local navigation, immediate action layout, and plugin-native presentation rules
> Not runtime truth: This document does not define backend topology, worker behavior, health semantics, or deployment constraints
> Interpretation rule: If this document conflicts with the UI token and structural layout canon, the canon wins

## Purpose

Define the canonical presentation contract for **tool-class modules** inside Codexify.

This contract exists to ensure that native tools and third-party plugins share the same structural grammar:

* modules look like modules
* local navigation looks local
* actions appear where users expect them
* content begins immediately
* secondary controls do not dominate the work surface

The goal is not visual sameness for its own sake.
The goal is **structural consistency with clear role separation**.

---

## Core Thesis

Codexify needs a stable distinction between:

* **app navigation**
* **module identity**
* **module-local navigation**
* **module actions**
* **work content**

Without this distinction, surfaces become crowded, repetitive, and visually ambiguous.

The correct module pattern is:

```text
Module Header
Action Zone
Content Surface
```

Not:

```text
Large title block
Explanatory paragraph
Pane label
Secondary pane
Status strip
Content eventually
```

---

## Canonical Terms

### 1. Codexify Navigational Dock

The global, app-level navigation surface.

Used for:

* Guardian
* Dashboard
* Documents
* Gallery
* Persona Studio
* other top-level routes

This dock is product navigation. It is not module-local navigation.

### 2. Module Header

The top identity band for a tool-class module.

Used for:

* module title
* short descriptor
* small status indicators
* optional right-side actions

The Module Header defines what the tool **is**, not how every internal section works.

### 3. Action Zone

The immediate control strip under the Module Header.

Used for:

* primary local actions
* section switching
* mode changes
* save/reset affordances
* compact local status controls

The Action Zone defines what the user can **do next**.

### 4. Secondary Pill-Nav

A module-scoped pill navigation surface used for local sections, modes, or views within a module.

It is visually related to the Codexify Navigational Dock, but serves **local** movement rather than app-wide route changes.

Examples:

* Identity / Model / Voice / Prompt / Tools / Retrieval / Truth
* Profiles / Diagnostics
* Thread / Project
* Shelf / Scratchpad / Inspector

---

## Structural Contract

## 1. Module Header

Every tool-class module should begin with a Module Header.

### Required contents

* module title
* short one-line descriptor

### Optional contents

* one small state chip
* one small mode/status token
* compact right-side action group

### Rules

* the descriptor must stay short
* the header must not become a documentation block
* large explanatory copy is prohibited in the primary header region
* the header must not consume unnecessary vertical space
* the header must not contain secondary pane labels like “Utility Pane”

### Design intent

The Module Header should feel like the nameplate on an instrument, not a marketing hero section.

---

## 2. Action Zone

The Action Zone appears immediately under the Module Header.

### Allowed contents

* Secondary Pill-Nav
* mode selectors
* save/reset/import/export controls
* context-sensitive actions
* compact toggle groups

### Rules

* content should begin immediately after the Action Zone
* the Action Zone must remain compact
* the Action Zone must not become a second full header
* controls in this zone should be directly relevant to the current module state
* this zone should minimize eye travel between intent and action

### Design intent

The Action Zone is the user’s handhold.
It should feel operational, not ceremonial.

---

## 3. Secondary Pill-Nav

Secondary Pill-Nav is optional.
It should appear only when a module has enough local structure to justify it.

### Use cases

* section switching inside a module
* local view modes
* content scope changes
* editor subsection movement

### Secondary Pill-Nav is

* module-scoped
* optional
* embedded inside the Action Zone or tightly associated with it
* lighter than the Codexify Navigational Dock
* token-governed

### Secondary Pill-Nav is not

* app-wide route navigation
* a branding surface
* a place for explanatory copy
* a substitute for poor information architecture
* a dumping ground for unrelated buttons

### Rules

* only use it when local navigation is genuinely needed
* keep labels concise
* do not overload it with passive status items
* do not mix unrelated actions inside the same pill structure
* selected state must be visually obvious and token-consistent

### Design intent

The Secondary Pill-Nav should feel like an instrument strip, not a second navbar.

---

## 4. Content Surface

After the Module Header and Action Zone, the content surface should begin immediately.

### Rules

* no unnecessary pane titles before content
* no redundant explanatory banners before content
* no repeated identity labels that restate what the header already established
* scrolling should happen in the content region when possible
* header and action zones should ideally remain stable anchors

### Design intent

The user should reach the working surface quickly.

---

## Information Hierarchy Rules

### Rule 1: Identity appears once

The active module identity should be established clearly, then not repeated unnecessarily.

### Rule 2: Secondary surfaces must not dominate

If a surface is supportive rather than primary, it should be:

* collapsible
* switchable
* drawer-based
* or integrated as a local mode

It should not permanently occupy prime vertical space unless the module truly depends on it.

### Rule 3: Explain less, orient better

Do not spend the top of the module on long disclaimers.
Use short descriptors, tooltips, helper text, or contextual microcopy instead.

### Rule 4: Action precedes bureaucracy

Users should reach an actionable region quickly.

### Rule 5: Module-local controls stay local

Do not blur app navigation and module navigation.

---

## Uniformity Rules for Native Tools and Plugins

Codexify should expose a consistent module grammar for first-party and third-party tools.

### If a surface is a Module, it should use

* Module Header
* Action Zone
* optional Secondary Pill-Nav
* token-governed Content Surface

### If a surface is not a Module, it should follow its own surface class

Examples:

* chat
* gallery
* document viewer
* dashboard grid
* workspace drawer

This distinction is important.
Not every screen should look like a module.
But every module should look recognizably like a module.

---

## Native Presentation SDK Implication

This contract is part of the future **Native Presentation SDK**.

The plugin system should provide first-class structural primitives rather than forcing developers to invent their own shell.

### Required plugin-native slots

* `ModuleHeader`
* `ActionZone`
* `ContentSurface`

### Optional plugin-native slots

* `StatusChip`
* `SecondaryPillNav`
* `Inspector`
* `FooterActions`

### SDK rules

* token-only styling
* no ad hoc header invention outside the shell contract
* no arbitrary radii or spacing systems
* no independent layout grammar for module-class plugins
* module-local navigation must use approved Secondary Pill-Nav semantics when appropriate

### Design goal

Make it easy for third-party developers to feel native without reverse-engineering Codexify’s visual logic.

---

## Persona Studio Application

Persona Studio should follow this contract as a flagship module.

### Module Header

* **Persona Studio**
* short descriptor only, such as:

  * *Build and tune runtime personas.*

### Action Zone

* Secondary Pill-Nav for local sections

  * Identity
  * Model
  * Voice
  * Prompt
  * Tools
  * Retrieval
  * Truth
* local mode switch

  * Profiles
  * Diagnostics
* save/reset actions
* compact draft state

### Content Surface

* preview harness first
* profile summary second
* section editor third
* truth summary / expandable matrix last

### Boundary note

Persona Studio may support local preview behavior, but it remains configuration-first and must not become a real persisted chat surface.

---

## Notification Placement Rule for Preview Surfaces

When a module includes an ephemeral preview composer, critical input-related warnings should appear in the composer path itself.

For Persona Studio preview specifically:

* no-memory warning belongs in or near the input/composer region
* it should not dominate the global module header
* stronger reminder text should appear only when the user expresses memory intent

This keeps the warning attached to the act of input, where the user is already looking.

---

## Non-Goals

This contract is not:

* a backend spec
* a runtime contract
* a diagnostics data contract
* a chat message UX spec
* a plugin permission/security model
* a requirement that every screen use Secondary Pill-Nav

---

## Adoption Guidance

Apply this contract when:

* creating a new first-party tool surface
* redesigning an existing tool-like interface
* defining plugin-native shells
* deciding whether a control belongs in the header, action zone, or content

Do not apply this contract mechanically to:

* message streams
* passive viewers
* gallery-only surfaces
* simple one-action cards
* app-wide route navigation

---

## Canonical Summary

Codexify module-class tools should follow a stable presentation grammar:

```text
Codexify Navigational Dock
Module Header
Action Zone
Secondary Pill-Nav (when needed)
Content Surface
```

This creates a system where:

* app navigation remains distinct
* module identity is clear
* local controls feel local
* work begins quickly
* plugins can feel native without improvising their own shell
