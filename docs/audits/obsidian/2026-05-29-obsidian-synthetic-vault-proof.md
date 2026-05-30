# Obsidian Synthetic Vault Proof

## Scope

This is the first synthetic-vault proof attempt for `/obsidian` workspace-context behavior on the primary Guardian chat surface.

This proof does not use the operator's real Obsidian vault. It does not promote Obsidian as required for normal chat completion, and it does not widen Codexify release posture.

Result: `PARTIAL`. Host Obsidian preflight passed on rerun, but the live proof stopped at the Codexify Obsidian config/index seam because `/api/obsidian/*` is not mounted under the active supported profile.

## Repository and Runtime

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before rerun: `5fa5340bc99a5634550b7d90d612229281676f56`
- Dirty/untracked files before rerun: none
- Proof timestamp/window: `2026-05-30T01:12:07Z` through `2026-05-30T01:16Z`
- Docker Compose services used: `db`, `redis`, `neo4j`, `migrator`, `backend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`
- Runtime refresh: `backend`, `worker-chat`, `worker-chat-embed`, and `worker-document-embed` were restarted before proof probes.

Safety gate commands run before proof:

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
```

Safety gate result:

- `pwd`: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- Branch: `codex/fix-chat-slash-commands`
- Status: clean

Runtime setup commands:

```bash
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-chat-embed worker-document-embed
docker compose restart backend worker-chat worker-chat-embed worker-document-embed
```

Health results:

- `GET /health` - `status=ok`, `release_hold=false`, supported profile valid.
- `GET /health/chat` - `status=healthy`, Redis ok, queue depth 0, worker heartbeat fresh.
- `GET /api/health/llm` - `status=online`, local provider selected.
- `GET /api/health/retrieval` - `status=ready`, `proof_capable=true`, backend search runtime matches worker write runtime.

## Host Preflight

Host Obsidian install checks:

```bash
test -d /Applications/Obsidian.app && echo "Obsidian app found"
mdfind "kMDItemCFBundleIdentifier == 'md.obsidian'" | head -5
```

Observed result:

- `/Applications/Obsidian.app` was present and printed `Obsidian app found`.
- Spotlight returned no `md.obsidian` bundle paths.

Host preflight is satisfied for this proof because the installed app bundle exists. The empty Spotlight result is recorded as a host-indexing nuance, not as the proof blocker.

## Synthetic Vault

Synthetic vault created outside the repo:

- Host path: `/private/tmp/codexify-obsidian-synthetic-vault-2026-05-29-rerun-011207Z`
- Backend container copy: `/tmp/codexify-obsidian-synthetic-vault-2026-05-29-rerun-011207Z`

Synthetic files:

- `plumbing-fixture-note.md`
- `codexify-architecture-note.md`
- `boundary-note.md`

Sentinel strings:

- `SENTINEL_OBSIDIAN_FIXTURE_2026_05_29`
- `SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29`
- `SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29`

Vault handling:

- The synthetic vault was not inside the repo.
- No personal notes, secrets, client material, screenshots, or local vault contents were used.
- No vault files were committed.
- The temp vault remains under `/private/tmp`; the backend container copy remains under container `/tmp` for inspection until cleanup or container restart.

## Ingestion / Linking Path

Intended supported path:

- Configure Obsidian vault root with `PUT /api/obsidian/config`.
- Trigger indexing with `POST /api/obsidian/index`.
- Verify search/readiness through `/api/health/retrieval`.
- Run queue-backed chat completion and inspect persisted assistant messages plus task-event retrieval posture.

Observed route evidence:

```bash
PUT /api/obsidian/config
```

Result:

```json
{"detail":"Not Found"}
```

OpenAPI route inspection returned no mounted Obsidian paths:

```json
{
  "obsidian_paths": []
}
```

Backend route-registration logs show the reason:

```text
[routers] quarantined obsidian (supported_profile=v1-local-core-web-mcp)
```

No indexing was run. No project/thread binding, document IDs, or Obsidian readiness evidence were produced because the current supported profile does not expose `/api/obsidian/config` or `/api/obsidian/index`.

## Slash Command Proof

The `/obsidian` chat questions were not submitted in this rerun because the synthetic vault could not be configured or indexed through the supported Codexify path.

Planned questions remained:

- `/obsidian What is the correct answer for SENTINEL_OBSIDIAN_FIXTURE_2026_05_29?`
- `/obsidian According to SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29, what remains the canonical user-facing transcript?`
- `/obsidian According to SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29, what does /obsidian grant?`

No source message IDs, task IDs, assistant message IDs, or assistant answer summaries exist for these questions in this run.

Frontend/backend seam status from pre-read:

- Frontend slash parsing recognizes `/obsidian` and sends sanitized `slashIntent` plus top-level `contextDirectives`.
- Backend chat route accepts `slashIntent` and Obsidian context directives.
- Prompt assembly contains bounded active Obsidian context guidance when the Obsidian directive/intent is active.
- The missing live proof seam is not slash parsing or prompt guidance; it is the route/profile posture for Obsidian vault config/index.

## Trace / Retrieval Evidence

No task event evidence, persisted assistant metadata, debug RAG trace, or retrieval readback evidence was produced for the sentinel questions.

Evidence caveat: the absence of trace evidence is expected because the proof stopped before ingestion and before chat completion. Vector-store searchability was not treated as equivalent to completion-time influence.

## Negative Control

The normal non-Obsidian control prompt was not submitted.

No behavior was observed for the negative control in this run.

## What This Proof Does Not Prove

- Not a real personal vault proof.
- Not broad MCP/tool access.
- Not command-bus activation.
- Not GitHub context.
- Not release promotion.
- Not complete connector ecosystem proof.
- Not proof that every vault shape or indexing mode works.
- Not proof that `/obsidian` completion succeeds on this host.
- Not proof that local Obsidian config/index is available under the active supported profile.

## Caveats

- The host Obsidian app bundle is installed, but Spotlight did not return a bundle identifier path.
- Local HTTP probes from the sandbox could not reach `127.0.0.1:8888`; local backend HTTP calls were rerun with elevated sandbox permissions.
- `scripts/dev/dev-key.sh` was not executable directly; probes used `sh scripts/dev/dev-key.sh`.
- The Obsidian route exists in source code, but the active supported profile quarantines the `obsidian` route label.
- This is a supported-profile/route-posture blocker, not evidence that local vault indexing failed.
- The synthetic vault was copied to backend container `/tmp`, but indexing was not attempted after route discovery returned 404.

## Validation

Validation commands for this docs/proof artifact:

```bash
./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k slash
python3 scripts/validate_docs.py
git diff --check
```

Validation results:

- `./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py` - 11 passed.
- `./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py` - 11 passed, 4 warnings.
- `./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k slash` - 6 passed, 12 deselected, 4 warnings.
- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

## Final Result

`PARTIAL`

The proof cannot reach `PASS` because the active supported profile quarantines the Obsidian control-plane route required to configure and index the synthetic vault. The next architecture-impacting slice should reconcile the current-truth statement that workspace-local Obsidian retrieval is supported with the live supported-profile route posture for `obsidian`.
