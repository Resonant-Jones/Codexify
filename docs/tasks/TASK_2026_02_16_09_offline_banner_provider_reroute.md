# TASK_2026_02_16_09_offline_banner_provider_reroute

## Task ID
TASK-2026-02-16-009_offline_banner_provider_reroute

## Goal
When the LLM backend is offline, provide an inline way to switch/reroute providers from the offline banner so work can continue without leaving chat.

## Files Touched
- frontend/src/features/chat/GuardianChat.tsx (or actual owner of chat header/offline banner)
- offline banner component owner (discovered via ripgrep)
- focused frontend test file(s) validating offline switch-provider behavior

## Tests Run
- `pnpm --dir frontend/src test <relevant_test_file> -- --runInBand`
- (if full suite is run) note unrelated pre-existing failures explicitly

## Notes / Risks
- Keep UI compact and calm; avoid large new controls.
- Do not add token counter back to header.
- Respect local-only/cloud-disabled posture:
  - if cloud providers are disabled, selector and messaging must reflect allowed providers only.
- Discovery commands:
  - `rg -n "LLM backend offline|ConnectTimeout|/api/tags|Recheck" frontend/src -S`
  - `rg -n "provider|LLM_PROVIDER|model.*offline|Provider:" frontend/src/features/chat frontend/src/components -S`
- Preferred wiring:
  - open/toggle existing provider selector state in-place (no duplicate settings UI).
  - alternate only if needed: open Persona settings provider section.

## Commit A
- `<pending>`

## Commit B
- `<pending>`
