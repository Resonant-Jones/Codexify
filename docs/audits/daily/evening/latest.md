# Daily Audit — 2026-04-03

## Repo Status
- Date: 2026-04-03
- Phase: `evening`
- Branch: `detached@977777c`
- HEAD: `977777c84e28a8e813a9d13205b100739b2e9497`
- Worktree: clean

## Audit CLI Summary
- Selected mode: `text_fallback`
- Attempted commands:
  - `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/venv/bin/python /Users/resonant_jones/.codex/worktrees/9d9d/Codexify/scripts/audit_platform_readiness.py --json` -> exit 0 (json probe)
  - `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/venv/bin/python /Users/resonant_jones/.codex/worktrees/9d9d/Codexify/scripts/audit_platform_readiness.py` -> exit 0 (plain)
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
- Commit count: 9
- Unique files changed: 38
- Files changed: `docs/architecture/2026-04-03-supported-rag-path-proof.md`, `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/SidebarRoot.test.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx`, `frontend/src/components/sidebar/__tests__/useSidebarThreads.test.tsx`, `frontend/src/components/sidebar/sidebarPresentation.ts`, `frontend/src/components/sidebar/useSidebarThreads.ts`, `docs/audits/latest.json`, `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/HealthPanel.test.tsx`, `frontend/src/features/commandCenter/components/HealthPanel.tsx`, `frontend/src/features/commandCenter/hooks/useHealthSummary.ts`, `frontend/src/features/commandCenter/types.ts`, `guardian/core/health_service.py`, `guardian/routes/health.py`, `tests/routes/test_health_routes.py`, `docs/architecture/competitive-parity-audit.md`, `docs/audits/daily/morning/2026-04-03-audit.json`, `docs/audits/daily/morning/2026-04-03-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.md`, `backend/Dockerfile.prod`, `backend/entrypoint-dev.sh`, `backend/run-server.sh`, `backend/scripts/docker/run_migrator.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py`, `backend/rag/chatgpt_migration.py`, `guardian/guardian_api.py`, `guardian/tests/migration/test_chatgpt_ingest.py`, `tests/core/test_supported_profile_startup.py`, `tests/routes/test_migration_routes.py`, `docs/audits/daily/evening/2026-04-02-audit.json`, `docs/audits/daily/evening/2026-04-02-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `977777c84e28` | docs(architecture): add supported rag path proof on current head | `docs/architecture/2026-04-03-supported-rag-path-proof.md` |
| `f0817a33192e` | Add provider filters for imported sidebar threads | `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/SidebarRoot.test.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx`, `frontend/src/components/sidebar/__tests__/useSidebarThreads.test.tsx`, `frontend/src/components/sidebar/sidebarPresentation.ts`, `frontend/src/components/sidebar/useSidebarThreads.ts` |
| `2548d6a2d28e` | Fix audit JSON newline | `docs/audits/latest.json` |
| `6c30fc202493` | normalize health endpoints and status interpretation | `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/HealthPanel.test.tsx`, `frontend/src/features/commandCenter/components/HealthPanel.tsx`, `frontend/src/features/commandCenter/hooks/useHealthSummary.ts`, `frontend/src/features/commandCenter/types.ts`, `guardian/core/health_service.py`, `guardian/routes/health.py`, `tests/routes/test_health_routes.py` |
| `eb8a96e2d551` | docs(audit): add competitive parity audit | `docs/architecture/competitive-parity-audit.md` |
| `35f32d0e8233` | Update daily audit snapshot for 2026-04-03 | `docs/audits/daily/morning/2026-04-03-audit.json`, `docs/audits/daily/morning/2026-04-03-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `afe052afbaa1` | Fix Alembic heads and chat indentation | `backend/Dockerfile.prod`, `backend/entrypoint-dev.sh`, `backend/run-server.sh`, `backend/scripts/docker/run_migrator.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py` |
| `b01818ef5759` | fix(import): batch ChatGPT embedding normalization | `backend/rag/chatgpt_migration.py`, `guardian/guardian_api.py`, `guardian/tests/migration/test_chatgpt_ingest.py`, `tests/core/test_supported_profile_startup.py`, `tests/routes/test_migration_routes.py` |
| `89cf1f4de587` | Add evening audit reports | `docs/audits/daily/evening/2026-04-02-audit.json`, `docs/audits/daily/evening/2026-04-02-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/routes/chat.py` |
| `docs` | 2 | `docs/architecture/2026-04-03-supported-rag-path-proof.md`, `docs/architecture/competitive-parity-audit.md` |
| `audit` | 10 | `docs/audits/latest.json`, `docs/audits/daily/morning/2026-04-03-audit.json`, `docs/audits/daily/morning/2026-04-03-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.md`, `docs/audits/daily/evening/2026-04-02-audit.json`, `docs/audits/daily/evening/2026-04-02-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md` |
| `providers` | 1 | `tests/core/test_supported_profile_startup.py` |
| `ingestion` | 1 | `guardian/tests/migration/test_chatgpt_ingest.py` |
| `frontend` | 12 | `frontend/src/components/sidebar/SidebarRoot.tsx`, `frontend/src/components/sidebar/ThreadList.tsx`, `frontend/src/components/sidebar/__tests__/SidebarRoot.test.tsx`, `frontend/src/components/sidebar/__tests__/ThreadList.test.tsx`, `frontend/src/components/sidebar/__tests__/useSidebarThreads.test.tsx`, `frontend/src/components/sidebar/sidebarPresentation.ts`, `frontend/src/components/sidebar/useSidebarThreads.ts`, `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/HealthPanel.test.tsx`, `frontend/src/features/commandCenter/components/HealthPanel.tsx`, `frontend/src/features/commandCenter/hooks/useHealthSummary.ts`, `frontend/src/features/commandCenter/types.ts` |
| `tests` | 2 | `tests/routes/test_health_routes.py`, `tests/routes/test_migration_routes.py` |
| `unknown` | 9 | `guardian/core/health_service.py`, `guardian/routes/health.py`, `backend/Dockerfile.prod`, `backend/entrypoint-dev.sh`, `backend/run-server.sh`, `backend/scripts/docker/run_migrator.py`, `guardian/core/chat_completion_service.py`, `backend/rag/chatgpt_migration.py`, `guardian/guardian_api.py` |

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

