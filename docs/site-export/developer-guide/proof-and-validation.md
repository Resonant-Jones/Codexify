# Proof and Validation

Proof in Codexify is narrower than “a thing exists in the repo.”

## What Does Not Count As Proof

- docs validation does not prove runtime behavior
- route presence does not prove support
- catalog presence does not prove release readiness
- a successful startup does not prove end-to-end completion

## Stronger Proof Surfaces

Better proof comes from surfaces that actually exercise the runtime:

- current-state truth docs
- health and operator surfaces
- supported-path live evidence
- backend seam tests where they exist
- persisted runtime artifacts

## Validation Rule

Validation commands are useful, but they only prove the surface they test.
They do not automatically widen the supported promise.

## Interpretation Rule

When validation and release truth disagree, release truth wins.
When current-state docs and older architecture docs disagree, current-state docs win.

## Practical Boundary

Use validation to check that the bundle is structurally sound.
Use runtime evidence to decide whether the runtime is actually supported.
