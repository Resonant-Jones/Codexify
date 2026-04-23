# Desktop Runtime Monitor Runbook

Purpose: give operators a read-only way to inspect the supported local Docker Compose runtime and the desktop-launcher proof surfaces together, without treating a single endpoint as the whole truth.

## Scope

- Supported runtime: local Docker Compose stack.
- Desktop shell: alternate launcher/client surface around that runtime.
- Operator task: compare runtime health, provider health, and launcher materialization evidence in one command.
- Non-goal: automatic repair.

## What the monitor proves

- The backend runtime is reachable or unreachable as a distinct fact.
- The chat, provider, and retrieval evidence surfaces can be read separately.
- The launcher startup-state file is present or absent as a separate fact.
- The packaged runtime manifest and marker are present or absent as a separate fact.
- One operator command can produce a structured summary without guessing from a single endpoint.

## What the monitor does not prove

- It does not prove a user-facing UI receipt.
- It does not prove accepted work completed successfully.
- It does not prove the launcher self-healed.
- It does not rewrite config, restart services, run migrations, or patch files.
- It does not replace live launch ritual proof in the installed app.

## Status vocabulary

The monitor uses a bounded status vocabulary:

- `ready`
- `degraded`
- `unreachable`
- `missing_artifact`
- `not_ready`

`ready` is the only exit-0 state. Any other status yields a nonzero exit code in `--once` mode.

## Files and roots

- Launcher startup state:
  - `~/Library/Application Support/Codexify/.codexify-launcher-startup-state.json`
- Packaged runtime materialization:
  - `~/Codexify/.codexify-runtime-manifest.json`
  - `~/Codexify/.codexify-packaged-runtime`

The monitor accepts overrides for both roots, which makes it safe to test against a temporary directory tree.

## Exact commands

Run a single read-only snapshot:

```bash
python scripts/ops/monitor_desktop_runtime.py --once
```

Run a single snapshot as JSON:

```bash
python scripts/ops/monitor_desktop_runtime.py --once --json
```

Watch repeatedly:

```bash
python scripts/ops/monitor_desktop_runtime.py --watch
```

Use custom roots during proof or test sessions:

```bash
python scripts/ops/monitor_desktop_runtime.py \
  --once \
  --base-url http://127.0.0.1:8888 \
  --app-support-root "$HOME/Library/Application Support/Codexify" \
  --runtime-root "$HOME/Codexify"
```

## Surface-by-surface interpretation

### `GET /health`

- Proves the backend is answering and exposes the active supported-profile view.
- If this is unreachable, the supported runtime itself is not trustworthy for proof.

### `GET /health/chat`

- Proves the queue-backed chat lane is healthy enough to inspect.
- This is not proof of UI receipt or eventual completion.

### `GET /api/health/llm`

- Proves the provider lane is reachable, warming, degraded, or offline as a distinct fact.
- This does not prove the catalog or launcher materialization is valid.

### `GET /api/health/retrieval`

- Proves the retrieval runtime can be inspected separately from provider health.
- This does not prove the UI consumed the result or that every retrieval path is live.

### `GET /api/llm/catalog?include=all`

- Proves the discovered provider inventory can be inspected in operator mode.
- This does not prove model execution is healthy by itself.

### Launcher startup state

- Proves whether the packaged launcher wrote a startup-state file.
- A present file that still says setup is incomplete remains `not_ready`.

### Packaged runtime manifest and marker

- Proves whether the packaged runtime materialization is present.
- Missing manifest or marker stays `missing_artifact`, not guessed.

## Operator workflow

1. Run `--once` before or after an installed-app launch ritual.
2. Check `overall_status` first.
3. Read runtime, provider, and launcher sections separately.
4. Treat `next_actions` as advisory only.
5. If launcher artifacts are missing, rerun the launcher ritual rather than editing files.

## Practical reading guide

- `ready`: the surface is healthy enough for the supported proof.
- `degraded`: the surface is reachable, but the proof is incomplete or slower/less trustworthy than expected.
- `not_ready`: the surface is present but not ready for proof.
- `missing_artifact`: the file or materialization is absent.
- `unreachable`: the request could not reach the surface at all.

## Example

```bash
python scripts/ops/monitor_desktop_runtime.py --once --json
```

The JSON output is intended to be machine-readable, but it is still read-only operator truth. It is not a remediation loop.
