# Codexify Presentation Template

A reusable markdown outline for building slide decks about Codexify subsystems, architecture, or operator concerns. Fill in the sections below, then export to your presentation tool of choice.

---

## Presentation title

<!-- e.g., "Codexify Core Chat Loop — Runtime Reality" -->

## Audience

<!-- e.g., implementation developers, architecture reviewers, Lead Engineer / PM -->

## Goal

<!-- One sentence: what should the audience understand or be able to do after this presentation? -->

## Source docs used

<!-- List relative links to governing source docs. Every claim in the slides must trace back to one of these. -->

- 
- 
- 

## Current truth disclaimer

> This presentation reflects the state of Codexify as of [DATE]. It is derivative teaching material. For authoritative runtime truth, see `docs/architecture/00-current-state.md`. Claims marked as interpretation are not part of the release promise.

---

## Slide outline

### 1. Why this exists

<!-- Problem statement, context, what gap this subsystem fills -->

### 2. What is true now

<!-- Supported-path facts, proven behavior, live evidence -->

### 3. What is not yet true

<!-- Explicitly call out what is NOT part of the current release promise, even if it appears in planning docs -->

### 4. System map

<!-- Diagram or component list: nodes, boundaries, data flow -->

### 5. Critical flow

<!-- Walk through one end-to-end path (e.g., chat message → response, upload → embed → readback) -->

### 6. Operator or developer responsibility

<!-- What a human must do to keep this working: config, monitoring, migration, failure response -->

### 7. Risks and non-goals

<!-- Known failure modes, deliberate exclusions, areas marked as future work -->

### 8. How to build safely on top

<!-- Extension seams, stable contracts, where to hook in without breaking the supported path -->

---

## Speaker notes

<!-- Per-slide talking points, caveats, answers to anticipated questions -->

---

## Claims checklist

Before presenting, verify:

- [ ] Every strong factual claim is backed by a source doc or linked to live evidence
- [ ] Claims marked as interpretation are labeled as such
- [ ] The current-truth disclaimer references the correct date and architecture doc version
- [ ] No speculative roadmap item is presented as current truth
- [ ] The supported path is correctly bounded — no accidental widening of the release promise

---

## Follow-up reading

<!-- Links to source docs, related ADRs, audit reports, or other lessons in the catalog -->
