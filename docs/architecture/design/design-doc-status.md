# Design Doc Status Tracker

> Classification: tracking index
> Status: operational
> Scope: active, superseded, proposed, and draft status for documents in `docs/architecture/design/`
> Not runtime truth: This file tracks document status only. It does not define runtime behavior, release readiness, or product guarantees.

## Purpose

This file exists to prevent document drift inside `docs/architecture/design/`.

It answers:

* which documents are active
* which documents are binding
* which documents are rationale only
* which drafts have been superseded
* which artifacts still need to be written or landed

This tracker should be updated whenever:

* a design document is added
* a draft is replaced
* a canon/contract is superseded
* a proposed document becomes active

---

## Status Legend

### Active

Current and intended for normal use.

### Binding

Current and authoritative within its stated scope.

### Proposed

Drafted and intended, but not yet treated as final law.

### Superseded

Replaced by a newer document and should not be used as authority.

### Archived

Retained for lineage only.

### Missing

Planned but not yet written.

---

## Current Design-Lane Status

| Document                                              | Type     |     Status | Authority Level | Notes                                                          |
| ----------------------------------------------------- | -------- | ---------: | --------------- | -------------------------------------------------------------- |
| `README.md`                                           | index    |     Active | entrypoint      | Directory reading order and interpretation rules               |
| `module-header-and-secondary-pill-nav-canon-v1.md`    | canon    |    Binding | high            | Primary first-party law for module-class surfaces              |
| `native-presentation-sdk-contract-v1.md`              | contract |     Active | high            | Plugin-facing companion contract                               |
| `persona-studio-design-contract-v1.md`                | contract |     Active | high            | Concrete design contract for Persona Studio                    |
| `adr-persona-studio-as-reference-module.md`           | ADR      |     Active | rationale       | Records why Persona Studio is the flagship reference module    |
| `module-header-and-secondary-pill-nav-contract-v1.md` | contract | Superseded | none            | Replaced by `module-header-and-secondary-pill-nav-canon-v1.md` |

---

## Supersession Rules

### 1. Canon beats earlier scaffold docs

If an earlier contract draft and a later canon cover the same conceptual surface, the canon wins.

### 2. Parent law beats child interpretation

If a module-specific design contract conflicts with its parent canon, the canon wins unless the child document explicitly states a valid exception.

### 3. ADRs explain, but do not outrank canon

ADR documents record reasoning and intent. They do not override canon or contract language.

### 4. Index files do not create authority

`README.md` and this tracker explain the doc lane. They do not act as design law by themselves.

---

## Current Superseded Items

### `module-header-and-secondary-pill-nav-contract-v1.md`

**Status:** Superseded
**Replaced by:** `module-header-and-secondary-pill-nav-canon-v1.md`

**Reason:**
The earlier contract was a transitional scaffold. The canon is the binding replacement and should be treated as the authoritative document.

**Action:**
Remove, archive, or clearly mark as superseded. Do not leave it appearing active beside the canon.

---

## Current Planned Additions

| Planned Document                   |  Status | Purpose                                                                                 |
| ---------------------------------- | ------: | --------------------------------------------------------------------------------------- |
| `module-surface-checklist.md`      | Missing | Fast implementation checklist for first-party module builders                           |
| `plugin-native-shell-checklist.md` | Missing | Fast checklist for plugin authors using the native shell                                |
| `surface-class-matrix.md`          | Missing | Distinguish modules, viewers, companions, utilities, and other sanctioned surface types |
| `design-adr-index.md`              | Missing | Index of design ADRs in this directory                                                  |

---

## Maintenance Rules

When a new document is added to `docs/architecture/design/`:

* add it here
* mark its type clearly
* mark whether it is Active, Binding, Proposed, Superseded, Archived, or Missing
* state what it supersedes, if anything

When a document is replaced:

* update this tracker in the same change
* remove ambiguity about which file is current
* do not leave two same-scope documents appearing equally authoritative

When a draft becomes final:

* change its status here
* update the directory `README.md` if the reading order changes

---

## Recommended Current Reading Order

1. `README.md`
2. `module-header-and-secondary-pill-nav-canon-v1.md`
3. `native-presentation-sdk-contract-v1.md`
4. `persona-studio-design-contract-v1.md`
5. `adr-persona-studio-as-reference-module.md`

---

## Canonical Summary

This tracker exists to keep the design lane orderly.

Its current key truth is:

* **Module Header + Secondary Pill-Nav Canon v1** is the binding authority
* **Native Presentation SDK Contract v1** is the active plugin-facing companion
* **Persona Studio Design Contract v1** is the active flagship implementation contract
* **ADR: Persona Studio as the Reference Module for Codexify** is rationale
* the earlier **Module Header + Secondary Pill-Nav Contract v1** is superseded
