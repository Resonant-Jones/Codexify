# Desktop Runtime Monitor Runbook

## Purpose

Provide operators with a read-only, single-command view of Codexify's supported runtime health and the packaged desktop-launcher materialization state. The monitor aggregates multiple independent truth surfaces and presents them without collapsing ambiguity into a binary healthy/unhealthy flag.

This tool is an **operator proof aid**, not an auto-remediation agent. It never changes code, restarts services, runs migrations, rewrites config, or patches files.

## Supported Scope

### Runtime surfaces (HTTP — requires running Docker Compose stack)

| Surface | Endpoint | What it proves |
|---|---|---|
| Backend liveness | `GET /health` | Backend process is up and the app bootstrapped successfully |
| Chat queue/worker health | `GET /health/chat` | Redis reachable, queue round-trips succeed, chat workers have fresh heartbeats |
| Active provider runtime | `GET /api/health/llm` | Currently selected model provider is reachable and in a known runtime state |
| Retrieval health | `GET /api/health/retrieval` | Vector store and retrieval layer are reachable |
| Model catalog | `GET /api/llm/catalog?include=all` | Discovered model inventory is accessible |

### Desktop-launcher proof artifacts (on-disk, platform-specific)

| Artifact | Location (macOS) | What its presence proves |
|---|---|---|
| `.codexify-launcher-startup-state.json` | `~/Library/Application Support/Codexify/` | Setup completed and a backend handoff target was recorded |
| `.codexify-runtime-manifest.json` | `~/Library/Application Support/Codexify/` | Packaged runtime config snapshot was written |
| `.codexify-packaged-runtime` (directory) | `~/Library/Application Support/Codexify/` | Packaged runtime materialization completed |

### What the monitor does NOT prove

- **Accepted work ≠ completion.** A green `/health/chat` proves Redis reachability, queue round-trip, and worker heartbeat freshness — not that any particular chat task has completed or that the UI received it.
- **Provider reachable ≠ model ready.** A `runtime_available` state on `/api/health/llm` means the provider transport is up; it does not mean the model is warm and ready to generate tokens.
- **Artifact present ≠ first-launch succeeded.** A present `.codexify-launcher-startup-state.json` proves the file was written; it does not prove the backend it points to is still running.
- **Task-event visibility ≠ downstream receipt.** Task event publication success proves the event was published to the transport; it does not prove the frontend or any subscriber received it.
- **One green endpoint ≠ runtime truth.** The monitor intentionally reads multiple surfaces. Treat any single surface as necessary but not sufficient.

## Bounded Status Vocabulary

The monitor classifies each surface using an explicit, limited vocabulary:

| Status | Meaning |
|---|---|
| `ready` | Surface responded with a healthy/ok status |
| `degraded` | Surface responded but with a degraded or warning indicator |
| `not_ready` | Surface responded but content indicates it is still initializing (e.g., model warming) |
| `unreachable` | Transport-level failure — timeout, connection error, or HTTP 5xx |
| `missing_artifact` | Expected on-disk file or directory is absent |

The monitor aggregates these into an **overall status** using priority order (highest wins):

```
UNREACHABLE > MISSING_ARTIFACT > NOT_READY > DEGRADED > READY
```

## Exact Commands

### One-shot check

```bash
# Default backend URL (http://localhost:8888)
python scripts/ops/monitor_desktop_runtime.py --once

# Custom backend URL
python scripts/ops/monitor_desktop_runtime.py --once --backend-url http://localhost:8888

# Emit JSON instead of human-readable output
python scripts/ops/monitor_desktop_runtime.py --once --json
```

### Continuous watch mode

```bash
# Poll every 15 seconds (default)
python scripts/ops/monitor_desktop_runtime.py --watch

# Custom interval
python scripts/ops/monitor_desktop_runtime.py --watch --interval 30
```

### Using the env var for backend URL

```bash
CODEXIFY_MONITOR_BACKEND_URL=http://localhost:8888 \
  python scripts/ops/monitor_desktop_runtime.py --once --json
```

## Exit Codes

