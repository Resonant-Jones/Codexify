# Guardian Work Brief - Truth Ledger - 2026-06-12

## Evidence Gathered
- Generator command path: `make guardian-brief` -> `python3 scripts/guardian/generate_work_brief.py`.
- Repo root: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`
- Branch: `codex/guardian-work-brief`
- HEAD: `21cc2131ea20`
- Upstream: origin/codex/guardian-work-brief; ahead 0, behind 0
- Status command captured before writing files: `git status --short --branch --untracked-files=all`
- Expected architecture file presence was checked.
- `docs/architecture/00-current-state.md` was read as the release-truth boundary.
- `docs/architecture/README.md` was checked as the architecture KB entrypoint.

Status snapshot:

```text
## codex/guardian-work-brief...origin/codex/guardian-work-brief
?? docs/guardian/work-briefs/2026-06-11/axis-brief.md
?? docs/guardian/work-briefs/2026-06-11/codex-next-task-packet.md
?? docs/guardian/work-briefs/2026-06-11/decision-log.md
?? docs/guardian/work-briefs/2026-06-11/truth-ledger.md
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
- The generator wrote the four canonical Guardian Work Brief markdown files for `2026-06-12`.
- The current-state document remains the release-truth boundary for interpreting this packet.

Current supported reality copied only as documentary context:
- Local Docker Compose remains the supported install path.
- The supported posture is local-only: `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`, `LLM_PROVIDER=local`.
- The current Apple Silicon default local inference target is Whoosh'd/OpenAI-compatible. The setup wizard defaults to Ollama on non-Mac machines when no preset is selected.
- Live model availability is proven only when `/v1/models` or `/api/tags` advertises the selected local model.
- Health checks report LLM model availability.
- Chat completion works on the supported path and persists back into the source thread.
- Upload -> embed -> readback works on the supported path.
- Workspace-local Obsidian retrieval is supported on the current tip.
- Coding results return through Guardian into the source thread on the supported path.
- Graph writes remain default-off on the supported Compose path.
- Provider timeout and slow-path failures are classified and presented more accurately in the UI.

## Code-Path Only / Not Re-Proven Today
- No backend runtime path was exercised.
- No queue, worker, provider, Redis, Postgres, frontend, SSE, browser, Docker Compose, or model runtime path was tested.
- No marketing generation, daily audit generation, heartbeat bundle generation, public export generation, or release machinery was invoked.
- Any runtime capability mentioned here remains documentary context unless backed by a separate supported-path proof.

## Blockers
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- Legacy `/tools` behavior still overlaps with the command bus.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains a high-blast-radius area with trust-policy and egress sensitivity.
- Docs-heavy merged work does not remove the need to recheck runtime proof on the supported path.

## Changed Files From This Run
- docs/guardian/work-briefs/2026-06-12/axis-brief.md
- docs/guardian/work-briefs/2026-06-12/codex-next-task-packet.md
- docs/guardian/work-briefs/2026-06-12/truth-ledger.md
- docs/guardian/work-briefs/2026-06-12/decision-log.md
