# ADR-095: Configuration Inspector Operator Control-Plane Boundary

**Status:** Accepted
**Date:** 2026-09-29
**Accepted:** 2026-09-29
**Human approver:** Resonant Jones

## Acceptance

Resonant Jones accepted this decision as written on 2026-09-29. Acceptance
removes the pending-human-acceptance prerequisite for a future implementation
task. It does not itself authorize runtime code changes; implementation still
requires a separately scoped, approved task and its required proof.

## Context

Codexify now has two documentation inputs for configuration work:

- The [User-Facing Settings Catalog](../user-facing-settings-catalog.md)
  inventories 55 families and records audience, scope, owners, evidence, and
  possible UI disposition. It is inventory, not runtime configuration
  authority.
- The [Configuration Operator Inspection Plan](../configuration-operator-inspection-plan.md)
  describes a future read-only operator view. It is planning doctrine, not an
  API, resolver, or runtime authority.

Neither document authorizes an authenticated aggregation endpoint. The first
backend projection therefore needs a bounded authority, access, evidence, and
failure contract before implementation.

Guardian already has an operator authentication dependency,
guardian.core.dependencies.require_operator_auth, and a supported-profile
route-registration path. The admin route family is gated by the existing
CODEXIFY_ENABLE_ADMIN_ROUTES setting as well as supported-profile posture.
These exposure controls are distinct from authentication. ADR-092 governs
operator-purpose authentication. The legacy
guardian.routes.admin.require_admin helper has different admin-token and
debug/private-preview semantics and is not the Inspector's authority boundary.

Existing owners do not form one configuration resolver. Profile policy,
provider selection, egress policy, Guardian's configured local target,
Whoosh'd inventory, and served-model provenance answer different questions.
Health endpoints are also a separate surface; for example, the LLM health
path can probe a provider and update probe cache state. Turning health into a
configuration authority would blur those claims and side effects.

docs/architecture/00-current-state.md remains release truth. The latest
complete supported-Compose qualification recorded there is HOLD; this
proposal changes no release or support posture.

## Decision

### 1. Inspector role

The Configuration Inspector is a **read-only operator projection over
existing configuration authorities**. Guardian coordinates an allowlisted
view; it does not become the owner or resolver of the underlying settings.

The projection may identify a configuration domain and its owner, report
bounded non-secret posture, report a safe value proven by that domain's
existing resolver, report a process-scoped observation, and report conflict or
unavailability. It may link to a separate runtime-health or inventory surface.

The Inspector must not own or mutate configuration, introduce precedence,
resolve arbitrary environment or file paths, persist settings or snapshots,
become a generic settings service, inspect account-owned values, expose
credentials, or decide release support.

### 2. Operator principal

The future route must use
guardian.core.dependencies.require_operator_auth. ADR-092 remains
authoritative for the exact operator_session purpose and the separation of
operator, account, and Hosted Room guest credentials.

The Inspector creates no principal, token purpose, API key, admin-token scheme,
or RBAC mechanism. It does not resolve an account or user principal.
Operator authentication is not permission to inspect an account's Persona,
thread, memory, connector grant, document, or other user-owned data.

The route must not use guardian.routes.admin.require_admin as its authority
dependency. That helper's separate admin-token/debug/private-preview behavior
does not replace the operator-authentication boundary.

### 3. Route namespace and methods

Reserve GET /api/operator/configuration as the sole initial Inspector route.
It returns one bounded snapshot for the responding Guardian process.

No POST, PUT, PATCH, DELETE, action, mutation, arbitrary-key lookup, or
arbitrary environment/configuration lookup is authorized. The route has no
query-parameter contract. Account IDs, thread IDs, Persona IDs, filesystem
paths, environment-variable names, configuration paths, and connector
credential selectors must not select or widen the projection.

### 4. Route exposure

The proposed route remains inside the existing admin/operator route exposure
posture: the admin route family, its supported-profile route gate, and
CODEXIFY_ENABLE_ADMIN_ROUTES. The route namespace remains
/api/operator/configuration; mounting it within that exposure family does
not make it an account-admin route.

require_operator_auth independently authorizes each request. A supported
profile or route-family flag controls exposure only; neither grants request
authority. No Inspector-specific feature flag is proposed. If implementation
inspection shows that the existing route-family gate cannot safely contain
this route, the implementation task must stop with NEEDS_FOLLOWUP for
architecture review instead of adding a new gate.

### 5. Authorized v1 projection

Only these four catalog families are authorized:

