# Workspace Baseline Capability Ledger

**Campaign:** Workspace Baseline Convergence (`WBC-0` truth freeze)
**Repository reconciled:** `eb6bdc530245fdffeff23589c98389be4102b564` (`origin/main`)
**Current-state authority read:** `docs/architecture/00-current-state.md` (2026-08-13)
**G0 result:** `CAMPAIGN_SWEEP_FROZEN`
**ADR impact:** No ADR impact. This ledger records present seams and does not
accept, change, or supersede an architecture decision.

## How to read this ledger

`00-current-state.md` remains the short-horizon release authority. The
evidence label below says what the cited code, test, contract, or receipt
actually establishes; it does not promote a capability to Beta support.

The evidence labels are deliberately independent from the posture labels:

- `partial` means a necessary semantic or ownership boundary is materially
  missing.
- `unproven` means the implementation seam exists, but the required proof
  level (usually current-tip supported-path proof) is missing.
- Historical receipts and focused tests are not silently treated as current-tip
  live proof.

No unresolved conflict between accepted ADRs, current architecture contracts,
and the current-state release boundary was found. Historical or supplementary
documents that imply more than the current-state file are recorded below as
evidence limits, not normalized into a release claim.

## Reconciliation findings before the row ledger

### Existing execution records and their proper scope

| Needed semantic | Existing record(s) | Current ownership and limit |
| --- | --- | --- |
| Authored turn | `chat_threads`, `chat_messages` | Canonical conversation and authored/assistant transcript authority. An authored message is not a provider attempt. |
| Chat request / attempt | `ChatCompletionTask`, Redis task-event stream and turn lock; `EvalTraceSnapshot` after a successful turn | The queue/task identity and terminal visibility are operational; trace snapshots are inspection-only and post-completion. There is no durable generic attempt record enclosing every chat input. |
| Bounded tool call | `command_runs`, ordered `command_run_events` | Canonical durable authority for a Command Bus invocation, including actor/auth subject, idempotency key, redacted args, result/error, and ordered events. |
| Delegated/coding run and step | `guardian_delegation_intents`, `agent_runs`, `agent_run_steps`, `agent_run_attempts`, `agent_run_artifacts` | Durable coding/delegation lifecycle records with thread/source-message lineage. Current-tip live adapter and return proof remain open. |
| Campaign work and attempt | `campaign_goals`, `campaigns`, `coding_work_orders`, `campaign_execution_attempts`, `work_order_result_receipts` | Canonical Campaign Engine / coding-work-order evidence family; it is not a replacement transcript or a generic chat ledger. |
| Process/job-like lifecycle | `agent_runs` / `agent_run_attempts`, `cron_runs`, `connector_runs`, `sync_jobs`, account-import jobs | Durable lifecycle metadata exists in several domains. None is a persistent terminal/session with reattachable stdout/stderr/PTY ownership. |
| Published result | assistant `chat_messages` (`kind=coding_result` for coding), `GuardianDelegationIntent` delivery fields, `CampaignExecutionAttempt` delivery fields | Guardian-owned coding-result reinjection is implemented and focused-test proven; it is not current-tip supported Coding Loop proof. |

**Answer to the ledger question:** Codexify does **not** have one canonical
execution ledger under another name. It has accepted, durable, domain-owned
records. Convergence must first use shared correlation and projections over
those records, extending the smallest owner only when the proven golden path
shows a missing invariant. A new universal event table is not justified by G0.

### Current model-visible context provenance result

The ordinary chat path durably retains authored messages and can retain an
`EvalTraceSnapshot` with task/request/thread IDs, provider/model,
retrieval/payload summaries, and trace metadata after successful completion.
`chat_completion_service` also builds trace metadata for retrieval plans,
profile/prompt assembly, browser context, and tool exposure. This is useful
inspection evidence, but it does not atomically freeze every byte or canonical
reference visible to the model before provider dispatch. Persona/system-prompt
assembly, profile and memory layers, retrieval contents, provider-specific
transformation, compaction, and tool/provider payload transformations can
change or are only summarized after the fact.

