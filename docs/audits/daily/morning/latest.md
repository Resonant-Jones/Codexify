# Daily Audit — 2026-03-28

## Repo Status
- Date: 2026-03-28
- Phase: `morning`
- Branch: `main`
- HEAD: `3614726a20ffbbc65575d99352f9832deddf4272`
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
- Commit count: 5
- Unique files changed: 20
- Files changed: `guardian/queue/redis_queue.py`, `guardian/tests/queue/test_redis_queue_clients.py`, `scripts/agent_task_worker.py`, `guardian/routes/chat.py`, `guardian/routes/health.py`, `guardian/routes/ui_session.py`, `docs/architecture/router-decision-table.md`, `guardian/context/retrieval_router_policy.py`, `tests/context/test_retrieval_router_policy.py`, `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/hooks/useLiveEvents.ts`, `frontend/src/lib/events/types.ts`, `frontend/src/lib/liveEventsHub.ts`, `frontend/src/test/live-events-singleton.test.tsx`, `docs/audits/daily/morning/2026-03-27-audit.json`, `docs/audits/daily/morning/2026-03-27-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `3614726a20ff` | fix(redis): enforce queue client usage for blocking operations | `guardian/queue/redis_queue.py`, `guardian/tests/queue/test_redis_queue_clients.py`, `scripts/agent_task_worker.py` |
| `9e1fcdfd304c` | fix(backend): enforce redis fail-fast and 503 degradation contract | `guardian/queue/redis_queue.py`, `guardian/routes/chat.py`, `guardian/routes/health.py`, `guardian/routes/ui_session.py` |
| `ab07c419d71a` | Add canonical retrieval router policy scaffold | `docs/architecture/router-decision-table.md`, `guardian/context/retrieval_router_policy.py`, `tests/context/test_retrieval_router_policy.py` |
| `ac53cba41425` | Introduce canonical LiveEvent normalization | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/hooks/useLiveEvents.ts`, `frontend/src/lib/events/types.ts`, `frontend/src/lib/liveEventsHub.ts`, `frontend/src/test/live-events-singleton.test.tsx` |
| `9319ecda6a9e` | Weekly and Daily Audit Reports | `docs/audits/daily/morning/2026-03-27-audit.json`, `docs/audits/daily/morning/2026-03-27-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/routes/chat.py` |
| `docs` | 1 | `docs/architecture/router-decision-table.md` |
| `audit` | 6 | `docs/audits/daily/morning/2026-03-27-audit.json`, `docs/audits/daily/morning/2026-03-27-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `frontend` | 5 | `frontend/src/features/chat/GuardianChat.tsx`, `frontend/src/hooks/useLiveEvents.ts`, `frontend/src/lib/events/types.ts`, `frontend/src/lib/liveEventsHub.ts`, `frontend/src/test/live-events-singleton.test.tsx` |
| `tests` | 2 | `guardian/tests/queue/test_redis_queue_clients.py`, `tests/context/test_retrieval_router_policy.py` |
| `unknown` | 5 | `guardian/queue/redis_queue.py`, `scripts/agent_task_worker.py`, `guardian/routes/health.py`, `guardian/routes/ui_session.py`, `guardian/context/retrieval_router_policy.py` |

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