| Family | Bounded information | Required distinction |
|---|---|---|
| **O02 — Supported-profile posture** | Safe profile name, version, surface/profile class, validity/posture, and bounded route-policy summary when the profile owner can report them. | Supported-profile policy is not runtime availability. |
| **O15 — Mounted Guardian route inventory** | Existing startup/runtime route inventory for the responding Guardian process. | Mounted does not mean authorized, healthy, implemented end to end, or release-supported. |
| **O07 — Provider / egress posture** | Safe provider-policy class, local-only/cloud allowance, egress posture, and supported-profile relationship where existing owners can establish them. | Configured or allowed provider does not mean available provider. |
| **O08 — Local inference target posture** | A bounded, non-secret Guardian-side configured logical or exact target only when the existing owner safely resolves it. | Keep profile policy, Guardian configuration, Whoosh'd inventory, runtime identity, and served-model provenance separate; do not invent one effective_model. |

These families are the entire v1 runtime-projection scope. The catalog's other
families are not implicitly authorized because they appear in the inventory.

### 6. Excluded configuration and user data

V1 exposes no values from U01–U17 application/account/client families and no
values from other operator, developer, compatibility, or unresolved families
outside O02, O15, O07, and O08.

In particular, the Inspector excludes auth secrets, database DSNs, Redis URLs,
API keys, provider credentials, OAuth grants, Persona prompts, identity or
memory values, thread inference/retrieval settings, connector credentials,
documents, messages, browser caches, scratchpads, desktop credentials,
federation secrets, Watchdog credentials, coding-agent credentials, webhook
secrets, TTS secrets, and optional or unproven legacy configuration.

Operator ownership of an installation does not grant access to
account-owned content. Documentation may identify those ownership boundaries;
the backend projection does not return their individual values.

### 7. Evidence semantics

The four terms below are contract semantics, not runtime protocol tokens or a
mandatory lifecycle:

| Claim | Meaning |
|---|---|
| **Declared** | A source contains a value or default; selection by the owning resolver is not established. |
| **Resolved** | The existing owning resolver deterministically reports a safe selected value for the stated scope. |
| **Observed** | Runtime evidence establishes a state or result for the stated process/scope. |
| **Unavailable** | A value cannot safely be determined or exposed, or competing authorities prevent a truthful single claim. |

A value is not effective merely because it appears in an environment, Compose,
Pydantic Settings, browser cache, catalog, or health payload. A resolved claim
requires the owning resolver. An observed claim requires runtime evidence for
the scope named. Do not add runtime tokens in this task; any later tokenization
requires a separate canonical-token review.

### 8. Process-local scope

The first snapshot describes only the **responding Guardian process and its
bounded local configuration owners**. It is not fleet-wide, cluster-wide,
cross-worker, cross-browser, historical, or a durable receipt.

No configuration database, snapshot table, event log, cache authority, or
historical inspection store is authorized. Future multi-process aggregation
requires separate review of identity, generation, freshness, partition and
stale-observation behavior.

### 9. No active probing

The Inspector request itself must not call remote providers, perform model
completions, validate credentials remotely, refresh OAuth, start Whoosh'd,
download models, enqueue work, restart processes, mutate health caches, write
Postgres or Redis, write diagnostics, or alter configuration.

Configuration inspection and runtime probing remain separate surfaces.
Existing health or inventory evidence may be linked or inspected separately;
the Inspector must not invoke an active health probe merely to fill a field.

### 10. Secret and privacy boundary

The response must never contain secret values or even partial/masked
credential fragments. Prohibited content includes API keys, passwords, OAuth,
session and JWT secrets, private keys, webhook secrets, attachment grants,
credential-bearing DSNs, and raw environment dumps.

Safe metadata may state configured/not configured, owner, source class,
unavailable, or a redacted validation/posture result where the credential
owner already provides that metadata. A generic environment serializer is
prohibited.

### 11. Response principles

The later response must be explicitly allowlisted and structured. Its semantic
shape must support:

- a snapshot timestamp and responding-process scope;
- separate supported-profile, mounted-route, provider/egress, and local-target
  sections;
- an evidence claim and owner/resolver identity for each section or field;
- a conflict or unavailable reason where safe and relevant; and
- clearly separate runtime-health or inventory references where useful.

Do not pass through arbitrary environment dictionaries, a full Settings
serialization, generic model_dump() output, raw provider-registry objects,
raw supported-profile manifests, or a whole health response. The later
implementation must deliberately project an allowlisted schema; this ADR does
not implement that schema.

### 12. Failure behavior

