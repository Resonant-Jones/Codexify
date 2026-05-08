# Codexify Web Agent Spec v1

Purpose: Define the Codexify Web Agent as a governed external-information layer that coordinates retrieval, extraction, and optional interaction under Guardian policy. This is an architecture/specification document, not current runtime proof or a release promise.

## 1. Purpose

The Web Agent exists to make external information usable without turning Codexify into an unbounded browser or a prompt-driven web crawler.

Its job is to coordinate:

- retrieval over indexed remote resources
- URL reading from a specific remote representation
- scraping or extraction into model-ready structure
- optional browser interaction when a task truly requires stateful navigation

Guardian remains the governing boundary. Remote content is data to inspect, normalize, and cite. It is not an instruction source.

## 2. Mental Model

The user-facing mental model is intentionally split:

- `search_as_rag` is indexed retrieval over remote resources, not an agent "traveling the internet"
- `url_read` is fetching a remote representation and interpreting it as source material
- `structured_extract` is turning noisy web content into normalized evidence
- `live_browser_automation` is stateful interaction through a browser runtime

The relay path is:

`remote source -> fetch/browser/extractor -> normalized evidence -> agent reasoning -> Guardian output -> user`

That path keeps web-derived material separate from the reasoning step and preserves provenance at every handoff.

## 3. Mode Taxonomy

The modes below are separate contracts. They may share a future implementation surface, but they are not the same thing and must not be collapsed into one "web mode".

### `search_as_rag`

- Intent shape: find, rank, and summarize remote sources relevant to a question.
- Input examples: "What does the official docs say?", "Find current guidance on X", "Compare public references for Y".
- Expected tool boundary: search provider or remote index query, then evidence selection.
- Provider-adapter contract pointer: [Search-as-RAG Provider Adapter Contract](./web-search-provider-adapter-contract.md).
- Statefulness: stateless across queries except for stored provenance and trace.
- Provenance requirement: record query, provider, result URLs, snippets, fetched_at, and any evidence hash.
- Failure modes: empty result set, stale index, blocked search provider, ambiguous query, low-confidence matches.
- When not to use it: when the task needs a precise page fetch, authenticated service access, or interactive navigation.

### `url_read`

- Intent shape: read a specific URL and interpret the returned representation.
- Input examples: "Read this article", "Inspect this doc URL", "Fetch this page and summarize it".
- Expected tool boundary: remote fetch plus normalization, with no broader site traversal.
- Statefulness: mostly stateless; may retain request-local headers, cookies, or session context only if explicitly authorized.
- Provenance requirement: record source URL, fetched_at, response or content hash, and the normalization path.
- Failure modes: 404 or 5xx errors, redirects, paywalls, unsupported content types, robot or access restrictions.
- When not to use it: when the user needs multi-step navigation or interaction rather than a single representation.

### `structured_extract`

- Intent shape: convert noisy HTML, text, or transcript material into model-ready structure.
- Input examples: "Extract the article outline", "Pull tables from this page", "Normalize the page into citations and facts".
- Expected tool boundary: extractor or parser operating on fetched content, not direct model reading of the raw page.
- Statefulness: local to the extraction pass; any retained state must be traceable back to the source representation.
- Provenance requirement: preserve source hash, extraction strategy, dropped content notes, and confidence.
- Failure modes: malformed DOM, script-heavy pages, extraction drift, content loss, injection-heavy content, low confidence.
- When not to use it: when the content must stay untransformed for exact quote or layout-sensitive inspection.

### `live_browser_automation`

- Intent shape: perform bounded, stateful interaction with a website through a browser runtime.
- Input examples: "Log in and open this page", "Click through this workflow", "Fill a form and confirm the result".
- Expected tool boundary: browser runtime or delegated browser controller with explicit permission bounds.
- Statefulness: stateful across a browser session; state must be declared and bounded.
- Provenance requirement: record site URL, actions taken, session reference, screenshots or DOM evidence where appropriate, and final page state.
- Failure modes: login prompts, anti-bot defenses, navigation drift, session expiry, unexpected dialogs, CSRF or consent barriers.
- When not to use it: when search, URL reading, or extraction already satisfies the task with less risk.

