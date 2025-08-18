## Summary

- Title: <!-- short, imperative -->
- Context: <!-- why this change is needed -->

## Changes

- Files touched (high-level):
- Key diffs: <!-- link code sections or summarize -->

## Artifacts

- Preflight summary: `artifacts/preflight/<timestamp>/summary.md`
- Run manifest: `docs/prompts/run-manifest.yml`
- Infra prompt pack: `docs/prompts/infra-codex-pack.md`
- Batch run summary (if executed): `artifacts/runs/<timestamp>/summary.md`

## Validation

- [ ] Preflight ACCEPT (clean tree, tag, branch, env, ports, prompts)
- [ ] Lint/typecheck pass
- [ ] Tests pass (unit/integration as applicable)
- [ ] Security/Privacy Check: no secrets committed; local-first defaults
- [ ] Mobile limits respected (embedders ≤ 3 GB; LLM ≤ 3 GB)
- [ ] Preserved files intact: `src/TagSelector.tsx`, `src/ThreadPromptBox.tsx`, `src/PersonaEngine.ts`

## Screenshots / Logs

<!-- drop relevant images or log excerpts -->

## Risks & Rollback

- Risk level: low/medium/high
- Rollback plan: revert to tag `vX.Y.Z` and stash failures in `artifacts/failures/<timestamp>`

## Next Steps

- Follow-ups / dependent tasks:
- Link to run-manifest stages affected:

