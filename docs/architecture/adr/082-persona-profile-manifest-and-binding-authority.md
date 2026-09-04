# ADR-082: Persona Profile Manifest and Binding Authority

**Status:** Accepted

**Date:** 2026-09-04

## Context

Persona Studio has two materially different current seams.

- The frontend maintains a broad browser-local draft for identity, model,
  voice, prompt, tools, skills, permissions, and retrieval configuration.
- Backend Persona Profile persistence currently stores only name, system
  prompt, model provider, model ID, and temperature. Those fields can enter
  the system-profile resolver and can be selected by chat threads.

The first is a client configuration surface; the second is a narrow
runtime-bearing persistence seam. Neither is yet a complete, account-scoped,
versioned Persona Profile manifest system.

Historical C07 artifacts accurately proved a bounded local-preview surface at
the time of their tests. They did not prove backend persistence, broad
configuration enforcement, connector execution, retrieval execution, voice
execution, or durable profile-revision semantics. Later code introduced the
five-field backend seam, so the historical local-only statement must not be
used as current implementation truth.

Without a single contract, a future YAML or JSON profile can accidentally
become a second source of account, Project, connector, or capability
authority. That would conflict with the existing authority boundaries:

- ADR-010 requires capabilities to pass through governed registration and
  runtime binding rather than a parallel permission universe.
- ADR-039 separates product-user access from operator authority.
- ADR-058 assigns authored runtime mask/profile composition to Persona Studio
  and durable identity governance elsewhere.
- ADR-069 keeps implementation evidence, support posture, and release claims
  distinct.
- ADR-071 keeps Connections configuration, authorization, health, and
  server-owned user-scoped credentials separate.
- ADR-081 assigns canonical Project ownership to Project authority, not to
  presentation or imported metadata.

This record establishes the architecture before full manifest persistence,
revision history, environmental binding, or runtime enforcement is added.

## Decision

### Canonical authored object

Codexify defines **PersonaProfileManifest** as the canonical typed
representation of authored Persona Profile configuration intent.

YAML and JSON are serialization formats only. They are not the canonical
object, an authority source, or an executable instruction. Browser
localStorage and a database JSON blob may cache or persist representations,
but neither alone defines the manifest contract or grants authority.

The conceptual attributes below are contract names, not
implementation-language-specific field syntax:

- **apiVersion** — manifest-schema compatibility, for example
  codexify.persona/v1;
- **profile identity** — a stable authored-profile identity that is distinct
  from an account owner, database row, or environment binding;
- **revision** — the immutable identity of one authored configuration
  snapshot;
- **identity and display configuration** — such as display name, description,
  avatar, or presentation choices, without durable-user-identity ownership;
- **prompt configuration**;
- **requested model configuration**;
- **requested voice configuration**;
- **requested capability references** — including tools, skills, and
  permission-shaped requests;
- **requested retrieval policy and source references**; and
- **non-secret connector intents or logical connection aliases** where an
  authored profile needs to name a desired connection.

The manifest records what an author asks a persona to be configured to use.
It does not record what any account, Project, participant, connection, or
runtime is authorized to grant.

### Schema compatibility and authored revision are separate

**apiVersion** and **revision** solve different problems and must never be
overloaded into one version field.

| Concept | Meaning | Required property |
| --- | --- | --- |
| apiVersion | The compatibility version of the manifest schema. | It determines how a manifest is parsed and validated. |
| revision | The identity of one authored Persona Profile configuration snapshot. | It identifies immutable historical configuration. |

A profile may have a stable profile identity across several revisions. A
revision may be represented by a monotonic sequence, an opaque immutable
identifier, or both, but a mutable integer that merely points at current state
is not enough to reproduce historical runtime configuration.

If a future thread binds a profile revision, it must bind an immutable
snapshot identified by that revision. Actual revision-history persistence and
thread-to-revision binding are deferred implementation work.

### Server-owned binding envelope

Codexify defines **PersonaProfileBinding** as the separate, server-owned
profile-to-environment binding envelope for a manifest or manifest revision.

It records server-derived or server-validated mappings and policy decisions
after the owning systems resolve them. It is authoritative for a profile's
binding state, but it does not supersede the canonical authorities for account
identity, Project ownership or access, participant relationships, Connections
authorization or credentials, capability grants, or runtime availability.

