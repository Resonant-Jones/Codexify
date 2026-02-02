# Infra Finalization → Codex Prompt Pack

A modular prompt kit to drive Codexify Runtime (or equivalent agent) to execute the infra punch list with reproducible outputs, review gates, and fallbacks. Copy/paste sections as needed. Variables in `{{braces}}`.

---

## 0) Global Orchestrator System Prompt

**Role:** You are the Infra Orchestrator. Your job is to take high‑level intents and produce concrete plans, code changes, commands, and PRs. Work in small atomic steps. Never skip validation.

**Non‑negotiables:**

- Respect sovereignty-first design: local-first, offline capable, optional cloud.
    
- Keep mobile runtime constraints: embedders ≤ 3 GB; LLM ≤ 3 GB.
    
- Preserve files: `src/TagSelector.tsx`, `src/ThreadPromptBox.tsx`, `src/PersonaEngine.ts`.
    
- Persist generated artifacts by default.
    
- No destructive ops without backup.
    

**Cycle:** Plan → Diff → Apply → Test → Summarize → Commit/PR → Next step.

**Output blocks per step:**

1. **PLAN**: goal, substeps, assumptions, risks.
    
2. **DIFF**: unified diffs or new files with full content.
    
3. **RUN**: exact commands.
    
4. **TEST**: quick checks, unit/integ tests, manual steps.
    
5. **ACCEPT**: pass/fail and next action.
    

---

## 1) Project Context Loader (one‑time)

**Prompt:**

> Load repository context. Index file tree and key configs. Summarize build system, package manager, scripts, and any Docker/Procfile. Detect mobile vs desktop targets. Identify existing vector store, embeddings, and any API keys usage.
> 
> **Deliver:** a context report with: package manager, entrypoints, env vars, ports, current RAG bits, Guardian stubs, and where `PersonaEngine` is referenced.

**Acceptance:** context report saved to `docs/infra/context-report.md`.

---

## 2) Epic: Backend Orchestration

### 2.1 ThreadVault ↔ PulseOS ↔ Codexify Sync

**Intent Prompt:**

> Implement persistent state sync across ThreadVault, PulseOS, and Codexify.
> 
> **Requirements:**
> 
> - Event bus/socket channel with auth.
>     
> - Minimal schema for thread state, persona selection, and codex lookup results.
>     
> - Idempotent upserts. Retry/backoff.
>     
> - Local-first storage with a cloud proxy toggle.
>     
> 
> **Deliverables:**
> 
> - New module: `packages/pulse-os/sync/{client,server}.ts`.
>     
> - API contract doc: `docs/infra/sync-contract.md`.
>     
> - Integration wiring in app entrypoints.
>     

**Acceptance Tests:**

- Start local cluster, flip persona tag in UI, observe persisted state after app restart.
    
- Simulate network drop; ensure replay and eventual consistency.
    

### 2.2 PersonaEngine Runtime Hookup

**Intent Prompt:**

> Wire `PersonaEngine` so `TagSelector` and `ThreadPromptBox` read/write via the engine API.
> 
> **Deliverables:**
> 
> - `PersonaEngine` provider and React hooks.
>     
> - Refactor components to use provider, no breaking props.
>     
> - Unit tests for tag selection and prompt dispatch.
>     

**Acceptance:** tests in `__tests__/persona/*` pass; UI reflects engine state.

### 2.3 Guardian Layer (Shallow + Vector)

**Intent Prompt:**

> Insert Guardian ethics filter into query path with two-tier checks.
> 
> **Requirements:**
> 
> - Tier 1: keyword/tag check, fast allow/flag.
>     
> - Tier 2: vector similarity only on Tier 1 triggers.
>     
> - Config-driven rules in `configs/guardian/*.yaml`.
>     
> 
> **Deliverables:** middleware, config, and logs with allow/block/soft-redirect events.

**Acceptance:** e2e test simulating disallowed prompt returns redirect with rationale.

---

## 3) Epic: Embedding & RAG Pipeline

### 3.1 Vector Store Spin‑up

**Intent Prompt:**

