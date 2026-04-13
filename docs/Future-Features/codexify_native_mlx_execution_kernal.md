Codexify Native MLX Execution Kernel
Future-Features Spec

Status: Future feature
Classification: architecture / execution-runtime spec
Not part of current beta promise: yes
Intended location: Future-Features/codexify-native-mlx-execution-kernel.md

1. Purpose

Define a future Codexify subsystem that provides Claude Code / Codex-class native coding capabilities without depending on an external harness product.

This subsystem would let Codexify act as a sovereign local coding environment with:

repo-aware task execution
file inspection and patch generation
command execution and validation loops
background and resumable coding runs
bounded multi-step orchestration
MLX-powered local inference routing
native support for throughput-aware local workflows

This is a future architecture target, not a statement of current runtime truth.

2. Why this belongs in Future-Features

Codexify’s current supported reality is still:

local Docker Compose as the supported path
local-only beta posture
queue-backed chat completion
upload → parse → embed → retrieve as the main validated knowledge path
command bus and several adjacent orchestration surfaces still internal, quarantined, or outside the release promise.

This spec describes a native execution layer above the current core loop. It should not be treated as current behavior, release-ready scope, or implied implementation status.

3. Product thesis

Codexify should eventually provide the feeling of a first-class coding runtime:

one environment
one identity boundary
one workspace
one execution story

The user should not need:

an external harness product
a second orchestration shell
a parallel agent-control plane to make Codexify feel capable
Core principle

Codexify should not avoid harness logic.

Codexify should internalize harness logic.

Externally:

Codexify feels like one coherent coding workspace.

Internally:

Codexify contains a runtime plane that handles orchestration, context assembly, validation, model routing, retries, and inspectable execution traces.
4. Proposed subsystem name
External-facing language
Codexify Native Coding Runtime
Codexify Local Operator
Codexify Workspace Execution
Internal subsystem names
Execution Kernel
TaskGraph Runtime
Local Inference Fabric
Workspace Operator
Validation Plane

Preferred internal umbrella name:

Codexify Execution Kernel

5. Non-goals

This future subsystem is not intended to be:

a no-code automation platform
a cloud-first agent orchestration service
an always-autonomous PR factory
a replacement for Codexify’s identity boundaries
a freeform script pile attached to chat
a promise that current Codexify already supports autonomous coding-agent execution
6. Desired future user outcomes

A user should eventually be able to say:

“Fix this failing test.”
“Implement this feature in this repo.”
“Review the current diff.”
“Figure out why the build broke.”
“Make a plan, then patch, then validate.”
“Pause before changing files.”
“Run these bounded subtasks in parallel.”
“Use a fast local model for triage and a stronger one for patch synthesis.”
“Resume the run that failed earlier.”

And Codexify should handle the workflow natively.

7. Architectural overview
User / Chat / Workspace Surface
        |
        v
Intent Interpreter
        |
        v
Codexify Execution Kernel
  ├─ TaskGraph Runtime
  ├─ Context Assembler
  ├─ Inference Router
  ├─ Workspace Operator
  ├─ Validation Plane
  ├─ Approval / Policy Engine
  └─ Provenance Recorder
        |
        +--> Local Inference Fabric (MLX)
        +--> Deterministic Executors (shell, git, tests, parsers, linters)
        +--> Retrieval / Memory / Docs / Project context

This future layer should sit above the current chat/retrieval substrate, not replace it. The current runtime already has meaningful seams in chat completion, context assembly, provider routing, queues, event transport, and subsystem boundaries that make this kind of later layering plausible.

8. Relationship to current architecture

This future subsystem should build on existing Codexify strengths rather than bypass them.

Existing foundations that matter
queue-backed task execution and event transport
context broker and retrieval assembly
durable Postgres state
Redis-backed coordination, locks, and task-event surfaces
vector-backed retrieval
project/thread/document linkage
artifact and lineage direction of travel
runtime token discipline for statuses and lifecycle semantics.
Important boundary

This subsystem should not collapse chat, retrieval, validation, and orchestration into one vague assistant blob.

The chat surface remains the invocation surface.

The execution kernel becomes the actor.

9. Core components
9.1 Intent Interpreter

Transforms a user request into an executable coding intent.

