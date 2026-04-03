# Codexify Core / Release Truth Competitive Parity Audit

Purpose: audit Codexify against a fixed competitor floor drawn from AnythingLLM and Open WebUI. The goal is to separate the minimum credible free-tier parity floor, real current edges, honest gaps, and code/runtime areas that are not yet safe release claims.

This is an evidence-bound audit. It does not re-research competitors.

## Method / Evidence Policy

- `00-current-state.md` wins on release readiness, supported install path, active blockers, and present-release promise.
- Status comes from current runtime docs and proof artifacts in this repo. Legacy Threadspace, GuardianOS, and installer-era material is not used as runtime truth.
- `capabilities-audit.md` is consulted only as exposure framing. It does not override runtime proof.
- Proof classes used here:
  - supported-path proof: live current-runtime evidence on the supported local Docker Compose path
  - backend seam proof: route, broker, worker, or test-seam proof without a full release claim
  - contract/spec only: normative or design language without runtime proof

Evidence keys used in the table:

| Key | Source |
|---|---|
| `RB` | [`README.md`](./README.md) |
| `CS` | [`00-current-state.md`](./00-current-state.md) |
| `OV` | [`system-overview.md`](./system-overview.md) |
| `FL` | [`flows.md`](./flows.md) |
| `DS` | [`data-and-storage.md`](./data-and-storage.md) |
| `CO` | [`config-and-ops.md`](./config-and-ops.md) |
| `MO` | [`modules-and-ownership.md`](./modules-and-ownership.md) |
| `TR` | [`tech-debt-and-risks.md`](./tech-debt-and-risks.md) |
| `SP` | [`2026-04-01-current-head-supported-path-proof.md`](./2026-04-01-current-head-supported-path-proof.md) |
| `DR` | [`2026-04-01-deterministic-retrieval-proof.md`](./2026-04-01-deterministic-retrieval-proof.md) |
| `RT` | [`2026-03-31-rag-trace-e2e-proof.md`](./2026-03-31-rag-trace-e2e-proof.md) |
| `SS` | [`2026-03-31-source-selector-proof.md`](./2026-03-31-source-selector-proof.md) |
| `CC` | [`chat-runtime-contract.md`](./chat-runtime-contract.md) |
| `PS` | [`persona-studio.md`](./persona-studio.md) |
| `EX` | [`account-export-restore-contract.md`](./account-export-restore-contract.md) |
| `OB` | [`obsidian-live-runtime-proof.md`](./obsidian-live-runtime-proof.md) |
| `OI` | [`obsidian-ingest-proof.md`](./obsidian-ingest-proof.md) |

## Status Vocabulary

| Label | Meaning |
|---|---|
| `proven_supported_path` | Proven on the current supported local Docker Compose path. Safe to treat as release truth for the current spine. |
| `proven_backend_seam` | Proven in a backend, route, broker, or test seam, but not yet as a full release claim. |
| `present_not_in_release_promise` | Present in runtime/topology or supporting architecture, but outside the current release promise. |
| `partial_or_boundary_sensitive` | Partially true, boundary-sensitive, or too unstable to turn into a simple release claim. |
| `not_yet_proven` | No current authoritative proof in the repo. |
| `not_current_target` | Explicitly outside the current release target or only described as future work. |

Release-claim shorthand used below:

- `safe`: defensible as current supported-path truth
- `seam-only`: real, but only backed by backend or test seams
- `not safe`: present or partial, but not safe to market as shipped
- `contract only`: normative doc exists, but not runtime proof
- `future only`: outside the current release target

## Comparison Table

