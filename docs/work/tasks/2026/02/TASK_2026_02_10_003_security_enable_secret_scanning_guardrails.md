# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_SECURITY_HARDENING
- Task ID: 003
- Title: Add CI and pre-commit secret scanning guardrails
- Finding: FINDING-2026-02-10-001
- Risk: HIGH

## Allowed Files
- .gitleaks.toml
- .pre-commit-config.yaml
- .github/workflows/secret-scan.yml
- docs/reference/security/secret-scanning.md

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. command -v gitleaks >/dev/null || { echo 'Install gitleaks: brew install gitleaks'; exit 1; }
4. command -v pre-commit >/dev/null || { echo 'Install pre-commit: brew install pre-commit'; exit 1; }
5. gitleaks detect --source . --no-git --redact
6. for f in $(git diff --name-only); do case $f in .gitleaks.toml|.pre-commit-config.yaml|.github/workflows/secret-scan.yml|docs/reference/security/secret-scanning.md) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Local pre-commit hook and CI workflow both run secret scanning.
- gitleaks detect exits 0 on clean working tree after remediation.
- Documentation explains scan execution and failure handling.

## Rollback / Cleanup
- git restore --staged .gitleaks.toml .pre-commit-config.yaml .github/workflows/secret-scan.yml docs/reference/security/secret-scanning.md || true
- git restore .gitleaks.toml .pre-commit-config.yaml .github/workflows/secret-scan.yml docs/reference/security/secret-scanning.md || true
- rm -f .gitleaks.toml .github/workflows/secret-scan.yml docs/reference/security/secret-scanning.md

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v gitleaks >/dev/null || { echo 'Install gitleaks: brew install gitleaks'; exit 1; }
- command -v pre-commit >/dev/null || { echo 'Install pre-commit: brew install pre-commit'; exit 1; }