A binding may carry:

- a server-derived owning-account reference;
- server-validated permitted Project scope references;
- server-validated participant or contact policy references;
- profile activation state;
- non-secret connection or connector resolution mappings returned by the
  Connections control plane;
- environment-specific reference mappings; and
- the account, Project, and profile scope inputs needed by existing authority
  resolvers.

The binding is not a portable persona identity. It is server-owned state that
is created, validated, changed, and audited through the relevant canonical
control planes; those systems remain authoritative for the underlying values.

An imported YAML or JSON manifest must never self-assign:

- account ownership;
- Project access or Project ownership;
- participant or user access;
- connector credentials or credential scopes; or
- runtime execution permission.

An import may offer non-secret logical references as authored intent. The
server must validate, remap, approve, or reject those references against the
receiving account and environment. An imported profile identity must not
collide with or overwrite a server-owned binding merely because its text uses
the same identifier.

### References are not secrets

PersonaProfileManifest may contain stable logical references, such as a
requested connection alias or a requested retrieval source reference. It must
not contain:

- OAuth tokens;
- API keys;
- passwords;
- raw provider credentials;
- session credentials; or
- connection secrets.

Connections and server-side persistence remain the sole credential authority.
Serialization, import, export, diagnostics, and effective-configuration
inspection must preserve that boundary.

### Requested, available, denied, and effective configuration

Persona Studio and future profile APIs must distinguish four states rather
than treating a saved request as a runtime grant.

| State | Meaning |
| --- | --- |
| requested configuration | Authored intent in PersonaProfileManifest. |
| available configuration | Resources, references, catalogs, or capability inputs present in the receiving environment. Presence is not authorization or health. |
| denied configuration | A requested value rejected because it is invalid, missing, outside scope, unsupported, or disallowed by policy. |
| effective configuration | The subset that may actually reach a runtime after authority and applicable runtime/support policy are resolved. |

For capabilities, Persona Studio must not create a parallel authorization
resolver. It uses the existing effective capability resolver as its
capability-authority input:

    effective capabilities =
      profile requested ceiling
      ∩ resolved capability snapshot(account, project, profile)
      ∩ applicable runtime/support policy

The existing resolver's internal precedence remains:

    profile > project > account

ADR-082 neither duplicates nor silently changes that precedence. The
manifest's requested capability ceiling is an authored limit or request; it is
not a grant. A future effective-configuration view may report requested,
available, denied, and effective values, but it remains observational until a
separately authorized runtime-integration task exists.

### Connections and connector resolution

A manifest may request a logical Connection by alias or non-secret reference.
The Connections subsystem decides whether the corresponding connection:

1. exists;
2. belongs to the current account;
3. is configured;
4. is authorized; and
5. is healthy enough for a particular use.

Persona Studio does not own any of those decisions. Configuration presence
does not imply authorization, and authorization does not imply runtime health.
Logical connector references must be resolved through server-owned
Connection/control-plane authority, never through client-provided credentials
or an imported manifest.

### Project and participant scope

Project IDs, Project access, and participant or user policy are environmental
bindings, not portable persona identity.

Persona Studio may eventually provide an interface for requesting or editing
those bindings. The backend must validate every request against canonical
account, Project, and relationship authority. In particular, imported profile
text must not create a second Project-ownership or participant-authorization
surface. Project ownership remains governed by ADR-081 and its canonical
Project authority.

### Persona and identity sovereignty

This decision preserves the following boundary:

- Persona Studio owns authored runtime mask and profile composition.
- Persona Studio does not own durable user identity.
- Editing, validating, saving, importing, or exporting a profile does not
  write memory or infer durable user traits.
- A persona may consume authorized identity or context at runtime, but it
  does not own that identity or context.
- Profile import and export do not mutate durable identity.

ADR-058 remains Proposed. ADR-082 aligns with its ownership boundary and does
not accept, modify, or supersede it.

### Saving is not execution

Saving or validating a Persona Profile must not itself:

- create chat messages;
- invoke a model;
- execute a tool or capability;
- perform retrieval;
- invoke a connector;
- mutate memory;
- change provider health; or
- grant new authority.

