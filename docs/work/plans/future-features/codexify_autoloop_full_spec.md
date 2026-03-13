# Codexify Autoloop Full Specification

## Document Status
- **System:** Codexify Autoloop
- **Purpose:** General-purpose bounded autonomous execution, optimization, and automation loop for user-defined goals
- **Spec Level:** Full system map
- **Use of this document:** Canonical architecture reference covering both MVP and production-grade targets within one frame

---

## 1. Executive Summary

Codexify Autoloop is a goal-directed execution and improvement system that compiles a user’s intent into a bounded, observable, policy-constrained search loop over plans, tools, prompts, workflows, and action sequences.

It is designed to let Codexify automate useful work across domains such as research, coding, communication, planning, document handling, browsing, and user-defined workflows, while preserving:

- user sovereignty
- identity boundaries
- bounded blast radius
- full traceability
- reversible execution where possible
- promotion of repeated success into reusable automations

Autoloop is not merely an agent runner. It is a structured runtime for:

1. compiling intent into a formal execution contract,
2. generating candidate plans,
3. executing bounded attempts,
4. evaluating outcomes against explicit success criteria,
5. learning from prior attempts,
6. promoting successful strategies into persistent workflows.

The core principle is simple:

> A user goal becomes a measurable search problem over executable strategies under governance constraints.

This spec is intentionally broad enough to measure both a narrow first release and a hardened production system. The same architecture should describe both.

---

## 2. Design Thesis

### 2.1 Problem Statement
Traditional assistant systems often fail at automation because they:

- operate with vague goals,
- lack explicit evaluators,
- have poor memory of failed attempts,
- do not model cost and risk cleanly,
- cannot distinguish reversible from irreversible actions,
- cannot reliably improve over repeated executions.

Codexify Autoloop addresses this by treating automation as a bounded optimization problem.

### 2.2 Core Thesis
A useful automation system must separate:

- **intent** from execution,
- **search** from action,
- **evaluation** from narration,
- **governance** from convenience,
- **persistent learning** from ephemeral chat.

### 2.3 System Goal
Enable Codexify to autonomously pursue user goals by searching over executable strategies, while preserving human approval over sensitive actions and recording a durable trace of how outcomes were achieved.

---

## 3. Definitions

### 3.1 Key Terms

**Goal**  
A user-stated desired outcome expressed in natural language and compiled into a structured contract.

**Execution Contract**  
A typed representation of the goal, constraints, success criteria, budgets, permissions, observability settings, and evaluation rules.

**Plan**  
A structured candidate strategy for achieving the goal, typically represented as a graph or ordered task list.

**Attempt**  
A single bounded execution of one candidate plan.

**Evaluator**  
A scoring component that measures how well an attempt satisfies the contract.

**Mutation**  
A controlled change to a plan, prompt, tool choice, order of operations, routing decision, or parameter.

**Loop**  
The iterative cycle of propose, execute, observe, score, retain or reject, and retry.

**Promotion**  
The conversion of repeated successful behavior into a durable reusable workflow, automation, template, or policy-backed routine.

**Blast Radius**  
The scope of side effects an attempt is permitted to cause.

**Approval Gate**  
A checkpoint requiring explicit user authorization before performing certain actions.

**Ledger**  
The durable log of attempts, traces, metrics, approvals, failures, costs, and artifacts.

---

## 4. Product Scope

### 4.1 In Scope
Autoloop should eventually support:

- research workflows
- research synthesis and reporting
- document transformations and packaging
- coding tasks and repo-local edits
- test-run-refine cycles
- email triage and drafting
- browser workflows
- knowledge organization
- planning and scheduling support
- recurring automation routines
- user-authored goal loops
- cross-tool workflows spanning local and cloud systems
- promotion of successful loops into saved automations

### 4.2 Out of Scope
This system should not:

- silently perform high-risk irreversible actions without approval
- infer durable identity traits without consent
- mutate persistent user memory without explicit policy or authorization
- self-expand permissions outside explicit allowed boundaries
- use opaque success criteria that users cannot inspect

---

## 5. System Principles

### 5.1 Sovereignty First
User intent governs execution. System initiative is permitted only within declared bounds.

