# Surface Class Matrix

> Classification: design matrix
> Status: binding taxonomy for presentation-side surface selection
> Scope: classify sanctioned Codexify surface types and define when to use Module, Viewer, Companion Surface, or Embedded Utility
> Parent documents:
>
> * Module Header + Secondary Pill-Nav Canon v1
> * Native Presentation SDK Contract v1
> * Persona Studio Design Contract v1
>   Interpretation rule: If this document conflicts with the Codexify UI token canon or structural layout canon, those canon documents win.

## Purpose

This document defines the canonical **surface classes** used in Codexify presentation architecture.

Its job is simple:

Before building or redesigning a surface, contributors must answer:

* What kind of surface is this?
* What shell grammar does it deserve?
* What shell grammar does it explicitly **not** deserve?

Without this classification step, Codexify risks a predictable failure mode:

* viewers start pretending to be modules
* support panels start behaving like primary tools
* tiny utilities grow headers, tabs, and civic ceremony
* local complexity gets hidden under “just make it a module”

This matrix exists to stop that drift.

---

## Core Law

Not every surface is a module.

Codexify supports multiple sanctioned surface classes because different jobs require different structural grammar.

The approved surface classes in this matrix are:

* **Module**
* **Viewer**
* **Companion Surface**
* **Embedded Utility**

When a surface is misclassified, the resulting UI usually becomes:

* denser than necessary
* slower to understand
* heavier than its task demands
* harder to keep native over time

---

## Surface Classes at a Glance

| Surface Class     | Primary Job                                                   | Typical Weight | May Use Module Header?               | May Use Secondary Pill-Nav?                             | Typical Scroll Owner      | Examples                                                       |
| ----------------- | ------------------------------------------------------------- | -------------- | ------------------------------------ | ------------------------------------------------------- | ------------------------- | -------------------------------------------------------------- |
| Module            | Structured tool with identity, actions, and internal workflow | High           | Yes                                  | Yes, when justified                                     | Content region            | Persona Studio, future plugin builders, advanced tool surfaces |
| Viewer            | Read or inspect content with minimal tool chrome              | Medium         | Sometimes, but lighter than a module | Usually no                                              | Content region            | document preview, image detail, artifact inspector             |
| Companion Surface | Secondary support surface attached to a primary task          | Medium to low  | No full module header by default     | Sometimes, for internal tabs only                       | Companion content region  | Workspace, scratchpad, inspector drawer                        |
| Embedded Utility  | Small inline helper or focused action widget                  | Low            | No                                   | No, unless it has clearly graduated into a larger class | Local element region only | quick formatter, mini converter, compact picker                |

---

## 1. Module

## Definition

A **Module** is a structured tool surface with:

* a distinct identity
* a clear primary task
* meaningful local actions
* enough internal complexity to justify a header and action zone
* a working surface that users actively inhabit

## Use a Module when all are true

* the surface has a strong tool identity
* the user can spend real time there
* there are multiple meaningful local controls or sections
* the surface has a coherent workflow rather than a single passive display
* the surface benefits from stable hierarchy:

  * Module Header
  * Action Zone
  * Content Surface

## Module grammar

A Module may use:

* **Module Header**
* **Action Zone**
* **Secondary Pill-Nav**, when justified
* **Content Surface**

A Module must not:

* bloat the header with explanatory prose
* bury content beneath stacked bureaucracy
* let supporting surfaces dominate by default

## Signs something is truly a Module

* removing the header would damage orientation
* the user needs local sections or modes
* save/reset or equivalent actions are meaningful
* the surface is not merely showing content, but helping shape or operate something

## Examples

* Persona Studio
* future plugin-native builders
* advanced authoring or configuration tools
* tool-class workflow surfaces

---

## 2. Viewer

## Definition

A **Viewer** is a surface whose primary job is to let the user **see, inspect, or read** something.

A Viewer may have light controls, but the content itself is the star.

## Use a Viewer when most are true

