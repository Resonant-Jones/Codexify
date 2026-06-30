# Model Chain Workflows and Cloud Escalation Policy

## Purpose

This note defines a future Codexify workflow model where provider/model selection belongs to each workflow step instead of only to the whole session.

It is contract planning only. It does not implement workflow execution, provider routing, cloud escalation, billing, credentials, UI controls, or model selection behavior.

## Governing Sources

- `docs/architecture/00-current-state.md`
- `docs/architecture/README.md`
- `docs/architecture/flows.md`
- `docs/architecture/providers.md`
- `docs/architecture/router-decision-table.md`
- `docs/architecture/provider-capability-contract.md`
- `docs/architecture/flow-builder-semantic-step-contract.md`
- `docs/architecture/flow-builder-validation-issue-taxonomy.md`
- `docs/architecture/flow-builder-testrun-activation-contract.md`
- `docs/architecture/web-search-provider-adapter-contract.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/self-extending-agent-plugin-system.md`

## Interpretation Rules

- Local-first remains the default posture.
- Provider selection is a property of a workflow step, not only a session-wide default.
- Cloud calls must be explicit, explainable, and policy-controlled.
- A workflow template may require a specific provider or model for a specific step.
- The workflow engine must not silently send private data to cloud providers without user or operator permission.
- Cloud escalation must be observable in the UI.
- This note does not claim any of the described workflow behaviors are already implemented on `main`.

## Boundary Model

### Nodes

- User client
- Local Codexify runtime
- Local model provider or Whoosh'd runtime
- Cloud model provider
- Workflow template authoring surface
- Workflow execution surface

### Trust Boundaries

- User boundary: user-owned inputs and approval decisions
- Device boundary: local machine or local server running the workflow engine
- Network boundary: any egress to cloud providers or remote services
- Template boundary: a stored workflow template that can constrain step behavior

### Threat Model

- Honest-but-buggy local or cloud provider
- Compromised cloud provider account or API key
- Malicious or overly broad workflow template
- Accidental data exposure through implicit escalation

## Core Concepts

### Workflow Step

A workflow step is a discrete unit of work inside a larger process.

Typical step kinds include:

- retrieve data
- draft response
- summarize sources
- generate artifact
- validate output
- polish final result

Each step may declare:

- expected inputs
- expected outputs
- preferred provider
- preferred model
- allowed provider classes
- required capability checks
- cloud escalation policy
- approval requirement
- redaction or source restrictions

### Model Chain

A model chain is a workflow where different steps may be routed to different providers or models.

The important property is not "multiple models in one session" but "step-local routing with explicit policy."

Example shape:

1. A retrieval step uses an API or index to gather source facts.
2. A local model drafts a response.
3. A second local model generates an artifact.
4. A cloud model validates, corrects, or polishes the final artifact when policy allows it.

### Workflow Template

A workflow template is the authored definition that binds a sequence of steps, step policies, and allowed escalation behavior.

A template may constrain:

- which steps must remain local
- which steps may escalate
- which steps require a specific provider or model
- which steps require user approval before cloud use
- which step outputs are eligible for downstream use

## Cloud Escalation Policy

Cloud escalation policy is the rule set that decides when Codexify may call a cloud model.

Canonical policy modes for this note:

| Mode | Meaning | Default posture |
|---|---|---|
| `never_use_cloud` | Cloud providers are disallowed for the step or workflow. | Fail closed. |
| `ask_before_cloud` | Cloud use is allowed only after explicit user or operator approval. | Prompt before egress. |
| `final_validation_only` | Cloud use is allowed only for the last validation or polish step. | No cloud during earlier drafting steps. |
| `low_confidence_escalation` | Cloud use is allowed when a step confidence threshold is not met. | Must explain the trigger and threshold. |
| `template_required` | The workflow template explicitly requires a cloud provider or cloud-capable model for the step. | Allowed only when the template and policy both permit it. |

Policy rules:

- Policy is evaluated per step, not only once per session.
- Policy decisions must be logged or receipted with the step attempt.
- A step may still be blocked by local-only mode, credential absence, egress policy, or capability checks even if the template allows cloud use.
- A template requirement does not override user or operator approval rules when approval is required.
- If policy is ambiguous, the system should fail closed rather than guess.

## Step-Level Routing Shape

A workflow step should be able to carry its own routing metadata.

Proposed step-level fields:

