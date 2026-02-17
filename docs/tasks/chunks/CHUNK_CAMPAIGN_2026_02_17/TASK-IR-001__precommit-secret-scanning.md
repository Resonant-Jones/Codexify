# TASK-IR-001 — Expand pre-commit secret detection (beyond private keys)

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Docs-only or config changes: run the relevant checks.
3. If checks pass: stage and commit.
4. Output: summary, checks, commit hash.

## Task Description
This change belongs in `/.pre-commit-config.yaml` because secrets must be blocked before they enter commits (push protection is not enough).

Files in scope:
- `.pre-commit-config.yaml`

Implement one of the following (choose the simplest that works in this repo):
- Option A (recommended): `gitleaks` pre-commit hook
- Option B: `detect-secrets` hook with a baseline file

Configure excludes so scanning skips:
- `node_modules/`
- `.venv/`
- `.pnpm-store/`
- large generated folders already ignored by repo conventions

## Explicit Test Commands
```bash
pre-commit run --all-files
```

## Explicit Git Add + Commit Steps
```bash
git add .pre-commit-config.yaml
git commit -m "Security: strengthen pre-commit secret scanning"
```

## Expected Output
- Hook added and passing.
- Git commit hash.