Therefore the invariant **"model-visible means logged" is partially
observable**, not enforceable and not fully reconstructable for a specific
attempt. The first future provenance slice must first prove whether an
attempt-scoped manifest can extend the existing accepted records; G0 does not
authorize a new primitive.

### Current capability and authority snapshot result

Existing pieces are real but not one frozen attempt authority object:

- the Command Bus manifest, advertised-subset gate, permission profiles, and
  durable `CommandRun` actor/auth-subject/idempotency/args-hash evidence;
- `GuardianDelegationIntent` approval state/source, source lineage, and
  bounded `context_basis`;
- immutable deployment `spec_hash`, executor registry capability declarations,
  and in-flight `CodexifyExecutorRequest.permissions`;
- account/project `RepositoryBinding` authority checks and supported-profile /
  egress configuration.

There is no durable, immutable snapshot that joins effective capability set,
approval, filesystem scope, egress policy, executor/provider selection, and
limits for every run. Settings and provider credentials remain substantially
environment-driven. Unknown scope or lineage continues to fail closed in the
implemented bounded paths.

### Persistent terminal/process result

There is no `TerminalSession`, `ExecutionSession`, PTY, process handle, or
reattachable terminal-output authority today. `AgentRun.runtime_target` may be
`terminal` and agent/coding executors invoke bounded subprocesses, while
`AgentRunArtifact` can retain an artifact URI or JSON result. Those are
lifecycle/result metadata, not a durable process abstraction. This gap must
be addressed only after runtime closure, execution enclosure, and frozen
authority are proven.

## Capability ledger

### A. Supported runtime closure

| Capability (family; baseline class) | Current Codexify posture | Evidence posture | Current owning subsystem and primary code anchors | Governing docs/contracts and ADR(s) | Existing durable authority / operational state | Disposition / Campaign decision | Prerequisites / required proof | Notes / truth conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Supported Compose completion path (runtime closure; Expected) | unproven | documented contract | Compose + Guardian startup: `docker-compose.yml`, `guardian/guardian_api.py`, `guardian/routes/health.py` | `00-current-state.md`; `config-and-ops.md`; ADR-001, ADR-069 | Postgres owns durable chat state; Redis owns queue/coordination | reuse / admit | Fresh supported-profile proof at `eb6bdc5`: health, inventory, one terminal completion, persisted assistant, independent readback | Local Compose is the supported install path, but current state explicitly keeps fresh current-tip proof open. |
| Provider/model execution (runtime closure; Expected) | unproven | test-proven | `guardian/core/provider_registry.py`, `ai_router.py`, `llm_catalog.py`, provider adapters | `provider-capability-contract.md`; `config-and-ops.md`; ADR-069; ADR-062 is Proposed, not an accepted account contract | Provider catalog/runtime DB rows; environment credentials and policy resolve execution | reuse / admit | Current supported local Whoosh'd inventory + terminal completion proof; preserve local-only policy | Adapter and qualification tests do not prove provider execution on the supported profile. |
| Redis enqueue/dequeue, heartbeat, turn lock, and terminal task evidence (runtime closure; Expected) | unproven | test-proven | `chat_completion_service.py::enqueue_chat_completion`, `queue/redis_queue.py`, `queue/turn_lock.py`, `queue/task_events.py`, `workers/chat_worker.py` | `completion_pipeline.md`; `chat-runtime-contract.md`; ADR-001, ADR-003, ADR-038 | Redis queue, event streams, heartbeat keys, cancellation set, and locks are operational only; assistant row is durable | reuse / admit | One current-tip queue-to-worker-to-terminal observation with lock acquisition/release and persisted readback | Existing separation of acceptance, execution, terminal event, and UI receipt is correct and must remain. |
| Assistant persistence and independent source-thread readback (runtime closure; Expected) | unproven | test-proven | `workers/chat_worker.py`, `core/chat_db.py`, `routes/chat.py` | `completion_pipeline.md`; `chat-runtime-contract.md`; ADR-001, ADR-003, ADR-069 | `chat_messages` is transcript authority; turn-completion anchor cache is ephemeral | reuse / admit | Current-tip proof that a terminal event and persisted assistant message are independently readable | Route acceptance and a health check do not close this proof. |
| Canonical/legacy configuration coherence (runtime closure; Expected) | partial | code-path only | `guardian/core/config.py`, `guardian/config/settings.py`, `guardian/core/dependencies.py` | `config-and-ops.md`; `00-current-state.md`; ADR-069 | Environment/config objects are authoritative; frontend preferences are not routing authority | extend / admit | Reconcile or explicitly fence canonical versus legacy config values, then prove startup observes the chosen truth | Current-state names this as an active drift risk; this is not a request to create a parallel Settings store. |
| Coding Loop supported posture (runtime closure; Expected) | unproven | test-proven | `guardian/routes/codex.py`, `guardian/agents/store.py`, `guardian/core/executors/`, `guardian/pi/invocation.py` | `delegation-runtime.md`; `pi-invocation-boundary-contract.md`; ADR-020, ADR-048, ADR-066, ADR-068, ADR-069 | Agent/campaign rows and source-thread result fields exist; executor/process state is not proven live | reuse / admit | Backend acceptance, adapter execution, terminal durable result, and source-thread readback on the claimed profile | Current state records a prior proof stop at backend exit code 3; route and tests are not support proof. |

