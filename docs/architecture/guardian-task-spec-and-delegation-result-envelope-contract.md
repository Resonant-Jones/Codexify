# Guardian Task Spec and Delegation Result Envelope Contract

> Classification: architecture-impact contract aligned with ADR-048
>
> Status: normative documentation; runtime implementation deferred
>
> Evidence posture: documented contract with code-path mapping

## Purpose and boundary

This document defines the shared outer contracts that Guardian will use to
delegate bounded work to the Pi, Codex, and Claude execution channels:

1. the outbound **Guardian Task Spec**; and
2. the inbound **Guardian Delegation Result Envelope**.

The contracts preserve Guardian authority, scope, lineage, review posture,
normalized return, and durable recordkeeping while allowing each execution
channel to keep its own plans, sessions, tools, subagents, retries, and native
receipt formats.

This contract is aligned with [ADR-048: Guardian Three-Channel Delegation
Topology](./adr/ADR-048-guardian-three-channel-delegation-topology.md) and
[ADR-020: Guardian Mediated Coding Agent Execution
Contract](./adr/020-guardian-mediated-coding-agent-execution-contract.md).
It does not implement runtime behavior, adapters, routing, queues, workers,
providers, persistence, migrations, runtime tokens, or supported-release
changes. Native Codex and native Claude delegation remain unshipped, and
end-to-end Guardian delegation remains outside the supported beta release
promise.

The field names and values below are contract vocabulary. They are not a
machine-readable schema and are not an authorization mechanism by themselves.
Future implementation work must add executable validation at the Guardian
boundary.

## Authority, nodes, and trust boundaries

### Authority order

Human authority remains above Guardian. Guardian owns delegation policy,
execution-channel selection, authoritative scope, lineage, review posture,
normalized result return, and durable records. An execution channel receives
bounded authority for one Task Spec; it does not receive Guardian authority.

For short-horizon release claims, `docs/architecture/00-current-state.md`
remains authoritative. This contract cannot widen the release promise merely
by defining a future interface.

Where runtime persistence exists, the durable store (currently Postgres-backed
where applicable) remains the record of truth; Redis queues and task/agent
events remain operational projections and must not be treated as the sole
acceptance or lineage surface. A direct human session in Codex or Claude is not
a Guardian-owned delegation unless it is imported through a separately
governed handoff that supplies the required Task Spec and lineage.

### Nodes

The minimal future delegation network is:

- a source thread, message, turn, campaign, work-order, or equivalent request
  record;
- Guardian intake and policy evaluation;
- durable storage for the Task Spec, result envelope, lineage, and evidence;
- queue/event transport and a bounded worker or orchestration process;
- one selected execution channel: Pi, Codex, or Claude;
- an optional repository, workspace, worktree, or other bounded mutation
  surface; and
- a human reviewer when the Task Spec requires review.

These nodes are architectural boundaries, not proof that the full network is
currently deployed or supported.

### Trust boundaries and threat model

The relevant boundaries are:

- human or source-request boundary to Guardian policy;
- Guardian to queue, worker, and persistence infrastructure;
- Guardian to the selected execution channel;
- execution channel to the repository, workspace, shell, network, or
  worktree; and
- returned evidence to Guardian normalization and human review.

The baseline threat model is an honest-but-buggy or partially failing channel,
stale queue visibility, missing lineage, scope drift, ambiguous native status,
and evidence that cannot be attributed. A malicious or compromised channel is
also not allowed to widen its authority: enforcement must eventually live at
Guardian and filesystem/identity boundaries, not in prompt wording.

What breaks first is intentionally explicit: route or queue acceptance may
precede execution, execution may precede visible events, a native success may
still fail Guardian validation, and an artifact may exist without a safe
source-thread return. Each phase therefore has separate evidence and no phase
implicitly proves the next one.

## Canonical terminology

| Term | Normative meaning |
| --- | --- |
| **Guardian Task Spec** | The Guardian-authored outbound contract that declares one bounded delegation's identity, authority, scope, expected evidence, review posture, and return destination. Use `Task Spec` consistently for this object. |
| **Task Spec identity** | The identity of one immutable Task Spec revision. It is represented by `task_spec_id`, bound to its immutable projection, and is distinct from a run, attempt, queue task, channel session, or result envelope. |
| **Task Spec immutable projection** | The deterministic projection of Guardian-owned authorization and provenance fields that defines what the delegation is allowed to do and what evidence it must return. Runtime progress and channel-native evidence are excluded. |
| **Task Spec hash or binding** | A cryptographic content binding, represented in this contract by `task_spec_hash`, over the versioned immutable projection. The hash is not a substitute for Guardian policy validation. |
| **Delegation identity** | The stable identity of the Guardian-authorized handoff, represented by `delegation_id`; it ties a Task Spec revision, one selected channel, and the resulting evidence together. A retry may have a new attempt identity while remaining linked to the delegation. |
| **Execution channel** | A governed peer execution lane selected by Guardian: `pi`, `codex`, or `claude` at the architecture-contract level. These values do not claim that the corresponding runtime is shipped. |
| **Execution-system identity** | The identity and version of the system that owns the native execution strategy, such as a Pi, Codex, or Claude execution system. It is not the model or provider identity. |
| **Underlying model identity** | The model or provider identity used by an execution system when it is declared or known. It is evidence and policy context, not execution-system identity or Guardian authority. |
| **Channel-declared metadata** | Capability, version, environment, or diagnostic metadata supplied by a channel. It may enrich evidence but may not override Guardian-owned fields. |
| **Channel-native evidence** | Plans, prompts, tool records, subagent records, sessions, receipts, logs, patches, commits, status strings, and validation output produced by the selected channel. It remains attributable to that channel. |
| **Guardian Delegation Result Envelope** | The normalized inbound contract that carries a channel result, preserves native evidence, records Guardian normalization, and gives Guardian enough information to accept, reject, block, or escalate the result. |
| **Lifecycle status** | The normalized execution-attempt axis defined in this contract: `accepted`, `queued`, `running`, `completed`, `blocked`, `failed`, `cancelled`, `timed_out`, or `rejected`. |
| **Review posture** | The separate human/Guardian review axis: `not_evaluated`, `not_required`, `required`, `pending`, `accepted`, `changes_requested`, or `rejected`. |
| **Mutation posture** | The declared boundary for whether and how the channel may write, mutate, commit, push, merge, or affect release state. |
| **Validation evidence** | Structured evidence that the declared validation contract was run, not run, failed, or was otherwise incompatible, including commands, outcomes, attempts, and bounded diagnostics. |
| **Result-return destination** | The Guardian-owned destination and delivery policy for the normalized result, such as a source thread/message, durable run record, artifact record, operator surface, or explicit future consumer. |
| **Source lineage** | References from the delegation back to the request that authorized it, including source request, thread, message, turn, campaign, work-order, actor, and project references when applicable. |
| **Result lineage** | References from the returned envelope to the exact Task Spec, delegation, attempt, native run/session, artifact, validation, commit, and return destination that produced or carried the result. |
| **Guardian acceptance** | A separate Guardian review decision about whether the returned result satisfies the Task Spec and may proceed to the declared destination. It is not the same as lifecycle `completed` or review posture `accepted`. |