| Exit code | Meaning |
|---|---|
| `0` | Overall status is `ready` or `degraded` — no unreachable or missing-artifact surfaces |
| `1` | One or more surfaces are `degraded` or `not_ready` |
| `2` | One or more surfaces are `unreachable` or `missing_artifact` |

> Exit code 1 (degraded) is advisory — the runtime is reachable but some surface is not fully healthy. Exit code 2 signals a more serious condition requiring operator attention.

## JSON Output Schema

```json
{
  "overall_status": "ready | degraded | not_ready | unreachable | missing_artifact",
  "runtime": {
    "<surface_name>": {
      "url": "http://localhost:8888/...",
      "status": "ready | degraded | not_ready | unreachable",
      "http_status_code": 200,
      "error": null
    }
  },
  "launcher_artifacts": {
    "<filename>": {
      "path": "/full/path/to/artifact",
      "status": "ready | degraded | missing_artifact",
      "detail": "present | permission denied | ..."
    }
  },
  "next_actions": [
    "Advisory string — never a command to auto-remediate"
  ]
}
```

## Platform Notes

### macOS (desktop launcher)

Desktop artifacts are written to `~/Library/Application Support/Codexify/`. This directory is created by the Tauri desktop shell during first-launch setup. If artifacts are missing, re-run the Codexify desktop setup wizard.

### Linux (desktop launcher)

Artifacts are written to `~/.local/share/Codexify/` (or `$XDG_DATA_HOME/Codexify/` if `XDG_DATA_HOME` is set).

### Windows (desktop launcher)

Artifacts are written to `%LOCALAPPDATA%\Codexify\`.

### Backend always

The backend always runs on port `8888` in the Docker Compose topology. The monitor defaults to `http://localhost:8888`. If your Compose stack exposes the backend on a different port, pass `--backend-url` explicitly.

## Relationship to Existing Health Endpoints

The monitor does not replace direct endpoint inspection. Operators may still run:

```bash
curl -s http://localhost:8888/health | jq .
curl -s http://localhost:8888/health/chat | jq .
curl -s "http://localhost:8888/api/health/llm" | jq .
curl -s "http://localhost:8888/api/health/retrieval" | jq .
curl -s "http://localhost:8888/api/llm/catalog?include=all" | jq .
```

The monitor simply aggregates and summarizes all of these in one pass, alongside the desktop-launcher artifact state, with advisory next actions.

## Reading the Monitor During Operator Proof Sessions

Use the monitor to establish baseline state before and after proof activities:

1. **Pre-proof baseline:** Run `--once --json` before starting a proof session. Record the output. All runtime surfaces should be `ready`; launcher artifacts should be `ready` if the desktop shell has been launched at least once.

2. **Post-activity check:** Run `--once --json` after chat completion, document upload, or retrieval operations. Compare runtime surface statuses to confirm no surface regressed to `unreachable` or `missing_artifact`.

3. **Watch during proof:** Use `--watch --interval 5` during active proof to observe surface stability in real time.

## Read-Only Constraint

The monitor is strictly read-only by design. If any surface reports `degraded` or `unreachable`:

- Do NOT run the monitor with elevated privileges expecting it to "fix" the issue
- Use the `next_actions` advisory strings as investigation leads, not as automated remediation commands
- Manually inspect the referenced surfaces using `curl` or your browser
- Check Docker Compose logs: `docker compose logs -f backend`, `docker compose logs -f worker-chat`, etc.
- Verify the desktop launcher setup completed: re-run the Codexify desktop setup wizard if launcher artifacts are `missing_artifact`

## Monitor Internals

The monitor is implemented in `scripts/ops/monitor_desktop_runtime.py`. Key design decisions:

- **No external dependencies beyond stdlib and `requests`** (requests is optional; the monitor degrades gracefully if it is absent)
- **All HTTP calls use a 5-second timeout** (configurable via `--timeout`)
- **HTTP surface classification inspects response body semantics**, not just HTTP status codes, to distinguish `ready` from `degraded` from `not_ready`
- **Artifact checks validate JSON parseability** for `.json` files, and distinguish "not found" from "permission denied" from "malformed"
- **The `next_actions` field never contains commands** that change code, restart services, run migrations, or rewrite config — it is strictly advisory for human operators
