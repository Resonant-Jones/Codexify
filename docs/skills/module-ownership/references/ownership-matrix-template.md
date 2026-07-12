# Portable Ownership Matrix

Use this template when a codebase needs an explicit ownership map for modules, shared state, or privileged boundaries.

## Questions To Answer

- What is the root composition layer?
- Which module owns the user-visible behavior?
- Which module owns the source of truth for the state?
- Which modules only read the state?
- Which modules may mutate it?
- What boundary is privileged or trust-sensitive?
- Does this belong in a shared contract instead of a feature module?

## Matrix Template

| Path / module | Owns | Reads | Writes / Mutates | Boundary notes |
| --- | --- | --- | --- | --- |
| Root shell / entrypoint | Composition only | Route and bootstrap state | Wiring and mounting | Keep thin; do not accumulate domain logic |
| Feature module | Domain UI and local orchestration | Shared state and selectors | Domain-specific mutation | Do not reach into other features' private helpers |
| Shared core / contracts | Pure helpers and common types | Any feature | Pure transformations only | No side effects or privileged access |
| Service / host layer | Privileged operations | Intent from UI or features | Filesystem, network, auth, IPC, process actions | Capability-gated and testable at the boundary |

## Review Checklist

- One owner per behavior.
- No feature module imports another feature module's private controller as a shortcut.
- Shared contracts live in the shared layer, not in a random feature.
- Privileged actions stay behind a service boundary.
- The ownership doc or architecture map matches the code path.
- Validation covers the changed boundary, not just the happy path.

## Minimal Review Output

- `owner`: the module that should carry the behavior
- `boundary`: the seam that must stay intact
- `out_of_scope`: what should not move with this change
- `follow_up`: any doc or ADR update that keeps the map current
