# Guardian Codex Runner Container Visibility Contract

> Classification: architecture contract
> Status: opt-in local Docker visibility seam only
> Scope: operator-configurable read-only container mount for backend preflight validation

Last updated: 2026-07-08

Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/guardian-codex-runner-preflight-bridge-contract.md
- docs/architecture/guardian-codex-runner-command-bus-proof.md
- docs/architecture/guardian-codex-runner-command-bus-live-validate-proof.md
- docs/architecture/guardian-codex-runner-command-bus-live-validate-retry-proof.md
- docker-compose.yml
- docker-compose.codex-runner-bridge.yml
- guardian/codex_runner_bridge/contracts.py
- guardian/codex_runner_bridge/adapter.py

## 1. Purpose

This contract defines the opt-in local Docker filesystem visibility seam that allows the Codexify backend container to see the host Codex Runner checkout at the exact path expected by the existing bridge adapter (`/Volumes/Dev_SSD/Codex-Runner`).

It exists because the live validate retry proof (`guardian-codex-runner-command-bus-live-validate-retry-proof.md`) reached the command-bus adapter but failed because the backend container could not see `/Volumes/Dev_SSD/Codex-Runner`.

The fix is an opt-in read-only mount, not a default runtime expansion.

## 2. Status

Status: opt-in local Docker visibility seam only.

This contract does not:

- prove live validation
- prove live orchestration (this is not live orchestration proof)
- add UI support
- add a new API route
- enable write flags
- authorize Pi Loop invocation
- authorize source mutation
- authorize Codexify ingestion

## 3. Scope

This contract governs only the Docker-level filesystem visibility seam between the Codexify backend container and the host Codex Runner checkout.

It covers:

- an opt-in Compose override file (`docker-compose.codex-runner-bridge.yml`)
- a read-only bind mount that preserves the expected bridge path
- operator-facing documentation for startup and validation

It does not implement or approve:

- new API route
- frontend panel
- UI trigger
- write flags
- receipt writing
- orchestration command invocation
- orchestration log writing
- orchestration receipt writing
- Codex Runner daemon/service integration
- native backend path mode
- adapter path rewrite
- Pi Loop invocation
- plan execution
- source mutation
- patch application
- provider execution
- Codexify ingestion
- receipt ingestion
- Execution Ledger writes
- WorkOrder mutation
- trust promotion
- reviewer auto-fill

## 4. Triggering Evidence

The live validate retry proof (`guardian-codex-runner-command-bus-live-validate-retry-proof.md`) reached the command-bus adapter but failed with:

```json
{
    "run_id": "run_ecf4b99e55ee4b7f",
    "status": "failed",
    "error": "[Errno 2] No such file or directory: PosixPath('/Volumes/Dev_SSD/Codex-Runner')"
}
```

The adapter's `subprocess.run(cwd=CODEX_RUNNER_ROOT)` failed because the working directory `/Volumes/Dev_SSD/Codex-Runner` does not exist inside the Docker container.

This is a host-path accessibility gap, not a bridge contract failure, command-bus lifecycle failure, or Codex Runner CLI failure.

## 5. Current Truth

What is true now:

- Codexify remains local-first beta hardening on `main`.
- The supported path remains local Docker Compose with local-only provider posture.
- Codex Runner owns the CLI Guardian preflight tools.
- Codexify has a typed bridge contract module, a JSON-only adapter, internal command-bus exposure for two preflight bridge commands, controlled proof tests, one blocked live validate proof, and one failed live validate retry proof.
- The bridge adapter expects Codex Runner at `/Volumes/Dev_SSD/Codex-Runner` inside the backend process.
- This contract adds an opt-in Docker visibility seam only.
- This contract does not prove live validation, live orchestration, UI integration, write flags, Pi Loop invocation, source mutation, Codexify ingestion, or durable mutation beyond command-bus run/event records.

## 6. Runtime Visibility Rule

The bridge adapter in `guardian/codex_runner_bridge/adapter.py` executes:

```python
subprocess.run(command, cwd=CODEX_RUNNER_ROOT, ...)
```

where `CODEX_RUNNER_ROOT = Path("/Volumes/Dev_SSD/Codex-Runner")`.

