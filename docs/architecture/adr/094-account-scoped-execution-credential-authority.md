# ADR-094: Account-Scoped Execution Credential Authority

- Status: Proposed
- Date: 2026-09-29
- Human decision requested: Resonant Jones acceptance before runtime implementation

## Context

The account-authenticated coding route can enqueue work for a shared coding worker, while the current Pi worker has a shared auth volume and may select provider and model from ambient process configuration. The route and task do not currently carry a canonical account-scoped execution-credential reference. A provider/model choice alone cannot authorize use of a credential found in that worker. The observed code path is an implementation gap, not proof that cross-account execution has occurred.

Resonant Jones directed that account-scoped execution credentials are the authority model for account-scoped coding execution. The existing single-user/operator credential lane may remain only as an explicitly bounded compatibility path. This direction authorizes drafting this general architecture contract; it is not acceptance of this Proposed ADR or authorization to implement credential storage or delivery.

## Governing relationships

- [ADR-020](020-guardian-mediated-coding-agent-execution-contract.md) makes Guardian the intake, lineage, policy, and result-ingestion authority for coding tasks.
- [ADR-048](ADR-048-guardian-three-channel-delegation-topology.md) keeps harnesses subordinate to Guardian. [ADR-093](093-native-execution-channel-and-inference-routing-contract.md) separates harness, invocation-scoped provider/model, funding route, and placement. This ADR defines the credential authority that an eligible execution binding must satisfy; it does not reopen harness selection.
- [ADR-071](071-connections-control-plane-boundary.md) distinguishes connection visibility and setup from inference authorization, and keeps credentials server-owned and user-scoped. Its catalog is a projection, not execution authority or a universal credential store.
- [ADR-092](092-credential-purpose-and-mixed-principal-authentication-boundary.md) separates account and operator principals. An operator credential or session does not become an account credential through routing fallback.
- [ADR-077](077-sandbox-execution-authority-and-provider-boundary.md) keeps provider credentials outside untrusted command environments unless a separate purpose-bound Guardian grant authorizes exposure.
- [00 Current State](../00-current-state.md) remains the release and supported-path authority. This proposal establishes no runtime or release support.

## Proposed decision

### Ownership, custody, and reference

1. Every execution credential or entitlement has one canonical owner scope: a Codexify account or an explicitly authorized operator scope. A shared worker, harness process, deployment, Project, Thread, provider, or model does not own it. Project and Thread identities narrow the permitted invocation; they do not transfer credential ownership.
2. Secret custody stays in a server-controlled, owner-scoped credential facility appropriate to the credential type. The custodian may hold encrypted API-key or OAuth material, broker a provider-native entitlement, or represent a local runtime with no secret. These forms need not share one table, schema, or delivery mechanism. Rotation, revocation, deletion, export, and restore must preserve owner scope; restored references cannot revive revoked authority. The Connections catalog may project setup state but cannot confer execution authority.
3. An execution binding may carry an opaque, non-bearing credential or entitlement reference, its canonical owner scope, source/type, and authorization-evidence reference. The reference is an identifier, not a bearer capability. Raw API keys, access or refresh tokens, native session secrets, bearer credentials, and equivalent secret material never enter the binding, queue/task records, events, logs, result artifacts, or durable provenance.
4. Provider/model selection, credential selection, and funding/entitlement classification are separate decisions. Choosing a provider or model, seeing a configured connection, or possessing a shared Pi auth file does not authorize use of a credential.

### Guardian resolution and dispatch

5. Guardian authenticates the invoking principal and verifies its account or explicit operator scope, source user, Project, Thread, source message, task/attempt lineage, requested harness/provider/model, policy, and credential or entitlement eligibility before dispatch. Account-scoped work may select an account-owned credential or an operator-scoped credential or entitlement only when a separate, explicit policy grant authorizes that account and invocation. The original operator owner remains recorded; the grant does not transfer ownership. Operator authority is never inferred from a failed account lookup.
6. Guardian resolves the credential reference against its owner and permitted provider/route, checks status, expiry, revocation, capability and placement compatibility, and records a bounded secret-free authorization decision. A selected model is not evidence that the selected credential can use it. Missing, revoked, expired, incompatible, or unauthorized credentials fail closed before provider execution.
7. The durable task and queue handoff carry the authorized binding or an authoritative reference to it, including owner scope and attempt lineage, without transporting secret values or a redeemable bearer grant. Worker receipt of a queue item is not credential authorization. The worker must use Guardian's binding and cannot choose another credential from its environment or auth store.

### Execution-time secret boundary