### 5.2 Observable by Default
All meaningful attempts, scores, tool actions, and approvals must be loggable and reviewable.

### 5.3 Reversible by Preference
Whenever possible, use reversible actions, drafts, previews, branch-based edits, or dry-runs before committing.

### 5.4 Typed Action Surfaces
Execution should occur through typed tools and controlled interfaces, not arbitrary freeform side effects.

### 5.5 Evaluator-Centric Design
Progress is determined by measurable success criteria, not by persuasive narration.

### 5.6 Budgeted Search
Every loop must operate within explicit constraints for time, tokens, spend, retries, and external side effects.

### 5.7 Promotion through Evidence
Persistent workflows are created from demonstrated success, not from one charismatic run.

### 5.8 Identity Boundary Integrity
Personas, agents, and automation layers may borrow context but do not own user identity.

---

## 6. High-Level Architecture

The system has eight major layers:

1. Intent Compilation Layer
2. Execution Contract Layer
3. Planning and Search Layer
4. Action Runtime Layer
5. Evaluation Layer
6. Attempt Ledger and Learning Layer
7. Governance and Safety Layer
8. Promotion and Reuse Layer

### 6.1 Architecture Flow

```text
User Goal
  -> Intent Compiler
  -> Execution Contract
  -> Candidate Plan Generator
  -> Attempt Executor
  -> Observation Collector
  -> Evaluator
  -> Retain / Reject / Refine
  -> Loop Controller
  -> Best Result + Ledger + Promotion Candidate
```

---

## 7. Intent Compilation Layer

### 7.1 Purpose
Convert natural language requests into structured machine-operable contracts.

### 7.2 Responsibilities
- parse objective
- extract deliverables
- infer task domain
- detect sensitive operations
- identify dependencies
- derive candidate evaluators
- determine required tools
- assign budgets and approval policies
- generate initial execution contract

### 7.3 Inputs
- user request
- user context
- available tools
- policy settings
- historical preferences
- prior similar workflows

### 7.4 Outputs
- normalized objective
- domain classification
- execution contract draft
- risk profile
- evaluator template selection
- permissions profile

### 7.5 Domain Taxonomy
The compiler should classify requests across at least:

- research
- communication
- code/dev
- browser task
- document operation
- data processing
- planning
- scheduling support
- monitoring
- multi-domain hybrid workflow

### 7.6 MVP Qualification
- natural-language goal parsing
- single-goal contract generation
- basic task domain inference
- manual evaluator template selection by system defaults

### 7.7 Production-Grade Qualification
- multi-objective contract synthesis
- explicit ambiguity modeling
- dependency extraction
- policy-aware risk classification
- user-visible contract explanation and editable controls

---

## 8. Execution Contract Layer

### 8.1 Purpose
Provide the canonical structured object governing all loop behavior.

### 8.2 Required Fields

```yaml
execution_contract:
  id: string
  version: string
  objective:
    summary: string
    details: string
  deliverables:
    - type: string
      description: string
  domain: string
  success_criteria:
    - id: string
      description: string
      metric_type: string
      threshold: optional
      weight: number
  constraints:
    time_budget_sec: number
    token_budget: optional
    spend_budget_usd: optional
    retry_budget: number
    blast_radius:
      max_external_writes: number
      max_files_modified: number
      allow_irreversible_actions: boolean
  permissions:
    tools_allowed: []
    tools_denied: []
    writable_surfaces: []
    approval_required_for: []
  observability:
    log_level: string
    store_inputs: boolean
    store_outputs: boolean
    store_diffs: boolean
    store_artifacts: boolean
  evaluator:
    template: string
    custom_rules: []
  fallback_policy:
    on_partial_success: string
    on_repeated_failure: string
    on_budget_exhaustion: string
  promotion_policy:
    allow_promotion: boolean
    min_success_count: number
  governance:
    identity_boundary_mode: string
    memory_mutation_policy: string
    data_handling_policy: string
```

### 8.3 Optional Fields
- recurrence settings
- escalation settings
- notification policy
- approval timeout semantics
- artifact retention policy
- persona routing hints
- preferred model family
- preferred cost-performance mode

