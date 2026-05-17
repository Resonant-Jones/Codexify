# Supported-Profile / Catalog / Health Drift Proof Rerun After Runtime Wiring

- Artifact date: 2026-05-15
- Branch: `main`
- HEAD at proof start: `a7ecef63e05bfb243f2ed5c92be28920f2645ddb`
- Runtime path: local Docker Compose on the supported beta stack
- Proof window: 2026-05-15 08:45 EDT to 2026-05-15 08:49 EDT
- Result: `PASS`

## Purpose

Rerun the supported-profile / catalog / health drift proof after the runtime wiring repair and determine whether the remaining hold can be retired on the current `main` tip.

The answer from live evidence is yes: the supported profile is loaded in the Compose backend, `/health` and `/api/health/llm` expose aligned supported-profile state, `/health/chat` is healthy, `/api/llm/catalog` stays local-only by default, and `?include=all` remains diagnostic-only for unauthorized or unavailable cloud providers.

## Repo State

- Branch: `main`
- HEAD: `a7ecef63e05bfb243f2ed5c92be28920f2645ddb`
- Worktree: clean at proof start
- No unrelated in-flight changes were staged

## Repair Ancestry Note

The task-specified repair hash `9402ffad51926bc48a9921651ae695703ed24821` did not resolve as an ancestor in this checkout. The live runtime repair is present at current `HEAD` with the same commit message, `Align supported profile health and catalog truth`, and that repaired HEAD was used for the rerun.

## Exact Commands Run

### Repo state

- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short`
- `git log --oneline -5`
- `git merge-base --is-ancestor 9402ffad51926bc48a9921651ae695703ed24821 HEAD && echo supported_profile_runtime_wiring_repair_present`

### Supported local Compose stack

- `docker compose up -d db redis neo4j`
- `docker compose run --rm migrator`
- `docker compose up -d backend frontend worker-chat worker-coding worker-document-embed worker-chat-embed worker-warmup`
- `docker compose ps`

### Backend loaded-profile probe

- `docker compose exec -T backend python3 - <<'PY' ... PY`

The probe printed:
- `CODEXIFY_SUPPORTED_PROFILE=v1-local-core-web-mcp`
- `LOCAL_BASE_URL=http://host.docker.internal:11434/v1`
- `LLM_PROVIDER=local`
- `ALLOW_CLOUD_PROVIDERS=false`
- `CODEXIFY_LOCAL_ONLY_MODE=true`
- `profile_file_exists=true`
- `active_supported_profile.name=v1-local-core-web-mcp`
- `supported_profile_posture.valid=true`
- `supported_profile_posture.release_hold=false`
- `supported_profile_posture.selected_provider=local`
- `supported_profile_posture.selected_provider_supported=true`
- `supported_profile_posture.cloud_capable_configuration_present=false`

### Supported-profile config inspection

- `sed -n '1,220p' config/supported_profiles/v1-local-core-web-mcp.yaml`

### Live health / catalog surfaces

- `BASE=http://localhost:8888`
- `KEY="$(bash scripts/dev/dev-key.sh)"`
- `python3 - <<'PY' ... PY` with `urllib.request` to GET:
  - `/health`
  - `/health/chat`
  - `/api/health/llm`
  - `/api/llm/catalog`
  - `/api/llm/catalog?include=all`

### Validation

- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Supported-Profile Config Summary

`config/supported_profiles/v1-local-core-web-mcp.yaml` is the local-only beta contract.

- `LLM_PROVIDER: local`
- `ALLOW_CLOUD_PROVIDERS: false`
- `CODEXIFY_LOCAL_ONLY_MODE: true`
- `CODEXIFY_EGRESS_ALLOWLIST: ""`
- `LOCAL_BASE_URL: http://host.docker.internal:11434/v1`
- `command_bus` is internal-only
- `neo`, `imprint`, `system_prompt`, `system_docs`, `memory`, `agent`, `research`, `share`, `federation`, `collaboration`, `connectors`, `voice`, `flows`, `tools`, `api_tools`, `exports`, `codex`, `devtools`, `websocket`, `cron`, `ui_session`, `agent_orchestration`, and `agent_orchestration_chat` are quarantined
- graph-write release expansion is not declared

This manifest matches the local-first supported contract.

## Backend Loaded-Profile Evidence

The backend container loaded the supported-profile manifest successfully:

```json
{
  "env": {
    "CODEXIFY_SUPPORTED_PROFILE": "v1-local-core-web-mcp",
    "CODEXIFY_SUPPORTED_PROFILE_DIR": null,
    "LLM_PROVIDER": "local",
    "ALLOW_CLOUD_PROVIDERS": "false",
    "CODEXIFY_LOCAL_ONLY_MODE": "true",
    "LOCAL_BASE_URL": "http://host.docker.internal:11434/v1"
  },
  "profile_file": "/app/config/supported_profiles/v1-local-core-web-mcp.yaml",
  "profile_file_exists": true,
  "active_supported_profile": {
    "name": "v1-local-core-web-mcp",
    "surface": "local-docker-compose-webui",
    "version": 1
  },
  "supported_profile_posture": {
    "name": "v1-local-core-web-mcp",
    "version": 1,
    "surface": "local-docker-compose-webui",
    "valid": true,
    "mismatches": [],
    "selected_provider": "local",
    "selected_provider_supported": true,
    "cloud_capable_configuration_present": false,
    "release_hold": false,
    "expected_provider": "local"
  }
}
```

