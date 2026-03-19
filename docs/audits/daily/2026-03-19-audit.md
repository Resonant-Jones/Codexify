# Daily Audit — 2026-03-19

## Repo Status
- Date: 2026-03-19
- Branch: `codex/add-daily-audit-generator`
- HEAD: `9a8a0de1a3f011632ad5fb812a64941cb16ab8bd`
- Worktree: dirty
- Status lines:
  - ` M Makefile`
  - `?? docs/audits/daily/2026-03-19-audit.json`
  - `?? docs/audits/daily/2026-03-19-audit.md`
  - `?? docs/audits/latest.json`
  - `?? docs/audits/latest.md`
  - `?? scripts/daily_audit.py`

## Audit CLI Summary
- Selected mode: `text_fallback`
- Attempted commands:
  - `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/venv/bin/python /Users/resonant_jones/.codex/worktrees/9657/Codexify/scripts/audit_platform_readiness.py --json` -> exit 0 (json probe)
  - `/Users/resonant_jones/Keep/Resonant_Constructs/Codexify/venv/bin/python /Users/resonant_jones/.codex/worktrees/9657/Codexify/scripts/audit_platform_readiness.py` -> exit 0 (plain)
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
- Commit count: 6
- Unique files changed: 18
- Files changed: `docs/audits/history/2026-03-19-platform-readiness-baseline.md`, `guardian/core/config.py`, `guardian/core/provider_registry.py`, `guardian/tests/workers/test_warmup_worker.py`, `guardian/workers/warmup_worker.py`, `guardian/tests/workers/test_chat_worker_dequeue_resilience.py`, `guardian/tests/workers/test_voice_worker_dequeue_resilience.py`, `guardian/workers/chat_worker.py`, `guardian/workers/voice_worker.py`, `guardian/guardian_api.py`, `guardian/tests/test_events_outbox.py`, `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/RagTracePanel.test.tsx`, `frontend/src/features/commandCenter/components/RagTracePanel.tsx`, `frontend/src/features/commandCenter/components/RunDetailDrawer.tsx`, `frontend/src/features/commandCenter/hooks/useRagTrace.ts`, `frontend/src/features/commandCenter/types.ts`, `frontend/src/lib/api.ts`

| SHA | Subject | Files |
| --- | --- | --- |
| `9a8a0de1a3f0` | Add platform readiness baseline audit (2026-03-19) | `docs/audits/history/2026-03-19-platform-readiness-baseline.md` |
| `5af25a5fa805` | Add governance alias and module logger to fix NameError in provider registry and config | `guardian/core/config.py`, `guardian/core/provider_registry.py` |
| `1513e2b773bb` | Make startup warmup best effort and low noise | `guardian/tests/workers/test_warmup_worker.py`, `guardian/workers/warmup_worker.py` |
| `17c37b359a06` | Harden chat and voice workers against transient redis dequeue failures | `guardian/tests/workers/test_chat_worker_dequeue_resilience.py`, `guardian/tests/workers/test_voice_worker_dequeue_resilience.py`, `guardian/workers/chat_worker.py`, `guardian/workers/voice_worker.py` |
| `0d53999a9819` | Harden api events stream against transient db restarts | `guardian/guardian_api.py`, `guardian/tests/test_events_outbox.py` |
| `1f87044f0fc0` | Add RAG trace viewer to command center | `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/RagTracePanel.test.tsx`, `frontend/src/features/commandCenter/components/RagTracePanel.tsx`, `frontend/src/features/commandCenter/components/RunDetailDrawer.tsx`, `frontend/src/features/commandCenter/hooks/useRagTrace.ts`, `frontend/src/features/commandCenter/types.ts`, `frontend/src/lib/api.ts` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/workers/chat_worker.py` |
| `audit` | 1 | `docs/audits/history/2026-03-19-platform-readiness-baseline.md` |
| `config` | 1 | `guardian/core/config.py` |
| `providers` | 1 | `guardian/core/provider_registry.py` |
| `frontend` | 7 | `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/RagTracePanel.test.tsx`, `frontend/src/features/commandCenter/components/RagTracePanel.tsx`, `frontend/src/features/commandCenter/components/RunDetailDrawer.tsx`, `frontend/src/features/commandCenter/hooks/useRagTrace.ts`, `frontend/src/features/commandCenter/types.ts`, `frontend/src/lib/api.ts` |
| `tests` | 4 | `guardian/tests/workers/test_warmup_worker.py`, `guardian/tests/workers/test_chat_worker_dequeue_resilience.py`, `guardian/tests/workers/test_voice_worker_dequeue_resilience.py`, `guardian/tests/test_events_outbox.py` |
| `unknown` | 3 | `guardian/workers/warmup_worker.py`, `guardian/workers/voice_worker.py`, `guardian/guardian_api.py` |

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