### 8.4 MVP Qualification
- single-objective contract
- simple success criteria list
- basic budget fields
- basic allowed tools list

### 8.5 Production-Grade Qualification
- nested subtasks
- weighted multi-objective scoring
- dynamic budget reallocation
- versioned contract evolution
- signed approvals and audit metadata

---

## 9. Planning and Search Layer

### 9.1 Purpose
Generate, mutate, rank, and select strategies for execution.

### 9.2 Responsibilities
- generate initial plan candidates
- search across plan variants
- select tool sequences
- assign model routing per subtask
- decompose complex goals into subtasks
- refine failed plans based on trace evidence

### 9.3 Plan Representation
Plans should be expressible as:

- ordered task lists
- DAGs
- state machines
- tool chain templates
- hierarchical subtasks

### 9.4 Plan Node Fields

```yaml
plan_node:
  id: string
  kind: action | reasoning | retrieval | approval | evaluation | transform
  description: string
  inputs: []
  outputs: []
  dependencies: []
  tool_binding: optional
  retry_policy: optional
  timeout_sec: optional
  approval_gate: optional
  reversible: boolean
```

### 9.5 Search Strategies
Autoloop should support:

- greedy refinement
- beam search over plans
- bandit-style exploration vs exploitation
- mutation-based search
- template retrieval from prior successful workflows
- planner-critic loop
- branch-and-bound using budget constraints

### 9.6 Mutation Dimensions
The search layer may mutate:

- prompt phrasing
- context packing strategy
- retrieval query
- tool choice
- action ordering
- decomposition granularity
- model/provider selection
- retry timing
- summarization length
- evaluator thresholds when contract permits
- browser path or interaction route

### 9.7 Planner Modes
- conservative
- balanced
- exploratory
- cost-minimizing
- latency-minimizing
- compliance-first

### 9.8 MVP Qualification
- initial plan generation
- single mutation path on failure
- ordered list execution
- retry with minor plan revision

### 9.9 Production-Grade Qualification
- multi-candidate parallel planning
- adaptive search strategies
- retrieval of historical workflow priors
- hierarchical decomposition
- learned plan ranking from past outcomes

---

## 10. Action Runtime Layer

### 10.1 Purpose
Execute plans through typed, bounded action interfaces.

### 10.2 Action Categories
- local file actions
- code actions
- shell actions
- browser actions
- email actions
- calendar actions
- document actions
- data transforms
- API calls
- retrieval and search actions
- human approval actions

### 10.3 Action Requirements
All runtime actions should be:

- typed
- validated
- permission-checked
- logged
- measurable
- timeout-bounded
- side-effect-classified
- reversible where possible

### 10.4 Action Lifecycle
1. validate input
2. check contract permissions
3. assess approval requirements
4. execute
5. capture outputs and side effects
6. classify result
7. emit observations
8. update ledger

### 10.5 Action Status Types
- not_started
- running
- succeeded
- failed_retryable
- failed_terminal
- blocked_approval
- skipped
- rolled_back

### 10.6 Reversibility Classes
- fully reversible
- soft-reversible
- recoverable with checkpoint
- irreversible

### 10.7 MVP Qualification
- support for a small typed tool surface
- sequential action execution
- basic retries
- dry-run mode for selected tools

### 10.8 Production-Grade Qualification
- transaction-aware orchestration
- checkpoints and rollback
- concurrency controls
- partial-order scheduling
- action provenance graph

---

## 11. Evaluation Layer

### 11.1 Purpose
Measure progress against explicit success criteria and determine whether to keep, revise, or reject an attempt.

### 11.2 Evaluator Responsibilities
- score attempt outputs
- compare against thresholds
- detect regressions
- compute partial success
- identify failure modes
- generate structured feedback for search refinement

### 11.3 Evaluator Types
- deterministic rule evaluator
- metric evaluator
- artifact quality evaluator
- test harness evaluator
- human approval evaluator
- hybrid evaluator

### 11.4 Example Scorecard Schema

```yaml
scorecard:
  overall_score: number
  verdict: accept | reject | partial
  criteria:
    - id: string
      score: number
      passed: boolean
      notes: string
  regressions: []
  risks_observed: []
  confidence: number
```

