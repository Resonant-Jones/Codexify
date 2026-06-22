# Campaign Charter Template

Copy this template to `<campaign-folder>/charter.md` and fill in all sections.

---

## Metadata

- **Campaign ID**: `<CXX>`
- **Title**: `<campaign title>`
- **Wave**: `<0–5>`
- **Status**: `planned` | `in-progress` | `complete` | `blocked`
- **Owner**: `<operator name or role>`
- **Risk**: `LOW` | `MED` | `HIGH`
- **Architecture Impact**: `yes` | `no`
- **Governing ADRs/Contracts**: `<list of governing documents>`

## Purpose

One or two sentences describing what this campaign accomplishes and why it matters.

## Current Truth Anchors

What is true now in the codebase that this campaign depends on or must preserve:
- `<fact>`
- `<fact>`

## Non-Goals

What this campaign explicitly does **not** do:
- `<excluded behavior or surface>`
- `<excluded behavior or surface>`

## Invariants

Invariants that must be preserved throughout this campaign:
- `<invariant>`
- `<invariant>`

## Dependencies

Campaigns that must be complete before this campaign can start:
- `<dependency campaign ID>` — `<reason>`

Campaigns that this campaign enables:
- `<dependent campaign ID>` — `<reason>`

## Backend/API Surfaces

Backend routes, services, or database changes this campaign touches:
- `<path or route>` — `<what changes>`

## Frontend Surfaces

Frontend components, pages, or state this campaign touches:
- `<path or component>` — `<what changes>`

## Proof Gates

| Category | Required Evidence |
|----------|-------------------|
| Docs proof | `<evidence description>` |
| Backend seam proof | `<evidence description>` |
| Frontend UI proof | `<evidence description>` |
| Live supported-path proof | `<evidence description>` |
| Operator usability proof | `<evidence description>` |

## Done-When

The campaign is done when:
1. `<criterion>`
2. `<criterion>`
3. `<criterion>`

## Risks

- `<risk description>` — `<mitigation>`

## Task Queue

Tasks are tracked in [`backlog.md`](./backlog.md). See [`task-index-template.md`](../../templates/task-index-template.md) for the task table format.
