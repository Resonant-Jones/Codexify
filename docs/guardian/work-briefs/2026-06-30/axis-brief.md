# Guardian Work Brief - Axis Brief - 2026-06-30

## Scope
Restore and use the repeatable Guardian Work Brief generation path for 2026-06-30. This packet is reporting-only. It does not generate marketing packets, daily audits, heartbeat bundles, public exports, release claims, or runtime proof.

## Current Workspace State
- Repo root: `/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main`
- Branch: `HEAD`
- Head: `29dd77beac21`
- Upstream: No upstream configured
- Status command: `git status --short --branch --untracked-files=all`

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

Expected architecture files:
- `docs/architecture/00-current-state.md`: present
- `docs/architecture/README.md`: present
- `docs/architecture/adr/ADR Index.md`: missing
- `docs/architecture/adr/adr-index.md`: present
- `docs/architecture/agent-protocol-operations.md`: present
- `docs/architecture/config-and-ops.md`: present

## Runtime Truth Boundary
`docs/architecture/00-current-state.md` remains the short-horizon authority for supported release truth. Runtime paths were not re-proven by this generator.

Current phase from the truth boundary:

> Codexify remains in local-first beta hardening on `main`. The supported path is still the local Docker Compose stack with local-only provider posture. Recent merged work is concentrated on operator-surface documentation, profile-supported runtime clarification, and quarantined continuity proof, not on widening the supported beta surface.

Do not widen release claims from this packet:
- Do not assume cloud-provider beta support.
- Do not assume the packaged desktop shell replaces the local Compose supported path.
- Do not assume the collab chat identity contract or personal-facts guardrails are release-proven runtime behavior from docs alone.
- Do not assume Scout/iOS contract docs mean shipped Scout runtime support.
- Do not assume the Turn Intake Compiler contract means a live runtime intake classifier, action router, retrieval-router integration, or model-prompt packet builder is implemented.
- Do not assume the Turn Intake Fixture Pack means executable tests exist.
- Do not assume the Turn Intake Token Domain Proposal means turn-intake runtime tokens, registries, or classifier behavior exist.
- Do not assume command bus, delegation, federation, or graph-write surfaces are part of the present release promise.
- Do not assume the Guardian delegation loop contract means the end-to-end delegation loop is shipped.
- Do not assume the Continuity operator surface is supported beta, user-facing, Project Pulse, export/restore, graph, chat runtime, worker, or command bus behavior.
- Do not assume any local runtime is available without live endpoint/model inventory proof.
- Do not infer a wider beta claim from docs-only onboarding or README links.
- Do not infer desktop packaging readiness from architecture docs alone.
- Do not infer a wider release promise from docs-only exports, scaffolds, or audit artifacts.
- Do not assume the legacy `AI_BACKEND` path is a new supported contract.

## Axis Read
The useful move is to make the operator brief repeatable while keeping it below runtime machinery. Treat this packet as a drift and decision surface, not as evidence that queues, workers, providers, databases, SSE, Docker Compose, frontend paths, or model runtimes are healthy today.

## Minimal Viable Network
- Nodes: local operator workstation, local git checkout, generated work-brief directory, and human reviewer.
- Trust boundaries: repository boundary, branch/worktree boundary, and current-state documentation boundary.
- Threat model: honest-but-buggy automation and branch drift. This task does not model malicious peers or compromised runtime nodes.
- State ownership: git owns repository state; `00-current-state.md` owns release-truth interpretation; generated briefs own only dated reporting.
- Consistency target: deterministic local reporting for the same date and repo snapshot.
- Conflict policy: human-in-the-loop; `00-current-state.md` wins over older planning docs.

## What Breaks First
- Queue-coupled chat still depends on Redis plus worker health.
- Canonical and legacy config paths still coexist, so startup and operator state can drift.
- End-to-end Guardian delegation is not yet a release-supported path.
- Federation remains high-blast-radius and trust-policy sensitive.
- Graph-write enablement stays outside the default release promise.
- OpenAI import coverage and embedding deferral still need ongoing regression proof.

## Recommended Focus
Review the generated evidence, classify any branch/worktree drift, and select the next human-approved implementation or verification slice. Do not treat this brief as runtime proof.
