# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 004
- Title: Drive active gallery UI from backend /api/media/images
- Finding: FINDING-2026-02-10-007
- Risk: MED

## Allowed Files
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/components/gallery/GalleryView.tsx
- frontend/src/tests/playwright/gallery_persistence.spec.ts

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. rg -n 'cfy.gallery|/api/media/images' frontend/src/components/persona/layout/AppShell.tsx frontend/src/components/gallery/GalleryView.tsx
5. cd frontend && npx playwright test src/tests/playwright/gallery_persistence.spec.ts
6. for f in $(git diff --name-only); do case $f in frontend/src/components/persona/layout/AppShell.tsx|frontend/src/components/gallery/GalleryView.tsx|frontend/src/tests/playwright/gallery_persistence.spec.ts) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- AppShell gallery render path uses backend image list as primary truth.
- Reload behavior reflects persisted backend state, not localStorage-only cache.
- Gallery persistence Playwright test passes.

## Rollback / Cleanup
- git restore --staged frontend/src/components/persona/layout/AppShell.tsx frontend/src/components/gallery/GalleryView.tsx frontend/src/tests/playwright/gallery_persistence.spec.ts || true
- git restore frontend/src/components/persona/layout/AppShell.tsx frontend/src/components/gallery/GalleryView.tsx frontend/src/tests/playwright/gallery_persistence.spec.ts || true
- rm -f frontend/src/tests/playwright/gallery_persistence.spec.ts

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
