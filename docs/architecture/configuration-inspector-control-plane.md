# Configuration Inspector Control-Plane Contract

## Status and purpose

This document is the implementation-oriented contract for the accepted
Configuration Inspector boundary in
[ADR-095](adr/095-configuration-inspector-operator-control-plane-boundary.md).
Resonant Jones accepted ADR-095 on 2026-09-29. The bounded v1 backend
implementation follows this contract; any expansion beyond it requires a
separately scoped, approved task.

The bounded v1 backend projection is implemented in commit
`dc77599ec50c9710eda2ea60795f383a204de44b`. Its focused evidence and known
validation limitation are recorded in the
[2026-09-29 backend proof](proofs/runtime/2026-09-29-configuration-inspector-v1-backend-proof.md).
The frontend Inspector is implemented with code-path and focused test evidence
for its Settings launcher, read-only snapshot view, manual refresh, and bounded
failure states. It retains only the current opening's request in browser memory;
it creates no durable snapshot store. Live supported-path frontend qualification
remains unproven. This does not change release support.

The Inspector is a read-only operator projection over existing configuration
authorities. It reports only bounded, non-secret installation posture whose
owner and evidence can be named. It does not own settings, authorize account
access, resolve new precedence, or decide release support.

## Authority and trust boundaries

Guardian coordinates the projection; each source subsystem remains
authoritative for its own configuration. A projection joins descriptions and
safe readbacks, not authority.

| Node or boundary | Authority and contract limit |
|---|---|
| Installation operator to Guardian | require_operator_auth establishes operator authority for this route. It does not establish an account principal or permission to read account-owned content. |
| Supported-profile owner to Guardian | Owns allowed/default profile posture. It does not establish provider or model availability. |
| Provider/egress owners to Guardian | Own provider policy, provider selection and outbound policy in their existing scopes. The projection must preserve their boundaries and must not probe them. |
| Guardian process to route inventory | May report routes mounted in this responding Guardian process. It cannot infer request authorization, end-to-end behavior, health or release support. |
| Guardian to Whoosh'd/runtime inventory | A separate runtime surface may report inventory or availability. The Inspector must not trigger startup or a probe and must not call inventory availability configured or served. |
| Guardian to application accounts | Account, thread, Persona, memory, document and connector-grant owners remain private to their account-scoped authorities. Operator status grants no access. |
| Guardian to secret-bearing configuration | Credential owners retain custody. The Inspector receives no secret values and returns no partial or masked fragments. |

The threat model includes honest-but-buggy components returning stale or
incomplete values, an unauthorized caller seeking protected state, a
compromised client attempting arbitrary lookups, and an authorized operator
requesting secrets or account-owned values beyond the installation posture.
Enforcement must be server-side and fixed-scope; UI wording is not a security
boundary.

## Endpoint and caller authority

The sole initial endpoint is:

**GET /api/operator/configuration**

The future route must depend on
guardian.core.dependencies.require_operator_auth. ADR-092 controls the
operator-purpose session and credential semantics. The route does not resolve
an account/user principal and rejects account or guest credentials as defined
by that boundary.

Do not use guardian.routes.admin.require_admin as the Inspector authority
dependency. It is a separate legacy admin gate.

The route is exposed inside the existing **admin** route family and its
supported-profile gate, using the existing
CODEXIFY_ENABLE_ADMIN_ROUTES posture. This flag and profile gate control
mounting only; authentication remains independently required on every request.
Do not add an Inspector-specific feature flag. If the existing route-family
gate cannot safely contain the endpoint, stop the implementation task with
NEEDS_FOLLOWUP and return to architecture review.

The endpoint is GET-only. It has no query parameters. It must not accept
arbitrary environment-variable names, configuration keys or paths, filesystem
paths, account IDs, thread IDs, Persona IDs, or connector credential
selectors. No method or parameter may turn the projection into a configuration
shell.

## V1 information domains

Only O02, O15, O07, and O08 are authorized. Each field must name its owning
subsystem and evidence claim.

### O02 — Supported-profile posture

May report safe, non-secret profile information already resolved by the
supported-profile owner:

- selected profile name and version;
- surface or profile class;
- validity/posture;
- bounded route-policy summary.

Report profile policy separately from runtime state. A valid or selected
profile is not proof that a provider, model, service, or route is available.

### O15 — Mounted Guardian route inventory

May report the bounded mounted-route inventory already available from Guardian
startup/runtime state for the responding process.

Label it as an observation for that Guardian process. Mounted does not mean
authorized, healthy, implemented end to end, or release-supported. Do not
project arbitrary route configuration flags as though they were all effective
or independently supported.

