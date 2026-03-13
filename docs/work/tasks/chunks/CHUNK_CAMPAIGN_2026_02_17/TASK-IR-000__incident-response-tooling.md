# TASK-IR-000 — Add repo-local incident response tooling and documentation

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Docs-only changes: run relevant checks if defined; otherwise note no automated tests apply.
3. If checks succeed: stage with `git add` and commit.
4. Output: summary, checks, commit hash.

## Task Description
This change belongs in `docs/reference/security/INCIDENT_RESPONSE.md` and `scripts/security/` because it establishes a repeatable playbook and scripts for secret incident response (rotation + history rewrite + scanning).

Create these files:
- `docs/reference/security/INCIDENT_RESPONSE.md`
- `scripts/security/scan_secrets.sh`
- `scripts/security/rewrite_history_remove_paths.sh`

Content requirements:
- `INCIDENT_RESPONSE.md` must include:
  - How to identify compromised credentials (OAuth client secret, refresh tokens).
  - Rotation steps checklist.
  - Git history rewrite steps using `git filter-repo` (preferred) and post-rewrite force-push instructions.
  - Post-incident verification checklist (`grep`, pre-commit, GitHub scanning).
- `scan_secrets.sh`:
  - Runs `git grep` patterns for known risky strings (`token.json`, `client_secret`, `refresh_token`).
  - Optionally runs `detect-secrets` or `gitleaks` if installed (`if command exists`).
- `rewrite_history_remove_paths.sh`:
  - Uses `git filter-repo --path <...> --invert-paths` for known secret paths.
  - Explicitly states this is destructive.

Operational note:
- Do not run rotation/revocation in code; only document those steps.

## Explicit Test Commands
```bash
# If a docs lint/build command exists:
make docs

# If docs tooling is unavailable:
# Docs/scripts only — no automated tests apply.
```

## Explicit Git Add + Commit Steps
```bash
git add docs/reference/security/INCIDENT_RESPONSE.md scripts/security/scan_secrets.sh scripts/security/rewrite_history_remove_paths.sh
git commit -m "Docs: add secret incident response playbook and tooling"
```

## Expected Output
- Confirmation of files created.
- Note about checks/tests.
- Git commit hash.
