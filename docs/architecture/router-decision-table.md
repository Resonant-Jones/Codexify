Purpose: define the first canonical retrieval-router doctrine for Guardian so contributors can reason about retrieval posture without embedding ad hoc heuristics in chat, prompt, or provider code.
Last updated: 2026-04-16
Source anchors:
- docs/architecture/README.md
- docs/architecture/system-overview.md
- docs/architecture/flows.md
- guardian/context/broker.py
- guardian/core/chat_completion_service.py
- guardian/context/retrieval_router_policy.py

# Retrieval Router Decision Table

## Why This Exists

Codexify's current runtime already separates completion routing, context
assembly, and provider execution. The retrieval decision point belongs in the
orchestration layer that sits before `ContextBroker` assembly, not in prompt
text and not in UI controls.

This document establishes the first canonical policy table for that seam.
It is doctrine plus contract only. It does not claim that the live completion
flow already consults this policy.

## Reference Table vs Runtime Scaffold

- `reference table`
  - Human-readable guidance for contributors.
  - Explains which query intents should stay conversation-only, which should
    stay local, and which may justify broader retrieval or graph enrichment.
- `runtime scaffold`
  - Machine-readable policy contract exported from
    `guardian/context/retrieval_router_policy.py`.
  - Mirrors the same tokens and default rules so future orchestration can adopt
    one canonical registry instead of re-inventing literals in routes,
    prompts, or workers.

The table is the doctrine. The scaffold is the backend contract. Neither one
introduces live retrieval behavior changes in this task.

## Intent Classes

- `conversation_only`: answer from the active conversation without retrieval.
- `direct_qa`: targeted question that may need ordinary local retrieval.
- `memory_recall`: recall prior user/thread/project memory.
- `timeline_recall`: reconstruct ordered events or state changes.
- `provenance`: explain where a claim, document, or fact came from.
- `exploratory`: broad inquiry where wider evidence gathering may help.
- `explicit_global_search`: the user explicitly asks for a broadened search.
- `scope_locked_local`: the user explicitly constrains the search to local scope.
- `relationship_trace`: follow links or relationships between entities or facts.
- `obsidian_only`: hard source mode that queries only Obsidian-backed documents and fails closed when no Obsidian evidence exists.

## Routing Dimensions

- `default scope`
  - Where retrieval begins.
  - `conversation` means do not leave the active message history.
  - `local` means start with thread/project-local evidence.
  - `global` means the intent explicitly justifies broader search posture.
- `time mode`
  - Whether time should shape the retrieval partition.
  - `none` means ordinary relevance rules are enough.
  - `recent` means favor recency-bounded recall.
  - `chronological` means preserve ordered history.
- `graph allowance`
  - Whether graph context is disallowed, merely allowed as enrichment, or
    preferred as enrichment.
  - Graph remains optional and feature-flagged in the current runtime.
- `depth bias`
  - The default retrieval budget when the caller asks for `auto`.
  - This is a budget envelope, not an execution recipe.
- `escalation order`
  - The order in which broader evidence sources may be considered.
- `stop condition`
  - The point where the router should stop widening retrieval.

## Canonical Decision Table

| Intent | Retrieval Needed | Default Scope | Time Mode | Graph Allowance | Depth Bias | Escalation Order | Stop Condition |
|---|---|---|---|---|---|---|---|
| `conversation_only` | no | `conversation` | `none` | `disallow` | `shallow` | none | stop at the active conversation |
| `direct_qa` | yes | `local` | `none` | `disallow` | `normal` | `thread_messages -> thread_semantic -> project_docs -> adjacent_local` | stop on first sufficient local evidence |
| `memory_recall` | yes | `local` | `recent` | `disallow` | `deep` | `thread_messages -> memory -> thread_semantic -> project_docs` | stop once recall is supported |
| `timeline_recall` | yes | `local` | `chronological` | `disallow` | `deep` | `thread_messages -> memory -> thread_semantic -> project_docs` | stop once a coherent ordered timeline exists |
| `provenance` | yes | `local` | `none` | `prefer_enrichment` | `normal` | `thread_messages -> thread_semantic -> project_docs -> graph_enrichment -> adjacent_local` | stop once source or lineage can be explained |
| `exploratory` | yes | `local` | `none` | `allow_enrichment` | `deep` | `thread_messages -> thread_semantic -> project_docs -> memory -> adjacent_local -> global_search` | stop when evidence budget is exhausted |
| `explicit_global_search` | yes | `global` | `none` | `allow_enrichment` | `deep` | `thread_messages -> thread_semantic -> project_docs -> adjacent_local -> global_search` | stop after the explicit broadened pass |
| `scope_locked_local` | yes | `local` | `none` | `disallow` | `normal` | `thread_messages -> thread_semantic -> project_docs` | stop without adjacent or global expansion |
| `relationship_trace` | yes | `local` | `none` | `prefer_enrichment` | `deep` | `thread_messages -> thread_semantic -> graph_enrichment -> project_docs -> adjacent_local` | stop once the relationship path is explainable |
| `obsidian_only` | yes | `local` | `none` | `disallow` | `normal` | `thread_messages -> obsidian_documents` | stop once Obsidian-backed evidence is sufficient, or fail closed if no Obsidian hits exist |

## Design Rules

- Retrieval is optional.
  - Some turns should remain conversation-only.
  - The router decides whether retrieval is needed instead of assuming it.
- Scope starts narrow.
  - Start from the active conversation and local evidence before widening.
  - Broader search should be explicit or policy-driven, not accidental.
- Time is a partition, not just ranking.
  - Timeline queries are not ordinary QA with a recency boost.
  - When time matters, retrieval should preserve the time posture directly.
- Graph is enrichment, not default ceremony.
  - Optional graph context may help provenance and relationship tracing.
  - It should not be treated as a required first step for ordinary QA.
- Depth is a budget envelope, not a fixed recipe.
  - `shallow`, `normal`, and `deep` describe how much evidence the router may
    spend, not a hard-coded execution trace.

## Current Boundary

- This policy defines the canonical token set and routing doctrine.
- Runtime enforcement now consumes the same `source_mode` vocabulary, including the hard `obsidian_only` mode.
- This policy does not add UI controls.
- This policy does not introduce graph execution behavior.
- This policy exists so runtime adoption can import one canonical contract instead of growing inline heuristic tangles.
