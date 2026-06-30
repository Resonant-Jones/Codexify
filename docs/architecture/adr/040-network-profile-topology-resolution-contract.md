---
tags:
* architecture
* adr
* network-profiles
* topology
* operator-surface
* provider-capabilities
  aliases:
* ADR-040
* Network Profile Topology Resolution Contract
---

# ADR-040: Network Profile Topology Resolution Contract

## Status

Proposed

## Date

2026-06-30

## Context

Codexify currently has a supported local-first beta path, but operator reality is broader than a single hostname.

The same instance may be reached differently depending on where the operator is:

- same-device development
- home LAN
- Tailscale or another private overlay network
- hosted-by-someone-else access
- future cloud-hosted access
- custom infrastructure

A small failure surfaced the larger shape: a Vite development server rejected `vaultnode` until the hostname was explicitly allowed. Meanwhile, the Tailscale IP resolved and the actual runtime path was available. The immediate bug was Vite host allowlisting. The underlying product problem was that Codexify currently lets operator topology leak into ad hoc hostnames, environment variables, and mental notes.

Hardcoded connection strings do not scale into a product experience. Codexify needs a first-class way to model where an instance lives and how the active client should reach it.

## Decision

Codexify will model infrastructure access through explicit `Network Profiles` instead of scattered hostnames or one-off connection strings.

A Network Profile is an operator-visible topology record that describes how a client should reach a Codexify instance and its related local-provider services under a named access posture.

The first canonical topology profile types are:

| Profile type | Meaning |
|---|---|
| `local_device` | Client and runtime are on the same machine or loopback boundary. |
| `home_lan` | Client reaches an operator-owned node on the same local network. |
| `tailscale_vpn` | Client reaches an operator-owned node through Tailscale or another private overlay network. |
| `hosted_instance` | User reaches an instance operated by someone else. |
| `cloud_hosted` | Instance is hosted on cloud infrastructure under an operator or service account. |
| `custom` | Explicit operator-defined routing profile for cases that do not fit the built-in set. |

## Profile Shape

A future profile record should be able to describe at least:

- profile id
- profile name
- profile type
- base address or host
- optional frontend address
- backend/API address
- local provider address when applicable
- Whoosh'd address when applicable
- transport/security notes such as `http`, `https`, local-only, LAN, or private overlay
- whether the profile is operator-owned, hosted, or user-provided
- whether the profile is active

The exact storage schema is deferred. This ADR defines the contract boundary, not an implementation plan.

## Provider-Aware, Not Provider-Exclusive

Network Profiles are provider-aware but not provider-exclusive.

Whoosh'd may receive the richest first-class experience because it can expose health, inventory, queue, memory, lifecycle, and runtime signals that Codexify understands. That is capability depth, not artificial feature gating.

Future profile resolution should prefer capability checks over provider-name special cases.

Use this posture:

```text
Whoosh'd is first-class because it can prove more.
Other providers are supported according to what they can expose.
```

Avoid this posture:

```text
Only Whoosh'd may use network profiles.
Other providers are blocked by product policy even when they can expose equivalent capability.
```

## Explicit Switching Before Automation

The first implementation must prefer explicit operator control.

Codexify may later detect that the user appears to be away from the home network, but it must not silently switch active profiles in the first implementation.

Allowed first behavior:

```text
Looks like you may be away from your home network. Tailscale Mode is available in Settings.
```

Disallowed first behavior:

```text
Codexify silently rewrites active runtime/provider URLs without explicit operator action.
```

Automatic switching may be revisited only after enough runtime evidence exists to avoid unsafe or confusing profile changes.

## Non-Goals

This ADR does not implement:

- Settings UI
- profile persistence
- profile synchronization across devices
- automatic topology detection
- Vite configuration changes
- provider routing changes
- backend endpoint rewrites
- mobile remote access
- hosted Codexify service behavior
- billing or paid feature policy

## Current-Truth Anchors

What is true now:

- Local Docker Compose remains the supported install path.
- The supported posture remains local-only provider operation.
- Whoosh'd remains the supported Apple Silicon local runtime preset.
- Runtime truth is still read through current health, chat, and provider surfaces.

What is not yet true:

- Network Profiles are not yet implemented.
- There is no active topology resolver.
- Tailscale/VPN profile selection is not yet a shipped setting.
- Hosted-instance access is not a shipped release promise.
- Cloud-provider beta support is not implied by this ADR.

What future tasks may assume:

- It is valid to introduce a central topology resolver behind Settings.
- It is valid to add a `tailscale_vpn` profile type.
- It is valid to design UI copy around explicit operator switching before automatic switching.
- It is valid to attach provider capability displays to profile health surfaces when the provider can prove them.

## Invariants

- Network profile selection must not bypass authentication, exposure-mode, or egress policy.
- Secrets must not be exposed into browser-visible Vite env unless already allowed by current dev-only rules.
- Profile activation must be visible and reversible.
- Automatic detection must notify before switching until a separate ADR/task approves stronger behavior.
- Provider capability display must be evidence-backed.
- `docs/architecture/00-current-state.md` remains the release-truth boundary.
- This ADR must not be read as proof of remote production support.

## Resolution Model

Future runtime/frontend code should resolve service URLs through one active profile instead of duplicating host logic at call sites.

Conceptual resolution shape:

```ts
type NetworkProfileType =
  | "local_device"
  | "home_lan"
  | "tailscale_vpn"
  | "hosted_instance"
  | "cloud_hosted"
  | "custom";

interface NetworkProfile {
  id: string;
  name: string;
  type: NetworkProfileType;
  baseAddress: string;
  frontendUrl?: string;
  backendApiUrl?: string;
  localProviderUrl?: string;
  whooshdUrl?: string;
  active: boolean;
}
```

This is an illustrative contract sketch, not a committed schema.

## User Experience Doctrine

The operator should not need to remember whether today requires:

- `localhost`
- `vaultnode.local`
- `vaultnode`
- a LAN IP
- a Tailscale IP
- a hosted URL

Codexify should present a small number of named profiles and make the active routing posture visible.

Example labels:

- `Home LAN`
- `Tailscale`
- `Local Device`
- `Hosted Instance`
- `Custom`

## Proof Surface For Future Implementation

A future implementation task must include proof for:

- Settings can create, edit, save, and activate a Network Profile.
- Resolver tests prove frontend/backend/provider URLs derive from the active profile.
- Local development behavior remains unchanged when no profile is active or when `local_device` is selected.
- Tailscale/VPN profile activation uses the configured host/IP without silent switching.
- Hostname validation and URL normalization reject unsafe malformed input.
- Provider capability display is derived from live evidence or a documented capability registry.
- No release claims are widened without updating and proving `00-current-state.md`.

## Documentation Follow-Through

If accepted, this ADR should be linked from:

- `docs/architecture/adr/adr-index.md`
- `docs/architecture/README.md` when network profile implementation begins
- future operator setup docs
- future Settings or Operator Surface docs

## Related Documents

- `docs/architecture/00-current-state.md`
- `docs/architecture/config-and-ops.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/modules-and-ownership.md`
- `docs/architecture/runtime-protocol-token-contract.md`
- `docs/architecture/canonical-token-philosophy.md`
- `docs/architecture/tech-debt-and-risks.md`
- `docs/architecture/adr/039-operator-user-access-boundary.md`
