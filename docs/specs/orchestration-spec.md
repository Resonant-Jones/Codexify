# Codexify Autonomous Work Orchestration Spec

## Working Name

**Codexify Orchestrator**

Alternative names:

* **Codexify Conductor**
* **TaskRun Engine**
* **ForgeRunner**
* **WorkMesh Orchestrator**
* **Execution Contract Runtime**

## Purpose

Codexify needs an autonomous work orchestration layer inspired by OpenAI Symphony’s architecture, but not dependent on Codex, Linear, Elixir, or any single model provider.

The goal is to convert structured project work into isolated implementation runs, where agents execute tasks, produce auditable artifacts, and submit work for human review.

The user should manage work, not supervise agent internals.

## Core Principle

> The task is the contract.
> The workspace is isolated.
> The agent is replaceable.
> The proof is mandatory.
> The human reviews artifacts, not streams.

## Non-Goals

This system should **not**:

* Depend exclusively on OpenAI Codex.
* Require Linear as the only task source.
* Require Elixir or BEAM as the runtime.
* Allow runaway autonomous loops without budget, permission, or scope controls.
* Treat agent output as trustworthy without tests, diffs, logs, and review gates.
* Collapse identity, persona, model provider, and execution authority into one layer.

## System Overview

Codexify Orchestrator watches one or more task sources, creates isolated workspaces for eligible tasks, dispatches provider-neutral coding agents, tracks execution, gathers proof artifacts, and returns the result to a review surface.

```text
Task Source
  -> Orchestrator
    -> Run Planner
      -> Workspace Manager
        -> Agent Runtime Adapter
          -> Execution Monitor
            -> Artifact Collector
              -> Review Gate
                -> Task Source / PR / Codexify UI
```

## Key Concepts

### 1. Task Source

A task source is any system that can provide actionable work items.

Supported or planned sources:

* Codexify internal task graph
* GitHub Issues
* GitHub Projects
* Linear
* Local markdown backlog
* Obsidian task notes
* Notion database
* Jira-style integrations later

Each task source must normalize into a `WorkItem`.

```ts
type WorkItem = {
  id: string;
  source: "codexify" | "github" | "linear" | "markdown" | "notion" | string;
  title: string;
  description: string;
  repository?: string;
  branch?: string;
  labels?: string[];
  priority?: "low" | "normal" | "high" | "urgent";
  status: "open" | "claimed" | "running" | "blocked" | "review" | "done" | "failed";
  acceptanceCriteria?: string[];
  metadata?: Record<string, unknown>;
};
```

### 2. Execution Contract

An execution contract defines how a task should be run.

This should be Codexify’s equivalent of Symphony’s `WORKFLOW.md`, but provider-neutral and compatible with the user’s existing **Execution Contract Template** and **Codexify Task Prompt** concepts.

Suggested file names:

* `EXECUTION.md`
* `.codexify/workflows/default.md`
* `.codexify/contracts/bugfix.md`
* `.codexify/contracts/feature.md`

Example shape:

```md
---
id: feature-implementation
name: Feature Implementation
agent_profile: engineer.default
provider_policy: balanced
workspace_strategy: isolated_per_task
max_runtime_minutes: 45
max_cost_usd: 3.00
requires_tests: true
requires_human_review: true
artifact_policy:
  diff: required
  test_output: required
  summary: required
  risk_notes: required
  walkthrough: optional
allowed_actions:
  - read_repo
  - write_workspace
  - run_tests
  - open_pr
  - comment_on_task
blocked_actions:
  - deploy_production
  - rotate_secrets
  - modify_billing
---

You are implementing the linked task in an isolated workspace.

Follow the acceptance criteria exactly.
Prefer minimal, reviewable changes.
Run the relevant tests.
If the task is underspecified, stop and mark the run blocked with specific questions.
Return a concise implementation summary, test evidence, and risk notes.
```

### 3. Agent Runtime Adapter

Agents must be replaceable.

The orchestrator should not care whether the implementation agent is:

* OpenAI Codex
* Claude Code
* Gemini CLI / Antigravity-style agent
* Cursor agent
* A local model via Ollama
* A Codexify-native local worker
* A future in-house agent runtime

Adapter interface:

```ts
type AgentRuntimeAdapter = {
  id: string;
  name: string;
  capabilities: AgentCapability[];
  startRun(input: AgentRunInput): Promise<AgentRunHandle>;
  getStatus(runId: string): Promise<AgentRunStatus>;
  cancelRun(runId: string): Promise<void>;
  collectArtifacts(runId: string): Promise<RunArtifacts>;
};
```

