# Operator Truth

Operator truth is the set of surfaces a person should read when deciding whether the current runtime is healthy, supported, or drifting.

## Supported Surfaces

- supported profile state
- health endpoints
- provider catalog
- task events
- logs
- metrics
- release-truth docs

Those surfaces answer different questions and should be read together.

## What They Prove

- supported profile tells you what posture is intended for the current runtime
- health tells you whether the selected runtime path is reachable
- catalog tells you what providers or models are discoverable
- task events tell you what the queued work is doing
- logs and metrics tell you what the runtime actually experienced
- release-truth docs tell you how to interpret the rest

## Known Risks

The current docs explicitly call out several risks that still matter to operators:

- Redis and worker coupling
- config drift between canonical and legacy paths
- legacy tools overlap
- process-local sync subscriptions
- federation blast radius

## Release Interpretation

Do not overstate release readiness.
A green surface can be useful, but it is not enough by itself.
The supported posture must be inferred from the current truth layer and the operator proof surfaces together.
