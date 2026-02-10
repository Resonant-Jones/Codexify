# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_FOLLOWUP_DRIFT
- Task ID: 001
- Title: Canonicalize SettingsView implementation and deprecate drifted variant
- Finding: FINDING-2026-02-10-011
- Risk: LOW

## Allowed Files
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/features/settings/SettingsView.tsx
- frontend/src/components/settings/SettingsView.tsx
- docs/frontend/settings-view-canonical.md

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. rg -n 'SettingsView|upload-chatgpt-export' frontend/src/components/persona/layout/AppShell.tsx frontend/src/features/settings/SettingsView.tsx frontend/src/components/settings/SettingsView.tsx
4. rg --files frontend/src | rg 'SettingsView.tsx'
5. cd frontend && npx vitest run --passWithNoTests
6. for f in $(git diff --name-only); do case $f in frontend/src/components/persona/layout/AppShell.tsx|frontend/src/features/settings/SettingsView.tsx|frontend/src/components/settings/SettingsView.tsx|docs/frontend/settings-view-canonical.md) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Single canonical settings implementation is documented and used by active app flow.
- Legacy settings component is explicitly deprecated or excluded from active build path.
- Drift ambiguity for migration endpoint usage is removed.

## Rollback / Cleanup
- git restore --staged frontend/src/components/persona/layout/AppShell.tsx frontend/src/features/settings/SettingsView.tsx frontend/src/components/settings/SettingsView.tsx docs/frontend/settings-view-canonical.md || true
- git restore frontend/src/components/persona/layout/AppShell.tsx frontend/src/features/settings/SettingsView.tsx frontend/src/components/settings/SettingsView.tsx docs/frontend/settings-view-canonical.md || true
- rm -f docs/frontend/settings-view-canonical.md

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v npx >/dev/null
