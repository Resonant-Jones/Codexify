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
- Provider: <provider ID or N/A>
- Model: <model ID or N/A>
```

Use explicit provider and model identifiers when a provider-dependent path is exercised. Record `N/A` only when the qualification surface does not involve a provider or model.

## Machine-readable metadata

The header above is for human readers. The registry is generated from a
fenced YAML block, so every receipt must also declare:

````markdown
```yaml qualification-metadata
qualification_id: supported-compose
rubric_version: 1
verdict: HOLD
commit: 5da79431fa059b7da80688380550cf29d4854b18
date: 2026-09-22
tester_alias: automated-architecture-proof
tester_kind: automated
assistance_level_peak: 0
evidence:
  - docs/architecture/proofs/supported-compose/some-proof.md
```
````

`qualification_id` must match the rubric the receipt qualifies.
`rubric_version` records which rubric version was applied, so a rubric
revision does not silently inherit an older run's verdict.

`tester_kind` is `human` or `automated`. Only human runs contribute to the
`human_testers` and `independent_completions` metrics, because the
qualification README treats independent human qualification as the
strongest available signal. `assistance_level_peak` is the highest
assistance level reached during the run, from the independence table.

`evidence` lists the proof artifacts the run cited, as repository-relative
paths. Every cited path must exist.

The generator rejects a receipt with a missing or malformed metadata block
rather than skipping it.

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
