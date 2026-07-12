---
name: module-ownership
description: Assign module ownership, define cross-module boundaries, and review ownership drift in modular codebases. Use when adding a module, moving behavior out of a root shell or app entrypoint, changing shared state or contracts, or reviewing a PR for ambiguous responsibility.
---

# Module Ownership

Use this skill to decide where behavior belongs in a modular codebase and how to keep cross-module boundaries honest.

## Use When

- Adding a new feature or module and you need a clear owner.
- Moving behavior out of an app shell, root component, or entrypoint.
- Changing shared state, shared contracts, or cross-module imports.
- Touching privileged boundaries such as host services, IPC, filesystem, network, auth, or process control.
- Reviewing a PR for ownership drift, mixed concerns, or a too-wide blast radius.

## Working Rules

- Give every behavior one primary owner.
- Keep composition layers thin: route, mount, wire, and pass callbacks.
- Let feature modules own their UI, local controllers, selectors, and domain mutation orchestration.
- Put shared contracts, data shapes, and pure helpers in a shared or core layer.
- Keep privileged operations behind a named service, client, or host boundary.
- Prefer the smallest truthful change that preserves the current architecture.
- If docs and code disagree, trust the live code path and note the drift.

## Process

1. Identify the user-visible behavior.
2. Find the source of truth for the state involved.
3. Assign the primary owner module.
4. Separate reads from writes.
5. Check whether the change crosses a trust or privilege boundary.
6. Move shared contracts to a shared layer if more than one module needs them.
7. Update the repo's module map or ownership doc when ownership changes.

## Output

When you answer with an ownership decision, keep it concise and explicit:

- Owner
- Why it owns the behavior
- What stays out of scope
- Files or modules to touch
- Boundary notes
- Follow-up doc or ADR, if one is warranted

## Reference

For a reusable ownership matrix and checklist, see [references/ownership-matrix-template.md](references/ownership-matrix-template.md).
