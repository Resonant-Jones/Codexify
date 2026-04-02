# Daily Audit — 2026-04-01

## Repo Status
- Date: 2026-04-01
- Phase: `evening`
- Branch: `main`
- HEAD: `a330261f7f7ea2e9dfe76ac5f49d3d8f7f24a14e`
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
- Commit count: 31
- Unique files changed: 57
- Files changed: `guardian/core/pgdb.py`, `guardian/services/account_export.py`, `tests/routes/test_account_export.py`, `guardian/routes/api_exports.py`, `guardian/tests/core/test_pgdb_account_export.py`, `docs/architecture/2026-04-01-current-head-supported-path-proof.md`, `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/CommandCenterPage.test.tsx`, `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudio.tabs.test.tsx`, `frontend/src/features/personaStudio/components/DiagnosticsPanel.tsx`, `frontend/src/features/personaStudio/components/TruthMatrix.tsx`, `frontend/src/features/personaStudio/personaStudioStore.ts`, `frontend/src/features/chat/__tests__/useChat.test.ts`, `frontend/src/features/chat/useChat.ts`, `docs/architecture/account-export-restore-contract.md`, `backend/rag/chatgpt_migration.py`, `guardian/tests/migration/test_chatgpt_import_flat_structure.py`, `guardian/tests/migration/test_chatgpt_ingest.py`, `docs/audits/investigations/2026-04-01-account-export-status.md`, `docs/architecture/README.md`, `docs/architecture/persona-studio.md`, `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioPage.persistence.test.tsx`, `docker-compose.yml`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `docs/architecture/persona-studio-spec.md`, `docs/audits/daily/morning/2026-04-01-audit.json`, `docs/audits/daily/morning/2026-04-01-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/architecture/2026-04-01-deterministic-retrieval-proof.md`, `guardian/context/broker.py`, `guardian/routes/chat.py`, `tests/core/test_context_broker_source_mode.py`, `tests/routes/test_chat_profile_trace.py`, `backend/rag/personal_fact_extraction.py`, `guardian/tests/migration/test_chatgpt_personal_fact_ingest.py`, `docs/architecture/2026-04-01-supported-path-proof.md`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, `docs/audits/daily/evening/2026-03-31-audit.json`, `docs/audits/daily/evening/2026-03-31-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/main.tsx`, `frontend/src/features/workspace/workspace.css`

