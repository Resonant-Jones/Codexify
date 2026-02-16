# TASK_2026_02_16_09_offline_banner_provider_reroute

## Task ID
TASK-2026-02-16-009_offline_banner_provider_reroute

## Goal
When the LLM backend is offline, provide an inline way to switch/reroute providers from the offline banner so work can continue without leaving chat.

## Files Touched
- frontend/src/features/chat/GuardianChat.tsx
- frontend/src/components/SessionRail/SessionRail.tsx
- frontend/src/components/ProviderSelect.tsx
- frontend/src/features/chat/__tests__/GuardianChat.offline-banner.test.tsx

## Tests Run
- `pnpm --dir frontend/src test features/chat/__tests__/GuardianChat.offline-banner.test.tsx -- --runInBand`
  - Result: pass (`1 passed`, no unrelated failures in this focused run)

## Notes / Risks
- Discovery confirmed the offline banner owner is `GuardianChat.tsx`, and provider selector owner is `SessionRail -> ProviderSelect`.
- Added compact `Switch provider` action in the offline banner, visible in offline/misconfigured states.
- Wired reroute action to existing provider selector UI by sending an open signal from `GuardianChat` through `SessionRail` into `ProviderSelect` (no duplicate settings surface).
- Added cloud-disabled gating support:
  - detect cloud-disabled signal from LLM health error payload (`ALLOW_CLOUD_PROVIDERS=false`)
  - show `Cloud providers disabled by config.` messaging in banner and provider menu
  - filter known cloud provider options from selector when cloud providers are disabled.

## Commit A
- `d23f0504f2dad5d33a7a50045f8f27834af6d462`

## Commit B
- `<this-commit>`
