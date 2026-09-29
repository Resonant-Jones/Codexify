# Lane 1 — Preview Human Loop

## Outcome

Produce an independent, reproducible account of what it is like to use the current Codexify Preview as a normal product rather than as its developer.

The value of this lane is not bug volume. It is finding where Codexify still assumes the user knows what the operator knows.

## Why this matters now

The current hosted-service plan says a stranger should be able to understand Codexify, enter it, complete a real path, return later, and get value without private founder knowledge.

A newer product decision also separates **Use Codexify** from **Operate Codexify**. The Preview needs evidence that ordinary client-facing workflows do not unnecessarily expose Full Stack/operator concepts.

## Sources

- Current truth: `docs/architecture/00-current-state.md`
- Notion: Codexify Hosted Service Launch Plan
- Notion: Codexify Product Surface Split — Client, Full Stack, and Domain Workspaces
- Recent UI/runtime work on current `main`

## First Bounded Slice

Use an existing approved Preview account in the browser. Do not inspect the repo, use the CLI, alter services, or ask Chris to rescue a step while executing the first slice.

Attempt these user-visible tasks in order:

1. Enter the product and identify where you would naturally begin.
2. Open or create a thread and send a message.
3. Observe whether request state, completion state, and failure state are understandable.
4. Navigate to at least two non-chat surfaces that look relevant to ordinary use, such as Library/artifacts, projects, settings, or personal messaging when present.
5. Close the browser session, return cold, and determine whether the prior work is findable and understandable.

If a task is impossible, stop that task at the user-visible boundary and record the blocker. Do not fix it during this lane.

## Evidence Artifact

Create:

`docs/collaborators/zac/reports/YYYY-MM-DD-preview-human-loop.md`

For each task, record:

- what you were trying to do;
- what you expected;
- what actually happened;
- whether you could continue without developer knowledge;
- exact reproduction steps for a blocker;
- screenshot or other evidence when it materially clarifies the finding.

Classify findings as one of:

- **Bug** — behavior contradicts the apparent contract.
- **Comprehension friction** — the behavior may be correct but the interface does not explain it.
- **Operator leakage** — ordinary use requires infrastructure/developer knowledge.
- **Missing path** — the user goal has no visible route.
- **Positive proof** — the path works clearly enough that it should be preserved.

## Proof Gate

The first slice is complete when the report contains:

- at least one complete end-to-end task trace;
- a cold-return/continuity observation;
- reproducible evidence for every blocker called significant;
- the three highest-impact friction points, justified from the task traces;
- at least one positive proof of behavior that should not be lost.

## Non-Goals

- Do not implement fixes.
- Do not rewrite architecture.
- Do not use terminal/repo access to make the product appear more usable.
- Do not widen Preview or Beta claims.
- Do not turn personal preference into a bug without describing the underlying user cost.

## Handoff After Proof

Chris can turn the strongest grounded findings into separate implementation tasks. Only then should code changes begin.
