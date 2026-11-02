# ADR-094: Account-Scoped Execution Credential Authority

- Status: Accepted
- Date: 2026-09-29
- Accepted: 2026-09-29
- Human approver: Resonant Jones
- Proposed amendment: 2026-11-02 — *delegated external credential custodian*
  (see [Proposed amendment](#proposed-amendment-delegated-external-credential-custodian-2026-11-02)).
  **Proposed only — not accepted, not operative.**

## Context

The account-authenticated coding route can enqueue work for a shared coding worker, while the current Pi worker has a shared auth volume and may select provider and model from ambient process configuration. The route and task do not currently carry a canonical account-scoped execution-credential reference. A provider/model choice alone cannot authorize use of a credential found in that worker. The observed code path is an implementation gap, not proof that cross-account execution has occurred.

Resonant Jones accepted this architecture on 2026-09-29: credential authority for account-scoped coding execution must be resolved per invocation. The existing single-user/operator credential lane may remain only as an explicitly bounded compatibility path. Codexify service-owned credentials must also be eligible for account invocations under explicit service policy, including the `codexify_included` and `codexify_metered` funding routes in ADR-093. Acceptance authorizes the bounded invocation-scoped execution-binding Task Spec to resume under ADR-093 and this ADR's contracts; it does not authorize a specific credential storage or delivery design.

## Governing relationships

- [ADR-020](020-guardian-mediated-coding-agent-execution-contract.md) makes Guardian the intake, lineage, policy, and result-ingestion authority for coding tasks.
- [ADR-048](ADR-048-guardian-three-channel-delegation-topology.md) keeps harnesses subordinate to Guardian. [ADR-093](093-native-execution-channel-and-inference-routing-contract.md) separates harness, invocation-scoped provider/model, funding route, and placement. This ADR defines the credential authority that an eligible execution binding must satisfy; it does not reopen harness selection.
- [ADR-071](071-connections-control-plane-boundary.md) distinguishes connection visibility and setup from inference authorization, and keeps credentials server-owned and user-scoped. Its catalog is a projection, not execution authority or a universal credential store.
- [ADR-092](092-credential-purpose-and-mixed-principal-authentication-boundary.md) separates account and operator principals. An operator credential or session does not become an account credential through routing fallback.
- [ADR-077](077-sandbox-execution-authority-and-provider-boundary.md) keeps provider credentials outside untrusted command environments unless a separate purpose-bound Guardian grant authorizes exposure.
- [00 Current State](../00-current-state.md) remains the release and supported-path authority. This decision establishes no runtime or release support.

## Decision

### Ownership, custody, and reference

1. Every execution credential or entitlement has one canonical owner scope: a Codexify account, an explicitly authorized human operator, or the Codexify service/deployment. A service-owned credential remains owned and custodied by that service/deployment when used for an account invocation; it does not become account-owned or derive authority from a human operator session. A shared worker or harness instance, Project, Thread, provider, or model does not own it. Project and Thread identities narrow the permitted invocation; they do not transfer credential ownership.
2. Secret custody stays in a server-controlled, owner-scoped credential facility appropriate to the credential or entitlement type. The custodian may hold encrypted API-key or OAuth material, broker access without releasing a secret, authorize use of a pre-authenticated native session, or represent a local runtime with no secret. Resolving an authorized reference need not yield plaintext secret material; native subscriptions and other non-exportable entitlements need not fit an API-key-shaped abstraction. These forms need not share one table, schema, or delivery mechanism. Rotation, revocation, deletion, export where applicable, and restore must preserve owner scope; restored references cannot revive revoked authority. The Connections catalog may project setup state but cannot confer execution authority.
3. An execution binding may carry an opaque, non-bearing credential or entitlement reference, its canonical owner scope, source/type, and authorization-evidence reference. The reference is an identifier, not a bearer capability. Raw API keys, access or refresh tokens, native session secrets, bearer credentials, and equivalent secret material never enter the binding, queue/task records, events, logs, result artifacts, or durable provenance.
4. Provider/model selection, credential selection, and funding/entitlement classification are separate decisions. Choosing a provider or model, seeing a configured connection, or possessing a shared Pi auth file does not authorize use of a credential.

### Guardian resolution and dispatch

5. Guardian authenticates the invoking principal and verifies its account or explicit operator scope, source user, Project, Thread, source message, task/attempt lineage, requested harness/provider/model, funding route, policy, and credential or entitlement eligibility before dispatch. Account-scoped work may use an account-owned credential, a service-owned credential under explicit Codexify policy, or an operator-owned credential only under a separate, explicit operator grant for that account and invocation. Service policy must authorize the specific account, invocation, provider/model binding, funding route, and applicable usage policy. The service or operator owner remains recorded; use does not transfer ownership. Service authority is not derived from an operator session, and operator authority is never inferred from a failed account lookup.
6. Guardian resolves the credential or entitlement reference against its canonical owner and permitted provider, model, funding route, and usage policy; checks status, expiry, revocation, capability, and placement compatibility; and records a bounded secret-free authorization decision. A selected model or funding route is not evidence that the selected credential or entitlement can use it. Missing, revoked, expired, incompatible, or unauthorized authority fails closed before provider execution.
7. The durable task and queue handoff carry the authorized binding or an authoritative reference to it, including owner scope and attempt lineage, without transporting secret values or a redeemable bearer grant. Worker receipt of a queue item is not credential authorization. The worker must use Guardian's binding and cannot choose another credential from its environment or auth store.

### Execution-time secret boundary

8. Immediately before each credential- or entitlement-backed attempt, the execution boundary revalidates that the binding, credential or entitlement, owner, attempt, and policy remain authorized. An execution-time grant is limited to that invocation's provider purpose, principal, attempt, placement, and lifetime. This is a logical lease of use, not a selected token format or transport. A retry or resumed native session requires a fresh authorization check; stale queue state and prior process state confer no authority.
9. Resolution may grant use without releasing plaintext, including brokered provider access, an authorized pre-authenticated native harness/provider session, or a local or other secretless runtime. Where plaintext is unavoidable, the custodian may supply it only to the minimum trusted credential-consuming control path required for that invocation, such as an authorized adapter, provider client, or necessary harness control plane. Exposure is limited to the authorized invocation and excluded from model-controlled tools, shell commands, sandbox workloads absent a separate ADR-077 grant, unrelated worker/harness state, and another account's invocation. It must avoid durable storage and output and clear or isolate temporary state before another invocation. A later implementation may prove brokered calls, invocation-scoped environment injection, isolated temporary auth material, provider SDK configuration, or another bounded mechanism; this ADR selects none of them.
10. Warm or persistent workers and harness sessions must not carry one account's credential or execution context into another account's invocation through process environment, shared home directory, auth file, SDK cache, session state, or retry state. Native session reuse is permitted only when the invoking account, owner, credential scope, binding compatibility, availability, and current authorization all match. Worker process lifetime grants no credential ownership.

### Compatibility, provenance, and failure

11. An existing single-user local or operator Pi credential path may remain, where already supported, only under an explicit local/operator policy and matching principal authority. Its shared auth volume and ambient `PI_PROVIDER`/`PI_MODEL` may serve bounded legacy execution or readiness, but cannot authorize account-scoped work, override an account binding, or act as fallback for missing account-authorized credential or entitlement access. Account-scoped tasks without a conforming credential path fail closed rather than being routed to that compatibility lane.
12. Guardian's durable provenance records the invoking account or operator, canonical credential owner scope (account, service/deployment, or operator), Project/Thread/task/attempt lineage, requested and observed harness/provider/model where available, funding route, execution placement, credential source/type or opaque identity needed for audit, and authorization, usage-policy, accounting, and result references. When multiple accounts use one service-owned credential, each invocation retains separate account authorization, lineage, and accounting/audit context. Requested identity is not reported as observed identity. Secret values, credential-derived bearer material, and raw provider errors are excluded from provenance and user-visible output.
13. Revocation or expiry wins over a queued authorization at execution-time revalidation. Duplicate delivery is correlated to the same authorized attempt and cannot redeem a credential twice or widen its scope. If the custodian, policy check, or isolation posture is unavailable, the attempt fails closed with a bounded, secret-free reason. A provider failure never triggers credential substitution across accounts or into operator or service scope.

## Authority and trust boundaries

| Boundary | Authority and required separation |
| --- | --- |
| Account or operator to Guardian | Authentication establishes the invoking principal and account or operator scope. Credential ownership may separately be account, Codexify service/deployment, or operator scope; none substitutes for another. |
| Guardian to credential custodian | Guardian authorizes an owner-scoped reference for the specific account, invocation, provider/model, funding route, and usage policy. The custodian protects secret material or non-exportable entitlement access and enforces current eligibility. Reference possession alone is insufficient. |
| Guardian to durable task and queue | The transport carries binding and lineage, not secrets or a reusable bearer grant. Queue acceptance is not execution authorization. |
| Shared worker to trusted credential consumer | Execution-time access is attempt-bound and limited to the minimum trusted control path. Worker, harness, SDK, and subprocess state cannot become cross-account credential stores. |
| Trusted credential consumer to untrusted tools and sandbox | Secret material stays outside model-controlled tools, shell commands, and sandbox workloads absent a separate explicit Guardian grant under ADR-077. |

Canonical account, Codexify service/deployment, or operator ownership is strongly checked at dispatch and again at execution-time access. Service-owned authority may be eligible for multiple accounts only through separate account-specific Guardian authorization; its bearer material is never exposed to the account. There is no cross-owner merge or last-writer-wins resolution of credential authority. Revocation, owner mismatch, or stale authorization denies access. The threat model includes honest but buggy workers, duplicate queue delivery, stale cached sessions, compromised untrusted tools, and attempts to use another account's, the service's, or the operator's ambient credentials without authorization.

## Implementation and proof gates

Any bounded implementation must choose and document the credential-type-specific custody and execution-time delivery mechanism, version its binding and queue contract, and define migration behavior for old queued tasks. Old account-scoped tasks without a valid owner-bound credential reference must fail closed; compatibility cannot silently populate one. Schema, storage, lease encoding, and secret transport remain undecided here.

Proof must include positive account-owned authorization; authorized service-owned use with account-specific provider/model, funding-route, usage-policy, lineage, and accounting separation across multiple accounts; same-worker sequential invocations with distinct account credentials and provider/model bindings; revocation and missing/incompatible authority rejection before provider execution; cross-account and account-to-operator/service fallback rejection; retry/session reauthorization; and checks that queue records, logs, artifacts, and durable provenance contain no secret material. Credential-type-specific proof must cover bounded plaintext consumption or non-exportable/secretless entitlement use as applicable. Runtime proof must identify the actual provider/model and credential source class used without exposing secrets. Focused tests or credential-presence checks alone do not establish live execution or isolation.

## Non-goals and review state

This acceptance does not select a database schema, credential table, secret broker, lease-token design, environment-variable or temporary auth-file injection, or a specific OAuth/API-key storage mechanism. It does not implement an API endpoint, Pi adapter change, queue/worker change, GUI, billing or metering, hosted execution, new harness, or release claim. It does not make all credential types share one model or change the accepted ADR-093 harness-selection semantics.

**The existing Guardian → queue → coding-worker → Pi invocation-scoped execution-binding Task Spec may resume as a separate bounded implementation task, subject to accepted ADR-093 and ADR-094 and its existing stop conditions.** Acceptance is not runtime completion; the account-scoped credential path remains unimplemented and no shared Pi credential may be treated as its authority.

---

## Proposed amendment: delegated external credential custodian (2026-11-02)

> **Status: PROPOSED — pending human acceptance. No operative effect.**
>
> This amendment is a proposal. It does not amend the accepted decision until Resonant
> Jones accepts it. Requirements 1–13 above remain the accepted decision, unchanged and
> in force. This amendment **extends** them to one named case; it does not supersede,
> weaken, reinterpret, or add an exception to any of them. It authorizes no
> implementation, no deployment, no migration, and no release claim, and it does not
> make OpenConnector adopted. The companion amendment to ADR-071 proposes the matching
> connection-control-plane reconciliation.

### A. The case this amendment admits

A **delegated external credential custodian** is a service that is not part of the
Guardian process and is not governed by the Guardian datastore, but that holds provider
credential material on behalf of a Codexify account and exposes a bounded execution
surface to an authorized adapter. The instance under review is an isolated OpenConnector
v1.9.4 gateway, deployed as a separate service with its own encrypted credential
database, its own administrative plane, and its own bearer-token vocabulary.

That instance is materially different from the custodian ADR-094 already anticipates.
It has an administrative interface and a credential database outside Guardian's
Postgres, and therefore outside Guardian's backup, export, and restore path. It has a
deployment-scoped master bearer that bypasses per-account connection grants by
construction. Its runtime authentication is configuration-dependent rather than
fail-closed by itself, so fail-closed behavior is a property Codexify's deployment
pipeline must supply.

ADR-094 is not silent on this case, but it is ambiguous at exactly this point.
Requirement 2 places custody in "a server-controlled, owner-scoped credential facility
appropriate to the credential or entitlement type," and the authority table already
contains a "Guardian to credential custodian" row. What was never resolved is what
"server-controlled" and "custodian" mean when the custodian is a **separate service
with its own administrative plane and its own credential database**. This amendment
resolves that, without weakening anything above it.

### B. Amendment clauses

**B1 — One canonical Guardian-owned binding.** For every custodian-backed execution
there is exactly one canonical authorization binding: the account-scoped record naming
the invoking Codexify account, the custodian, the provider, the custodian-side
connection identity, and the custodian-side credential reference. Guardian owns that
record, stores it, and authorizes from it. The custodian's credential record, connection
record, discovery result, or setup state is **delegated custody** — never an
independently authoritative grant of Codexify account access. Possession of a
custodian-side credential, connection identifier, or token is not evidence of Codexify
account authority, and a custodian-side record that no Guardian binding references is
not usable state.

**B2 — Custody is not authority.** The custodian may hold provider credential material,
enforce its own scoped grants, and refuse a request. It may not grant, widen, infer,
reissue, or revoke Codexify account access. Every account-scoped invocation passes
through Guardian authorization, whether or not the custodian's own policy would also
permit it. A custodian that is unreachable, internally inconsistent, or mistaken fails
the invocation **closed**; it never becomes the deciding authority.

**B3 — Canonical ownership is preserved across scopes.** Account, operator, and
Codexify service/deployment ownership scopes remain exactly as in requirement 1. A
custodian's ownership scope does not change because a credential is stored in it, and a
service/deployment-owned custodian credential used for an account invocation remains
service-owned and still requires account-specific Guardian authorization. Connection
discovery, provider setup, credential existence, and credential validation each confer
**no** execution authority.

**B4 — Credential classes are distinct and non-substitutable.** The custodian's
credential vocabulary is classified explicitly, and no class substitutes for another:

| Class | Owner | Purpose | May authorize account execution? |
| --- | --- | --- | --- |
| Deployment enforcement secret (runtime guard) | Codexify service/deployment | Makes the custodian's runtime surface fail closed | **No** — never presented for execution |
| Operator administrative token | Operator | Custodian-side administration: connection setup, token issuance, revocation | **No** — operator path only |
| Scoped persistent runtime token | Guardian, per account | Account execution against named custodian connections | **Yes** — the only class used for it |
| Provider credential | Account or provider | The provider's own credential, held by the custodian | **No** — it is what the custodian spends, not what authorizes it |

A failure in one class never falls back to another, in either direction, consistent with
ADR-092's lane rule. In particular, a scoped-token failure does not escalate to the
operator or deployment class, and the operator class does not reach account execution.

**B5 — Ordinary execution requires an explicitly scoped persistent token.** Account
execution uses a scoped persistent token whose grant names the custodian-side
connections that account may use. Unscoped, master, bootstrap, or JWT-class custodian
credentials are never used for account execution. Every issued scoped token carries an
explicit, non-empty grant, because an empty grant means unrestricted rather than
deny-all; and because token updates replace a stored policy wholesale, every update
carries the complete grant rather than a delta.

**B6 — The deployment enforcement secret is not an execution credential.** The
deployment-scoped enforcement secret is accepted as a deployment-level mechanism that
makes the custodian's runtime surface fail closed by configuration, subject to four
conditions carried forward unchanged: it is **service-owned and operator-custodied**;
it is **never used for execution** — never in adapter configuration, a model context, a
queue, a command, or a user-visible API; the deployment is **fail-closed**, meaning a
missing guard prevents startup or promotion and environment changes require container
recreation and verification; and it is subject to **explicit privileged-secret
accounting**, so a leak is a credential incident requiring rotation and recreation.
Fail-closed startup is Codexify-side deployment-pipeline enforcement — a preflight, a
post-start assertion that the guard is present in the running container, and a
promotion gate — not a property the substrate provides.

**Rotation procedure.** Rotating the deployment enforcement secret follows a
fail-closed sequence, and every step is observable:

1. **Access shutdown / drain.** Stop admitting new custodian-backed invocations.
   In-flight invocations are not force-cancelled; their outcomes are recorded as
   unknown (B8).
2. **Configuration replacement.** Replace the secret in the host secret store.
3. **Container recreation.** Recreate the container. A plain restart does **not**
   re-read the environment file, so it does not apply the new value and must not
   be used for this purpose.
4. **Running-container verification.** Assert that the new value is actually
   present in the running container's environment, and that the old value is no
   longer accepted.
5. **Anonymous-request rejection.** Assert that a request carrying no credential
   and a request carrying the old value are both rejected.
6. **Controlled reopening.** Re-enable dispatch only after steps 4 and 5 pass.

**This procedure is not zero-downtime.** It introduces a window in which
custodian-backed execution is unavailable, and invocations during that window
fail closed. No continuity claim is made, and the ordering above is not evidence
of one. Because the deployment secret is never used for execution, invalidating
it does not invalidate scoped persistent tokens; what the drain protects is the
window in which the running container's actual enforcement state is uncertain.

**B7 — Execution-time authorization.** Guardian authorizes every invocation at dispatch
and revalidates at execution time, consistent with requirement 8. The custodian's own
grant check is a second, independent constraint; the intersection is what bounds
execution, and neither alone is sufficient. Authority is revalidated against Guardian's
current state, not against the custodian's view of it.

**B8 — Revocation is a sequence with a defined order and stated in-flight semantics.**
Guardian denial is **first and sufficient** to stop further dispatch: no queued attempt,
retry, resumed session, or re-dispatch of that invocation proceeds. Custodian-side
revocation — the scoped token and, where applicable, the connection grant — **follows**
Guardian denial; it removes the capability for subsequent calls. A provider-side
disconnect is a **distinct third step**, because a provider credential can be revoked
at the provider while Guardian and the custodian still hold apparently valid
references. These three steps are not interchangeable and none substitutes for another.

In-flight execution is stated rather than assumed. Once Guardian has dispatched and the
custodian has accepted the call, Guardian-side revocation **does not retroactively
unwind** an invocation already in progress at the provider: the correct disposition is
an **unknown outcome**, recorded as such — not as success and not as "did not happen".
A timeout, a lost response, or a cancellation carries the same ambiguity, and a
cancelled call may still have completed at the provider. Retry is a new attempt under
the same authorization state, never a continuation of a revoked one. Where the outcome
is uncertain, the invocation fails **closed** for any subsequent capability the
custodian would otherwise expose.

**B9 — Recovery.** Four dispositions are fixed, and none of them is left implicit.
Restoring Guardian state **must not revive a revoked binding**: the restore procedure
re-applies the revocation set to restored state before that state is used for
authorization, and a restored binding whose revocation status is unknown remains
unusable. A custodian-side binding that is unknown to Guardian, or inconsistent with
Guardian's record, remains **unusable** pending reconciliation or explicit
reauthorization; it is never treated as authorized by default. A custodian-side cleanup
failure **cannot restore Guardian authority** — a failed token or connection deletion
is reported as an outstanding obligation, and is never a reason to re-authorize. Account
deletion has an **observable cleanup outcome**: the outcome records, per account, which
Guardian-side records were removed and which custodian-side cleanups completed or
remained outstanding, and a cleanup that did not complete is visible rather than
silent.

**B10 — Interfaces are preserved.** The Connections bay remains the control surface and
the Command Bus remains the execution surface. This amendment authorizes no second
Settings surface, no second connection-identity authority, and no model-facing gateway
API. The custodian is the `runtime_binding.adapter` behind ordinary provider entries,
never a catalog entry of its own, and native provider integrations keep their existing
precedence.

**B11 — The first authorized implementation class.** The first slice authorized by this
amendment, if it is accepted, is internal-only and bounded: reviewed read-only actions
only, drawn from a server-controlled allowlist rather than from a runtime catalog or a
request-supplied list; explicit Guardian permission checks on every invocation;
explicitly scoped connection selection with no reliance on a default or shared
connection; sanitized provider outcomes that never carry raw provider text or
credential material; and **no general write access**.

**B12 — Explicit dispositions.** No authority condition is left to inference. Each
of the following fails closed, with outcomes drawn from ADR-024's canonical
vocabulary:

| Authority condition | Disposition |
| --- | --- |
| Scoped token or grant missing | `denied` — no custodian call is made |
| Binding or scoped token revoked | `denied`; no subsequent dispatch, retry, or re-dispatch of that invocation |
| Restored state whose revocation status is unknown | unusable pending reconciliation or explicit reauthorization |
| Request presenting another account's token or connection | `denied` before credential lookup, so no existence is leaked |
| Custodian unreachable, internally inconsistent, or authority uncertain | `unavailable`; never a fallback to another account's credential |
| Deployment secret presented on an account path | refused — it authorizes nothing |

### C. Proof still required

Acceptance of this amendment authorizes no runtime behavior. Before any custodian-backed
execution is qualified, runtime proof must establish: that account-scoped authorization
is enforced at execution time and not only at dispatch; that revocation prevents
subsequent dispatch and retries, and that in-flight outcomes are recorded as unknown
where that is the truth; that a custodian-side cleanup failure leaves Guardian's denial
intact; that a restored Guardian state does not revive a revoked binding; that
cross-account use of a custodian credential is refused; and that the deployment
enforcement secret's rotation closes the anonymous-access window it is intended to
close. Guard rotation, cross-account isolation, and OAuth callback correlation remain
separately gated, as does public multi-user release qualification. A working deployment
configuration answers none of the questions in this amendment.

### D. Human acceptance required

**This amendment becomes accepted governing architecture only on explicit human
acceptance.** Until then it is a proposal: the accepted requirements 1–13 stand alone,
no custodian-backed implementation may be written against it, and the integration
program remains held at the gate that precedes implementation. Proposal status is not
approval, and this section must not be cited as an authority to build.
