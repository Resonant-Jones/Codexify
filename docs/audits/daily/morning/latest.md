# Daily Audit — 2026-05-19

## Repo Status
- Date: 2026-05-19
- Phase: `morning`
- Branch: `main`
- HEAD: `d1574f7954c6bcd06b58b84ef331d35dc568c5c4`
- Worktree: dirty
- Status lines:
  - ` D docs/architecture/00-current-state.md`

## Audit CLI Summary
- Selected mode: `json`
- Attempted commands:
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify/scripts/audit_platform_readiness.py --json` -> exit 0 (json)

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
- Commit count: 4
- Unique files changed: 18
- Files changed: `docker-compose.yml`, `docs/audits/daily/evening/2026-05-18-audit.json`, `docs/audits/daily/evening/2026-05-18-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/features/commandCenter/api.ts`, `guardian/workers/coding_worker.py`, `config/supported_profiles/v1-local-core-web-mcp.yaml`, `guardian/guardian_api.py`, `tests/core/test_supported_profile.py`, `tests/routes/test_retrieve_health_or_mount.py`, `docs/Heartbeat/README.md`, `docs/architecture/00-current-state.md`, `scripts/content/generate_local_model_draft.py`, `tests/scripts/test_generate_local_model_draft.py`, `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`

| SHA | Subject | Files |
| --- | --- | --- |
| `d1574f7954c6` | Fix supported profile and draft adapter wiring | `docker-compose.yml`, `docs/audits/daily/evening/2026-05-18-audit.json`, `docs/audits/daily/evening/2026-05-18-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/features/commandCenter/api.ts`, `guardian/workers/coding_worker.py` |
| `019a5f2d2fec` | Fix personal facts settings route | `config/supported_profiles/v1-local-core-web-mcp.yaml`, `guardian/guardian_api.py`, `tests/core/test_supported_profile.py`, `tests/routes/test_retrieve_health_or_mount.py` |
| `f1439c72385e` | Add local model draft adapter | `docs/Heartbeat/README.md`, `docs/architecture/00-current-state.md`, `scripts/content/generate_local_model_draft.py`, `tests/scripts/test_generate_local_model_draft.py` |
| `0ca9fa5e64f1` | Surface runtime visual state in GuardianChatWithSidebar | `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `docs` | 2 | `docs/Heartbeat/README.md`, `docs/architecture/00-current-state.md` |
| `audit` | 6 | `docs/audits/daily/evening/2026-05-18-audit.json`, `docs/audits/daily/evening/2026-05-18-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `providers` | 2 | `config/supported_profiles/v1-local-core-web-mcp.yaml`, `tests/core/test_supported_profile.py` |
| `frontend` | 2 | `frontend/src/features/commandCenter/api.ts`, `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx` |
| `tests` | 2 | `tests/routes/test_retrieve_health_or_mount.py`, `tests/scripts/test_generate_local_model_draft.py` |
| `infra` | 1 | `docker-compose.yml` |
| `unknown` | 3 | `guardian/workers/coding_worker.py`, `guardian/guardian_api.py`, `scripts/content/generate_local_model_draft.py` |

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

