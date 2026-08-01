---
tags:
  - architecture
  - adr
  - vaultnode
  - soft-serve
  - git
  - publication
aliases:
  - ADR-054
  - VaultNode Soft Serve Local Forge and GitHub Publication Remote
---

# ADR-054: VaultNode Soft Serve Local Forge and GitHub Publication Remote

## Status

Accepted

## Date

2026-07-29

## Context

Codexify uses VaultNode as the canonical machine and audit authority, while
GitHub `main` is the accepted external code authority under ADR-041. GitHub is
useful as a publication and off-node redundancy surface, but it is not the
only place where active development history needs to exist. The operator needs
an optional local Git forge on VaultNode that can hold selected development
history before explicit publication.

Soft Serve is an operator/developer substrate. It is not a Codexify service,
dependency, provider, queue, worker, persistence layer, or supported beta
runtime path. Its Compose file must therefore remain separate from the
default Codexify Compose graph and its failure must not affect Codexify.

## Decision

Codexify provides an opt-in Soft Serve deployment in
`docker-compose.soft-serve.yml`. It runs one independently operated
`soft-serve` service using a pinned released image, a host-configurable data
directory, and SSH public-key administration. The deployment defaults to
loopback host publication, disables anonymous and keyless access after service
initialization, does not publish Git daemon port 9418, and does not create or
change Git remotes.

The Soft Serve repository is the local forge authority for development history
only after an operator explicitly verifies it and chooses the Phase B remote
transition in the runbook. GitHub remains the publication remote and the
accepted code authority described by ADR-041. A local `origin` name is a Git
convention, not evidence that GitHub publication or release acceptance has
occurred.

## Remote naming contract

The safe introduction phase preserves the existing GitHub `origin` and adds a
temporary named remote such as `soft-serve`. The operator pushes and verifies
branches, tags, clone, and fetch behavior before changing names.

Only after that verification and an explicit operator decision may the local
operator run:

```bash
git remote rename origin github
git remote rename soft-serve origin
```

The intended resulting convention is `origin = Soft Serve on VaultNode` and
`github = GitHub publication and off-node redundancy`. This task does not add
`pushInsteadOf`, multi-push URLs, hooks, background synchronization, automatic
imports, or automatic remote mutation.

## Authority model

| Surface | Authority | Meaning |
|---|---|---|
| Accepted Codexify source | GitHub `main` | Canonical accepted code, docs, schemas, and contracts under ADR-041. |
| Active local development forge | Verified Soft Serve repository on VaultNode | Operator-controlled development history and selected unpublished work. |
| Runtime and audit machine | VaultNode | Canonical execution origin; local forge presence does not make every local observation canonical evidence. |
| Publication decision | Resonant Jones / authorized operator | Explicit choice of what is pushed to GitHub and when. |
| Other clones and machines | Provisional | May develop and validate, but do not silently replace either authority. |

Soft Serve users, collaborators, repository visibility, service configuration,
and server keys are service state. They are not represented by Git objects and
must not be inferred from a successful GitHub push.

## Exposure posture

The host bind address defaults to `127.0.0.1`. Operators who need access from
another trusted device should bind the published ports to the VaultNode
Tailscale IP and keep firewall and tailnet policy explicit. The deployment
does not default to `0.0.0.0` or public-internet exposure. SSH is the initial
workflow; HTTP and stats ports are configurable operator surfaces. Git daemon
port 9418 is intentionally not published.

The trust boundary is the operator-controlled VaultNode host and its Docker
daemon. Tailnet clients are a separate network boundary and must authenticate
with registered SSH keys. The threat model is honest-but-buggy local tooling
plus potentially compromised or unauthorized network clients; prompt text is
not an access-control mechanism.

## Backup semantics

Three different forms of redundancy remain distinct:

1. **Git repository redundancy:** pushing refs and objects to GitHub preserves
   the published Git history that GitHub received.
2. **Soft Serve service-state backup:** the configured
   `CODEXIFY_SOFT_SERVE_DATA_DIR` is the required backup root. It contains the
   repositories plus service database, users and collaborator configuration,
   SSH host/client keys, hooks, generated config, and related state.
3. **VaultNode host backup:** host-level backup must preserve the data root,
   operator Compose/env configuration, permissions, and the recovery context
   needed to restore the service on another host.

GitHub does not preserve unpublished Soft Serve repositories, Soft Serve users
or collaborator configuration, service database state, SSH host keys, server
hooks, or operator configuration. GitHub mirroring is therefore not a complete
backup of the Soft Serve service.

## Failure isolation

Soft Serve uses a separate Compose file, service, project invocation, storage
root, and network topology. The default Codexify Compose graph does not include
or depend on it. Stopping, removing, or corrupting Soft Serve must not stop or
change Codexify startup, health, workers, queues, providers, or runtime
configuration. Soft Serve outage means local-forge unavailability; it does not
change the supported Codexify runtime or authorize a silent GitHub failover.

## Consequences

Positive consequences include local control of active development history,
explicit publication boundaries, persistent forge state outside the container,
and a small operator surface that can be disabled without touching Codexify.

Costs include a second Git authority to reason about, a required service-state
backup procedure, manual publication and remote-name decisions, and the need
to independently verify the live Soft Serve service. Repository redundancy
and service recovery remain separate operational duties.

## Non-goals

This decision does not add GitHub Actions synchronization, a Soft Serve Action,
automatic repository import or mirroring, repository migration, automatic
remote rewriting, multi-push behavior, Git hooks, a Codexify application
dependency, or a supported-release/runtime claim.

## Rollback

The operator can stop Soft Serve with `make soft-serve-down` without deleting
the configured data directory. If the Phase B remote naming transition was
completed, rollback is an explicit manual operation after confirming both
remote URLs:

```bash
git remote rename origin soft-serve
git remote rename github origin
```

If the local forge data is unavailable, GitHub remains the publication and
accepted-code surface. Recovery of unpublished work requires the configured
Soft Serve data backup or another verified local copy; GitHub cannot recreate
that unpublished service state.

## Relationship to ADR-041

ADR-041 remains governing for VaultNode as canonical runtime/audit machine and
GitHub `main` as canonical accepted code authority. This ADR adds the missing
forge/publication distinction: Soft Serve may be the operator-selected local
development forge, while GitHub remains the explicit publication and accepted
source surface. Nothing here changes evidence promotion, trusted `latest`, or
human decision authority under ADR-041.

## Supported runtime boundary

Soft Serve remains optional operator substrate. This does not widen the
supported Codexify runtime.
The supported product path remains the existing local Docker Compose stack
described by `docs/architecture/00-current-state.md`. Soft Serve is optional
operator substrate and has no supported Codexify beta dependency.
