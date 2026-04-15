# Persona Studio Design Contract v1

> Classification: design contract
> Status: binding for Persona Studio implementation and redesign work
> Audience: first-party contributors, design-system maintainers, and UI-generating agents
> Scope: Persona Studio structure, hierarchy, local preview behavior, diagnostics placement, and module-specific presentation rules
> Parent documents:
>
> * Module Header + Secondary Pill-Nav Canon v1
> * Native Presentation SDK Contract v1
>   Interpretation rule: If this document conflicts with the Codexify UI token canon or structural layout canon, those canon documents win. If it conflicts with the Persona Studio product boundary, the product boundary wins.

## Purpose

This document defines the canonical presentation and interaction contract for **Persona Studio**.

Persona Studio is a flagship module-class surface.
It should model the intended Codexify module grammar clearly enough that future first-party tools and plugin-native modules can inherit from its structure without inheriting its mistakes.

This contract exists to prevent Persona Studio from drifting into:

* a dense settings wall
* a three-pane admin console
* a diagnostics-heavy observability slab
* a fake chat surface with unclear persistence rules
* a pile of stacked status bands that delay arrival at actual work

Persona Studio must feel like a **persona forge**:

* build
* preview
* amend
* save

Not a settings cemetery.

---

## Product Boundary

Persona Studio is a **configuration-first** surface.

It may support local preview behavior, but it must not silently become:

* a real chat thread
* a memory-writing surface
* a history-bearing conversation space
* a source of identity contamination

### Hard rule

Persona Studio preview is ephemeral unless and until a separate product contract explicitly changes that rule.

Preview state must not be mistaken for runtime conversation state.

---

## Core Experience Thesis

Persona Studio exists to support this loop:

```text
Edit -> Observe -> Amend
```

The interface must optimize for that loop.

This means:

* editing controls must be reachable quickly
* preview must be visible early
* diagnostics must remain subordinate
* content must begin immediately after the action zone
* explanatory chrome must not dominate the page

---

## Canonical Structure

Persona Studio must follow this order:

```text
Module Header
Action Zone
Content Surface
```

No additional structural band may sit between these layers unless explicitly justified by this contract.

---

## 1. Module Header

### Required contents

* title: `Persona Studio`
* short descriptor

### Recommended descriptor

* `Build and tune runtime personas.`

### Optional contents

* compact unsaved/saved chip
* compact help affordance
* compact top-right actions when justified

### Prohibited contents

* long explanation about configuration-only behavior
* large disclaimers about memory or chat history
* pane labels
* repeated profile identity blocks
* implementation-language text like `Utility Pane`

### Design rule

The header must remain compact and module-like.

### Design intent

The header should identify the surface and get out of the way.

---

## 2. Action Zone

The Action Zone sits directly under the Module Header.

### Required contents

* Secondary Pill-Nav for Persona Studio sections
* local mode switch for supporting surfaces
* save/reset actions

### Secondary Pill-Nav section set

* Identity
* Model
* Voice
* Prompt
* Tools
* Retrieval
* Truth

### Supporting mode switch

Persona Studio should expose:

* Profiles
* Diagnostics

This switch belongs in the Action Zone, not as a large secondary pane.

### Optional compact state items

* Unsaved Draft
* Validation warning count
* Preview-only indicator when needed

### Prohibited contents

* separate utility-pane title rows
* stacked administrative status panels
* long instructional paragraphs
* extra profile identity cards above the content surface

### Design intent

The Action Zone should feel like the instrument strip of the module.

---

## 3. Content Surface

After the Action Zone, the content surface must begin immediately.

Persona Studio content should follow this priority order:

1. Preview Harness
2. Compact Active Profile Summary
3. Active Section Editor
4. Truth Summary
5. Expandable Full Truth Matrix

This order is intentional.

Preview must arrive before bureaucracy.

---

## 4. Preview Harness Contract

The Preview Harness is the emotional center of Persona Studio.

### Purpose

Allow the user to test the current draft profile while building it.

### Preview nature

The Preview Harness is:

* local-only
* ephemeral
* draft-aware
* non-persistent
* non-threaded

### It must not

* create real Guardian threads
* write to memory systems
* create durable conversation history
* masquerade as a normal chat surface

### Required behaviors

* local transcript area
* canned prompt chips
* freeform input
* send action
* clear preview action
* deterministic preview responses when runtime-backed behavior is not active
* visible indication that preview uses the current unsaved draft

### Priority rule

The Preview Harness must appear high enough in the content surface to be visible without excessive scroll on common desktop layouts.

### Design intent

Preview is not a side feature.
Preview is the center of the loop.

---

## 5. Composer Warning Rule

Warnings related to preview persistence or memory must live in the composer path.

### Required behavior

* default composer hint may indicate preview-only / no memory
* stronger boundary language should appear only when the user expresses memory intent

### Memory-intent examples

* remember this
* save this
* keep this
* do not forget
* store this for later

### Required assistant boundary response pattern

When memory intent is expressed, the preview assistant should respond with a clear boundary statement such as:

> I have no memory in this Persona Preview. If you want to keep this result, copy it somewhere safe before leaving.

### Prohibited placement

Do not place large no-memory warnings in:

* the Module Header
* the Action Zone
* page-wide banner furniture

### Design intent

Warnings should appear where the user is already looking: the input path.

---

## 6. Active Profile Summary

Persona Studio may show current draft/profile context, but it must do so compactly.

### Required fields

* profile name
* short description
* small status chips as needed

### Optional fields

* default badge
* validation state
* version or dirty state

### Prohibited behavior

* do not repeat profile identity in multiple stacked panels
* do not create separate “Active Profile” and “Selection” cards if they communicate the same truth
* do not re-state the same profile name in multiple structural bands

### Design intent

Identity appears once, then work continues.

---

## 7. Diagnostics Placement

Diagnostics are supporting surfaces, not the main event.

### Required rule

Diagnostics must remain subordinate to the build-and-preview loop.

### Allowed implementations

* Action Zone mode switch
* drawer
* collapsible panel
* expandable region inside the content surface
* explicit summon interaction

### Prohibited implementations

* permanent dominant side rail
* full-width slab above the content surface
* default-open bureaucracy that pushes preview below fold

### Diagnostic content may include

* save status
* validation results
* effective config preview
* debug stream
* config diff
* effective runtime snapshot

### Design intent

Diagnostics should be available when needed, quiet when not.

---

## 8. Truth Surface Contract

Persona Studio must preserve truthfulness of derived configuration without letting the Truth Matrix become a cliff face.

### Required hierarchy

* compact truth summary first
* full truth matrix second, behind expansion or lower in the content flow

### Compact summary may include

* runtime-applied count
* local-only count
* unsaved changes count
* warnings count

### Full matrix may include

* resolved config
* field precedence
* derived values
* validation or conflict indicators

### Prohibited behavior

* do not lead the content surface with full raw config dominance
* do not make truth harder to access
* do not bury truth so deeply that it stops being inspectable

### Design intent

Truth must be accessible, but it should not shout over the actual task.

---

## 9. Profiles Mode Contract

Profiles is a local module mode, not a permanent lane.

### Profiles mode responsibilities

* list profiles
* select profile
* create
* duplicate
* delete
* import/export
* mark default

### Rules

* profile selection must remain easy
* profile management should not consume the prime vertical lane by default
* profile-management UI should feel like a local module tool, not a separate product area

### Design intent

Profiles supports the forge.
It is not the forge.

---

## 10. Secondary Pill-Nav Behavior

Persona Studio’s Secondary Pill-Nav governs internal editor sections.

### Required rule

Section switching must feel local, fast, and obviously scoped to Persona Studio.

### Labels must remain concise

Use:

* Identity
* Model
* Voice
* Prompt
* Tools
* Retrieval
* Truth

Do not introduce verbose labels unless a future section genuinely requires it.

### Visual rule

It should visually relate to the Codexify Navigational Dock while remaining lighter and more local.

---

## 11. Scroll Rule

Persona Studio should minimize stacked pre-content chrome.

### Preferred behavior

* Module Header stays stable
* Action Zone stays stable
* content region scrolls

### Do not introduce

* avoidable extra scroll surfaces
* nested scroll prisons
* stacked administrative slabs before the actual working surface

### Design intent

The user should feel anchored, not buried.

---

## 12. Uniformity Rule

Persona Studio should model the Codexify **module archetype**.

That means it must demonstrate:

* compact module header
* immediate action zone
* local section navigation through Secondary Pill-Nav
* fast arrival at work content
* subordinate support surfaces
* token-safe presentation
* no ad hoc shell invention

Persona Studio is not just a feature.
It is a reference specimen.

---

## 13. Explicitly Forbidden Patterns

The following patterns are forbidden in Persona Studio unless a later canon update permits them:

* long descriptive paragraphs under the title
* `Show Utility Pane` / `Hide Utility Pane` wording
* full-width support slabs above real content
* repeated `Active Profile` cards that duplicate the same truth
* diagnostics that dominate the first screenful
* preview buried beneath administration
* page-level warning banners for input-local caveats
* custom non-token header geometry
* module-local controls visually confused with app-wide navigation

---

## 14. Success Criteria

Persona Studio satisfies this contract when:

* the page reads as a module, not a settings dump
* preview is visible early
* diagnostics feel available but subordinate
* the active profile identity is stated once
* the user reaches meaningful work quickly
* the interface supports edit -> observe -> amend without friction
* configuration-only boundaries remain intact without wasting header real estate

---

## Canonical Summary

Persona Studio must present itself as a **module-class persona forge**.

Its required grammar is:

```text
Persona Studio
short descriptor

Action Zone
- Secondary Pill-Nav
- Profiles / Diagnostics mode switch
- Save / Reset

Content Surface
- Preview Harness
- Compact Active Profile Summary
- Active Section Editor
- Truth Summary
- Expandable Truth Matrix
```

This contract exists to keep Persona Studio legible, native, and worthy of becoming the model for future plugin-native modules.
