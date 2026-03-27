# Daily Audit — 2026-03-27

## Repo Status
- Date: 2026-03-27
- Phase: `morning`
- Branch: `codex/fix-chat-fetch-loops`
- HEAD: `cb09d316f063f866b7ee4e2b76d7cfd28c5e61f4`
- Worktree: clean

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
- Unique files changed: 34
- Files changed: `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/useAgentRuns.test.tsx`, `frontend/src/features/chat/hooks/useAgentRuns.ts`, `frontend/src/lib/liveEventsHub.ts`, `frontend/src/test/live-events-singleton.test.tsx`, `docs/audits/daily/evening/2026-03-26-audit.json`, `docs/audits/daily/evening/2026-03-26-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/features/chat/api/actionCenter.ts`, `frontend/src/features/chat/api/approvalInbox.ts`, `frontend/src/features/chat/api/threadApprovals.ts`, `frontend/src/features/chat/hooks/useGuardianActionCenter.ts`, `frontend/src/features/chat/hooks/useGuardianApprovalInbox.ts`, `frontend/src/features/chat/hooks/useGuardianThreadApprovalRail.ts`, `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/index.css`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/SessionRail/SessionRail.tsx`, `backend/rag/chatgpt_migration.py`, `frontend/src/components/modals/ChatGPTImportModal.tsx`, `frontend/src/tests/playwright/migration_e2e_import.spec.ts`, `guardian/routes/migration.py`, `tests/routes/test_migration_routes.py`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `docs/audits/daily/morning/2026-03-26-audit.json`, `docs/audits/daily/morning/2026-03-26-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `cb09d316f063` | feat(chat): drive agentRunsStore from task events for real-time UI updates | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/useAgentRuns.test.tsx`, `frontend/src/features/chat/hooks/useAgentRuns.ts`, `frontend/src/lib/liveEventsHub.ts`, `frontend/src/test/live-events-singleton.test.tsx` |
| `6623f8ee9638` | Refresh daily evening audit snapshot | `docs/audits/daily/evening/2026-03-26-audit.json`, `docs/audits/daily/evening/2026-03-26-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `62d7672a93ac` | fix(chat): promote useAgentRuns to shared per-thread store with subscription model | `frontend/src/features/chat/hooks/useAgentRuns.ts` |
| `a4b717b21c1c` | refactor(chat): centralize agent-runs fetching into useAgentRuns hook and remove duplicate fetch paths | `frontend/src/features/chat/api/actionCenter.ts`, `frontend/src/features/chat/api/approvalInbox.ts`, `frontend/src/features/chat/api/threadApprovals.ts`, `frontend/src/features/chat/hooks/useAgentRuns.ts`, `frontend/src/features/chat/hooks/useGuardianActionCenter.ts`, `frontend/src/features/chat/hooks/useGuardianApprovalInbox.ts`, `frontend/src/features/chat/hooks/useGuardianThreadApprovalRail.ts` |
| `f729bd25a342` | fix(chat): clear active thread when entering General scope | `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` |
| `e26072448db1` | fix(chat): stop runaway profile and agent-runs fetch loop by enforcing thread gating and removing self-triggering effects | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/api/actionCenter.ts`, `frontend/src/features/chat/api/approvalInbox.ts`, `frontend/src/features/chat/api/threadApprovals.ts` |
| `91cb0c71c534` | Fixed the Codexify pill badge in the nav bar. The text was displaying black on Light mode inside the Badge. | `frontend/src/features/chat/chatLane.ts`, `frontend/src/index.css` |
| `83aa933cf078` | fix(ui): stabilize Codexify brand badge across light and dark modes | `frontend/src/index.css` |
| `633629b59020` | Use accent text tokens for brand tab styling | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/index.css` |
| `f13943a2200b` | Fixing Session Rail Tool array | `frontend/src/components/SessionRail/SessionRail.tsx`, `frontend/src/features/chat/GuardianChat.tsx` |
| `8218ad4a80e8` | fix(import): accept large ChatGPT exports for background migration | `backend/rag/chatgpt_migration.py`, `frontend/src/components/modals/ChatGPTImportModal.tsx`, `frontend/src/tests/playwright/migration_e2e_import.spec.ts`, `guardian/routes/migration.py`, `tests/routes/test_migration_routes.py` |
| `0c1d2602460b` | Fix composer send button boundary and circle styling | `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `298e57fd94cd` | Align chat lane and shell width tokens | `frontend/src/features/chat/chatLane.ts` |
| `0a8f487cdfe9` | fix(ui): correct Codexify logo text color by theme | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx` |
| `5c6f54caa18c` | chore(audit): refresh daily morning audit snapshot | `docs/audits/daily/morning/2026-03-26-audit.json`, `docs/audits/daily/morning/2026-03-26-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `e7b2cfa8f027` | debug(ui): add layout instrumentation for guardian chat shell and controls | `frontend/src/features/chat/GuardianChat.tsx` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `audit` | 10 | `docs/audits/daily/evening/2026-03-26-audit.json`, `docs/audits/daily/evening/2026-03-26-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/morning/2026-03-26-audit.json`, `docs/audits/daily/morning/2026-03-26-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md` |
| `frontend` | 21 | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/useAgentRuns.test.tsx`, `frontend/src/features/chat/hooks/useAgentRuns.ts`, `frontend/src/lib/liveEventsHub.ts`, `frontend/src/test/live-events-singleton.test.tsx`, `frontend/src/features/chat/api/actionCenter.ts`, `frontend/src/features/chat/api/approvalInbox.ts`, `frontend/src/features/chat/api/threadApprovals.ts`, `frontend/src/features/chat/hooks/useGuardianActionCenter.ts`, `frontend/src/features/chat/hooks/useGuardianApprovalInbox.ts`, `frontend/src/features/chat/hooks/useGuardianThreadApprovalRail.ts`, `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/index.css`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/SessionRail/SessionRail.tsx`, `frontend/src/components/modals/ChatGPTImportModal.tsx`, `frontend/src/tests/playwright/migration_e2e_import.spec.ts`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx` |
| `tests` | 1 | `tests/routes/test_migration_routes.py` |
| `unknown` | 2 | `backend/rag/chatgpt_migration.py`, `guardian/routes/migration.py` |

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

