# Native Presentation SDK Contract v1

> Classification: UI/design canon
> Audience: first-party contributors, plugin authors, and SDK implementers
> Scope: native presentation rules for tool-class plugins and modules inside Codexify
> Not runtime truth: This document does not define backend execution, permissions, storage, health surfaces, or deployment behavior
> Interpretation rule: If this document conflicts with the Codexify UI token canon or structural layout canon, those canon documents win

## Purpose

Define the **Native Presentation SDK** contract that allows third-party plugins and user-built tools to render inside Codexify with a native, coherent, token-safe interface.

This contract exists so plugin authors do **not** need to reverse-engineer the product’s visual language.

The Native Presentation SDK should make it easy to build plugin surfaces that feel:

* structurally native
* visually consistent
* behaviorally predictable
* easy for users to learn
* safe for future theming and shell evolution

The goal is not to force every plugin to look identical.
The goal is to ensure every plugin speaks the same **presentation grammar**.

---

## Core Thesis

Plugins should not invent their own shell.

Codexify should provide a canonical presentation frame for any tool-class surface:

```text
Module Header
Action Zone
Content Surface
```

Optional local navigation may appear through **Secondary Pill-Nav** when needed.

This creates three benefits:

1. **Users** learn one interaction grammar.
2. **Plugin authors** gain a stable native shell.
3. **Codexify** avoids visual drift and interface fragmentation.

---

## Product Position

The Native Presentation SDK is part of the broader plugin SDK, but it serves a different purpose.

### Plugin Runtime SDK

Defines:

* registration
* lifecycle
* commands
* permissions
* data exchange
* storage and sandbox rules
* event hooks

### Native Presentation SDK

Defines:

* module shell
* module header
* action zone
* secondary local navigation
* content surface behavior
* token-safe layout and styling
* native empty/loading/error presentation

Both layers matter.

A plugin system without a native presentation contract becomes a patchwork of improvised interfaces.

---

## Design Goal

Third-party and user-built plugins should be able to feel:

* **native enough to belong**
* **flexible enough to differentiate**
* **bounded enough not to damage the shell**

Codexify should feel like an ecosystem, not a flea market.

---

## Canonical Terms

### 1. Codexify Navigational Dock

The global app-level route surface.

This is the top-level product navigation and is not owned by plugins.

### 2. Module Header

The native identity band for a tool-class module.

Used for:

* title
* short descriptor
* small status cues
* compact right-side actions

### 3. Action Zone

The immediate operational strip under the Module Header.

Used for:

* primary actions
* mode switches
* local save/reset/import/export
* compact toggles
* section switching

### 4. Secondary Pill-Nav

A module-scoped pill navigation surface used for local sections, modes, or views within a plugin or module.

It is visually related to the Codexify Navigational Dock, but serves **local navigation only**.

### 5. Content Surface

The main work area for the plugin.

This is where actual work begins and where scrolling should occur when necessary.

---

## Native Module Contract

Any plugin that presents itself as a **tool-class module** should use the following shell:

## 1. Module Header

### Required

* plugin/module title
* short one-line descriptor

### Optional

* compact status chip
* tiny state label
* help affordance
* compact header actions

### Rules

* keep the descriptor short
* do not use the header as a documentation block
* do not place warnings, diagnostics, or setup essays in the primary header region
* do not create a second custom title band above or below the Module Header

### Design intent

The Module Header is a nameplate, not a speech.

---

## 2. Action Zone

Appears immediately below the Module Header.

### Allowed contents

* Secondary Pill-Nav
* local mode toggles
* context-sensitive actions
* save/reset/import/export controls
* compact status-aware actions

### Rules

* content should begin immediately after this zone
* the Action Zone must remain compact
* the Action Zone must not become a second full header
* actions placed here must be immediately relevant to the module

### Design intent

The Action Zone is where intent becomes motion.

---

## 3. Content Surface

The working region of the plugin.

### Rules

* actual interaction begins here
* avoid unnecessary labels like “Main Content” or “Utility Pane”
* avoid repeating module identity already established above
* prefer content-region scrolling rather than extra stacked header bands
* do not bury the main task beneath administrative chrome

### Design intent

Users should reach the working surface quickly.

---

## Secondary Pill-Nav Contract

Secondary Pill-Nav is optional.

Use it only when the plugin has enough internal structure to justify local navigation.

### Appropriate use cases

* editor sections
* local content modes
* view scopes
* multi-step but non-wizard tool surfaces
* tabbed working regions within a single module

### Inappropriate use cases

* app-level navigation
* branding
* passive status display
* dumping unrelated actions into a tab strip
* replacing good information architecture with more pills

### Visual character

Secondary Pill-Nav should feel:

* related to Codexify’s dock language
* lighter than the global dock
* tighter in spacing
* lower in visual mass
* clearly local in scope

### Behavioral rules

* selected state must be obvious
* labels must stay concise
* do not mix unrelated semantics inside one pill group
* do not overload it with more options than the module can support clearly

### Design intent

Secondary Pill-Nav is an instrument strip, not a second navbar.

---

## Slot Model for Plugin Authors