Required capabilities should be declared explicitly.

```ts
type AgentCapability =
  | "read_files"
  | "write_files"
  | "run_shell"
  | "run_tests"
  | "open_pull_request"
  | "comment_on_issue"
  | "summarize_diff"
  | "record_walkthrough";
```

### 4. Workspace Isolation

Each autonomous task run should execute in a controlled workspace.

Workspace strategies:

* `isolated_per_task`: one clean workspace per task.
* `isolated_per_attempt`: new workspace for every retry.
* `shared_branch`: shared workspace for related tasks, discouraged by default.
* `readonly_plan`: no write permissions, planning only.

A workspace should track:

```ts
type Workspace = {
  id: string;
  workItemId: string;
  repoPath: string;
  baseBranch: string;
  workingBranch: string;
  createdAt: string;
  status: "ready" | "dirty" | "archived" | "failed";
  isolationMode: "git_worktree" | "container" | "vm" | "sandbox";
};
```

Recommended MVP isolation:

* Git worktree per task.
* Optional Docker sandbox for risky commands.
* Hard timeout and cancellation.
* No access to global secrets by default.

### 5. Run Lifecycle

A run is a single attempt to complete a task.

```text
queued
  -> claimed
    -> workspace_created
      -> planning
        -> executing
          -> testing
            -> artifact_collection
              -> review_ready
                -> accepted | rejected | needs_revision | failed | cancelled
```

Run object:

```ts
type WorkRun = {
  id: string;
  workItemId: string;
  contractId: string;
  workspaceId: string;
  agentRuntimeId: string;
  model?: string;
  status: WorkRunStatus;
  startedAt?: string;
  completedAt?: string;
  costEstimateUsd?: number;
  actualCostUsd?: number;
  tokenUsage?: TokenUsage;
  attempts: number;
  artifacts?: RunArtifacts;
  failureReason?: string;
};
```

### 6. Proof Artifacts

Every completed run must produce proof.

Minimum required artifacts:

```ts
type RunArtifacts = {
  summary: string;
  diff?: string;
  changedFiles: string[];
  testCommands: string[];
  testResults: TestResult[];
  riskNotes: string[];
  openQuestions?: string[];
  pullRequestUrl?: string;
  taskCommentUrl?: string;
  logsRef?: string;
  complexityAnalysis?: ComplexityAnalysis;
  walkthroughVideoUrl?: string;
};
```

For Codexify, proof artifacts should also become memory/events in the project graph.

Example graph events:

* `agent.run.started`
* `workspace.created`
* `file.modified`
* `test.executed`
* `run.blocked`
* `run.review_ready`
* `human.accepted`
* `human.rejected`

### 7. Review Gate

No autonomous run should land changes without review unless explicitly authorized.

Review modes:

* `manual_required`: default.
* `auto_merge_if_green`: only for low-risk scoped tasks.
* `comment_only`: agent posts patch summary but does not open PR.
* `plan_only`: agent returns implementation plan.

A review gate should evaluate:

* Did tests run?
* Did acceptance criteria pass?
* Were files outside scope modified?
* Did the cost/runtime exceed limits?
* Did the agent disclose uncertainty?
* Are there risky migrations, secrets, network calls, or dependency changes?

### 8. Provider Policy

Provider routing should be separate from the orchestration contract.

Example:

```yaml
provider_policy: balanced
```

Possible policies:

* `cheapest_safe`
* `local_first`
* `fastest`
* `best_reasoning`
* `privacy_strict`
* `manual_selection`
* `balanced`

The policy resolves to a runtime adapter at execution time.

```text
provider_policy -> ModelRouter -> AgentRuntimeAdapter
```

This preserves independence from Codex.

### 9. Budget and Blast Radius Controls

Each run must have limits.

Required controls:

* Max runtime.
* Max cost.
* Max retry count.
* Max files changed.
* Allowed directories.
* Blocked directories.
* Allowed commands.
* Blocked commands.
* Secret access policy.
* Network access policy.

Example:

```yaml
limits:
  max_runtime_minutes: 45
  max_cost_usd: 3.00
  max_retries: 1
  max_files_changed: 12
  allowed_paths:
    - src/**
    - tests/**
  blocked_paths:
    - .env
    - secrets/**
    - billing/**
  network: restricted
  secrets: none
```

### 10. Codexify Identity Boundaries

Codexify should treat autonomous execution as an authority-bearing action, not just text generation.

Therefore:

* Personas may propose work.
* Personas may draft execution contracts.
* Personas may review results through their lens.
* Personas should not automatically gain filesystem or shell authority.
* Execution authority belongs to the runtime permission layer, not the persona identity layer.

