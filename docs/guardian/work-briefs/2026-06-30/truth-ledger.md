# Guardian Work Brief - Truth Ledger - 2026-06-30

## Evidence Gathered
- Generator command path: `make guardian-brief` -> `python3 scripts/guardian/generate_work_brief.py`.
- Repo root: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`
- Branch: `HEAD`
- HEAD: `29dd77beac21`
- Upstream: No upstream configured
- Status command captured before writing files: `git status --short --branch --untracked-files=all`
- Expected architecture file presence was checked.
- `docs/architecture/00-current-state.md` was read as the release-truth boundary.
- `docs/architecture/README.md` was checked as the architecture KB entrypoint.

Status snapshot:

```text
## HEAD (no branch)
M  docs/architecture/README.md
M  docs/collaborators/zac/README.md
M  docs/collaborators/zac/agent-startup-prompt.md
A  docs/collaborators/zac/report-only-agent-lenses.md
A  docs/collaborators/zac/report-output-templates.md
A  docs/collaborators/zac/report-request-prompts.md
M  docs/collaborators/zac/source-map.md
```

Architecture file presence:
- `docs/architecture/00-current-state.md`: present
- `docs/architecture/README.md`: present
- `docs/architecture/adr/ADR Index.md`: missing
- `docs/architecture/adr/adr-index.md`: present
- `docs/architecture/agent-protocol-operations.md`: present
- `docs/architecture/config-and-ops.md`: present

## Proven
- The generator resolved a local git checkout.
- The generator captured branch, HEAD, upstream, ahead/behind when available, dirty state, and expected architecture file presence before writing.
- The generator wrote the four canonical Guardian Work Brief markdown files for `2026-06-30`.
- The current-state document remains the release-truth boundary for interpreting this packet.

Current supported reality copied only as documentary context:
- Local Docker Compose remains the supported install path.
- The supported posture remains local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- `AI_BACKEND=local` is legacy compatibility only.
- `LOCAL_RUNTIME_PRESET` still selects `whooshd-mlx`, `ollama`, `lmstudio`, or `custom-openai-compatible` under the local provider boundary.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Chat completion, upload -> embed -> readback, and workspace-local retrieval remain the supported beta paths.
- OpenAI export import and Task Prompt Archive are present on `main`.
- Live model availability is still proven only by inventory from `/v1/models` or `/api/tags`.
- `GET /health`, `GET /health/chat`, and `GET /api/health/llm` remain the fastest runtime checks.
- Graph writes remain default-off on the supported Compose path.
- The Continuity operator surface is test-only, API-key-gated, and profile-quarantined under `test-continuity`.

## Code-Path Only / Not Re-Proven Today
- No backend runtime path was exercised.
- No queue, worker, provider, Redis, Postgres, frontend, SSE, browser, Docker Compose, or model runtime path was tested.
- No marketing generation, daily audit generation, heartbeat bundle generation, public export generation, or release machinery was invoked.
- Any runtime capability mentioned here remains documentary context unless backed by a separate supported-path proof.

## Blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- OpenAI import coverage and embedding deferral still need ongoing regression proof.

## Changed Files From This Run
- docs/guardian/work-briefs/2026-06-30/axis-brief.md
- docs/guardian/work-briefs/2026-06-30/codex-next-task-packet.md
- docs/guardian/work-briefs/2026-06-30/truth-ledger.md
- docs/guardian/work-briefs/2026-06-30/decision-log.md
