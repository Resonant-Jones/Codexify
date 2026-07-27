# Guardian Task Discovery and Proposal Specification

Status: Future-facing specification

Last updated: 2026-07-27

## Purpose

This specification defines how Guardian should transform vague, partial, colloquial, or highly specific user-authored task intent into a grounded, reviewable Task Proposal before any Pi, Codex, or other execution channel is allowed to act.

The central rule is:

> Users author intent. Guardian authors tasks. Execution systems execute approved Task Specs.

A user-authored command such as `/pi-task peanut butter donuts` is not an executable prompt and must never be forwarded verbatim to Pi or Codex as authority. It is a request for Guardian to investigate what the user may mean, gather relevant evidence, expose uncertainty, and present a proposed next step for human evaluation.

## Current truth

What is true now:

- Guardian owns delegation authority, lineage, policy, review posture, and result return.
- Codexify already has project, thread, document, architecture, retrieval, connector, delegation, work-order, run, and result-return concepts.
- The Guardian Orientation Layer defines a docs-first readiness posture before delegation packets are prepared.
- Pi invocation contracts define bounded envelopes, receipts, artifacts, provenance, permission checks, and Guardian-owned validation.
- Guardian Delegation already separates authored source messages, durable intents, approval state, AgentRun identity, result visibility, and source-thread return.
- Pi is an execution channel under Guardian, not a user-facing chat provider or direct Composer target.

What is not yet true:

- `/pi-task` does not exist as a supported Composer command.
- No canonical Guardian Discovery Intent exists.
- No deterministic discovery ladder currently resolves ambiguous task intent across local context, connectors, and read-only Pi discovery.
- No canonical Guardian Task Proposal schema exists.
- No confidence model separates reference confidence, intent confidence, and execution readiness.
- No complete runtime loop has been proven from vague user intent through discovery, proposal, approval, structured Task Spec, execution, and result return.
- This specification does not authorize autonomous dispatch or widen release support.

## Product semantics

`/pi-task <request>` means:

> Guardian, treat this authored text as a task-intent candidate. Orient yourself, investigate what it refers to, and return a grounded proposal for human review.

It does not mean:

> Send this string to Pi.

The first durable output of `/pi-task` is a Guardian-owned discovery and proposal record, not an AgentRun.

## Identity model

The following identities must remain separate:

1. **Authored Message**
   - The exact user-authored request stored in the source thread.
   - Preserved as lineage and conversational truth.

2. **Guardian Discovery Intent**
   - Guardian-owned record that a user asked for task interpretation and discovery.
   - Carries source lineage, discovery posture, ambiguity state, and evidence references.

3. **Discovery Request**
   - One bounded retrieval or investigation action issued by Guardian.
   - May target local retrieval, an authorized connector, or a read-only Pi discovery lane.

4. **Guardian Task Proposal**
   - Reviewable synthesis of what Guardian believes the user means and what should happen next.
   - Not executable authority.

5. **Approved Task Spec**
   - Human-approved, bounded execution contract containing goal, scope, acceptance criteria, validation, non-goals, review posture, permissions, and lineage.

6. **Coding Work Order**
   - Canonical atomic implementation unit derived from the approved Task Spec when the execution path requires one.

7. **AgentRun / Execution Attempt**
   - One execution attempt under a selected execution channel.

8. **Native Pi or Codex Session**
   - Channel-native execution identity beneath Guardian governance.

9. **Guardian Result Envelope**
   - Normalized outcome, evidence, validation, review posture, and remaining human action.

10. **Source-Thread Result Message**
    - Bounded user-visible return artifact.

No implementation may collapse these identities into one generic task ID.

## Canonical lifecycle

```text
RECEIVED
  -> ORIENTING
  -> RETRIEVING
  -> DISCOVERY_REQUIRED
  -> DISCOVERING
  -> PROPOSAL_READY
  -> AWAITING_CLARIFICATION or AWAITING_APPROVAL
  -> TASK_SPEC_APPROVED
  -> DISPATCHABLE
```

Terminal non-execution outcomes:

```text
NO_MATCH
INSUFFICIENT_CONTEXT
DISCOVERY_UNAVAILABLE
DECLINED
CANCELLED
SUPERSEDED
```

`NO_MATCH` is an honest discovery result, not an execution failure.

## Discovery ladder

Guardian must escalate through evidence sources gradually and record why each source was used.

### Stage 1: Interpret the authored request

Guardian extracts provisional signals only:

- possible goal
- named entities
- likely subsystem
- possible action
- ambiguity markers
- possible workflow, issue, document, symbol, test fixture, command alias, or prior decision references

Guardian must not create execution authority at this stage.

### Stage 2: Search available local context

Guardian should inspect the closest and cheapest context first:

1. selected source message
2. active thread frame when needed
3. selected Project KB
4. current-state and architecture corpus
5. known workflows, task definitions, and campaign artifacts
6. linked documents and attachments
7. indexed repository knowledge
8. recent project-scoped decisions or workstream state when available

Every included source must be recorded in `context_basis` with:

- `source_type`
- `source_id`
- `included_fields`
- `reason`
- `confidence`
- `policy_allowed`

### Stage 3: Assess understanding

Guardian must keep at least three distinct assessments:

- `reference_confidence`: Did Guardian identify what the user was referring to?
- `intent_confidence`: Does Guardian understand the outcome the user appears to want?
- `execution_readiness`: Is there enough grounded information to propose bounded work?

These values must not be collapsed into one confidence score.

Example:

```text
reference_confidence: high
intent_confidence: medium
execution_readiness: blocked
```

### Stage 4: Retrieve from authorized connectors

When local context is insufficient, Guardian may consult an authorized connector such as GitHub, Notion, Obsidian, Drive, or another approved source.

Guardian must record:

- connector identity
- bounded retrieval purpose
- query or lookup shape
- records matched
- records rejected
- whether the evidence changed the interpretation
- any connector failure or scope limitation

Connector consultation is retrieval, not execution.

### Stage 5: Delegate read-only discovery to Pi

When the missing information lives inside the codebase and local retrieval cannot resolve it, Guardian may create a bounded Pi Discovery Request.

A Pi Discovery Request must be read-only by default.

Allowed operations may include:

- repository search
- file reads
- symbol and dependency inspection
- bounded read-only git history inspection

Prohibited operations by default:

- file writes
- package installation
- network access
- commits
- branches
- implementation
- task dispatch
- recursive delegation

The discovery request must return:

- possible matches
- evidence paths and symbols
- confidence by match
- unresolved ambiguity
- recommended clarification question
- a receipt proving what was inspected

Pi answers Guardian. Pi does not answer the user directly.

### Stage 6: Synthesize a Guardian Task Proposal

Guardian combines authored intent, local retrieval, connector evidence, and optional Pi discovery into a reviewable proposal.

The proposal must not execute automatically, even when confidence is high.

## Guardian Task Proposal contract

A proposal should contain at minimum:

- `proposal_id`
- `discovery_intent_id`
- `thread_id`
- `source_message_id`
- `interpreted_goal`
- `probable_target`
- `evidence_summary`
- `context_basis`
- `reference_confidence`
- `intent_confidence`
- `execution_readiness`
- `assumptions`
- `unresolved_questions`
- `proposed_scope`
- `proposed_files_or_surfaces`
- `acceptance_criteria`
- `validation_requirements`
- `non_goals`
- `architecture_impact`
- `recommended_execution_channel`
- `requested_permission_posture`
- `human_decision_required`
- `created_at`
- `supersedes_proposal_id` when applicable

The proposal is reviewable planning state, not execution authority.

## Human decision outcomes

The user must be able to:

- approve the proposal
- edit or redirect the proposal
- ask Guardian to investigate further
- answer a clarification question
- decline the proposal
- cancel the discovery intent

Only an approved proposal may become an executable Task Spec.

## Example behavior

### No meaningful match

Input:

```text
/pi-task peanut butter donuts
```

Expected behavior:

Guardian searches relevant local context and available records. If no grounded match exists, Guardian should report the effort honestly and ask one targeted clarification question.

Example response:

> I checked the active project context, known workflows, architecture records, and repository references for “peanut butter donuts.” I did not find a grounded match, so I have not created an executable task. Did you mean a new feature, a name for an existing workflow, or a phrase from something we discussed elsewhere?

### Possible but uncertain match

If Guardian finds several weakly related records, it should summarize the strongest candidate and propose a bounded next discovery step.

Example:

> I found one possible connection: the repository contains `PeanutButterPipeline`, and an older test fixture uses “donut” as a sentinel payload. The evidence is not strong enough to assume they are what you meant. My proposed next step is a read-only inspection of that pipeline and its fixture tests. Is that the area you meant?

### Strong match

If Guardian finds a strong workflow or project match, it still presents a proposal rather than executing.

Example:

> I found a strong match in the project workflow registry and linked regression notes. The phrase maps to the import-write verification workflow. I prepared a proposed task with scope, acceptance criteria, validation, and a recommended Pi execution posture. Nothing has been executed.

A strong match does not equal confirmed intent, approval, or execution authority.

## Task Spec transformation boundary

The user-authored text may be preserved as source lineage, but it must not become the downstream Pi or Codex prompt verbatim.

Guardian must produce a structured, bounded Task Spec containing at minimum:

- Task Spec identity and version
- source lineage
- approved goal
- explicit scope
- permitted files or surfaces
- acceptance criteria
- validation commands or proof requirements
- non-goals
- permission posture
- review posture
- execution-channel identity
- provider/model identity when resolved
- required result and evidence shape