## Field ownership, requirement, and mutability

### Ownership classes

| Class | Owner | Rule |
| --- | --- | --- |
| **Guardian-owned authoritative field** | Guardian | Guardian creates, validates, and persists the field. A channel must not rewrite it or infer a broader value from it. |
| **Channel-declared metadata** | Selected execution channel, recorded by Guardian | The channel may declare metadata about its capabilities, version, native state, or environment. Guardian may reject contradictory metadata; it never becomes authorization merely because the channel supplied it. |
| **Channel-native evidence** | Selected execution channel, preserved by Guardian | Native plans, sessions, receipts, logs, patches, commits, and validation output remain evidence from their originating channel. Normalization must not erase origin or turn evidence into authority. |
| **Immutable delegation identity** | Guardian | `task_spec_id`, `delegation_id`, the immutable Task Spec projection, and its binding identify the exact authorization version. They do not change during execution. |
| **Runtime-mutable execution state** | Guardian result/persistence layer, informed by the channel | Queue state, lifecycle progress, timestamps, retry counters, cancellation, timeout, delivery, normalization, and review state may change only through governed transitions and durable records. They do not amend authorization. |

### Requirement levels

- **Required** means the field must be present, even when its value is an
  explicit empty, `none`, `not_applicable`, or `not_evaluated` value.
- **Conditionally required** means the field is required when the stated
  condition applies. The condition must be evaluated by Guardian, not silently
  assumed by the channel.
- **Optional** means the field may be omitted when unavailable, but a supplied
  value must remain attributable and schema-valid.

An explicitly empty field is not permission to use ambient authority. For
example, an empty `allowed_paths` set means no repository path is authorized,
not “all paths.” A Task Spec with missing scope, identity, lineage, review, or
validation semantics fails closed.

### Mutability classes

- **Immutable**: participates in the Task Spec identity or binding and cannot
  change within a delegation attempt.
- **Runtime-mutable**: may change only through Guardian-owned lifecycle or
  review transitions and must retain history where durable state exists.
- **Append-only evidence**: may be added as new attributable evidence but may
  not overwrite the original native record.
- **Derived**: computed by Guardian from immutable fields or preserved
  evidence; it is not an authority source and must be reproducible or explained.

Channel-declared metadata may be append-only evidence. It never changes the
immutable projection. If a channel needs a changed scope, acceptance criterion,
permission, or non-goal, it must stop and request a new Guardian-authored Task
Spec revision or delegation attempt.

## Guardian Task Spec

### Contract rules

Guardian creates or validates the Task Spec before the selected channel sees
the bounded request. The Task Spec is independent of channel-native plans,
sessions, tools, subagents, and receipts. A channel may choose any internal
execution strategy that remains inside the declared boundary.

The Task Spec must make authority explicit rather than relying on ambient
repository access, provider defaults, shell configuration, prompt language, or
the channel's own interpretation of “safe.” Guardian must preserve the source
request and expected result destination even when the channel is offline,
degraded, cancelled, or unable to return native evidence.

### Normative Task Spec field table

The following table is normative. Nested field names identify the intended
semantic home; they do not prescribe a serializer.

| Field name | Requirement | Authority owner | Mutability | Purpose | Validation or failure rule |
| --- | --- | --- | --- | --- | --- |
| `task_spec_id` | Required | Guardian | Immutable | Identifies this immutable Task Spec revision. | Missing, duplicated, or reused for a changed projection fails closed. |
| `schema_version` | Required | Guardian | Immutable | Identifies the contract revision used to interpret the fields. | Unknown or unsupported version is rejected; do not guess. |
| `task_spec_revision` | Required | Guardian | Immutable | Orders revisions for one logical delegation request. | A changed revision must receive a new immutable identity and binding. |
| `delegation_id` | Required | Guardian | Immutable | Binds this Task Spec to one Guardian delegation. | Must be stable for the handoff and distinct from run/attempt/session IDs. |
| `source_request_identity` | Required | Guardian | Immutable | Identifies the authored request or accepted source request record. | Must resolve to an authorized source or the Task Spec is rejected. |
| `source_lineage.thread_id` | Conditionally required | Guardian | Immutable | Identifies the originating thread when the request is thread-bound. | Missing or ambiguous thread lineage blocks a thread-bound return. |
| `source_lineage.message_id` | Conditionally required | Guardian | Immutable | Identifies the authored message that seeded the delegation. | Must remain distinct from request and attempt identity. |
| `source_lineage.turn_id` | Conditionally required | Guardian | Immutable | Identifies the logical turn or request boundary when available. | A supplied value must match the source request record. |
| `source_lineage.campaign_id` | Conditionally required | Guardian | Immutable | Links campaign-owned work when applicable. | Must resolve to the declared campaign scope. |
| `source_lineage.work_order_id` | Conditionally required | Guardian | Immutable | Links a work order when applicable. | Must resolve to the work-order scope and owner. |
| `source_lineage.project_id` | Conditionally required | Guardian | Immutable | Links project ownership when applicable. | Project scope must not be inferred from a path alone. |
| `source_lineage.actor_subject` | Required | Guardian | Immutable | Records the acting user or authority subject. | Missing actor binding fails closed; do not use display text as identity. |
| `selected_execution_channel` | Required | Guardian | Immutable | Selects the peer channel bounded by this contract. | Must be an explicitly registered future channel; unknown values are rejected. |
| `execution_system_identity` | Required | Guardian and selected channel | Immutable | Identifies the execution system and declared system version. | Must remain distinct from `underlying_model_identity`; ambiguity requires review or rejection. |
| `underlying_model_policy` | Required | Guardian | Immutable | Declares whether model identity is fixed, policy-selected, channel-selected, or unavailable. | The policy must not imply a model is available when it is not proven. |
| `underlying_model_identity` | Conditionally required | Channel, recorded by Guardian | Immutable evidence | Records the model/provider identity when known. | Unknown is allowed only when the policy says so; never substitute it for execution-system identity. |
| `goal` | Required | Guardian | Immutable | States the bounded outcome sought. | Empty or materially ambiguous goals are rejected or clarified before dispatch. |
| `authorized_repository_or_workspace` | Required | Guardian | Immutable | Names the repository, workspace, or read-only context boundary. | Must be explicit; absence is not permission for the channel's current directory. |
| `repository_identity` | Conditionally required | Guardian | Immutable | Records repository identity, remote identity, or equivalent ownership when known. | If supplied, it must match the expected repository or the attempt is blocked. |
| `expected_code_reference` | Conditionally required | Guardian | Immutable | Pins an expected branch, commit, tag, or source revision when relevant. | Drift from the expected reference requires an explicit Guardian decision. |
| `allowed_paths` | Required | Guardian | Immutable | Lists the only paths the channel may inspect or mutate for this Task Spec. | Missing scope or unbounded wildcard fails closed; empty means no path authority. |
| `forbidden_paths` | Required | Guardian | Immutable | Lists explicit exclusions inside or adjacent to the workspace boundary. | A change or access crossing an exclusion is a scope violation. |
| `requirements` | Required | Guardian | Immutable | Lists implementation or analysis requirements. | A channel must not add requirements that expand scope. |
| `acceptance_criteria` | Required | Guardian | Immutable | Defines observable conditions for Guardian review. | Missing, contradictory, or channel-rewritten criteria fail closed. |
| `validation_contract` | Required | Guardian | Immutable | Declares commands, checks, evidence classes, or an explicit no-validation posture. | A required validation that is absent, incompatible, or unproven blocks acceptance. |
| `non_goals` | Required | Guardian | Immutable | States work the channel must not perform or claim. | A channel may not silently remove or weaken a non-goal. |
| `architecture_impact_classification` | Required | Guardian | Immutable | Records standard, architecture-impact, proof, or other approved task classification. | Architecture-impact work requires the applicable ADR/review posture. |
| `risk_classification` | Required | Guardian | Immutable | Records scope, identity, mutation, release, or other relevant risk. | Unknown risk is not treated as low risk. |
| `human_review_posture` | Required | Guardian | Immutable | Declares whether and when human review is required. | Required review cannot be cleared by native success or a commit alone. |
| `mutation_posture` | Required | Guardian | Immutable | Declares read-only, bounded-write, isolated-write, or other approved mutation mode. | Any mutation outside the declared mode is a violation. |
| `permission_posture.allow_network` | Required | Guardian | Immutable | Grants or denies network access for the attempt. | A channel must not use network access when false or unspecified. |
| `permission_posture.allow_shell` | Required | Guardian | Immutable | Grants or denies shell/command execution. | A required validation cannot be treated as run when shell permission is denied. |
| `permission_posture.allow_write` | Required | Guardian | Immutable | Grants or denies workspace writes. | Any write when false is a mutation violation. |
| `permission_posture.allow_commit` | Required | Guardian | Immutable | Grants or denies creating commits. | A native commit without authority is rejected as evidence of scope drift. |
| `permission_posture.allow_push` | Required | Guardian | Immutable | Grants or denies pushing refs. | Push is never implied by write or commit permission. |
| `permission_posture.allow_merge` | Required | Guardian | Immutable | Grants or denies merge actions. | Merge permission does not remove required human review. |
| `permission_posture.allow_release` | Required | Guardian | Immutable | Grants or denies release or deployment actions. | Release permission is not inferred from merge or validation success. |
| `timeout_posture` | Required | Guardian | Immutable | Declares deadline, timeout behavior, and required timeout evidence. | A timeout must not be normalized as completion without evidence. |
| `retry_posture` | Required | Guardian | Immutable | Declares retry budget, backoff, idempotency, and whether a retry is a new attempt. | Retries cannot expand authority or mutate the existing Task Spec. |
| `cancellation_posture` | Required | Guardian | Immutable | Declares who may cancel, how cancellation is recorded, and expected evidence. | Cancellation must remain distinguishable from failure and timeout. |
| `expected_artifacts` | Required | Guardian | Immutable | Names the artifact classes or references expected from the channel. | Missing required artifacts block or escalate the result. |
| `expected_proof_surfaces` | Required | Guardian | Immutable | Declares which checks, receipts, logs, diffs, or live surfaces can prove each criterion. | A proof surface cannot be replaced by an unrelated success signal. |
| `result_return_destination` | Required | Guardian | Immutable | Names the durable and user-facing destinations for a result. | An orphaned or ambiguous destination blocks final return. |
| `creation_provenance` | Required | Guardian | Immutable | Records who/what authored the Task Spec, source revision, and approval context. | Missing provenance prevents trustworthy attribution. |
| `created_at` | Required | Guardian | Immutable | Records Task Spec creation time in a machine-readable form. | Invalid or missing time prevents deterministic ordering/audit. |
| `supersedes_task_spec_id` | Conditionally required | Guardian | Immutable | Links a revised Task Spec to the prior revision. | A changed scope without a new linked revision is rejected. |
| `channel_declared_metadata` | Optional | Selected channel, recorded by Guardian | Append-only evidence | Carries declared capability, version, environment, or native setup information. | It may enrich evidence but may not override any Guardian-owned field. |
| `task_spec_hash` | Required | Guardian | Derived immutable binding | Binds the canonical immutable projection to a cryptographic digest. | The digest must verify against the declared versioned projection; future implementations must reject mismatch. |

