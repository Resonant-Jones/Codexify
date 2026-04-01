# Daily Audit — 2026-04-01

## Repo Status
- Date: 2026-04-01
- Phase: `morning`
- Branch: `main`
- HEAD: `969355bf438b3e7d678c506ec7f46052b0f297bf`
- Worktree: dirty
- Status lines:
  - `?? docs/architecture/persona-studio-spec.md`

## Audit CLI Summary
- Selected mode: `text_fallback`
- Attempted commands:
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/audit_platform_readiness.py --json` -> exit 0 (json probe)
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/audit_platform_readiness.py` -> exit 0 (plain)
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
- Commit count: 29
- Unique files changed: 60
- Files changed: `docs/audits/daily/evening/2026-03-31-audit.json`, `docs/audits/daily/evening/2026-03-31-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/main.tsx`, `backend/rag/embedder.py`, `docker-compose.yml`, `guardian/core/config.py`, `guardian/workers/document_embed_worker.py`, `tests/backend/rag/test_embedder.py`, `tests/workers/test_document_embed_worker.py`, `docs/architecture/2026-03-31-supported-path-proof.md`, `frontend/src/components/SessionRail/SessionRail.tsx`, `frontend/src/components/SessionRail/__tests__/SessionRail.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceTabs.test.tsx`, `frontend/src/index.css`, `frontend/src/components/persona/layout/AppShell.runtimeHealth.test.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/useChat.ts`, `guardian/cognition/prompts.py`, `tests/core/test_chat_completion_service_retrieval_plan.py`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceInspectorPanel.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceShelfPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceInspectorPanel.tsx`, `frontend/src/features/workspace/components/WorkspaceShelfPanel.tsx`, `docs/architecture/2026-03-31-rag-trace-e2e-proof.md`, `tests/routes/test_chat_profile_trace.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py`, `frontend/src/features/workspace/__tests__/WorkspaceScratchpadPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceScratchpadPanel.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/panels/RAGTracePanel.tsx`, `frontend/src/features/settings/SettingsView.test.tsx`, `frontend/src/features/settings/SettingsView.tsx`, `frontend/src/features/settings/diagnostics/MemoryBrowser.tsx`, `frontend/src/package.json`, `guardian/context/broker.py`, `tests/core/test_context_broker_source_mode.py`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.source-selector.test.tsx`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/architecture/2026-03-31-source-selector-proof.md`, `tests/core/test_chat_completion_service_source_mode_fallback.py`, `tests/routes/test_chat_source_mode.py`, `frontend/src/components/ui/__tests__/dropdown-menu.portal.test.tsx`, `frontend/src/components/ui/dropdown-menu.tsx`, `frontend/src/features/chat/components/ComposerSelectMenu.tsx`, `frontend/src/features/chat/components/__tests__/ComposerSelectMenu.test.tsx`, `docs/architecture/runtime-protocol-token-contract.md`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts`