### B. Execution history, provenance, authority, and persistent execution

| Capability (family; baseline class) | Current Codexify posture | Evidence posture | Current owning subsystem and primary code anchors | Governing docs/contracts and ADR(s) | Existing durable authority / operational state | Disposition / Campaign decision | Prerequisites / required proof | Notes / truth conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Canonical execution event spine (execution history; Expected) | partial | code-path only | `guardian/command_bus/store.py`; `guardian/agents/store.py`; `campaign_runner_store.py`; DB models for CommandRun, AgentRun, CampaignExecutionAttempt | `execution-ledger-gate-artifacts-contract.md`; `campaign-engine-contract.md`; ADR-028, ADR-066, ADR-068 | Durable domain records listed above; Redis task events are ephemeral transport visibility | extend / admit | G1 proof plus an architecture slice establishing a shared correlation/projection across needed records | No single ledger exists, but no new event table is justified before existing record seams are proven insufficient. |
| Explicit turn/request/step/tool lifecycle (execution history; Expected) | partial | test-proven | `ChatCompletionTask`; `EvalTraceSnapshot`; `CommandRun`/events; `AgentRunStep`/attempts; `CampaignExecutionAttempt` | `chat-runtime-contract.md`; `agent-tool-loop-contract.md`; ADR-001, ADR-003, ADR-028 | Each domain owns parts of the lifecycle; authored message identity stays distinct from request identity | extend / admit | G1 followed by a mapping/contract for cross-domain attempt correlation | Do not collapse a message, queue task, command run, and coding attempt into one ID. |
| Model-visible context provenance (provenance; Expected) | partial | code-path only | `chat_completion_service.py`, `workers/chat_worker.py`, `EvalTraceSnapshot`, `cognition/system_prompt_builder.py` | `chat-runtime-contract.md`; `completion_pipeline.md`; retrieval contracts; ADR-003, ADR-012, ADR-059, ADR-060 | Authored messages and some trace summaries are durable; assembled prompt/provider payload is not an immutable attempt manifest | extend / admit | G1; then prove a bounded pre-dispatch context manifest/correlation using existing authority where possible | Classification: partially observable, not enforceable/reconstructable end to end. No raw secret-bearing provider payload capture is implied. |
| Typed capability contracts and effective resolution (authority; Expected) | existing | test-proven | `guardian/command_bus/manifest.py`, `invoke.py`, `permission_profiles.py`, `core/provider_registry.py`, plugin capability/binding code | `agent-tool-loop-contract.md`; `self-extending-agent-plugin-system.md`; ADR-061, ADR-065, ADR-069 | Command manifest and policy govern actual bounded commands; registry/config resolves providers | reuse / already-satisfied | Preserve advertised-subset and fail-closed tests; use as input to a future frozen snapshot | Existing bounded resolution is not a generic approval or sandbox authority. |
| Frozen run capability/permission snapshot (authority; Expected) | partial | code-path only | `CommandRun`; `GuardianDelegationIntent`; `AgentDeployment.spec_hash`; `CodexifyExecutorRequest.permissions`; repository bindings | `agent-tool-loop-contract.md`; `pi-invocation-boundary-contract.md`; ADR-061, ADR-065, ADR-068 | Durable auth/approval and lineage fragments; permission object is currently in-flight and configuration is environment-driven | extend / admit | G1 and execution-correlation decision; prove immutability, scope, provider/executor identity, and negative/fail-closed cases | No unified durable snapshot covers all requested authority dimensions. |
| Guarded command/tool execution (authority; Expected) | existing | test-proven | `guardian/command_bus/`, `core/chat_completion_service.py::_prepare_chat_tool_exposure`, `codex_runner_bridge/command_bus.py` | `agent-tool-loop-contract.md`; `provider-tool-turn-boundary-contract.md`; ADR-061, ADR-065, ADR-069 | `command_runs` / ordered events with idempotency and policy are durable; capability exposure is bounded | reuse / already-satisfied | Maintain one-command boundary and prove it as part of future golden-path work | Generic tools, shell, and public Command Bus remain internal/quarantined. |
| Durable approvals and permission presets (authority; Expected) | partial | test-proven | `GuardianDelegationIntent` approval fields; `routes/guardian_delegations.py`; `command_bus/permission_profiles.py` | `delegation-runtime.md`; ADR-020, ADR-048, ADR-061 | Delegation approval is durable and idempotent; permission profiles are bounded command policy, not universal approval records | extend / admit | Frozen attempt authority design after G1 | Existing manual/scoped delegation approval must not be generalized by assumption. |
| Persistent terminal/process session (persistent execution; Expected) | gap | code-path only | `AgentRun.runtime_target`, `AgentRunArtifact`, `core/executors/codex_executor.py`, `pi/invocation.py` | `delegation-runtime.md`; `pi-invocation-boundary-contract.md`; ADR-020, ADR-048 | Result/lifecycle rows exist; subprocess/Pi calls are transient and no session/PTY/reattach record exists | extend / admit | G1, execution enclosure, and frozen authority; then one bounded process design and live recovery proof | This is a genuine golden-path prerequisite, but not the first implementation slice. |
| Durable large-output/spill references (persistent execution; Expected) | gap | code-path only | `AgentRunArtifact.uri`, media/storage services, coding-result serializer | `data-and-storage.md`; `delegation-runtime.md`; ADR-066 | Artifacts can point to URIs; no general terminal-output spill lifecycle/retention contract is exercised | extend / conditional | Only admit if the bounded golden path exceeds safe durable result limits; prove bounded retrieval and cleanup | Do not store unbounded output in message metadata or later prompts. |
| Idempotent source-thread result return (result integrity; Expected) | partial | test-proven | `guardian/agents/store.py::persist_coding_result_and_inject_source_thread`, `GuardianDelegationIntent`, `CampaignExecutionAttempt` | `delegation-runtime.md`; `pi-invocation-boundary-contract.md`; ADR-020, ADR-048, ADR-066 | Assistant `coding_result` message, delivery key/status/error, and campaign delivery fields are durable | reuse / admit | Current-tip Coding Loop live proof plus retry/restart/operator-visible failure proof | Guardian delegation delivery has durable duplicate suppression in focused tests; not every executor path is live-qualified. |
| Restart recovery and replay invariants (resilience; Expected) | partial | test-proven | account-import recovery; turn-lock recovery; command-run idempotency; delegation delivery store | `data-and-storage.md`; `completion_pipeline.md`; ADR-001, ADR-066 | Domain-specific durable checkpoints; Redis dequeue and task events are not durable generic history | extend / admit | G4 bounded run; fault injection before/after enqueue, execution, persistence, and return | Existing recovery mechanisms are not a universal replay contract. |
| Bounded subagent/delegation seam (delegation; Expected) | partial | test-proven | `guardian_delegation_service.py`, `delegation_worker.py`, `core/executors/`, `pi/invocation.py`, `AgentRun*` | `delegation-runtime.md`; `pi-invocation-boundary-contract.md`; ADR-020, ADR-048, ADR-066, ADR-068 | Intent/run/step/attempt/artifact lineage exists; external executor output is normalized through Guardian | extend / admit | G4 golden path, immutable authority snapshot, live executor result, and source-thread return proof | Start/run/result identities and lineage have canonical equivalents for bounded coding; frozen authority and supported live proof do not. |
| Context compaction with provenance (maturity; Expected workspace capability) | partial | documented contract | chat summaries/trace fields and context assembly seams | `chat-runtime-contract.md`; `chat-runtime-state-contract.md` | Transcript remains durable; no attempt-proven provenance-preserving compaction closure identified | no-action / conditional | Only after execution/provenance proof shows a real context-window need | Must never rewrite authoritative transcript. |
| Session queries and derived projections (maturity; Mature UX) | partial | code-path only | `AgentRun*` read models, task events, Command Bus readback, frontend run hooks | `modules-and-ownership.md`; `flows.md`; ADR-028, ADR-066 | Multiple domain read models already exist | extend / conditional | Require a proven common correlation query need | Do not create a projection platform from the Campaign alone. |
| Trusted skill catalog and progressive loading (extension; Mature UX) | partial | documented contract | plugin proposal/registry/binding and capability resolution seams | `self-extending-agent-plugin-system.md`; ADR-061 | Proposal/binding registry concepts are durable where implemented; activation/sandbox is not | no-action / conditional | Only after golden-path authority proof | Advanced partial control plane; no dynamic activation is admitted. |

### C. Provider, integration, Connector Bay, Settings, and onboarding

| Capability (family; baseline class) | Current Codexify posture | Evidence posture | Current owning subsystem and primary code anchors | Governing docs/contracts and ADR(s) | Existing durable authority / operational state | Disposition / Campaign decision | Prerequisites / required proof | Notes / truth conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Provider connection instances (provider control plane; Expected) | gap | code-path only | `InferenceProvider`, `InferenceProviderRuntime`, `OAuthConnection`, `provider_registry.py`, `core/config.py` | `config-and-ops.md`; `provider-capability-contract.md`; ADR-069; ADR-062 is Proposed | Provider definition/runtime is keyed by `provider_id`; OAuth is keyed uniquely by `(user_id, provider, mode)`; API keys are environment-driven | extend / admit | G1/G3 authority work; explicit connection-instance schema/selection contract only after a separate approved task | Multiple same-provider/same-mode accounts cannot coexist. OAuth and API-key selection are not one clean per-account runtime path. |
| General integration registry (integration control plane; Expected) | partial | test-proven | `guardian/connections/catalog.py`, `routes/connections.py`, `protocol_tokens.py` | `connections-control-plane.md`; ADR-071; ADR-024 applies to connector/tool semantics | Static general catalog combines messaging, web, and inference metadata; mutation remains in channels/connectors/provider subsystems | extend / admit | G4; normalize definition versus instance/credential/health ownership without moving execution authority | The read-only catalog is a real general aggregation seam, not a general integration-instance registry. |
| Connector Bay inventory and health (integration UI; Expected) | partial | test-proven | `frontend/src/features/connectors/connectionCatalog.ts`, `SettingsView.tsx::ConnectionsBay`, `routes/connections.py` | `connections-control-plane.md`; ADR-071 | Static catalog + safe OAuth/channel/provider projection; legacy `connector_configs`/runs track sync configuration | extend / admit | G4 then representative instance/health proof | **Empty state trace:** current tip has no literal `No connectors available` string. Canonical bay shows `No connections match` only when filtered catalog is empty; a disabled/unmounted `CODEXIFY_ENABLE_CONNECTOR_ROUTES` route returns 404 and `useConnections` deliberately projects it as empty. The legacy sync panel says `No sync connectors configured` when `GET /api/connectors` returns no persisted `connector_configs`. The normal backend catalog is static and nonempty. |
| Guided first-run onboarding over canonical state (onboarding; Mature UX) | partial | code-path only | desktop `runtimeBootstrap.ts`; `guardian/ops/setup_wizard.py`; `imprint_zero_onboarding.py`; Settings components | `config-and-ops.md`; `00-current-state.md`; ADR-069 | Desktop bootstrap and Imprint onboarding exist; supported provider/configuration truth remains backend/environment-owned across surfaces | extend / admit | G6 canonical provider/integration instance APIs and minimum-path health evidence | No unified product onboarding owns only canonical configuration today. |
| Settings projection of canonical state (operator UX; Mature UX) | partial | test-proven | Settings views, provider picker/state, Connections Bay, `iddb_settings_service.py` | `config-and-ops.md`; `connections-control-plane.md`; ADR-071 | Some settings are persisted/user-scoped; provider credentials and several runtime flags remain environment-only | extend / admit | G6 inventory of canonical write paths and unsupported environment-only fields | UI preferences and local storage are not runtime authority. |
| Attachments and uploads (workspace core; Expected) | existing | documented contract | media routes/storage, document embedding worker, `uploaded_documents`, `media_assets` | `data-and-storage.md`; `flows.md`; ADR-069 | Postgres metadata + file/object bytes; Redis embed queue | reuse / already-satisfied | Preserve supported upload-to-readback proof boundary; no expansion | Current state includes implemented supported formats; this Campaign does not broaden them. |
| Governed web access (web integration; Mature UX) | partial | documented contract | web/provider adapter contracts and existing remote-recall/research seams | `web-search-provider-adapter-contract.md`; `config-and-ops.md` | Separate provider/config policy seams; no admitted general web registry/runtime proof | no-action / park | Reconsider only if an admitted capability cannot be proven without it | Not a persistent-execution prerequisite. |

### D. Advanced, differentiator, and explicit parking decisions

| Capability (family; baseline class) | Current Codexify posture | Evidence posture | Current owning subsystem and primary code anchors | Governing docs/contracts and ADR(s) | Existing durable authority / operational state | Disposition / Campaign decision | Prerequisites / required proof | Notes / truth conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dynamic self-extension (extension; Advanced) | partial | documented contract | plugin proposal/registry/binding seams | `self-extending-agent-plugin-system.md`; ADR-061 | Bounded registry/proposal concepts; no general sandbox or autonomous activation | no-action / park | Separate architecture and runtime-proof intake | Not a baseline prerequisite. |
| General workflow/autonomy engine (automation; Advanced) | partial | documented contract | `guardian/flows/`, Campaign Engine contracts, cron records | `campaign-engine-contract.md`; ADR-050, ADR-066, ADR-068 | Flow and campaign artifacts exist; they do not prove autonomous dispatch/execution | no-action / park | Separate scoped authorization, idempotency, and proof task | Campaign Engine does not authorize auto-merge, auto-push, or unattended agent execution. |
| LSP/navigation provider (developer tooling; Advanced) | gap | working theory | No canonical runtime owner found in current accepted runtime path | Architecture KB and current-state boundary | None identified as durable baseline authority | no-action / park | Separate intake must identify a bounded owner and authority model | Absence is a G0 reconciliation finding, not implementation authorization. |
| Identity, provenance, and portability doctrine (cross-cutting; Differentiator) | existing | documented contract | users/projects/threads, conversation origin, source lineage, export/restore and identity contracts | `data-and-storage.md`; identity contracts; ADR-046, ADR-061, ADR-069 | Postgres user/thread/source-lineage records are authoritative in their domains | reuse / already-satisfied | Preserve invariants in every admitted slice | Existing doctrine/substrate does not prove every model-visible input is attributable. |