### Immutable projection and binding

The immutable projection includes every Guardian-owned field above except:

- `channel_declared_metadata`, which is channel evidence and may be appended
  without changing authorization; and
- runtime observations, progress, timestamps after creation, event delivery,
  retry counters, cancellation outcomes, timeout observations, result data,
  review decisions, and native evidence generated after dispatch.

`task_spec_hash` is computed over the canonical immutable projection without
including the hash field itself. Future implementations must use a
deterministic, versioned canonical serialization and a cryptographic content
binding. This task intentionally does not prescribe JSON canonicalization,
field ordering, a hash algorithm, or an executable serializer. A future
machine-readable schema and token-registration task must make those choices
explicit and test them.

The identity is therefore:

```text
Task Spec identity = (task_spec_id, task_spec_revision, schema_version, task_spec_hash)
```

An implementation may add a stronger binding, but it must preserve this
distinction between the logical delegation, the immutable revision, and the
runtime attempt.

## Task Spec amendment rules

1. An execution channel may not amend the Task Spec.
2. A scope expansion, permission change, acceptance change, new non-goal, or
   changed result destination requires a new Guardian-authored revision or a
   new delegation attempt with a new immutable identity and hash.
3. Evidence from an older Task Spec remains bound to that exact
   `task_spec_id`, revision, and hash. It must not be silently reattached to a
   newer authorization.
4. Timeout, cancellation, retry, and clarification events do not silently
   mutate immutable authorization. They change runtime state or create a new
   attempt only through Guardian-owned transitions.
5. A clarification that changes scope, permissions, or acceptance criteria is
   not an in-place clarification. It requires a new Guardian-approved Task
   Spec revision and an explicit supersession link.
6. Native plans, tool choices, sessions, subagents, patches, commits, and
   intermediate artifacts may change within the bounded attempt, but they do
   not change the Task Spec.

## Guardian Delegation Result Envelope

### Contract rules

Every returned result must identify the exact Task Spec version it claims to
implement. Guardian normalizes lifecycle and review axes while preserving the
native status, originating channel, native identifiers, and native evidence.
The envelope is not a promise that the channel's result is correct; it is the
minimum attributable evidence surface on which Guardian can make a review
decision.

### Normative result-envelope field table