## Live Health Evidence

### `/health`

- `status: ok`
- `release_hold: false`
- `supported_profile.name: v1-local-core-web-mcp`
- `supported_profile.valid: true`
- `supported_profile.release_hold: false`
- `supported_profile.selected_provider: local`
- `supported_profile.selected_provider_supported: true`
- `supported_profile.cloud_capable_configuration_present: false`

### `/health/chat`

- `status: healthy`
- `details: null`
- Queue and worker posture remained healthy enough for the supported path

### `/api/health/llm`

- `status: ok`
- `release_hold: false`
- `details.provider: local`
- `details.supported_profile.name: v1-local-core-web-mcp`
- `details.supported_profile.valid: true`
- `details.supported_profile.release_hold: false`
- `details.provider_truth.supported_profile_name: v1-local-core-web-mcp`
- `details.provider_truth.supported_profile_valid: true`
- `details.provider_truth.supported_profile_approved: true`
- `details.provider_truth.cloud_capable_configuration_present: false`

### `/api/llm/catalog`

- `provider_ids: ["local"]`
- local provider:
  - `authorized: true`
  - `available: true`
  - `enabled: true`
  - `truth.supported_profile_name: v1-local-core-web-mcp`
  - `truth.supported_profile_approved: true`
  - `truth.cloud_capable_configuration_present: false`

### `/api/llm/catalog?include=all`

- `provider_ids: ["openai", "anthropic", "gemini", "groq", "alibaba", "minimax", "local"]`
- cloud providers were diagnostic inventory only:
  - `authorized: false`
  - `available: false`
  - `enabled: false`
  - `disabled_reason: "Missing provider credentials"`
- local remained:
  - `authorized: true`
  - `available: true`
  - `enabled: true`
  - `truth.supported_profile_approved: true`

The live catalog stayed local-only by default, and the diagnostic inventory did not imply cloud beta support.

## Drift Comparison

| Surface | Observation | Alignment |
|---|---|---|
| Supported-profile manifest file | Local-only beta contract with local provider, cloud disabled, and local-only egress posture | Aligns with release claim |
| Backend-loaded profile | Manifest loaded from `/app/config/supported_profiles/v1-local-core-web-mcp.yaml` and active in runtime | Aligns with manifest |
| Live `/health` | `release_hold=false`, non-null supported-profile state, local-only posture | Aligns with manifest |
| Live `/health/chat` | Healthy queue/worker posture | Aligns with supported Compose expectations |
| Live `/api/health/llm` | Non-null supported-profile state, local provider, `release_hold=false` | Aligns with manifest |
| Live `/api/llm/catalog` | Local provider only | Aligns with local-only promise |
| Live `/api/llm/catalog?include=all` | Cloud providers shown only as unauthorized/unavailable/disabled diagnostic inventory | Aligns with operator diagnosis, not beta support |
| Provider-truth cloud capability | Explicit cloud capability is `false` under the local-only Compose contract | Aligns with supported-profile posture |

### Drift verdict

No meaningful drift remains on the current `main` tip.

- The supported profile manifest is loaded in the live backend.
- `/health` and `/api/health/llm` expose non-null supported-profile state.
- The catalog remains local-only by default.
- `?include=all` remains diagnostic-only for unsupported cloud providers.
- The live health and catalog surfaces agree with the supported-profile beta contract.

## No-Authority-Widening Evidence

No unsupported authority was widened during this proof:

- No Command Center dispatch endpoint was called
- No lease allocation from UI occurred
- No terminal execution from UI occurred
- No plugin runtime was activated
- No merge automation occurred
- No graph-write release claim was widened
- No cloud-provider beta support was claimed

## Validation Results

- Live proof rerun completed successfully on the supported Compose stack
- Documentation validation passed:
  - `./.venv/bin/python scripts/validate_docs.py`
- Diff hygiene passed:
  - `git diff --check`

The earlier implementation repair had already validated the targeted health/provider tests. This rerun focused on live runtime truth plus docs hygiene.

## Final Result

`PASS`

The current `main` tip justifies retiring the supported-profile / catalog / health drift hold in `docs/architecture/00-current-state.md`.

## Explicit Non-Claims

- This proof does not claim cloud-provider beta support.
- This proof does not claim packaged desktop replaces the supported local Compose path.
- This proof does not claim command bus / delegation / federation / graph-write release expansion.
- This proof does not claim UI dispatch.
- This proof does not claim lease allocation from UI.
- This proof does not claim terminal execution from UI.
- This proof does not claim plugin runtime.
- This proof does not claim merge automation.
- This proof does not claim live MiniMax/Codex successful execution from Command Center.
- This proof does not generalize this result to future runtime changes without renewed proof.
