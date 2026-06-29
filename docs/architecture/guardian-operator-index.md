# Guardian Operator Index

Purpose: Provide a compact, Guardian-facing retrieval index that maps operator intents to the canonical docs, health checks, setup notes, troubleshooting rituals, and architecture truth anchors they need. This is a routing/index surface, not a runtime proof source.

Last updated: 2026-06-27

Classification: docs-only architecture contract. It does not implement runtime retrieval, connector logic, UI changes, database changes, background workers, or prompt assembler behavior.

Governing docs and contracts:
- [`00-current-state.md`](./00-current-state.md)
- [`README.md`](./README.md)
- [`kb-validity-matrix.md`](./kb-validity-matrix.md)
- [`agent-protocol-operations.md`](./agent-protocol-operations.md)
- [`config-and-ops.md`](./config-and-ops.md)
- [`system-overview.md`](./system-overview.md)
- [`flows.md`](./flows.md)
- [`modules-and-ownership.md`](./modules-and-ownership.md)
- [`runtime-protocol-token-contract.md`](./runtime-protocol-token-contract.md)
- [`canonical-token-philosophy.md`](./canonical-token-philosophy.md)

## Purpose

This index exists so Guardian can quickly locate, retrieve, and surface operator-facing knowledge without relying on broad semantic search alone. It maps a small, stable set of operator intent classes to the specific docs and probes that answer them.

It is a retrieval/orientation aid. It does not change runtime behavior, release claims, queue/worker semantics, identity boundaries, provider routing, connector behavior, or supported release posture.

## Scope

- Define an index entry schema that Guardian or a future retrieval helper can parse.
- Define a stable set of operator intent classes.
- Map intent classes to canonical docs, health checks, and failure signatures.
- Provide initial index entries for the core architecture and operator docs.
- Provide connector placeholder entries with explicit no-runtime-proof boundaries.
- Provide a failure lookup table mapping operator symptoms to first docs.
- Provide example operator queries Guardian should be able to route.

## Non-goals

- This index is not a runtime retrieval implementation.
- This index is not a source of runtime proof. Catalog presence, route presence, connector names, or an entry here do not prove live support.
- This index does not widen the supported beta release promise. The supported path remains local Docker Compose with local-only provider posture.
- This index does not prove connector functionality, GitHub PAT handling, Obsidian/Google/GitHub/web-search connector runtime behavior, or any UI surface.
- This index does not introduce prompt-based authority as a substitute for retrieval or runtime policy.
- This index does not expose secrets, PATs, API keys, tokens, or connector credentials.

## How Guardian should use this index

- Treat this index as a router: read the operator's question, map it to one or more intent classes, then surface the `primary_doc` and `supporting_docs` for the matching entries.
- Always defer to `00-current-state.md` for short-horizon release/runtime truth. If an entry conflicts with current-state truth, current-state wins.
- Before quoting a doc as current runtime evidence, check its `source_of_truth_rank` and consult [`kb-validity-matrix.md`](./kb-validity-matrix.md).
- Surface probe/health commands from `validation_or_probe_commands` when the operator asks "is it healthy?" Do not fabricate endpoints.
- Never paste credentials into chat. Connector setup entries redirect to local secret/config paths only.
- When a symptom matches a `related_failure_signatures` row, route to the failure lookup table first.
- Do not claim an entry proves a capability is shipped. Entries route to docs; docs are not runtime proof unless backed by live supported-path evidence.

## Index entry schema

Every index entry follows this shape so Guardian or a future retrieval helper can parse it consistently. Fields are optional unless marked required.

```text
id:                    # required; stable snake_case identifier, no ad hoc synonyms
title:                 # required; short human-readable label
intent_classes:        # required; one or more values from Operator intent classes
aliases:               # alternate phrasings/operators synonyms this entry should match
primary_doc:           # required; the single doc to surface first
supporting_docs:       # additional docs for depth or cross-checking
source_of_truth_rank:  # where this entry sits in Source-of-truth priority
when_to_surface:       # operator situations that should trigger this entry
do_not_use_for:        # questions this entry must NOT be used to answer
freshness_rule:        # how to tell if the entry or its doc is stale
operator_summary:      # 1-3 sentence plain-language summary
validation_or_probe_commands:  # health checks / probes / commands to run
related_failure_signatures:    # symptom keys from the Failure lookup table
```

Conventions:
- `id` values are stable labels. Do not introduce ad hoc synonyms for repeated operator concepts; add new aliases to the existing entry instead.
- `primary_doc` is the first doc to retrieve. `supporting_docs` widen context only.
- Every entry must stay compact enough for Guardian to retrieve and reason over.

## Source-of-truth priority