| Field name | Requirement | Authority owner | Mutability | Purpose | Validation or failure rule |
| --- | --- | --- | --- | --- | --- |
| `delegation_id` | Required | Guardian | Immutable | Links the envelope to the handoff identity. | Must match the Task Spec and durable delegation record. |
| `result_envelope_id` | Required | Guardian | Immutable | Identifies this returned envelope version. | Missing or duplicate identity fails closed. |
| `schema_version` | Required | Guardian | Immutable | Identifies the result contract revision. | Unknown or unsupported version is rejected. |
| `task_spec_id` | Required | Guardian | Immutable | Identifies the authorization claimed by the result. | Must match the selected Task Spec exactly. |
| `task_spec_hash` | Required | Guardian | Immutable | Verifies the result against the exact immutable Task Spec binding. | Mismatch, omission, or unverifiable binding blocks acceptance. |
| `selected_execution_channel` | Required | Guardian, preserved from channel | Immutable | Records the channel that executed or attempted the work. | Must match the Task Spec; a channel cannot self-select a different authority lane. |
| `execution_system_identity` | Required | Guardian, declared by channel | Immutable evidence | Identifies the system that produced the native result. | Must remain separate from the model identity and be attributable. |
| `underlying_model_identity` | Conditionally required | Channel, recorded by Guardian | Append-only evidence | Records the model/provider identity when available. | Unknown is allowed only with an explicit unavailable reason; never invent one. |
| `native_run_id` | Conditionally required | Selected channel | Immutable evidence | Links to the channel's native run when one exists. | Must be preserved without being mistaken for `delegation_id` or `task_spec_id`. |
| `native_thread_id` | Optional | Selected channel | Immutable evidence | Preserves a channel-native thread when one exists. | Must remain channel-scoped and attributable. |
| `native_session_id` | Optional | Selected channel | Immutable evidence | Preserves a channel-native session when one exists. | A session ending is not by itself completion or acceptance. |
| `native_campaign_id` | Optional | Selected channel | Immutable evidence | Preserves a channel-native campaign identity when one exists. | Must not replace Guardian campaign lineage. |
| `native_attempt_id` | Conditionally required | Selected channel | Immutable evidence | Identifies the channel-native attempt when available. | Must map to the Guardian attempt without collapsing identities. |
| `attempt` | Required | Guardian | Runtime-mutable until terminal | Records Guardian attempt number, retry relationship, and idempotency key. | A retry must remain attributable and must not reuse immutable authorization incorrectly. |
| `lifecycle_status` | Required | Guardian normalization | Runtime-mutable until terminal | Carries the normalized lifecycle vocabulary. | Must be one of the canonical values and obey terminality rules. |
| `native_status` | Required | Selected channel, preserved by Guardian | Append-only evidence | Preserves the original channel state, including unknown or native review states. | Never overwrite the native value with the normalized value. |
| `status_mapping` | Required | Guardian and adapter | Derived plus provenance | Records adapter identity, mapping version, mapping outcome, and source. | Unknown or ambiguous mapping must fail closed and may not become `completed`. |
| `summary` | Required | Channel, normalized by Guardian | Append-only/derived | Gives a bounded human-readable account of the result or stop. | Empty summaries require an explicit error/stop reason. |
| `changed_paths` | Conditionally required | Channel, verified by Guardian | Append-only evidence | Lists paths changed or reported as changed. | Required for mutating work; paths outside scope cause rejection or blocked review. |
| `commit_hashes` | Conditionally required | Channel, verified by Guardian | Append-only evidence | Records commits attributable to the attempt. | A commit without permission or attribution is a mutation finding, not approval. |
| `patch_references` | Optional | Channel, preserved by Guardian | Append-only evidence | References diffs, patch bundles, or bounded patch manifests. | References must be stable, attributable, and free of secrets. |
| `artifact_references` | Conditionally required | Channel, recorded by Guardian | Append-only evidence | Links expected and returned artifacts. | Missing expected artifacts block or escalate the result. |
| `receipt_references` | Optional | Channel, preserved by Guardian | Append-only evidence | Links native receipts or execution records. | A receipt is evidence, not Guardian acceptance. |
| `validation_results` | Conditionally required | Channel and Guardian validation | Append-only/derived | Carries structured validation evidence and its source. | Missing or incompatible required validation blocks acceptance. |
| `scope_findings` | Required | Guardian | Derived, append-only findings | Records allowed, changed, unverified, and out-of-scope path findings. | Unknown scope is not normalized as within scope. |
| `mutation_findings` | Required | Guardian | Derived, append-only findings | Records violations or verification of write, shell, commit, push, merge, or release posture. | A violation prevents unconditional acceptance. |
| `lineage_verification_findings` | Required | Guardian | Derived, append-only findings | Records whether source and result references resolve and remain consistent. | Missing or ambiguous lineage fails closed. |
| `errors` | Conditionally required | Channel and Guardian | Append-only evidence | Lists machine-readable and bounded error findings. | Required for failure, rejection, blocked, timeout, or mapping-failure outcomes. |
| `stop_reason` | Conditionally required | Channel, normalized by Guardian | Immutable once terminal | Explains why execution stopped or could not proceed. | Timeout, cancellation, scope rejection, lineage rejection, and execution failure remain distinct. |
| `timeout_evidence` | Conditionally required | Channel and Guardian | Append-only evidence | Records deadline, observed timeout, signal, and bounded evidence. | A claimed timeout without evidence is blocked or rejected. |
| `cancellation_evidence` | Conditionally required | Guardian and channel | Append-only evidence | Records actor, request, time, and observed cancellation outcome. | Cancellation must not be rewritten as failure or completion. |
| `retry_or_attempt_information` | Required | Guardian | Runtime-mutable until terminal | Records attempt number, prior attempt links, retry budget, and idempotency posture. | A retry cannot silently broaden scope or erase prior evidence. |
| `review_posture` | Required | Guardian | Runtime-mutable through review | Separates native execution outcome from human/Guardian review. | Must use the canonical review vocabulary; native success cannot set acceptance by itself. |
| `guardian_acceptance` | Required | Guardian | Runtime-mutable through review | Records whether Guardian accepted, rejected, blocked, or escalated the result. | Must be separate from `lifecycle_status` and native status. |
| `remaining_human_action` | Required | Guardian | Runtime-mutable | Names pending review, approval, clarification, repair, or other human action; explicit empty means none. | A required human action may not be hidden by `completed`. |
| `source_result_lineage` | Required | Guardian | Immutable references plus append-only verification | Connects source request, Task Spec, delegation, attempt, native execution, artifacts, and result. | Orphaned or ambiguous result lineage blocks return. |
| `result_return_destination` | Required | Guardian | Immutable declaration plus runtime delivery state | Identifies where Guardian may return or persist the result. | Delivery to an undeclared or mismatched destination is rejected. |
| `created_at` | Required | Guardian | Immutable | Records envelope creation time. | Missing or invalid timestamp prevents audit ordering. |
| `started_at` | Conditionally required | Guardian/channel | Immutable evidence | Records when native execution began. | A claimed run without start evidence remains partial or unknown. |
| `updated_at` | Required | Guardian | Runtime-mutable | Records the latest envelope update. | Must be monotonic for the durable record. |
| `terminal_at` | Conditionally required | Guardian | Immutable once terminal | Records terminal time for terminal statuses. | Non-terminal envelopes must not claim terminality. |
| `channel_native_evidence` | Required | Selected channel, preserved by Guardian | Append-only evidence | Carries or references native plans, sessions, tools, subagents, receipts, logs, patches, commits, and raw status. | It may be empty only with an explicit unavailable reason; origin must be retained. |
| `guardian_normalization_provenance` | Required | Guardian | Append-only/derived | Records normalizer, adapter, mapping version, validation time, and Guardian decision source. | Without normalization provenance, the envelope cannot be trusted as normalized. |

### Result acceptance boundary

Guardian may accept, reject, block, or escalate a returned result. It must
separate at least these decisions:

- **native execution status**: what the channel says happened;
- **normalized lifecycle**: how Guardian represents the attempt's progress or
  terminal outcome;
- **review posture**: whether Guardian or a human must evaluate the result; and
- **Guardian acceptance**: whether the result satisfies the Task Spec and may
  proceed to the declared destination.

`lifecycle_status=completed` means native execution completed or returned a
completion-like state after the adapter's explicit mapping. It does not mean
Guardian accepted the result, that a merge is approved, that a release is
ready, or that the supported beta promise changed.

## Lifecycle status and review posture

### Normalized lifecycle vocabulary

The contract-level lifecycle values are:

| Value | Terminal for represented attempt? | Meaning |
| --- | --- | --- |
| `accepted` | No | Guardian accepted the handoff for processing; this is not result acceptance. |
| `queued` | No | The bounded attempt is recorded for execution but has not started. |
| `running` | No | The attempt is executing or its liveness is still established. |
| `completed` | Yes | Native execution completed; review and Guardian acceptance remain separate. |
| `blocked` | Yes | The represented attempt cannot safely proceed, often because of clarification, permission, scope, lineage, or mapping ambiguity. A follow-up attempt may be created. |
| `failed` | Yes | Execution or validation failed after the applicable bounded policy. |
| `cancelled` | Yes | Guardian or an authorized actor cancelled the attempt, with cancellation evidence. |
| `timed_out` | Yes | The declared timeout posture was reached or timeout was otherwise verified. |
| `rejected` | Yes | Guardian rejected the handoff or returned evidence for scope, lineage, identity, binding, or policy non-conformance. |

`accepted`, `queued`, and `running` are non-terminal. `completed`, `blocked`,
`failed`, `cancelled`, `timed_out`, and `rejected` are terminal for the
represented attempt. Terminality does not imply success, approval, merge, or
release readiness.

### Review posture vocabulary

Review is a separate axis with these values:

- `not_evaluated`: Guardian has not yet made the review decision;
- `not_required`: the Task Spec explicitly permits no additional review;
- `required`: review is required by the Task Spec or a finding;
- `pending`: review has been requested or is waiting on a human/Guardian gate;
- `accepted`: review accepted the result for the declared next step;
- `changes_requested`: review requires a new bounded attempt or revision; and
- `rejected`: review rejected the result.

For example, a channel-native `needs_review` status maps to a normalized
`lifecycle_status=completed` when native execution has actually stopped, plus
`review_posture=required` or `pending`. It must not be treated as a new
lifecycle value, and it must not be flattened into `completed` with no review
signal. If the native state means execution is waiting and not finished,
Guardian may instead use `lifecycle_status=blocked` with the appropriate review
posture and stop reason.

These are contract-level canonical values only. Registration in
`guardian/protocol_tokens.py`, machine-readable schema work, persistence
constraints, and runtime emission are deferred to a future implementation Task
Spec. This document does not authorize new runtime tokens.

## Native-status mapping rules

Every future adapter must provide an explicit, versioned mapping from native
states into the normalized lifecycle and review axes. The mapping must include:

- the original `native_status`, unchanged;
- the adapter or normalizer identity;
- a `mapping_version` and mapping source;
- whether terminality was explicit, inferred, or unavailable;
- the resulting lifecycle and review values;
- preserved timeout, cancellation, scope, lineage, and validation evidence;
- a bounded reason for any rejection, block, or mapping failure.

The following rules are mandatory:

1. Preserve the original native status. Normalization adds a value; it does not
   replace the channel's truth.
2. Fail closed on unknown or ambiguous terminality. An unknown state must never
   map to `completed`.
3. If the adapter cannot establish a safe mapping, Guardian must preserve the
   native evidence and return a mapping failure as `blocked` or `rejected`,
   depending on whether the handoff or returned evidence is invalid. It must
   not present an uncertain state as successful execution.
4. Preserve timeout and cancellation evidence distinctly. A timeout is not a
   generic failure, and cancellation is not a timeout.
5. Preserve scope or lineage rejection distinctly from execution failure. A
   channel that was prevented from acting because its authority was invalid did
   not merely experience an execution error.
6. Treat a native `needs_review` or equivalent as a combination of lifecycle
   and review axes, not a reason to invent a fourth axis or hide review in a
   summary string.
7. Do not require Pi, Codex, and Claude to expose identical native states,
   internal plans, APIs, sessions, tools, subagents, or receipt formats.

### Illustrative mapping examples

| Native evidence | Normalized lifecycle | Review posture | Mapping note |
| --- | --- | --- | --- |
| `accepted` or `queued` | `accepted` or `queued` | `not_evaluated` | Handoff/queue state only; no execution completion claim. |
| `running` | `running` | `not_evaluated` | Liveness must remain attributable. |
| `succeeded` with complete native evidence | `completed` | `not_evaluated` or `required` | Native completion only; Guardian still checks scope, validation, and review. |
| `needs_review` after native execution stopped | `completed` | `required` or `pending` | Preserve native state and require review. |
| `waiting_for_permission` or unresolved clarification | `blocked` | `required` or `pending` | The attempt stops without widening authority. |
| `timed_out` with deadline evidence | `timed_out` | `not_evaluated` or `required` | Preserve deadline and timeout evidence. |
| `cancelled` with cancellation evidence | `cancelled` | `not_evaluated` or `required` | Preserve actor and cancellation request. |
| out-of-scope mutation or bad Task Spec binding | `rejected` | `rejected` | Authority or evidence failure, not ordinary execution failure. |
| adapter error after bounded execution | `failed` | `not_evaluated` or `required` | Preserve native errors and Guardian validation findings. |
| unknown or contradictory terminal state | `blocked` or `rejected` | `pending` or `rejected` | Fail closed; never map to `completed`. |

## Trust and Guardian acceptance rules

Guardian must reject, block, or escalate a result when any of the following is
true:

- `task_spec_id`, revision, or `task_spec_hash` does not match;
- a Guardian-owned field appears rewritten by the channel;
- changed paths exceed `allowed_paths` or enter `forbidden_paths`;
- the mutation posture was violated or cannot be verified;
- source or result lineage is missing, ambiguous, or inconsistent;
- required validation is missing, incomplete, incompatible, or only asserted
  by a summary;
- artifacts, patches, or commits cannot be attributed to the attempt;
- cancellation or timeout evidence conflicts with the claimed status;
- human review is required but absent;
- native evidence cannot be preserved or attributed to its originating channel;
- the result destination is missing, mismatched, or would create an orphaned
  publication; or
- the native-status mapping is unknown, ambiguous, or not versioned.

Guardian acceptance is a review decision, not a channel response. Native plans,
patches, commits, logs, session records, validation output, and a native
success-like state remain evidence. None establishes merge approval, release
readiness, or a wider supported runtime claim by itself.

## Current runtime mapping

The following matrix classifies existing structures as inputs to future
implementation. It does not rename, migrate, or declare any structure
compliant with this contract.