| SHA | Subject | Files |
| --- | --- | --- |
| `7f6041f8b4ac` | feat: bundle export blobs in account zip | `guardian/core/pgdb.py`, `guardian/services/account_export.py`, `tests/routes/test_account_export.py` |
| `6abd595d245f` | Stream account exports and snapshot PG reads | `guardian/core/pgdb.py`, `guardian/routes/api_exports.py`, `guardian/services/account_export.py`, `guardian/tests/core/test_pgdb_account_export.py`, `tests/routes/test_account_export.py` |
| `a9cb170165c6` | docs(proof): add current-head supported-path proof after retrieval-boundary changes | `docs/architecture/2026-04-01-current-head-supported-path-proof.md` |
| `48d8411840e1` | refactor(command-center): canonicalize runtime status chips | `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/CommandCenterPage.test.tsx` |
| `0e334f30ecb5` | feat: add canonical account export zip | `guardian/core/pgdb.py`, `guardian/routes/api_exports.py`, `guardian/services/account_export.py`, `tests/routes/test_account_export.py` |
| `99f359d278f7` | refactor(command-center): improve legibility and library convergence | `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/CommandCenterPage.test.tsx` |
| `c5ff19c1105d` | refactor(command-center): emphasize signal over detail | `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/CommandCenterPage.test.tsx` |
| `7759b432cf1b` | refactor(persona-studio): strengthen editor hierarchy | `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx` |
| `45ff9b4d0e50` | persona-studio: promote Truth Matrix to first-class tab and separate from diagnostics | `frontend/src/features/personaStudio/__tests__/PersonaStudio.tabs.test.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx` |
| `83c1068c8270` | Promote Truth Matrix to first-class Persona Studio tab | `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/components/DiagnosticsPanel.tsx`, `frontend/src/features/personaStudio/components/TruthMatrix.tsx`, `frontend/src/features/personaStudio/personaStudioStore.ts` |
| `671aedc2e0e8` | fix(chat): reconcile persisted assistant messages after completion | `frontend/src/features/chat/__tests__/useChat.test.ts`, `frontend/src/features/chat/useChat.ts` |
| `97f7c8028bc3` | docs: add account export restore contract | `docs/architecture/account-export-restore-contract.md` |
| `809c4d76c3e9` | Flatten ChatGPT imports and preserve grouping as metadata | `backend/rag/chatgpt_migration.py`, `guardian/tests/migration/test_chatgpt_import_flat_structure.py`, `guardian/tests/migration/test_chatgpt_ingest.py` |
| `6b8189a5db8c` | Add Persona Studio truth matrix | `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx` |
| `acd5fd37c63f` | docs: add account export status investigation | `docs/audits/investigations/2026-04-01-account-export-status.md` |
| `8c89d4d2c867` | Document Persona Studio architecture and data flow | `docs/architecture/README.md`, `docs/architecture/persona-studio.md` |
| `ce0afeede6c4` | Add persona studio route syncing to AppShell | `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx` |
| `b2799e59c7ad` | Persist Persona Studio local drafts | `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioPage.persistence.test.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx`, `frontend/src/features/personaStudio/personaStudioStore.ts` |
| `64dbe1f0143d` | Integrate Persona Studio into app shell | `docker-compose.yml`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx` |
| `1bfadb556f40` | Wire ChatGPT import into personal fact review inbox | `docs/architecture/persona-studio-spec.md`, `docs/audits/daily/morning/2026-04-01-audit.json`, `docs/audits/daily/morning/2026-04-01-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md` |
| `b53219f7cdd0` | docs(rag): add deterministic retrieval proof matrix | `docs/architecture/2026-04-01-deterministic-retrieval-proof.md`, `guardian/context/broker.py`, `guardian/routes/chat.py`, `tests/core/test_context_broker_source_mode.py`, `tests/routes/test_chat_profile_trace.py` |
| `e34697b6a0fa` | Wire ChatGPT import into personal fact review inbox | `backend/rag/chatgpt_migration.py`, `backend/rag/personal_fact_extraction.py`, `guardian/tests/migration/test_chatgpt_personal_fact_ingest.py` |
| `66020c9b63d9` | docs(proof): add fresh supported-path proof after embed lifecycle fix | `docs/architecture/2026-04-01-supported-path-proof.md` |
| `07571f2823a5` | feat(workspace): add per-thread posture preset control | `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts` |
| `59589eee32b2` | fix(workspace): normalize markdown image sources | `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx` |
| `4eea960f76b9` | fix(workspace): detect signed image preview urls | `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx` |
| `a593c0adb77c` | fix(workspace): restore unsupported preview link | `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx` |
| `487131abc9a8` | fix(workspace): avoid auth headers on external preview urls | `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx` |
| `45ffc5c08da5` | feat(workspace): render markdown previews in inspector | `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx` |
| `969355bf438b` | Refresh daily evening audit snapshot | `docs/audits/daily/evening/2026-03-31-audit.json`, `docs/audits/daily/evening/2026-03-31-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/main.tsx` |
| `ecedc62f47dc` | feat(workspace): render actual document previews in inspector | `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx`, `frontend/src/features/workspace/workspace.css` |

## Subsystems Touched
| Bucket | Count | Files |
| --- | --- | --- |
| `chat` | 1 | `guardian/routes/chat.py` |
| `docs` | 7 | `docs/architecture/2026-04-01-current-head-supported-path-proof.md`, `docs/architecture/account-export-restore-contract.md`, `docs/architecture/README.md`, `docs/architecture/persona-studio.md`, `docs/architecture/persona-studio-spec.md`, `docs/architecture/2026-04-01-deterministic-retrieval-proof.md`, `docs/architecture/2026-04-01-supported-path-proof.md` |
| `audit` | 11 | `docs/audits/investigations/2026-04-01-account-export-status.md`, `docs/audits/daily/morning/2026-04-01-audit.json`, `docs/audits/daily/morning/2026-04-01-audit.md`, `docs/audits/daily/morning/latest.json`, `docs/audits/daily/morning/latest.md`, `docs/audits/latest.json`, `docs/audits/latest.md`, `docs/audits/daily/evening/2026-03-31-audit.json`, `docs/audits/daily/evening/2026-03-31-audit.md`, `docs/audits/daily/evening/latest.json`, `docs/audits/daily/evening/latest.md` |
| `ingestion` | 2 | `guardian/tests/migration/test_chatgpt_ingest.py`, `guardian/tests/migration/test_chatgpt_personal_fact_ingest.py` |
| `frontend` | 24 | `frontend/src/contracts/runtimeTokens.ts`, `frontend/src/features/commandCenter/CommandCenterPage.tsx`, `frontend/src/features/commandCenter/__tests__/CommandCenterPage.test.tsx`, `frontend/src/features/personaStudio/PersonaStudioPage.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioShell.test.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudio.tabs.test.tsx`, `frontend/src/features/personaStudio/components/DiagnosticsPanel.tsx`, `frontend/src/features/personaStudio/components/TruthMatrix.tsx`, `frontend/src/features/personaStudio/personaStudioStore.ts`, `frontend/src/features/chat/__tests__/useChat.test.ts`, `frontend/src/features/chat/useChat.ts`, `frontend/src/App.tsx`, `frontend/src/components/persona/layout/AppShell.tsx`, `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`, `frontend/src/features/personaStudio/__tests__/PersonaStudioPage.persistence.test.tsx`, `frontend/src/features/workspace/WorkspaceViewer.tsx`, `frontend/src/features/workspace/__tests__/WorkspaceDrawer.test.tsx`, `frontend/src/features/workspace/components/WorkspaceDrawer.tsx`, `frontend/src/features/workspace/state/useWorkspaceLayoutMode.ts`, `frontend/src/features/workspace/__tests__/WorkspacePane.preview.test.tsx`, `frontend/src/features/workspace/WorkspacePane.tsx`, `frontend/src/features/workspace/components/WorkspaceTabs.tsx`, `frontend/src/main.tsx`, `frontend/src/features/workspace/workspace.css` |
| `tests` | 5 | `tests/routes/test_account_export.py`, `guardian/tests/core/test_pgdb_account_export.py`, `guardian/tests/migration/test_chatgpt_import_flat_structure.py`, `tests/core/test_context_broker_source_mode.py`, `tests/routes/test_chat_profile_trace.py` |
| `infra` | 1 | `docker-compose.yml` |
| `unknown` | 6 | `guardian/core/pgdb.py`, `guardian/services/account_export.py`, `guardian/routes/api_exports.py`, `backend/rag/chatgpt_migration.py`, `guardian/context/broker.py`, `backend/rag/personal_fact_extraction.py` |

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