* the main task is inspection, reading, or preview
* the surface does not need a full action zone
* internal sections are minimal or absent
* the user is not “living” in the tool so much as looking through it
* the content object is more important than the shell around it

## Viewer grammar

A Viewer may use:

* a light title row or context row
* compact viewer actions
* content-first layout
* optional contextual inspector affordances

A Viewer should usually avoid:

* full Module Header ceremony
* Secondary Pill-Nav
* large action zones
* support slabs above the content

## Signs something is really a Viewer

* the content is the focal point, not the controls
* the shell can stay light without hurting comprehension
* the user mostly needs view, scroll, inspect, or lightly interact

## Examples

* document preview
* image detail panel
* artifact detail view
* resolved-config reader
* focused log or trace viewer, if the task is primarily inspection

---

## 3. Companion Surface

## Definition

A **Companion Surface** is a secondary, support-oriented surface that exists beside or around a primary task.

It is useful, persistent when needed, but not the main event.

## Use a Companion Surface when most are true

* the surface supports another primary workflow
* it should remain available but subordinate
* it benefits from being summonable, collapsible, peekable, or docked
* it should not own the first impression of the page
* it contains context, scratch work, preview, shelf, or support utilities

## Companion Surface grammar

A Companion Surface may use:

* local tabbing
* drawer behavior
* collapsible panels
* peek/open/focused states
* compact local headers when needed

A Companion Surface should avoid:

* full module framing unless it has actually graduated into a primary tool
* pretending to be the page’s main content
* large introduction bands
* dominant prime vertical occupation

## Signs something is really a Companion Surface

* the page still makes sense when it is hidden
* it supports the main task rather than replacing it
* it feels like a side desk, not the whole room

## Examples

* Workspace
* scratchpad drawers
* inspector panels
* shelf surfaces
* contextual sidecars
* diagnostics drawers when diagnostics are not the main task

---

## 4. Embedded Utility

## Definition

An **Embedded Utility** is a small, focused helper embedded inside another surface.

It solves a narrow task and should not drag an entire shell behind it.

## Use an Embedded Utility when most are true

* the task is narrow and local
* the utility exists inside a larger flow
* the user does not need a dedicated header
* a widget-like presentation is enough
* the thing would become absurd if given full module ceremony

## Embedded Utility grammar

An Embedded Utility may use:

* compact controls
* inline labels
* popovers
* mini state handling
* simple local affordances

An Embedded Utility must avoid:

* Module Header
* Action Zone
* Secondary Pill-Nav
* large shell chrome
* pretending to be its own product surface

## Signs something is really an Embedded Utility

* it can be understood in place
* it supports one local job well
* promoting it to module form would add ceremony without clarity

## Examples

* quick formatters
* compact selector widgets
* inline preview toggles
* simple action palettes
* mini converters
* local insertion helpers

---

## Classification Decision Matrix

Use this matrix before selecting a shell.

| Question                                                   | If Yes                            | If No                                  |
| ---------------------------------------------------------- | --------------------------------- | -------------------------------------- |
| Does the surface have a distinct tool identity?            | likely Module or Viewer           | likely Companion or Embedded Utility   |
| Is the main task active operation rather than inspection?  | lean Module                       | lean Viewer or Companion               |
| Is the surface secondary to another primary task?          | lean Companion                    | lean Module or Viewer                  |
| Does it need a stable header + action hierarchy?           | lean Module                       | avoid Module                           |
| Does it need internal sections or local modes?             | maybe Module, sometimes Companion | Viewer or Embedded Utility more likely |
| Would full module chrome feel excessive?                   | avoid Module                      | Module may be justified                |
| Can the page function normally when the surface is hidden? | likely Companion                  | likely Module or Viewer                |
| Is the task narrow and local?                              | lean Embedded Utility             | not an Embedded Utility                |

---

## Promotion and Demotion Rules

Surface classes are not moral status levels.

A module is not “better” than a viewer.
A companion is not “less serious” than a module.

