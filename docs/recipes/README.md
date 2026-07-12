# Codexify Recipe Book

This directory contains reusable operational recipes for Codexify.

A recipe is a portable workflow contract that any capable assistant can follow. It captures intent, prerequisites, commands, safety boundaries, verification, rollback, and expected receipts.

Recipes are not tools by themselves. A proven recipe may later be collapsed into a callable Guardian tool after it succeeds repeatedly without widening authority.

## Structure

```text
docs/recipes/
├── README.md
└── networking/
    └── tailscale-tester-isolation.md
```

## Recipe lifecycle

1. Draft the workflow from a real successful or observed operating path.
2. Mark assumptions, approvals, mutations, and failure boundaries explicitly.
3. Execute it in a bounded environment.
4. Save a receipt with the evidence required to support the result.
5. Revise the recipe from real failures and recovery behavior.
6. Collapse stable, repeated steps into a Guardian tool only after the recipe is proven.

## Recipe contract

Each recipe should include:

- stable recipe ID and status
- trigger conditions and non-goals
- required inputs and permissions
- current architecture anchors
- safety invariants
- preflight checks
- ordered implementation steps
- verification and negative tests
- success receipt shape
- rollback procedure
- explicit failure conditions
- tool-collapse candidate, if appropriate

## Authority rule

Creating or executing a recipe does not create new authority. A recipe may describe actions that require operator approval, but an assistant must not infer permission to apply policy, disclose secrets, invite users, delete persistent state, or widen network access.

## Current recipes

| Recipe | Domain | Status | Related work |
|---|---|---|---|
| [Tailscale tester isolation](./networking/tailscale-tester-isolation.md) | Networking | Draft | Issue #536 |

# Media

- [Codexify demo video production](media/codexify-demo-video-production.md)
