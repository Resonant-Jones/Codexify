# Collaborator Onboarding

This directory is the first stop for trusted collaborators working inside Codexify.

You should not have to infer what matters from repo structure alone. This front door exists to make the working model explicit: how to orient, how to change things safely, what shared truth to protect, and which existing docs and tools matter most.

Principle: `Explore freely, but keep shared truth protected.`

`docs/architecture/00-current-state.md` remains the release-truth authority.

## Collaborator Lanes

- [Zac Collaborator RAG Source](./zac/README.md) - inspiration-led exploration and proposal-before-change workflow.
- [Paul Collaborator Study Lane](./paul/README.md) - architecture-study lane with a clear first path, report-first prompts, and a BIOME/CORAL memory lens.

## Start Here

Read in this order:

1. [collaboration-protocol.md](./collaboration-protocol.md)
2. [dev-kit-inventory.md](./dev-kit-inventory.md)
3. [worktree-and-branching-guide.md](./worktree-and-branching-guide.md)
4. [task-spec-protocol.md](./task-spec-protocol.md)
5. [../architecture/00-current-state.md](../architecture/00-current-state.md)
6. [../architecture/README.md](../architecture/README.md)
7. [../architecture/system-overview.md](../architecture/system-overview.md)
8. [../architecture/flows.md](../architecture/flows.md)
9. [../architecture/data-and-storage.md](../architecture/data-and-storage.md)
10. [../architecture/modules-and-ownership.md](../architecture/modules-and-ownership.md)
11. [../architecture/config-and-ops.md](../architecture/config-and-ops.md)

## What This Folder Is For

- Trusted collaborator onboarding
- Clear working norms
- A practical inventory of existing repo resources
- A shared map for worktrees, branches, and task packets
- Per-collaborator study lanes with their own first path and prompts

## What This Folder Is Not For

- Public contributor onboarding
- Runtime implementation
- New automation
- Release claims beyond current-state docs

If you are about to change code or runtime behavior, use the onboarding docs here first, then check the architecture docs that govern the surface you are touching.
