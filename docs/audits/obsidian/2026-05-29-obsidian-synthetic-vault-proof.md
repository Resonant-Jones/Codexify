# Obsidian Synthetic Vault Proof

## Scope

This is the first synthetic-vault proof attempt for `/obsidian` workspace-context behavior on the primary Guardian chat surface.

This proof does not use the operator's real Obsidian vault. It does not promote Obsidian as required for normal chat completion, and it does not widen Codexify release posture.

Initial result: `PARTIAL`. Host Obsidian preflight passed on the first rerun, but that live proof stopped at the Codexify Obsidian config/index seam because `/api/obsidian/*` was not mounted under the active supported profile.

Latest rerun result after supported-profile repair: `PASS`. See [Rerun After Supported-Profile Repair](#rerun-after-supported-profile-repair).

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

## Rerun After Supported-Profile Repair

### Scope

This rerun occurred after commit `539d3d1830a9b29c0a8d295582b09b8d39f22794`, which enabled the existing Obsidian router in the supported local profile.

This rerun tests the synthetic-vault path after the Obsidian route/profile repair. It does not use the operator's real vault, does not add runtime behavior, and does not widen release posture beyond the already documented workspace-local Obsidian path.

### Repository and Runtime

- Working directory: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Branch: `codex/fix-chat-slash-commands`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- HEAD before proof: `539d3d1830a9b29c0a8d295582b09b8d39f22794`
- Dirty/untracked files before proof: none
- Proof timestamp/window: `2026-05-30T04:22Z` through `2026-05-30T04:29Z`
- Docker Compose services used: `db`, `redis`, `neo4j`, `migrator`, `backend`, `worker-chat`, `worker-chat-embed`, `worker-document-embed`

Safety gate commands run before proof:

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
git show --name-only --stat 539d3d1830a9b29c0a8d295582b09b8d39f22794
git show --name-only --stat eae61213a55353ad1ff1a3ba81c856daf1da5e8e
git show --name-only --stat 5fa5340bc99a5634550b7d90d612229281676f56
```

Safety gate result:

- `pwd`: `/Volumes/Dev_SSD/Codexify-main`
- Git root: `/Volumes/Dev_SSD/Codexify-main`
- Remote: `origin https://github.com/Resonant-Jones/Codexify.git`
- Branch: `codex/fix-chat-slash-commands`
- Status: clean
- Commit `539d3d1830a9b29c0a8d295582b09b8d39f22794` changed only the supported-profile manifest and supported-profile tests.
- Commits `eae61213a55353ad1ff1a3ba81c856daf1da5e8e` and `5fa5340bc99a5634550b7d90d612229281676f56` changed only this proof artifact.
- Temp vault commit check found no committed `/private/tmp` or `/tmp` vault files. Sentinel strings appear only in Obsidian audit docs; `git ls-files` showed no synthetic vault files.

Runtime setup commands:

```bash
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend worker-chat worker-chat-embed worker-document-embed
```

### Host Preflight

Host Obsidian install checks:

```bash
test -d /Applications/Obsidian.app && echo "Obsidian app found"
mdfind "kMDItemCFBundleIdentifier == 'md.obsidian'" | head -5
```

Observed result:

- `/Applications/Obsidian.app` was present and printed `Obsidian app found`.
- Spotlight returned no `md.obsidian` bundle paths.

Host preflight is satisfied for this proof because the installed app bundle exists. The empty Spotlight result is recorded as a host-indexing nuance.

### Route/Profile Posture

Live route/profile evidence:

- `GET /health`: `status=ok`
- `GET /health/chat`: `status=healthy`
- `GET /api/health/llm`: `status=ok`
- `GET /api/health/retrieval`: `status=ready`, `proof_capable=true`
- `GET /openapi.json` exposed:
  - `/api/obsidian/config`
  - `/api/obsidian/index`
  - `/api/obsidian/preview`
- Authenticated `GET /api/obsidian/config` reached the mounted route and returned structured `404` detail:

```json
{"detail":{"error":"obsidian_config_missing"}}
```

Generic absent-router 404 is gone. The remaining `404` before configuration is the route-level "no config yet" state.

### Synthetic Vault

Synthetic vault created outside the repo:

- Host path: `/private/tmp/codexify-obsidian-synthetic-vault-2026-05-29-rerun-20260530T042624Z`
- Backend container copy: `/tmp/codexify-obsidian-synthetic-vault-2026-05-29-rerun-20260530T042624Z`

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
- The temp vault remains under `/private/tmp`; the backend container copy remains under container `/tmp` for inspection.

### Config and Indexing

Config route used:

```http
PUT /api/obsidian/config
```

Safe payload shape:

```json
{
  "vault_root": "/tmp/codexify-obsidian-synthetic-vault-2026-05-29-rerun-20260530T042624Z",
  "allowed_paths": null,
  "allowed_tags": null
}
```

Config result:

- `status=200`
- Stored connector: `obsidian_local`
- Stored type: `obsidian`
- Stored vault root: `/tmp/codexify-obsidian-synthetic-vault-2026-05-29-rerun-20260530T042624Z`
- Stored allowed paths/tags normalized to empty lists.

Preview route result:

- `POST /api/obsidian/preview`
- `note_count=3`
- `scanned=3`
- `failures=[]`
- sample paths included all three synthetic markdown files.

Index route result:

- `POST /api/obsidian/index`
- `indexed=3`
- `scanned=3`
- `failures=[]`
- `indexed_at=2026-05-30T04:26:24.674983+00:00`
- `deleted=1`

Caveat: Obsidian indexing currently uses a full namespace rebuild for `obsidian:local`. The route reported `deleted=1` before indexing the three synthetic notes. No existing non-synthetic Obsidian config was present before this proof; the pre-config route state was `obsidian_config_missing`.

Readback/retrieval readiness:

- `GET /api/health/retrieval?q=SENTINEL_OBSIDIAN_FIXTURE_2026_05_29&namespace=obsidian:local&k=5`: `match_count=3`
- `GET /api/health/retrieval?q=SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29&namespace=obsidian:local&k=5`: `match_count=3`
- `GET /api/health/retrieval?q=SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29&namespace=obsidian:local&k=5`: `match_count=3`

The returned matches were in namespace `obsidian:local` and referenced the synthetic container vault path.

### Slash Command Completion Proof

CLI/API proof simulated the frontend payload shape:

- The persisted user message used the post-command query text.
- The completion request carried sanitized `slashIntent`.
- The completion request carried top-level `contextDirectives`.
- The completion request used `source_mode=obsidian_only`.

Proof thread:

- Thread ID: `3`
- Title/summary: `obsidian-synthetic-vault-proof-2026-05-29`

Question 1:

- Raw slash input: `/obsidian What is the correct answer for SENTINEL_OBSIDIAN_FIXTURE_2026_05_29?`
- Persisted source message content: `What is the correct answer for SENTINEL_OBSIDIAN_FIXTURE_2026_05_29?`
- Source message ID: `15`
- Task ID: `1c256e9d-3dd9-4042-80d1-0cbf803e1826`
- Terminal event: `task.completed`
- Assistant message ID: `16`
- Assistant answer summary: answered `lantern valve`.
- Local evidence: yes. The terminal payload reported `connector_context_count=3`, `connector_context_injected=true`, `retrieval_injected=true`, `obsidian_count=3`, and `source_mode=obsidian_only`.
- Guardian avoided "I do not recognize /obsidian": yes.

Question 2:

- Raw slash input: `/obsidian According to SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29, what remains the canonical user-facing transcript?`
- Persisted source message content: `According to SENTINEL_OBSIDIAN_ARCHITECTURE_2026_05_29, what remains the canonical user-facing transcript?`
- Source message ID: `17`
- Task ID: `6998a12e-55fd-46be-a4e6-20295fe577a8`
- Terminal event: `task.completed`
- Assistant message ID: `18`
- Assistant answer summary: answered that the chat thread remains the canonical user-facing transcript.
- Local evidence: yes. The terminal payload reported `connector_context_count=3`, `connector_context_injected=true`, `retrieval_injected=true`, `obsidian_count=3`, and `source_mode=obsidian_only`.
- Exact expected phrase check: partial. The answer was grounded and semantically aligned, but it did not repeat the exact phrase `source thread remains truth`.
- Guardian avoided "I do not recognize /obsidian": yes.

Question 3:

- Raw slash input: `/obsidian According to SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29, what does /obsidian grant?`
- Persisted source message content: `According to SENTINEL_OBSIDIAN_BOUNDARY_2026_05_29, what does /obsidian grant?`
- Source message ID: `19`
- Task ID: `5fb667c8-0aee-4a6f-aad3-c02c0a8695b4`
- Terminal event: `task.completed`
- Assistant message ID: `20`
- Assistant answer summary: answered that `/obsidian` activates local workspace context only and does not grant arbitrary MCP, command bus, or external tool access.
- Local evidence: yes. The terminal payload reported `connector_context_count=3`, `connector_context_injected=true`, `retrieval_injected=true`, `obsidian_count=3`, and `source_mode=obsidian_only`.
- Exact expected phrase check: partial. The answer was grounded and semantically aligned, but it did not repeat the exact phrase `local context only`.
- Guardian avoided "I do not recognize /obsidian": yes.

### Trace / Retrieval Evidence

Task event evidence:

- All three `/obsidian` completions reached `task.completed`.
- All three terminal payloads reported local provider execution under supported profile `v1-local-core-web-mcp`.
- All three terminal payloads reported `connector_context_count=3`, `connector_context_injected=true`, and `retrieval_injected=true`.
- All three terminal payloads reported `source_mode=obsidian_only` and same-user retrieval posture.

Persisted assistant evidence:

- Assistant messages persisted as IDs `16`, `18`, and `20` in source thread `3`.
- None of the persisted assistant messages claimed `/obsidian` was unrecognized.
- At least one persisted answer exactly contained the sentinel answer from local evidence: `lantern valve`.

Debug evidence:

- `GET /api/chat/debug/rag-trace/3/latest` returned `200` during proof inspection.
- `GET /api/chat/debug/retrieval-posture/3/latest` returned same-user `obsidian_only` posture for the first two proof turns.
- The latest retrieval-posture debug endpoint returned an empty state after the third proof turn; the terminal `task.completed` payload remains the stronger evidence surface for executed retrieval posture.

### Negative Control

Negative-control thread:

- Thread ID: `4`
- Prompt: `Without using a slash command, what is the correct answer for SENTINEL_OBSIDIAN_FIXTURE_2026_05_29?`
- Source message ID: `21`
- Completion source mode: `project`
- Task ID: `b9a62044-6274-4f48-8294-9ba9f41809c0`
- Terminal event: `task.completed`
- Assistant message ID: `22`

Observed behavior:

- The assistant did not answer `lantern valve`.
- The assistant said it did not have internal reference or context for the sentinel and asked for more background.
- Terminal payload reported `connector_context_count=0`, `connector_context_injected=false`, `obsidian_count=0`, and `obsidian_injected=false`.

Local Obsidian evidence was avoided for the non-slash control prompt.

### What This Rerun Does Not Prove

- Not a real personal vault proof.
- Not broad MCP/tool access.
- Not command-bus activation.
- Not GitHub context.
- Not release promotion.
- Not complete connector ecosystem proof.
- Not proof that every vault shape or indexing mode works.
- Not proof that Obsidian is required for normal chat completion.
- Not proof that exact-answer wording is guaranteed across all local models.

### Caveats

- Spotlight did not return an `md.obsidian` bundle path even though `/Applications/Obsidian.app` exists.
- Local HTTP probes from the sandbox required elevated permissions to reach `127.0.0.1:8888`.
- The proof used a temporary helper script at `/private/tmp/codexify_obsidian_rerun_probe.py`; no probe helper was committed.
- The synthetic vault remains under `/private/tmp`, and its backend container copy remains under container `/tmp` for inspection.
- Obsidian indexing is a full namespace rebuild and reported `deleted=1` before indexing the synthetic notes.
- The second and third `/obsidian` answers were grounded in local evidence but did not repeat the exact expected answer strings.
- The debug retrieval-posture endpoint was weaker than the terminal task payload for the final proof turn.
- Known unrelated source-mode tests have broader failures when run with `-k "slash or obsidian or context"` due an existing memory-preselection trace signature issue; the required `-k slash` slice passed in the previous proof and is rerun below for this artifact.

### Validation

Validation commands for this rerun:

```bash
./.venv/bin/pytest -v tests/core/test_supported_profile.py tests/core/test_supported_profile_quarantine.py tests/routes/test_obsidian_routes.py
./.venv/bin/pytest -v tests/core/test_obsidian_only_retrieval.py
./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py
./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k slash
python3 scripts/validate_docs.py
git diff --check
```

Validation results:

- `./.venv/bin/pytest -v tests/core/test_supported_profile.py tests/core/test_supported_profile_quarantine.py tests/routes/test_obsidian_routes.py` - 10 passed, 4 warnings.
- `./.venv/bin/pytest -v tests/core/test_obsidian_only_retrieval.py` - 2 passed.
- `./.venv/bin/pytest -v tests/core/test_chat_completion_service_context_directives.py` - 11 passed.
- `./.venv/bin/pytest -v tests/routes/test_chat_context_directives.py` - 11 passed, 4 warnings.
- `./.venv/bin/pytest -v tests/routes/test_chat_source_mode.py -k slash` - 6 passed, 12 deselected, 4 warnings.
- `python3 scripts/validate_docs.py` - passed.
- `git diff --check` - passed.

### Final Result

`PASS`

The rerun satisfies the proof gate:

- Obsidian host preflight is satisfied.
- The synthetic markdown vault exists outside the repo.
- Obsidian routes are mounted under the supported local profile.
- Codexify config/index routes succeeded for the synthetic vault.
- `/obsidian` completion path ran through queue-backed Guardian chat.
- All three `/obsidian` completions reached `task.completed`.
- At least one sentinel answer was exactly grounded in local evidence.
- All three `/obsidian` answers used injected local synthetic evidence.
- Guardian did not claim `/obsidian` was unrecognized.
- The negative control did not receive local Obsidian evidence.
- No release posture was widened.