> Stand up a vector store (local default, cloud proxy optional) and register it with PulseOS.
> 
> **Constraints:**
> 
> - Portable: SQLite/pg backed store acceptable; local-first by default.
>     
> - Embeddings model size respects mobile limits.
>     
> 
> **Deliverables:** connection module, env templates, health check.

**Acceptance:** health endpoint returns ready; CRUD roundtrip on sample docs.

### 3.2 Ingestion for Obsidian + OpenAI History Chunks

**Intent Prompt:**

> Build ingestion scripts to index Obsidian markdown and pre-chunked conversation JSON.
> 
> **Deliverables:**
> 
> - `tools/ingest/obsidian.ts` with frontmatter/tag handling.
>     
> - `tools/ingest/conversations.ts` with metadata mapping.
>     
> - Batch job and incremental watcher.
>     

**Acceptance:** `npm run ingest:all` indexes sample vault and reports stats.

### 3.3 Runtime Retrieval Wiring

**Intent Prompt:**

> Expose retrieval API in PulseOS and add resolver in Codexify for contextual prompts.
> 
> **Deliverables:** `/api/retrieve` endpoint, client, and caching.

**Acceptance:** prompt box suggestions include recent vault docs; latency budget < 150 ms local.

---

## 4) Epic: Frontend Scaffolding

**Intent Prompt:**

> Scaffold Codexify base UI with ambient/frosted theme and slot preserved components.
> 
> **Deliverables:**
> 
> - Layout shell, theme tokens, glass surfaces.
>     
> - Migrate `TagSelector.tsx` and `ThreadPromptBox.tsx` into new shell.
>     
> - Empty state screens and loading skeletons.
>     

**Acceptance:** storybook/docs, Lighthouse pass on basic views.

---

## 5) Epic: DevOps / Deployment

**Intent Prompt:**

> Establish local/remote parity and CI/CD hooks.
> 
> **Deliverables:**
> 
> - `devcontainers` or `docker-compose` for local.
>     
> - CI workflow: lint, test, build, package.
>     
> - Release script that produces versioned artifacts.
>     

**Acceptance:** green pipeline on main with cached deps; one-click local up.

---

## 6) Evaluator Prompts (Self‑Check)

Use these after each step.

**Static Check:**

> Review the DIFF for violations of the non-negotiables and mobile limits. If any, propose fixes.

**Runtime Check:**

> Run the TEST commands, capture logs, summarize failures, and suggest the minimal code change to pass.

**Security/Privacy Check:**

> Verify no credentials hard-coded; local-first default behavior; telemetry opt-in only.

---

## 7) Branching & PR Ritual

**Prompt:**

> Create short-lived branch `{{prefix}}/{{ticket}}-{{slug}}`. Commit atomic changes with useful messages. Open PR with checklist:
> 
> -  Acceptance tests pass locally
>     
> -  Docs updated
>     
> -  Guardian rules reviewed
>     
> -  Bundle size within limits
>     

PR must include: context, screenshots, logs, and next-step plan.

---

## 8) Fallbacks & Recovery

**If tests fail:** rollback to last green tag `v{{X.Y.Z}}`. Save failing state to `artifacts/failures/{{timestamp}}`.

**If retrieval too slow:** switch to smaller embedding or enable caching; update config and re-run tests.

---

## 9) One‑Shot Prompts (Copy/Paste)

- **Kickoff:**
    

> Use the Project Context Loader, then begin Epic 2.1. Produce PLAN, DIFF, RUN, TEST, ACCEPT. Stop after ACCEPT.

- **RAG Bring‑up:**
    

> Execute Epics 3.1 → 3.3 sequentially. After each, run Evaluator Prompts and only continue on ACCEPT.

- **Frontend Slot‑in:**
    

> Execute Epic 4 with priority on preserving component contracts. Output diffs and screenshots refs.

---

## 10) Definition of Done (Infra)

- Backend sync live and durable.
    
- PersonaEngine powering TagSelector and ThreadPromptBox.
    
- Guardian filter active with logs.
    
- Vector store running; ingestion jobs scheduled; retrieval wired.
    
- Base UI scaffolded; preserved files migrated.
    
- CI/CD green; local/remote parity proven.
    

Save this file as `docs/prompts/infra-codex-pack.md` in the repo.

---

## 11) Orchestrated Multi‑Step Runs (Parallel where safe)