For this to work inside the Docker container, the host filesystem path `/Volumes/Dev_SSD/Codex-Runner` must be visible inside the container at the same exact path.

Without the mount, the backend container has no access to host-local filesystem paths and the adapter fails with a `FileNotFoundError` / `OSError`.

## 7. Compose Override

The override file is:

`docker-compose.codex-runner-bridge.yml`

It must be applied explicitly as an additional `-f` argument:

```bash
docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml up backend
```

It is never applied by default. It targets only the `backend` service.

## 8. Mount Contract

Exact mount declaration:

```yaml
services:
  backend:
    volumes:
      - ${CODEX_RUNNER_HOST_ROOT:-/Volumes/Dev_SSD/Codex-Runner}:${CODEX_RUNNER_CONTAINER_ROOT:-/Volumes/Dev_SSD/Codex-Runner}:ro
```

Mount properties:

- **Host path** (default): `/Volumes/Dev_SSD/Codex-Runner`
- **Container path** (default): `/Volumes/Dev_SSD/Codex-Runner`
- **Mode**: `ro` (read-only)
- **Configurable via env var**: `CODEX_RUNNER_HOST_ROOT` and `CODEX_RUNNER_CONTAINER_ROOT`
- **Scope**: `backend` service only
- **Opt-in**: must be explicitly included via `-f`

The mount is read-only. Codex Runner source must not be modified by the backend container under any circumstances.

## 9. Operator Startup Command

Start the backend with the Codex Runner visibility override:

```bash
docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml up backend
```

If the repo's current documented local startup command requires additional services or flags, include them while preserving the explicit override file. For example, a full stack startup with the override:

```bash
docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml up
```

## 10. Validation Command

Validate the mount is working inside the backend container:

```bash
docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml exec backend test -d /Volumes/Dev_SSD/Codex-Runner
```

Exit code 0 means the directory is visible. Exit code 1 means the mount is not working (host path not shared, Docker Desktop settings need adjustment, or Codex Runner checkout does not exist at the expected host path).

## 11. What This Enables

When the mount is active, the backend container can:

- see `/Volumes/Dev_SSD/Codex-Runner` at the exact path the bridge adapter expects
- execute `codexrun guardian validate-plan-pack` inside the Codex Runner root
- execute `codexrun guardian orchestrate-dry-run` inside the Codex Runner root
- return preflight results through the command-bus bridge

The command-bus lifecycle, manifest registration, and adapter logic remain unchanged. The mount fixes only the filesystem visibility seam.

## 12. What This Does Not Enable

This mount does NOT enable:

- live validate proof (requires a separate retry proof with the mount active)
- live orchestration proof (requires a separate explicit proof attempt)
- UI support (no Guardian UI panel exists for this bridge)
- write flags (all write flags remain disabled in this adapter slice)
- receipt writing (not supported in this adapter slice)
- orchestration log writing (not supported in this adapter slice)
- orchestration receipt writing (not supported in this adapter slice)
- Pi Loop invocation (authority locks remain false)
- source mutation (authority locks remain false; mount is read-only)
- Codexify ingestion (a separate adoption contract would be required)
- durable mutation beyond command-bus run/event records
- any change to the default docker-compose.yml

## 13. Failure Modes

| Failure | Cause | Operator action |
|---|---|---|
| `test -d` returns exit code 1 | Mount not working | Verify host path exists; check Docker Desktop File Sharing settings |
| Adapter still fails with `No such file or directory` | Mount path mismatch | Verify `CODEX_RUNNER_HOST_ROOT` and `CODEX_RUNNER_CONTAINER_ROOT` env vars match the actual host path |
| `codexrun` not found inside container | Codex Runner CLI not on PATH inside container | The bridge adapter uses a full path or relies on the binary being available at the mounted root; verify `codexrun` is installed at the expected location |
| Docker Desktop refuses to bind-mount the path | Path not in shared file list | Go to Settings → Resources → File Sharing and add `/Volumes/Dev_SSD` |

## 14. Security / Authority Boundary

This mount:

- is read-only (`:ro`)
- does not grant write access to Codex Runner source
- is opt-in (never applied by default)
- is local-only (no remote or hosted implication)
- stays within the existing backend container boundary