When sources conflict, Guardian must apply these rules in order for short-horizon operator and release truth:

1. [`00-current-state.md`](./00-current-state.md) wins for short-horizon release/runtime truth, release readiness, supported install path, active blockers, and current priorities.
2. [`config-and-ops.md`](./config-and-ops.md) wins for environment variables, supported checks, and operator verification workflow, unless `00-current-state.md` narrows it.
3. [`flows.md`](./flows.md) wins for trigger-to-output runtime sequencing, unless current-state docs narrow release claims.
4. [`system-overview.md`](./system-overview.md) wins for coarse runtime component mapping.
5. [`modules-and-ownership.md`](./modules-and-ownership.md) wins for subsystem seams, dependency edges, and blast radius.
6. [`kb-validity-matrix.md`](./kb-validity-matrix.md) wins when deciding whether a doc is safe to use as current runtime evidence.
7. UI canon docs (e.g. [`codexify_workspace_surface_spec_v_1.md`](./codexify_workspace_surface_spec_v_1.md), [`persona-studio-spec.md`](./persona-studio-spec.md), `docs/dev/ARTIFACT*.md`) are valid for UI work only, not backend/runtime claims.
8. The [Architecture Atlas](./architecture-atlas.md) is a guide, not the source of truth itself.
9. This Operator Index is a routing/index surface, not a runtime proof source.

## Operator intent classes

Guardian maps operator questions to one or more of these stable intent classes. Do not invent ad hoc synonyms; reuse these labels.

```text
current_state           # what is true / supported / blocked right now
start_stop_reset        # bring the stack up, down, or recover from a bad state
health_check            # is the runtime actually healthy?
provider_check          # is the configured provider reachable, warm, and authorized?
chat_pipeline           # accept -> enqueue -> worker -> provider -> persist -> events
rag_retrieval           # context assembly, retrieval depth, source modes, workspace retrieval
connector_setup         # configure an external source connector (status may be unproven)
github_pat_setup        # GitHub credential/PAT handling (doctrine only; not runtime-proven)
obsidian_setup          # Obsidian-backed workspace retrieval / indexing
google_setup            # Google-style connector (doctrine only; not runtime-proven)
task_prompting          # writing Codexify task prompts and issue work packets
architecture_change     # work that touches contracts, runtime meaning, or release claims
ui_surface              # Workspace / Persona Studio / UI canon routing
workspace_surface       # Workspace Shelf / Scratchpad / Inspector behavior
failure_diagnosis       # map a symptom to a first doc and a probe
release_boundary        # what is and is not part of the supported beta promise
collaborator_onboarding # first docs for a new operator or agent
```

## Initial index entries

These are the foundational truth anchors, topology, ops, validity, risk, and agent-ritual docs. Operator-facing docs that fit a single narrow domain are indexed in the topical sections that follow (Runtime and health, Retrieval and RAG, Task and delegation, UI and workspace, Connector and tool setup). Every required operator doc appears exactly once as a full index entry.

```text
id: current_state_truth
title: Current state and release truth
intent_classes: current_state, release_boundary, collaborator_onboarding
aliases: what is supported right now, release readiness, active blockers, beta posture
primary_doc: docs/architecture/00-current-state.md
supporting_docs: docs/architecture/README.md, docs/architecture/kb-validity-matrix.md
source_of_truth_rank: 1 (wins for short-horizon release/runtime truth)
when_to_surface: any question about what is supported, blocked, shipped, or part of the beta promise
do_not_use_for: implementation detail; topology; UI canon
freshness_rule: check the file's "Last updated" line; it is the override for older docs
operator_summary: Canonical short-horizon operational truth for release readiness, supported install path (local Docker Compose, local-only provider posture), active blockers, and current priorities. It overrides older or broader docs.
validation_or_probe_commands: GET /health, GET /api/llm/catalog
related_failure_signatures: release_hold, provider_catalog_mismatch
```

```text
id: system_topology
title: System overview and runtime topology
intent_classes: current_state, chat_pipeline, rag_retrieval, architecture_change
aliases: runtime components, topology, critical paths, node boundaries
primary_doc: docs/architecture/system-overview.md
supporting_docs: docs/architecture/flows.md, docs/architecture/modules-and-ownership.md
source_of_truth_rank: 4 (coarse runtime component mapping)
when_to_surface: "what are the runtime components?", "where does X live?", critical-path questions
do_not_use_for: release claims; operator verification steps (use config-and-ops)
freshness_rule: verify against current routes/workers; Last updated 2026-04-27
operator_summary: Current runtime components, deployment topology, runtime boundaries, provider governance, and critical paths (chat completion, RAG assembly, ingestion, tool execution, sync/federation).
validation_or_probe_commands: docker compose config
related_failure_signatures: route_accepted_no_answer, provider_catalog_mismatch
```

