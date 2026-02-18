# Deterministic Campaign Runner v2

Canonical runtime: `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner`

Legacy package note:
- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tools/codex-runner` is frozen/deprecated.

## Core Guarantees

- Runner owns identifiers (`run_id`, `audit_id`) and artifact paths.
- Runner owns state (`docs/_campaign_runs/state/state.json`) and transition history.
- Stage B is a proposal; runner merges deterministically and hard-fails on task mutation drift.
- Campaign mapping edits are restricted to:
  - `<!-- RUNNER_TASK_MAP -->`
  - `<!-- /RUNNER_TASK_MAP -->`
- Task execution uses a strict two-commit receipt pipeline per task.

## Deterministic IDs

- `run_id` = first 12 hex chars of `sha256(canonical(run_inputs.json))`
- `audit_id` = `AUDIT_<run_id>`
- Stage A output must echo `audit_id` exactly.

## Run Metadata

The runner writes `run_meta.json` to:
- `docs/_audits/YYYY-MM-DD/<audit_id>/run_meta.json`
- `docs/_campaign_runs/YYYY-MM-DD/<campaign_slug>/<run_id>/run_meta.json`

Tracked by default:
- `docs/_audits/**`
- `docs/_campaign_runs/**`

## CLI

Required:

```bash
python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/runner.py \
  --repo-root /absolute/path/to/repo \
  --audit-prompt-file /path/to/mega_audit.md \
  --audit-schema-file /path/to/mega_audit_output.schema.json \
  --compiler-prompt-file /path/to/audit_report_to_campaign_runner.md \
  --campaign-set-schema-file /path/to/campaign_set.schema.json
```

Optional flags:
- `--passes N` (default: `1`)
- `--base-ref <git-ref>` (default: `HEAD`)
- `--execute` or `--dry-run`
- `--branch-per-campaign` / `--no-branch-per-campaign`
- `--allow-discovery-fallback`
- `--auto-commit` / `--no-auto-commit` (`--no-auto-commit` currently hard-fails by design)
- `--verify` / `--no-verify`
- `--debug`

Verify default policy:
- local/dev default: `--no-verify`
- CI default: `--verify` when `CI=true`
- explicit flag always wins

## Safety Defaults

- Hard-fail on dirty preflight.
- Hard-fail on schema drift.
- Hard-fail on invalid `Task.files[]` paths (absolute or `..`).
- Hard-fail when Stage B mutates an already materialized task.
- Selected campaign with zero tasks:
  - default: hard-fail
  - with `--allow-discovery-fallback`: synthesize discovery task and stop for review.
