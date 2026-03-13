# TASK-IR-002 — Add toxic secret paths guardrails (ignore + denylist)

## Context
You are operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

## Instructions
1. Perform the described edit only in the specified files.
2. Run relevant checks or note none apply.
3. Stage and commit.
4. Output: summary + commit hash.

## Task Description
This change belongs in `/.gitignore` and `docs/reference/security/` because you need both prevention (ignore) and policy (documented forbidden paths).

Files in scope:
- `.gitignore`
- `docs/reference/security/INCIDENT_RESPONSE.md` (append a Forbidden Paths section)

Implement:
- Add explicit ignore rules for:
  - `guardian/secrets/`
  - `**/token.json`
  - `**/client_secret*.json`
  - `.env` (if not already present) and OAuth credential downloads
- In `INCIDENT_RESPONSE.md`, add section:
  - `Never commit these paths; they must be treated as compromised if committed.`

## Explicit Test Commands
```bash
# Docs/ignore update only
# No automated tests apply.
```

## Explicit Git Add + Commit Steps
```bash
git add .gitignore docs/reference/security/INCIDENT_RESPONSE.md
git commit -m "Security: formalize forbidden secret paths and ignore rules"
```

## Expected Output
- Updated ignore rules + documented policy.
- Git commit hash.