### 11.5 Domain Evaluator Templates

#### Research
- source count
- citation completeness
- relevance score
- novelty coverage
- consistency across sources
- user approval

#### Code/Dev
- tests passing
- lint status
- typecheck status
- benchmark delta
- diff size
- rollback success

#### Email/Communication
- classification accuracy
- draft quality
- policy compliance
- false positive rate
- user acceptance rate

#### Browser Task
- target page reached
- field completeness
- required data extracted
- no unauthorized submission
- user confirmation achieved

#### Planning
- schedule completeness
- dependency coverage
- conflict detection
- user revisions required

### 11.6 Human-in-the-Loop Evaluation
The system must support user scoring on:

- output usefulness
- correctness
- tone/style fit
- completion adequacy
- trustworthiness

### 11.7 MVP Qualification
- template-based evaluators
- rule and threshold scoring
- accept/reject/partial verdicts

### 11.8 Production-Grade Qualification
- ensemble evaluators
- evaluator calibration
- human feedback integration into ranking
- learned evaluator tuning with guardrails

---

## 12. Attempt Ledger and Learning Layer

### 12.1 Purpose
Record attempts as durable structured evidence and enable future improvement.

### 12.2 Responsibilities
- persist full attempt trace
- store inputs and outputs
- record tool actions and timings
- record scorecards and verdicts
- capture user approvals
- classify failure modes
- enable replay and analysis
- mine repeated successful patterns

### 12.3 Attempt Record Schema

```yaml
attempt_record:
  id: string
  contract_id: string
  iteration: number
  parent_attempt_id: optional
  plan_snapshot: object
  action_trace: []
  observations: []
  outputs: []
  artifacts: []
  scorecard: object
  verdict: string
  failure_mode: optional
  cost:
    tokens: number
    wall_time_ms: number
    api_spend_usd: optional
  approvals: []
  checkpoints: []
  timestamp: string
```

### 12.4 Learning Products
From the ledger, the system should be able to derive:

- workflow priors
- prompt variants with higher success rates
- tool-order preferences
- domain-specific heuristics
- common failure clusters
- user preference signatures

### 12.5 Memory Policy
Attempt history should not automatically become user identity memory. Workflow evidence and user identity are separate layers.

### 12.6 MVP Qualification
- store attempt records
- allow simple replay
- basic failure summaries

### 12.7 Production-Grade Qualification
- graph-based trace analytics
- workflow mining
- learned priors for planner ranking
- drift detection on workflow quality

---

## 13. Governance and Safety Layer

### 13.1 Purpose
Constrain autonomous behavior within user, system, and policy boundaries.

### 13.2 Responsibilities
- enforce permissions
- enforce approval gates
- cap budgets
- classify action risk
- preserve identity boundaries
- prevent silent memory mutation
- block unauthorized irreversible actions
- support kill switch and loop halt

### 13.3 Governance Domains
- identity governance
- action governance
- data governance
- cost governance
- compliance governance
- retention governance

### 13.4 Approval Gate Triggers
Approval should be required for at least:

- sending messages or emails
- submitting forms
- making payments
- deleting files or messages
- editing user memory or persistent profile
- publishing externally
- mutating permissions
- executing high-risk shell commands

### 13.5 Risk Tiers
- Tier 0: read-only and reversible
- Tier 1: low-risk writable actions
- Tier 2: meaningful user-facing side effects
- Tier 3: irreversible or high-consequence actions

### 13.6 Kill Conditions
Loop must halt on:

- budget exhaustion
- repeated terminal failures
- policy violation attempt
- user cancellation
- unsafe state detection
- evaluator confidence collapse

### 13.7 MVP Qualification
- static approval rules
- budget caps
- tool allowlist
- halt on repeated failures

### 13.8 Production-Grade Qualification
- dynamic risk scoring
- policy inheritance by workflow type
- detailed audit logging
- tenant- or org-level governance packs

---

## 14. Promotion and Reuse Layer

### 14.1 Purpose
Convert repeated successful loop behavior into reusable assets.

