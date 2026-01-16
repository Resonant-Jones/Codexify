# TASK-2026-01-16-003 — Fix glass “sharp corner” bleed (blur overflow containment)

## Task Prompt
- **Context:** Guardian chat sidebar polish campaign; prevent glass/blur surfaces from bleeding beyond rounded corners.
- **Instructions:** Edit only `frontend/src/features/chat/GuardianChat.tsx`. Run `pnpm test`. Use two-phase commits and record both commit hashes in the Summary.
- **Task Description:** Ensure containers using backdrop-blur-* and rounded corners don’t “bleed” as translucent rectangles (overflow clipping / stacking context issues).
- **Expected Output:** Glass corners render cleanly without rectangular bleed, `pnpm test` passes, and the task artifact records both commit hashes with a clean `git status --porcelain`.

## Summary
- Changed files: `frontend/src/features/chat/GuardianChat.tsx` (clip blur surface to rounded composer rail).
- Commands: `pnpm test` (pass); `git status --porcelain` (clean).
- Commit mode: two-phase
- Implementation hash: `0188b941e44c38671d246088ae0b16e1b31c76d3`
- Finalize-artifact hash: (this commit; see git log / final mapping)