## Required answers

1. **Canonical execution ledger?** No single one. `command_runs`/events are canonical for Command Bus invocations; `AgentRun*`, `CampaignExecutionAttempt`, and work-order receipts are canonical in coding/Campaign Engine domains; chat owns transcript and operational task evidence separately. G0 selects shared correlation and smallest-owner extension before any new durable primitive.
2. **Existing Turn, Step, ToolCall, Job, Result records?** Turn = `chat_threads`/`chat_messages`; request/attempt = `ChatCompletionTask` plus optional `EvalTraceSnapshot`; Step = `AgentRunStep`/`AgentRunAttempt`; ToolCall = `CommandRun`/`CommandRunEvent`; Job = delegation, agent, cron, sync, connector, account-import, and campaign attempt records; Result = assistant message, `AgentRunArtifact`, `WorkOrderResultReceipt`, and delivery fields. Their meanings remain domain-scoped.
3. **Model-visible means logged?** Partially observable. Authored messages and selected summaries/traces persist, but there is no atomic, immutable, complete pre-dispatch input manifest for every prompt, retrieval source, profile/persona layer, memory, system prompt, provider transformation, or compaction result.
4. **Existing capability/permission snapshots?** Command manifest/policy and durable command actor/auth metadata; delegation approval/lineage/context basis; deployment spec hash; executor declarations; repository authority checks; profile/egress configuration. Missing is one immutable, durable, attempt-level effective authority snapshot.
5. **Persistent terminal/process abstraction?** None. `AgentRun.runtime_target`, artifacts, bounded subprocess invocation, and Pi receipts record lifecycle/result evidence but do not create a persistent process, terminal, PTY, reattach, or output-stream authority.
6. **Result-return paths?** Ordinary chat persists an assistant message after accepted terminal evidence but needs current-tip supported-path proof. Guardian coding/delegation return to the source thread is implemented, durable, duplicate-suppressed, and focused-test proven; a failed/stale return is recorded as degraded/suppressed. Its claimed Coding Loop/executor profile is not live-qualified. Hosted Room Guardian invocation reuses ordinary chat persistence and likewise lacks release qualification. Generic delegation summary publication exists, but a universal source-thread return guarantee is not established.
7. **Multiple provider accounts per family/auth mode?** No. `OAuthConnection` is unique on `(user_id, provider, mode)`, inference provider/runtime rows are keyed by one `provider_id`, and API keys are environment configuration. API-key and OAuth configuration can coexist as separate seams, but not as clean independently selectable connection instances; two same-provider/same-mode accounts cannot coexist.
8. **Connector architecture classification?** A combination: static general Connections catalog/projection; messaging-specific channels/adapters; ingestion/sync-specific `connector_configs`/runs; and legacy/provider/OAuth paths that are only partly normalized. The catalog aggregates; it does not own execution or instances.
9. **Connector Bay empty state?** Current tip has `No connections match`, not the literal historical string. It is driven by an empty filtered `GET /api/connections` projection. The hook intentionally uses an empty catalog after a 404 (for example, connector routes disabled) or invalid payload; normally `guardian.connections.catalog` is nonempty. The separate legacy sync list says `No sync connectors configured` only when no persisted connector config exists.
10. **Already satisfied provisional capabilities?** Bounded Command Bus command authority, attachment/upload substrate within its existing support boundary, identity/provenance doctrine/substrate, and the basic typed capability resolution seam leave the active queue. They remain invariants and proof inputs, not new implementation work.
11. **Genuine golden-path prerequisites?** First prove current-tip supported Compose closure and configuration coherence; then correlate existing attempt records and capture model-visible provenance; freeze effective authority; establish one persistent process/output/cancellation/recovery enclosure; and prove idempotent source-thread return. Provider account instances and general integration instances follow the execution baseline rather than precede it.
12. **Frozen order and next candidate?** The dependency order below is final for G0. The singular next Task Spec candidate is `WBC-1A — Capture current-tip supported-Compose runtime closure evidence`.

