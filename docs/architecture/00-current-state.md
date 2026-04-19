## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-04-19

## Interpretation rule
This file is authoritative for:
- release readiness
- supported install path
- active blockers
- current priorities
- what is and is not part of the present release promise

## Current phase
Codexify is in local-beta hardening on `main`. The supported path is still the local Docker Compose stack with a local-only provider policy, while recent merged work tightened startup ingestion and retrieval sharing. Quarantined surfaces remain outside the beta promise.

## What changed recently
- A backend-only candidate-trace diagnostic surface was added: `GET /chat/{thread_id}/debug/candidate-trace/latest`. It captures transient pre-answer candidate outputs for the latest completion attempt, remains thread-scoped, and is intentionally excluded from export/restore.
- A dedicated retrieval-posture diagnostics route was added to the backend: `GET /api/chat/debug/retrieval-posture/{thread_id}/latest`. It reuses the same latest-trace evidence path as the RAG trace route and returns the canonical posture snapshot or an empty state. A fallback synthesis path is included for legacy trace fields (source_mode, widen_reason, retrieval_override).
- A companion frontend surface was added via `useRetrievalPosture` hook and a `RetrievalPostureSection` in `TraceWorkbench.tsx`. It shows source mode, boundary label, retrieval override mode, widen reason, and conversation-only flag as compact badges with distinct loading, empty, and error states.
- A retrieval-posture history route was added: `GET /api/chat/{thread_id}/debug/retrieval-posture/history` for richer temporal access.
- A retrieval posture explainer was added to the Command Center, rendering human-readable explanations for each posture field value with copy-to-clipboard support.
- The retrieval-posture explainer UI surface was added to the Command Center with a standalone panel and per-thread posture history display.
- Executable backend-seam evaluation suites continue to provide coverage for: identity-boundary proof (project scope containment, explicit widening, exclusion filters), supported-path golden tasks (completion acceptance, RAG trace isolation, Obsidian ingest→retrieve seam), and broker/source-mode matrix reconciliation.
- Live runtime proof was attempted on `codex/add-retrieval-explainer` (branch 6 commits ahead of `main`). The retrieval-posture diagnostics route is confirmed live and returns correct empty-state shape. Chat completion proof is blocked by an Ollama model name mismatch (`LOCAL_CHAT_MODEL` set to "Gemma 4 E 4 B Hauhau" but Ollama instance has `gemma4-e4b-hauhau:latest`). Chroma retrieval remains healthy (`proof_capable: true`). **Fixed:** `LOCAL_CHAT_MODEL` updated to `gemma4-e4b-hauhau:latest` in `.env.example` (2026-04-14).

## Current supported reality
- Local Docker Compose remains the supported install path.
- Supported beta posture is still local-only: `LLM_PROVIDER=local`, `CODEXIFY_LOCAL_ONLY_MODE=true`, `ALLOW_CLOUD_PROVIDERS=false`.
- Chat acceptance, worker execution, and Postgres persistence remain the core validated loop.
- Upload -> parse -> embed -> retrieve remains supported, with one shared runtime vector store.
- Built-in system docs/help are seeded at startup and available to retrieval.
- The import embed worker can drain a live backlog without breaking chat or health surfaces.
- `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`, and `/api/llm/catalog?include=all` remain the primary runtime evidence surfaces.
- Executable evaluation suites now cover backend seam evidence for:
  - Supported-path golden tasks (completion acceptance, RAG trace isolation, Obsidian ingest→retrieve seam).
  - Identity-boundary proof (project scope containment, explicit widening, exclusion filters).
  - Broker/source-mode reconciliation (`effective_source_mode` derived from `source_mode` + `retrieval_override`).

## Identity and Runtime Mode

- Codexify now defines `single_user` and `multi_user` runtime modes.
- `multi_user` mode introduces strict `user_id` enforcement across:
  - API routes
  - retrieval
  - persistence
- exportability is now a first-class invariant.

## Not yet true / do not assume
- Do not assume the supported-path golden tasks or identity-boundary suites replace the need for fresh live release evidence on the exact current `main` tip; these are backend seam tests, not full live Compose runtime proof.
- Do not assume the Obsidian ingest→retrieve seam proof constitutes a full connector sync or live runtime validation; it uses an in-memory fixture at the backend route level.
- Do not assume `personal_facts` is part of the supported beta surface; the supported profile quarantines it.
- Do not assume delegation or autonomous coding-agent execution is shipped; the current release promise still excludes that loop.
- Do not assume internal operator surfaces or quarantined routes represent the supported beta contract.
- Do not assume older proof docs alone describe the current tip if a newer merge changed runtime wiring.

## Active blockers
- Chat completion blocked: `LOCAL_CHAT_MODEL` was set to "Gemma 4 E 4 B Hauhau" but the Ollama instance at `100.109.4.57:11434` has `gemma4-e4b-hauhau:latest`. Codexify requests fail with HTTP 400 "invalid model name". **Fixed 2026-04-14:** `LOCAL_CHAT_MODEL` updated to `gemma4-e4b-hauhau:latest` in `.env.example`. Live verification still required.
- Retrieval-posture populated state not yet demonstrated: The completion-service seam has not yet been updated to emit `payload_summary["retrieval_posture"]`. The diagnostics route is live and returns correct empty-state shape, but the fast path (reading canonical snapshot) is a dead letter until that seam is updated. The fallback synthesis path also returns empty because historical task.completed events lack the required legacy trace fields.
- Fresh live release evidence on the exact current `main` tip is still required before release signoff; the proof was run on `codex/add-retrieval-explainer` (6 commits ahead of `main`). Backend-seam eval suites reduce scope-boundary ambiguity but do not substitute for live runtime proof.
- Release signoff still depends on the supported-profile, provider registry, and health surfaces staying aligned.

## This week's priorities
1. ~~Resolve Ollama model name mismatch~~ — **Done 2026-04-14:** `LOCAL_CHAT_MODEL` in `.env.example` updated to `gemma4-e4b-hauhau:latest`. Live verification still required.
2. Update the completion-service seam (`guardian/core/chat_completion_service.py`) to emit `payload_summary["retrieval_posture"]` so the diagnostics route's fast path becomes functional.
3. Re-run the supported local Compose beta proof on `main` once the above are resolved; verify chat completion, retrieval-posture populated state, and all health surfaces pass.
4. Keep the supported-profile contract, catalog, and health surfaces aligned with the local-only provider posture.

## Release definition right now
- [ ] Supported-profile flags and mounted routes still match the beta contract.
- [ ] Fresh live evidence exists on the current `main` tip for clean start, assistant completion, upload -> embed -> retrieve, and health surfaces.
- [ ] Backend-seam eval suites (golden tasks, identity boundaries, source-mode matrix) are passing on the current `main` tip — this reduces scope-boundary ambiguity but does not replace the live proof requirement above.
- [ ] The release promise does not include `personal_facts` unless the supported profile is updated.
- [ ] Delegation is either explicitly excluded or implemented with a real executor plus source-thread result return.
- [ ] No internal-only or quarantined surface is part of the release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
