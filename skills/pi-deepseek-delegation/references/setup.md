# Pi and DeepSeek setup

Use this guide only when preflight fails or the user asks how the delegation plumbing works.

## Architecture

Codex invokes a local shell script. The script launches `pi` in non-interactive print mode with an ephemeral session, selects Pi's built-in `deepseek` provider and a currently registered model, restricts the available Pi tools according to the delegation mode, and saves the final response as a local artifact.

Codex remains responsible for planning, repository permissions, diff review, testing, and integration.

## Canonical source

The canonical source lives at `skills/pi-deepseek-delegation/` in the Codexify repository.

Install from source:
```bash
bash skills/pi-deepseek-delegation/scripts/install.sh --install
```

Check for drift between installed and canonical:
```bash
bash skills/pi-deepseek-delegation/scripts/install.sh --check
```

Re-install after updating the repository to synchronize the installed deployment. The installer is atomic and idempotent — repeated installation is safe.

## 1. Install Pi

Pi requires Node.js. Install the Pi coding agent with the current package name shown by the Pi project documentation. Common installations are:

```bash
npm install -g @earendil-works/pi-coding-agent
```

Some existing installations use the earlier package name:

```bash
npm install -g @mariozechner/pi-coding-agent
```

Verify the executable:

```bash
pi --version
```

Do not install both package names unless troubleshooting requires it.

## 2. Configure DeepSeek authentication

Obtain a DeepSeek API key from the DeepSeek platform. Choose one method:

### Environment variable

```bash
export DEEPSEEK_API_KEY="..."
```

### Pi auth storage

Run Pi interactively:

```bash
pi
```

Then use `/login` and select DeepSeek. Pi stores credentials in `~/.pi/agent/auth.json`.

Do not write the key into a repository, skill directory, prompt, shell history, or committed dotfile.

## 3. Discover available models

Run:

```bash
pi --list-models deepseek
```

The current built-in `deepseek` provider ships with models that Pi resolves at runtime. As of writing, the registered models include `deepseek-v4-pro` and `deepseek-v4-flash`.

The delegation wrapper automatically prefers:
1. `deepseek-v4-pro`
2. `deepseek-v4-flash`
3. The first listed model as a fallback.

Optionally set a default:

```bash
export PI_DEEPSEEK_MODEL="deepseek-v4-pro"
```

Model IDs change over time. Run `pi --list-models deepseek` after Pi upgrades and update your default if needed. The wrapper never selects a model that is absent from the current listing.

## 4. Live probe

After authentication is configured, run a minimal live probe to confirm end-to-end connectivity without sending any repository content:

```bash
CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK=1 \
  bash /path/to/skill/scripts/pi_deepseek_delegate.sh --probe --thinking low
```

The probe sends a fixed synthetic prompt (`Say exactly: DEEPSEEK_PI_PROBE_OK`). A successful response confirms transport, authentication, model availability, and response handling.

## 5. Record external-provider consent

After the user understands that delegated prompts and selected repository content leave the local machine for DeepSeek inference, set:

```bash
export CODEX_DEEPSEEK_EXTERNAL_PROVIDER_ACK=1
```

This acknowledgement is intentionally separate from the API key.

Write-capable delegation is disabled unless explicitly enabled:

```bash
export CODEX_DEEPSEEK_WRITE_DELEGATION=1
```

Enable write delegation only for the current shell or specific command when possible.

## 6. Run preflight

From any directory:

```bash
bash /path/to/skill/scripts/pi_deepseek_delegate.sh --check
```

A successful preflight confirms:

- `pi` is on `PATH`.
- DeepSeek authentication appears configured.
- Pi exposes at least one DeepSeek model or the configured model is present.
- The wrapper can determine the requested execution settings.

Preflight does not send repository content to DeepSeek.

## Common failures

### `pi: command not found`

Install Pi or fix the shell `PATH`. Verify with `command -v pi`.

### No DeepSeek authentication detected

Set `DEEPSEEK_API_KEY` or authenticate through Pi. Do not pass the key through `--api-key` in saved scripts because process listings and logs may expose it.

### No model selected

Run `pi --list-models deepseek`, then set `PI_DEEPSEEK_MODEL` to an exact available identifier or matching pattern.

### Provider or model rejected at runtime

The Pi model catalog or DeepSeek API may have changed. Run:
```bash
pi --list-models deepseek
```
Select a currently registered model, or install Pi updates and re-check.

### Pi version too old

The built-in `deepseek` provider shipped in Pi 0.82.0. Upgrade Pi if your version predates this:
```bash
pi update self
```

### Installed skill drifted from source

Re-install from the canonical source:
```bash
bash skills/pi-deepseek-delegation/scripts/install.sh --install
```

### API key rotation

After rotating your DeepSeek API key, update either `DEEPSEEK_API_KEY` or re-run `pi` and `/login deepseek`. The wrapper reads the key at invocation time — no cache invalidation is needed.

### Worker can see too much of the repository

Pi's file tools operate relative to the delegated working directory. Create a scoped temporary directory containing only the necessary files for sensitive read-only analysis, or do not delegate that repository.