When a safe value cannot be established, the field is unavailable, a conflict
is reported, or the unsafe field is omitted according to the later response
contract. The route remains usable when one optional domain fails resolution.

The Inspector must not guess, choose the first declaration, apply an unrelated
fallback, create precedence, infer configuration from health, or synthesize a
single value from conflicting authorities. A local resolution failure does not
justify exposing additional source data.

### 13. Existing authority and known debt

Existing configuration owners remain authoritative. This proposal preserves,
without resolving or flattening, the known seams:

- core/legacy settings startup timing;
- auth-key precedence;
- database endpoint precedence;
- TTS selector precedence; and
- revisionless profile/model fallback.

The Inspector may eventually identify a conflict or unavailable value when
that can be done safely. Resolving these seams requires separate architecture
work.

### 14. ADR-094 remains separate

ADR-094 remains unchanged and continues to govern account-scoped execution
credential authority. ADR-095 neither supersedes nor extends it. The Inspector
does not expose execution credentials, credential references, or account-scoped
execution secrets, and operator authentication does not grant access to them.
Any future credential posture must remain secret-free and subordinate to
ADR-094.

### 15. Documentation hierarchy

- **Release truth:** docs/architecture/00-current-state.md.
- **Governing decision:** Accepted ADR-095.
- **Normative Inspector contract:** docs/architecture/configuration-inspector-control-plane.md.
- **Planning and inventory inputs:** the Configuration Operator Inspection
  Plan, User-Facing Settings Catalog, and Configuration Authority Path Census.

The planning and inventory inputs remain non-runtime authorities.

## Alternatives considered

1. **Add inspection to ordinary Application Settings.** Rejected because an
   installation-operator projection has a different principal and scope from
   account/user settings. Combining them would blur authority and risk exposing
   installation data through a user surface.
2. **Expose all environment variables.** Rejected because it bypasses owning
   resolvers, exposes secret-bearing and topology-sensitive values, and cannot
   distinguish declared inputs from selected configuration.
3. **Extend /health into the complete Inspector.** Rejected because health
   reports operational observations, not configuration authority, and some
   health paths actively probe providers or update probe caches.
4. **Use guardian.routes.admin.require_admin.** Rejected because it is not
   the operator-purpose dependency selected by ADR-092 and carries separate
   admin-token/debug/private-preview semantics.
5. **Create a configuration database.** Rejected because it would establish a
   competing source of truth, persistence and precedence without an owner or
   migration contract.
6. **Aggregate all 55 catalog families immediately.** Rejected because many
   families are user-owned, secret-bearing, intentionally separate, unresolved,
   or lack safe owner-specific readback. The catalog is inventory, not a grant
   to expose every row.

## Consequences and deferred work

The first runtime task can implement one authenticated, process-local,
non-persistent GET projection without changing configuration owners. It must
use a fixed allowlist, preserve the evidence distinctions above, and return
unavailable rather than manufacturing an effective value.

Runtime route implementation, response models, resolver work, feature flags,
frontend UI, persistence, snapshots, configuration mutation, conflict
resolution, broad catalog coverage, and any release-support decision are
deferred. ADR-095 is accepted; implementation still requires a separately
scoped, approved task.

## Runtime and release boundary

This is an accepted architecture decision only. It adds no endpoint, route,
model, resolver, token, feature flag, persistence, probe, UI, or release claim.
No current runtime endpoint is the canonical Configuration Inspector.
00-current-state.md remains release truth.

## Governing and related records

- [ADR-039: Operator / User Access Boundary](039-operator-user-access-boundary.md)
- [ADR-071: Connections Control Plane Boundary](071-connections-control-plane-boundary.md)
- [ADR-072: Bounded Settings and Connections Route Promotion](072-bounded-settings-and-connections-route-promotion.md)
- [ADR-074: Tester Provider / Model Configuration Authority](074-tester-provider-model-configuration-authority.md)
- [ADR-082: Persona Profile Manifest and Binding Authority](082-persona-profile-manifest-and-binding-authority.md)
- [ADR-092: Credential Purpose and Mixed-Principal Authentication Boundary](092-credential-purpose-and-mixed-principal-authentication-boundary.md)
- [ADR-094: Account-Scoped Execution Credential Authority](094-account-scoped-execution-credential-authority.md)
- [Configuration Operator Inspection Plan](../configuration-operator-inspection-plan.md)
- [Configuration Inspector Control-Plane Contract](../configuration-inspector-control-plane.md)
- [00 Current State](../00-current-state.md)