| SHA | Subject | Files |
| --- | --- | --- |
| `969355bf438b` | Refresh daily evening audit snapshot | `docs/audits/daily/evening/2026-03-31-audit.json`, `docs/audits/daily/evening/2026-03-31-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/main.tsx` |
| `a7d9f8200ceb` | fix(embed): complete document embed lifecycle and terminal status handling | `backend/rag/embedder.py`, `docker-compose.yml`, `guardian/core/config.py`, `guardian/workers/document_embed_worker.py`, `tests/backend/rag/test_embedder.py`, `tests/workers/test_document_embed_worker.py` |
| `f0596e1dee48` | docs(proof): add fresh supported-path proof for runtime contract behavior | `docs/architecture/2026-03-31-supported-path-proof.md` |
| `5318886dd69d` | fix(chat): apply segmented styling to session rail | `frontend/src/components/SessionRail/SessionRail.tsx`, `frontend/src/components/SessionRail/__tests__/SessionRail.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx` |
| `72ebb44110c5` | refactor(workspace): localize session rail styles | `frontend/src/features/workspace/__tests__/WorkspaceTabs.test.tsx`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/index.css` |
| `902112ce5447` | feat(chat): implement frontend runtime contract for provider and request state | `frontend/src/components/persona/layout/AppShell.runtimeHealth.test.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/useChat.ts` |
| `5880120e7a7b` | fix(chat): make retrieval boundary language truthful | `guardian/cognition/prompts.py`, `tests/core/test_chat_completion_service_retrieval_plan.py` |
| `d5abf6353579` | refactor(workspace): enforce segmented session rail tabs | `frontend/src/features/workspace/__tests__/WorkspaceTabs.test.tsx`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/index.css` |
| `8f7d6f6e0f29` | feat(workspace): connect shelf documents to inspector | `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceInspectorPanel.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceShelfPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceInspectorPanel.tsx`, `frontend/src/features/workspace/components/WorkspaceShelfPanel.tsx` |
| `1b33c01b9d3d` | feat(workspace): wire shelf to thread and project artifacts | `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceShelfPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceShelfPanel.tsx` |
| `0d0bc059869b` | docs(chat): add end-to-end rag trace proof | `docs/architecture/2026-03-31-rag-trace-e2e-proof.md`, `tests/routes/test_chat_profile_trace.py` |
| `9e8bd6d8dc29` | fix(chat): restore latest rag trace persistence | `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py`, `tests/core/test_chat_completion_service_retrieval_plan.py`, `tests/routes/test_chat_profile_trace.py` |
| `6be727c355e5` | refactor(workspace): strengthen tab switcher hierarchy | `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceScratchpadPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceScratchpadPanel.tsx`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx` |
| `bfd2046060d6` | Refine Guardian base prompt for co-creative companion behavior | `guardian/cognition/prompts.py` |
| `368afb1b41b3` | fix(diagnostics): bind rag trace surfaces to active thread | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/panels/RAGTracePanel.tsx`, `frontend/src/features/settings/SettingsView.test.tsx`, `frontend/src/features/settings/SettingsView.tsx`, `frontend/src/features/settings/diagnostics/MemoryBrowser.tsx` |
| `37c2162c2bff` | Force Vite re-optimization on frontend dev startup | `frontend/src/package.json` |
| `2ea451bc13a2` | refactor(shell): simplify session rail visual hierarchy | `frontend/src/components/SessionRail/SessionRail.tsx`, `frontend/src/components/SessionRail/__tests__/SessionRail.test.tsx` |
| `a90b2c33f4ad` | fix(chat): replace weak local hit during widening | `guardian/context/broker.py`, `tests/core/test_context_broker_source_mode.py` |
| `e64dec215ea9` | fix(chat): simplify source selector trigger label | `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.source-selector.test.tsx` |
| `06af0f2351b0` | fix(workspace): remove redundant internal close button | `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx` |
| `727f8f0918be` | refactor(workspace): polish header and scratchpad layout | `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceScratchpadPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceScratchpadPanel.tsx`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx` |
| `85da3a918748` | Refresh latest audit reports | `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `e2539f35eaa3` | test(chat): harden source selector proof and fallback behavior | `docs/architecture/2026-03-31-source-selector-proof.md`, `guardian/context/broker.py`, `guardian/routes/chat.py`, `tests/core/test_chat_completion_service_source_mode_fallback.py`, `tests/core/test_context_broker_source_mode.py`, `tests/routes/test_chat_source_mode.py` |
| `0c35af4239c5` | fix(ui): constrain model menu and open upward | `frontend/src/components/ui/__tests__/dropdown-menu.portal.test.tsx`, `frontend/src/components/ui/dropdown-menu.tsx`, `frontend/src/features/chat/components/ComposerSelectMenu.tsx`, `frontend/src/features/chat/components/__tests__/ComposerSelectMenu.test.tsx` |
| `61c696b92e1c` | feat(chat): add source selector for retrieval boundary | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.source-selector.test.tsx`, `guardian/context/broker.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py`, `tests/core/test_context_broker_source_mode.py`, `tests/routes/test_chat_source_mode.py` |
| `757fc402acf4` | docs(runtime): expand protocol token contract to include provider and request lifecycle domains | `docs/architecture/runtime-protocol-token-contract.md` |
| `afec57d252d2` | fix(workspace): clean up posture header affordances | `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx` |
| `45eb65e5457f` | feat(workspace): make workspace focus visually dominant | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts` |
| `03f128bc5013` | feat(workspace): add layout mode state contract | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/routes/chat.py` |
| `docs` | 4 | `docs/architecture/2026-03-31-supported-path-proof.md`, `docs/architecture/2026-03-31-rag-trace-e2e-proof.md`, `docs/architecture/2026-03-31-source-selector-proof.md`, `docs/architecture/runtime-protocol-token-contract.md` |
| `audit` | 8 | `docs/audits/daily/evening/2026-03-31-audit.json`, `docs/audits/daily/evening/2026-03-31-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md` |
| `config` | 1 | `guardian/core/config.py` |
| `ingestion` | 2 | `guardian/workers/document_embed_worker.py`, `tests/workers/test_document_embed_worker.py` |
| `frontend` | 33 | `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/main.tsx`, `frontend/src/components/SessionRail/SessionRail.tsx`, `frontend/src/components/SessionRail/__tests__/SessionRail.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceTabs.test.tsx`, `frontend/src/index.css`, `frontend/src/components/persona/layout/AppShell.runtimeHealth.test.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/useChat.ts`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceInspectorPanel.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceShelfPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/components/WorkspaceInspectorPanel.tsx`, `frontend/src/features/workspace/components/WorkspaceShelfPanel.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceScratchpadPanel.test.tsx`, `frontend/src/features/workspace/components/WorkspaceScratchpadPanel.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/panels/RAGTracePanel.tsx`, `frontend/src/features/settings/SettingsView.test.tsx`, `frontend/src/features/settings/SettingsView.tsx`, `frontend/src/features/settings/diagnostics/MemoryBrowser.tsx`, `frontend/src/package.json`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.source-selector.test.tsx`, `frontend/src/components/ui/__tests__/dropdown-menu.portal.test.tsx`, `frontend/src/components/ui/dropdown-menu.tsx`, `frontend/src/features/chat/components/ComposerSelectMenu.tsx`, `frontend/src/features/chat/components/__tests__/ComposerSelectMenu.test.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts` |
| `tests` | 6 | `tests/backend/rag/test_embedder.py`, `tests/core/test_chat_completion_service_retrieval_plan.py`, `tests/routes/test_chat_profile_trace.py`, `tests/core/test_context_broker_source_mode.py`, `tests/core/test_chat_completion_service_source_mode_fallback.py`, `tests/routes/test_chat_source_mode.py` |
| `infra` | 1 | `docker-compose.yml` |
| `unknown` | 4 | `backend/rag/embedder.py`, `guardian/cognition/prompts.py`, `guardian/core/chat_completion_service.py`, `guardian/context/broker.py` |

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

