# AGENTS.md — Codexify UI dev rules

- Canonical UI components live in `src/components/`.
- Archive duplicate or experimental copies to `src/archive/duplicates/` using `git mv`. Do not delete.
- For DashboardView, canonical = `src/components/dashboard/DashboardView.tsx`.
- Make changes in small batches (<= 5 files per commit).
- After each batch run `npm run build` (or `npm run dev`) and `npm test`. Fail fast on build/test errors.
- Preserve git history. Always create a PR for review.
- If an import is ambiguous, stop and request human review.

You are doing a SURGICAL, MINIMAL patch. Honor these invariants exactly:

- Keep 6px page rim and 3px inner rim.
- Do not touch LayeredCard internals or token names.
- Do not rename/move files, exports, or imports unless explicitly asked.
- No broad refactors, no formatting churn, no added dependencies.

Task:

- [State the exact visual/behavioral change in 1–2 bullets]

Scope:

- Only edit these files (and nothing else):
  - src/components/layout/AppShell.tsx
  - src/components/chat/Sidebar.tsx
  - [list any others]

Procedure:

1) List the plan and the exact files/lines you will change.
2) Output unified diffs (git-style) for each file.
3) After the diffs, include a SHORT “sanity checklist”:
   - No duplicate imports (e.g., React twice),
   - All JSX tags closed,
   - No destructuring from possibly undefined (e.g., PALETTE[tone]).
4) If a change would cause a type/import ripple, STOP and ask to expand scope.

Style:

- Smallest possible change set. Keep existing naming and structure.
- If a prop might be missing (e.g., `tone`), normalize with a safe default.