When you don’t want to babysit one‑shots, use a manifest‑driven queue with dependency‑aware execution. The agent processes tasks in topological order, spawning parallel workers for independent steps.

### 11.1 Run Manifest (YAML)

```yaml
# docs/prompts/run-manifest.yml
version: 1
concurrency: 3        # max concurrent tasks
retry_limit: 2        # per task
rollback_on_fail: true

locks:
  - name: repo_write   # prevent concurrent write/diff collisions
  - name: port_apis    # prevent port binding races

artifacts_dir: artifacts/runs

stages:
  - id: context
    prompt: Project Context Loader
    needs: []

  - id: sync
    prompt: Epic 2.1 ThreadVault ↔ PulseOS ↔ Codexify Sync
    needs: [context]
    locks: [repo_write, port_apis]

  - id: persona_hook
    prompt: Epic 2.2 PersonaEngine Runtime Hookup
    needs: [sync]
    locks: [repo_write]

  - id: vector_store
    prompt: Epic 3.1 Vector Store Spin‑up
    needs: [context]
    locks: [port_apis]

  - id: ingest
    prompt: Epic 3.2 Ingestion for Obsidian + OpenAI History
    needs: [vector_store]
    locks: [repo_write]

  - id: retrieval
    prompt: Epic 3.3 Runtime Retrieval Wiring
    needs: [vector_store, ingest]
    locks: [repo_write, port_apis]

  - id: frontend
    prompt: Epic 4 Frontend Scaffolding
    needs: [persona_hook, retrieval]
    locks: [repo_write]

  - id: devops
    prompt: Epic 5 DevOps / Deployment
    needs: [frontend]
    locks: [repo_write, port_apis]
```

### 11.2 Batch Orchestrator Prompt

**Role:** Batch Orchestrator. Read `docs/prompts/run-manifest.yml`, resolve dependencies, and execute tasks with the standard PLAN → DIFF → RUN → TEST → ACCEPT cycle. Respect locks to avoid collisions. Run up to `concurrency`tasks in parallel when `needs` are satisfied and locks do not conflict.

**Behavior:**

1. Parse manifest. Build a DAG. Compute a topological schedule.
    
2. For each runnable task:
    
    - Create `artifacts/runs/{timestamp}/{task_id}/` and write PLAN, DIFF, RUN, TEST, ACCEPT logs.
        
    - Acquire required `locks` before DIFF/RUN; release on ACCEPT/FAIL.
        
    - If TEST fails, attempt up to `retry_limit` minimal diffs.
        
3. On failure with `rollback_on_fail: true`, revert to last green tag and stash failing state under `artifacts/failures/{timestamp}-{task_id}`.
    
4. Emit a final run summary with task statuses, durations, and next actions.
    

**Input:**

- `docs/prompts/infra-codex-pack.md` (this file) for the task prompts referenced by `prompt` keys.
    
- `docs/prompts/run-manifest.yml` for the DAG and settings.
    

**Output:**

- `artifacts/runs/{timestamp}/summary.md` including a Gantt‑like table and pass/fail grid.
    

### 11.3 Minimal Runner Script (optional)

If you prefer a harness, provide a small script that feeds the orchestrator prompt and captures logs.

```bash
# tools/run-batch.sh
set -euo pipefail
RUN_ID=$(date +%Y%m%d-%H%M%S)
ART=artifacts/runs/$RUN_ID
mkdir -p "$ART"
# Hand off to agent with Orchestrator Prompt and manifest path
# Save agent output to $ART/summary.md (integration depends on your agent runtime)
```

### 11.4 Safety & Idempotency Rules

- Tasks must be idempotent: re-running does not corrupt state.
    
- Never bind fixed ports without checking availability.
    
- Never commit secrets. Validate with Security/Privacy Check after each DIFF.
    
- All generated files live under version control or `artifacts/` with timestamps.
    

### 11.5 Example Parallelization

- `vector_store` can run alongside `sync` once `context` is ready.
    
- `ingest` waits for `vector_store`, but not for `persona_hook`.
    
- `frontend` only begins after both `persona_hook` and `retrieval` pass.
    

This turns the one‑shot prompts into a dependency‑aware batch that runs multiple steps concurrently where safe, with logs, retries, and rollbacks.



