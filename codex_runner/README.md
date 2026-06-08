# Codexify Campaign Runner (Deterministic v2)

Canonical runtime: `codex_runner/`

Legacy package note:
- `tools/codex-runner` is frozen/deprecated.

Pi wrapper note:
- `src/agent-wrapper.js` is an optional Pi-backed path.
- It ships with a vendored Pi SDK tree under `codex_runner/vendor/pi-coding-agent`, so the normal path does not require a separate Pi install.
- It reuses the shared Pi auth store at `~/.pi/agent/auth.json`, so an existing Pi login or API-key setup on the same user account is visible automatically.
- If the vendored tree is missing or incomplete, the wrapper fails closed with repair guidance rather than resolving a machine-specific absolute path.
- Direct Codex/Claude execution is unsupported for Campaign Runner; downstream provider/model identity is brokered through Pi and should be read from explicit receipts when available.

## Interactive TUI (command-first)

Running with no arguments opens the TUI in interactive terminals:

```bash
python codex_runner/runner.py
```

Force TUI mode:

```bash
python codex_runner/runner.py --tui
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
provider = "pi"
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
python codex_runner/runner.py \
  --repo-root /absolute/path/to/repo \
  --audit-prompt-file /path/to/mega_audit.md \
  --audit-schema-file /path/to/mega_audit_output.schema.json \
  --compiler-prompt-file /path/to/audit_report_to_campaign_runner.md \
  --campaign-set-schema-file /path/to/campaign_set.schema.json
```

### Intention packet seam

Use `--intention-packet-file` to provide an operator-authored Markdown packet that narrows Stage A audit posture and Stage B campaign compilation without editing the base prompt templates for one-off targeting.

Minimal example:

```bash
python codex_runner/runner.py \
  --repo-root /absolute/path/to/repo \
  --audit-prompt-file codex_runner/prompts/mega_audit.md \
  --audit-schema-file codex_runner/schemas/mega_audit_output.schema.json \
  --compiler-prompt-file codex_runner/prompts/audit_report_to_campaign_runner.md \
  --campaign-set-schema-file codex_runner/schemas/campaign_set.schema.json \
  --intention-packet-file docs/Campaign/templates/campaign-runner-intention-packet-template.md
```

The packet is planning input only. It can narrow the audit/campaign posture, but it does not prove runtime support, provider support, execution readiness, or release scope. Prefer a completed packet over prompt-template edits whenever the target is a one-off planning objective.

General flags:
- `--provider pi`
- `--passes N` (default: `1`)
- `--base-ref <git-ref>` (default: `HEAD`)
- `--execute` or `--dry-run`
- `--branch-per-campaign` / `--no-branch-per-campaign`
- `--allow-discovery-fallback`
- `--auto-commit` / `--no-auto-commit` (`--no-auto-commit` currently hard-fails by design)
- `--verify` / `--no-verify`
- `--debug`

Pi broker flags:
- `--pi-provider`
- `--pi-model`
- `--pi-model-audit`
- `--pi-model-compiler`
- `--pi-model-task`
- `--pi-thinking`

Verify default policy:
- local/dev default: `--no-verify`
- CI default: `--verify` when `CI=true`
- explicit flag always wins

## Provider requirements

- `pi` provider: `node` executable on PATH plus `codex_runner/src/agent-wrapper.js`
- Downstream provider/model identity is brokered by Pi rather than selected as a direct Campaign Runner provider choice.

## Safety defaults

- Hard-fail on dirty preflight.
- Hard-fail on schema drift.
- Hard-fail on invalid `Task.files[]` paths (absolute or `..`).
- Hard-fail when Stage B mutates an already materialized task.
- Selected campaign with zero tasks:
  - default: hard-fail
  - with `--allow-discovery-fallback`: synthesize discovery task and stop for review.
