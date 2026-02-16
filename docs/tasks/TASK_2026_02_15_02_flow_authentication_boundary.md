
TASK 2 — Flow Authentication Boundary (Pre-Auth, No Exfil, No Mid-Run Escalation)

Objective

Implement a capability-secure flow execution boundary where:

- Flows are pre-authenticated before execution.
- Flows cannot request new authentication or new permissions mid-run.
- External network egress is disabled by default.
- Any external destination must be explicitly user-approved during installation/binding (not during execution).
- Transferable/imported flows are disabled for MVP (user-created only).

This task hardens the automation surface so a downloaded flow cannot silently exfiltrate data or expand its authority.

Scope

Backend-only for this task.
Do not modify frontend UI.
Do not implement flow sharing, marketplace, or blueprint exchange.
Do not add connector integrations (email, cloud drives) beyond policy gates.

Security Invariants (Must Hold)

1) No Mid-Flow Auth
- If a step requires auth that is not already present in the flow execution context, the flow must fail closed.

2) No Permission Escalation
- If a step requires a scope not granted at flow start, the flow must fail closed.

3) No Silent Network Egress
- Network calls are forbidden unless the flow execution context explicitly allows them AND the destination is pre-approved.

4) No Transfer Imports
- Import/install of external flow definitions is disabled for MVP.

System Model

Introduce two core data structures:

A) FlowExecutionContext
- pre_authenticated: bool
- granted_scopes: list[str]
- allowed_external_domains: list[str]
- allow_network_egress: bool (default false)
- run_id: string
- issued_at: timestamp
- expires_at: timestamp (short-lived run grant)

B) FlowStepSpec (validated before run)
- step_id: string
- action: string (must map to an existing primitive or command id)
- required_scopes: list[str]
- external_domain: string | null
- requires_network: bool

Preflight Contract (Required)

Before execution begins, compute a Preflight Contract that includes:
- steps_count
- required_scopes (union)
- external_domains (union)
- requires_network_egress (bool)

If any external_domains exist and are not already user-approved (binding-time), fail closed.
If requires_network_egress is true but allow_network_egress is false, fail closed.

Files Likely Affected

This change belongs in backend orchestration and flow execution layers, likely including:
- guardian/core/orchestrator/*
- guardian/cli/* if CLI flows exist
- guardian/routes/* only if flow execution is exposed via API
- any existing flow/automation module

Do not introduce new top-level subsystems in this task.

Codexify Task Prompt

Context:
You’re operating on the local Codexify repo. Each task must be self-contained, testable, and committed individually.

Instructions:

1) Implement FlowExecutionContext
- Add a backend model (dataclass/pydantic/typed dict depending on existing conventions) named FlowExecutionContext with:
  - pre_authenticated
  - granted_scopes
  - allowed_external_domains
  - allow_network_egress
  - run_id
  - issued_at
  - expires_at
- Add helper:
  - validate_step(step_spec, ctx) -> None | raises

2) Implement FlowStepSpec Validation
- Define a FlowStepSpec schema with:
  - step_id
  - action
  - required_scopes
  - external_domain
  - requires_network
- Ensure runtime never executes an unvalidated step spec.

3) Enforce No Mid-Run Auth
- At the start of flow execution, require ctx.pre_authenticated == True.
- Reject any step that attempts to:
  - prompt for auth
  - request additional scopes
  - mutate ctx.granted_scopes

4) Enforce Scope Boundaries
- For every step:
  - required_scopes must be subset of ctx.granted_scopes.
  - If not, fail closed with a structured error.

5) Enforce Network Egress Policy
- Default: block all network calls from flows.
- Only allow if:
  - ctx.allow_network_egress == True
  - step.requires_network == True
  - step.external_domain is in ctx.allowed_external_domains
- If step.requires_network == True but step.external_domain is null, fail closed.

6) Disable Transferable Flow Import (MVP)
- If any flow import/install endpoint or CLI exists:
  - disable it behind a hard gate (feature flag or explicit NotImplementedError)
  - allow only local/user-created flow definitions
- Add a clear error message explaining that importing is disabled for MVP.

7) Tests (Required)
Add backend tests that fail before and pass after:

- Flow run fails if ctx.pre_authenticated == False.
- Step fails if it requires a scope not granted at start.
- Step fails if it attempts to mutate granted scopes.
- Step fails if it requires network but ctx.allow_network_egress == False.
- Step fails if it targets a domain not in ctx.allowed_external_domains.
- Flow import/install rejects non-local/transferable definitions (if code path exists).

8) Validation
Run backend tests:

pytest -v

9) Commit
Stage only modified files.
Commit message:

"Add pre-auth flow boundary with scope + egress enforcement"

Output (Required)

- Summary of changes (files + key functions).
- Backend test results summary.
- Git commit hash.

Constraints

- Do not build a marketplace or sharing format in this task.
- Do not add UI.
- Do not add new connectors.
- Do not loosen existing auth requirements.

This task establishes the flow execution security boundary that all future flows must pass through.

---

Execution Notes (2026-02-16)

- Added runtime security models and guards in `guardian/flows/security.py`:
  - `FlowExecutionContext`
  - `FlowStepSpec`
  - preflight contract builder/validator
  - per-step enforcement for pre-auth, scope boundaries, no mid-run auth, and network/domain gates
- Extended flow schema + compiler to carry security metadata on each step:
  - `required_scopes`
  - `requires_network`
  - `external_domain`
  - `requests_auth`
  - `requested_scopes`
- Enforced security boundary in `guardian/flows/runner.py` before primitive execution:
  - execution context coercion
  - preflight contract validation (fail closed)
  - per-step validation (fail closed) before primitive invoke
- Added API hard gate for transferable import in `guardian/routes/flows.py`:
  - `POST /api/flows/import` returns explicit MVP-disabled error
  - flow run route now forwards/normalizes execution context
- Added backend tests in `tests/test_flows_core.py` for:
  - pre-auth failure
  - missing scope failure
  - scope escalation/mutation failure
  - network egress blocked failure
  - unapproved external domain failure
  - flow import disabled gate