### O07 — Provider and egress posture

May report safe policy posture when existing owners can establish it, such as:

- provider policy class or selected configured provider class;
- local-only posture;
- whether cloud providers are allowed;
- safe egress-policy posture; and
- the supported-profile relationship.

Do not expose API keys, provider credentials, raw environment content, or
credential-bearing URLs. Do not call the provider or discover models to
populate this section. Configured or permitted provider is not available
provider.

### O08 — Local inference target posture

May report only a bounded, non-secret Guardian-side configured logical or
exact target when its existing owner can safely resolve that value.

Keep these claims separate:

1. supported-profile policy;
2. Guardian configured logical/exact target;
3. Whoosh'd or other runtime inventory;
4. runtime identity; and
5. served-model provenance for an actual request.

Do not synthesize a single effective_model. Do not expose local API keys,
credential-bearing endpoints, or arbitrary paths. An advertised model is not
proof that a particular request was served by that physical model.

## Explicitly excluded information

V1 returns no individual values from U01–U17 application/account/client
families and no values from other operator, developer, compatibility, or
unresolved families outside the four authorized domains.

Examples explicitly excluded:

- account identity or memory policy;
- Persona authored values or system prompts;
- thread inference or retrieval choices;
- user connector setup, grants, and OAuth state;
- documents, messages, conversation state, browser-local preferences,
  scratchpads, and cached content;
- database DSNs, Redis URLs, auth secrets, API keys, provider credentials,
  OAuth/session/JWT tokens, private keys, attachment grants, webhook secrets,
  and credential-bearing endpoints;
- desktop credentials, federation trust secrets, Watchdog credentials,
  coding-agent credentials, TTS secrets, and optional/unproven legacy paths.

Operator ownership of the installation is not account-data authorization.
Documentation may name an excluded domain and its owner, but v1 must not
project its value.

## Evidence semantics

These labels are conceptual contract semantics, not canonical runtime tokens.
They describe what a claim means, not a required lifecycle:

| Claim | Required evidence |
|---|---|
| Declared | A source contains a value/default, but the owning resolver has not been shown to select it. |
| Resolved | The named existing owner deterministically reports the safe selected value for the stated scope. |
| Observed | Runtime evidence establishes a state/result for the stated process or scope. |
| Unavailable | The value cannot safely be determined or exposed, or conflicting authorities prevent a truthful unified claim. |

Do not add protocol tokens as part of this documentation task. A later token
proposal requires a separate canonical-token review.

An environment value, Compose value, Pydantic Settings field, catalog entry,
browser cache, or health result alone does not prove an effective
configuration value. Health is not configuration authority. A configured
provider is not an available provider; a configured target is not a served
physical model; a mounted route is not an authorized or supported route.

## Response-contract principles

Do not implement response models in this task. The later response must be
explicit, structured, and allowlisted. It must semantically support:

- snapshot timestamp;
- responding Guardian process scope;
- separate O02, O15, O07, and O08 sections;
- evidence claim per field or section;
- owning subsystem/resolver identity;
- conflict or unavailable reason where relevant; and
- links or references to separate runtime-health/inventory evidence where
  useful.

Process identity and time must be sufficient to scope a local observation; they
do not create a historical store or cross-process authority. Do not serialize
arbitrary dictionaries of environment values, an entire Settings object,
generic model_dump() output, a whole provider registry, a whole supported
profile manifest, or raw health payloads. A future implementation must choose
and project an explicit allowlist.

## Redaction and privacy rules

Never return:

- API keys, passwords, OAuth tokens or grants, session tokens, JWT secrets,
  client secrets, private keys, webhook secrets, or attachment grants;
- credential-bearing DSNs, URLs, or endpoints;
- raw or partial/masked credential fragments; or
- raw environment contents.

Safe metadata is limited to values such as configured/not configured, owner,
source class, unavailable, and an already-redacted validation/posture state.
Do not emit raw exception text if it may contain credentials, URLs, account
data, or environment content.

Do not return account/user-owned memory, Persona, thread, connector, document,
message, preference, scratchpad, or cached values.

## Process scope and side-effect prohibition

The response describes the process serving the request and bounded local
owners only. It is not a fleet or cluster view, a cross-worker/client
aggregation, historical state, or durable audit evidence. Do not write a
snapshot, receipt, cache authority, event, or configuration value.

The Inspector request itself must not:

- make an external network call or provider/model probe;
- perform a completion or validate a credential remotely;
- refresh OAuth;
- start Whoosh'd, download a model, enqueue work, or restart a process;
- mutate health/probe caches or write diagnostics;
- write Postgres or Redis; or
- change configuration.

