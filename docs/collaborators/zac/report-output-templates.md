# Zac Report Output Templates

**For:** Zac's agent — standardized report shapes for report-only lenses  
**Last updated:** 2026-06-26

## General Report Template

Use this template when no specific lens template fits better.

- **Report title** — descriptive, names the area inspected.
- **Lens used** — which lens from `report-only-agent-lenses.md`.
- **Area inspected** — which directory, subsystem, module, or surface.
- **Files/docs read** — specific paths inspected.
- **What I found** — key observations grounded in evidence.
- **What seems important** — why this matters to Codexify.
- **What is confusing or unresolved** — things that remain unclear after inspection.
- **Risk notes** — sensitivity of the area, any boundaries touched.
- **What this report does not prove** — explicit limits of the inspection.
- **Questions for Resonant** — things only Resonant can clarify.
- **Suggested next report** — what would be useful to map or explore next.

## Directory Map Report Template

For the Cartographer lens.

- **Directory inspected** — path and purpose.
- **Main files** — list of key files with one-line role summaries.
- **File responsibilities** — for each main file, what it owns and why.
- **Important flows** — how data or control moves through the area. Include entrypoints, exits, and key dependencies.
- **Related tests** — test files that cover this area (paths).
- **Related docs** — architecture docs that discuss this area (paths).
- **Unknowns** — structural questions that could not be answered from code alone.
- **What not to infer** — things the directory structure might suggest but are not true (e.g., "this directory exists but is not mounted in the supported profile").

## UI Observation Report Template

For the UI Naturalist lens.

- **Surface inspected** — which UI area and its entrypoint file.
- **Components/files observed** — key components and their paths.
- **User-facing behavior** — what a user would see and do on this surface.
- **Visual/interaction notes** — layout, flow, affordances, accessibility observations.
- **Confusing labels or empty states** — copy that might be unclear to users.
- **Low-risk polish candidates** — small improvements that do not alter runtime meaning (copy fixes, spacing, empty-state hints).
- **Sensitive boundaries not touched** — confirm no runtime semantics, auth, routing, or provider behavior was altered.

## Runtime Boundary Report Template

For the Runtime Boundary Scout lens.

- **Boundary inspected** — which architecture-sensitive boundary (e.g., auth, provider routing, Continuity).
- **Governing docs** — contracts, ADRs, and architecture files that define the boundary (paths).
- **Runtime files** — implementation files that touch this boundary (paths).
- **Current truth** — what is implemented and proven now.
- **Not yet true** — deferred, planned, or unsupported behavior in this boundary area.
- **Invariants** — rules that must not be broken if this boundary changes.
- **Risk level** — estimated impact of changing this boundary (Low/Medium/High).
- **Required proposal lane if changed** — Architecture-Impact, Standard, or Docs-only.
- **Questions for Resonant** — boundary intent questions only Resonant can answer.

## Test Coverage Report Template

For the Test Cartographer lens.

- **Area tested** — which subsystem, module, or capability.
- **Test files** — paths and brief description of what each covers.
- **What tests prove** — specific behaviors verified. Cite test names or assertions where useful.
- **What tests do not prove** — behaviors not covered or only partially covered.
- **Missing confidence** — areas with no test coverage or insufficient coverage.
- **Proof scripts** — any live-proof harnesses that validate this area (paths).
- **Suggested next validation report** — what adjacent test surface would be useful to map.
- **Questions for Resonant** — testing philosophy, coverage priorities, or known gaps.

## Continuity Phase Report Template

For the Continuity Museum Guide lens.

- **Continuity area inspected** — which part of the Continuity operator phase.
- **Current completed behavior** — what exists and is proven, in plain language.
- **Gates** — profile quarantine, feature flag, API key auth, and how the surface is protected.
- **Proof artifacts** — what was proven and where the evidence lives (file paths).
- **Regression guardrails** — what protects the surface from accidental drift.
- **Release boundary** — what is and is not supported beta behavior.
- **What not to touch** — expansion, activation, or integration without a new contract.
- **Open questions** — what is still unclear or deliberately deferred.
