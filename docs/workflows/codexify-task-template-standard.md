# Codexify Task Template (Standard)

## Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Use this template for ordinary implementation work that does **not** materially change architecture doctrine, runtime contracts, or control-plane semantics.

Examples:

* UI work
* component behavior
* test fixes
* local refactors
* docs-only edits without architecture impact
* bug fixes that preserve existing contracts

If the task changes architecture meaning, use the **Codexify Architecture-Impact Task Template** instead.

---

## Instructions

Perform the described edit only in the specified files.

This change belongs in:

* `/path/to/file.ext`
* `/path/to/another-file.ext`

Do not modify files outside this scope unless explicitly required.

---

## Goal

State the outcome clearly in one paragraph.

This should answer:

* what is changing
* where it is changing
* what should remain unchanged

---

## Required changes

Break the work into explicit steps.

### 1. First change

This change belongs in:

* `/path/to/file.ext`

Requirements:

* ...
* ...
* ...

### 2. Second change

This change belongs in:

* `/path/to/file.ext`

Requirements:

* ...
* ...
* ...

### 3. Tests or follow-through

This change belongs in:

* `/path/to/test-or-doc.ext`

Requirements:

* ...
* ...
* ...

---

## Scope boundaries

Do **not**:

* refactor unrelated areas
* expand the blast radius without reason
* change architecture doctrine unless the task explicitly says so
* introduce speculative future work
* modify runtime truth docs unless necessary for this task

Keep the change focused.

---

## Test requirements

Run the correct test scope based on the files touched.

### Backend-only work

Use repo-defined backend tests, for example:

```bash id="ih82eu"
pytest -v
```

### Frontend-only work

Use repo-defined frontend tests, for example:

```bash id="e9x4xq"
pnpm test
```

### Mixed work

Run both relevant test scopes.

### Docs-only work

If no docs-specific check exists, report:

```text id="p5ijti"
No automated tests apply
```

But still validate:

* link/path sanity
* markdown well-formedness
* internal consistency

---

## If checks pass

```bash id="rigwxy"
git add <modified files>
git commit -m "<concise descriptive message>"
```

---

## Output must include

1. Summary of changes

   * files changed
   * key functions/components/docs updated

2. Test results

   * exact command(s) run
   * pass/fail outcome
   * explicit “no automated tests apply” if true

3. Git commit hash

---

## Output contract

The final task result must confirm:

* what changed
* how it was validated
* what commit captured it