```text
id: critical_flows
title: Critical runtime flows
intent_classes: chat_pipeline, rag_retrieval, failure_diagnosis
aliases: chat completion flow, RAG flow, ingestion flow, acceptance semantics, turn lock
primary_doc: docs/architecture/flows.md
supporting_docs: docs/architecture/completion_pipeline.md, docs/architecture/chat-runtime-contract.md
source_of_truth_rank: 3 (trigger-to-output runtime sequencing)
when_to_surface: "why did chat accept but never answer?", sequencing, failure-mode, or acceptance-semantics questions
do_not_use_for: release scope decisions (current-state wins)
freshness_rule: verify anchors against current code; Last updated 2026-05-08
operator_summary: Highest-value runtime flows in trigger-to-output form with explicit failure modes and acceptance semantics (acceptance != completion; task-event publication != UI receipt).
validation_or_probe_commands: GET /api/tasks/{task_id}/events
related_failure_signatures: 429_turn_in_flight, 503_queue_unavailable, route_accepted_no_answer, task_events_missing
```

```text
id: config_and_ops
title: Config and ops
intent_classes: start_stop_reset, health_check, provider_check, failure_diagnosis
aliases: env vars, config precedence, health checks, run commands, failure signatures
primary_doc: docs/architecture/config-and-ops.md
supporting_docs: docs/architecture/system-overview.md, docs/architecture/00-current-state.md
source_of_truth_rank: 2 (env vars, supported checks, operator verification workflow)
when_to_surface: "how do I check health?", "which env vars matter?", "what is the supported run path?", operator verification
do_not_use_for: release-scope interpretation (current-state wins)
freshness_rule: verify env vars against guardian/core/config.py; Last updated 2026-05-08
operator_summary: Environment variables, config resolution order, local dev commands, healthchecks, the beta operator verification workflow, common failure signatures, and the workspace Obsidian E2E proof harness.
validation_or_probe_commands: GET /health, GET /health/chat, GET /health/llm, GET /api/llm/catalog, docker compose config, make test
related_failure_signatures: 401_unauthorized, 429_turn_in_flight, 503_queue_unavailable, provider_catalog_mismatch, workspace_retrieval_missing
```

```text
id: modules_and_ownership
title: Modules and ownership
intent_classes: architecture_change, failure_diagnosis, collaborator_onboarding
aliases: subsystem map, dependency edges, blast radius, high-coupling hotspots
primary_doc: docs/architecture/modules-and-ownership.md
supporting_docs: docs/architecture/system-overview.md, docs/architecture/README.md
source_of_truth_rank: 5 (subsystem seams and blast radius)
when_to_surface: planning a change, assessing blast radius, locating a subsystem seam
do_not_use_for: runtime sequencing (use flows); release truth
freshness_rule: verify against current code anchors; Last updated 2026-03-11
operator_summary: Subsystem matrix, dependency edges that matter most, high-coupling hotspots, and change-planning heuristics.
validation_or_probe_commands: (none; orientation doc)
related_failure_signatures: route_accepted_no_answer
```

```text
id: data_and_storage
title: Data and storage
intent_classes: architecture_change, rag_retrieval, failure_diagnosis
aliases: persistence, storage systems, invariants, migrations
primary_doc: docs/architecture/data-and-storage.md
supporting_docs: docs/architecture/flows.md, docs/architecture/config-and-ops.md
source_of_truth_rank: below flows for storage/persistence invariants
when_to_surface: storage, schema, migration, or persistence-invariant questions
do_not_use_for: runtime flow sequencing (use flows)
freshness_rule: verify against guardian/db/models.py and migrations; Last updated 2026-04-22
operator_summary: Storage systems in use, key entities, persistence invariants, and data risk hotspots.
validation_or_probe_commands: make test (migration tests)
related_failure_signatures: rag_result_missing
```

```text
id: kb_validity_matrix
title: KB validity matrix
intent_classes: current_state, architecture_change, collaborator_onboarding
aliases: which docs are safe, diagram source sets, quarantined docs, classification
primary_doc: docs/architecture/kb-validity-matrix.md
supporting_docs: docs/architecture/00-current-state.md, docs/architecture/architecture-atlas.md
source_of_truth_rank: 6 (decides whether a doc is safe as current runtime evidence)
when_to_surface: "can I trust this doc as runtime evidence?", before diagram generation or reuse
do_not_use_for: answering runtime behavior directly (it classifies, it does not describe)
freshness_rule: re-audit when new docs are added or identity drift reappears
operator_summary: Classifies the architecture corpus into authoritative_now, supplementary_verify_against_code, design_canon_not_runtime_truth, historical_archive, and misleading_identity_drift. Defines runtime and UI diagram source sets and quarantined docs.
validation_or_probe_commands: (none; classification doc)
related_failure_signatures: provider_catalog_mismatch
```