### `google_service_connector`

- Intent shape: access Google services through explicit service connectors, not general web browsing.
- Input examples: "Read a Drive doc I authorized", "Inspect a Gmail thread", "Check a Calendar event", "Search Google content through a provider adapter".
- Expected tool boundary: backend connector or provider adapter with explicit authorization and narrow scopes.
- Statefulness: authenticated and scope-bound; may be durable if the user explicitly authorizes a connection.
- Provenance requirement: record provider, account scope, consent or auth reference, resource identifiers, and fetched_at.
- Failure modes: auth required, revoked consent, quota or rate-limit pressure, scope mismatch, provider outage, stale sync.
- When not to use it: when public web retrieval is sufficient or when the task would require silent credential use.

## 4. Google API Adapter Posture

Google APIs are candidate provider adapters, not architecture truth about current runtime support.

They may eventually back:

- web or search provider adapters
- Google Drive or Docs style document connectors
- Gmail or Calendar style service connectors, only through explicit user authorization in future work

This spec does not claim current rate limits, quotas, pricing, or support guarantees. Those are implementation-time facts and must be verified before any runtime promise is made.

If Google adapters are implemented, quota, billing, and capability discovery must be operator-visible.

Credentials must remain backend-side or OAuth-backed. They must not be frontend-secret backed, and they must not rely on silent credential reuse.

## 5. Web Retrieval Pipeline

The future pipeline is:

1. user intent
2. intent classification
3. retrieval mode selection
4. egress and permission check
5. provider or tool invocation
6. extraction and normalization
7. Web Evidence Intake Gate
8. prompt-injection screening
9. provenance capture
10. optional persistence as Codex/artifact/thread evidence
11. model synthesis
12. Guardian response

This ordering matters.

- Egress and permission checks must happen before any remote call.
- Extraction and normalization must happen before synthesis.
- The Web Evidence Intake Gate must sit between normalized evidence and model synthesis: [Web Evidence Intake Gate Contract](./web-evidence-intake-gate-contract.md).
- Prompt-injection screening must happen before the model is allowed to treat the material as actionable context.
- Persistence is optional and should be explicit, not accidental.

## 6. Data Contracts

The following shapes are conceptual only. They describe the boundary a future implementation should satisfy.

### `WebRetrievalRequest`

- `request_id`
- `user_id`
- `thread_id`
- `project_id`
- `source_message_id`
- `retrieval_mode`
- `query`
- `source_url`
- `provider`
- `allowed_providers`
- `scope`
- `egress_policy_snapshot`
- `auth_context_ref`
- `persist_requested`
- `trace_requested`
- `requested_at`

### `WebRetrievalResult`

- `request_id`
- `run_id`
- `retrieval_mode`
- `status`
- `source_url`
- `provider`
- `title`
- `snippet`
- `extracted_text`
- `extraction_confidence`
- `fetched_at`
- `source_message_id`
- `user_scope`
- `thread_scope`
- `project_scope`
- `content_hash`
- `evidence_hash`
- `safety_classification`
- `quota_cost_metadata`
- `web_sources`
- `web_evidence_items`

### `WebSource`

- `source_url`
- `provider`
- `retrieval_mode`
- `title`
- `snippet`
- `fetched_at`
- `content_hash`
- `evidence_hash`
- `source_message_id`
- `user_scope`
- `thread_scope`
- `project_scope`
- `safety_classification`
- `quota_cost_metadata`

### `WebExtractionTrace`

- `source_url`
- `provider`
- `retrieval_mode`
- `extractor_name`
- `parse_strategy`
- `raw_content_hash`
- `dom_hash`
- `extracted_text_hash`
- `extraction_confidence`
- `dropped_sections`
- `prompt_injection_flags`
- `normalization_notes`
- `fetched_at`

