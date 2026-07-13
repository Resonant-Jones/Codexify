---
tags:
* architecture
* adr
* operator
* user-boundary
* access-topology
  aliases:
* ADR-039
* Operator User Access Boundary
---

# ADR-039: Operator / User Access Boundary

## Status

Proposed

## Date

2026-06-30

## Context

Codexify is local-first today, but real users are already exercising more than one access shape.

Some people will run Codexify directly on the same machine that hosts the runtime. Some will run a home node and access it from another device. Some will use a private overlay network such as Tailscale or another VPN. Others may only be users of an instance hosted by someone else.

The existing supported beta posture remains local Docker Compose with local-only provider posture. This ADR does not widen that release promise. It records the product and architecture boundary needed before later implementation work adds configuration, routing, or hosted access surfaces.

The key distinction is that infrastructure control and product usage are related, but not identical.

## Decision

Codexify will treat `Operator` and `User` as separate access roles.

An `Operator` controls or administers infrastructure. A `User` consumes the Codexify experience through an available access path. One person may hold both roles, but Codexify must not assume that the active user is always the infrastructure operator.

This decision establishes the following canonical role model for future work:

| Role | Meaning |
|---|---|
| `Operator` | Person or entity responsible for deployment, runtime configuration, provider/network setup, backups, upgrades, uptime posture, and support decisions. |
| `User` | Person using the Codexify application experience, including chat, documents, workspace, gallery, or other user-facing surfaces. |
| `Host Operator` | Operator who hosts an instance for one or more other users. This may be a friend, household member, organization, steward, or future service provider. |
| `Self Operator` | User who also operates their own instance. This is the current solo/local-first default but not the only future topology. |

## Required Interpretation

Future features that touch deployment, network routing, provider configuration, uptime expectations, support posture, backups, or hosted access must explicitly name whether the surface is for an Operator, a User, or both.

A user-facing convenience must not silently become an operator authority surface. An operator setting must not assume the operator is the only person who will use the instance.

## Non-Goals

This ADR does not implement:

- authentication or authorization changes
- roles/permissions tables
- hosted SaaS behavior
- billing, stewardship tiers, or commercial packaging
- network profile storage
- auto-discovery or auto-switching
- remote access support beyond current documented beta claims

## Current-Truth Anchors

What is true now:

- Codexify remains local-first beta hardening on `main`.
- Local Docker Compose remains the supported install path.
- The supported provider posture remains local-only.
- Whoosh'd remains the supported Apple Silicon local runtime preset.

What is not yet true:

- Codexify does not yet ship a full operator/user role system.
- Codexify does not yet ship hosted multi-user access semantics.
- Codexify does not yet ship automatic topology detection or network profile switching.
- Docs-only role language must not be treated as runtime support.

What future tasks may assume:

- It is valid to design settings, onboarding, support docs, and topology docs around the Operator/User separation.
- It is valid to describe solo usage as `Self Operator` rather than collapsing all users into operator authority.
- It is valid to require future implementation tasks to state which role owns a new setting or action.

## Invariants

- User identity, persona identity, and operator authority remain separate concepts.
- Personas do not own infrastructure authority.
- Chat history is not operator identity.
- Deep identity consent must not be inferred from operator status.
- Runtime support claims remain bounded by `docs/architecture/00-current-state.md`.
- Operator surfaces must not silently widen supported beta promises.

## Consequences

This gives future Codexify work a cleaner language for:

- onboarding flows
- installation guides
- home-node setup
- support agreements
- Stewardship calls and support posture
- network profile configuration
- hosted-by-someone-else access
- mobile/client companion planning
- provider and runtime administration

The main cost is that future UI and docs must avoid the convenient but leaky assumption that every user is the operator. That is a useful constraint. It keeps authority visible instead of letting it evaporate into vibes and buttons.

## Implementation Guidance

Future implementation tasks should prefer explicit language:

- `Operator Settings` for deployment, runtime, network, backup, and provider administration.
- `User Settings` for personal UX, interface preferences, workspace behavior, and account-local choices.
- `Instance Settings` for host-owned configuration that affects everyone using that deployment.

If a setting can affect other users, it belongs to the operator or instance authority layer, not ordinary user preferences.

## Proof Surface For Future Implementation

Any future implementation that operationalizes this ADR must include proof for:

- role-safe labeling in Settings or onboarding
- tests proving user preferences do not mutate operator-owned configuration without authority
- docs that explain Self Operator and Host Operator postures
- no release-claim widening in `00-current-state.md` unless separately proven

## Related Documents

- `docs/architecture/00-current-state.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/persona-studio-spec.md`
- `docs/architecture/adr/040-network-profile-topology-resolution-contract.md`

## Documentation Follow-Through

If accepted, this ADR should be linked from:

- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md` when operator topology work begins
- any future operator onboarding or network profile documentation