```text
id: architecture_atlas
title: Architecture atlas
intent_classes: collaborator_onboarding, current_state, architecture_change
aliases: reading order, peer review, validated corpus
primary_doc: docs/architecture/architecture-atlas.md
supporting_docs: docs/architecture/kb-validity-matrix.md, docs/architecture/adr/adr-index.md
source_of_truth_rank: 8 (guide, not source of truth)
when_to_surface: onboarding a new operator/agent; choosing a reading order
do_not_use_for: proof of runtime behavior
freshness_rule: verify recommended reading order against current corpus
operator_summary: Peer-facing reading guide into the validated corpus, current-truth model, two-view (runtime vs UI) model, and a peer review checklist. It is a guide, not the source of truth.
validation_or_probe_commands: (none; orientation doc)
related_failure_signatures: (none)
```

```text
id: tech_debt_and_risks
title: Tech debt and risks
intent_classes: architecture_change, failure_diagnosis, release_boundary
aliases: risk register, blockers, cautions, beta limitations
primary_doc: docs/architecture/tech-debt-and-risks.md
supporting_docs: docs/architecture/00-current-state.md, docs/architecture/config-and-ops.md
source_of_truth_rank: risk overlay; not the active-blocker list unless repeated in current-state
when_to_surface: assessing risk of a change; release caveats
do_not_use_for: current active blockers (use current-state); topology
freshness_rule: evidence-backed; re-check against current audit window; Last updated 2026-04-21
operator_summary: Evidence-backed risk register with beta release classifications (blocker, caution, acceptable limitation, operator burden). Use as a risk overlay, not as the active-blocker list.
validation_or_probe_commands: (none; risk register)
related_failure_signatures: 503_queue_unavailable, route_accepted_no_answer
```

```text
id: agent_protocol_operations
title: Agent protocol operations
intent_classes: task_prompting, architecture_change, collaborator_onboarding
aliases: agent rituals, task workflow, architecture-impact lane, validation expectations
primary_doc: docs/architecture/agent-protocol-operations.md
supporting_docs: docs/architecture/README.md, docs/Ops/codexify-issue-template-contract.md
source_of_truth_rank: ritual/orientation surface; below governing ADRs
when_to_surface: before writing or executing a Codexify task; architecture-impact questions
do_not_use_for: runtime proof; replacing ADRs or task files
freshness_rule: stable rituals; verify links still resolve
operator_summary: Agent-facing map for operational rituals: where to start, architecture-impact workflow, validation interpretation, docs/code disagreement handling, and contingency protocols. An index, not a replacement for governing docs.
validation_or_probe_commands: make test, make lint (as applicable to the task surface)
related_failure_signatures: (none)
```

## Connector and tool setup entries

These are placeholder entries. Each one states explicitly that runtime setup is NOT proven by this docs-only task. Connectors referenced here may appear in ADR doctrine or catalogs without being shipped runtime support.

```text
id: connector_github
title: GitHub connector (placeholder)
intent_classes: connector_setup, github_pat_setup
aliases: github, PAT, repo connector
primary_doc: docs/architecture/adr/024-context-command-active-connector-semantics.md
supporting_docs: docs/architecture/00-current-state.md, docs/architecture/runtime-protocol-token-contract.md
source_of_truth_rank: doctrine only; NOT runtime proof
when_to_surface: operator asks about GitHub integration, GitHub context, or PAT setup
do_not_use_for: claiming GitHub connector runtime support; pasting credentials
freshness_rule: recheck when a connector verification task lands
operator_summary: GitHub-style connector context exists as ADR-024 doctrine only. No GitHub connector runtime, no PAT handling, and no write-capable workflow is proven by this docs-only task.
validation_or_probe_commands: (none; no runtime connector proven)
related_failure_signatures: connector_not_visible
setup_status_boundaries:
  - Known setup status is NOT proven by this docs-only task.
  - Credentials must NEVER be pasted into chat.
  - PAT/API-key setup must be handled through local secret/config paths only.
  - Read-only validation should come before any write-capable workflow.
  - Runtime proof requires a later connector-specific verification task.
```