### 14.2 Promotion Targets
- saved automation
- workflow template
- skill-like routine
- recurring schedule
- policy-backed operation profile
- personalized execution style

### 14.3 Promotion Criteria
A workflow may be promoted when it meets thresholds such as:

- repeated success count
- stable evaluator score
- low intervention rate
- acceptable cost profile
- no recent safety violations

### 14.4 Promotion Artifact Contents
- canonical execution contract
- plan template
- evaluator template
- approval profile
- preferred tools/models
- rollback/fallback rules
- provenance summary

### 14.5 MVP Qualification
- save successful workflow manually
- reuse by user invocation

### 14.6 Production-Grade Qualification
- automated promotion suggestions
- versioned workflow templates
- analytics-backed retirement or retraining of stale workflows

---

## 15. Workflow Lifecycle

### 15.1 End-to-End Lifecycle
1. User states goal
2. Intent compiled into execution contract
3. Contract reviewed or accepted implicitly within safe bounds
4. Planner generates initial plan
5. Runtime executes bounded attempt
6. Observations collected
7. Evaluator scores results
8. Loop controller decides accept, refine, retry, escalate, or halt
9. Best result surfaced to user
10. Attempt trace stored in ledger
11. Successful strategy optionally promoted

### 15.2 Loop Controller Decisions
- continue with mutation
- continue with alternate plan
- continue with reduced scope
- halt and present best partial result
- request approval
- request missing information
- promote workflow

---

## 16. Mode Matrix

### 16.1 Operational Modes

| Mode | Description | Typical Use |
|---|---|---|
| Assist | one-pass execution with minimal search | simple tasks |
| Loop | iterative refinement with bounded retries | automation and research |
| Simulation | dry-run without side effects | planning and verification |
| Approval-Staged | prepares actions but waits for confirmation | communications, external actions |
| Continuous | recurring scheduled operation | daily briefs, monitoring |
| Benchmark | compares multiple candidate strategies | code, retrieval, planning |

### 16.2 MVP
- Assist
- Loop
- Approval-Staged

### 16.3 Production Grade
- all of the above with recurrence, monitoring, and comparative benchmarking

---

## 17. Domain Modules

### 17.1 Research Module
Supports:
- source gathering
- deduplication
- synthesis
- citation assembly
- insight ranking
- recurring briefs

### 17.2 Communication Module
Supports:
- inbox triage
- classification
- drafting
- reply recommendation
- approval before send

### 17.3 Code/Dev Module
Supports:
- repo-local editing
- tests
- linting
- benchmarking
- branch-based attempts
- diff scoring

### 17.4 Browser Module
Supports:
- navigation
- structured extraction
- bounded form completion
- comparison across pages
- approval before submission

### 17.5 Document Module
Supports:
- summarization
- extraction
- transformation
- formatting
- packaging into final artifacts

### 17.6 Planning Module
Supports:
- daily planning
- project planning
- dependency sequencing
- meeting prep
- follow-up extraction

### 17.7 Monitoring Module
Supports:
- recurring checks
- change detection
- threshold alerts
- summarization of state changes

---

## 18. Data Model

### 18.1 Core Entities
- Goal
- ExecutionContract
- Plan
- PlanNode
- AttemptRecord
- ActionTrace
- Observation
- Artifact
- Scorecard
- ApprovalRecord
- WorkflowTemplate
- PromotionRecord
- PolicyProfile

### 18.2 Suggested Relational Shape

```text
goals
execution_contracts
plans
plan_nodes
attempt_records
action_traces
observations
artifacts
scorecards
approval_records
workflow_templates
promotion_records
policy_profiles
```

### 18.3 Graph Relationships
Useful graph relations include:

- goal -> contract
- contract -> plan
- plan -> attempt
- attempt -> action
- attempt -> artifact
- attempt -> scorecard
- attempt -> failure_mode
- workflow_template -> promoted_from_attempts

---

## 19. API Surface

### 19.1 Core API Groups
- contract APIs
- planning APIs
- execution APIs
- evaluation APIs
- ledger APIs
- promotion APIs
- governance APIs
- scheduling APIs

### 19.2 Illustrative Endpoints

