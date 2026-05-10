# Codexify Service Offers (v1)

Date: 2026-05-10  
Status: Baseline offer map aligned to open-core strategy

## Purpose
Translate Codexify's technical value into paid service offers tied to real user friction.

## Core Value Principle
Users can access software. They pay when they want:
- faster time-to-value,
- lower failure risk,
- operational accountability.

## Offer 1: Launch Install and Hardening
### Best For
- solo builders and small teams that want Codexify running correctly on day one.

### Scope
- Environment assessment (machine/network/provider posture).
- Install and bootstrap on supported path.
- Identity/permission boundary setup.
- Baseline retrieval posture verification.
- Handoff with runbook and recovery steps.

### Success Criteria
- healthy runtime with documented config,
- known-good chat and retrieval baseline,
- owner can reproduce startup and basic diagnostics.

## Offer 2: Reliability and Upgrade Care
### Best For
- teams already running Codexify who need fewer outages and safer upgrades.

### Scope
- Queue/worker health tuning.
- Runtime drift detection (supported profile versus live posture).
- Migration planning and rollback plans.
- Monthly runtime review and proof refresh.

### Success Criteria
- reduced incident frequency,
- successful upgrade windows,
- current-tip proof artifacts for critical paths.

## Offer 3: Security and Governance Hardening
### Best For
- users handling sensitive data or regulated workflows.

### Scope
- Threat model and trust-boundary workshop.
- Capability-based access and tool-policy review.
- Egress policy and provider exposure hardening.
- Audit trail and incident response procedure.

### Success Criteria
- explicit boundary documentation,
- fail-closed defaults for sensitive surfaces,
- verified policy enforcement points.

## Offer 4: Domain Integration Sprint
### Best For
- teams needing Codexify integrated into existing workflows or systems.

### Scope
- Data-model mapping and ingestion alignment.
- Connector/retrieval posture adaptation.
- UI workflow customization and operator training.
- Validation suite focused on domain-critical paths.

### Success Criteria
- domain workflow works end to end,
- local operator can run and validate without custom heroics.

## Suggested Packaging
- Offer 1: fixed-fee kickoff package.
- Offer 2: monthly retainer.
- Offer 3: fixed-fee assessment + optional follow-on retainer.
- Offer 4: scoped sprint package.

## Pricing Posture (Non-Numeric by Default)
Set price by risk ownership and time-to-value, not feature count:
- Higher risk transfer and uptime accountability -> higher price tier.
- Pure configuration guidance without accountability -> lower price tier.

## Anti-Pattern to Avoid
Do not sell "private access to source" as the premium. Sell deployment certainty, operational maturity, and response accountability.

## Proof-Based Sales Assets to Build Next
- One-page install hardening checklist.
- One-page supported-path live proof sample.
- One-page incident response sample timeline.
- One-page boundary/governance sample deliverable.