Responsibilities
classify request type
determine scope
decide whether a simple loop or graph is needed
determine approval requirements
build an initial run plan
Example intent classes
bug_fix
feature_build
refactor
review_diff
root_cause_analysis
spec_to_patch
patch_validation
9.2 TaskGraph Runtime

The orchestration core for future coding runs.

Responsibilities
represent coding work as DAGs or bounded loops
execute nodes in dependency order
support retries, branching, joins, and checkpoints
pause, resume, cancel
run background jobs
preserve partial progress and recovery state
Reason this matters

Current Codexify already distinguishes between acceptance, execution, and visibility in its runtime truth surfaces. A future TaskGraph Runtime should preserve that discipline rather than flattening everything into “sent / failed.”

9.3 Context Assembler

Builds bounded context bundles for each execution step.

Responsibilities
retrieve relevant files and symbols
include project/thread/docs context when appropriate
attach prior attempts and validation traces
compress repo state
prevent oversized or lazy context dumping
Future design rule

Context must be assembled, not dumped.

This aligns with Codexify’s existing retrieval-router doctrine and context-broker structure, even though this future execution layer does not yet exist.

9.4 Inference Router

Chooses the appropriate local model lane per node.

Responsibilities
map node type to model capability
manage escalation
respect memory and concurrency limits
separate “fast enough” work from “deep reasoning” work
support fallback and degraded execution policies
9.5 Local Inference Fabric

The MLX-backed engine for local inference.

Responsibilities
host local models
manage throughput-aware scheduling
track memory pressure
reuse prompt prefixes and caches
protect foreground interaction quality
support multiple bounded inference lanes
Design intent

High throughput does not mean reckless parallelism.

It means:

the right model for the job
controlled concurrency
cached context reuse
clear degradation behavior
local-first stability
9.6 Workspace Operator

The deterministic tool layer.

Responsibilities
inspect files
search tree/symbols
apply patches
revert patches
run shell commands
inspect git status and diffs
invoke tests, linters, and type checks
capture structured command results
Rule

Generative steps should not impersonate deterministic tools.

9.7 Validation Plane

The quality gate.

Responsibilities
run validators
interpret failure traces
determine whether failures are pre-existing or induced
trigger bounded repair loops
decide when to stop and ask for approval
Validation classes
syntax
lint
typecheck
tests
build
contract checks
regression checks
9.8 Approval / Policy Engine

Controls when Codexify must stop and ask.

Responsibilities
gate destructive actions
require approval for wide patch scopes
require approval for branch / PR / external side effects
enforce trust and workspace policies
prevent silent escalation of risky actions
9.9 Provenance Recorder

Records what happened and why.

Responsibilities
link runs to threads, workspaces, artifacts, and patches
preserve node inputs and outputs
record model choices and validation outcomes
support replay and inspection
maintain lineage integrity

This direction should align with Codexify’s existing interest in thread-artifact lineage and explicit export/restore contracts rather than inventing disposable execution state with no provenance.

10. MLX routing strategy
10.1 Model lanes
Fast lane

Use for:

classification
routing
issue extraction
lightweight summaries
diff labeling
file triage
Mid lane

Use for:

bounded code edits
small refactors
test failure analysis
retrieval-grounded responses
localized review tasks
Heavy lane

Use for:

architecture reasoning
multi-file implementation
difficult debugging
patch synthesis after failed validation
deep review passes
10.2 Routing policy goals

Each node should eventually declare:

preferred lane
fallback lane
context budget
latency class
escalation rule
retry policy

This follows the same broad discipline as Codexify’s existing move toward canonical protocol/state contracts and explicit runtime truth vocabularies.

10.3 Throughput controls

The future scheduler should enforce:

max concurrent heavy jobs
bounded medium-job concurrency
microtask batching for fast-lane work
memory-pressure aware admission control
cancellation of stale nodes
prioritization for interactive foreground tasks
Principle

Do not let background cleverness murder foreground usability.

10.4 Cache strategy

Potential reusable caches:

repo summaries
symbol maps
retrieval bundles
prompt-prefix caches
validator result summaries
diff review summaries
prior failure pattern summaries
11. Data model sketch
11.1 Key future entities
WorkspaceExecutionRun
run id
workspace id
thread id
intent type
status
priority
summary
approval mode
graph id
TaskGraph
graph id
run id
version
entry nodes
failure policy
checkpoint policy
ExecutionNode
node id
graph id
kind
dependencies
retry policy
routing policy
timeout
approval requirement
ContextBundle
bundle id
node id
files
symbols
documents
constraints
prior artifacts
compression level
PatchArtifact
artifact id
run id
node id
diff
file changes
apply status
revert handle
ValidationResult
result id
node id
validator type
status
logs
structured failures
ModelAssignment
node id
selected lane
model name
reason
budget
fallback metadata
ApprovalCheckpoint
checkpoint id
run id
node id
reason
status
user response
12. Node taxonomy
12.1 Deterministic nodes

Examples:

read_file
search_symbols
run_tests
run_lint
run_typecheck
git_diff
apply_patch
revert_patch
12.2 Model nodes

Examples:

classify_request
summarize_region
plan_fix
propose_patch
review_diff
explain_failure
12.3 Hybrid nodes

Examples:

triage_test_failures
root_cause_analysis
repair_after_validation
spec_to_patch
12.4 Approval nodes

Examples:

approve_plan
approve_patch
approve_wide_scope_edit
13. Execution rules
13.1 Default small-task loop
classify request
assemble context
generate plan
propose patch
validate
repair if needed
ask for approval if required
finalize summary
13.2 Graph execution for larger work
classify
research and symbol discovery
join results
create plan
decompose subtasks
implement
validate
review
approval
finalize
13.3 Fresh-context rule

Planning and implementation may intentionally use separate bounded contexts to reduce anchoring bias and preserve clarity.

1. UX requirements
14.1 Default user experience

The user should see:

simple request surface
optional execution preview
live status
patch preview
validation results
concise final summary
14.2 Advanced user experience

Power users may inspect:

task graph
node logs
model assignments
context bundles
retry tree
validation traces
execution history
14.3 Approval experience

The system should support explicit checkpoints for:

plan approval
patch approval
broad workspace mutation
external side effects
15. Alignment requirements with existing Codexify doctrine

This future feature must respect existing Codexify architectural laws rather than inventing a private kingdom.

15.1 Identity boundaries

No durable identity mutation from coding runs by default.
Execution state is not identity state.
This aligns with Codexify’s explicit separation of diary/history from identity modeling.

15.2 Token discipline

All repeated status and lifecycle meanings should become canonical tokens rather than local string drift.

15.3 Message versus attempt integrity

Future execution attempts should preserve the distinction between authored turn identity and execution-attempt identity, consistent with the chat runtime contract.

15.4 Provenance

Execution-generated artifacts should remain linkable to source thread/project/message context and not become lineage-orphaned debris.

15.5 Retrieval posture

Future coding execution should respect retrieval-router discipline rather than embedding ad hoc retrieval heuristics inside prompt text.

16. MVP boundary for the future feature

When this layer is eventually tackled, a realistic first slice would be:

Phase 1
repo registration
file read/search/edit
shell execution
git diff inspection
patch apply/revert
Phase 2
single-run execution loop
bounded context assembly
validation loop
patch preview + approval
Phase 3
MLX routing with fast and heavy lanes
memory-aware scheduler
cache reuse
Phase 4
DAG execution
retries
checkpoints
background resumable runs
Phase 5
safe bounded parallelism
file-scope collision control
richer review and planning nodes
17. Explicit deferrals

Do not start with:

full multi-agent teams
automatic PR creation
unrestricted autonomous repo mutation
broad cloud-provider orchestration
voice-driven coding control
distributed execution across nodes

Those can come later, if ever.

The first win is a stable native repo operator with validation discipline.

18. Final principle

Codexify should eventually behave like this:

Chat is the invocation surface.
The Execution Kernel is the actor.
The Workspace Operator is the hand.
The Local Inference Fabric is the nervous system.
The Validation Plane is the conscience.

That gives Codexify the capabilities people seek from Claude Code or Codex while keeping the product sovereign, local-first, and internally coherent.

19. Future implementation note

When this feature graduates from Future-Features into active engineering, planning should start from:

current runtime truth and supported-path constraints
subsystem boundaries and blast radius
current queue / retrieval / provider / operator-surface risks
canonical token and runtime-contract discipline.
