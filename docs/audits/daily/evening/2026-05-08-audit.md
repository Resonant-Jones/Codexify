# Daily Audit — 2026-05-08

## Repo Status
- Date: 2026-05-08
- Phase: `evening`
- Branch: `codex/run-readiness-audit`
- HEAD: `6e0fca808c3e48d8d543da2499cdb181c4107de4`
- Worktree: dirty
- Status lines:
  - `M  docs/architecture/2026-05-08-supported-profile-live-proof.md`
  - `M  docs/architecture/flows.md`
  - `MM guardian/db/models.py`
  - `M  guardian/routes/documents.py`
  - `M  guardian/routes/media.py`
  - `M  guardian/workers/document_embed_worker.py`
  - `M  tests/proofs/test_supported_profile_live_proof_contract.py`
  - `M  tests/routes/test_documents.py`
  - `M  tests/routes/test_media_upload.py`

## Audit CLI Summary
- Selected mode: `text_fallback`
- Attempted commands:
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/audit_platform_readiness.py --json` -> exit 0 (json probe)
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/Codexify/scripts/audit_platform_readiness.py` -> exit 0 (plain)
- Summary counts: PASS 42, WARN 12, FAIL 0
- Strongest evidence: `Extension Boundary`, `Core Loop Integrity`, `Primitive Stability`
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
- Commit count: 19
- Unique files changed: 51
- Files changed: `guardian/core/chat_completion_service.py`, `tests/core/test_chat_completion_service_model_selection_trace.py`, `docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md`, `guardian/routes/chat.py`, `guardian/memory_graph/graph_backend.py`, `tests/memory_graph/test_graph_backend_adapter.py`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/hooks/useUploader.ts`, `docs/audits/daily/evening/2026-05-08-audit.json`, `docs/audits/daily/evening/2026-05-08-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/architecture/00-current-state.md`, `docs/architecture/2026-05-08-supported-profile-live-proof.md`, `docker-compose.yml`, `docs/architecture/README.md`, `docs/architecture/adr/026-graph-write-runtime-flag-boundary-on-supported-compose-path.md`, `docs/architecture/adr/adr-index.md`, `docs/architecture/candidate-ingest-pipeline.md`, `docs/architecture/config-and-ops.md`, `docs/architecture/memory-graph-indexing-plan.md`, `guardian/core/config.py`, `guardian/memory_graph/graph_backend_factory.py`, `guardian/workers/graph_write_worker.py`, `tests/memory_graph/test_graph_backend_factory.py`, `tests/workers/test_graph_write_worker.py`, `docs/proofs/2026-05-07-neo4j-graph-backend-live-proof.md`, `docs/proofs/2026-05-07-platform-readiness-audit-extension-boundary-proof.md`, `scripts/audit_platform_readiness.py`, `tests/scripts/test_audit_platform_readiness.py`, `docs/architecture/adr/025-neo4j-graph-backend-adapter-flagged-off-by-default.md`, `guardian/memory_graph/neo4j_graph_backend.py`, `guardian/memory_graph/noop_graph_backend.py`, `tests/memory_graph/test_neo4j_graph_backend.py`, `docs/architecture/self-extending-agent-plugin-system.md`, `guardian/extensions/contracts.py`, `guardian/extensions/reentry.py`, `guardian/extensions/tokens.py`, `tests/extensions/test_capability_one_turn_reentry.py`, `docs/DEV_LOG/2026-05-07/Dev Log - 2026-05-07`, `docs/architecture/flows.md`, `docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md`, `docs/proofs/2026-05-04-image-turn-containment-proof.md`, `tests/context/test_retrieval_trace_provenance.py`, `tests/contracts/test_protocol_tokens.py`, `tests/routes/test_chat_profile_trace.py`, `tests/routes/test_image_turn_live_trace_contract.py`, `guardian/context/broker.py`

| SHA | Subject | Files |
| --- | --- | --- |
| `6e0fca808c3e` | fix(chat): repair model selection trace helper invocation on main | `guardian/core/chat_completion_service.py`, `tests/core/test_chat_completion_service_model_selection_trace.py` |
| `135d7ed64cdd` | docs(proof): re-run neo4j graph backend live proof after runtime boundary fix | `docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md` |
| `8654bcc22d18` | docs(proof): re-run neo4j graph backend live proof after runtime boundary fix | `docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md`, `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py` |
| `f947a407201d` | fix: repair graph backend syntax errors and merge conflicts | `guardian/memory_graph/graph_backend.py`, `tests/memory_graph/test_graph_backend_adapter.py` |
| `ba47588bd3fe` | Merge remote-tracking branch 'origin/main' into main | `guardian/memory_graph/graph_backend.py` |
| `dd8fd19233a4` | Harden stored general project context | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/hooks/useUploader.ts` |
| `8b6eb383909f` | docs: capture fresh platform readiness audit | `docs/audits/daily/evening/2026-05-08-audit.json`, `docs/audits/daily/evening/2026-05-08-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `a5881aefa3b8` | docs: add 2026-05-08 supported profile live proof (PARTIAL) | `docs/architecture/00-current-state.md`, `docs/architecture/2026-05-08-supported-profile-live-proof.md` |
| `9ca4caf56973` | fix: enforce default-off graph write runtime boundary on compose path | `docker-compose.yml`, `docs/architecture/README.md`, `docs/architecture/adr/026-graph-write-runtime-flag-boundary-on-supported-compose-path.md`, `docs/architecture/adr/adr-index.md`, `docs/architecture/candidate-ingest-pipeline.md`, `docs/architecture/config-and-ops.md`, `docs/architecture/memory-graph-indexing-plan.md`, `guardian/core/config.py`, `guardian/memory_graph/graph_backend_factory.py`, `guardian/workers/graph_write_worker.py`, `tests/memory_graph/test_graph_backend_factory.py`, `tests/workers/test_graph_write_worker.py` |
| `8cbf733c96dd` | docs(proof): capture live neo4j graph backend proof behind explicit flag | `docs/proofs/2026-05-07-neo4j-graph-backend-live-proof.md` |
| `ae1ee8f9f5b8` | fix: align readiness audit extension boundary checks | `docs/proofs/2026-05-07-platform-readiness-audit-extension-boundary-proof.md`, `scripts/audit_platform_readiness.py`, `tests/scripts/test_audit_platform_readiness.py` |
| `1ae2bcb31c7e` | feat: add feature-flagged neo4j graph backend behind adapter seam | `docs/architecture/README.md`, `docs/architecture/adr/025-neo4j-graph-backend-adapter-flagged-off-by-default.md`, `docs/architecture/adr/adr-index.md`, `docs/architecture/candidate-ingest-pipeline.md`, `docs/architecture/config-and-ops.md`, `docs/architecture/memory-graph-indexing-plan.md`, `guardian/core/config.py`, `guardian/memory_graph/graph_backend.py`, `guardian/memory_graph/graph_backend_factory.py`, `guardian/memory_graph/neo4j_graph_backend.py`, `guardian/memory_graph/noop_graph_backend.py`, `guardian/workers/graph_write_worker.py`, `tests/memory_graph/test_graph_backend_adapter.py`, `tests/memory_graph/test_graph_backend_factory.py`, `tests/memory_graph/test_neo4j_graph_backend.py`, `tests/workers/test_graph_write_worker.py` |
| `c9427bb2f815` | feat: add one-turn assistant reentry seam | `docs/architecture/self-extending-agent-plugin-system.md`, `guardian/core/chat_completion_service.py`, `guardian/extensions/contracts.py`, `guardian/extensions/reentry.py`, `guardian/extensions/tokens.py`, `tests/extensions/test_capability_one_turn_reentry.py` |
| `dffb8f66a49d` | fix: repair chat route trace evidence block | `guardian/routes/chat.py` |
| `f2dc2d93e2a6` | Capture workspace obsidian e2e proof | `docs/DEV_LOG/2026-05-07/Dev Log - 2026-05-07` |
| `09a6ceeca943` | docs(proof): capture workspace obsidian e2e proof | `docs/architecture/00-current-state.md`, `docs/architecture/flows.md`, `docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md` |
| `b04f9ec52bd3` | tests: repair image-turn regression syntax gate | `docs/proofs/2026-05-04-image-turn-containment-proof.md`, `guardian/core/chat_completion_service.py`, `guardian/routes/chat.py`, `tests/context/test_retrieval_trace_provenance.py`, `tests/contracts/test_protocol_tokens.py`, `tests/routes/test_chat_profile_trace.py`, `tests/routes/test_image_turn_live_trace_contract.py` |
| `09d849af87ae` | docs(proof): capture workspace obsidian e2e proof | `docs/architecture/00-current-state.md`, `docs/architecture/flows.md`, `docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md` |
| `9f083c7141c6` | fix: repair context broker result filtering block | `guardian/context/broker.py` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/routes/chat.py` |
| `docs` | 16 | `docs/proofs/2026-05-08-neo4j-graph-backend-live-proof-after-runtime-boundary-fix.md`, `docs/architecture/00-current-state.md`, `docs/architecture/2026-05-08-supported-profile-live-proof.md`, `docs/architecture/README.md`, `docs/architecture/adr/026-graph-write-runtime-flag-boundary-on-supported-compose-path.md`, `docs/architecture/adr/adr-index.md`, `docs/architecture/config-and-ops.md`, `docs/architecture/memory-graph-indexing-plan.md`, `docs/proofs/2026-05-07-neo4j-graph-backend-live-proof.md`, `docs/proofs/2026-05-07-platform-readiness-audit-extension-boundary-proof.md`, `docs/architecture/adr/025-neo4j-graph-backend-adapter-flagged-off-by-default.md`, `docs/architecture/self-extending-agent-plugin-system.md`, `docs/DEV_LOG/2026-05-07/Dev Log - 2026-05-07`, `docs/architecture/flows.md`, `docs/proofs/2026-05-07-workspace-obsidian-e2e-proof.md`, `docs/proofs/2026-05-04-image-turn-containment-proof.md` |
| `audit` | 8 | `docs/audits/daily/evening/2026-05-08-audit.json`, `docs/audits/daily/evening/2026-05-08-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `scripts/audit_platform_readiness.py`, `tests/scripts/test_audit_platform_readiness.py` |
| `config` | 1 | `guardian/core/config.py` |
| `ingestion` | 1 | `docs/architecture/candidate-ingest-pipeline.md` |
| `frontend` | 3 | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/hooks/useUploader.ts` |
| `tests` | 10 | `tests/core/test_chat_completion_service_model_selection_trace.py`, `tests/memory_graph/test_graph_backend_adapter.py`, `tests/memory_graph/test_graph_backend_factory.py`, `tests/workers/test_graph_write_worker.py`, `tests/memory_graph/test_neo4j_graph_backend.py`, `tests/extensions/test_capability_one_turn_reentry.py`, `tests/context/test_retrieval_trace_provenance.py`, `tests/contracts/test_protocol_tokens.py`, `tests/routes/test_chat_profile_trace.py`, `tests/routes/test_image_turn_live_trace_contract.py` |
| `infra` | 1 | `docker-compose.yml` |
| `unknown` | 10 | `guardian/core/chat_completion_service.py`, `guardian/memory_graph/graph_backend.py`, `guardian/memory_graph/graph_backend_factory.py`, `guardian/workers/graph_write_worker.py`, `guardian/memory_graph/neo4j_graph_backend.py`, `guardian/memory_graph/noop_graph_backend.py`, `guardian/extensions/contracts.py`, `guardian/extensions/reentry.py`, `guardian/extensions/tokens.py`, `guardian/context/broker.py` |

