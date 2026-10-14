# Qualification Metric Definitions

This file defines common metric names used by human and runtime qualification receipts.

Metrics are evidence fields, not vanity scores. A metric should be recorded only when it was actually observed.

## Common identity fields

- `tester_alias`
- `tester_role`
- `commit`
- `branch`
- `runtime_profile`
- `deployment_environment`
- `device_class`
- `browser_client`
- `prior_familiarity`
- `rubric_id`
- `rubric_version`

## Common human-experience metrics

### task_completed

`yes | no`

Whether the tester completed the requested task.

### assistance_level

Integer `0-4`.

| Level | Meaning |
| --- | --- |
| 0 | Independent |
| 1 | Self-recovery |
| 2 | Clarification |
| 3 | Navigation hint |
| 4 | Directed |

### wrong_turns

Integer count of incorrect surfaces/actions tried before success.

### self_recovered

`yes | no | n/a`

Whether the tester recovered from confusion without operator direction.

### time_to_first_success_seconds

Elapsed seconds where time is meaningful. This is observational, not a default PASS gate.

### repeat_task_confidence_1_to_5

Tester response to:

> How confident are you that you could do this again without help?

### felt_real_name_pressure

`yes | no | n/a`

Use for identity/profile flows.

### tester_quotes

Verbatim or lightly normalized tester language. Do not rewrite confusion into operator interpretation.

### observed_confusion

Operator record of the observable confusion or wrong mental model.

### positive_signals

What worked as the tester expected without prompting.

## Contract metrics

Contract metrics should use direct observable values whenever possible.

Examples:

- `message_persisted: true`
- `conversation_id_stable: true`
- `skip_state_persisted: true`
- `wrong_account_access_rejected: true`
- `backend_restart_readback: true`

Contract metrics may block qualification when the rubric declares them blocking.

## Aggregation rules

For small samples, report raw counts.

Prefer:

```text
independent_completions: 2 / 3
human_testers: 3
```

over:

```text
67% success
```

Percentages may be added later when sample sizes make them useful, but must always retain the denominator.

## Missing data

Do not convert missing observations to false.

Use:

- omitted field, or
- explicit `null` in machine-readable receipts,

when a metric was not collected.

## Dashboard rule

Dashboard summaries must be projections of committed run receipts and registry entries.

The dashboard must not calculate a PASS verdict from arbitrary UX averages. Verdict semantics come from the governing rubric.