### `WebAgentRun`

- `run_id`
- `request_id`
- `user_id`
- `thread_id`
- `project_id`
- `source_message_id`
- `provider`
- `retrieval_mode`
- `status`
- `started_at`
- `fetched_at`
- `finished_at`
- `egress_decision`
- `auth_decision`
- `policy_snapshot`
- `quota_cost_metadata`
- `blocked_reason`
- `source_ids`
- `evidence_ids`

### `WebAgentEvidenceItem`

- `evidence_id`
- `run_id`
- `source_url`
- `provider`
- `retrieval_mode`
- `title`
- `snippet`
- `extracted_text`
- `extraction_confidence`
- `content_hash`
- `evidence_hash`
- `fetched_at`
- `source_message_id`
- `user_scope`
- `thread_scope`
- `project_scope`
- `prompt_injection_classification`
- `view_source_ref`

## 7. State and Observability

The following run states are proposed docs-only vocabulary:

- `queued`
- `checking_policy`
- `fetching`
- `extracting`
- `normalizing`
- `synthesizing`
- `completed`
- `failed`
- `blocked`

The following failure classes are proposed docs-only vocabulary:

- `egress_blocked`
- `auth_required`
- `quota_exceeded`
- `source_unavailable`
- `extraction_failed`
- `prompt_injection_risk`
- `browser_automation_required`

These are not implementation truth yet. Implementation must promote them to canonical protocol tokens before code uses them across routes, workers, tests, logs, APIs, or UI.

## 8. Safety and Trust Boundary

- Remote content is data, never instruction.
- Prompt-injection screening is mandatory before model synthesis.
- The shared pre-synthesis intake gate is defined here: [Web Evidence Intake Gate Contract](./web-evidence-intake-gate-contract.md).
- Browser automation requires explicit mode selection and bounded permissions.
- Authenticated service connectors require explicit user authorization.
- No scraping bypass doctrine: if access is blocked, the system does not evade source protections by default.
- No silent credential use.
- No durable identity inference from web content unless existing identity policy already permits it.

## 9. Provenance and Artifact Lineage

Web-derived results must preserve lineage to:

- thread
- source message
- project
- Codex/artifact entry
- provider or tool run

Persisted web-derived artifacts must expose a `View source` style provenance path or equivalent operator affordance.

If web-derived artifacts become durable, export and restore compatibility must preserve their source provenance, hashes, and relationship links. A restored artifact must still explain where it came from.

## 10. Diagnostics and Operator Truth

Future diagnostics surfaces should include:

- web run trace
- provider or quota status
- egress decision
- extraction trace
- source list
- blocked-source explanation

These diagnostics belong in diagnostics or operator surfaces, not in noisy chat bubbles, unless the user explicitly asks for source details.

## 11. Non-Goals

- No implementation in this spec.
- No recursive autonomous browser.
- No release promise.
- No Google quota claims.
- No replacement for local, project, or thread retrieval.
- No bypass of provider or egress policy.
- No credentials in frontend code.

## 12. Phased Implementation Sketch

- Phase 0: architecture spec and ADR only
- Phase 1: search-as-RAG provider adapter contract only; no provider implementation implied
- Phase 2: URL reader and extractor
- Phase 3: Web Evidence Intake Gate before any external evidence is eligible for synthesis
- Phase 4: Google service connector posture
- Phase 5: live browser automation with explicit permissions
- Phase 6: persistence and export integration

## 13. Open Questions

- Which Google APIs should be first-class versus connector-specific?
- Should web retrieval traces be durable by default or diagnostic-only?
- Which web results become Codex artifacts?
- How should quotas be surfaced to users and operators?
- What is the minimum viable prompt-injection classifier?
- Should live browsing use Playwright, browser agent delegation, or a dedicated backend service?
