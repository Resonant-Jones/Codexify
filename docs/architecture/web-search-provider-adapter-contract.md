# Search-as-RAG Provider Adapter Contract

Purpose: define the future Search-as-RAG provider adapter as the first Web Agent adapter seam. This is a contract for external indexed retrieval, not live browsing automation. It is architecture/specification only and does not describe current runtime support.

## 1. Purpose

This contract names the future boundary where Codexify can ask a search provider or search-backed index for relevant remote evidence, normalize the response, screen it for safety, preserve provenance, and hand normalized evidence back to the retrieval pipeline.

It does not describe browser control, URL reading, structured extraction, or service-connector access. It also does not describe current runtime behavior.

## 2. Relationship to Web Agent Spec

This contract implements the future shape of `search_as_rag` only.

It explicitly excludes:

- `url_read`
- `structured_extract`
- `live_browser_automation`
- `google_service_connector`

The Web Agent Spec remains the mode-level source for the broader boundary: [Web Agent Spec v1](./web-agent-spec.md).

## 3. Relationship to Retrieval Router

This adapter sits behind an explicit broadened retrieval posture such as the existing `explicit_global_search` intent.

This task does not introduce a new router intent token. The router remains the decision seam, while the adapter is the execution seam for external indexed retrieval.

See the router doctrine here: [Retrieval Router Decision Table](./router-decision-table.md).

## 4. Adapter Boundary

The future adapter boundary is:

1. inbound normalized request
2. egress and permission check
3. provider invocation
4. result normalization
5. safety screening
6. provenance capture
7. return of normalized evidence

Provider adapters must not perform synthesis. Synthesis happens after this boundary, in the retrieval or completion pipeline that consumes normalized evidence.

Adapter output is not synthesis-ready until it is accepted by the Web Evidence Intake Gate: [Web Evidence Intake Gate Contract](./web-evidence-intake-gate-contract.md).

## 5. Conceptual Data Shapes

The following shapes are docs-only and conceptual. They describe the contract a future implementation should satisfy without prescribing code structure.

| Shape | Purpose | Conceptual fields |
|---|---|---|
| `SearchProviderAdapter` | Future adapter seam that invokes a provider, applies policy, and returns normalized evidence | `provider`, `allowed_providers`, `egress_policy_snapshot`, `safe_search_or_content_filter`, `supports_locale`, `supports_time_window`, `supports_quota_snapshot`, `invoke_policy`, `normalize_result`, `screen_for_injection`, `capture_provenance` |
| `SearchProviderRequest` | Inbound normalized request for external indexed retrieval | `request_id`, `user_id`, `thread_id`, `project_id`, `source_message_id`, `query`, `retrieval_mode`, `provider`, `allowed_providers`, `egress_policy_snapshot`, `safe_search_or_content_filter`, `locale`, `time_window`, `max_results` |
| `SearchProviderResult` | Normalized provider response ready for downstream consumption | `request_id`, `provider`, `retrieval_mode`, `status`, `result_count`, `results`, `provider_metadata`, `quota_cost_metadata`, `safety_classification`, `prompt_injection_flags`, `blocked_reason`, `evidence_hash` |
| `SearchResultItem` | Single normalized search hit | `result_url`, `title`, `snippet`, `display_url`, `rank`, `fetched_at`, `provider_metadata`, `quota_cost_metadata`, `content_hash`, `evidence_hash`, `safety_classification`, `prompt_injection_flags` |
| `SearchProviderTrace` | Operator and diagnostics trace for the provider run | `request_id`, `user_id`, `thread_id`, `project_id`, `source_message_id`, `provider`, `query`, `retrieval_mode`, `egress_policy_snapshot`, `egress_decision`, `quota_cost_metadata`, `result_count`, `blocked_reason`, `safety_classification`, `persistence_decision` |
| `SearchProviderQuotaSnapshot` | Conceptual quota or budget snapshot attached to a provider run | `request_id`, `provider`, `user_id`, `project_id`, `quota_cost_metadata`, `window`, `cost_units`, `limit_hint`, `remaining_hint`, `reset_at`, `provider_metadata` |

## 6. Provider Candidate Posture

Candidate providers may include:

- Google search-related APIs
- other search APIs
- local or private indexes
- hosted extraction or search vendors

No provider is selected by this contract. Provider choice is future implementation work. Quota, pricing, capability, and terms must be verified when implementation begins.

Credentials must be backend-side or OAuth-backed. They must never depend on frontend-held secrets.

## 7. Egress and Authorization

Egress policy must be evaluated before any provider invocation.

The request must be scoped by user, account, and project where applicable. Account-bound service data requires explicit authorization.

Public indexed retrieval is not the same thing as authenticated service-connector retrieval. Public search does not grant permission to bypass source access controls.

## 8. Safety and Prompt-Injection Handling

Remote snippets and provider metadata are untrusted data.

Provider results must not become instructions.

Prompt-injection screening is required before synthesis.

Search snippets may be incomplete, stale, or adversarial. Adapter output should preserve suspicious-content flags rather than silently dropping uncertainty.

## 9. Provenance and Persistence

Search results must preserve provider, query, URL, rank, timestamp, and evidence hash.

Persisted web-derived artifacts must preserve lineage to thread, source message, project, and provider or tool run.

Durable persistence is optional and explicit. If persisted artifacts enter export or restore flows, their provenance must remain restorable.

## 10. Diagnostics and Operator Truth

Future diagnostics should expose:

- provider selected
- query issued
- egress decision
- quota or cost snapshot when available
- result count
- blocked or filtered result reasons
- safety classification
- extraction or synthesis boundary
- persistence decision

These diagnostics belong in diagnostics or operator surfaces unless the user explicitly asks for source details.

## 11. Failure Classes

The following failure vocabulary is docs-only:

- `provider_not_configured`
- `egress_blocked`
- `auth_required`
- `quota_exceeded`
- `provider_unavailable`
- `empty_result_set`
- `low_confidence_results`
- `safety_screen_blocked`
- `normalization_failed`

These values remain docs-only until implementation promotes repeated contract-bearing values into canonical protocol or domain tokens.

## 12. Non-Goals

- No implementation
- No endpoint
- No worker
- No frontend UI
- No Google API integration
- No quota claims
- No scraping bypass
- No browser automation
- No replacement for local, thread, or project retrieval
- No automatic persistence of web results

## 13. Implementation Readiness Checklist

Future implementation work must satisfy all of the following:

- provider selected and current docs verified
- egress policy wired
- backend-side credential handling
- canonical tokens created for repeated statuses or errors
- contract tests for normalized request and result shapes
- prompt-injection screening seam
- provenance and hash capture
- diagnostics surface
- no frontend secrets
- docs updated with current runtime truth only after implementation proof
