# Daily Audit — 2026-03-26

## Repo Status
- Date: 2026-03-26
- Phase: `morning`
- Branch: `main`
- HEAD: `f640a77f6e855e96fd24da0ae3810de1359d749c`
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
- Commit count: 33
- Unique files changed: 81
- Files changed: `.env.template`, `README.md`, `docs/Codexify/CONFIGURATION.md`, `docs/architecture/providers.md`, `frontend/src/components/persona/layout/AppShell.runtimeHealth.test.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/hooks/useRuntimeHealth.ts`, `guardian/cognition/modular_prompt_builder.py`, `guardian/core/ai_router.py`, `guardian/core/chat_completion_service.py`, `guardian/core/config.py`, `guardian/core/provider_registry.py`, `guardian/providers/minimax_adapter.py`, `guardian/providers/registry.py`, `guardian/tests/core/test_ai_router.py`, `guardian/tests/core/test_provider_registry.py`, `guardian/tests/test_llm_catalog_endpoint.py`, `guardian/tests/test_minimax_provider.py`, `guardian/tests/test_minimax_smoke.py`, `guardian/workers/chat_worker.py`, `tests/core/test_ai_router.py`, `tests/routes/test_llm_catalog.py`, `tests/system_prompt/test_modular_prompt_builder.py`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/chatLane.ts`, `docs/Future-Features/Internal-Advanced-Settings-v1.md`, `guardian/core/llm_catalog.py`, `guardian/core/provider_truth.py`, `guardian/routes/health.py`, `guardian/tests/test_health_endpoints.py`, `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `docs/audits/daily/evening/2026-03-25-audit.json`, `docs/audits/daily/evening/2026-03-25-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/features/chat/ChatView.tsx`, `frontend/src/hooks/useUploader.ts`, `guardian/routes/media.py`, `tests/routes/test_media_routes.py`, `scripts/verification/run_supported_path_proof.sh`, `frontend/src/features/chat/__tests__/ChatView.loop-guards.test.tsx`, `guardian/cli/ingest_cli.py`, `guardian/context/broker.py`, `guardian/obsidian/indexer.py`, `tests/core/test_context_broker_depth.py`, `tests/obsidian/test_file_lifecycle.py`, `tests/obsidian/test_indexer.py`, `tests/obsidian/test_ingest_idempotency.py`, `tests/test_chat_payload_summary.py`, `tests/test_chat_worker_turn_integrity.py`, `frontend/src/components/ProviderSelect.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.catalog-options.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx`, `frontend/src/features/chat/components/ComposerSelectMenu.tsx`, `frontend/src/features/chat/hooks/useLlmCatalog.ts`, `.gitignore`, `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/index.css`, `tests/core/test_chat_completion_service_image_routing.py`, `docs/architecture/2026-03-23-supported-path-proof.md`, `guardian/routes/documents.py`, `tests/core/test_chat_completion_service_attachments.py`, `guardian/guardian_api.py`, `guardian/routes/obsidian.py`, `tests/routes/test_obsidian_routes.py`, `guardian/cognition/prompts.py`, `tests/test_retrieval_context_prompt.py`, `guardian/cognition/personas/store.py`, `guardian/cognition/system_prompt_builder.py`, `tests/test_persona_prompt_wiring.py`, `docs/audits/daily/morning/2026-03-25-audit.json`, `docs/audits/daily/morning/2026-03-25-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/architecture/00-current-state.md`, `docs/architecture/README.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `f640a77f6e85` | Add MiniMax Anthropic-first integration | `.env.template`, `README.md`, `docs/Codexify/CONFIGURATION.md`, `docs/architecture/providers.md`, `frontend/src/components/persona/layout/AppShell.runtimeHealth.test.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/hooks/useRuntimeHealth.ts`, `guardian/cognition/modular_prompt_builder.py`, `guardian/core/ai_router.py`, `guardian/core/chat_completion_service.py`, `guardian/core/config.py`, `guardian/core/provider_registry.py`, `guardian/providers/minimax_adapter.py`, `guardian/providers/registry.py`, `guardian/tests/core/test_ai_router.py`, `guardian/tests/core/test_provider_registry.py`, `guardian/tests/test_llm_catalog_endpoint.py`, `guardian/tests/test_minimax_provider.py`, `guardian/tests/test_minimax_smoke.py`, `guardian/workers/chat_worker.py`, `tests/core/test_ai_router.py`, `tests/routes/test_llm_catalog.py`, `tests/system_prompt/test_modular_prompt_builder.py` |
| `47dbc792b72d` | Tuning Guardian Shell to be visually proportionate to the chat lane | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `000e2680caa3` | refactor(guardian): update provider truth wiring | `docs/Future-Features/Internal-Advanced-Settings-v1.md`, `guardian/core/ai_router.py`, `guardian/core/config.py`, `guardian/core/llm_catalog.py`, `guardian/core/provider_registry.py`, `guardian/core/provider_truth.py`, `guardian/routes/health.py`, `guardian/tests/test_health_endpoints.py`, `guardian/tests/test_llm_catalog_endpoint.py`, `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `guardian/workers/chat_worker.py`, `tests/core/test_ai_router.py`, `tests/routes/test_llm_catalog.py` |
| `49b855e3ed24` | refactor(chat): inset and circle send button | `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `5c13de5425ea` | fix(chat): unify shell width with chat lane and remove independent shell max-width | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `a4b021148e76` | refactor(chat): flatten composer inset stack | `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `6d9879575de0` | fix(chat): unify shell width with chat lane and remove independent shell max-width | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `af65545ac2ec` | Update daily evening audit for 2026-03-25 | `docs/audits/daily/evening/2026-03-25-audit.json`, `docs/audits/daily/evening/2026-03-25-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `4912259832b6` | Extract shared chat lane layout constants | `frontend/src/features/chat/ChatView.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `fc0e683abac7` | fix(ui): cap guardian shell width in fullscreen | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `854674c46c8d` | Fix chat uploads and sanitize media upload errors | `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/hooks/useUploader.ts`, `guardian/routes/media.py`, `tests/routes/test_media_routes.py` |
| `5c5a3eb5efd7` | feat(release): add supported-path proof runner script | `scripts/verification/run_supported_path_proof.sh` |
| `000f37e98b75` | merge: reconcile PR 162 chat composer layout conflicts | `frontend/src/features/chat/ChatView.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/ChatView.loop-guards.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `3c9ed4d006c0` | Align chat lane and composer width and anchor controls at bottom | `frontend/src/features/chat/ChatView.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/ChatView.loop-guards.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx` |
| `583936234041` | feat(obsidian): add read-only vault indexing for beta | `guardian/cli/ingest_cli.py`, `guardian/context/broker.py`, `guardian/core/chat_completion_service.py`, `guardian/obsidian/indexer.py`, `tests/core/test_context_broker_depth.py`, `tests/obsidian/test_file_lifecycle.py`, `tests/obsidian/test_indexer.py`, `tests/obsidian/test_ingest_idempotency.py`, `tests/test_chat_payload_summary.py` |
| `91ca4ad617cc` | Fix gallery image src paths in AppShell | `frontend/src/components/persona/layout/AppShell.tsx` |
| `f15cff897af5` | fix(chat): restore completion compatibility after multimodal gating | `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `tests/test_chat_worker_turn_integrity.py` |
| `7b9aa6760ad1` | fix(ui): tighten chat lane and composer density | `frontend/src/features/chat/ChatView.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/Composer.tsx` |
| `442d159ac291` | fix(chat): gate model selection by capability | `frontend/src/components/ProviderSelect.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.catalog-options.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/ComposerSelectMenu.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/features/chat/hooks/useLlmCatalog.ts`, `guardian/core/llm_catalog.py`, `guardian/core/provider_registry.py`, `guardian/tests/core/test_provider_registry.py`, `tests/routes/test_llm_catalog.py` |
| `ee0f9fbba8b0` | Remove duplicate compound-mcp-server-main entry from .gitignore | `.gitignore` |
| `71e83c921e7c` | Fix code block extraction in chat pre renderer | `frontend/src/features/chat/components/ChatBubble.tsx` |
| `f2f23c3f5614` | Enhance chat code blocks with header and copy button | `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/index.css` |
| `fa2811a86887` | feat(chat): add multimodal image routing contract | `guardian/core/ai_router.py`, `guardian/core/chat_completion_service.py`, `guardian/core/provider_registry.py`, `guardian/routes/media.py`, `tests/core/test_chat_completion_service_image_routing.py` |
| `d448071deb7f` | docs(audit): refresh supported path proof after prompt integrity fixes | `docs/architecture/2026-03-23-supported-path-proof.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `43ab90f016dd` | fix(chat): restore worker compatibility after prompt wiring | `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py` |
| `25bc3e8bbebb` | Link uploaded documents to project scope and fix broker sessions | `guardian/context/broker.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/documents.py`, `guardian/routes/media.py`, `tests/core/test_chat_completion_service_attachments.py`, `tests/core/test_context_broker_depth.py`, `tests/routes/test_media_routes.py` |
| `2e04790ceb0d` | fix(ui): unify chat lane alignment across breakpoints | `frontend/src/features/chat/ChatView.tsx`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/chatLane.ts` |
| `36fec4608275` | Add Obsidian config and indexing routes | `guardian/guardian_api.py`, `guardian/obsidian/indexer.py`, `guardian/routes/obsidian.py`, `tests/routes/test_obsidian_routes.py` |
| `54c745f78e36` | fix(chat): wire retrieval context into prompt assembly | `guardian/cognition/prompts.py`, `guardian/core/chat_completion_service.py`, `guardian/workers/chat_worker.py`, `tests/test_chat_payload_summary.py`, `tests/test_retrieval_context_prompt.py` |
| `5972b4c5b67d` | Add Obsidian config and indexing routes | `guardian/guardian_api.py`, `guardian/obsidian/indexer.py`, `guardian/routes/obsidian.py`, `tests/routes/test_obsidian_routes.py` |
| `2aafd4c90185` | fix(chat): wire saved persona into system prompt | `guardian/cognition/personas/store.py`, `guardian/cognition/system_prompt_builder.py`, `guardian/core/chat_completion_service.py`, `tests/test_chat_worker_turn_integrity.py`, `tests/test_persona_prompt_wiring.py` |
| `97af4512e929` | Update daily morning audit to 2026-03-25 | `docs/audits/daily/morning/2026-03-25-audit.json`, `docs/audits/daily/morning/2026-03-25-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `ac57d5612422` | docs: refresh weekly current-state override | `docs/architecture/00-current-state.md`, `docs/architecture/README.md` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/workers/chat_worker.py` |
| `docs` | 5 | `docs/Codexify/CONFIGURATION.md`, `docs/Future-Features/Internal-Advanced-Settings-v1.md`, `docs/architecture/2026-03-23-supported-path-proof.md`, `docs/architecture/00-current-state.md`, `docs/architecture/README.md` |
| `audit` | 10 | `docs/audits/daily/evening/2026-03-25-audit.json`, `docs/audits/daily/evening/2026-03-25-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/morning/2026-03-25-audit.json`, `docs/audits/daily/morning/2026-03-25-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md` |
| `config` | 2 | `.env.template`, `guardian/core/config.py` |
| `providers` | 14 | `docs/architecture/providers.md`, `guardian/core/ai_router.py`, `guardian/core/provider_registry.py`, `guardian/providers/minimax_adapter.py`, `guardian/providers/registry.py`, `guardian/tests/core/test_ai_router.py`, `guardian/tests/core/test_provider_registry.py`, `guardian/tests/test_llm_catalog_endpoint.py`, `guardian/tests/test_minimax_provider.py`, `tests/core/test_ai_router.py`, `tests/routes/test_llm_catalog.py`, `guardian/core/llm_catalog.py`, `guardian/core/provider_truth.py`, `frontend/src/components/ProviderSelect.tsx` |
| `ingestion` | 3 | `guardian/routes/media.py`, `guardian/cli/ingest_cli.py`, `tests/obsidian/test_ingest_idempotency.py` |
| `frontend` | 17 | `frontend/src/components/persona/layout/AppShell.runtimeHealth.test.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/hooks/useRuntimeHealth.ts`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/features/chat/chatLane.ts`, `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/features/chat/components/__tests__/Composer.draft-sync.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.session-tabs.test.tsx`, `frontend/src/features/chat/ChatView.tsx`, `frontend/src/hooks/useUploader.ts`, `frontend/src/features/chat/__tests__/ChatView.loop-guards.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.catalog-options.test.tsx`, `frontend/src/features/chat/__tests__/GuardianChat.turn-lock-lifecycle.test.tsx`, `frontend/src/features/chat/components/ComposerSelectMenu.tsx`, `frontend/src/features/chat/hooks/useLlmCatalog.ts`, `frontend/src/features/chat/components/ChatBubble.tsx`, `frontend/src/index.css` |
| `tests` | 15 | `guardian/tests/test_minimax_smoke.py`, `tests/system_prompt/test_modular_prompt_builder.py`, `guardian/tests/test_health_endpoints.py`, `guardian/tests/workers/test_chat_worker_completion_semantics.py`, `tests/routes/test_media_routes.py`, `tests/core/test_context_broker_depth.py`, `tests/obsidian/test_file_lifecycle.py`, `tests/obsidian/test_indexer.py`, `tests/test_chat_payload_summary.py`, `tests/test_chat_worker_turn_integrity.py`, `tests/core/test_chat_completion_service_image_routing.py`, `tests/core/test_chat_completion_service_attachments.py`, `tests/routes/test_obsidian_routes.py`, `tests/test_retrieval_context_prompt.py`, `tests/test_persona_prompt_wiring.py` |
| `infra` | 1 | `scripts/verification/run_supported_path_proof.sh` |
| `unknown` | 13 | `README.md`, `guardian/cognition/modular_prompt_builder.py`, `guardian/core/chat_completion_service.py`, `guardian/routes/health.py`, `guardian/context/broker.py`, `guardian/obsidian/indexer.py`, `.gitignore`, `guardian/routes/documents.py`, `guardian/guardian_api.py`, `guardian/routes/obsidian.py`, `guardian/cognition/prompts.py`, `guardian/cognition/personas/store.py`, `guardian/cognition/system_prompt_builder.py` |

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