Authority locks remain false across all bridge responses:

```yaml
authority:
  guardian_operational: false
  plan_execution_allowed: false
  pi_loop_invocation_allowed: false
  codexify_ingestion_allowed: false
  durable_mutation_allowed: false
  provider_execution_allowed: false
  patch_application_allowed: false
  dispatch_allowed: false
  merge_allowed: false
```

## 15. Codex Runner Executable Availability

The mounted live validate proof (`guardian-codex-runner-command-bus-live-validate-mounted-proof.md`) showed that path visibility is solved (Codex Runner is visible at `/Volumes/Dev_SSD/Codex-Runner` inside the backend container) but `codexrun` was missing on the container PATH.

This task adds an opt-in executable availability seam in the bridge adapter (`guardian/codex_runner_bridge/adapter.py`) that supports explicit binary/module invocation modes:

- **binary mode** (default): invokes `codexrun` on PATH — preserves original behavior
- **module mode** (opt-in): invokes `python -m codex_runner ...` — uses the mounted source checkout without requiring a global `codexrun` binary

The opt-in compose override (`docker-compose.codex-runner-bridge.yml`) selects module mode for the local Docker backend:

```yaml
environment:
  CODEXRUN_INVOCATION_MODE: "module"
  CODEXRUN_PYTHON_BINARY: "python"
  CODEXRUN_MODULE: "codex_runner"
  PYTHONPATH: "/Volumes/Dev_SSD/Codex-Runner/src:/app"
```

Module mode uses argv-list command construction only:

```
python -m codex_runner guardian validate-plan-pack --path <plan_pack_path> --json
python -m codex_runner guardian orchestrate-dry-run --plan-pack <plan_pack_path> --require-receipt <receipt_path> --json
```

Invariants preserved:

- no shell execution is allowed (no `shell=True`, no whitespace in config tokens)
- no write flags are enabled
- no orchestration is authorized
- no live validation pass is claimed by this configuration alone
- a separate mounted live validate retry proof is still required

## 16. Future Live Validate Pass Slice

A live validate pass remains a future proof slice, not implied by this mount contract.

To prove live validation would require, at minimum:

- the mount contract applied and verified (this task)
- the backend running with the override active
- a real `codexrun` invocation to `internal::guardian.codex_runner.validate_plan_pack`
- a successful command-bus response with `inline_result.result = "pass"`

A separate retry proof document should record that attempt and its result.

## 17. Future Orchestration Slice

Live orchestration proof remains deferred.

A future orchestration slice would require, at minimum:

- a successful live validate proof
- a real validation receipt path
- an explicit separate proof attempt for `internal::guardian.codex_runner.orchestrate_dry_run_preflight`
- continued prohibition on write flags in this bridge slice unless separately approved

## 18. Forbidden Interpretations

Do not interpret this contract as meaning:

- live validation is proven
- live orchestration is proven
- Guardian UI integration is shipped
- the bridge supports write flags
- Pi Loop invocation is authorized
- source mutation is authorized
- Codexify ingestion is authorized
- the mount is applied by default
- this task proves preflight readiness end-to-end
- a validation receipt is execution authority
- an orchestration receipt is dispatch authority

## 19. Bottom Line

This contract adds an opt-in, read-only Docker Compose override that makes the host Codex Runner checkout visible to the Codexify backend container at `/Volumes/Dev_SSD/Codex-Runner`.

REQUIRED BOUNDARY:

```
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

It solves the filesystem visibility gap that blocked the live validate retry proof.

A mounted live validate proof attempt was run using this override. Result: [`FAIL`](./guardian-codex-runner-command-bus-live-validate-mounted-proof.md) — the filesystem mount worked but the `codexrun` binary was not available on the container PATH.

A module live validate proof was run using both the mount and module invocation. Result: [`PASS`](./guardian-codex-runner-command-bus-live-validate-module-proof.md) — `python -m codex_runner` through the mounted checkout produced a successful `validate-plan-pack` response with all authority locks false.

It does not prove live validation, live orchestration, UI integration, or any broader runtime capability. A live validate pass remains a separate future proof slice.
