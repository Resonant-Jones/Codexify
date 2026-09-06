---

tags:

* architecture
* adr
* imprint
* identity
* persona-studio
* ownership
  aliases:
* ADR-058
* Imprint UI Deprecation and Identity Ownership

---

# ADR-058: Imprint UI Deprecation and Identity Ownership

## Status

Accepted

## Date

2026-04-15

## Acceptance revision

Accepted 2026-09-05 after reconciliation with the implemented Persona Profile
architecture governed by ADR-082. This revision ratifies the ownership
boundary; it does not perform the remaining runtime or frontend convergence.

## Canonicalization history

This decision was originally stored as ADR-005, which collided with the later
Accepted Runtime Mode and Account Boundary Invariants. Human canonicalization
retained Runtime Mode as ADR-005 and moved this decision to ADR-058. Historical
references to the former Imprint ADR-005 remain historical evidence and must
not be reinterpreted as references to Runtime Mode.

ADR-058 remained Proposed when ADR-082 was accepted. ADR-082 therefore aligned
with this boundary without accepting it. The 2026-09-05 ratification accepts
ADR-058 and preserves ADR-082 as the governing authority for canonical Persona
Profile manifests, bindings, revisions, selection, and accepted-task execution.

## Context

The original Imprint Zero concept combined durable user modeling, relational
fit, and Persona-adjacent prompt authoring. Codexify now has distinct surfaces
and materially implemented canonical Persona Profile machinery:

* `PersonaProfileManifest` as the authored profile configuration object;
* immutable Persona Profile revisions;
* server-owned account/profile binding state;
* thread pins to an exact profile revision;
* `PersonaSelectionSnapshot` captured at task acceptance; and
* worker execution of the accepted Persona revision.

Legacy Imprint and Persona machinery remains active alongside that canonical
path. In particular, Imprint acceptance still writes legacy Persona state,
Settings still exposes legacy Persona controls through the Imprint lane, and
status/inspector surfaces still report legacy assumptions. Those are current
implementation facts and migration debt, not a second accepted authority.

Durable identity remains separately governed. Current lifecycle-shaped identity
data includes the `personal_facts`, `personal_fact_evidence`, and
`personal_fact_revisions` seams. Their presence does not establish a supported
end-user surface or make either Imprint or Persona Studio their owner.

## Problem

Without one accepted boundary, four adjacent concerns can become competing
authorities:

1. Guardian's stable first-person actor identity;
2. durable user identity and memory;
3. authored Persona Profile configuration; and
4. relational/presentation synthesis and diagnostics.

The implemented canonical Persona Profile path makes the ambiguity operational:
legacy Imprint acceptance and Settings can still author mutable legacy Persona
state even though ADR-082 assigns authored Persona intent, revision history,
binding, and deterministic accepted-task execution to the canonical profile
model.

## Decision

Codexify adopts the following ownership doctrine.

### Guardian

Guardian is the stable platform actor and the only stable first-person actor in
the current runtime. Persona Profiles and Imprint are additive configuration
and presentation layers. Neither may replace Guardian, rebind first-person
identity, or override base safety and policy rules.

### Durable user identity

Durable user identity remains outside Persona Studio and Imprint. Settings-owned
governance may expose durable identity and relational preferences, while
Personal Facts and any future MemoryOS identity seams remain governed by their
own contracts, consent rules, and authority boundaries.

Neither saving a Persona Profile nor resolving an Imprint may infer, persist,
or claim durable user identity. This decision does not change MemoryOS
authority or make Personal Facts a Beta-supported product surface.

### Canonical Persona Profile

`PersonaProfileManifest` is the canonical authored configuration object for how
Guardian may be configured to operate as a Persona or profile. ADR-082 governs
its authority, serialization, account binding, immutable revisions, selection,
and execution semantics.

Canonical Persona Profiles own authored:

* profile identity and display intent;
* prompt configuration;
* requested model configuration;
* requested voice configuration;
* requested capabilities;
* requested retrieval configuration; and
* other profile intent governed by ADR-082.

Authored requests are not grants. Canonical account, Project, participant,
Connections, capability, retrieval, provider, and runtime policies remain
authoritative for what is available, authorized, and effective. Persona
Profiles do not own durable user identity.

### Imprint

Imprint is a **derived relational/presentation layer**. It may encode or
synthesize authorized interaction-shaping guidance such as:

* Guardian presentation name;
* preferred user address;
* style;
* grammar preferences;
* warmth or heat; and
* other relational presentation guidance.

Imprint is not:

* an authored Persona Profile;
* a second system-prompt editor;
* durable user identity authority;
* memory authority;
* model, tool, skill, or capability authority;
* connector, Project, participant, or retrieval authority; or
* runtime execution authority.

Derived relational synthesis may remain internally useful and may contribute
an additive prompt segment. Its derived output does not become canonical
authored Persona state merely because it is persisted, displayed, or used by a
legacy compatibility path.

The standalone Imprint UI is deprecated as a primary authored UI pattern. Any
retained Imprint surface must govern or explain relational/presentation state;
it must not author a parallel Persona or system prompt.

### Settings

Settings owns user-facing governance surfaces for durable identity and
relational preferences. Settings must not create a parallel Persona/Profile
persistence model.