Provider/model selection is requested configuration, not proof of provider
availability. A resolved Connection is not a connector invocation. An
effective-configuration inspection is observation, not a task acceptance or
runtime execution event.

### Compatibility with the current five-field resolver seam

The current runtime-bearing persisted projection is limited to:

1. name;
2. system prompt;
3. model provider;
4. model ID; and
5. temperature.

A future full-manifest persistence implementation may project these values
from PersonaProfileManifest through the existing system-profile resolver.
Broader manifest fields remain non-executing until each has an individually
implemented and proven enforcement seam. This decision does not require a
wholesale resolver rewrite.

## Current-truth boundary

This ADR is architecture doctrine, not a claim that the target model is
implemented.

| Current condition | Evidence posture |
| --- | --- |
| Browser-local Studio drafts carry broad profile configuration. | Code path |
| Backend profiles persist the five runtime-bearing fields and can be resolved for selected chat profiles. | Code path |
| Current backend Persona Profile persistence is not account-scoped. | Code path |
| Effective capability resolution already accepts account, Project, and profile scope with profile > Project > account precedence. | Code path |
| Connections separates configuration, authorization, health, and credential ownership. | Documented accepted contract |
| C07's bounded local-preview proof was test-proven at the historical time of its closeout. | Historical test proof |

The following remain unimplemented or unproven:

- full durable PersonaProfileManifest persistence;
- server-owned PersonaProfileBinding persistence;
- account-scoped Persona Profile APIs;
- immutable profile revision history;
- thread-to-profile-revision binding;
- an effective-configuration endpoint or resolver that reports requested,
  available, denied, and effective values;
- capability, retrieval, connector, or voice execution controlled by broad
  Studio settings; and
- provider inventory or runtime-health validation caused by profile selection.

No supported-profile configuration, release posture, Beta classification, or
claim in 00-current-state.md changes because of this ADR.

## Consequences

### Positive

- Persona profiles can become portable without exporting environmental
  authority or credentials.
- Future persistence has one authored object to validate rather than several
  competing local-storage, YAML, and database representations.
- Capability, Project, connection, participant, and identity authority remain
  in their existing owning systems.
- Historic runtime configuration can be reproducible once immutable revisions
  and thread bindings are implemented.
- The current five-field runtime seam remains a narrow, compatible migration
  path.

### Constraints and deferred implementation

Separate implementation tasks must define and prove, at minimum:

1. typed manifest validation, serialization, import, and export;
2. immutable revision storage and revision-aware thread binding;
3. server-owned binding persistence, account scoping, and environmental
   reference resolution;
4. requested/available/denied/effective configuration inspection;
5. individual enforcement seams for capabilities, retrieval, connectors, and
   voice; and
6. any release-posture change under ADR-069 and 00-current-state.md.

No such implementation, migration, route change, runtime behavior, or
supported-surface change is authorized by this ADR alone.

## Invariants

- No portable manifest may self-grant authority.
- No imported manifest may choose its authoritative owner account.
- Credentials remain server-owned.
- Project ownership remains governed by canonical Project authority.
- Existing capability-resolver precedence is not duplicated or changed.
- Persona configuration remains distinct from durable identity.
- Saving configuration is not runtime execution.
- Provider/model selection is not provider availability.
- Connection configuration is not authorization.
- Authorization is not health.
- Historical C07 evidence remains historical evidence.
- No Beta or release claim is widened.

## Governing and related records

- [ADR-010: Self-Extending Agent Plugin System](./010-self-extending-agent-plugin-system.md)
- [ADR-039: Operator / User Access Boundary](./039-operator-user-access-boundary.md)
- [ADR-058: Imprint UI Deprecation and Identity Ownership](./058-imprint-ui-deprecation-and-identity-ownership.md)
- [ADR-069: Codexify Beta Runtime Support Boundary](./069-codexify-beta-runtime-support-boundary.md)
- [ADR-071: Connections Control Plane Boundary](./071-connections-control-plane-boundary.md)
- [ADR-081: Project Ownership Authority](./081-project-ownership-authority.md)
- [Persona Studio Spec](../persona-studio-spec.md)
- [00 Current State](../00-current-state.md)

## Notes

ADR-082 establishes one ownership model before implementation creates a
second. Persona Studio may author the mask; it may not quietly inherit the
keys to the kingdom.
