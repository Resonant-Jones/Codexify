# Marketing Run History

`run-history.jsonl` is append-only and records each generation run.

Each line represents one run summary.
Generated campaign artifacts are overwritten deterministically for the same campaign ID, while history remains append-only.