```text
POST   /autoloop/contracts
GET    /autoloop/contracts/:id
POST   /autoloop/plans/generate
POST   /autoloop/attempts/run
POST   /autoloop/attempts/:id/cancel
GET    /autoloop/attempts/:id
POST   /autoloop/evaluate
GET    /autoloop/workflows
POST   /autoloop/workflows/promote
POST   /autoloop/approvals/:id/respond
GET    /autoloop/ledger/query
```

### 19.3 Event Types
- contract.created
- plan.generated
- attempt.started
- attempt.completed
- attempt.failed
- approval.requested
- approval.granted
- approval.denied
- workflow.promoted
- loop.halted

---

## 20. UI and UX Surfaces

### 20.1 Required Views
- goal composer
- execution contract viewer
- plan preview
- attempt timeline
- scorecard view
- approval inbox
- workflow library
- trace and artifact browser
- metrics dashboard

### 20.2 UX Principles
- show current objective clearly
- expose loop state without overwhelming the user
- distinguish proposed actions from committed actions
- show cost and risk indicators
- allow user intervention and stopping
- preserve inspectability of why a strategy was chosen

### 20.3 MVP Qualification
- goal composer
- contract summary
- attempt log
- approval prompt
- simple saved workflow list

### 20.4 Production-Grade Qualification
- interactive plan graph
- evaluator breakdowns
- workflow analytics
- multi-attempt comparison
- policy and permission editor

---

## 21. Observability and Telemetry

### 21.1 Required Metrics
- attempt success rate
- partial success rate
- average attempts per goal
- tool failure rate
- cost per successful task
- user intervention rate
- approval acceptance rate
- rollback frequency
- promotion conversion rate

### 21.2 Trace Requirements
Each attempt trace should record:
- selected plan
- tools invoked
- timing per step
- outputs and artifacts
- evaluator results
- approval points
- budget consumption
- failure mode classification

### 21.3 Production-Grade Analytics
- workflow drift over time
- evaluator disagreement rates
- domain-specific cost-performance curves
- user trust signals

---

## 22. Failure Handling

### 22.1 Failure Classes
- missing context
- tool unavailable
- permission denied
- evaluation failure
- low confidence output
- budget exhausted
- policy conflict
- contradictory success criteria
- environment instability

### 22.2 Failure Strategies
- retry same node
- mutate plan
- reduce scope
- fall back to human review
- halt with partial result
- checkpoint rollback

### 22.3 Production-Grade Requirements
- structured failure taxonomy
- replay and diff tools
- root cause aggregation by workflow type

---

## 23. Cost and Budget System

### 23.1 Budget Dimensions
- token budget
- wall-clock budget
- compute budget
- API spend budget
- retry budget
- side-effect budget

### 23.2 Budget Policies
- hard cap
- soft warning threshold
- auto-degrade mode
- alternate cheap-model routing
- reduced-evaluator mode for exploratory search

### 23.3 MVP Qualification
- wall time cap
- retry count cap
- optional token cap

### 23.4 Production-Grade Qualification
- dynamic rebalancing
- domain-aware budget profiles
- per-user or per-workflow cost governance

---

## 24. Security and Privacy

### 24.1 Requirements
- least-privilege tool access
- approval for irreversible actions
- separation of attempt logs from identity memory
- redactable artifacts
- configurable retention windows
- explicit memory mutation controls
- auditability of side effects

### 24.2 Sensitive Data Handling
- identify secrets and credentials in traces
- mask or redact as needed
- prevent unsafe storage of privileged values

### 24.3 Production-Grade Qualification
- encrypted artifact storage
- tenant-aware policy enforcement
- role-based access controls for shared workspaces

---

## 25. Multi-User and Shared Workspace Considerations

### 25.1 Shared Context Support
In collaborative modes, Autoloop should support:
- project-level workflows
- approval routing by role
- shared trace visibility with permissions
- project guardian policies
- per-user identity lenses over shared artifacts

### 25.2 Conflict Handling
- competing goals on same resource
- approval conflicts
- workflow ownership and edit rights

---

## 26. Scheduling and Recurrence