| Capability | Competitor floor | Codexify status | Current evidence | Release-claim safety | Edge classification | Notes / risk |
|---|---|---|---|---|---|---|
| Core parity floor - threaded persistent chat | Persistent threaded chat | `proven_supported_path` | `CS + OV + FL + SP` | safe | floor | Thread chat is the core supported flow; acceptance still must be read separately from completion. |
| Core parity floor - document upload | Document upload + semantic RAG ingestion | `proven_supported_path` | `CS + OV + FL + SP` | safe | floor | Upload is proven on the current-head supported path and the embedding lifecycle reaches `ready`. |
| Core parity floor - upload -> embed -> retrieve loop | Upload, embed, and retrieval in one path | `proven_supported_path` | `CS + SP + FL` | safe for the mounted retrieval-equivalent path | floor | The current-head proof passes on the mounted query-based retrieval seam; legacy `POST /api/retrieve` is still `404`. |
| Core parity floor - retrieval in chat from active thread/project context | Workspace/document-scoped retrieval | `proven_backend_seam` | `DR + SS + RT + FL` | seam-only | edge | Active-thread-first, project-local widening, and personal-knowledge widening are proven at the broker seam, not as a fresh chat UI claim. |
| Core parity floor - retrieval transparency / RAG trace / source visibility | Visible source grounding | `proven_backend_seam` | `RT + SS + DR` | seam-only | edge | Trace payloads preserve `source_mode`, `widen_reason`, and retrieved document metadata, but the trace is not a durable release-grade operator surface yet. |
| Core parity floor - full-document attach / brute-force context mode | Attached/full-document mode | `proven_backend_seam` | `OV + FL + DS + SP` | not safe | gap | Linked thread/project documents are injected, but there is no safe claim of a user-visible whole-document attach mode. |
| Core parity floor - retrieval controls (source selection, depth, scope) | Snippet count / threshold / scope controls | `proven_backend_seam` | `SS + DR + RT + CC` | seam-only | edge | Source selection and widening scope are proven in backend seams; UI exposure is not yet a release-safe parity claim. |
| Core parity floor - RAG reranking | Rerank-style retrieval sophistication | `not_current_target` | `PS` | contract only | gap | Persona Studio drafts mention `rerank`, but the runtime is not wired and this is not part of the current release promise. |
| Core parity floor - chunking controls | Chunking controls | `not_current_target` | `PS` | contract only | gap | Worker chunking exists, but there is no current user-facing control surface or release-safe control claim. |
| Core parity floor - citations / visible provenance | Citations / visible source grounding | `partial_or_boundary_sensitive` | `RT + SS + SP` | not safe | gap | Backend traces expose provenance, but chat-level citation rendering is not proven as a current supported-path claim. |
| Core parity floor - chat import / ChatGPT history import | ChatGPT history import | `not_current_target` | `EX` | contract only | gap | The export/restore contract is normative only; no runtime importer is proven in the current release truth set. |
| Core parity floor - chat export / account export | Export-friendly chat/document workflows | `not_current_target` | `EX` | contract only | gap | Account export is a contract, not a shipped runtime surface in the current truth set. |
| Core parity floor - local-first install path | Local/self-hosted install | `proven_supported_path` | `RB + CS + CO + SP` | safe | floor | Supported install path is local Docker Compose with backend, frontend, Postgres, Redis, and workers. |
| Core parity floor - local-model-first runtime posture | Local model first, cloud optional | `proven_supported_path` | `CS + CO + SP` | safe | floor | Supported profile is local-only by default, cloud providers are quarantined, and the active model is local. |
| Knowledge-source expansion - Obsidian/local vault ingest | Local vault ingestion | `proven_backend_seam` | `OB + OI + DS + OV` | not safe | edge | Live CLI ingest and retriever seam proof exist, but it is not a released connector surface. |
| Knowledge-source expansion - URL/web knowledge ingestion | Web URL ingestion | `not_current_target` | No current runtime proof in the current-source set | future only | gap | No current authoritative doc proves a web crawler or URL ingest path. |
| Knowledge-source expansion - YouTube knowledge ingestion | YouTube ingestion | `not_current_target` | No current runtime proof in the current-source set | future only | gap | No current authoritative doc proves a YouTube ingest path. |
| Knowledge-source expansion - Google/Drive-style connector ingestion | Cloud connector ingestion | `not_current_target` | No current runtime proof in the current-source set | future only | gap | No current authoritative doc proves Google Drive or comparable cloud connector ingestion. |
| Knowledge-source expansion - general connector ecosystem | Connector ecosystem | `present_not_in_release_promise` | `OV + DS + MO + CO` | not safe | internal-only | Generic connector scaffolding exists, but the supported profile quarantines connectors and only GitHub is concretely surfaced. |
| Advanced context / differentiation - project-scoped vs personal-knowledge retrieval modes | Workspace/project vs personal scopes | `proven_backend_seam` | `DR + SS + RT` | seam-only | edge | Active-thread-first, project-local widening, and same-user personal-knowledge widening are better scoped than a generic RAG default. |
| Advanced context / differentiation - graph / Neo4j / PKG-assisted context | Graph-assisted context | `present_not_in_release_promise` | `OV + DS + CO + MO` | not safe | internal-only | Optional graph context exists in topology and config, but it is not part of the current release promise. |
| Advanced context / differentiation - identity / persona / prompt-shaping system | Persona/profile shaping | `partial_or_boundary_sensitive` | `DS + CC + PS + OV` | not safe | edge | Prompt shaping and identity boundaries exist, but Persona Studio is frontend-local and automatic runtime binding is still partial. |
| Advanced context / differentiation - operator truth surfaces / health reconciliation | Operator diagnostics surfaces | `partial_or_boundary_sensitive` | `CS + CO + TR + SP` | not safe | edge | The repo has richer operator truth surfaces than a single chat pane, but release signoff still requires multi-surface reconciliation. |
| Advanced context / differentiation - automation / scheduler surfaces | Automation / scheduler | `present_not_in_release_promise` | `OV + FL + MO + CS` | not safe | internal-only | Cron exists as a supporting runtime surface, but current-state does not elevate it into the supported spine. |
| Advanced context / differentiation - command bus / tool execution surface | Tool execution | `present_not_in_release_promise` | `OV + FL + MO + CO` | not safe | internal-only | Command bus and legacy tools coexist, but supported-profile docs mark command_bus internal-only. |
| Advanced context / differentiation - shareable artifacts / thread-document sharing | Shareable artifacts | `present_not_in_release_promise` | `DS + MO + FL` | not safe | internal-only | Shared links and collaboration tables exist, but there is no current supported-path proof of a share workflow. |
| Advanced context / differentiation - media/image handling relevant to the current product shape | Media / image handling | `partial_or_boundary_sensitive` | `CS + OV + FL + DS + SP` | not safe | gap | Media and image tables exist, and browser-dev media rendering was fixed, but image-specific release proof is thin. |

