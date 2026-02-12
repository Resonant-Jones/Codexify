# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_SECURITY_HARDENING
- Task ID: 001
- Title: Quarantine OAuth secrets and replace with templates
- Finding: FINDING-2026-02-10-001
- Risk: HIGH

## Allowed Files
- .gitignore
- guardian/secrets/client_secret_oauth.json
- guardian/secrets/token.json
- guardian/secrets/client_secret_oauth.template.json
- guardian/secrets/token.template.json
- guardian/secrets/README.md

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. git ls-files guardian/secrets
4. git log -- guardian/secrets/client_secret_oauth.json guardian/secrets/token.json
5. git diff -- .gitignore guardian/secrets/client_secret_oauth.template.json guardian/secrets/token.template.json guardian/secrets/README.md
6. git ls-files guardian/secrets
7. test ! -f guardian/secrets/client_secret_oauth.json || { echo 'STOP: secret file still exists'; exit 1; }
8. test ! -f guardian/secrets/token.json || { echo 'STOP: secret file still exists'; exit 1; }
9. for f in $(git diff --name-only); do case $f in .gitignore|guardian/secrets/client_secret_oauth.json|guardian/secrets/token.json|guardian/secrets/client_secret_oauth.template.json|guardian/secrets/token.template.json|guardian/secrets/README.md) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Real OAuth secret/token files are removed from tracked working tree paths.
- Template files with placeholder-only values exist.
- .gitignore prevents guardian/secrets/*.json from being committed while allowing *.template.json.

## Rollback / Cleanup
- git restore --staged .gitignore guardian/secrets/client_secret_oauth.json guardian/secrets/token.json guardian/secrets/client_secret_oauth.template.json guardian/secrets/token.template.json guardian/secrets/README.md || true
- git restore .gitignore guardian/secrets/client_secret_oauth.json guardian/secrets/token.json guardian/secrets/client_secret_oauth.template.json guardian/secrets/token.template.json guardian/secrets/README.md || true
- rm -f guardian/secrets/client_secret_oauth.template.json guardian/secrets/token.template.json

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
