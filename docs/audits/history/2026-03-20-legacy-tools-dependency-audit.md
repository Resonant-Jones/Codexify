# Legacy Tools Dependency Audit

## Question
Does any live Codexify code still depend on the legacy `/tools` surface?

## Files Inspected
- guardian/routes/tools.py
- guardian/routes/command_bus.py
- guardian/guardian_api.py
- guardian/command_bus/loopback_http_adapter.py
- config/public_routes.yaml
- frontend/src/features/chat/GuardianChat.tsx
- frontend/src/dcw-services/gc.ts
- tests/routes/test_tools.py
- tests/routes/test_tools_legacy_shims_phase15.py
- tests/routes/test_tools_phase2_spec_policy.py
- tests/routes/test_tools_phase3_callable_contract.py
- tests/routes/test_tools_manifest_phase21_format.py
- tests/core/test_beta_router_quarantine.py
- tests/core/test_supported_profile_quarantine.py
- docs/architecture/flows.md
- docs/guardian/command-bus-auth-cli-automations.md
- docs/guardian/toolspec-policy-wall.md
- docs/chat/production_grade_chat_plan.md
- docs/Ops/SOLO_OPERATOR_SYSTEM_MAP.md
- docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md
- docs/Plans/PLAN.md
- docs/architecture/guardian-agent-delegation-recon.md
- docs/architecture/system-overview.md
- docs/architecture/solo-operator-runtime-bootcamp.md
- docs/Codexify/Codexify-Master-Architecture-Report.md
- docs/Codexify/CONFIGURATION.md
- docs/tasks/BETA_STABILIZATION/BS_001.md
- docs/Campaign/CAMPAIGN_2026_03_11_BETA_STABILIZATION_SWEEP.md
- docs/release/run/2026-03-17-beta-smoke-supported-profile-proof.md
- docs/release/run/2026-03-17-runtime-stability-audit.md
- docs/release/run/2026-03-18-supported-profile-proof.md
- API_AUDIT_REPORT.md
- Scratchfile.md
- guardian/guardian_api.py.old
- guardian/guardian_api.py.backup

## Findings
### Live runtime dependencies
- guardian/routes/tools.py (defines `/tools/*` and `/api/tools/*` compatibility routes; shims onto command bus)
- guardian/guardian_api.py (registers `tools_router` and `api_tools_router` behind `CODEXIFY_ENABLE_TOOL_ROUTES`)
- config/public_routes.yaml (lists `/tools/execute` and `/api/tools/execute` as public paths)
- frontend/src/features/chat/GuardianChat.tsx (calls `POST /tools/execute` for profile switching)
- frontend/src/dcw-services/gc.ts (client wrapper uses `POST /tools/execute`)
- guardian/command_bus/loopback_http_adapter.py (recursion block list includes `/tools/` and `/api/tools/`)

### Test-only dependencies
- tests/routes/test_tools.py (`/api/tools/execute`, `/api/tools/jobs/{id}`)
- tests/routes/test_tools_legacy_shims_phase15.py (`/tools/execute`, `/api/tools/execute`)
- tests/routes/test_tools_phase2_spec_policy.py (`/api/tools/execute?legacy=1`)
- tests/routes/test_tools_phase3_callable_contract.py (`/api/tools/execute`, `/api/tools/approve`)
- tests/routes/test_tools_manifest_phase21_format.py (`guardian.routes.tools.*` references + `/api/tools/manifest`)
- tests/core/test_beta_router_quarantine.py (`/api/tools/manifest`)
- tests/core/test_supported_profile_quarantine.py (`/api/tools/manifest`)

### Docs/spec references
- docs/architecture/flows.md (mentions `/api/tools/call`, `/api/tools/execute`)
- docs/guardian/command-bus-auth-cli-automations.md (`/tools/execute`, `/api/tools/execute`)
- docs/guardian/toolspec-policy-wall.md (`/api/tools/execute`, `/tools/execute`)
- docs/chat/production_grade_chat_plan.md (`/api/tools/execute`)
- docs/Ops/SOLO_OPERATOR_SYSTEM_MAP.md (`/api/tools/*` compatibility surface)
- docs/Ops/SOLO_OPERATOR_AUTOMATION_RUNBOOK.md (`/api/tools/*` compatibility surface)
- docs/Plans/PLAN.md (`/api/tools/*`, `/tools/*` quarantine notes)
- docs/architecture/guardian-agent-delegation-recon.md (`/tools`, `/api/tools` compatibility layer)
- docs/architecture/system-overview.md (trigger includes legacy `/api/tools/*`)
- docs/architecture/solo-operator-runtime-bootcamp.md (legacy `/api/tools/*` behavior)
- docs/Codexify/Codexify-Master-Architecture-Report.md (`tools.py` route mention)
- docs/Codexify/CONFIGURATION.md (`CODEXIFY_ENABLE_TOOL_ROUTES` for `/tools` and `/api/tools`)
- docs/tasks/BETA_STABILIZATION/BS_001.md (`guardian.routes.tools` compatibility notes)
- docs/Campaign/CAMPAIGN_2026_03_11_BETA_STABILIZATION_SWEEP.md (`guardian.routes.tools` contract)
- docs/release/run/2026-03-17-beta-smoke-supported-profile-proof.md (`/api/tools/manifest` checks)
- docs/release/run/2026-03-17-runtime-stability-audit.md (`/api/tools/manifest` checks)
- docs/release/run/2026-03-18-supported-profile-proof.md (`/api/tools/manifest` checks)
- API_AUDIT_REPORT.md (`/tools/execute` audit references)

### Dead or stale references
- Scratchfile.md (legacy `/tools/execute` snippet)
- guardian/guardian_api.py.old (old inline `/tools/execute` route)
- guardian/guardian_api.py.backup (old inline `/tools/execute` route)

## Verdict
- Yes. There are live runtime callers still depending on the legacy `/tools` surface (notably frontend profile switching and the shared GC client wrapper), and the compatibility routes remain registered and publicly allowlisted.
- `/api/tools/execute` appears in tests and docs but no repo-local runtime callers were found. `/api/tools/call` only appears in docs and is not implemented in the current routes.
- Architecture docs are partially stale: they still cite `/api/tools/call` as a caller path even though the route does not exist, and they imply `/api/tools/*` as a primary call path rather than compatibility.

## Recommended Next Action
- Leave in place pending migration.