## Risk Flags
- `chat_depends_on_redis_and_workers`: Chat completion is queue-coupled and depends on Redis plus worker availability. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- `config_split_brain_risk`: Canonical and legacy config paths still coexist, so startup and operator state can drift. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- `legacy_tools_and_command_bus_duality`: Legacy /tools behavior and the command bus still overlap, which increases contract drift risk. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`
- `sync_not_durable`: Sync subscriptions are still process-local rather than durable across restarts. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`, `docs/architecture/data-and-storage.md`
- `federation_high_blast_radius`: Federation remains sensitive to trust policy, feature flags, and egress behavior. Evidence: `docs/architecture/tech-debt-and-risks.md`, `docs/architecture/roadmap-signals.md`

## Notable Change From Prior Audit
- Extension Boundary no longer fails solely because legacy `guardian/routes/tools.py` is absent; this run records `FAIL 0`.
- `--json` remains unsupported by `scripts/audit_platform_readiness.py` in this checkout (the `--json` probe returned non-JSON text), so this capture stays in `text_fallback` mode.
- No release-promise widening is implied by this capture.

## Manual Review Summary
- Domains requiring human review: `Alternate Surface Readiness`, `Governance Readiness`
- Primary cautions: federation remains high-blast-radius and config-sensitive; sync subscriptions remain process-local; observability docs still carry unverified logging guarantees.

## Manual Notes
- Finished today: Captured fresh 2026-05-08 evening readiness artifacts after Extension Boundary audit repair and updated latest pointers.
- Blocked: `scripts/audit_platform_readiness.py --json` returned non-JSON text output; JSON capture remains via fallback schema.
- Next priority: Keep current-state/release truth synchronized with future readiness deltas, especially if any new FAIL appears.