8. Immediately before each provider-backed attempt, the execution boundary revalidates that the binding, credential, owner, attempt, and policy remain authorized. An execution-time grant is limited to that invocation's provider purpose, principal, attempt, placement, and lifetime. This is a logical lease of use, not a selected token format or transport. A retry or resumed native session requires a fresh authorization check; stale queue state and prior process state confer no authority.
9. The custodian supplies secret material only to the authorized provider transport at execution time, through a bounded mechanism selected and proved in a later implementation task. Where the adapter must temporarily handle plaintext, it must limit visibility to the authorized invocation, prevent exposure to untrusted tools or commands, avoid durable storage and output, and clear or isolate state before another account's invocation. The contract permits brokered use in which the shared worker never sees plaintext. It does not choose between these mechanisms.
10. Warm or persistent workers and harness sessions must not carry one account's credential into another account's invocation through process environment, shared home directory, auth file, SDK cache, session state, or retry state. Native session reuse is permitted only when the owner, credential scope, binding compatibility, availability, and current authorization all match. Worker process lifetime grants no credential ownership.

### Compatibility, provenance, and failure

11. An existing single-user local or operator Pi credential path may remain, where already supported, only under an explicit local/operator policy and matching principal authority. Its shared auth volume and ambient `PI_PROVIDER`/`PI_MODEL` may serve bounded legacy execution or readiness, but cannot authorize account-scoped work, override an account binding, or act as fallback for a missing account credential. Account-scoped tasks without a conforming credential path fail closed rather than being routed to that compatibility lane.
12. Guardian's durable provenance records the source account or operator scope, Project/Thread/task/attempt lineage, requested and observed harness/provider/model where available, execution placement, credential source/type or opaque identity needed for audit, and authorization/result references. Requested identity is not reported as observed identity. Secret values, credential-derived bearer material, and raw provider errors are excluded from provenance and user-visible output.
13. Revocation or expiry wins over a queued authorization at execution-time revalidation. Duplicate delivery is correlated to the same authorized attempt and cannot redeem a credential twice or widen its scope. If the custodian, policy check, or isolation posture is unavailable, the attempt fails closed with a bounded, secret-free reason. A provider failure never triggers credential substitution across accounts or into operator scope.

## Authority and trust boundaries

| Boundary | Authority and required separation |
| --- | --- |
| Account or operator to Guardian | Authentication establishes one principal class and owner scope. Account and operator lanes never substitute for each other. |
| Guardian to credential custodian | Guardian authorizes an owner-scoped reference; the custodian protects secret material and enforces current eligibility. Reference possession alone is insufficient. |
| Guardian to durable task and queue | The transport carries binding and lineage, not secrets or a reusable bearer grant. Queue acceptance is not execution authorization. |
| Shared worker to harness/provider transport | Execution-time access is attempt-bound. Worker, harness, SDK, and subprocess state cannot become cross-account credential stores. |
| Harness to untrusted tools and sandbox | Model/provider transport credentials stay outside command environments absent a separate explicit Guardian grant under ADR-077. |

Canonical account or operator ownership is strongly checked at dispatch and again at execution-time access. There is no cross-owner merge or last-writer-wins resolution of credential authority. Revocation, owner mismatch, or stale authorization denies access. The threat model includes honest but buggy workers, duplicate queue delivery, stale cached sessions, compromised untrusted tools, and attempts to use another account's or the operator's ambient credentials.

## Implementation and proof gates after acceptance

Any bounded implementation must choose and document the credential-type-specific custody and execution-time delivery mechanism, version its binding and queue contract, and define migration behavior for old queued tasks. Old account-scoped tasks without a valid owner-bound credential reference must fail closed; compatibility cannot silently populate one. Schema, storage, lease encoding, and secret transport remain undecided here.

Proof must include positive account-owned authorization, same-worker sequential invocations with distinct account credentials and provider/model bindings, revocation and missing/incompatible credential rejection before provider execution, cross-account and account-to-operator fallback rejection, retry/session reauthorization, and checks that queue records, logs, artifacts, and durable provenance contain no secret material. Runtime proof must identify the actual provider/model and credential source class used without exposing secrets. Focused tests or credential-presence checks alone do not establish live execution or isolation.

## Non-goals and review state

This proposal does not add a credential table, secret broker, lease token, API endpoint, Pi adapter change, queue/worker implementation, GUI, billing, hosted execution, new harness, or release claim. It does not make all credential types share one model or change the accepted ADR-093 harness-selection semantics.

**Human acceptance is required before the Guardian → queue → coding-worker → Pi invocation-binding implementation resumes.** Until then, the account-scoped credential path remains unimplemented and no shared Pi credential may be treated as its authority.
