# Qualification Run Receipts

This directory contains immutable or append-only receipts for actual qualification attempts.

Use one file per tester/session/context.

Recommended filename:

```text
YYYY-MM-DD-<surface>-<tester-or-context>.md
```

Examples:

```text
2026-09-30-onboarding-zac.md
2026-09-30-onboarding-george.md
2026-10-02-people-two-user-live.md
```

## Required receipt header

```markdown
# <Qualification surface> — <tester/context> — <date>

- Rubric: ../rubrics/<rubric>.md
- Rubric version: <n>
- Verdict: PASS | HOLD | FAIL
- Date/time window:
- Tester alias:
- Tester role:
- Prior familiarity:
- Assistance level peak:
- Branch:
- Commit:
- Runtime profile:
- Deployment/environment:
- Device class:
- Browser/client:
```

## Required body

### Qualification matrix

| Criterion | Result | Observation | Evidence |
| --- | --- | --- | --- |
| ... | PASS / FAIL / UNPROVEN / N/A | ... | ... |

### Metrics

Record the metrics required by the governing rubric.

### Tester language

Preserve useful direct tester comments.

### Proven

List only what this run directly established.

### Failed

List reproduced contract failures.

### Unproven

List anything not exercised or not evidenced strongly enough.

### Human friction

Separate usability findings from functional defects.

### Positive signals

Record what worked without prompting.

### Highest-priority follow-up

Name one concrete next product or qualification seam.

### Evidence

Link to exact supporting proof artifacts, screenshots, traces, logs, or architecture proof receipts.

## Historical integrity

Do not silently rewrite a committed run to make an old result match newer behavior.

When a later run supersedes an earlier run:

1. preserve the earlier receipt;
2. add the new receipt;
3. update `../registry.json` to project the current result;
4. mark prior registry status as superseded only where needed.

The run is evidence. The registry is the current projection.