## Frozen dependency order

1. **WBC-1A — current-tip supported runtime closure**
   *Prerequisite:* G0 frozen. *Closes:* Compose, provider/model, Redis worker,
   turn lock, terminal persistence/readback, and config-drift evidence. *Proof
   gate:* G1. *Work type:* proof (plus an explicitly scoped configuration
   correction only if the proof identifies one).
2. **Execution enclosure and attempt provenance**
   *Prerequisite:* G1. *Closes:* cross-record correlation and the smallest
   justified attempt/context manifest. *Proof gate:* durable reconstruction of
   one completed/failed attempt without Redis memory. *Work type:* architecture
   then implementation/proof.
3. **Frozen capability and authority snapshot**
   *Prerequisite:* execution enclosure. *Closes:* immutable effective
   capabilities, approvals, scopes, provider/executor identity, and limits.
   *Proof gate:* G3. *Work type:* architecture then implementation/proof.
4. **One persistent guarded execution golden path**
   *Prerequisite:* G3. *Closes:* bounded process ownership, output/cancellation,
   terminal result, and source-thread return. *Proof gate:* G4. *Work type:*
   implementation and live proof.
5. **Recovery, replay, and bounded delegation**
   *Prerequisite:* G4. *Closes:* duplicate/restart/fault semantics and
   authority-preserving subagent result return. *Proof gate:* G5. *Work type:*
   implementation/proof.
