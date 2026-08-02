# Codexify Design Architecture Index

> Classification: design index
> Status: entrypoint
> Scope: reading order, document roles, and interpretation rules for the design-canon layer inside `docs/architecture/design/`
> Not runtime truth: These documents define presentation law, module grammar, and plugin-native shell rules. They do not define backend topology, worker behavior, queue semantics, or release-readiness truth.

## Purpose

This directory is the **design-canon lane** for Codexify.

It exists to keep presentation architecture, module grammar, and plugin-native shell rules in one place so contributors can answer three questions quickly:

1. **What kind of surface am I building?**
2. **What presentation law applies to it?**
3. **Which document is authoritative for this decision?**

This directory is not a replacement for the runtime architecture KB.

Use it when the question is about:

* module structure
* local navigation grammar
* header/action/content hierarchy
* plugin-native presentation
* design-law enforcement for first-party tools

Do **not** use it as the source of truth for:

* backend execution
* queues
* storage invariants
* health semantics
* release-readiness claims

---

## Reading Order

Read these in order:

1. **Module Header + Secondary Pill-Nav Canon v1**
   Start here for the binding law governing module-class surfaces.

2. **Native Presentation SDK Contract v1**
   Read next for the plugin-facing shell contract and native presentation rules.

3. **Persona Studio Design Contract v1**
   Read after the broader canon to see the module grammar applied concretely to a flagship first-party surface.

4. **ADR: Persona Studio as the Reference Module for Codexify**
   Read last for the rationale behind using Persona Studio as the reference specimen for module-class design.

This sequence matters.

The canon defines the law.
The SDK contract defines the external shell model.
The Persona Studio contract defines one concrete implementation target.
The ADR records why this direction exists.

---

## Directory Role

`docs/architecture/design/` exists to hold the documents that sit **between**:

* the broad UI token/layout canon
* and
* the implementation details of individual surfaces

These docs answer questions like:

* What is a module?
* What belongs in a Module Header?
* When should local navigation become Secondary Pill-Nav?
* Where should diagnostics live?
* How do plugin-native tools feel native without cloning the whole app shell?
* Why is Persona Studio being treated as a reference module rather than a settings page?

---

## Interpretation Rules

### 1. Runtime truth wins on runtime questions

If a document in this directory conflicts with runtime truth, runtime truth wins.

Use:

* `docs/architecture/00-current-state.md`
* the broader architecture KB
* supported-path proofs
* runtime contracts

when the question is about actual backend or release reality.

### 2. UI token and structural canon win on lower-level presentation law

If a document in this directory conflicts with the Codexify token or structural layout canon, the lower-level canon wins.

This directory builds on those laws.
It does not override them.

### 3. Product-boundary documents win on product-behavior constraints

If a design contract conflicts with an explicit product-boundary rule, the product-boundary rule wins.

Example:

* Persona Studio may contain preview behavior
* but it remains configuration-first unless a product contract changes that rule

### 4. Directory docs should not compete for authority

Each document in this directory should have a clearly bounded role.

Avoid:

* two documents with the same title and different force
* multiple “source of truth” docs for the same design question
* old drafts left standing as if they are still active law

Superseded drafts should be removed, archived, or explicitly marked as non-authoritative.

---

## Current Document Map

### Module Header + Secondary Pill-Nav Canon v1

**Role:** binding first-party design law for module-class surfaces.

Use this when deciding:

* how modules are structured
* what belongs in the Module Header
* what belongs in the Action Zone
* when Secondary Pill-Nav is appropriate
* how supporting surfaces stay subordinate

### Native Presentation SDK Contract v1

**Role:** plugin-facing shell contract.

Use this when deciding:

* how third-party or user-built plugins render natively
* which shell slots are provided
* how plugin-native surfaces stay token-safe
* how modules differ from viewers, companions, and utilities

### Persona Studio Design Contract v1

**Role:** concrete module-level implementation contract for Persona Studio.

Use this when deciding:

* how Persona Studio should be arranged
* where preview belongs
* where diagnostics belong
* how truth surfaces should appear
* how the Persona Studio loop should prioritize edit -> observe -> amend

### ADR: Persona Studio as the Reference Module for Codexify

**Role:** rationale record.

Use this when deciding:

* why Persona Studio is the flagship module specimen
* why it should not regress into a settings page
* why module grammar needs a first-party exemplar

---

## How to Use This Directory

### If you are building a new first-party tool

Start with:

1. Module Header + Secondary Pill-Nav Canon v1
2. Then check whether the tool is truly a module-class surface
3. If yes, follow the module grammar before inventing local structure

### If you are building a plugin shell or plugin-native surface

Start with:

1. Native Presentation SDK Contract v1
2. Then use the module canon only if the plugin is actually a module-class surface

### If you are redesigning Persona Studio

Start with:

1. Persona Studio Design Contract v1
2. Then use the module canon as the parent law
3. Then read the ADR to understand the larger reason the constraints exist

### If you are working on runtime or operator surfaces

This directory is probably not your first stop.

Go back to:

* `docs/architecture/README.md`
* `docs/architecture/00-current-state.md`
* the validated runtime KB
* proof artifacts and contracts

---

## Non-Goals

This directory is not:

* a backlog
* a roadmap
* a runtime contract folder
* an implementation log
* a place for superseded draft clutter
* a replacement for the architecture KB root

---

## Maintenance Rules

When adding a new document here:

* give it a sharply bounded role
* state whether it is canon, contract, ADR, or index
* define what it does **not** govern
* link to its parent document when it derives authority from one
* avoid duplicating authority already established elsewhere

When replacing a document:

* remove or archive the older draft
* do not leave two competing documents active under the same conceptual title
* update this index so the reading order stays truthful

---

## Suggested Future Additions

This directory may later include:

* a module surface checklist
* a plugin-native shell checklist
* a design-law ADR index
* a diagnostics-surface design companion
* a surface-class matrix distinguishing modules, viewers, companions, and utilities

Only add these if they clarify authority rather than multiplying it.

---

## Canonical Summary

`docs/architecture/design/` is the design-law lane for Codexify.

Use it to understand:

* how modules are structured
* how local navigation should behave
* how plugin-native tools feel native
* how flagship surfaces like Persona Studio should model the system

Read in this order:

```text
Module Header + Secondary Pill-Nav Canon v1
Native Presentation SDK Contract v1
Persona Studio Design Contract v1
ADR: Persona Studio as the Reference Module for Codexify
```

This keeps the design layer legible, bounded, and resistant to drift.
