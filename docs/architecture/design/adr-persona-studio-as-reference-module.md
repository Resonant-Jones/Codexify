# ADR: Persona Studio as the Reference Module for Codexify

> Classification: design ADR
> Status: proposed
> Scope: rationale for treating Persona Studio as a flagship module-class surface rather than a conventional settings page
> Related documents:
>
> * Module Header + Secondary Pill-Nav Canon v1
> * Native Presentation SDK Contract v1
> * Persona Studio Design Contract v1

## Context

Codexify is converging on a clearer distinction between:

* global application navigation
* module identity
* module-local controls
* local section navigation
* primary work surfaces
* supporting or diagnostic surfaces

Persona Studio exposed the cost of not making that distinction explicit.

As originally structured, Persona Studio tended to drift toward a dense configuration console:

* oversized explanatory header copy
* stacked status bands
* repeated profile identity blocks
* separate support surfaces that consumed prime space
* diagnostics and utility furniture competing with the actual build loop

This produced a surface that was technically functional but visually heavy and cognitively noisy.

At the same time, Persona Studio is one of the best places in Codexify to define what a **module-class tool** should feel like:

* it has a clear identity
* it has local sections
* it has immediate actions
* it has a meaningful content workflow
* it has supporting surfaces that must remain available but subordinate
* it is likely to inform future plugin-native tools

That combination makes Persona Studio a better reference specimen for module grammar than a generic settings page.

---

## Decision

Codexify will treat **Persona Studio as the reference module-class surface** for the product’s module presentation grammar.

Persona Studio will no longer be treated primarily as:

* a settings page
* a configuration dump
* a diagnostics-heavy utility console

Instead, Persona Studio will be treated as a **persona forge** organized around the loop:

```text
Edit -> Observe -> Amend
```

Its presentation grammar will be:

```text
Module Header
Action Zone
Content Surface
```

With:

* **Secondary Pill-Nav** for local sections
* **Profiles / Diagnostics** as subordinate local modes
* **Preview Harness** as an early and central content feature
* **truth and diagnostics** kept accessible but visually secondary

---

## Why this decision was made

### 1. Persona Studio has stronger module identity than generic settings

Persona Studio is not a miscellaneous preference panel.

It has:

* a distinct job
* a bounded internal workflow
* its own section structure
* its own feedback loop
* its own supporting surfaces

That makes it behave more like a tool than a settings tab.

### 2. The old configuration-console shape produced unnecessary density

The previous layout direction allowed:

* too much chrome before real work
* repeated identity statements
* overexposed diagnostics furniture
* support surfaces that visually behaved like primary surfaces

This undermined usability and made the page feel heavier than its actual function required.

### 3. Persona Studio is a strong proving ground for module law

Because Persona Studio includes:

* local navigation
* save/reset actions
* preview behavior
* profile management
* diagnostics
* derived truth surfaces

it forces Codexify to answer the structural questions that plugin-native modules will also face later.

That makes it an ideal place to establish:

* Module Header discipline
* Action Zone discipline
* Secondary Pill-Nav semantics
* support-surface subordination
* content-first hierarchy

### 4. Plugin-native presentation needs a first-party exemplar

A plugin ecosystem cannot depend only on abstract shell rules.

It needs at least one first-party module that demonstrates:

* how headers stay compact
* how local navigation stays local
* how action zones behave
* how support surfaces remain subordinate
* how work starts quickly

Persona Studio is the best current candidate for that role.

### 5. Preview-centric interaction is a better fit than settings-page bureaucracy

Persona Studio is about shaping behavior and observing the result.

That makes it closer to:

* a builder
* a forge
* a tuning instrument

than to a passive settings form.

The layout should reflect that reality.

---

## Consequences

### Positive consequences

* Persona Studio becomes a clearer, more coherent flagship module
* Codexify gains a first-party reference implementation for module grammar
* future plugin-native tools can inherit a stronger presentation model
* module identity, local controls, and content hierarchy become easier to standardize
* support surfaces are less likely to dominate prime working space

### Negative or constraining consequences

* Persona Studio redesign work must now satisfy module-canon requirements, not only local convenience
* future layout changes to Persona Studio may have broader design-system implications
* contributors lose some freedom to improvise one-off layout structures inside Persona Studio
* if Persona Studio drifts, it risks teaching the wrong lessons to future plugin/module work

### Neutral but important consequence

Persona Studio remains configuration-first.

Using it as the reference module does **not** change its product boundary into a real persistent conversation surface.

---

## Rejected alternatives

### 1. Treat Persona Studio as a conventional settings page

Rejected because this encourages:

* dense forms
* passive configuration posture
* heavier explanatory framing
* weaker module identity

### 2. Treat Persona Studio as a diagnostics-first observability panel

Rejected because diagnostics are supporting surfaces, not the primary user task.

### 3. Wait for a future plugin tool to define module grammar

Rejected because Codexify needs a first-party exemplar now, not after plugin drift has already begun.

### 4. Use a generic abstract module shell without a flagship example

Rejected because abstract rules alone are too easy to misread or underapply.

---

## Implementation guidance

This ADR implies the following for Persona Studio:

* header remains compact
* action zone appears immediately beneath header
* Secondary Pill-Nav governs internal sections
* Profiles / Diagnostics remain subordinate local modes
* preview appears early in the content surface
* truth remains inspectable without dominating first impression
* input-local warnings belong near the preview composer, not in global page chrome

This ADR does not itself define the full detailed layout contract.
That remains the job of the Persona Studio Design Contract.

---

## Status rationale

This ADR is valuable because it records the design decision at the level of principle:

**Persona Studio is not merely another settings page.**
It is the reference module for Codexify’s tool-class presentation grammar.

That decision affects:

* first-party UI work
* design canon
* plugin-native shell design
* future module consistency

Without this rationale, later contributors may incorrectly “simplify” Persona Studio back into dense settings-page habits.

---

## Decision summary

Codexify adopts Persona Studio as the flagship reference module for module-class surface design.

This means Persona Studio should model:

* compact module identity
* immediate operational controls
* local navigation through Secondary Pill-Nav
* fast arrival at work
* subordinate support surfaces
* clear preview-centered iteration

The point is not to make Persona Studio special for its own sake.

The point is to make it **instructive**.
