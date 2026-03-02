# Codexify Campaign Runner (Deterministic v2)

Canonical runtime: `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner`

Legacy package note:
- `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/tools/codex-runner` is frozen/deprecated.

## Install (pip)

Install from PyPI:

```bash
pip install codexify-campaign-runner
```

Run:

```bash
codex-runner --tui
```

or:

```bash
python -m codex_runner --tui
```

For local development install:

```bash
pip install -e .
```

## Interactive TUI (command-first)

Running with no arguments opens the TUI in interactive terminals:

```bash
codex-runner
```

Force TUI mode:

```bash
codex-runner --tui
```

Non-interactive behavior:
- no args in non-interactive mode (CI/piped): does not launch TUI; falls back to CLI argument validation
- explicit `--tui` in non-interactive mode: hard-fails with an interactive terminal error
- missing Textual dependency: hard-fails with install guidance

## TUI workflow

The TUI is command-bar first (single input bar) with compact summaries for:
- active settings
- staged changes
- recent events

### Command surface

- `/set <key> <value>`
- `/toggle <key>`
- `/preset <name>`
- `/apply`
- `/discard`
- `/preview`
- `/run`
- `/save`
- `/edit-paths`
- `/help`
- `/quit`

### Staged/apply model

- settings edits are staged first
- `/apply` commits staged settings to active settings (with validation)
- `/run` is strict and blocks if staged changes exist

### Run modes

Strict run (`/run` or `Ctrl+R`):
- blocks on staged changes
- enforces TUI validation
- shows preview before running

Instant run (`Cmd+Enter` or `Ctrl+Enter`):
- treats key combo as explicit consent
- auto-applies staged changes
- skips TUI validation and preview
- exits immediately to run

### Preview command behavior (minimal args by default)

TUI preview/run now emits a minimal argument set by default. Flags that match
`default_settings()` are omitted.

Example with defaults unchanged:

```bash
python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/runner.py
```

Example after changing only passes and execute mode:

```bash
python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/runner.py --passes 2 --execute
```

The deterministic runner now accepts these omitted defaults directly:
- `--repo-root` defaults to current working directory
- prompt/schema file flags default to bundled files in `codex_runner/`

This means common speed-run defaults are implicit unless changed:
- verify default (`--no-verify` in local/dev, `--verify` in CI)
- `--branch-per-campaign`
- `--passes 1`

For a full explicit flag list (debugging/tooling), use `to_cli_args(..., minimal=False)`.

### Important: legacy `codex-runner` binary on PATH

If `codex-runner -h` shows legacy flags like `--cycles` and does not show `--tui`,
your shell is using an older global binary. Use one of these instead:

```bash
python -m codex_runner --tui
```

or:

```bash
python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner/runner.py --tui
```

### Path editing

Use `/edit-paths` to bulk-edit long path settings in a focused modal.

### Key bindings

- `/`: focus command input
- `Ctrl+S`: save profile
- `Ctrl+R`: strict run
- `Cmd+Enter`: instant run (macOS)
- `Ctrl+Enter`: instant run fallback
- `q`: quit

## Persisted settings

Stored at:
- `~/.config/campaign_runner/settings.toml`

Load order:
1. built-in defaults
2. persisted profile
3. optional `--tui` CLI overrides

Presets are supported via TOML blocks:

```toml
[presets.fast]
passes = 2
verify = false
branch_per_campaign = true
provider = "codex"
```

Unknown preset keys are ignored with warnings.

## Core guarantees

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

## Run metadata

The runner writes `run_meta.json` to:
- `docs/_audits/YYYY-MM-DD/<audit_id>/run_meta.json`
- `docs/_campaign_runs/YYYY-MM-DD/<campaign_slug>/<run_id>/run_meta.json`

Additional provider traceability in `run_meta.json`:
- provider name
- provider model map (`default`, `audit`, `compiler`, `task`)
- sanitized provider settings list (redacts token/secret/password/key markers)

## CLI

Required:

```bash
codex-runner \
  --repo-root /absolute/path/to/repo \
  --audit-prompt-file /path/to/mega_audit.md \
  --audit-schema-file /path/to/mega_audit_output.schema.json \
  --compiler-prompt-file /path/to/audit_report_to_campaign_runner.md \
  --campaign-set-schema-file /path/to/campaign_set.schema.json
```

General flags:
- `--provider {codex,claude}`
- `--passes N` (default: `1`)
- `--base-ref <git-ref>` (default: `HEAD`)
- `--execute` or `--dry-run`
- `--branch-per-campaign` / `--no-branch-per-campaign`
- `--allow-discovery-fallback`
- `--auto-commit` / `--no-auto-commit` (`--no-auto-commit` currently hard-fails by design)
- `--verify` / `--no-verify`
- `--debug`

Codex provider flags:
- `--codex-model`
- `--codex-model-audit`
- `--codex-model-compiler`
- `--codex-model-task`
- `--codex-config` (repeatable)

Claude provider flags:
- `--claude-model`
- `--claude-model-audit`
- `--claude-model-compiler`
- `--claude-model-task`
- `--claude-settings` (repeatable)

Verify default policy:
- local/dev default: `--no-verify`
- CI default: `--verify` when `CI=true`
- explicit flag always wins

## Provider requirements

- `codex` provider: `codex` executable on PATH
- `claude` provider: `claude` executable on PATH

## Safety defaults

- Hard-fail on dirty preflight.
- Hard-fail on schema drift.
- Hard-fail on invalid `Task.files[]` paths (absolute or `..`).
- Hard-fail when Stage B mutates an already materialized task.
- Selected campaign with zero tasks:
  - default: hard-fail
  - with `--allow-discovery-fallback`: synthesize discovery task and stop for review.
