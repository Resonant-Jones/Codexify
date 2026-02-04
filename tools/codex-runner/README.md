# Codex Runner (Standalone Tool)

Codex Runner turns an audit prompt into a campaign JSON, writes campaign/task
artifacts into a target repo, and optionally executes each task sequentially
with `codex exec`.

## Prereqs
- Python >= 3.10
- Git installed and available on PATH
- Codex CLI installed and authenticated per Codex CLI docs

## Usage
```bash
codex-runner --repo-root /path/to/repo --audit-prompt-file /path/to/audit.md --dry-run
```

```bash
codex-runner --repo-root /path/to/repo --audit-prompt-file /path/to/audit.md --execute
```

## Notes
- Branch per campaign: the runner creates/switches to a branch named
  `campaign/YYYY-MM-DD/<slug>` using the campaign_slug from the audit output.
- `--no-verify` is the default to keep automation deterministic and avoid
  pre-commit hooks; use `--verify` to run hooks.
- Parallel campaigns require separate worktrees or clones to avoid Git
  serialization.
