# PR #869 review repair

Baseline main: `3814de8e0bca9c09fb3baeebc22a84091322fc6a`.
Reviewed PR head: `2ce14128c2cca924c5d5ea4143a4dd35544a20d8`.
Evidence class: proven-test / proven-code-path, not live runtime qualification.

## Changes

- Merge main while preserving its release classes and current-state content.
- Compare Chronicle thread/origin membership independently of order without dropping duplicate cardinality.
- Reject system/developer/tool roles across canonical, importer, and original provenance, including tool-result aliases.
- Preserve distinct local-provider unavailability through generation and return HTTP 503; malformed output remains HTTP 422.
- Let caller-controlled evidence-reader request errors propagate to HTTP 422 in authorization-check and preview.
- Mark the historical constrained-JSON qualification report unverified in this PR; no retained qualification artifact is added or claimed.

These repairs align with ADR-016 and the existing request-scoped interpretation and ephemeral preview contracts. No new authority, durable state, provider fallback, tool capability, release support, or ADR is introduced.

## Validation

- `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python -m pytest -q tests/services/test_chronicle_model_exposure.py`: 38 passed.
- From `frontend`, `pnpm --dir src exec vitest run features/chat/components/__tests__/Composer.landing-hover-controls.test.tsx components/persona/layout/__tests__/GuardianMobileComposerSingleSurface.test.tsx`: 29 passed.
- From `frontend`, `pnpm test`: 1,943 passed, four failed, one skipped; the failed first stage prevented the chrome-extension stage from executing.
- All four frontend failures reproduced on the frozen main baseline: two UnifiedDesktopCompositor tests, one GuardianMobileSidebarAppMenu test, and one SettingsPanelShell test. Baseline rerun: four failed, ten passed. Existing installed dependencies were reused without package/version changes.
- Chronicle/import inspection HTTP tests could not collect: main's `memory_purge` imports missing `MemoryLifecycleRevision` and other UMS revision models. `guardian/db/models.py` and `memory_purge.py` are unchanged relative to main.
- Standalone imported-history reader PostgreSQL tests failed fixture setup: Alembic has multiple heads (`2e865c4a9b10`, `c7f4a9b2e6d1`). A separate temporary PostgreSQL container was used; production databases and existing containers were untouched.
- `python3 scripts/validate_docs.py`: passed.
- `git diff --check`: passed.
- After hydrating architecture fixtures, `pytest -q --disable-warnings tests/architecture`: 431 passed. The three stale canonical source hashes (ADR index, current-state, KB entrypoint) were synchronized; freshness and authority fields were not promoted.
- Remote frontend CI: 1,946 passed, one failed, one skipped; its sidebar failure is reproduced on main.
- Remote backend CI failed collection because the CI dependency environment lacks `mcp`; no backend suite pass is claimed.

HTTP regression tests for the review fixes are added but remain blocked by those inherited backend failures. No HTTP, deployed-provider, semantic-entailment, or release qualification is claimed. Release remains `HOLD`.