6. **Provider connection instances and Integration Registry**
   *Prerequisite:* G4 (delegation work may continue independently after G4).
   *Closes:* account identity, canonical definitions/instances, settings, health,
   and representative integration proof. *Proof gate:* G6. *Work type:*
   architecture then implementation/proof.
7. **Guided onboarding and revalidation**
   *Prerequisite:* G6. *Closes:* first-run configuration through canonical APIs
   and final baseline reclassification. *Proof gate:* G7. *Work type:*
   implementation/proof.

## Singular next Task Spec candidate

**`WBC-1A — Capture current-tip supported-Compose runtime closure evidence`**

This is deliberately a proof-first task, not an execution-ledger or terminal
implementation task. It must exercise the supported local profile at
`eb6bdc5`, distinguish health/acceptance/dequeue/terminal/persistence/readback,
record the canonical-versus-legacy configuration values actually consumed, and
stop at a bounded failure. It may not promote Coding Loop, provider preview,
or any release class merely because a route or focused test passes.

## G0 invariant check

- PostgreSQL remains the durable authority for the records it already owns;
  Redis remains queue/coordination/visibility transport.
- Guardian retains authorization, lineage validation, and publication in every
  identified return path; Command Bus remains the bounded command authority.
- Authored message, request/task, command run, coding run, and result are kept
  distinct. Acceptance, completion, event publication, and UI receipt remain
  distinct.
- Provider account identity remains separate from Codexify user identity;
  personas do not own permission or identity truth.
- This documentation creates no durable mutation, token domain, release claim,
  provider schema, connector, terminal, or delegation behavior.
