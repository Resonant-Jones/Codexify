# Design Lane Adoption Sequence

> Classification: adoption guide
> Status: operational
> Scope: reading order and execution sequence for using `docs/architecture/design/` during planning, implementation, review, and cleanup
> Not runtime truth: This document explains how to apply the design lane. It does not define backend behavior, supported-path reality, or release readiness.

## Purpose

This document defines the recommended sequence for adopting the design lane inside Codexify.

Its goal is to answer:

* where contributors should start
* which document to read next
* when a canon should be consulted
* when a checklist should be used
* when a surface-specific contract is required
* how to avoid multiplying new design documents unnecessarily

This is not another source of design law.

It is the **usage path** for the existing design-law set.

---

## Core Rule

Do not start implementation by improvising layout.

Start by classifying the surface, then selecting the right design document, then validating the shape before writing or reviewing code.

The design lane should be used in this order:

```text
Classify
Read parent law
Read child contract if one exists
Implement
Check
Update status/index docs if authority changed
```

---

## Adoption Sequence

## Step 1: Decide whether the work belongs in the design lane at all

Use the design lane when the question is about:

* module structure
* local navigation grammar
* module header design
* action-zone placement
* supporting surface hierarchy
* plugin-native presentation
* surface classification
* token-safe visual shell decisions

Do **not** start here when the question is about:

* backend topology
* queue semantics
* worker behavior
* release readiness
* storage invariants
* runtime health interpretation

For those, return to the main architecture KB first.

---

## Step 2: Classify the surface before choosing a shell

Read:

* `surface-class-matrix.md`

Ask:

* Is this a **Module**?
* Is this a **Viewer**?
* Is this a **Companion Surface**?
* Is this an **Embedded Utility**?

Do not skip this step.

A large amount of UI drift begins when a Viewer or small utility is given module ceremony just because modules look important.

### Output of this step

You should be able to state clearly:

> “This surface is a Module.”

or

> “This surface is a Companion Surface.”

If you cannot do that, do not move on yet.

---

## Step 3: Read the parent law for the chosen class

### If the surface is a Module

Read:

* `module-header-and-secondary-pill-nav-canon-v1.md`

This is the binding first-party law for:

* Module Header
* Action Zone
* Secondary Pill-Nav
* content-first hierarchy
* supporting-surface subordination

### If the work involves plugin-native presentation

Also read:

* `native-presentation-sdk-contract-v1.md`

This is required when:

* building plugin-native shells
* defining plugin slots
* shaping first-party surfaces that are intended to become plugin exemplars

### If the work is not a Module

Use the surface-class matrix first and stay with the lighter class.
Do not import module law by habit.

---

## Step 4: Check for a surface-specific contract

If a surface already has its own design contract, read that next.

### Example

For Persona Studio, read:

* `persona-studio-design-contract-v1.md`

This step matters because parent canon explains the grammar, but a child contract explains the local expression of that grammar.

### Rule

Surface-specific contracts inherit authority from parent canon.
They do not replace classification or parent law.

---

## Step 5: Read the rationale only after the law is clear

If the surface has an ADR or rationale doc, read it after the binding docs.

### Example

For Persona Studio, then read:

* `adr-persona-studio-as-reference-module.md`

Why this order matters:

* canon tells you what must be true
* contract tells you what should be built here
* ADR tells you why the decision exists

Starting with the ADR first is how contributors end up understanding the poetry while missing the constraints.

---

## Step 6: Implement against the lightest truthful shell

Once the surface class and governing docs are clear:

* use the lightest shell that fits the task
* do not promote a surface to module form because it feels more “complete”
* do not add explanatory bands to compensate for weak structure
* do not invent local shell grammar
* do not let supporting surfaces dominate the first impression

### This is the implementation hinge

Ask continuously:

* Is this shell heavier than the task?
* Am I adding hierarchy or just more furniture?
* Did I choose this structure because the task needs it, or because I needed somewhere to put controls?

---

## Step 7: Run the practical checklist before calling the work done