| Current structure | Classification | Reusable evidence or gap |
| --- | --- | --- |
| `guardian/agents/coding_agent_contracts.py::CodingAgentTaskEnvelope` | Reusable conceptually but incomplete | Carries Guardian-facing IDs, source thread/message, attempt, instructions, adapter, workspace, validation, permissions, worktree, commit, and review hints. It lacks the full immutable Task Spec projection, schema/revision identity, explicit forbidden paths, separate execution-system/model identity, full permission matrix, proof surfaces, and result destination. |
| `guardian/agents/coding_agent_contracts.py::CodingAgentPermissionPolicy` | Reusable conceptually but incomplete | Provides shell, network, write, allowed paths, and runtime bounds. It does not represent forbidden paths or separate commit, push, merge, release, timeout, retry, cancellation, and mutation posture. |
| `guardian/agents/coding_agent_contracts.py::CodingAgentResult` | Reusable conceptually but incomplete | Provides attempt status, summary, changed files, artifacts, errors, adapter session reference, and optional validation results. It lacks result-envelope identity, Task Spec binding, normalized review axis, native-status mapping, lineage verification, timeout/cancellation evidence, timestamps, and Guardian normalization provenance. |
| `guardian/agents/coding_agent_contracts.py::CodingAgentTaskStatus` | Incompatible with the shared contract as an authoritative lifecycle | Its `dispatching`, `failed_retryable`, and `failed_fatal` values are useful legacy/channel evidence, but it is not the canonical nine-value lifecycle and must not be aliased into it without an explicit mapping. |
| `guardian/routes/agent_orchestration.py::CodingExecutionRequest` | Reusable conceptually but incomplete | Shows current route intake fields and explicit validation/worktree/review controls. It is a runtime request model, not the shared immutable Task Spec and does not contain the full authority/lineage/proof/return contract. |
| Guardian deployment `spec_json` | Reusable conceptually but incomplete | Already persists Guardian-owned deployment context and adapter selection. Its shape is runtime-specific and may include mutable or legacy fields; it is not by itself the canonical immutable projection. |
| Current deployment `spec_hash` | Reusable conceptually but incomplete | Demonstrates bounded hashing of a selected runtime projection. It is not yet a binding over the finalized three-channel Task Spec projection and must not be treated as that identity. |
| `guardian/agents/test_results.py::NormalizedTestResult` | Reusable as-is for its bounded component | Provides structured validation evidence and bounded diagnostics. It is a validation field within the result envelope, not a complete result envelope or Guardian acceptance decision. |
| Coding-worker run and attempt identities | Reusable conceptually but incomplete | `run_id`, `coding_task_id`, `attempt_id`, queue task identity, and worker attempt counters provide runtime lineage. They must be mapped to, not conflated with, `delegation_id`, `task_spec_id`, and `result_envelope_id`. |
| Adapter session references | Reusable as-is as native evidence | `adapter_session_ref` can remain an attributable native-session reference. It cannot become Guardian task identity or durable truth without a separate storage contract. |
| Worktree and patch artifacts | Reusable as-is as bounded evidence | Worktree metadata, changed paths, patch manifests, hashes, and diff references are valuable scope/proof evidence. They do not imply merge, release, or Guardian acceptance. |
| Commit-after-green metadata | Reusable conceptually but incomplete | Commit hash, status, reason, merge-ready, and human-review fields can populate evidence and review findings. Commit-after-green is not merge approval and is not a release action. |
| `AgentStore.store_coding_result()` | Reusable conceptually but incomplete | It already persists result payloads, validation, artifacts, commit metadata, delivery state, and source-thread return attempts through Guardian. It must not be treated as the new envelope schema or migrated in this task. |
| Source-thread result return | Reusable conceptually but incomplete | Guardian-owned result injection and delivery status provide a result-return destination and provenance seam. Missing lineage or degraded delivery must remain visible rather than being treated as successful return. |
| Task and agent event streams | Reusable conceptually but incomplete | Events such as running, validation, retry, patch-artifact, completed, failed, and cancelled provide operational projections. They are not durable truth, Task Spec authority, or proof of user-visible receipt. |
| `guardian/protocol_tokens.py` status/event domains | Deferred to implementation | Existing runtime tokens must remain unchanged by this task. Future implementation must register contract-level lifecycle values only through a separate token/schema task with tests. |
| Machine-readable schema and persistence migration | Deferred to implementation | No JSON Schema, Pydantic model, database migration, consumer migration, or legacy alias removal is authorized here. |

The current Pi-compatible coding-worker substrate remains the compatibility
baseline. The existing `pi_codex_runner` alias is legacy-compatible runtime
state and must not be interpreted as shipped native Codex delegation.

## Illustrative non-executable skeletons

The following JSON-like examples are illustrative and non-executable. They do
not define a serializer, do not claim runtime implementation, and contain no
credentials, absolute developer-machine paths, personal identifiers, or
provider secrets.

### Guardian Task Spec skeleton

```text
{
  "task_spec_id": "ts_example_001",
  "schema_version": "guardian-task-spec.v1",
  "task_spec_revision": 1,
  "delegation_id": "delegation_example_001",
  "source_request_identity": {"request_id": "request_example_001"},
  "source_lineage": {
    "thread_id": "thread_example_001",
    "message_id": "message_example_001",
    "turn_id": "turn_example_001",
    "actor_subject": "actor-bound-by-guardian"
  },
  "selected_execution_channel": "pi",
  "execution_system_identity": {
    "name": "pi-execution-system",
    "version": "declared-by-channel"
  },
  "underlying_model_policy": {"mode": "declared_when_known"},
  "goal": "Document the bounded architecture contract.",
  "authorized_repository_or_workspace": {"repository": "example/repo"},
  "repository_identity": {"expected_ref": "main"},
  "allowed_paths": ["docs/architecture/**"],
  "forbidden_paths": ["guardian/**", "frontend/**"],
  "requirements": ["Preserve Guardian authority and native evidence."],
  "acceptance_criteria": ["Contract sections and mappings are reviewable."],
  "validation_contract": {"commands": ["make docs"]},
  "non_goals": ["No runtime implementation."],
  "architecture_impact_classification": "architecture-impact",
  "risk_classification": {"scope": "bounded", "release": "no-change"},
  "human_review_posture": {"required": true, "stage": "before-merge"},
  "mutation_posture": "bounded-write",
  "permission_posture": {
    "allow_network": false,
    "allow_shell": true,
    "allow_write": true,
    "allow_commit": false,
    "allow_push": false,
    "allow_merge": false,
    "allow_release": false
  },
  "timeout_posture": {"mode": "bounded"},
  "retry_posture": {"max_attempts": 1, "new_attempt_on_retry": true},
  "cancellation_posture": {"authorized_by": "guardian"},
  "expected_artifacts": ["contract-document"],
  "expected_proof_surfaces": ["docs-validation", "scoped-diff"],
  "result_return_destination": {"durable": "guardian-record"},
  "creation_provenance": {"source": "guardian-authored"},
  "created_at": "2026-01-01T00:00:00Z",
  "task_spec_hash": "computed-over-immutable-projection"
}
```

### Guardian Delegation Result Envelope skeleton

