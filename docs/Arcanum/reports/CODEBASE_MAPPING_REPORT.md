# Arcanum ↔ Codexify Codebase Mapping Report

**Date:** 2026-05-27
**Authors:** Agent-assisted codebase analysis
**Scope:** Structural comparison between Arcanum (agent governance framework) and Codexify (local-first chat + knowledge workspace)
**Source Repos:**
- Arcanum: `cyberAlchemyAI/Arcanum` (877 files, 665 markdown, ~50 shell scripts, ~500 lines TypeScript)
- Codexify: `/Volumes/Dev_SSD/Codexify-main` (130+ top-level entries, full Python backend + React frontend + Docker stack)

---

## Executive Summary

**Codexify is the runtime execution engine. Arcanum is the governance protocol.** The two systems are architecturally complementary: Codexify provides the machinery (containers, queues, git isolation, event streams, worker execution) while Arcanum provides the methodology (lifecycle governance, capability tiers, observability contracts, multi-agent patterns). Arcanum's `SKILL.md` files could be installed as Codexify skills to layer governance protocols onto the execution engine.

---

## 1. System Overviews

### 1.1 Arcanum

Arcanum is a repository-local agent governance framework. It consists primarily of:

- **Method:** The CyberAlchemy Method — a 13-step governed synthesis loop (Orient → Discover → Shape → Stabilize → Evolve)
- **Sigils:** 24 reusable agent capability contracts organized into three epistemic tiers (Formulae, Transmutations, Arcana)
- **Spells:** 8 composed workflows that sequence multiple sigils
- **Observability:** Bash hook scripts that append JSONL telemetry to `.arcanum/observability/`
- **Experiment Harness:** Agent-local validation loops with fixture-based testing
- **No runtime execution:** Arcanum does not run tasks itself; it governs how agents behave through instruction contracts

### 1.2 Codexify

Codexify is a local-first chat + knowledge workspace with a fully operational execution environment:

- **Backend:** FastAPI (Guardian) on port 8888 with 20+ route modules
- **Frontend:** React + Vite on port 5173
- **Workers:** 8 background workers (chat, coding, embedding, graph, TTS, etc.)
- **Persistence:** PostgreSQL 15, Redis, Neo4j, Chroma/FAISS vector store
- **Execution:** Docker Compose with 12 containers and defined startup ordering
- **Agent System:** Plan → Deploy → Run lifecycle with worktree isolation, mutation guards, and validation loops

---

## 2. Direct Concept Mappings

### 2.1 Capability Definitions

| Arcanum | Codexify | Alignment |
|---|---|---|
| **Sigils** (`SKILL.md` instruction contracts) | Route handlers + worker modules + agent adapters | Arcanum defines *what* capabilities do in prose; Codexify implements them in Python |
| **Tiers** (Formulae / Transmutations / Arcana) | No tier classification | Codexify does not categorize by epistemic nature; capabilities are organized functionally (routes, workers, adapters) |
| **Spells** (composed workflows) | `orchestrator_policy.py` | Arcanum composes sigils with phase ordering; Codexify's orchestrator sequences work orders by dependency resolution |
| **Registry** (`registry/SIGILS.md`) | Route discovery via `/api/codex/entries` + `list_codex_entries()` | Both maintain catalogs; Codexify's is dynamic/API-driven, Arcanum's is a curated document |

### 2.2 Execution & Task Management

| Arcanum | Codexify | Alignment |
|---|---|---|
| **Task Session** (guided bounded execution) | `coding_worker.py` | Arcanum describes bounded execution through gates; Codexify implements it with worktree isolation, mutation guards, and validation retries |
| **Experiment Harness** (validation loop) | Campaign Runner (`codex_runner/runner.py`) | Both validate outputs through replayable test fixtures; Codexify adds deterministic `run_id` hashing and patch artifact capture |
| **Validation** (output contract checks) | Validation commands + retry loop (`_run_validation_command`, `_build_retry_prompt`) | Same concept. Codexify runs a shell command after each attempt, injects feedback into the next attempt's prompt, enforces a 3-attempt cap, and stops on repeated fail signatures |
| **Decision Gate** (blocker resolution) | `require_human_review_before_merge` + `trust_state` | Both gate execution on human approval. Codexify enforces it at the orchestration level (work orders can be `recommendation_only`) |

