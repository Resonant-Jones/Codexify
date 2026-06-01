---
marp: true
title: Campaigns, Tasks, and the Codexify Task Template
description: Teaching deck for Codexify campaign/task normalization methodology.
paginate: true
---

# Campaigns, Tasks, and the Codexify Task Template

## Normalizing developer input without forcing developers to work the same way

Teaching deck

Source status: docs-backed methodology proof

---

# Goal

Show how Codexify can normalize varied developer input into a shared execution format.

The method:

- let each developer express intent in their own working style
- translate that intent into a standardized Codexify Task Prompt Template
- organize related tasks under campaigns
- preserve prompt, output, validation, and goal relationships for later review

---

# Core Claim

Codexify does not need every developer to write the same way.

It needs every execution unit to arrive at the same contract boundary.

That boundary is the Codexify Task Prompt Template:

- objective
- scope
- allowed files
- preconditions
- execution checklist
- expected results
- validation
- rollback
- receipt

---

# Current Truth Boundary

This deck is a teaching artifact, not a new runtime claim.

What is already repo-backed:

- Campaigns and tasks are established documentation and runner concepts.
- The task template exists as a concrete prompt artifact.
- Campaign Runner schemas require structured campaign and task outputs.
- ADR-028 defines Execution Ledger as a governed Campaign Runner extension.

What this deck does not claim:

- autonomous dispatch is release-proven
- UI dispatch is release-proven
- file artifacts are canonical runtime truth
- task acceptance equals completion

---

# The Problem

Developers naturally vary.

One developer writes:

> Fix upload retries. It flakes when Redis stalls.

Another writes:

> Add retry/backoff/dead-letter behavior to the document embed queue and prove it with tests.

A third writes:

> Prevent silent doc embedding stalls; preserve transcript truth.

All three may point at the same intent. Without normalization, agents must guess.

---

# The Codexify Move

Developer language stays flexible.

System intake becomes strict.

```text
raw developer intent
  -> intent extraction
  -> campaign placement
  -> task boundary selection
  -> Codexify Task Prompt Template
  -> execution attempt
  -> receipt and proof
```

The human style is preserved at the edge.

The execution contract is standardized at the center.

---

# Campaign Layer

Campaigns organize work by feature, goal, or proof arc.

They answer:

- What larger goal does this task serve?
- Which tasks belong together?
- Which task must happen first?
- What proof is required before the campaign can be considered done?
- Which prompt/output relationships should future agents inspect?

Campaigns are the goal graph.

Tasks are the atomic execution units.

---

# Task Layer

A task is the smallest work unit that can be bounded, validated, and reviewed.

The task template makes ambiguity visible:

- `Metadata`: task, campaign, run, risk
- `Objective`: measurable outcome
- `Scope`: in and out
- `Allowed Files`: strict blast-radius boundary
- `Preconditions`: starting state
- `Execution Checklist`: deterministic commands
- `Expected Results`: success signals
- `Rollback / Cleanup`: recovery path
- `Runner Receipt Contract`: completion evidence

---

# Why This Normalizes

The template turns intent into fields.

That matters because fields can be checked.

Examples:

- "touch the upload pipeline" becomes `Allowed Files`
- "make it reliable" becomes `Expected Results`
- "prove it works" becomes `Validation commands`
- "do not break transcript truth" becomes `Out of scope` plus acceptance criteria
- "this belongs to beta hardening" becomes `campaign_id`

Normalization is not style enforcement.

It is translation into a stable execution interface.

---

# Proof Object: Template

Repo artifact:

`codex_runner/prompts/task_file_template.md`

The template requires:

- task and campaign identity
- risk classification
- measurable objective
- in-scope and out-of-scope boundaries
- strict allowed files
- deterministic execution checklist
- concrete expected results
- rollback path
- runner-owned receipt sections

This is the normalization target.

---

# Proof Object: Schema

Repo artifact:

`codex_runner/schemas/campaign_set.schema.json`

The schema forces campaign/task outputs into machine-checkable structure:

- `campaign_id`
- `campaign_slug`
- `depends_on`
- `campaign_markdown`
- task `id`
- task `slug`
- task `area`
- task `risk`
- task `files`
- task `tests`
- task `commit_message`
- task `task_artifact_markdown`
- task `activation_prompt`
- task `dependencies`

This is proof that normalization can be validated, not merely suggested.

---

# Proof Object: Runner Guarantees

Repo artifact:

`codex_runner/README.md`

The runner doctrine adds operational discipline:

- runner owns identifiers and artifact paths
- runner owns state and transition history
- generated proposals are merged deterministically
- task mapping edits are restricted to runner-owned markers
- task execution uses receipt discipline
- dirty preflight, schema drift, invalid paths, and task mutation drift hard-fail

This keeps normalization from becoming decorative prompt formatting.

---

# Proof Object: Ledger Contract

Repo artifact:

`docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`

ADR-028 defines the task/campaign relationship:

- campaigns and campaign goals are top-level planning containers
- coding work orders are atomic execution units
- execution attempts are separate from work-order identity
- attempt evidence is the durable proof surface
- approval does not equal completion
- completion requires validation output and receipts

This is the governance frame for agent learning.

---

# Before Normalization

