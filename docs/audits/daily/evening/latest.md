# Daily Audit — 2026-03-30

## Repo Status
- Date: 2026-03-30
- Phase: `evening`
- Branch: `main`
- HEAD: `961e9092a06e2dc01226eeced3a9876527832422`
- Worktree: dirty
- Status lines:
  - ` M prompts.py`

## Audit CLI Summary
- Selected mode: `text_fallback`
- Attempted commands:
  - `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/venv/bin/python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/audit_platform_readiness.py --json` -> exit 0 (json probe)
  - `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/venv/bin/python /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/audit_platform_readiness.py` -> exit 0 (plain)
- Summary counts: PASS 40, WARN 11, FAIL 0
- Strongest evidence: `Core Loop Integrity`, `Primitive Stability`, `Extension Boundary`
- Weakest signals: `Federation Readiness`, `Governance Readiness`, `Alternate Surface Readiness`

### Current Suggested Score Bands
| Domain | Band |
| --- | --- |
| `Core Loop Integrity` | 1-2 likely |
| `Primitive Stability` | 1-2 likely |
| `Extension Boundary` | 1-2 likely |
| `Observability` | 1-2 likely |
| `Durability & Recovery` | 1-2 likely |
| `Alternate Surface Readiness` | manual review required |
| `Federation Readiness` | 0-1 likely |
| `Governance Readiness` | manual review required |

### Baseline Score State
- Source: `docs/audits/history/2026-03-19-platform-readiness-baseline.md`
- Summary: Codexify has progressed beyond prototype into an operational substrate.
- Phase gate: Early-Adopter Ready: ❌ Not yet

| Domain | Baseline Score |
| --- | --- |
| `Core Loop Integrity` | 2 |
| `Primitive Stability` | 2 |
| `Extension Boundary` | 2 |
| `Observability` | 2 |
| `Durability & Recovery` | 1 |
| `Alternate Surface Readiness` | 2 |
| `Federation Readiness` | 1 |
| `Governance Readiness` | 2 |