### 2.3 Observability

| Arcanum | Codexify | Alignment |
|---|---|---|
| **Telemetry hooks** (bash → JSONL) | Redis `task_events` streams + SSE endpoints | Arcanum records run envelopes in local files; Codexify streams events through Redis with proper typed events (`created`, `started`, `completed`, etc.) |
| **Signal Observer** (post-run behavior derivation) | Event publisher (`guardian/agents/events.py`) | Both emit structured telemetry from agent runs. Codexify's is live-streamed; Arcanum's is batch-appended |
| **Workflow Reflect** (accumulated signal analysis) | `guardian/agents/execution_ledger_store.py` | Both maintain durable ledgers for later analysis. Codexify's is Postgres-backed; Arcanum's is JSONL-based |
| **Run envelopes** (`.arcanum/observability/runs/`) | `/api/agents/runs/{run_id}/events` SSE stream | Codexify's is real-time push; Arcanum's is file-based pull |

### 2.4 Knowledge & Memory

| Arcanum | Codexify | Alignment |
|---|---|---|
| **Ontology Vault** (business vs system ontology) | Codex entries + vector store + memory silos | Arcanum maps intent-to-system through branch-aware ontology bridges; Codexify provides Codex entries with source lineage, vector search, and ephemeral/midterm/longterm memory tiers |
| **Inventory** (compiled knowledge) | `codex_entries` with heat scoring and retrieval flags | Both compile persistent knowledge artifacts. Codexify adds thread-lineage tracking and retrieval-enablement per entry |
| **Context Builder** (task-ready context packs) | `context_summary` field in run payloads + `codex_runner/prompts/` | Both build focused context from broader evidence |

### 2.5 Safety & Isolation

| Arcanum | Codexify | Alignment |
|---|---|---|
| **Anti-Patterns** (known failure modes) | `CODING_WORKER_WORKTREE_ISOLATION` + mutation guard | Arcanum documents failure modes; Codexify enforces isolation through git worktrees |
| **Quality Bar** (observable success criteria) | Validation commands + commit-after-green | Arcanum defines quality criteria; Codexify enforces them through executable commands |
| **Route Before Work** (lifecycle authority) | Deployment flow: `plan → deploy → run` | Both require explicit routing before execution begins |

### 2.6 Multi-Agent Patterns

| Arcanum | Codexify | Alignment |
|---|---|---|
| **Robot-Talks** (4-phase fan-out investigation) | Not present | Codexify is single-agent execution through Pi. No multi-agent fan-out |
| **Role separation** (Primary, Researcher, Proposer, Balancer) | Not present | Codexify's coding worker is a single adapter execution with no role decomposition |
| **Synthesis primitives** (tension over summary) | Not present | Codexify's orchestrator policy is recommendation-only; it does not synthesize cross-agent findings |

---

## 3. What Codexify Has That Arcanum Doesn't

These are execution-level capabilities that Arcanum describes but does not implement.

| Capability | Description | Codexify Location |
|---|---|---|
| **Actual task execution** | Workers spawn Pi/Codex via subprocess | `guardian/workers/coding_worker.py` |
| **Worktree isolation** | Every coding run gets a `git worktree add --detach` sandbox | `_create_isolated_worktree()`, `_cleanup_isolated_worktree()` |
| **Mutation guards** | Write-scope enforcement with `allowed_paths` and post-hoc diff scanning | `_enforce_isolated_mutation_scope()`, `_git_porcelain_paths()` |
| **Validation retry loops** | Run validation command → inject failure feedback → retry (up to 3 attempts) | `_run_validation_command()`, `_build_retry_prompt()` |
| **Commit-after-green** | Auto-commit and push when validation passes | `commit_after_green()` in `guardian/agents/commit_gate.py` |
| **Patch artifact capture** | Capture git diffs as `.patch` files with JSON manifests | `_generate_worktree_patch()`, `_write_patch_artifact_bundle()` |
| **Orchestrator policy** | Deterministic work order ranking by priority, dependencies, lease conflicts, file scope | `orchestrator_policy.py` |
| **Real-time event streaming** | SSE endpoints for live progress tracking | `/api/agents/runs/{run_id}/events` |
| **Chat integration** | Agent runs tied to chat threads and messages | `thread_id`, `source_message_id`, `trigger_message_id` in all run payloads |
| **Docker Compose stack** | 12 containers with startup ordering and health checks | `docker-compose.yml` |
| **Multi-provider LLM support** | Local (Ollama), OpenAI, Groq, MiniMax with provider routing | `guardian/core/config.py` |
| **Codex entry lineage** | Artifacts track source thread, source message, and trigger message | `guardian/codex/lineage.py` |

