# Guardian Work Brief - Decision Log - 2026-06-05

## Decisions

### D1 - Use manual packet fallback again
- Decision: Create the four expected Guardian work-brief files manually for 2026-06-05.
- Reason: The preferred `make guardian-brief` target is missing in this checkout.
- Boundary: This does not restore the automation generator and should be treated as a fallback artifact.

### D2 - Preserve branch state
- Decision: Do not pull, rebase, merge, commit, clean, or stage the worktree.
- Reason: The automation request says to include dirty/behind state as part of the brief rather than fixing it.
- Current state: Branch `codex/map-researchcode-functions` is ahead 2, behind 0 versus upstream, with a clean worktree before today's packet.

### D3 - No release claim expansion
- Decision: Keep Guardian Retrieval Navigation Model material classified as planning-only.
- Reason: `docs/architecture/00-current-state.md` explicitly prevents treating the model, adaptive route hints, graph evolution proposals, or self-improving memory as shipped runtime behavior.
- Consequence: Any future implementation needs fresh supported-path proof before it can affect release truth.

### D4 - Next task remains generator restoration or explicit absence
- Decision: The next Codex task should be restoring/porting the Guardian brief generation path or documenting its intentional absence on this branch.
- Reason: Repeated manual generation preserves daily evidence but does not satisfy repeatable automation health.