The execution system receives the Task Spec, not the raw user message.

## Composer semantics

The preferred initial command is:

```text
/pi-task <request>
```

Rules:

- The authored request is persisted before discovery begins.
- The `/pi-task` control token may be stored as command metadata, but it should not pollute the clean task text used by Guardian.
- The Composer never calls Pi, Codex, a worker, or the raw coding execution route directly.
- The Composer creates or requests a Guardian Discovery Intent.
- Normal chat completion should not race the discovery flow unless explicitly designed as a separate response lane.
- Discovery is non-blocking; the user may continue ordinary conversation.
- No provider or model picker is required in the Composer.
- Empty `/pi-task` requests must fail locally without creating discovery or execution records.

A future action-menu item may insert the `/pi-task ` scaffold, but it must not dispatch work directly.

## Evidence and observability

The operator-visible proof surface should expose:

- source message identity
- discovery intent identity
- discovery stage
- sources consulted
- connectors consulted
- Pi discovery invocation identity when used
- match candidates and confidence
- rejected candidates when relevant
- proposal identity
- unresolved questions
- human decision state
- approved Task Spec identity
- execution channel and run identity only after approval

Diagnostics must remain separate from conversational truth. Raw connector payloads, hidden prompts, secrets, personal context, and harness-internal logs must not be dumped into the primary chat lane.

## Invariants

- Users author intent; Guardian authors tasks.
- Raw user text is lineage, not execution authority.
- Guardian must investigate before proposing execution when meaning is uncertain.
- Guardian must expose uncertainty rather than fabricate understanding.
- Guardian may be eager without pretending certainty.
- Local orientation precedes connector retrieval when appropriate.
- Connector retrieval precedes codebase discovery when cheaper, sufficient, and policy-allowed.
- Pi discovery is read-only by default.
- Pi and Codex never receive broader authority than the approved Task Spec.
- Discovery, proposal, approval, execution, validation, visibility, and completion remain separate states.
- A strong retrieval match does not authorize execution.
- Human approval is required before the first write-capable implementation path.
- No autonomous recursive dispatch.
- No prompt-only authority.
- No personal-fact or broad-chat-history leakage into coding tasks.
- No hidden context widening.
- No release-claim widening from this specification.

## Relationship to Workstreams

A future Workstream may contain Guardian Discovery Intents, Discovery Requests, Task Proposals, approved Task Specs, runs, evidence, decisions, and outcomes for one continuing objective.

This specification does not implement Workstreams. It defines one planning and interpretation loop that a future Workstream could host.

## Candidate implementation stages

1. Define canonical discovery, proposal, confidence, and Task Spec schemas.
2. Add a read-only local discovery service over current thread, Project KB, and architecture corpus.
3. Add connector-backed discovery with explicit context-basis records.
4. Add a read-only Pi Discovery Request lane.
5. Add proposal persistence and human review actions.
6. Transform approved proposals into immutable Task Specs.
7. Connect approved Task Specs to Pi or Codex execution channels.
8. Prove exact lineage and result return end to end.
9. Only then consider bounded automation for low-risk discovery or proposal generation.

## ADR posture

Classification: No new ADR impact yet.

This specification aligns with existing Guardian authority, Orientation Layer, Context Command, delegation, Pi invocation, and three-channel execution topology decisions. It records desired future behavior without changing runtime semantics.

A new or superseding ADR is required if implementation would:

- make raw authored text executable authority
- allow Composer-to-executor dispatch
- collapse discovery and execution identities
- introduce a second control plane
- allow automatic execution from retrieval confidence alone
- change Guardian ownership of policy, lineage, approval, or result return

## Proof gate before execution integration

Execution integration must remain blocked until Codexify can prove:

1. a vague or partial `/pi-task` request is persisted with source lineage
2. Guardian searches local context and records context basis
3. insufficient local context triggers bounded connector retrieval or read-only Pi discovery
4. no-match and uncertain-match outcomes produce honest clarification rather than fabricated understanding
5. a strong match produces a proposal, not an execution attempt
6. a human can inspect, revise, approve, or decline the proposal
7. approval creates an immutable Task Spec distinct from the authored message
8. Pi or Codex receives the Task Spec, not the raw user text
9. the resulting execution preserves run, artifact, validation, and result lineage
10. exactly one bounded result returns to the source thread

Until this gate passes, `/pi-task` remains specification and architecture-discovery material only.

## Non-goals

- No runtime implementation
- No route implementation
- No Composer implementation
- No schema or migration
- No connector implementation
- No Pi SDK invocation
- No Codex invocation
- No automatic task execution
- No automatic approval
- No provider or model UI
- No autonomous recursion
- No Workstream runtime
- No release-readiness claim