```text
{
  "delegation_id": "delegation_example_001",
  "result_envelope_id": "result_example_001",
  "schema_version": "guardian-delegation-result-envelope.v1",
  "task_spec_id": "ts_example_001",
  "task_spec_hash": "computed-over-immutable-projection",
  "selected_execution_channel": "pi",
  "execution_system_identity": {"name": "pi-execution-system"},
  "underlying_model_identity": {"value": "declared-by-channel"},
  "native_run_id": "native_run_example_001",
  "native_session_id": "native_session_example_001",
  "native_attempt_id": "native_attempt_example_001",
  "attempt": {"number": 1, "idempotency_key": "attempt_example_001"},
  "lifecycle_status": "completed",
  "native_status": "needs_review",
  "status_mapping": {
    "adapter": "example-adapter",
    "mapping_version": "1",
    "terminality": "explicit"
  },
  "summary": "Native execution completed; Guardian review remains pending.",
  "changed_paths": ["docs/architecture/example.md"],
  "commit_hashes": [],
  "patch_references": [],
  "artifact_references": ["artifact_example_001"],
  "receipt_references": ["receipt_example_001"],
  "validation_results": {"status": "passed", "source": "guardian"},
  "scope_findings": {"status": "within_scope"},
  "mutation_findings": {"status": "within_posture"},
  "lineage_verification_findings": {"status": "verified"},
  "errors": [],
  "stop_reason": "native_execution_completed",
  "timeout_evidence": {"status": "not_applicable"},
  "cancellation_evidence": {"status": "not_cancelled"},
  "retry_or_attempt_information": {"prior_attempts": []},
  "review_posture": "pending",
  "guardian_acceptance": "pending",
  "remaining_human_action": ["Review the bounded patch."],
  "source_result_lineage": {"source_thread_id": "thread_example_001"},
  "result_return_destination": {"durable": "guardian-record"},
  "created_at": "2026-01-01T00:00:00Z",
  "started_at": "2026-01-01T00:00:01Z",
  "updated_at": "2026-01-01T00:01:00Z",
  "terminal_at": "2026-01-01T00:01:00Z",
  "channel_native_evidence": {"references": ["receipt_example_001"]},
  "guardian_normalization_provenance": {
    "normalizer": "guardian-normalizer",
    "mapping_version": "1"
  }
}
```

## Compatibility and migration posture

Migration is additive and compatibility-first. No migration occurs in this
task. The implementation sequence is:

1. adopt this shared documentation contract;
2. define runtime token registration and a machine-readable schema in a
   separate implementation task;
3. map and prove the current Pi-compatible coding-worker lane;
4. add native Codex and Claude adapters behind explicit Guardian selection;
5. preserve legacy `pi_codex_runner` aliases through a compatibility window;
6. migrate persistence and result-return consumers only through separate
   atomic tasks with rollback and proof requirements; and
7. remove legacy coupling only after compatibility, rollback, and
   implementation proof are complete.

The current runtime must remain a valid compatibility baseline until a
successor path is proven. No consumer may infer that a current runtime hash,
run, event, result store, or adapter session is already the shared contract.

## Follow-up dependencies

The following future work depends on this contract and must not invent
channel-specific authority rules:

- native Codex delegation adapter and proof;
- native Claude delegation adapter and proof;
- Pi-channel reframing around its deterministic execution role;
- runtime schema and canonical token registration;
- persistence and migration work;
- adapter-native status mapping;
- Codex-Runner migration and naming plan; and
- separate result-return and rollback proof for each implementation slice.

Each follow-up remains subject to current-state release truth, ADR alignment,
explicit scope, human review, and surface-specific proof.

## Non-goals and explicit deferrals

This document does not:

- implement a Codex adapter;
- implement a Claude adapter;
- refactor or rename the Pi adapter;
- add a runtime dataclass, Pydantic model, JSON Schema, or persistence model;
- register lifecycle values in `guardian/protocol_tokens.py`;
- change routes, APIs, queues, workers, providers, command-bus semantics,
  validation behavior, result stores, migrations, aliases, or release paths;
- authorize automatic merge, push, release, or self-modification; or
- update current-state release claims.

The contract provides architecture-document proof only. It does not provide
runtime, adapter, integration, provider, queue, worker, persistence,
migration, or live end-to-end delegation proof.

## Proof surface and validation expectations

This task's proof surface is limited to:

- existence of this canonical contract;
- separate Task Spec and result-envelope definitions;
- field ownership, requirement, and mutability tables;
- immutable projection, hash, and amendment rules;
- lifecycle terminality and separate review vocabulary;
- explicit native-status mapping and fail-closed rules;
- scope, lineage, provenance, validation, review, timeout, cancellation,
  error, artifact, commit, and human-action homes;
- current-runtime mapping matrix;
- illustrative non-executable skeletons;
- compatibility, migration, and follow-up sections;
- architecture README discoverability; and
- a diff limited to the two authorized documentation files.

Documentation validation is not runtime proof. Future implementation tasks must
add executable schema, token, adapter, persistence, migration, and live proof
surfaces before making runtime or release claims.

## Related reading

- [00 Current State](./00-current-state.md)
- [Architecture KB](./README.md)
- [ADR Index](./adr/adr-index.md)
- [ADR-048: Guardian Three-Channel Delegation Topology](./adr/ADR-048-guardian-three-channel-delegation-topology.md)
- [ADR-020: Guardian Mediated Coding Agent Execution Contract](./adr/020-guardian-mediated-coding-agent-execution-contract.md)
- [Guardian Build Loop Doctrine](./guardian-build-loop-doctrine.md)
- [Pi Invocation Boundary Contract](./pi-invocation-boundary-contract.md)
- [Delegation Runtime Contract](./delegation-runtime.md)
- [Delegation Operator Manual](./delegation-operator-manual.md)
- [Agent Protocol Operations Index](./agent-protocol-operations.md)
- [Agent Tool-Loop Contract](./agent-tool-loop-contract.md)
- [Runtime Protocol Token Contract](./runtime-protocol-token-contract.md)
- [Account Export + Restore Contract](./account-export-restore-contract.md)
- [Task Spec Protocol](../Collaborators/task-spec-protocol.md)
