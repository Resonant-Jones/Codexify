# Workspace Surface

Workspace is a design canon, not a runtime truth claim.
It describes how the UI should present a persistent working surface across supported views.

## Three Roles

Workspace is organized as:

- Shelf
- Scratchpad
- Inspector

## What Each Role Means

- Shelf holds pinned or recent materials the user is orbiting around.
- Scratchpad is a fast, low-friction note surface.
- Inspector previews the currently selected item without taking over the whole surface.

## Supported View Framing

The supported surface framing in the current docs is:

- Dashboard
- Guardian
- Documents

Workspace appears in those views as a shared shell model with view-specific defaults.

## Canonical Distinction

Workspace design language is not the same thing as backend runtime truth.
It helps shape the UI, but it does not redefine deployment topology, worker behavior, health surfaces, or release support.

That distinction matters because the workspace spec is deliberately a UI/design canon document.
If it conflicts with current runtime truth, current runtime truth wins.
