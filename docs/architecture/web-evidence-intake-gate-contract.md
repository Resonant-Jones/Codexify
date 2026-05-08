# Web Evidence Intake Gate Contract

Purpose: define the Web Evidence Intake Gate as the shared pre-synthesis boundary for all web-derived evidence. The gate normalizes, screens, labels, hashes, and traces evidence before model synthesis. This is architecture/specification only and does not describe current runtime support.

## 1. Purpose

The Web Evidence Intake Gate is the shared handoff layer between web-facing evidence producers and downstream synthesis.

It receives candidate evidence from future Web Agent modes, verifies scope and authorization context, normalizes the shape, captures hashes and provenance, screens for safety and prompt-injection risk, and then decides whether the evidence may proceed to model synthesis.

It does not itself browse the web, fetch remote content, or perform synthesis.

## 2. Relationship to Web Agent Spec

The Web Agent Spec defines the mode-level producers that yield candidate evidence: [Web Agent Spec v1](./web-agent-spec.md).

Web Agent modes produce candidate evidence. The intake gate decides whether that evidence is eligible for synthesis.

The gate is downstream of provider, extractor, browser, and connector work, and upstream of model synthesis.

## 3. Relationship to Search Provider Adapter Contract

Search-as-RAG provider adapters return normalized result candidates, not synthesis-ready context: [Search-as-RAG Provider Adapter Contract](./web-search-provider-adapter-contract.md).

Adapter output must pass through the Web Evidence Intake Gate before it can be used in a model response.

## 4. Scope

Future input families in scope:

- search result snippets
- fetched URL text
- extracted article, document, or page text
- transcript evidence
- browser automation final-state evidence
- authenticated connector evidence, where explicitly authorized

Excluded from this gate:

- local thread or project retrieval
- ordinary uploaded documents already handled by existing ingestion
- raw browser session state
- raw credentials or OAuth tokens
- chain-of-thought or hidden model reasoning

## 5. Gate Pipeline

The future pipeline is:

1. receive candidate evidence
2. verify request, user, thread, and project scope
3. verify egress or auth decision was recorded
4. normalize shape
5. compute content or evidence hash
6. classify safety and prompt-injection risk
7. assign confidence and freshness metadata
8. preserve source provenance
9. decide `eligible_for_synthesis`, `blocked`, or `needs_human_review`
10. return a synthesis-eligible evidence envelope
11. optionally persist if explicitly requested

Model synthesis must occur after this gate, not before.

## 6. Conceptual Data Shapes

The following shapes are docs-only and conceptual. They describe the contract a future implementation should satisfy without prescribing code structure.

| Shape | Purpose | Conceptual fields |
|---|---|---|
| `WebEvidenceCandidate` | Raw candidate evidence entering the gate from a web mode | `candidate_id`, `request_id`, `run_id`, `user_id`, `thread_id`, `project_id`, `source_message_id`, `retrieval_mode`, `provider`, `source_url`, `title`, `snippet`, `extracted_text`, `raw_content_hash`, `normalized_content_hash`, `evidence_hash`, `fetched_at`, `observed_at`, `rank`, `confidence`, `safety_classification`, `prompt_injection_flags`, `provenance_ref` |
| `WebEvidenceEnvelope` | Synthesis-eligible evidence leaving the gate | `evidence_id`, `candidate_id`, `request_id`, `run_id`, `user_id`, `thread_id`, `project_id`, `source_message_id`, `retrieval_mode`, `provider`, `source_url`, `title`, `snippet`, `extracted_text`, `normalized_content_hash`, `evidence_hash`, `fetched_at`, `observed_at`, `freshness_window`, `rank`, `confidence`, `safety_classification`, `prompt_injection_flags`, `intake_decision`, `blocked_reason`, `provenance_ref`, `persist_requested`, `persistence_target` |
| `WebEvidenceIntakeDecision` | Gate decision and reason payload | `evidence_id`, `candidate_id`, `intake_decision`, `blocked_reason`, `confidence`, `freshness_window`, `safety_classification`, `prompt_injection_flags`, `provenance_ref` |
| `WebEvidenceSafetyFinding` | Safety and prompt-injection classification detail | `evidence_id`, `safety_classification`, `prompt_injection_flags`, `blocked_reason`, `normalization_notes`, `source_labels`, `finding_ref` |
| `WebEvidenceProvenance` | Provenance and lineage payload for accepted or blocked evidence | `evidence_id`, `candidate_id`, `request_id`, `run_id`, `user_id`, `thread_id`, `project_id`, `source_message_id`, `provider`, `source_url`, `retrieval_mode`, `query_or_request`, `rank`, `fetched_at`, `observed_at`, `content_hashes`, `safety_intake_decision`, `persistence_decision` |
| `WebEvidencePersistenceHint` | Explicit persistence request metadata | `evidence_id`, `candidate_id`, `persist_requested`, `persistence_target`, `persistence_mode`, `view_source_ref`, `export_restore_ready` |