## Where Codexify Is Actually Ahead

- Local-first governance is real, not aspirational: current-state, config, and supported-path proof all point to local Docker Compose plus local-only model posture as the supported spine. That is release-safe for the core path. Evidence: `CS`, `CO`, `SP`, `RB`.
- Retrieval boundaries are stricter than a generic RAG default: active thread first, same-user widening, project-local widening, and explicit `source_mode` / `widen_reason` trace fields are all proven in backend seams. That is an actual scoped-retrieval edge, but it is seam-safe rather than a full user-facing parity claim. Evidence: `DR`, `SS`, `RT`, `FL`.
- Operator truth is more explicit than a single chat screen: queue health, task events, LLM health, vector health, and retrieval probes are all separated. That is a real operator edge, but the repo still treats it as multi-surface truth, not a single polished signoff surface. Evidence: `CS`, `CO`, `TR`, `SP`.
- Identity and prompt boundaries are more explicit than typical RAG apps: the data model, chat runtime contract, and Persona Studio docs all keep persona/prompt shaping separate from raw chat history. That is an architectural edge, but it is only partially wired at runtime. Evidence: `DS`, `CC`, `PS`, `OV`.
- Local vault ingest exists as a genuine local-first knowledge path: the Obsidian live proof shows a real vault can be ingested and retrieved through the configured local vector backend. It is an edge for local-first users, but it is not a released connector surface. Evidence: `OB`, `OI`, `DS`, `OV`.

## Where Codexify Is Behind Or Not Yet Safe To Claim