| Field | Meaning |
|---|---|
| `step_kind` | What the step does. |
| `preferred_provider` | The provider class or provider family the step wants to use. |
| `preferred_model` | The model id or model alias the step wants to use. |
| `allowed_providers` | The providers the step may use if the preferred provider is unavailable. |
| `required_capabilities` | Capabilities the selected provider must prove, such as structured output, tool use, context window size, or retrieval support. Capability definitions live in [`Provider Capability Contract`](./provider-capability-contract.md). |
| `cloud_escalation_policy` | The policy mode governing cloud use for the step. |
| `approval_required` | Whether cloud use requires explicit approval for this step. |
| `fallback_behavior` | What happens if the preferred provider or model is unavailable. |
| `policy_reason` | Human-readable reason for the routing choice. |

Selection precedence should be treated as a policy chain:

1. Template constraints
2. Step-level provider and model declaration
3. Cloud escalation policy
4. Capability checks
5. Runtime availability

If any earlier layer forbids cloud, later layers must not override it.

## Invariants

- Provider selection is step-local.
- Local-first is the default.
- Cloud is explicit, not ambient.
- Cloud routing must be explainable to the operator.
- Private data must not cross the cloud boundary without permission.
- Template authors may require a provider or model for a step, but not by bypassing policy.
- UI surfaces must show when a step is local, hybrid, cloud-eligible, blocked, or escalated.

## Failure Modes

1. Step requires a cloud model but the workflow is in local-only mode.
   - Mitigation: block the step and show a clear policy reason.
2. Step is allowed to escalate but the user has not approved cloud use.
   - Mitigation: pause before egress and request approval if policy requires it.
3. Template asks for a model that is not available or not authorized.
   - Mitigation: fail closed and surface a capability or availability issue.
4. Cloud validation step receives sensitive inputs that should stay local.
   - Mitigation: enforce redaction, permission checks, and source restrictions before dispatch.
5. A chain mixes local and cloud steps without an auditable explanation.
   - Mitigation: record step-level provenance, routing reasons, and escalation decisions.

## Example Workflows

### Local-Only Workflow

Policy posture:

- `never_use_cloud`

Step chain:

1. Retrieve local workspace facts with a local retrieval step.
2. Draft with Whoosh'd or another local model.
3. Validate with a second local model.
4. Polish the final artifact locally.

What this proves:

- Model chaining does not imply cloud usage.
- A workflow can stay entirely local while still using different models for different steps.
- Provider choice remains step-local even when every step is local.

### Hybrid Local/Cloud Workflow

Policy posture:

- `final_validation_only`

Step chain:

1. Retrieve source facts locally.
2. Draft a response with a local model.
3. Generate an artifact with a local model.
4. Send only the final artifact to a cloud model for validation and polish.

What this proves:

- Local-first drafting can coexist with a bounded cloud validation step.
- Cloud escalation is limited to the step that explicitly permits it.
- The UI should expose that the workflow escalated only for the final validation step.

## Observability and UI Requirements

Cloud escalation should be visible in the UI as step-level state, not hidden behind a single session label.

The UI should show:

- the provider selected for each step
- the model selected for each step
- whether the step is local, hybrid, or cloud-bound
- when escalation was requested
- whether escalation was approved, denied, or not needed
- why a step was blocked from cloud use
- which policy mode applied

The execution trace or receipt should preserve the same step-level explanation so the UI can reconstruct what happened without guessing.

## Follow-Up Implementation Specs

This note intentionally stops before implementation. The next specs should separate execution, UI, and capability concerns.

### 1. Workflow Execution Spec

Should define:

- step scheduling and dispatch order
- step-local provider/model resolution
- policy evaluation before dispatch
- retry and fallback behavior
- idempotency and provenance recording
- how local and cloud steps hand off data to each other

Suggested future name:

- `workflow-execution-contract.md`

### 2. UI Controls Spec

Should define:

- per-step provider and model selectors
- cloud escalation badges and warnings
- approval prompts for cloud use
- template-level policy summaries
- step-level audit and explanation surfaces

Suggested future name:

- `workflow-ui-cloud-controls-contract.md`

### 3. Provider Capability Checks Spec

Should define:

- provider capability registry shape
- capability checks for local and cloud providers
- model inventory checks
- context window and output-shape requirements
- fallback or fail-closed behavior when capabilities are missing
- how capability results are surfaced to policy and UI layers

Suggested future name:

- `provider-capability-checks-contract.md`

This follow-up should consume [`Provider Capability Contract`](./provider-capability-contract.md) as the capability vocabulary and record shape.

## Non-Goals

- No workflow execution implementation
- No cloud routing implementation
- No billing logic
- No credential management changes
- No new default cloud posture
- No UI implementation
- No provider capability registry implementation
- No silent escalation behavior
- No release-surface expansion
