# Qualification Rubrics

This directory holds one rubric per qualification surface.

A rubric defines **what must be proven**. It does not record whether it was
proven — that is the job of a run receipt under `../runs/`, and the job of
`../registry.json` to project the current state of those runs.

See [`../README.md`](../README.md) for the full qualification directory
contract and vocabulary.

## Required structure

Every rubric declares a `Qualification ID`, a `Version`, and a
machine-readable metadata block:

````markdown
# <Surface title>

## Qualification ID

`<qualification-id>`

## Version

`<n>`

## Qualification metadata

```yaml qualification-metadata
qualification_id: <qualification-id>
version: <n>
title: <surface title>
scope: One line describing exactly what this surface covers.
surface_paths:
  - guardian/routes/**
evidence:
  - docs/architecture/proofs/some-proof.md
```
````

The `Qualification ID` in prose and `qualification_id` in the metadata block
must agree. The validator checks this.

## What each field means

`qualification_id`
: The canonical identity of the surface. It keys the registry entry and
  must match the file name stem.

`version`
: The rubric version. A run receipt records the rubric version it was
  performed against, so revising a rubric does not silently inherit an
  older run's verdict.

`title` and `scope`
: The scope statement is what makes a PASS interpretable. "Supported Compose
  runtime on one frozen evaluated tip" is a scope. "The backend works" is
  not.

`surface_paths`
: The repository paths whose changes make a qualification run
  unrepresentative of current code. This is how freshness is computed: the
  generator diffs the tested commit against the tip and asks whether
  anything in the surface moved.

  Choose the surface narrowly enough that the question is meaningful. A
  surface that covers the whole repository will always be stale; a surface
  that covers nothing will always be current. Neither tells the reader
  anything.

`evidence`
: Standing proof artifacts that document the surface, as repository-relative
  paths. This is the evidence that exists regardless of whether a
  qualification run has been recorded, so a surface with no run still links
  the proofs that describe it — without ever being projected as qualified.

## Rules

- A rubric is a definition, not a result. It must not claim that a surface
  passed.
- A surface with no rubric is `UNPROVEN`, not implicitly passing.
- Only create a qualification area when there is a defined rubric.
- Blocking criteria belong in the rubric. A run that meets every required
  check but leaves a boundary unexercised is `HOLD`, not `PASS`.

## Adding a surface

1. Write the rubric with its metadata block.
2. Regenerate the registry:
   `python scripts/qualification/generate_registry.py`
3. Validate it:
   `python scripts/qualification/validate_registry.py`

A new surface appears in the registry as `HOLD` until a run receipt exists
for it. That is correct: the registry must never manufacture qualification.
