# Codexify Solo Operator OS + Automation Bootcamp (2 Weeks)

Purpose: Install a practical solo-founder operating system for Codexify with guided drills, maintained in-repo maps/runbooks, and a no-code automation baseline that works in current local Docker.
Last updated: 2026-02-27
Source anchors:
- `docs/Ops/SOLO_OPERATOR_SYSTEM_MAP.md`
- `docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md`
- `docs/Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/flows.md`

## Canonical Deliverables

1. System map: `docs/Ops/SOLO_OPERATOR_SYSTEM_MAP.md`
2. Automation runbook: `docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md`
3. Failure signatures page: `docs/Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md`

These are the canonical docs for solo operations. Other tools/boards are mirrors.

## Phase 1 (Days 1-3): Build Your Map

1. Use the 6-lane map (UI, API, Workers, Data, Automation, Ops).
2. Anchor each lane to exact code/docs paths.
3. Practice first-debug command per lane.

Exit criteria:
- You can answer "where does X live?" in under 30 seconds.
- You can name the first log or endpoint to inspect for a broken flow.

## Phase 2 (Days 4-6): Learn Command and Automation Surfaces

1. Drill command bus flow: manifest -> invoke -> run events.
2. Drill cron flow: create job -> trigger run row -> inspect run history.
3. Internalize baseline constraint: local-only setup + current cron types means the practical baseline is `noop` discipline and observability.

Exit criteria:
- You can run one command-bus invocation and one cron lifecycle without guessing.
- You can explain the difference between `/api/tools/*` compatibility behavior and durable `/api/cron/*` records.

## Phase 3 (Days 7-10): Install Your Solo OS

1. Run the daily 20-minute loop.
2. Run the weekly 90-minute review loop.
3. Enforce single source of truth: repo docs are canonical.

Exit criteria:
- Daily loop executed 5 days straight.
- Weekly review outputs a prioritized top-3 with explicit kill/defer decisions.

## Phase 4 (Days 11-14): Stabilize and Scale Yourself

1. Run failure drills (worker down, queue unavailable, bad auth, webhook denied).
2. Keep failure signatures current in `docs/Ops/SOLO_OPERATOR_FAILURE_SIGNATURES.md`.
3. Freeze baseline checks before starting new feature work.

Exit criteria:
- You can recover from common failures using your own runbook.
- Map/runbook remain aligned with reality after one week of change.

## Daily and Weekly Loops (Canonical)

- Daily loop details: `docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md`
- Weekly loop details: `docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md`

## Drill Sequence (Canonical)

Use the exact drill sequence from:
- `docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md`

## Scope Guardrails

1. This bootcamp introduces no API contract changes.
2. Focus is operational fluency, not feature expansion.
3. Keep docs synchronized as code changes land.
