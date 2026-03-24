

# TASK_2026_03_24_06_restore_docker_to_local_ollama_accessibility

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Fix local Ollama provider connectivity from the Codexify runtime so “on-my-machine” Ollama is reachable from the app when running in Docker on macOS.

This change belongs in:

- provider configuration files
- Docker compose / runtime env files
- backend provider adapter/config resolution for Ollama
- tests covering provider base URL resolution where available
- docs if a runtime note is required

## Goal

Local-machine Ollama must be reachable deterministically from the Dockerized backend without requiring manual intervention or environment-specific hacks.

Vault node behavior must remain unchanged and separate.

## Required Behavior

1. Determine the canonical local Ollama URL resolution path used by backend/provider config.

2. Ensure Dockerized backend can reach host Ollama on macOS:
   - support Docker Desktop host bridging (e.g. `host.docker.internal` if applicable)
   - avoid hardcoded localhost assumptions inside containers

3. Support a clear env-configurable base URL for local Ollama:
   - allow override via environment variable
   - document expected variable name and behavior

4. Implement deterministic fallback behavior:
   - attempt configured URL first
   - fallback to known host bridge resolution if appropriate
   - do not silently fail

5. On failure:
   - emit clear diagnostics
   - do not silently exclude the provider from catalog

6. Do not conflate local Ollama with remote vault-node Ollama:
   - maintain explicit separation in config and resolution logic

## Files to Modify

List all files before changes. Likely candidates include:

- `docker-compose.yml` or related compose/env files
- backend provider config files
- provider adapter files
- provider tests
- relevant docs

## Run Tests

Run based on scope:

### Backend

```bash
pytest -v
```

### If frontend provider catalog logic is also modified

```bash
pnpm test
```

Also include a manual verification note in output:

- local Ollama reachable from backend container
- provider appears in catalog as expected

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Fix local Ollama connectivity in Docker runtime"
```

## Output Must Include

- Summary of changes
- Files modified
- Config/provider logic touched
- Test results
- Manual verification result
- Git commit hash