```text
id: connector_obsidian
title: Obsidian connector (placeholder)
intent_classes: connector_setup, obsidian_setup, rag_retrieval
aliases: obsidian, vault, workspace notes, local knowledge
primary_doc: docs/architecture/flows.md
supporting_docs: docs/architecture/config-and-ops.md, docs/architecture/router-decision-table.md, docs/architecture/adr/024-context-command-active-connector-semantics.md
source_of_truth_rank: retrieval seam proven via harness; full connector write/sync NOT runtime proof
when_to_surface: operator asks about Obsidian indexing, workspace notes, or vault setup
do_not_use_for: claiming Obsidian sync/write automation is shipped
freshness_rule: recheck against current workspace proof harness status
operator_summary: Obsidian-backed workspace-local retrieval for source_mode=workspace is the supported retrieval seam on the local Compose path (proven via scripts/proofs/prove_workspace_obsidian_e2e.py). A full Obsidian "connector" with sync/write automation is NOT runtime-proven by this docs-only task.
validation_or_probe_commands: python scripts/proofs/prove_workspace_obsidian_e2e.py, GET /health, GET /health/chat
related_failure_signatures: workspace_retrieval_missing, rag_result_missing
setup_status_boundaries:
  - Known setup status for full connector write/sync is NOT proven by this docs-only task.
  - Credentials must NEVER be pasted into chat.
  - Any API-key/token setup must be handled through local secret/config paths only.
  - Read-only validation should come before any write-capable workflow.
  - Runtime proof of broader connector behavior requires a later connector-specific verification task.
```

```text
id: connector_google
title: Google connector (placeholder)
intent_classes: connector_setup, google_setup
aliases: google, drive, gcs
primary_doc: docs/architecture/adr/024-context-command-active-connector-semantics.md
supporting_docs: docs/architecture/00-current-state.md
source_of_truth_rank: doctrine only; NOT runtime proof
when_to_surface: operator asks about Google/Drive-style integration
do_not_use_for: claiming Google connector runtime support; pasting credentials
freshness_rule: recheck when a connector verification task lands
operator_summary: Google/Drive-style connector context exists as ADR-024 doctrine only. No Google connector runtime, no credential handling, and no write-capable workflow is proven by this docs-only task.
validation_or_probe_commands: (none; no runtime connector proven)
related_failure_signatures: connector_not_visible
setup_status_boundaries:
  - Known setup status is NOT proven by this docs-only task.
  - Credentials must NEVER be pasted into chat.
  - API-key/OAuth setup must be handled through local secret/config paths only.
  - Read-only validation should come before any write-capable workflow.
  - Runtime proof requires a later connector-specific verification task.
```

```text
id: connector_web_search
title: Future web search connector (placeholder)
intent_classes: connector_setup, rag_retrieval
aliases: web search, search-as-rag, remote recall, global search
primary_doc: docs/architecture/web-search-provider-adapter-contract.md
supporting_docs: docs/architecture/web-agent-spec.md, docs/architecture/web-evidence-intake-gate-contract.md, docs/architecture/config-and-ops.md
source_of_truth_rank: implementation seam, default-off; NOT supported beta proof
when_to_surface: operator asks about web search, Search-as-RAG, or Remote Recall
do_not_use_for: claiming web search is part of the supported beta promise
freshness_rule: recheck REMOTE_RECALL_ENABLED / GROQ_WEB_SEARCH_ENABLED posture and current-state
operator_summary: A Remote Recall Search-as-RAG seam (Groq built-in web search adapter) exists behind explicit flags with unit-test proof only. It is default-off (REMOTE_RECALL_ENABLED=false, GROQ_WEB_SEARCH_ENABLED=false) and is NOT part of the supported beta release promise. Web search as a general "connector" is NOT runtime-proven by this docs-only task.
validation_or_probe_commands: (none for supported beta; seam is default-off)
related_failure_signatures: rag_result_missing
setup_status_boundaries:
  - Known setup status for general web-search connector support is NOT proven by this docs-only task.
  - Credentials must NEVER be pasted into chat.
  - Provider API-key setup must be handled through local secret/config paths only.
  - Read-only validation should come before any write-capable workflow.
  - Runtime proof requires a later connector-specific verification task and live supported-path evidence.
```

## Runtime and health entries

```text
id: chat_runtime_contract
title: Chat runtime contract
intent_classes: chat_pipeline, provider_check, failure_diagnosis
aliases: provider runtime state, request state, message vs request identity, replay
primary_doc: docs/architecture/chat-runtime-contract.md
supporting_docs: docs/architecture/runtime-protocol-token-contract.md, docs/architecture/flows.md
source_of_truth_rank: normative vocabulary; verify against current code
when_to_surface: provider state vs request state, warming/connecting, message/attempt identity, replay
do_not_use_for: topology (use system-overview); release scope
freshness_rule: verify token vocabulary against runtime-protocol-token-contract; Last updated 2026-03-29
operator_summary: Normative frontend/shared-runtime vocabulary for provider runtime state, request execution state, message-vs-attempt identity, UI presentation, and replay handling.
validation_or_probe_commands: GET /health/llm
related_failure_signatures: model_slow_warming_no_first_token, route_accepted_no_answer
```