The Native Presentation SDK should expose canonical shell slots rather than forcing each plugin to assemble layout manually.

## Required slots

* `ModuleHeader`
* `ActionZone`
* `ContentSurface`

## Optional slots

* `StatusChip`
* `SecondaryPillNav`
* `Inspector`
* `FooterActions`
* `EmptyState`
* `LoadingState`
* `ErrorState`

## Rules

* plugins may omit optional slots
* plugins must not invent replacement shells outside this contract unless Codexify explicitly supports a different surface class
* if a plugin is not a module-class tool, it should use a different sanctioned surface type instead of faking one

---

## Surface Classes

Not every plugin should be forced into the same interface shape.

The SDK should distinguish between several surface classes.

### 1. Module

For structured tools and builders.

Uses:

* Module Header
* Action Zone
* optional Secondary Pill-Nav
* Content Surface

### 2. Viewer

For passive or primarily read-only surfaces.

Examples:

* previewer
* document inspector
* image detail surface

### 3. Companion Surface

For lightweight assistant or sidecar tools.

Examples:

* inspector
* scratchpad
* small contextual helper

### 4. Embedded Utility

For small inline helpers that do not need a full module shell.

The Native Presentation SDK should support these classes explicitly so plugin authors choose the right shell instead of stretching one pattern to fit everything.

---

## Token Compliance Rules

All plugin-native presentation must obey the existing Codexify token law.

### Required

* tokenized spacing
* tokenized radii
* tokenized colors
* tokenized card and glass geometry
* token-governed layout widths and gaps

### Forbidden

* custom local radius systems
* ad hoc header geometry
* arbitrary color literals
* plugin-owned shadow/blur systems that conflict with shell rules
* fixed layout hacks that ignore token-driven responsiveness

### Design intent

A plugin should be able to express its identity without breaking the host language.

---

## Shell Behavior Rules

### Rule 1: Header first, action second, work third

Plugins must not introduce extra prefaces above the work surface.

### Rule 2: Content should start immediately

After the Module Header and Action Zone, the user should reach real content without crossing a swamp of labels and banners.

### Rule 3: Secondary surfaces should not dominate

Diagnostics, profile lists, inspectors, and supporting utilities should be:

* collapsible
* switchable
* drawer-based
* or integrated as local modes

They should not permanently steal the primary lane unless the module truly depends on them.

### Rule 4: Explain less, orient better

Long caveat text should move to:

* tooltips
* helper text
* popovers
* contextual composer hints
* empty states

Not the main module header.

### Rule 5: Input warnings belong near input

If a warning matters at the moment of typing, placing it near the composer is preferable to burying it in header chrome.

---

## Native States Contract

Plugins should inherit native treatments for common UI states.

### Empty state

Should:

* explain the absence of content
* suggest the next action
* feel calm, not broken

### Loading state

Should:

* remain structurally stable
* avoid layout jumping
* preserve shell identity

### Error state

Should:

* be explicit
* be compact
* avoid collapsing the whole module into panic furniture

### Read-only state

Should:

* remain legible
* preserve structure
* clearly distinguish view from edit

These states should be provided as part of the Native Presentation SDK, not reinvented per plugin.

---

## Persona Studio as the Flagship Example

Persona Studio should act as a reference implementation for the Native Presentation SDK.

### Module Header

* **Persona Studio**
* *Build and tune runtime personas.*

### Action Zone

* Secondary Pill-Nav for local sections
* local mode switch for Profiles / Diagnostics
* save/reset actions
* compact draft state

### Content Surface

* preview harness first
* profile summary second
* active editor surface third
* truth summary / expandable matrix last

### Input-level warning behavior

For preview-only composers:

* memory warning belongs in or near the input path
* stronger reminder text should surface only when the user expresses memory intent
* warnings should not consume the prime header zone

Persona Studio is a good flagship because it clearly shows the difference between:

* module identity
* local controls
* preview interaction
* supporting diagnostics

---

## Plugin Author Experience Goals

The Native Presentation SDK should make authors feel:

* guided, not constrained
* accelerated, not fenced in
* native, not bolted on

A plugin author should be able to say:

> “I know where my title goes, where my local controls go, how section navigation works, and where the work starts.”

That is the test of a good host shell.

---

## Non-Goals

This contract is not:

* a backend plugin execution spec
* a permission/security policy
* a data contract
* a runtime diagnostics contract
* a chat interaction spec
* a guarantee that every plugin uses Secondary Pill-Nav

It is strictly a presentation contract.

---

## Adoption Guidance

Apply this contract when:

* creating a new first-party module
* exposing a plugin as a tool-class surface
* designing native plugin wrappers
* defining host-rendered plugin shells

Do not apply it blindly to:

* pure chat surfaces
* passive galleries
* simple inline widgets
* single-action utilities
* global product navigation

---

## Canonical Summary

The Native Presentation SDK defines how plugins become visibly native inside Codexify.

The canonical module grammar is:

```text
Module Header
Action Zone
Secondary Pill-Nav (when needed)
Content Surface
```

This allows Codexify to support a growing plugin ecosystem without losing structural coherence, token safety, or user orientation.