12) Preflight Prompt (Safe Launch)

Use this before any batch or one‑shot run to create a clean checkpoint, tag, branch, env, ports check, and artifacts folders. It also verifies preserved files and prompt pack paths.

12.1 One‑Shot: Preflight Orchestrator

Role: Preflight Orchestrator.

Goal: Prepare the repository for a safe automation run. Create a checkpoint commit and tag, switch to a work branch, ensure env scaffolding, verify required files, check port availability, record environment diagnostics, and produce a preflight report. Do not push to remote.

Inputs (defaults):

prebatch_tag: v0.0.1-prebatch

work_branch: chore/batch-run-001

env_file: .env

env_template: .env.example

ports: [3000, 5173, 8000, 5432]

artifacts_dir: artifacts

prompt_pack_path: docs/prompts/infra-codex-pack.md

manifest_path: docs/prompts/run-manifest.yml

preserve_files: [src/TagSelector.tsx, src/ThreadPromptBox.tsx, src/PersonaEngine.ts]

Cycle: PLAN → RUN → VALIDATE → ACCEPT

PLAN:

Detect package manager and versions (node, pnpm/npm/yarn, git, docker if installed).

Decide safe tag name: if {prebatch_tag} exists, append numeric suffix (-2, -3, ...).

Determine which of {ports} are busy and by what process.

RUN (exact actions):

git add -A then git commit -m "checkpoint before batch run" (skip if nothing to commit).

Create annotated tag {resolved_tag}.

Create or switch to branch {work_branch} from current HEAD.

If {env_file} missing and {env_template} exists, copy template to create it.

Create directories: {artifacts_dir}/runs and {artifacts_dir}/failures and {artifacts_dir}/preflight/{timestamp}.

Probe {ports} and capture listeners (use lsof -i :PORT if available; otherwise netstat/ss). Do not kill processes; only report.

Generate environment diagnostics: node -v, package manager version, git status --porcelain=v1 -b, git rev-parse --short HEAD, OS, CPU/RAM summary, disk free, docker --version if present.

Verify presence of {prompt_pack_path} and {manifest_path}; if missing, create stub files with TODO headers.

Verify preserve_files exist. If any missing, create placeholder stubs with TODO and mark as warning, not fatal.

Save all outputs to {artifacts_dir}/preflight/{timestamp}/report.md and include a copy of git diff --staged if a commit occurred.

VALIDATE (hard checks):

The tag {resolved_tag} exists and points to the preflight commit or current HEAD.

Current branch is {work_branch}.

{prompt_pack_path} and {manifest_path} exist and are readable.

git status is clean after the preflight commit.

Soft warnings (do not fail):

Any busy ports in {ports}.

Missing Docker binary.

Large untracked files not ignored.

ACCEPT:

Output a concise summary block with: resolved tag, branch, env file status, ports status, preserved files status, and paths to artifacts.

Write the same summary to {artifacts_dir}/preflight/{timestamp}/summary.md.

On FAIL:

Do not modify the tag or branch further. Emit a remediation checklist with the minimal steps to pass VALIDATE on next run.

Artifacts:

{artifacts_dir}/preflight/{timestamp}/report.md

{artifacts_dir}/preflight/{timestamp}/summary.md

{artifacts_dir}/preflight/{timestamp}/env-snapshot.txt (redact secrets by default)

Redaction Rules:

Never print full secret values from .env. Mask with **** after first 2 characters if shown.

12.2 Copy‑Paste Minimal Invocation

Run the Preflight Orchestrator with defaults. Produce PLAN, RUN, VALIDATE, ACCEPT. Stop after ACCEPT.

12.3 Optional: Extended Checks

If available tools exist, also run:

Lint: npm run lint or pnpm lint

Typecheck: npm run typecheck or pnpm typecheck

Vulnerability scan: npm audit --audit-level=high (non-fatal)

Git hooks presence: verify .husky/ or equivalent and list installed hooks.

12.4 Idempotency & Safety

Running Preflight multiple times must not corrupt state.

If the branch {work_branch} already exists with diverged history, create {work_branch}-{timestamp} and continue.

If the tag exists, auto-increment suffix and record the mapping in the report.
