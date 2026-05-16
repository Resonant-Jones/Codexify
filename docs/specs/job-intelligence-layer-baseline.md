# Job Intelligence Layer Baseline

This document is a baseline orientation artifact for the Job Intelligence Layer concept. It is not an implementation plan and not a release promise. It does not describe shipped runtime behavior in Codexify's current supported beta surface.

## Purpose

Job Intelligence Layer is framed as a reusable applied workflow pattern:

- customer interaction in
- structured operational profile out
- human review before confirmation
- durable operational memory after confirmation

The intent is to turn ambiguous intake into actionable structure while preserving operator control.

## Product Thesis

The core thesis is:

- the system should compress ambiguity before human labor begins
- the output should be a reviewed operational record, not only a chatbot transcript
- the human operator remains final authority for confirmation, correction, and downstream action

## Initial Domain Example

The first seed example is plumbing or service-call intake. A customer interaction can be transformed into a draft operational profile that highlights concrete intake elements such as:

- symptoms
- job-site details
- access notes
- system type
- urgency
- scheduling preference
- policy or pricing questions

Plumbing is the motivating starting example, not the permanent domain boundary.

## Portable Pattern

If validated, the same pattern could later apply to intake-heavy lanes such as:

- HVAC
- electrical
- cleaning
- repair shops
- consulting intake
- other service, order, or case intake businesses

This document does not commit Codexify to supporting all of these domains now.

## Codexify Relationship

This concept starts inside Codexify as a docs-first incubation lane.

Why start here:

- Codexify already has conversation runtime primitives
- Codexify already has durable storage primitives
- Codexify already has artifact and worker primitives
- Codexify already has workflow-planning language and contract surfaces

Using Codexify as the incubation substrate allows concept validation before rebuilding scaffolding elsewhere.

If the lane proves durable, it may later be:

- kept as a Codexify workflow feature
- extracted as a vertical product
- split into a separate repository
- packaged as an applied Codexify deployment profile

This baseline does not claim any hosted, SaaS, on-prem, or hybrid commitment.

## MVP Shape

First plausible MVP shape:

- transcript or message text input
- extraction pass
- generated Job Profile draft
- human review and edit
- confirmed record persistence

Explicitly out of scope for the first MVP:

- full AI voice agent
- autonomous dispatch
- route optimization
- billing automation
- customer-facing production messaging
- compliance-sensitive recording or transcription handling

## Architectural Boundaries

If implementation proceeds later, architecture-impacting surfaces will need explicit atomic tasks, including:

- data contracts
- identity and customer-memory boundaries
- event and provenance model
- workflow extraction behavior
- possible transcription or audio handling
- external communication surfaces
- operator review UI

No changes to these surfaces are made or promised by this baseline document.

## Memory and Record Doctrine

The baseline memory doctrine for this lane is:

- store concrete events and facts, not opinions
- derive actions from evidence
- keep human review and correction available
- avoid durable subjective labels such as "difficult customer"
- prefer structured facts such as payment issue, dispute, access problem, safety flag, or follow-up requirement

## Open Questions

- Which delivery posture fits first validation: on-prem, hosted, or hybrid?
- What transcription consent and retention policy is acceptable per deployment context?
- Where is the minimum local-vs-cloud model boundary for this lane?
- Should Job Profile live in Codexify core or an extracted package?
- Which vertical should be validated first?
- What minimum review UI is required for safe operator confirmation?
- Which schema becomes canonical for Job Profile and revision history?

## Next Step

The next task should create the dedicated directory scaffold under:

- `docs/specs/job-intelligence-layer/`

No implementation work should begin until both this baseline orientation document and the directory scaffold exist.