```text
id: runtime_protocol_tokens
title: Runtime protocol token contract
intent_classes: chat_pipeline, failure_diagnosis, architecture_change
aliases: status strings, event names, error codes, canonical tokens
primary_doc: docs/architecture/runtime-protocol-token-contract.md
supporting_docs: docs/architecture/canonical-token-philosophy.md, docs/architecture/chat-runtime-contract.md
source_of_truth_rank: canonical token registry; verify against guardian/protocol_tokens.py
when_to_surface: decoding a status/event/error code; adding a new runtime literal
do_not_use_for: topology; release scope
freshness_rule: verify tokens against code before quoting; recheck when new tokens land
operator_summary: Canonical source for runtime protocol tokens: acceptance statuses, task event types, machine-readable error codes, campaign runner statuses, trace suppression/absence reasons. New literals must come from the registry, not ad hoc strings.
validation_or_probe_commands: (none; token registry)
related_failure_signatures: 429_turn_in_flight, 503_queue_unavailable, task_events_missing
```

```text
id: completion_pipeline
title: Completion request pipeline
intent_classes: chat_pipeline, failure_diagnosis
aliases: completion pipeline, queue-backed completion, accept to complete
primary_doc: docs/architecture/completion_pipeline.md
supporting_docs: docs/architecture/flows.md, docs/architecture/config-and-ops.md
source_of_truth_rank: supplementary_verify_against_code; flows.md is the fresher sequencing source
when_to_surface: deep-diving the queue-backed completion path and actors
do_not_use_for: current sequencing truth without verifying against flows.md and code
freshness_rule: older deep dive; verify against current routes/workers
operator_summary: Older deep dive into the queue-backed chat completion path, its actors, and responsibilities. Useful detail, but verify against flows.md and current code.
validation_or_probe_commands: GET /api/tasks/{task_id}/events
related_failure_signatures: route_accepted_no_answer, 503_queue_unavailable
```

## Retrieval and RAG entries

```text
id: retrieval_router
title: Retrieval router decision table
intent_classes: rag_retrieval, architecture_change
aliases: retrieval posture, source mode, router policy, conversation vs workspace vs global
primary_doc: docs/architecture/router-decision-table.md
supporting_docs: docs/architecture/flows.md, docs/architecture/system-overview.md
source_of_truth_rank: canonical retrieval-router doctrine
when_to_surface: "what should I read before changing retrieval behavior?", source-mode/posture questions
do_not_use_for: provider routing (use system-overview/provider governance)
freshness_rule: verify runtime scaffold against guardian/context/retrieval_router_policy.py; Last updated 2026-05-04
operator_summary: First canonical retrieval-router doctrine: a reference table plus runtime scaffold that decides retrieval posture before ContextBroker assembly, keeping heuristics out of prompt/provider code.
validation_or_probe_commands: GET /debug/rag-trace/{thread_id}/latest (dev-only)
related_failure_signatures: rag_result_missing, workspace_retrieval_missing
```

## Task and delegation entries

```text
id: codexify_issue_template
title: Codexify issue template contract
intent_classes: task_prompting, collaborator_onboarding
aliases: task prompt, issue work packet, Axis task, board metadata
primary_doc: docs/Ops/codexify-issue-template-contract.md
supporting_docs: docs/architecture/agent-protocol-operations.md, docs/Ops/docs-to-issue-compiler-protocol.md
source_of_truth_rank: canonical issue/task shape; docs-only
when_to_surface: "what should I read before writing a Codexify task prompt?", creating a work packet
do_not_use_for: runtime behavior; board automation (explicitly out of scope)
freshness_rule: stable contract; verify required fields still match current practice
operator_summary: Canonical GitHub issue-body shape for Codexify work packets. Docs-only: it describes how Axis/Codex/board exchange task context through issues and does not implement Actions, .github/ templates, scripts, or board automation. Note: the canonical file lives under docs/Ops/, not docs/architecture/.
validation_or_probe_commands: (none; docs-only contract)
related_failure_signatures: (none)
```

## UI and workspace entries

