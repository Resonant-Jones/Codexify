# ADR-037 Campaign Runner Pi Provider Broker

- Status: Proposed
- Date: 2026-05-25

## Title

Pi is the preferred lightweight provider-broker adapter for Campaign Runner when available.

## Context

Campaign Runner needs a lightweight adapter seam that preserves provider plurality without embedding direct Codex/Claude binary assumptions into runner core, coding-worker routing, or runtime images. Existing Pi invocation surfaces already provide a bounded broker seam, but current release truth does not yet prove universal live receipt dispatch. The architecture still benefits from defining Pi as the preferred broker boundary for this module.

## Decision

Pi is the preferred lightweight provider-broker adapter for Campaign Runner when available.

- Pi is preferred, not mandatory
- Pi is a provider-broker adapter, not Campaign Runner core
- Pi is a sidecar-style execution broker boundary
- Pi is distinct from OpenRouter
- Campaign Runner must rely on resolved backend receipts rather than assumptions about Pi internals
- Codex and Claude are downstream possibilities behind Pi, not required direct module dependencies
- direct Codex/Claude process, binary, package, or CLI pinning is intentionally removed from this module posture

## Consequences

- coding-worker and Campaign Runner surfaces keep Pi as the preferred broker lane
- direct Codex/Claude runtime image installs and Compose wiring are removed for this module
- downstream provider plurality stays available only through explicit Pi resolution and receipts
- future adapter plurality remains possible because Pi is preferred, not monopolistic

## Non-goals

- requiring Pi globally for all Codexify execution
- requiring Pi for every Campaign Runner path regardless of context
- treating Pi as a model
- treating Pi as ResonantOS runtime
- making Campaign Runner depend on Pi internals

## Rationale

- Pi has a lighter RAM/process footprint than installing and invoking multiple heavy CLIs directly.
- Pi improves contributor accessibility by reducing local setup burden.
- Pi preserves provider plurality while keeping Campaign Runner core provider-agnostic.
- Pi makes resolved backend transparency explicit through receipts rather than through runner-native branching.
- Pi fits a lightweight sidecar posture that preserves local-first ergonomics.

## Dependency posture

- Campaign Runner should prefer Pi over direct provider CLIs for this module
- Docker/runtime image installs of Codex/Claude CLIs are not part of the preferred Campaign Runner posture
- direct provider binaries are not required dependencies for coding-worker or Campaign Runner execution

## Rejected alternatives

- requiring Pi globally for all Codexify execution
- treating Pi as a model
- treating Pi as ResonantOS runtime
- making Campaign Runner depend on Pi internals
- replacing provider adapter plurality with a single broker monopoly
- direct Codex binary execution in Campaign Runner
- direct Claude binary execution in Campaign Runner
- Docker/runtime image installs of Codex/Claude CLIs for this module

## Validation / proof expectations

- runtime and TUI/CLI surfaces prefer `pi`
- direct Codex/Claude execution paths fail closed
- runtime images no longer install direct Codex/Claude CLIs for this module
- Compose stacks no longer wire coding-worker services to direct Codex/Claude binary env vars
- documentation frames Pi as the preferred broker seam without claiming a global mandatory runtime replacement

## Documentation follow-through

- add ADR-036 and ADR-037 entries to the ADR index
- update Campaign Runner specs to define Pi receipts and broker behavior
- update operator runbooks and doctrine notes so they stop recommending direct Codex/Claude execution for this module
