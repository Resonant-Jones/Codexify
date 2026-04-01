# Daily Audit — 2026-03-29

## Repo Status
- Date: 2026-03-29
- Phase: `evening`
- Branch: `main`
- HEAD: `e4ea73708ad4e149fef631708bfd79b28c10ef81`
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
- Commit count: 23
- Unique files changed: 78
- Files changed: `docs/architecture/2026-03-29-supported-path-proof.md`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/components/chat/Composer.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/components/media/MediaTile.test.tsx`, `frontend/src/components/media/MediaTile.tsx`, `frontend/src/components/modals/ImagePreviewModal.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/features/chat/components/__tests__/ChatBubble.test.tsx`, `frontend/src/features/dashboard/components/DashboardGallery.test.tsx`, `frontend/src/features/dashboard/components/DashboardGallery.tsx`, `frontend/src/hooks/useRenderableMediaSrc.ts`, `frontend/src/lib/mediaUrl.ts`, `frontend/src/test/useRenderableMediaSrc.test.tsx`, `frontend/src/tests/media_rendering.spec.tsx`, `frontend/src/tests/playwright/desktop-media-contract.spec.ts`, `src-tauri/Cargo.lock`, `src-tauri/Cargo.toml`, `src-tauri/src/commands.rs`, `src-tauri/src/lib.rs`, `frontend/src/features/chat/components/__tests__/Message.execution.test.tsx`, `frontend/src/features/chat/useChat.ts`, `frontend/src/types/chat.ts`, `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `guardian/workers/chat_worker.py`, `frontend/src/features/chat/hooks/useTaskEvents.test.tsx`, `frontend/src/features/chat/hooks/useTaskEvents.ts`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/components/__tests__/GuardianActionCenter.test.tsx`, `frontend/src/features/chat/components/__tests__/GuardianApprovalInbox.test.tsx`, `frontend/src/test/utils/mockTaskEvents.ts`, `guardian/core/config.py`, `guardian/guardian_api.py`, `guardian/vector/store.py`, `guardian/workers/document_embed_worker.py`, `tests/routes/test_retrieve_health_or_mount.py`, `tests/vector/test_vector_store_resolution.py`, `tests/workers/test_document_embed_worker.py`, `frontend/src/features/chat/__tests__/useChat.test.ts`, `guardian/core/ai_router.py`, `tests/core/test_ai_router.py`, `tests/routes/test_health_endpoints.py`, `tests/routes/test_llm_catalog.py`, `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/tests/queue/test_task_events.py`, `docs/audits/daily/morning/2026-03-29-audit.json`, `docs/audits/daily/morning/2026-03-29-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/architecture/00-current-state.md`, `docs/architecture/chat-runtime-gap-analysis.md`, `docs/architecture/completion_pipeline.md`, `docs/architecture/flows.md`, `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/chat-runtime-state-contract.md`, `docs/architecture/request-state-machine.md`, `docs/architecture/README.md`, `guardian/core/llm_catalog.py`, `guardian/routes/health.py`, `guardian/core/provider_registry.py`, `guardian/tests/core/test_provider_registry.py`, `guardian/tests/test_llm_catalog_endpoint.py`, `frontend/src/features/workspace/WorkspacePane.spec.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/tests/vite.config.proxy.spec.ts`, `frontend/src/vite.config.ts`, `docs/audits/daily/evening/2026-03-28-audit.json`, `docs/audits/daily/evening/2026-03-28-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `e4ea73708ad4` | Add fresh supported-path proof after runtime hardening | `docs/architecture/2026-03-29-supported-path-proof.md` |
| `f155900866a6` | chore(chat): remove guardian header debug box | `frontend/src/features/chat/GuardianChat.tsx` |
| `61ff812859cb` | Align chat composer send controls with lane padding | `frontend/src/components/chat/Composer.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `e81d8e678cdf` | Adjust composer send button inset | `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `1c06f061988e` | Route backend media through the desktop fetch contract | `frontend/src/components/media/MediaTile.test.tsx`, `frontend/src/components/media/MediaTile.tsx`, `frontend/src/components/modals/ImagePreviewModal.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/features/chat/components/__tests__/ChatBubble.test.tsx`, `frontend/src/features/dashboard/components/DashboardGallery.test.tsx`, `frontend/src/features/dashboard/components/DashboardGallery.tsx`, `frontend/src/hooks/useRenderableMediaSrc.ts`, `frontend/src/lib/mediaUrl.ts`, `frontend/src/test/useRenderableMediaSrc.test.tsx`, `frontend/src/tests/media_rendering.spec.tsx`, `frontend/src/tests/playwright/desktop-media-contract.spec.ts`, `src-tauri/Cargo.lock`, `src-tauri/Cargo.toml`, `src-tauri/src/commands.rs`, `src-tauri/src/lib.rs` |
| `de41700f72a0` | fix(stream): enforce content-only streaming contract and drop reasoning channel | `frontend/src/features/chat/components/__tests__/Message.execution.test.tsx`, `frontend/src/features/chat/useChat.ts`, `frontend/src/types/chat.ts`, `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `guardian/workers/chat_worker.py` |
| `bc74e1322ac1` | Route task event streams through runtime API resolver | `frontend/src/features/chat/hooks/useTaskEvents.test.tsx`, `frontend/src/features/chat/hooks/useTaskEvents.ts` |
| `9622b374cb93` | Tighten composer empty-state balance | `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `1d6e0f7d02b6` | test(chat): align frontend tests with event-driven task lifecycle (remove polling assumptions) | `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/components/__tests__/GuardianActionCenter.test.tsx`, `frontend/src/features/chat/components/__tests__/GuardianApprovalInbox.test.tsx`, `frontend/src/test/utils/mockTaskEvents.ts` |
| `018b9f7ab6df` | Unify vector store resolution across backend and workers | `guardian/core/config.py`, `guardian/guardian_api.py`, `guardian/vector/store.py`, `guardian/workers/document_embed_worker.py`, `tests/routes/test_retrieve_health_or_mount.py`, `tests/vector/test_vector_store_resolution.py`, `tests/workers/test_document_embed_worker.py` |
| `cb7dba45741a` | fix(chat): replace polling with resilient task event stream listener | `frontend/src/features/chat/__tests__/useChat.test.ts`, `frontend/src/features/chat/hooks/useTaskEvents.ts`, `frontend/src/features/chat/useChat.ts` |
| `27f721e03e46` | Enforce resolved local model in local execution paths | `guardian/core/ai_router.py`, `tests/core/test_ai_router.py`, `tests/routes/test_health_endpoints.py`, `tests/routes/test_llm_catalog.py` |
| `a918d44f68ca` | Scope local-model inventory failures to authoritative mode | `guardian/core/ai_router.py`, `tests/core/test_ai_router.py`, `tests/routes/test_llm_catalog.py` |
| `2c1f763ae076` | fix(redis): use queue client + blocking read + backoff for task event streams | `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/tests/queue/test_task_events.py` |
| `c08401a0bfc9` | Refresh daily morning audit snapshot | `docs/audits/daily/morning/2026-03-29-audit.json`, `docs/audits/daily/morning/2026-03-29-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `96dd6704c7ae` | docs(runtime): add chat runtime gap analysis and align architecture docs | `docs/architecture/00-current-state.md`, `docs/architecture/chat-runtime-gap-analysis.md`, `docs/architecture/completion_pipeline.md`, `docs/architecture/flows.md`, `docs/architecture/tech-debt-and-risks.md` |
| `613708e64c92` | Document chat runtime state machine and contract | `docs/architecture/chat-runtime-gap-analysis.md`, `docs/architecture/chat-runtime-state-contract.md`, `docs/architecture/request-state-machine.md` |
| `e35d7be068cb` | docs: refresh weekly current-state override | `docs/architecture/00-current-state.md`, `docs/architecture/README.md` |
| `29b5ee235dbc` | Align local execution model with health and catalog truth | `guardian/core/ai_router.py`, `guardian/core/llm_catalog.py`, `guardian/routes/health.py`, `tests/core/test_ai_router.py`, `tests/routes/test_health_endpoints.py`, `tests/routes/test_llm_catalog.py` |
| `1166207ef620` | fix(llm): enable soft-fallback classification so providers with models are treated as chat-capable when strict detection fails | `guardian/core/llm_catalog.py`, `guardian/core/provider_registry.py`, `guardian/tests/core/test_provider_registry.py`, `guardian/tests/test_llm_catalog_endpoint.py`, `tests/routes/test_llm_catalog.py` |
| `fcbe41220f24` | Fix browser-dev media rendering across shared surfaces | `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/features/chat/components/__tests__/ChatBubble.test.tsx`, `frontend/src/features/workspace/WorkspacePane.spec.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/lib/mediaUrl.ts`, `frontend/src/tests/media_rendering.spec.tsx`, `frontend/src/tests/vite.config.proxy.spec.ts`, `frontend/src/vite.config.ts` |
| `50d3e9cf6124` | Refresh daily evening audit snapshot | `docs/audits/daily/evening/2026-03-28-audit.json`, `docs/audits/daily/evening/2026-03-28-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `3e44dad62afb` | Fix browser-dev media rendering across shared surfaces | `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/features/chat/components/__tests__/ChatBubble.test.tsx`, `frontend/src/features/workspace/WorkspacePane.spec.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/lib/mediaUrl.ts`, `frontend/src/tests/media_rendering.spec.tsx`, `frontend/src/tests/vite.config.proxy.spec.ts`, `frontend/src/vite.config.ts` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/workers/chat_worker.py` |
| `docs` | 9 | `docs/architecture/2026-03-29-supported-path-proof.md`, `docs/architecture/00-current-state.md`, `docs/architecture/chat-runtime-gap-analysis.md`, `docs/architecture/completion_pipeline.md`, `docs/architecture/flows.md`, `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/chat-runtime-state-contract.md`, `docs/architecture/request-state-machine.md`, `docs/architecture/README.md` |
| `audit` | 10 | `docs/audits/daily/morning/2026-03-29-audit.json`, `docs/audits/daily/morning/2026-03-29-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/evening/2026-03-28-audit.json`, `docs/audits/daily/evening/2026-03-28-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md` |
| `config` | 1 | `guardian/core/config.py` |
| `providers` | 7 | `guardian/core/ai_router.py`, `tests/core/test_ai_router.py`, `tests/routes/test_llm_catalog.py`, `guardian/core/llm_catalog.py`, `guardian/core/provider_registry.py`, `guardian/tests/core/test_provider_registry.py`, `guardian/tests/test_llm_catalog_endpoint.py` |
| `ingestion` | 2 | `guardian/workers/document_embed_worker.py`, `tests/workers/test_document_embed_worker.py` |
| `frontend` | 38 | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/components/chat/Composer.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/components/media/MediaTile.test.tsx`, `frontend/src/components/media/MediaTile.tsx`, `frontend/src/components/modals/ImagePreviewModal.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/features/chat/components/__tests__/ChatBubble.test.tsx`, `frontend/src/features/dashboard/components/DashboardGallery.test.tsx`, `frontend/src/features/dashboard/components/DashboardGallery.tsx`, `frontend/src/hooks/useRenderableMediaSrc.ts`, `frontend/src/lib/mediaUrl.ts`, `frontend/src/test/useRenderableMediaSrc.test.tsx`, `frontend/src/tests/media_rendering.spec.tsx`, `frontend/src/tests/playwright/desktop-media-contract.spec.ts`, `src-tauri/Cargo.lock`, `src-tauri/Cargo.toml`, `src-tauri/src/commands.rs`, `src-tauri/src/lib.rs`, `frontend/src/features/chat/components/__tests__/Message.execution.test.tsx`, `frontend/src/features/chat/useChat.ts`, `frontend/src/types/chat.ts`, `frontend/src/features/chat/hooks/useTaskEvents.test.tsx`, `frontend/src/features/chat/hooks/useTaskEvents.ts`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/components/__tests__/GuardianActionCenter.test.tsx`, `frontend/src/features/chat/components/__tests__/GuardianApprovalInbox.test.tsx`, `frontend/src/test/utils/mockTaskEvents.ts`, `frontend/src/features/chat/__tests__/useChat.test.ts`, `frontend/src/features/workspace/WorkspacePane.spec.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/tests/vite.config.proxy.spec.ts`, `frontend/src/vite.config.ts` |
| `tests` | 5 | `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `tests/routes/test_retrieve_health_or_mount.py`, `tests/vector/test_vector_store_resolution.py`, `tests/routes/test_health_endpoints.py`, `guardian/tests/queue/test_task_events.py` |
| `unknown` | 5 | `guardian/guardian_api.py`, `guardian/vector/store.py`, `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/routes/health.py` |

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

