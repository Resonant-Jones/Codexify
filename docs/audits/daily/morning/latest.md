# Daily Audit — 2026-05-30

## Repo Status
- Date: 2026-05-30
- Phase: `morning`
- Branch: `codex/add-whooshd-provider`
- HEAD: `65eedff3917c00429d2039d181d1e5ead8f84561`
- Worktree: dirty
- Status lines:
  - ` M docs/Marketing/generated/history/run-history.jsonl`
  - ` M docs/audits/daily/evening/latest.json`
  - ` M docs/audits/daily/evening/latest.md`
  - ` M docs/audits/latest.json`
  - ` M docs/audits/latest.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/ad-copy.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/channel-community.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/channel-social.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/channel-website.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/core-brief.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/evidence-ledger.json`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/infographic-spec.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/review-notes.md`
  - `?? docs/Marketing/generated/CAMPAIGN_2026_05_30_MARKETING_V1/run-metadata.json`
  - `?? docs/audits/daily/evening/2026-05-29-audit.json`
  - `?? docs/audits/daily/evening/2026-05-29-audit.md`

## Audit CLI Summary
- Selected mode: `text_fallback`
- Attempted commands:
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify/scripts/audit_platform_readiness.py --json` -> exit 1 (json probe)
  - `/opt/homebrew/opt/python@3.13/bin/python3.13 /Users/resonant_jones/Keep/Resonant_Constructs/projectCodexify/Codexify/scripts/audit_platform_readiness.py` -> exit 0 (plain)
- Summary counts: PASS 43, WARN 11, FAIL 0
- Strongest evidence: `Extension Boundary`, `Core Loop Integrity`, `Primitive Stability`
- Weakest signals: `Federation Readiness`, `Alternate Surface Readiness`, `Governance Readiness`

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
- Unique files changed: 22
- Files changed: `docs/architecture/00-current-state.md`, `docs/architecture/README.md`, `backend/Dockerfile`, `backend/Dockerfile.prod`, `tests/ops/test_compiled_runtime_contract.py`, `docs/whooshd-local-provider.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/ad-copy.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-community.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-social.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-website.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/core-brief.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/evidence-ledger.json`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/infographic-spec.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/review-notes.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/run-metadata.json`, `docs/Marketing/generated/history/run-history.jsonl`, `docs/audits/daily/morning/2026-05-29-audit.json`, `docs/audits/daily/morning/2026-05-29-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`

| SHA | Subject | Files |
| --- | --- | --- |
| `65eedff3917c` | docs: refresh weekly current-state override | `docs/architecture/00-current-state.md`, `docs/architecture/README.md` |
| `388b6d64d2aa` | Pin backend images to bookworm bases | `backend/Dockerfile`, `backend/Dockerfile.prod`, `tests/ops/test_compiled_runtime_contract.py` |
| `ae6c1be98411` | Document Whooshd local provider integration | `docs/whooshd-local-provider.md` |
| `ae87deb5b134` | Pin backend images to docker.io python bases | `backend/Dockerfile`, `backend/Dockerfile.prod` |
| `d6a92310dbae` | Refresh audit and marketing generated records | `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/ad-copy.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-community.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-social.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-website.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/core-brief.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/evidence-ledger.json`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/infographic-spec.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/review-notes.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/run-metadata.json`, `docs/Marketing/generated/history/run-history.jsonl`, `docs/audits/daily/morning/2026-05-29-audit.json`, `docs/audits/daily/morning/2026-05-29-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `docs` | 12 | `docs/architecture/00-current-state.md`, `docs/architecture/README.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/ad-copy.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-community.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-social.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/channel-website.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/core-brief.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/evidence-ledger.json`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/infographic-spec.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/review-notes.md`, `docs/Marketing/generated/CAMPAIGN_2026_05_29_MARKETING_V1/run-metadata.json`, `docs/Marketing/generated/history/run-history.jsonl` |
| `audit` | 6 | `docs/audits/daily/morning/2026-05-29-audit.json`, `docs/audits/daily/morning/2026-05-29-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `providers` | 1 | `docs/whooshd-local-provider.md` |
| `tests` | 1 | `tests/ops/test_compiled_runtime_contract.py` |
| `unknown` | 2 | `backend/Dockerfile`, `backend/Dockerfile.prod` |

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

