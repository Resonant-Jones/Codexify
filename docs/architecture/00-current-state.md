## Purpose
This file is Codexify's canonical short-form source of truth for current operational and release state. If it conflicts with older architecture, planning, or roadmap language on short-horizon reality, this file wins.

## Last updated
2026-04-29

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
- Verified active personal facts now flow through the backend chat context path and into the provider-ready prompt block as a bounded, user-scoped identity-context source; candidate, disputed, and inactive facts are excluded before prompt assembly.
- A backend-only candidate-trace diagnostic surface was added: `GET /chat/{thread_id}/debug/candidate-trace/latest`. It captures transient pre-answer candidate outputs for the latest completion attempt, remains thread-scoped, and is intentionally excluded from export/restore.
- A dedicated retrieval-posture diagnostics route was added to the backend: `GET /api/chat/debug/retrieval-posture/{thread_id}/latest`. It reuses the same latest-trace evidence path as the RAG trace route and returns the canonical posture snapshot or an empty state. A fallback synthesis path is included for legacy trace fields (source_mode, widen_reason, retrieval_override).
- The completion-service seam now emits a canonical `retrieval_posture` snapshot during chat completion, so the retrieval-posture route can read the live snapshot directly instead of depending on fallback synthesis when completion has run.
- The command-bus route family now includes a read-only activation inspection surface at `GET /api/guardian/commands/activation/inspect`, which returns the existing capability-activation decision and dispatch-envelope shape without invoking command execution.
- `retrievalSource="workspace"` is now a live backend completion seam for user-bounded local knowledge, including Obsidian-backed notes, without turning retrieval into a global search posture or a separate connector subsystem.
- A companion frontend surface was added via `useRetrievalPosture` hook and a `RetrievalPostureSection` in `TraceWorkbench.tsx`. It shows source mode, boundary label, retrieval override mode, widen reason, and conversation-only flag as compact badges with distinct loading, empty, and error states.
- A post-completion eval spine now exists in backend code: assistant completions can persist a durable trace snapshot and attempt-scoped groundedness verdicts in Postgres, with a diagnostics route at `GET /api/chat/debug/evals/{thread_id}/latest`. It is inspection-only and does not gate chat acceptance.
- The RAG trace payload summary now carries graph-ready diagnostics placeholders (`graph_hit_count`, `graph_enrichment_status`) that report `not_used_yet` on current supported runs; graph remains enrichment-only and is not part of active retrieval here.
- The retrieval broker now enforces strict `user_id` isolation at the aggregation boundary and requires widening to carry an explicit `widen_reason`; `widen_reason` normalizes to `none` when no widening occurs.
- The completion worker now emits a canonical retrieval-posture snapshot that can distinguish `conversation`, `project`, `personal_knowledge`, `obsidian_only`, and `workspace` source modes.
- A retrieval-posture history route was added: `GET /api/chat/{thread_id}/debug/retrieval-posture/history` for richer temporal access.
- A retrieval posture explainer was added to the Command Center, rendering human-readable explanations for each posture field value with copy-to-clipboard support.
- The retrieval-posture explainer UI surface was added to the Command Center with a standalone panel and per-thread posture history display.
- Executable backend-seam evaluation suites continue to provide coverage for: identity-boundary proof (project scope containment, explicit widening, exclusion filters), supported-path golden tasks (completion acceptance, RAG trace isolation, Obsidian ingest→retrieve seam), and broker/source-mode matrix reconciliation.
- Fresh live proof was re-run on the exact current `main` tip. Chat completion still works and the chat ownership seam normalizes a browser display label to `local`, and the supported local Compose migrator now reaches the merged extension/eval head cleanly so the expected `agent_extension_*` tables are present again. The live backend container still needs a separate supported-profile recheck, and the bounded tool-loop cases still regress instead of matching the claimed supported-path behavior.

## Current supported reality
- Local Docker Compose remains the supported install path.
- Supported beta posture is intended to be local-only, but the live backend container currently reports `CODEXIFY_BETA_CORE_ONLY=false`, `CODEXIFY_LOCAL_ONLY_MODE=false`, and `ALLOW_CLOUD_PROVIDERS=true`, so the running stack is not in the supported posture.
- Chat acceptance, worker execution, and Postgres persistence still work for plain chat completion on the current live runtime.
- Single-user ownership on the chat path normalizes browser display labels to `local`; that seam did not leak the display label into persisted thread ownership in this run.
- Upload -> parse -> embed -> retrieve is not currently proven on the live runtime. The earlier `agent_extension_*` schema gap that blocked document upload on the supported path is repaired on the supported local Compose stack, but the full end-to-end upload -> embed -> retrieve proof still needs a fresh rerun on the current tip.
- The bounded tool-loop slice is not currently behaving as claimed on the live runtime: the one-turn case fails with `tool_command_execution_failed`, and the hard-stop / blocked-result prompts collapse into plain answers instead of staying bounded.
- Retrieval assembly now keeps user boundaries explicit in the broker and records widening reasons so trace output stays truthful.
- Built-in system docs/help are seeded at startup and available to retrieval.
- The import embed worker can drain a live backlog without breaking chat or health surfaces.
- `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`, and `/api/llm/catalog?include=all` remain the primary runtime evidence surfaces, but this runtime now shows a supported-profile/catalog mismatch that must be resolved before any release claim.
- Executable evaluation suites now cover backend seam evidence for:
  - Supported-path golden tasks (completion acceptance, RAG trace isolation, Obsidian ingest→retrieve seam).
  - Identity-boundary proof (project scope containment, explicit widening, exclusion filters).
  - Broker/source-mode reconciliation (`effective_source_mode` derived from `source_mode` + `retrieval_override`).
  - Workspace-local retrieval posture, including live completion evidence for Obsidian-backed notes.

