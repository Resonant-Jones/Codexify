# Extension Boundaries

Codexify’s extension story is bounded by design.
The system supports governed extension seams, not unrestricted self-modification.

## What Exists

The architecture docs describe a self-extending plugin system with these lifecycle stages:

- proposal
- forge
- sandbox
- review
- registration

They also describe the supporting seams:

- install gate
- capability registry
- runtime binding

The runtime also includes a bounded tool-augmented completion slice that can execute one governed command-bus turn and then stop.
That is a narrow seam, not a general autonomous loop.

## What That Means

Those seams exist to keep extension work reviewable, scope-bound, and lineage-preserving.
They do not imply that autonomous recursive agent execution is part of the current supported promise.

## Implemented vs Not Yet Shipped

Keep these separate:

- implemented backend seams for bounded extension governance
- not-yet-shipped sandboxed autonomous runtime claims

The first is a control surface.
The second is not a current release promise.

## Governance Rule

Any extension must remain explicit about:

- what it can touch
- what it cannot touch
- how it is registered
- how it is bound at runtime
- how it is rolled back

If those answers are not explicit, the extension is not truly bounded.