Identity boundary rule:

> Persona identity can shape interpretation. It cannot silently expand execution authority.

### 11. Storage Model

Minimum tables or collections:

```text
work_items
execution_contracts
work_runs
workspaces
run_artifacts
agent_runtime_adapters
provider_policies
review_decisions
event_log
```

Suggested Postgres shape:

```sql
work_items(id, source, title, description, status, metadata, created_at, updated_at)
execution_contracts(id, name, version, body, config, created_at, updated_at)
work_runs(id, work_item_id, contract_id, workspace_id, agent_runtime_id, status, started_at, completed_at, metadata)
run_artifacts(id, run_id, type, uri, content, metadata, created_at)
review_decisions(id, run_id, reviewer_id, decision, notes, created_at)
event_log(id, entity_type, entity_id, event_type, payload, created_at)
```

### 12. MVP Scope

The MVP should avoid boiling the orchestration ocean.

Build only:

1. Local markdown or Codexify task source.
2. GitHub repository target.
3. Git worktree workspace isolation.
4. One provider adapter first.
5. Contract file parser.
6. Run status tracking.
7. Artifact collection: summary, diff, changed files, test output.
8. Manual review gate.
9. Codexify UI surface for run history.

Do **not** start with:

* Multi-agent swarms.
* Auto-merge.
* Video walkthroughs.
* Linear integration.
* Full sandboxing VM layer.
* Complex persona mediation.

### 13. Phase Plan

#### Phase 1: Local Orchestrator Skeleton

* Parse execution contract files.
* Load task from local Codexify task graph or markdown.
* Create git worktree.
* Dispatch agent adapter.
* Collect diff and logs.
* Mark task `review_ready`.

#### Phase 2: Provider-Neutral Runtime

* Implement `AgentRuntimeAdapter` interface.
* Add OpenAI/Codex adapter only as one option.
* Add Claude/Gemini/local placeholder adapters.
* Route via `provider_policy`.

#### Phase 3: Review UI

* Show run summary.
* Show changed files.
* Show diff.
* Show test output.
* Accept/reject/request revision.
* Save review event to project graph.

#### Phase 4: GitHub PR Integration

* Open PR from worktree branch.
* Post artifact summary.
* Link task to PR.
* Track CI status.

#### Phase 5: Hardened Autonomy

* Add command allowlist.
* Add cost/runtime enforcement.
* Add container sandbox option.
* Add retry policy.
* Add auto-merge only for scoped low-risk tasks.

### 14. Strategic Differentiation from Symphony

Codexify should diverge from Symphony in these ways:

| Symphony             | Codexify Orchestrator                          |
| -------------------- | ---------------------------------------------- |
| Codex-first          | Provider-neutral                               |
| Linear-first         | Task-source agnostic                           |
| Elixir reference     | Runtime-agnostic, likely TS/Go/Rust-friendly   |
| Engineering preview  | Productized local-first workflow               |
| Team work management | Individual + team sovereign work orchestration |
| OpenAI agent loop    | Codexify permissioned execution layer          |

### 15. Architectural Risks

#### Runaway Cost

Mitigation:

* Hard budget caps.
* Provider policy enforcement.
* Local-first option.
* Kill switch.

#### Weak Test Suites

Mitigation:

* Surface test coverage warning.
* Require explicit human review.
* Allow plan-only mode.

#### Workspace Contamination

Mitigation:

* Git worktree isolation.
* Dirty-state detection.
* Archive failed runs.

#### Provider Lock-In

Mitigation:

* Adapter layer from day one.
* No provider-specific concepts in core run schema.

#### Persona Authority Leakage

Mitigation:

* Separate persona prompts from execution permissions.
* Require explicit execution grants.

#### Dangerous Shell Commands

Mitigation:

* Command allowlist.
* Sandboxed execution.
* Human approval for high-risk commands.

### 16. Immediate Next Step

Create a minimal Codexify implementation spike:

```text
.codexify/
  contracts/
    default.md
  runs/
  orchestrator.config.json
```

Build a CLI command:

```bash
codexify run-task TASK_ID --contract default
```

Expected behavior:

1. Load task.
2. Load contract.
3. Create isolated worktree.
4. Dispatch selected agent runtime.
5. Collect diff and test logs.
6. Write run artifact bundle.
7. Mark task ready for review.

### 17. Design Mantra

Codexify should not become dependent on Codex to do autonomous implementation.

Codex is one possible performer.
The orchestrator is the stage.
The contract is the score.
The review gate is the conductor’s baton.
The user owns the theater.