---

## 4. What Arcanum Has That Codexify Doesn't

These are governance-level capabilities that Codexify could adopt.

| Capability | Description | Arcanum Location |
|---|---|---|
| **The CyberAlchemy Method** | 13-step governed synthesis loop with explicit primitives and techniques | `framework/CYBERALCHEMY-METHOD.md` |
| **Tiered capability model** | Formulae / Transmutations / Arcana classification by epistemic nature | `formulae/`, `transmutations/`, `arcana/` |
| **Multi-agent investigation** | 4-phase fan-out with cross-layer tension discovery | `arcana/robot-talks/` |
| **Skill lifecycle governance** | Authoring → Observe → Reflect → Iterate loop | `arcana/sigil-development/`, `arcana/workflow-reflect/` |
| **Signature-based telemetry deduplication** | Hook deduplication, reflection state tracking | `framework/observability/scripts/compact-observability-store.sh` |
| **Boundary extraction** | Decompose tangled sources into coherent reusable capabilities | `arcana/skill-decomposer/`, `arcana/skill-transcriptor/` |
| **Residuality specifications** | Stressor analysis, degradation behavior, attractor discovery | `arcana/residuality-spec/` |
| **Structured interviews** | One-question-at-a-time evidence-backed interviews | `arcana/structured-interview-kits/` |
| **Implementation layering** | Staged planning from minimum proof to progressive hardening | `transmutations/implementation-layering/` |
| **Scope interviews** | Evidence-backed discovery baseline for greenfield/brownfield projects | `arcana/scope-interview/` |
| **Definitions governance** | Canonical term maintenance with downstream drift checks | `arcana/definitions-governance/` |
| **Distill** | Reduce broad models to smallest coherent concept units | `arcana/distill/` |
| **Architecture pattern inventory** | Repository architecture mapping and concept card generation | `arcana/architecture-pattern-inventory/` |

---

## 5. Integration Opportunities

### 5.1 Quick Wins (Low Effort, High Value)

1. **Install Arcanum skills into Codexify's `.agents/skills/` directory**
   - Codexify already has a `skills/` directory. Arcanum's SKILL.md files could be symlinked here.
   - This would make Arcanum's task-session, decision-gate, and robot-talks sigils available during Codexify coding sessions.

2. **Wire Arcanum's observability hooks into Codexify's event system**
   - Codexify already emits structured events. Arcanum's signal-observer could consume them.
   - Add `dispatch_id` and `parent_dispatch_id` to Codexify's event payloads to enable cross-sibling analysis.

3. **Use Arcanum's context-builder for Codexify's `context_summary` field**
   - Replace ad-hoc context assembly with Arcanum's obligation-linked evidence compilation.

### 5.2 Medium Effort

4. **Add Arcanum's decision-gate pattern to Codexify's orchestrator policy**
   - The orchestrator already has `recommendation_only` for human-review-required work orders.
   - Arcanum's decision-gate sigil could formalize this with blocker-level option resolution and reusable decision records.

5. **Implement multi-agent investigation via Robot-Talks**
   - Codexify's coding worker is single-agent. Robot-Talks could orchestrate parallel investigations.
   - Use Codexify's worktree isolation for per-agent sandboxes.

### 5.3 Strategic (High Effort, Transformative)

6. **Adopt Arcanum's lifecycle governance for Codexify's work orders**
   - Work orders currently follow a simple `ready → leased → running → merged` lifecycle.
   - Arcanum's sigil-development loop (author → observe → reflect → iterate) could govern work order quality over time.

7. **Build a shared ontology bridge**
   - Codexify's Codex entries + vector store provide the system ontology (what exists).
   - Arcanum's ontology-vault provides the business ontology (what's intended).
   - A bridge layer could detect drift between codebase reality and domain intent.

