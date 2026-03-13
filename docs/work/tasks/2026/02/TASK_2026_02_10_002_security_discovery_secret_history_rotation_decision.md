# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_SECURITY_HARDENING
- Task ID: 002
- Title: Discovery decision for secret history purge and credential rotation
- Finding: FINDING-2026-02-10-001
- Risk: HIGH

## Allowed Files
- docs/reference/security/oauth-secret-incident-2026-02-10.md

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. git rev-list --all -- guardian/secrets/client_secret_oauth.json guardian/secrets/token.json > /tmp/oauth_secret_revlist.txt
4. wc -l /tmp/oauth_secret_revlist.txt
5. git log --date=iso --pretty=format:'%H %ad %an %s' -- guardian/secrets/client_secret_oauth.json guardian/secrets/token.json
6. git remote -v
7. command -v git-filter-repo >/dev/null || echo 'MISSING: git-filter-repo'
8. rg -n 'Decision|Affected commits|Purge command|Rotation owners|Completion evidence' docs/reference/security/oauth-secret-incident-2026-02-10.md
9. for f in $(git diff --name-only); do case $f in docs/reference/security/oauth-secret-incident-2026-02-10.md) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Incident document lists affected commits, refs, and purge command plan.
- Document records explicit go/no-go decision for history rewrite.
- Document records credential rotation owners and completion evidence placeholders.

## Rollback / Cleanup
- git restore --staged docs/reference/security/oauth-secret-incident-2026-02-10.md || true
- git restore docs/reference/security/oauth-secret-incident-2026-02-10.md || true
- rm -f docs/reference/security/oauth-secret-incident-2026-02-10.md

## Dependencies / Prereqs
- command -v git >/dev/null