### If the surface is a first-party module

Run:

* `module-surface-checklist.md`

### If the surface is plugin-native

Run:

* `plugin-native-shell-checklist.md`

Do this before:

* calling the design finished
* filing a UI task as done
* accepting a redesign as structurally correct

Checklists are not busywork.
They are where drift gets caught before it hardens.

---

## Step 8: Update the design-lane metadata when authority changes

If the work added, replaced, or superseded a design document, update:

* `README.md`
* `design-doc-status.md`

### Required cases

Update the tracker and index when:

* a new canon lands
* a contract is replaced
* an ADR becomes active
* a draft is superseded
* a new checklist or matrix is added

### Rule

Do not leave same-scope documents competing for truth.

The design lane should stay legible at a glance.

---

## Step 9: Decide whether a new document is actually needed

Before creating a new design doc, ask:

* Does an existing canon already govern this?
* Is this really a new law, or just an example of an existing law?
* Is this a surface-specific contract?
* Is this a rationale doc?
* Is this just checklist material?
* Is this just a note that belongs in an existing index or status tracker?

### Create a new document only when the role is clear

Good candidates:

* new canon
* new contract
* new ADR
* new checklist
* new matrix
* new index

Bad candidates:

* vague “thoughts” docs
* duplicate same-scope contracts
* near-identical restatements of existing canon
* implementation notes pretending to be architecture

---

## Practical Reading Sequences

## A. New first-party module

1. `surface-class-matrix.md`
2. `module-header-and-secondary-pill-nav-canon-v1.md`
3. relevant child contract, if one exists
4. `module-surface-checklist.md`
5. update tracker/index only if document authority changed

## B. Persona Studio redesign work

1. `surface-class-matrix.md`
2. `module-header-and-secondary-pill-nav-canon-v1.md`
3. `persona-studio-design-contract-v1.md`
4. `adr-persona-studio-as-reference-module.md`
5. `module-surface-checklist.md`

## C. Plugin-native shell work

1. `surface-class-matrix.md`
2. `native-presentation-sdk-contract-v1.md`
3. module canon only if the plugin is truly a Module
4. `plugin-native-shell-checklist.md`

## D. Reviewing an existing crowded surface

1. classify the surface
2. read the parent law
3. check whether support surfaces are dominating
4. run the relevant checklist
5. only then decide whether the problem is structural or cosmetic

---

## Anti-Patterns in Adoption

Do not do the following:

### 1. Start with implementation screenshots only

A screenshot can reveal symptoms, but it cannot tell you which law applies.

### 2. Read rationale before law

This produces poetic misunderstanding.

### 3. Treat every surface as a module

This is how chrome inflation begins.

### 4. Add a new doc before checking the index and tracker

That is how ghost law appears.

### 5. Use checklists without classification

A checklist is only useful if it is the correct checklist.

### 6. Use the design lane for runtime truth

This lane is for presentation architecture, not operational reality.

---

## Role of the Design Index and Status Tracker

### `README.md`

Use this as the directory entrypoint and reading-order map.

### `design-doc-status.md`

Use this as the truth surface for:

* active
* binding
* superseded
* missing

These two docs should be updated whenever design authority changes.

They are not decoration.
They are lane hygiene.

---

## Suggested Contributor Workflow

For any surface-affecting task:

```text
1. classify the surface
2. read the governing canon/contract
3. implement the lightest truthful shell
4. run the correct checklist
5. update design-lane metadata if the doc set changed
```

If that feels repetitive, good.

Repetition is cheaper than semantic drift.

---

## Canonical Summary

Use the design lane in this sequence:

```text
Surface Class Matrix
-> parent canon or SDK contract
-> child surface contract if one exists
-> ADR/rationale if needed
-> implementation
-> relevant checklist
-> README / status tracker update if authority changed
```

The sequence exists to keep Codexify from solving every UI problem with:

* more chrome
* more tabs
* more banners
* more unofficial shell grammar
* more documents than law
