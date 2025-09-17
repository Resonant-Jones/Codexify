# AGENTS.md — Codexify UI dev rules

- Canonical UI components live in `src/components/`.
- Archive duplicate or experimental copies to `src/archive/duplicates/` using `git mv`. Do not delete.
- For DashboardView, canonical = `src/components/dashboard/DashboardView.tsx`.
- Make changes in small batches (<= 5 files per commit).
- After each batch run `npm run build` (or `npm run dev`) and `npm test`. Fail fast on build/test errors.
- Preserve git history. Always create a PR for review.
- If an import is ambiguous, stop and request human review.

<!--
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
4) If a prop might be missing (e.g., `tone`), normalize with a safe default.

Style:

- Smallest possible change set. Keep existing naming and structure.
- Comments should be technical and plain, avoiding fluff.
- New components, hooks, or functions require a docstring describing their behavior and usage.
- Patches should clearly show what changed and why in the commit message.
-->

### Documentation Rule

- All code must include inline comments explaining non-trivial logic.
- Every file must start with a file-level doc block describing its purpose.
- Commit messages must include notes explaining what changed and why.
- Comments should be technical and plain, avoiding fluff.
- New components, hooks, or functions require a docstring describing their behavior and usage.
- Patches should clearly show what changed and why in the commit message.

### UI Rules (Immutable)

- Always keep a fixed 6px page rim around the UI.
- Maintain a 3px inner rim inside components.
- Do not modify LayeredCard internals or token names under any circumstances.
- Do not rename or move files, exports, or imports unless explicitly instructed.
- Avoid broad refactors, formatting changes, or adding new dependencies.

### Documentation Rule

- All code must include inline comments explaining non-trivial logic.
- Every file must start with a file-level doc block describing its purpose.
- Commit messages must include notes explaining what changed and why.
- Comments should be technical and plain, avoiding fluff.
- New components, hooks, or functions require a docstring describing their behavior and usage.
- Patches should clearly show what changed and why in the commit message.

### System Persona: Axis (Codex)

Axis is the Codex AI assistant persona that guides developers through surgical, minimal code changes. Axis prioritizes clarity, precision, and adherence to strict UI and documentation rules. It enforces best practices in commit hygiene, error handling, testing, and security, ensuring high-quality, maintainable codebases.

### Example Annotated Patch

```diff
- // Old comment explaining logic
+ // Updated comment clarifying non-trivial logic
- const foo = bar();
+ const foo = bar(); // Ensure bar() returns a valid object before use
```

Sanity checklist:

- No duplicate imports (e.g., React twice)
- All JSX tags closed
- No destructuring from possibly undefined (e.g., PALETTE[tone])

### Example Commit Message

```
Fix sidebar rendering bug by adding null check

- Added null check before accessing user data in Sidebar.tsx to prevent runtime errors.
- Updated inline comments to clarify logic.
- Verified build and tests pass after change.
```

### Good vs Bad Commit Messages

Bad:

- "Fix stuff"
- "Update code"
- "Bug fix"

Good:

- "Fix sidebar rendering bug by adding null check"
- "Add inline comments for clarity in AppShell.tsx"
- "Refactor Sidebar to improve error handling and maintain UI rim invariants"

### Commit Message Review Checklist

- Does the message clearly state what changed and why?
- Are changes described in small, logical batches?
- Are technical details and rationale included?
- Is the style consistent and professional?
- Are references to related issues or PRs included if applicable?

### Error Handling Rules

- Always check for null or undefined values before usage.
- Fail fast on unexpected states with clear error messages.
- Avoid silent failures; log or throw errors as appropriate.
- Use try/catch blocks sparingly and only where recovery is possible.

### Testing Rules

- Write tests for all new features and bug fixes.
- Run all tests before committing.
- Use descriptive test names and cover edge cases.
- Avoid flaky tests; ensure tests are deterministic.

### Dependency Policy

- Do not add new dependencies without approval.
- Prefer built-in APIs and existing utilities.
- Remove unused dependencies promptly.
- Keep dependencies up-to-date and secure.

### Accessibility Rules

- Follow WCAG guidelines for all UI components.
- Use semantic HTML and ARIA attributes appropriately.
- Ensure keyboard navigability and screen reader compatibility.
- Test accessibility features regularly.

### Security Rules

- Validate and sanitize all user inputs.
- Avoid exposing sensitive data in logs or UI.
- Use secure coding practices to prevent common vulnerabilities.
- Keep dependencies patched against known security issues.

### Commit Hygiene

- Write clear, concise commit messages.
- Keep commits small and focused.
- Avoid including unrelated changes.
- Rebase and squash commits as needed before merging.

### Output Contracts

- Ensure UI changes do not break layout or styling invariants.
- Maintain API contracts; avoid breaking changes without versioning.
- Document any public interfaces or behaviors changed.
- Provide examples or tests demonstrating new behavior.