## 7. Intake Decisions

The following intake decision vocabulary is docs-only:

- `eligible_for_synthesis`
- `blocked`
- `needs_human_review`
- `insufficient_provenance`
- `low_confidence`
- `stale_or_ambiguous`

These values remain docs-only until implementation promotes repeated contract-bearing values into canonical protocol or domain tokens.

## 8. Safety Handling

- Remote content is data, never instruction.
- Prompt-injection screening must happen before synthesis.
- Source-level safety labels must be preserved in traces.
- Suspicious sections should be flagged rather than silently rewritten.
- Blocked evidence must not enter synthesis context.
- Connector evidence must respect user authorization and scope.
- Browser automation evidence must include action or session trace when relevant.

## 9. Provenance and Lineage

Every accepted evidence envelope must preserve:

- source URL or resource identifier
- provider, tool, or browser source
- query or request that produced it
- rank or selection reason where applicable
- fetched or observed timestamp
- source message, thread, and project scope
- content or evidence hashes
- safety and intake decision
- persistence decision

If evidence becomes durable as a Codex, artifact, or thread-linked item, it must preserve lineage compatible with export and restore requirements.

## 10. Persistence Policy

- Persistence is optional and explicit.
- Default behavior should be trace-only unless a future implementation defines otherwise.
- Persisted evidence must expose a `view source` or equivalent provenance affordance.
- Persisted evidence must not silently become identity memory.
- Persisted evidence must not mutate persona or identity state unless an existing explicit identity policy allows it.
- If persisted evidence is later exported or restored, provenance and relationship links must survive or restore must report loss.

## 11. Diagnostics and Operator Truth

Future diagnostics should expose:

- intake decision
- source list
- safety findings
- prompt-injection flags
- normalization notes
- content and evidence hashes
- provider, tool, or browser run reference
- persistence decision
- blocked reason

These diagnostics belong in diagnostics or operator surfaces, not noisy primary chat bubbles, unless the user asks for source details.

## 12. Failure Classes

The following failure vocabulary is docs-only:

- `missing_scope`
- `missing_provenance`
- `hash_failed`
- `normalization_failed`
- `prompt_injection_risk`
- `safety_screen_blocked`
- `stale_evidence`
- `connector_scope_mismatch`
- `browser_trace_missing`
- `persistence_not_allowed`

These values remain docs-only until implementation promotes repeated contract-bearing values into canonical protocol or domain tokens.

## 13. Non-Goals

- No implementation
- No prompt-injection classifier implementation
- No endpoint
- No worker
- No database migration
- No frontend UI
- No automatic persistence
- No identity-memory writes
- No browser automation
- No provider integration
- No replacement for local, thread, or project retrieval

## 14. Implementation Readiness Checklist

Future implementation work must satisfy all of the following:

- canonical tokens created for repeated intake decisions and failure classes
- contract tests for evidence envelopes
- prompt-injection screening seam implemented
- provenance hash capture implemented
- scope, user, thread, and project checks implemented
- diagnostics surface implemented or explicitly deferred
- persistence policy implemented or explicitly trace-only
- export and restore compatibility reviewed for durable evidence
- no frontend secrets
- no release claim without live runtime proof