- Chat-level citations are not safe to claim yet. The repo proves trace payloads and source metadata at backend seams, but not a durable supported-path chat citation surface. Evidence: `RT`, `SS`, `TR`.
- Rerank, chunking, and retrieval tuning controls are not safe to claim yet. Persona Studio drafts mention some of these fields, but the runtime is not bound and there is no current supported-path proof. Evidence: `PS`, `EX`.
- Full-document attach is not safe to claim yet. Linked documents are injected, but there is no release-safe user-visible whole-doc mode or brute-force context toggle in the current truth set. Evidence: `FL`, `DS`, `SP`.
- Chat import / ChatGPT history import and account export are contract-level work, not runtime truth. They are useful architectural targets, but they are not shipped surfaces in the current supported path. Evidence: `EX`.
- URL/web, YouTube, and Drive-style knowledge ingestion are not current targets in the evidence set. No current authoritative runtime doc proves them. Evidence: none in the current-source set.
- General connector breadth is not safe to market as core. The repo has connector scaffolding, but the supported profile quarantines connectors and the only concretely surfaced connector path is GitHub. Evidence: `OV`, `MO`, `CO`, `DS`.
- Cron, command bus, sharing, and graph surfaces exist, but they are supporting, experimental, or internal-only rather than current beta claims. They are useful backend surfaces, not parity claims. Evidence: `OV`, `MO`, `CO`, `DS`, `FL`, `CS`.
- Persona Studio is not a live runtime claim yet. It is frontend-local and the automatic binding from saved profile state into live chat behavior is still partial. Evidence: `PS`, `CS`, `SP`.
- The supported retrieval story is now better, but the strongest current claim is the mounted retrieval-equivalent query path. The legacy `POST /api/retrieve` route still returned `404` in the current-head proof, so any claim that depends on that exact route is not safe. Evidence: `SP`, `CS`.

## Minimum Credible Core Tier

What Codexify already has that is enough to be credible:

- Local Docker Compose install with a local model posture.
- Threaded chat with queue-backed completion and persisted assistant output.
- Document upload followed by embedding readiness and retrieval on the mounted query-based retrieval seam.
- Scoped retrieval behavior that can distinguish active thread, project, and personal-knowledge widening.
- Traceable operator surfaces for health, queue state, and retrieval inspection.

What must be true to claim AnythingLLM parity:

- Document upload and semantic RAG must be release-safe on the supported path, not just seam-safe.
- Workspace/document-scoped retrieval must be visible as a stable user-facing behavior.
- A full-document attach or equivalent whole-doc mode must be a safe claim.
- Retrieval tuning must be real, not just implied by backend internals.
- Export-friendly chat/document workflows must exist as shipped surfaces, not just as a contract.

What must be true to claim Open WebUI parity:

- Everything required for AnythingLLM parity must be true first.
- Visible citations or provenance must be safe to claim in the chat surface.
- Chunking controls and rerank / hybrid-search sophistication must be real, not draft fields.
- URL, web, and YouTube ingestion must be release-safe.
- ChatGPT import / export must be proven, not just specified.

Launch-blocking missing items for parity claims:

- Chat-level citations.
- Release-safe rerank and chunking controls.
- Safe full-document attach mode.
- ChatGPT import / export runtime proof.
- URL, web, YouTube, and Drive-style ingestion.
- A claim that depends on the legacy `POST /api/retrieve` route rather than the mounted retrieval-equivalent query path.

Post-launch ammunition:

- Obsidian/local vault ingest.
- Command bus and cron surfaces.
- Graph and federation surfaces.
- Shareable artifacts and collaboration surfaces.
- Persona Studio hardening.
- Media and image handling proof.
- Better operator dashboards and single-pane reconciliation.

Minimum credible conclusion:

- Codexify is credible today as a local-first chat-and-knowledge workspace with queue-backed completion, supported document ingest, and scoped retrieval boundaries.
- It is not yet safe to claim parity with AnythingLLM or Open WebUI on the competitor floor items that depend on user-visible citations, rerank/chunk controls, web or video ingestion, or chat import/export.