Existing independent health and inventory surfaces can be linked or read
separately by an operator. The Inspector must not call them as a hidden probe
or mirror their full response. In particular, the existing LLM health path can
actively probe providers and update probe-cache state; it is not a
configuration-readback dependency for this endpoint.

## Failure behavior

Failure is truthful and bounded:

- report a field as unavailable when its value is unknown or unsafe;
- report conflict rather than selecting between competing owners;
- omit a field when even its safe posture cannot be established;
- keep the overall snapshot usable when one optional domain fails; and
- return only a safe classification/reason, never raw source data or secrets.

Do not guess, echo the first declaration, fall back to an unrelated resolver,
infer configuration from health, or collapse conflicting sources into a
synthetic value.

## Existing authority debt

The Inspector must preserve and not resolve:

- core/legacy settings startup timing;
- authentication-key precedence;
- database endpoint precedence;
- the separate TTS selector precedence; and
- revisionless profile/model fallback.

These are separate authority questions. The Inspector cannot become a hidden
precedence resolver.

## ADR-094 non-overlap

ADR-094 remains the independent authority for account-scoped execution
credentials. ADR-095 does not supersede or modify it. The Inspector:

- does not return execution credential values or references;
- does not inspect account-scoped execution secrets;
- does not use operator authentication to access account-owned credentials;
- does not decide credential ownership, funding, or execution eligibility; and
- may show only secret-free installation posture already authorized under
  O07/O08, without implying credential usability.

Any later credential-related display must remain secret-free and be reviewed
against ADR-094's owner-scope and execution-time authorization rules.

## Implementation invariants

A later runtime implementation must preserve all of the following:

1. Guardian coordinates; existing configuration owners remain authoritative.
2. One operator-only principal boundary: require_operator_auth.
3. Account and guest credentials do not gain operator authority.
4. One endpoint: GET /api/operator/configuration.
5. Existing admin route-family and supported-profile exposure posture is reused.
6. Route exposure is not request authorization.
7. No new principal, token purpose, API key, admin-token scheme, RBAC system, or
   Inspector feature flag.
8. Only O02, O15, O07, and O08 may appear in the v1 projection.
9. No user/account values, secrets, or arbitrary lookups.
10. Evidence remains declared, resolved, observed, or unavailable by meaning;
    no runtime token is added here.
11. The snapshot is scoped to the responding process and is not persisted.
12. The request performs no active probe, external call, completion, enqueue,
    process start/restart, cache mutation, or database/Redis/configuration
    write.
13. Health, provider availability, model inventory, and served provenance stay
    distinct from configuration.
14. Authority conflicts fail truthfully without new precedence.
15. ADR-094 remains unchanged and outside Inspector authority.
16. No release claim changes; 00-current-state.md remains release truth.

## Future expansion gates

Any expansion beyond O02/O15/O07/O08 requires a separate bounded architecture
review naming the source owner, caller authority, privacy/secret boundary,
evidence strength, conflict policy, process scope, failure behavior, and proof
required. Adding user-owned data, cross-process aggregation, history,
persistence, active probing, mutation, or a new exposure gate requires an
explicit new decision. Catalog membership alone does not authorize expansion.

## Future runtime proof requirements

A later implementation task must prove at least:

1. Unauthenticated requests are rejected.
2. Account credentials without operator purpose do not gain Inspector
   authority.
3. A valid operator credential succeeds through require_operator_auth.
4. No secret value or masked/partial credential appears.
5. No account/user-owned value appears.
6. Only O02/O15/O07/O08 are returned.
7. Mounted-route evidence is limited to the responding process.
8. Provider configuration is not labeled provider availability.
9. A configured local target is not labeled the served physical model.
10. The Inspector request makes no external network call.
11. The Inspector request makes no database write.
12. The Inspector request makes no Redis or configuration write.
13. Partial resolution failure is represented as unavailable/conflict without
    unsafe detail.
14. Existing Settings, Connections, provider, and profile owners are
    unchanged.
15. ADR-094 credential authority remains unchanged.
16. No supported Beta or release claim widens.

These are future proof gates, not tests or implementation work authorized by
this contract alone.

## Documentation relationships

- Release truth: [00 Current State](00-current-state.md).
- Governing accepted decision: [ADR-095](adr/095-configuration-inspector-operator-control-plane-boundary.md).
- Planning: [Configuration Operator Inspection Plan](configuration-operator-inspection-plan.md).
- Inventory: [User-Facing Settings Catalog](user-facing-settings-catalog.md).
- Resolver reconnaissance: [Configuration Authority Path Census](config-authority-path-census.md).

The plan, catalog, and census remain non-runtime authorities.