```text
id: workspace_surface_spec
title: Workspace surface spec v1
intent_classes: ui_surface, workspace_surface
aliases: workspace, shelf, scratchpad, inspector, dashboard/guardian/documents
primary_doc: docs/architecture/codexify_workspace_surface_spec_v_1.md
supporting_docs: docs/architecture/persona-studio-spec.md, docs/architecture/kb-validity-matrix.md
source_of_truth_rank: 7 (UI canon; UI work only, not backend/runtime claims)
when_to_surface: "where is Workspace behavior defined?", UI/layout/interaction/persistence questions for Workspace
do_not_use_for: backend/runtime topology; health; worker behavior; supported-path truth
freshness_rule: UI canon; if it conflicts with runtime KB, runtime truth wins
operator_summary: UI/design canon defining Workspace as Shelf + Scratchpad + Inspector across Dashboard, Guardian, and Documents. Explicitly not runtime truth.
validation_or_probe_commands: (none; UI canon)
related_failure_signatures: (none)
```

```text
id: persona_studio_spec
title: Persona Studio spec
intent_classes: ui_surface, collaborator_onboarding
aliases: persona studio, agent command center, profiles, model behavior config
primary_doc: docs/architecture/persona-studio-spec.md
supporting_docs: docs/architecture/persona-studio.md, docs/architecture/codexify_workspace_surface_spec_v_1.md
source_of_truth_rank: 7 (UI/product canon; UI work only, not backend/runtime claims)
when_to_surface: "where is Persona Studio defined?", profile/model/voice/tool/retrieval configuration UI questions
do_not_use_for: runtime provider routing; release truth
freshness_rule: product spec; verify against current frontend implementation
operator_summary: Product spec for Persona Studio as a non-conversational configuration/observability interface for agent profiles (model behavior, voice, system prompt, tools, retrieval/memory policy). UI/product canon, not runtime topology.
validation_or_probe_commands: (none; product spec)
related_failure_signatures: (none)
```

## Failure lookup table

Map an operator symptom to the first doc(s) to consult, then to a probe. Symptom keys are referenced by index entries via `related_failure_signatures`.

| Symptom key | Operator symptom | First doc(s) | First probe | Likely cause |
|---|---|---|---|---|
| `401_unauthorized` | `401 Unauthorized` | [`config-and-ops.md`](./config-and-ops.md), [`agent-protocol-operations.md`](./agent-protocol-operations.md) | `GET /health` (does backend boot? is `GUARDIAN_API_KEY` set?) | Missing/invalid API key or auth-mode/exposure mismatch |
| `409_conflict` | `409 Conflict` | [`flows.md`](./flows.md), [`config-and-ops.md`](./config-and-ops.md) | `GET /api/tasks/{task_id}/events` | Turn-lock contention or command-bus idempotency conflict |
| `429_turn_in_flight` | `429 turn_in_flight` | [`flows.md`](./flows.md), [`runtime-protocol-token-contract.md`](./runtime-protocol-token-contract.md) | `GET /api/tasks/{task_id}/events`, inspect worker heartbeat | Existing turn lock; stale-lock recovery refused to guess on ambiguous evidence |
| `503_queue_unavailable` | `503 queue_unavailable` | [`flows.md`](./flows.md), [`config-and-ops.md`](./config-and-ops.md) | `GET /health/chat` (Redis reachability, enqueue, worker heartbeat) | Redis unavailable or chat enqueue failure (`QUEUE_ENQUEUE_FAILED`) |
| `model_slow_warming_no_first_token` | model slow / warming / no first token | [`chat-runtime-contract.md`](./chat-runtime-contract.md), [`config-and-ops.md`](./config-and-ops.md) | `GET /health/llm`, `GET /api/llm/catalog` | Provider runtime state is `model_warming`/`connecting`, or provider connectivity/timeout |
| `route_accepted_no_answer` | route accepted but no answer | [`flows.md`](./flows.md), [`completion_pipeline.md`](./completion_pipeline.md) | `GET /api/tasks/{task_id}/events`, worker logs | Acceptance != completion: chat worker down, provider timeout, or task queued without completion |
| `task_events_missing` | task events missing | [`flows.md`](./flows.md), [`runtime-protocol-token-contract.md`](./runtime-protocol-token-contract.md) | `GET /api/events`, `GET /api/tasks/{task_id}/events` | Task-event publish failure (`TASK_EVENT_PUBLISH_FAILED`); lifecycle visibility degraded without stopping execution |
| `provider_catalog_mismatch` | provider catalog mismatch | [`config-and-ops.md`](./config-and-ops.md), [`system-overview.md`](./system-overview.md) | `GET /api/llm/catalog`, `GET /api/llm/catalog?include=all`, `GET /health/llm` | Provider selectable in catalog but not actually supported/executable; registry/health/catalog disagree |
| `connector_not_visible` | connector not visible | connector placeholder entries above, [`adr/024-context-command-active-connector-semantics.md`](./adr/024-context-command-active-connector-semantics.md) | (none; doctrine only) | Connector is ADR doctrine/catalog name only; no runtime connector shipped or proven |
| `rag_result_missing` | RAG result missing | [`router-decision-table.md`](./router-decision-table.md), [`flows.md`](./flows.md) | `GET /debug/rag-trace/{thread_id}/latest` (dev-only) | Retrieval posture excluded the source; vector store empty; depth `shallow`; broker filtered the candidate |
| `workspace_retrieval_missing` | workspace retrieval not surfacing expected notes | [`flows.md`](./flows.md), [`config-and-ops.md`](./config-and-ops.md) | `python scripts/proofs/prove_workspace_obsidian_e2e.py` | Obsidian note not indexed; `source_mode` not `workspace`; broker selection/injection not proven for that turn |