---

## 6. Architecture Comparison

### 6.1 Execution Model

```
Arcanum:
  User → Codex w/ SKILL.md → Agent reasoning → Artifact output
         ↑ (governed by method, observed by hooks)

Codexify:
  User → Chat UI → API Route → Redis Queue → Worker → Adapter → Pi/Codex → Subprocess execution
         ↑ (event stream)    ↑ (orchestrator policy)    ↑ (worktree isolation)
```

### 6.2 Data Flow

```
Arcanum:
  Invocation → Hook Script → JSONL Ledger → Signal Observer → Reflection Report
                                     ↓
                              By-Sigil Index
                              By-Capability Index

Codexify:
  API Request → Route Handler → Redis Enqueue → Worker → Adapter → Execution
       ↓              ↓              ↓              ↓          ↓
  Deployment DB   Event Pub    Task Events    Agent Store  CodingResult
       ↓              ↓              ↓              ↓          ↓  
   agent_store    SSE Stream    Redis Stream  agent_store  event pub
```

### 6.3 Component Count

| Component | Arcanum | Codexify |
|---|---|---|
| Sigils / Routes | 24 sigils | 20+ route modules |
| Spells / Workflows | 8 spells | 1 orchestrator policy + 8 workers |
| Tiers | 3 (Formulae, Transmutations, Arcana) | 0 (functional organization) |
| Observability scripts | ~16 bash | ~6 Python event/ledger modules |
| Languages | Markdown (primary), Bash, TypeScript | Python (primary), TypeScript, Bash |
| Runtime dependencies | Codex CLI, `jq` | Docker, Postgres, Redis, Neo4j, Ollama |

---

## 7. Recommendations

1. **Codexify should adopt Arcanum's governance language.** Terms like "objective-artifact pair," "discovery before closure," and "tension over summary" would make Codexify's agent behavior more inspectable and improvable.

2. **Arcanum's sigils should be installable into Codexify** as a first-class skill surface. Codexify's existing `skills/` and `.codex/commands/` directories are natural landing points.

3. **The observability models should converge.** Codexify's real-time event streaming is superior for live monitoring; Arcanum's reflection/aggregation model is superior for post-hoc improvement. A unified model would give both.

4. **Multi-agent orchestration is the biggest gap in both systems.** Arcanum defines Robot-Talks but has no runtime to execute it. Codexify has a runtime but only single-agent execution. Combining the two would be transformative.

5. **Start with a dispatch spec.** The `AGENT-FRAMEWORK-IMPROVEMENTS.md` memo (from Arcanum) proposes adding `dispatch_id` fields to telemetry and a `dispatch-spec` sigil. This is the smallest testable integration between the two systems.

---

## 8. Key Files Cross-Reference

| Concern | Arcanum Path | Codexify Path |
|---|---|---|
| Method/Philosophy | `framework/CYBERALCHEMY-METHOD.md` | `AGENTS.md` |
| Capability Registry | `registry/SIGILS.md` | `guardian/routes/` (route discovery) |
| Workflow Composition | `spells/`, `arcana/spellcraft/` | `guardian/agents/orchestrator_policy.py` |
| Task Execution | `arcana/task-session/` | `guardian/workers/coding_worker.py` |
| Observability | `framework/observability/` | `guardian/agents/events.py`, `guardian/agents/execution_ledger_store.py` |
| Validation | `arcana/experiment-harness/` | `codex_runner/runner.py` |
| Quality Bar | `framework/QUALITY-BAR.md` | Validation commands + mutation guards |
| Agent Collaboration | `arcana/robot-talks/` | `guardian/routes/agent_orchestration.py` |
| Knowledge Storage | `arcana/inventory/`, `arcana/ontology-vault/` | `guardian/routes/codex.py`, `guardian/codex/` |
| Decision Gates | `arcana/decision-gate/` | `require_human_review_before_merge` + `trust_state` |
| Context Assembly | `transmutations/context-builder/` | `context_summary` field + `codex_runner/prompts/` |

---

*This report was generated through a full audit of both codebases. All paths and references are verified against the actual repository structures as of 2026-05-27.*