Three valid developer inputs:

```text
Dev A: "Fix upload retries. Redis stalls break the run."
Dev B: "Add backoff and dead-letter behavior to document embed work."
Dev C: "Make doc embedding failure visible without claiming chat failed."
```

These are not identical sentences.

They may still normalize to the same task boundary.

---

# After Normalization

```text
task_id: TASK-DOC-EMBED-RETRY-001
campaign_id: CAMPAIGN-BETA-HARDENING-DOC-INGEST
risk: MED
objective: Add retry/backoff visibility for document embed queue stalls.
in_scope:
  - queue retry behavior
  - dead-letter recording
  - status visibility
out_of_scope:
  - provider routing changes
  - UI redesign
  - transcript state changes
allowed_files:
  - guardian/queue/document_embed_queue.py
  - guardian/workers/document_embed_worker.py
  - tests/.../test_document_embed_retry.py
validation:
  - pytest -v tests/.../test_document_embed_retry.py
```

The system translates many expressions into one reviewable task contract.

---

# Why Campaigns Help Agents Learn

Agents do not learn from vibes.

They learn from durable comparisons:

- original intent
- normalized task prompt
- files allowed
- execution attempt
- output summary
- validation result
- receipt
- follow-up task, if needed

Campaigns preserve the relationship between goal, task, prompt, output, and proof.

That makes mistakes inspectable instead of anecdotal.

---

# What "Learning" Means Here

This is not a claim that the runtime autonomously improves itself.

Learning means the system has evidence future agents can use:

- which task boundaries were too broad
- which prompts caused scope drift
- which validations were too weak
- which files were repeatedly touched
- which attempts failed for environmental reasons
- which follow-up tasks closed the gap

The lesson is stored in structure, not memory theater.

---

# Boundary Model

Nodes:

- developer laptop
- repo checkout
- Campaign Runner
- Guardian-mediated execution lane
- provider adapter or broker
- durable stores for attempts, receipts, and lineage

Trust boundaries:

- developer identity boundary
- repo/worktree boundary
- provider boundary
- execution-attempt boundary

Threat model:

- honest-but-inconsistent developers
- honest-but-buggy agents
- stale docs
- malicious or compromised inputs

---

# Data Model Reality

State ownership:

- campaign owns goal grouping
- task/work order owns atomic execution identity
- attempt owns run-specific evidence
- receipt owns completion claim evidence

Consistency target:

- eventual for campaign/task documentation
- durable and append-oriented for attempt evidence
- never collapse acceptance, execution, and completion

Conflict policy:

- prefer explicit review gates
- use follow-up tasks for unresolved proof gaps
- reject silent mutation drift

Identity binding:

- campaign id, task id, run id, attempt id, commit hash, and receipt reference

---

# Failure Modes

1. Over-normalization drops developer nuance.
   - Mitigation: preserve original intent as source context.

2. Prompt-only enforcement gets bypassed.
   - Mitigation: schema validation, allowed files, receipts, and review gates.

3. Acceptance is mistaken for completion.
   - Mitigation: keep request, attempt, and proof states separate.

4. Campaign docs become stale.
   - Mitigation: tie tasks to validation, commit hashes, and receipts.

5. Agents repeat failed patterns.
   - Mitigation: inspect prompt/output/proof relationships before new attempts.

---

# Minimal Viable Proof

The smallest useful proof is not a giant automation system.

It is a deterministic fixture:

1. Feed several differently written developer intents into the compiler.
2. Normalize each into the Codexify Task Prompt Template.
3. Assert stable fields:
   - same campaign placement
   - same allowed file boundary
   - same validation command class
   - same out-of-scope exclusions
4. Execute one normalized task.
5. Compare receipt evidence to the original intent.

That proves normalization without pretending autonomy is done.

---

# Prototype Track

Fast validation path:

- create three sample developer-intent files
- write expected normalized task artifacts
- add schema checks for required fields
- run docs validation and diff checks
- review whether the normalized task is executable by a new agent

Success signal:

- a second agent can execute the normalized task without asking what the developer meant

---

# Hardening Track

Production discipline path:

- bind developer identity to submitted intent
- preserve original input as immutable source context
- validate normalized task fields before execution
- reject absolute paths, `..`, missing tests, or missing rollback
- record attempt evidence separately from task identity
- require completion proof before campaign mapping updates
- report normalization failures as first-class review items

Success signal:

- task completion claims are traceable from raw intent to receipt evidence

---

# The Teaching Sentence

Campaigns give Codexify a goal graph.

Tasks give Codexify atomic execution units.

The Codexify Task Prompt Template gives Codexify a normalization boundary.

Together, they let developers keep their own working style while the system translates intent into a standard, reviewable, repeatable execution contract.

---

# Source Map

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/agent-protocol-operations.md`
- `docs/architecture/adr/028-execution-ledger-campaign-runner-contract.md`
- `codex_runner/README.md`
- `codex_runner/prompts/task_file_template.md`
- `codex_runner/prompts/audit_report_to_campaign_runner.md`
- `codex_runner/schemas/campaign_set.schema.json`
- `codex_runner/schemas/task_result.schema.json`
- `docs/Campaign/`
- `docs/tasks/`