A future simplified **My Guardian** editor may surface a subset of canonical
Persona Profile configuration. If implemented, it must edit the same canonical
Persona object as Persona Studio rather than copy, mirror, or synchronize a
second object. This decision deliberately does not define Default Guardian
Profile persistence or binding semantics.

### Persona Studio

Persona Studio owns advanced authored Persona Profile composition through the
canonical Persona Profile model. It does not own:

* durable user identity;
* Imprint-derived relational state;
* memory;
* account or Project authority;
* participant authority;
* connector credentials or authorization; or
* runtime execution grants.

### Diagnostics

System Prompt Inspector and related diagnostics report persisted, resolved,
acceptance-time, or executed/runtime truth only to the extent their evidence
supports those claims. They are observational and do not own or mutate any
layer they inspect. Combining multiple status endpoints does not promote a
diagnostic surface into identity authority.

## Current compatibility and migration debt

The following current behaviors are preserved as implementation facts, not
accepted architecture:

* `guardian/routes/imprint.py:accept_imprint()` activates an Imprint and calls
  the legacy Persona store to create/activate Persona state;
* `POST /api/imprint/persona` exposes direct legacy Persona mutation;
* `GET /api/imprint/status` reports active legacy Persona state alongside
  Imprint and prompt metadata;
* Settings still exposes legacy Persona editing/synchronization through the
  Imprint API family;
* legacy Persona resolution remains active in prompt assembly beside canonical
  Persona Profile resolution; and
* some built-in, environment, Flow, and historical compatibility paths remain
  revisionless.

Existing legacy Persona or Imprint rows may remain during migration. Their
existence, active flags, status projection, or prompt participation does not
supersede ADR-082 or silently reclassify them as canonical Persona revisions.

The next implementation slice must remove legacy Imprint -> Persona mutation
authority while preserving existing data and canonical Persona Profile
semantics. Data deletion, row migration, prompt changes, UI changes, and route
changes require separately scoped implementation and proof.

## Rationale

One authored profile authority avoids copy/synchronization conflicts between
Settings, Persona Studio, and Imprint. Keeping relational presentation separate
preserves useful adaptive behavior without turning derived synthesis into a
permission, identity, or execution control plane. Keeping Diagnostics
observational prevents a read model from acquiring authority merely because it
can describe resolved state.

The split also preserves the constitutional distinction between intent and
authority: authored Persona configuration expresses requested intent; server
control planes determine ownership, authorization, availability, and effective
execution.

## Consequences

### Positive

* Guardian actor semantics remain stable.
* ADR-082 has one compatible ownership boundary for authored Persona Profiles.
* Imprint retains a bounded relational/presentation role.
* Settings and Persona Studio cannot become parallel profile stores.
* Inspector surfaces remain read-only truth projections.
* Later convergence work has an explicit migration target without silently
  deleting or reclassifying legacy data.

### Negative

* Runtime and UI behavior temporarily continues to diverge from the accepted
  ownership model.
* Legacy rows, endpoints, tests, and labels require bounded migration work.
* Diagnostics must distinguish legacy, canonical, resolved, accepted, and
  executed state during the convergence period.

## Invariants

* Guardian remains the stable first-person actor.
* `PersonaProfileManifest` is the sole canonical authored Persona configuration
  object.
* Imprint is derived relational/presentation synthesis, not authored Persona or
  durable user identity.
* Imprint and Persona configuration cannot grant authority.
* Durable identity and MemoryOS authority remain separately governed.
* Diagnostics are observational only.
* Legacy state is compatibility/migration debt and is not silently canonical.
* No runtime, frontend, supported-profile, Beta, or release claim changes merely
  because this ADR is Accepted.

## Non-goals

This decision does **not**:

* modify runtime or frontend behavior;
* remove, migrate, or reinterpret legacy rows;
* change prompt assembly or Persona selection;
* implement a canonical inspection endpoint;
* define Default Guardian Profile persistence or binding;
* change account, Project, participant, Connections, capability, retrieval, or
  MemoryOS authority;
* make Personal Facts a supported user-facing feature; or
* widen the Beta or release promise.

## Follow-on implementation slices

1. Remove legacy Imprint -> Persona mutation authority while preserving
   existing data and canonical Persona Profile semantics.
2. Reconcile Settings and any future My Guardian editor with the canonical
   Persona object without introducing a second persistence model.
3. Convert prompt inspection to one canonical observational surface that labels
   legacy, canonical, acceptance-time, and executed state truthfully.
4. Reshape or remove standalone Imprint authoring UI in bounded, separately
   proven slices.

## Governing and related records

* [ADR-082: Persona Profile Manifest and Binding Authority](./082-persona-profile-manifest-and-binding-authority.md)
* [Identity Precedence Contract](../identity-precedence-contract.md)
* [IDDB Policy v1](../../iddb_policy_v1.md)
* [Persona Studio Spec](../persona-studio-spec.md)
* [00 Current State](../00-current-state.md)

## Notes

The convergence rule is compact: Guardian acts; durable identity remains
separately governed; canonical Persona Profiles own authored profile intent;
Imprint shapes relational presentation; Settings governs user-facing identity
and relational preferences; Persona Studio composes canonical profiles; and
Diagnostics observes.