Choose the lightest class that truthfully fits the job.

## Promotion rule

A surface may be promoted to a heavier class only when repeated pressure proves it needs more structure.

Examples:

* Embedded Utility -> Companion Surface
* Companion Surface -> Module
* Viewer -> Module, if editing/action workflow becomes primary

## Demotion rule

A surface should be demoted to a lighter class when its shell is heavier than its task.

Examples:

* a Viewer with too much module chrome should be simplified
* a Companion Surface dominating the page should be reduced
* a tiny utility with tabs and header rituals should be cut back to utility form

## Warning

Do not promote a surface merely because:

* modules look polished
* tabs feel “powerful”
* contributors want more places to put controls
* the shell is compensating for weak information architecture

---

## Persona Studio Classification

Persona Studio is a **Module**.

Why:

* strong tool identity
* primary working surface
* meaningful local sections
* clear action zone
* preview-driven build loop
* supporting surfaces that must remain subordinate

Persona Studio should not be treated as:

* a settings page
* a Viewer
* a Companion Surface
* a giant diagnostics slab

---

## Workspace Classification

Workspace is a **Companion Surface**.

Why:

* it supports Dashboard, Guardian, and Documents
* it remains user-owned and persistent
* it should be available without dominating
* it is explicitly described as a side working surface rather than the primary page identity

Workspace should not be promoted into a Module unless its product role changes fundamentally.

---

## Diagnostics Classification Guidance

Diagnostics are not automatically their own surface class.

Their classification depends on role.

### Diagnostics may be

* **Companion Surface** when supporting another primary task
* **Viewer** when primarily inspecting truth surfaces
* **Module** only if diagnostics itself becomes a full standalone tool with its own workflow

Default assumption:
Diagnostics should remain subordinate unless the product explicitly says otherwise.

---

## Plugin Guidance

Third-party and user-built plugins must choose a surface class intentionally.

## Required rule

A plugin must declare its surface class before shell selection.

### Plugin consequences

* **Module plugin** -> may use Module Header, Action Zone, Secondary Pill-Nav
* **Viewer plugin** -> should use a lighter content-first shell
* **Companion plugin** -> should support docked, drawer, or support-oriented behavior
* **Embedded Utility plugin** -> should stay compact and inline

## Warning

Do not let every plugin claim module status by default.

That path leads directly to shell inflation and design drift.

---

## Anti-Patterns

The following are strong indicators of misclassification:

### Viewer disguised as Module

* huge header
* lots of empty chrome
* tabs that do almost nothing
* content pushed downward by ceremony

### Companion disguised as Module

* side surface trying to become the page
* support tool dominating first impression
* full module shell for something that should dock quietly

### Utility disguised as Companion

* tiny local action wrapped in a drawer or tab system
* more shell than function

### Utility disguised as Module

* miniature helper with title, tabs, state banners, and explanatory copy
* absurd chrome-to-value ratio

---

## Fast Classification Checklist

Before implementation, answer these:

* Is this surface primarily **operate**, **inspect**, **support**, or **assist locally**?
* Does it deserve a full header/action/content hierarchy?
* Would the interface improve if the shell were lighter?
* Can this surface be hidden without damaging the page’s primary task?
* Is the content the focal point, or is the tool behavior the focal point?
* Are we adding shell because the task needs it, or because the shell looks impressive?

If the last answer is “because the shell looks impressive,” stop.

---

## Canonical Summary

Codexify supports four sanctioned presentation-side surface classes:

* **Module**
* **Viewer**
* **Companion Surface**
* **Embedded Utility**

Use the lightest class that truthfully fits the task.

In general:

* **Module** = operate
* **Viewer** = inspect
* **Companion Surface** = support
* **Embedded Utility** = assist locally

The purpose of this matrix is not taxonomy for taxonomy’s sake.

It is to keep Codexify from turning every useful thing into a tiny republic of headers, tabs, and page chrome.