## Changes in Last 24 Hours
- Commit count: 16
- Unique files changed: 37
- Files changed: `docs/architecture/codexify_workspace_surface_spec_v_1.md`, `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx`, `frontend/src/App.tsx`, `frontend/src/components/documents/DocumentsView.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceInvocation.test.tsx`, `frontend/src/features/workspace/state/useWorkspaceState.ts`, `frontend/src/components/documents/DocumentTile.tsx`, `frontend/src/components/media/MediaTile.test.tsx`, `prompts.py`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePreview.test.tsx`, `frontend/src/components/dashboard/DashboardView.demo-state.test.tsx`, `frontend/src/components/dashboard/DashboardView.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/components/documents/DocumentsView.demo-state.test.tsx`, `tests/routes/test_media_routes.py`, `frontend/src/features/settings/SettingsView.test.tsx`, `guardian/server/app.py`, `tests/routes/test_imprint_routes.py`, `tests/routes/test_projects_routes.py`, `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/__tests__/CreateProjectModal.test.tsx`, `guardian/routes/health.py`, `tests/routes/test_health_endpoints.py`, `docs/audits/daily/morning/2026-03-30-audit.json`, `docs/audits/daily/morning/2026-03-30-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/evening/2026-03-29-audit.json`, `docs/audits/daily/evening/2026-03-29-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `961e9092a06e` | Workspace Spec | `docs/architecture/codexify_workspace_surface_spec_v_1.md` |
| `0d54ae7a2923` | fix(chat): relabel active scope as project | `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx` |
| `fde7e2e6ffa6` | fix(chat): darken thread tiles in dark mode | `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx` |
| `8c1d880fb9e1` | fix(workspace): unify invocation flow and block recursive mounts | `frontend/src/App.tsx`, `frontend/src/components/documents/DocumentsView.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceInvocation.test.tsx`, `frontend/src/features/workspace/state/useWorkspaceState.ts` |
| `dbd6a7b189b3` | fix(media): restore document tile layout contract | `frontend/src/components/documents/DocumentTile.tsx`, `frontend/src/components/media/MediaTile.test.tsx`, `prompts.py` |
| `1b024d7414dc` | feat(workspace): add typed preview registry for supported documents | `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePreview.test.tsx` |
| `1b83e7c5b744` | refactor(dashboard): auto-hide demo content when real data exists | `frontend/src/components/dashboard/DashboardView.demo-state.test.tsx`, `frontend/src/components/dashboard/DashboardView.tsx` |
| `4d46923d04d2` | refactor(gallery): auto-hide demo content when real data exists | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx` |
| `a2066e26e5b6` | refactor(documents): auto-hide demo content when real data exists | `frontend/src/components/documents/DocumentsView.demo-state.test.tsx`, `frontend/src/components/documents/DocumentsView.tsx` |
| `6ebe4b81df24` | fix(media): unify dashboard and gallery persisted truth | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `tests/routes/test_media_routes.py` |
| `6dc00bb17b05` | fix(settings): restore save route contract | `frontend/src/features/settings/SettingsView.test.tsx`, `guardian/server/app.py`, `tests/routes/test_imprint_routes.py` |
| `9aa40796cb03` | fix(projects): restore dashboard create project flow | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `tests/routes/test_projects_routes.py` |
| `2b908467e23a` | fix(projects): restore sidebar create project flow | `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/__tests__/CreateProjectModal.test.tsx`, `tests/routes/test_projects_routes.py` |
| `d531231112e1` | Fix chat worker heartbeat truth in health endpoint | `guardian/routes/health.py`, `tests/routes/test_health_endpoints.py` |
| `be58a548cfcd` | Refresh daily morning audit snapshot | `docs/audits/daily/morning/2026-03-30-audit.json`, `docs/audits/daily/morning/2026-03-30-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `d9bce5e158b9` | Refresh daily evening audit snapshot | `docs/audits/daily/evening/2026-03-29-audit.json`, `docs/audits/daily/evening/2026-03-29-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `docs` | 1 | `docs/architecture/codexify_workspace_surface_spec_v_1.md` |
| `audit` | 10 | `docs/audits/daily/morning/2026-03-30-audit.json`, `docs/audits/daily/morning/2026-03-30-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/evening/2026-03-29-audit.json`, `docs/audits/daily/evening/2026-03-29-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md` |
| `frontend` | 19 | `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx`, `frontend/src/App.tsx`, `frontend/src/components/documents/DocumentsView.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceInvocation.test.tsx`, `frontend/src/features/workspace/state/useWorkspaceState.ts`, `frontend/src/components/documents/DocumentTile.tsx`, `frontend/src/components/media/MediaTile.test.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePreview.test.tsx`, `frontend/src/components/dashboard/DashboardView.demo-state.test.tsx`, `frontend/src/components/dashboard/DashboardView.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/components/documents/DocumentsView.demo-state.test.tsx`, `frontend/src/features/settings/SettingsView.test.tsx`, `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/__tests__/CreateProjectModal.test.tsx` |
| `tests` | 4 | `tests/routes/test_media_routes.py`, `tests/routes/test_imprint_routes.py`, `tests/routes/test_projects_routes.py`, `tests/routes/test_health_endpoints.py` |
| `unknown` | 3 | `prompts.py`, `guardian/server/app.py`, `guardian/routes/health.py` |

## Risk Flags
- `chat_depends_on_redis_and_workers`: Chat completion is queue-coupled and depends on Redis plus worker availability. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- `config_split_brain_risk`: Canonical and legacy config paths still coexist, so startup and operator state can drift. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- `legacy_tools_and_command_bus_duality`: Legacy /tools behavior and the command bus still overlap, which increases contract drift risk. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- `sync_not_durable`: Sync subscriptions are still process-local rather than durable across restarts. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`, `docs/architecture/data-and-storage.md`
- `federation_high_blast_radius`: Federation remains sensitive to trust policy, feature flags, and egress behavior. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`

## Manual Notes
- Finished today: 
- Blocked: 
- Next priority: 