Routing notes:
- A green `GET /health` alone is never beta proof. Read `config-and-ops.md`'s beta readiness operator verification workflow before calling `go`.
- `route_accepted_no_answer` and `task_events_missing` are distinct: acceptance is real even when lifecycle visibility is degraded.
- `connector_not_visible` must never be "fixed" by assuming a connector exists. Verify against a connector-specific runtime task first.

## Example operator queries

Guardian should be able to route each of these to the entry id(s) and primary doc(s) shown.

| Operator query | Routed intent class(es) | Entry id(s) | Primary doc |
|---|---|---|---|
| How do I check if Codexify is actually healthy? | health_check | `config_and_ops`, `current_state_truth` | [`config-and-ops.md`](./config-and-ops.md) |
| Why did chat accept but never answer? | failure_diagnosis, chat_pipeline | `critical_flows`, `completion_pipeline` | [`flows.md`](./flows.md) |
| Which doc explains local provider setup? | provider_check, start_stop_reset | `config_and_ops` | [`config-and-ops.md`](./config-and-ops.md) |
| Where do I look for Redis or worker health? | health_check | `config_and_ops` | [`config-and-ops.md`](./config-and-ops.md) |
| How do I know whether a connector is configured? | connector_setup | `connector_github`, `connector_obsidian`, `connector_google`, `connector_web_search` | [`adr/024-context-command-active-connector-semantics.md`](./adr/024-context-command-active-connector-semantics.md) |
| What should I read before changing retrieval behavior? | rag_retrieval, architecture_change | `retrieval_router`, `critical_flows` | [`router-decision-table.md`](./router-decision-table.md) |
| What should I read before writing a Codexify task prompt? | task_prompting | `agent_protocol_operations`, `codexify_issue_template` | [`agent-protocol-operations.md`](./agent-protocol-operations.md) |
| What source wins for current release truth? | current_state, release_boundary | `current_state_truth`, `kb_validity_matrix` | [`00-current-state.md`](./00-current-state.md) |
| Where is the Workspace behavior defined? | ui_surface, workspace_surface | `workspace_surface_spec` | [`codexify_workspace_surface_spec_v_1.md`](./codexify_workspace_surface_spec_v_1.md) |
| Where is Persona Studio defined? | ui_surface | `persona_studio_spec` | [`persona-studio-spec.md`](./persona-studio-spec.md) |

## Maintenance rules

- Keep the index compact. It must stay retrievable and reason-over-able by Guardian.
- Use stable `id` and `intent_classes` labels. Do not introduce ad hoc synonyms for repeated operator concepts; extend `aliases` on the existing entry instead.
- When a new operator doc is added, add one entry in the matching topical section and choose a stable `id`.
- When a doc's release truth changes, update `source_of_truth_rank` and `operator_summary`; never use this index to override `00-current-state.md`.
- Connector entries must keep their `setup_status_boundaries` block intact until a connector-specific verification task proves runtime behavior.
- Do not add runtime claims, error-prone credentials, or prompt-based authority to entries.
- Re-validate this index against `kb-validity-matrix.md` classifications whenever the corpus is re-audited.
- Do not treat the existence of an entry, a route, a catalog name, or a connector name as proof of live support.

## Future runtime integration deferred

This index is intentionally docs-only. The following are explicitly deferred to later runtime tasks and must NOT be implied by this document:

- Runtime retrieval integration (wiring this index into retrieval/router/prompt-assembly code paths).
- Context broker integration.
- Prompt assembler integration.
- Connector verification docs (GitHub, Obsidian write/sync, Google, web search).
- UI search/index surface (Command Center / Observability Deck).
- Slash-command routing onto this index.
- Automated index validation script.

Any of the above requires its own task with explicit scope, ADR alignment where applicable, and live supported-path evidence before it can be claimed as shipped. Until then, this index is a routing/orientation surface only.