### 26.1 Recurring Loop Support
Autoloop should support recurring goals such as:
- daily briefs
- inbox triage
- weekly research sweeps
- ongoing webpage monitoring
- codebase maintenance loops

### 26.2 Scheduling Controls
- schedule frequency
- budget per run
- approval policies per recurrence
- stale-result handling
- output destination routing

---

## 27. Model Routing

### 27.1 Purpose
Use different models or providers for different subtasks when beneficial.

### 27.2 Routing Factors
- domain fit
- latency
- cost
- context length
- tool calling capability
- deterministic reliability
- privacy mode

### 27.3 Routing Levels
- contract-level preferred model
- plan-level override
- node-level override

### 27.4 Production-Grade Qualification
- learned routing policies
- evaluator-aware model switching
- hybrid local/cloud execution

---

## 28. Extensibility

### 28.1 Plugin Model
Autoloop should be extensible via:
- new action providers
- new evaluators
- new workflow templates
- domain packs
- governance packs
- reporting sinks

### 28.2 Required Plugin Interfaces
- action adapter interface
- evaluator interface
- planner extension interface
- promotion rule interface

---

## 29. Quality Targets

### 29.1 Functional Quality
- goals compile correctly
- plans execute predictably
- evaluator decisions are inspectable
- retries are bounded and meaningful
- traces are complete enough for review

### 29.2 Product Quality
- user trust in automation output
- low surprise rate
- high usefulness of saved workflows
- stable behavior under repeated runs

### 29.3 Production SLO Candidates
- attempt trace completeness > 99%
- approval request integrity 100%
- no unauthorized irreversible action
- workflow replay determinism within accepted bounds

---

## 30. MVP vs Production Grade Matrix

| Capability | MVP | Production Grade |
|---|---|---|
| Goal parsing | single-goal contract | multi-objective, editable contracts |
| Planning | single candidate + retries | multi-candidate adaptive search |
| Runtime | sequential typed actions | transactional, checkpointed, concurrent |
| Evaluation | template-based rules | ensemble, calibrated, feedback-aware |
| Ledger | attempt logging | analytics, mining, priors, drift detection |
| Governance | static rules and approvals | dynamic risk, audit packs, org policies |
| Promotion | manual save | automated promotion suggestions and versioning |
| UI | summary views | graph views, analytics, controls |
| Scheduling | limited | full recurring and monitored operations |
| Model routing | static/default | learned, node-level hybrid routing |

---

## 31. Recommended Build Order

### Phase 1
- contract compiler
- basic planner
- typed runtime
- evaluator templates
- attempt ledger
- approval gates

### Phase 2
- saved workflows
- recurrence
- richer scorecards
- search mutation strategies
- better dashboards

### Phase 3
- workflow mining
- promotion suggestions
- model routing optimization
- collaborative policy packs
- production-grade observability and security

---

## 32. Canonical Example

### 32.1 User Goal
“Every morning, scan my inbox, identify anything financially important, summarize it, and draft next actions.”

### 32.2 Contract Summary
- domain: communication + planning
- success criteria:
  - relevant emails identified
  - concise summary generated
  - next actions drafted
  - no emails sent without approval
- budget:
  - 10 minutes
  - max 3 retries per stage
- approvals:
  - required before sending or labeling outside allowed namespace

### 32.3 Loop Behavior
1. search inbox
2. classify messages
3. score classification confidence
4. summarize high-salience items
5. draft actions
6. present approval packet
7. store trace and artifacts
8. reuse improved classification heuristics next time

---

## 33. Non-Goals and Anti-Patterns

Autoloop should avoid becoming:
- an unbounded agent with vague initiative
- a permission creep engine
- a silent background mutator of user state
- a system that confuses eloquence with success
- a black box that cannot explain why it chose a plan

---

## 34. Final Position

Codexify Autoloop is a general-purpose automation substrate, not merely a chat feature and not merely an agent wrapper. Its defining property is iterative bounded search over executable strategies under explicit evaluation and governance.

The full production vision and the first shippable slice live on the same ruler:

- MVP is the shortest reliable measurable segment.
- Production grade is the full marked instrument.

This document is the map for both.