## Identity and Runtime Mode

- Codexify now defines `single_user` and `multi_user` runtime modes.
- `multi_user` mode introduces strict `user_id` enforcement across:
  - API routes
  - retrieval
  - persistence
- Retrieval now enforces strict user isolation and explicit widening semantics at the broker boundary.
- exportability is now a first-class invariant.

## Not yet true / do not assume
- Do not assume the supported-path golden tasks or identity-boundary suites replace the need for fresh live release evidence on the exact current `main` tip; these are backend seam tests, not full live Compose runtime proof.
- Do not assume the bounded tool-augmented completion proof closes the broader release gate by itself; it proves the tool-loop slice only, not the full release evidence pack.
- Do not assume the Obsidian ingest→retrieve seam proof constitutes a full connector sync or live runtime validation; it uses an in-memory fixture at the backend route level.
- Do not assume the verified-personal-facts seam implies a UI fact-management surface or broader retrieval mode; this task only adds backend identity-context injection.
- Do not assume delegation or autonomous coding-agent execution is shipped; the current release promise still excludes that loop.
- Do not assume internal operator surfaces or quarantined routes represent the supported beta contract.
- Do not assume older proof docs alone describe the current tip if a newer merge changed runtime wiring.

## Active blockers
- Live backend posture mismatch: the running backend container reports `CODEXIFY_BETA_CORE_ONLY=false`, `CODEXIFY_LOCAL_ONLY_MODE=false`, and `ALLOW_CLOUD_PROVIDERS=true`, while the catalog still exposes cloud inventory such as `groq` as enabled. Supported-path signoff is not satisfied until the live runtime is brought back into the local-only supported profile.
- Fresh live release evidence on the exact current `main` tip is still required before release signoff for the full beta evidence pack; this run now proves chat acceptance, chat ownership normalization, and migration/schema consistency on the supported Compose stack, but upload -> embed -> retrieve and bounded tool-loop behavior still need fresh live proof.
- Release signoff still depends on the supported-profile, provider registry, and health surfaces staying aligned.

## This week's priorities
1. ~~Resolve Ollama model name mismatch~~ — **Done 2026-04-14:** `LOCAL_CHAT_MODEL` in `.env.example` updated to `gemma4-e4b-hauhau:latest`. Live verification still required.
2. Re-run live `upload -> embed -> retrieve` proof on the current tip now that the `agent_extension_*` schema gap is repaired on the supported path.
3. Bring the live backend back into the supported local-only posture so the running stack matches the beta contract again.
4. Repair the bounded tool-loop path that currently fails with `tool_command_execution_failed` and does not preserve the claimed hard-stop / blocked-result behavior.
5. Re-run the supported local Compose beta proof on `main` once the above are resolved; verify chat completion, retrieval-posture populated state, and all health surfaces pass.

## Release definition right now
- [ ] Supported-profile flags and mounted routes still match the beta contract.
- [ ] Fresh live evidence exists on the current `main` tip for clean start, assistant completion, retrieval-posture populated state, upload -> embed -> retrieve, and health surfaces.
- [ ] Backend-seam eval suites (golden tasks, identity boundaries, source-mode matrix) are passing on the current `main` tip — this reduces scope-boundary ambiguity but does not replace the live proof requirement above.
- [ ] The release promise does not include a UI fact-management surface or any broader personal-facts retrieval doctrine unless the supported profile is updated.
- [ ] Delegation is either explicitly excluded or implemented with a real executor plus source-thread result return.
- [ ] No internal-only or quarantined surface is part of the release claim.

## How to read the rest of the KB
- `system-overview.md` explains structure, not release readiness.
- `flows.md` explains runtime behavior.
- `data-and-storage.md` explains persistence/invariants.
- `config-and-ops.md` explains operator/runtime truth.
- `roadmap-signals.md` is planning guidance, not live status.
- `tech-debt-and-risks.md` is a risk register, not the active blocker list unless repeated here.
