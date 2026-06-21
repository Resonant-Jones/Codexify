# Codex Runner (Standalone Tool)

> Deprecated for active development. Canonical runtime is `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/codex_runner`.

Codex Runner turns an audit prompt into a campaign JSON, writes campaign/task
artifacts into a target repo, and optionally executes each task sequentially
with `codex exec`.

## Prereqs
- Python >= 3.10
- Git installed and available on PATH
- OpenAI Codex CLI installed, authenticated, and available as `codex` on PATH

## Codex CLI setup
Run these checks from the same shell or service account that will launch
`codex-runner`.

1. Install the official OpenAI Codex CLI using one supported path:
   ```bash
   curl -fsSL https://chatgpt.com/codex/install.sh | sh
   ```
   ```bash
   npm install -g @openai/codex
   ```
   ```bash
   brew install --cask codex
   ```

2. Confirm the binary is visible:
   ```bash
   command -v codex
   codex --version
   ```

3. Authenticate the CLI:
   ```bash
   codex login
   ```
   For API-key auth instead of browser/ChatGPT sign-in:
   ```bash
   codex login --api-key "$OPENAI_API_KEY"
   ```

4. Verify non-interactive runner access before launching:
   ```bash
   codex login status
   codex exec "Return only: OK"
   ```

If `codex` is missing from PATH, `codex-runner` stops before invoking the
model and prints the install, auth, and verification steps above.

## Usage
```bash
# Plan-only: generate + commit artifacts, skip task execution.
codex-runner --repo-root /path/to/repo --audit-prompt-file /path/to/audit.md --dry-run
```

```bash
# Execute tasks after generating artifacts.
codex-runner --repo-root /path/to/repo --audit-prompt-file /path/to/audit.md --execute
```

```bash
# Preview only: no filesystem writes, no git operations.
codex-runner --repo-root /path/to/repo --audit-prompt-file /path/to/audit.md --preview
```

## Notes
- Branch per campaign: the runner creates/switches to a branch named
  `campaign/YYYY-MM-DD/<slug>` using the campaign_slug and the campaign doc date.
- `--no-verify` is the default to keep automation deterministic and avoid
  pre-commit hooks; use `--verify` to run hooks.
- `--preview` cannot be combined with `--execute` or `--dry-run`.
- Parallel campaigns require separate worktrees or clones to avoid Git
  serialization.
