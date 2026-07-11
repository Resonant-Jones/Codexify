# Guardian Evidence Packet Authoring Guide

> Classification: static authoring guidance
> Status: docs-only; no packet generator or runtime reducer

## 1. Purpose

This guide defines a repeatable human or agent ritual for authoring `GuardianEvidencePacket` fixtures from bounded source evidence. It complements the [Guardian Evidence Packet and Reducer Profile Contract](./guardian-evidence-packet-reducer-contract.md), the [static validator contract](./guardian-evidence-packet-static-validator-contract.md), and the [authoring template](./templates/guardian-evidence-packet-template.v1.json).

The goal is consistent evidence hygiene: preserve source references, separate claims from authority, and make uncertainty and forbidden interpretations visible.

## 2. Status

This is static authoring guidance only. It does not implement packet generation, runtime reducer behavior, runtime validation, persistence, ingestion, UI, execution, or release support.

## 3. Scope

The guide applies to static `GuardianEvidencePacket` examples and future fixture authoring. It covers evidence references, claim ledgers, authority locks, invariants, uncertainty, forbidden interpretations, next gates, and bounded self-check policy.

The bridge proof-chain fixture is an example, not a required model for every evidence domain.

The local validator toolchain fixture is the second example packet. It demonstrates packet authoring for local tooling evidence rather than bridge proof evidence. It is still a static fixture, not runtime reducer output, packet generator output, Codexify ingestion, Execution Ledger truth, or WorkOrder mutation.

Manual authoring remains valid before runtime reducer implementation. The [runtime reducer design contract](./guardian-evidence-packet-runtime-reducer-design-contract.md) defines future automated reduction boundaries. Future reducer output must preserve the same authoring invariants: evidence refs, uncertainty, forbidden interpretations, and false authority locks unless separately authorized.

## 4. When to Author a GuardianEvidencePacket

Author a packet when raw evidence needs bounded Guardian-readable reduction. Suitable inputs include proof documents, command-run records, receipts, validation output, hashes, architecture contracts, and other source artifacts whose references can be preserved.

A packet is useful when a reviewer needs to distinguish supported, unsupported, blocked, inferred, and not-evaluated claims without treating a summary as authority.

## 5. When Not to Author a GuardianEvidencePacket

Do not author a packet for ordinary notes, unverified guesses, or broad narrative summaries without evidence references. Do not use a packet to make an unproven capability look shipped, to authorize execution, or to replace a governing contract.

## 6. Authoring Inputs

Start with the source artifacts that establish the evidence domain and its boundaries. Record stable paths or URIs, source systems, timestamps where available, content hashes where available, status, and trust posture. Evidence refs must point to source artifacts; they must not paste entire artifacts into the packet.

Use `docs/architecture/templates/guardian-evidence-packet-template.v1.json` as an authoring aid. Keep the template outside `docs/architecture/fixtures`; it is not evidence and is not a fixture.

## 7. Choosing review_depth

Choose one of `light`, `medium`, `high`, or `xhigh` based on evidence volume, contradiction risk, and review needs. review_depth controls evidence handling and self-check policy, not model personality.

High and xhigh packets must preserve uncertainty and forbidden interpretations. A deeper review does not grant authority or convert evidence into truth.

## 8. Evidence Reference Rules

Each evidence ref must identify the source artifact with a non-empty `ref_id`, `ref_type`, `uri_or_path`, `source_system`, `status`, and `trust_posture`. Keep the ref small and navigable; the source artifact remains the evidence surface.

Treat hashes as continuity evidence only. A hash match proves file continuity, not correctness. Command-bus run/event records, receipts, proof docs, and validation logs are evidence surfaces, not authority by themselves.

## 9. Claim Ledger Rules

Every claim ledger entry must bind its claim to one or more `evidence_refs`. Include confidence, context and temporal limits, counterclaims, missing evidence, and forbidden interpretations.

The statuses `supported`, `unsupported`, `blocked`, `inferred`, and `not_evaluated` are all allowed. Unsupported, blocked, inferred, and not-evaluated claims are often safer than pretending support.

## 10. Authority State Rules

Keep every authority lock false unless a future explicit contract permits otherwise. In particular, a valid packet must not authorize plan execution, Pi Loop invocation, provider execution, source mutation, dispatch, merge, durable mutation, or Codexify ingestion.

Evidence is not authority, and a validation result is not execution authority.

## 11. Invariant Check Rules

Record the invariant, its status, its evidence refs, and notes that explain the boundary. Preserve negative boundaries such as no execution, no source mutation, no provider execution, no ingestion, no UI support, and no durable mutation where they apply.

## 12. Uncertainty Rules

Preserve contradictions, missing proof, blocked paths, temporal limits, and future-contract gaps. High and xhigh packets must not silently omit uncertainty. State what evidence is missing and provide bounded resolution options.

## 13. Forbidden Interpretation Rules

Write explicit statements describing what the packet must not be read as. Include the exact bridge boundary label when the packet is preflight-oriented:

```text
PREFLIGHT ONLY
NO PI LOOP INVOCATION
NO SOURCE MUTATION
NO CODEXIFY INGESTION
```

Forbidden interpretations prevent summaries from silently widening authority or release claims.

## 14. Next Gate Rules

List bounded next gate options with prerequisites and risk. Set one recommended next gate or explicitly record that the evidence is parked. A next gate is a review step, not an execution request.

## 15. Loop Policy Rules

Set bounded self-check limits and keep `recursive_autonomous_loop_allowed` false. Record passes executed and their results. Reducer depth controls evidence handling and self-check policy, not model personality; no packet authoring step creates a recursive autonomous execution loop.

## 16. Template Usage

Copy the template into a working location, replace every placeholder, and retain the full top-level shape. Set `provenance.template` to `false` only when authoring a real packet from actual evidence. Do not place the completed packet in `docs/architecture/fixtures` until it represents real evidence and its boundary language is complete.

The template is intentionally not a fixture and is not a packet generator.

## 17. Validation Ritual

Use this sequence:

1. Identify evidence domain.
2. Collect source artifacts.
3. Assign evidence refs.
4. Extract candidate claims.
5. Bind claims to refs.
6. Mark unsupported, blocked, inferred, or not_evaluated claims honestly.
7. Preserve uncertainty.
8. Preserve forbidden interpretations.
9. Set authority locks.
10. Choose next gate options.
11. Validate with:

    ```bash
    make guardian-evidence-packets-validate
    ```

12. Review warnings without treating them as authority.

The batch validator validates fixtures under `docs/architecture/fixtures`, not the template. Validation checks shape and guardrails only. Passing validation does not prove claim truth. Passing validation does not promote evidence to authority. Passing validation is not Codexify ingestion, Execution Ledger truth, WorkOrder mutation, or runtime support.

## 18. Review Ritual

A reviewer should confirm that every claim has evidence refs, uncertainty and contradictions remain visible, authority locks are false, and forbidden interpretations preserve the boundary. Review warnings as prompts for inspection, not as permission to repair broadly or execute anything.

## 19. Relationship to Runtime Reducer

Future runtime reducer implementation requires a separate explicit contract. This guide does not generate packets, run a reducer, persist packets, or authorize reducer output as truth.

## 20. Relationship to Future UI

Future UI surfacing requires a separate explicit contract. This guide does not add a Guardian panel, API route, UI trigger, or dev-build test affordance.

## 21. Relationship to Execution Ledger and WorkOrder

Future Execution Ledger adoption requires a separate explicit contract. Future WorkOrder mutation requires a separate explicit contract. A packet and its validation result do not create either durable truth or mutation authority.

## 22. Generated Fixture Policy

A static generated GuardianEvidencePacket fixture exists at
`docs/architecture/fixtures/guardian-evidence-packet.generated-local-tooling.v1.json`.
It was produced by the local stdout-only packet generator
(`scripts/guardian/generate_evidence_packet.py`) and checked in as a fixture. The
fixture must preserve the generator output shape, evidence refs with content hashes,
uncertainty with skipped-source representation, forbidden interpretations including
the boundary label, and all authority locks false. It must contain no absolute paths
or secrets. The focused test
`tests/evidence_packets/test_guardian_evidence_packet_generated_fixture.py` asserts
structural equivalence between the static fixture and fresh generator output. This
fixture is a static artifact, not runtime reducer output, not packet generation by
itself, not evidence ingestion, not WorkOrder mutation, not an Execution Ledger
write, and not release support expansion. Authoring a new generated fixture requires
a separate task, generator invocation, and fixture extraction. Do not hand-edit the
generated fixture; regenerate it from the generator and re-extract the packet object.

## 23. Failure Modes

| Failure | Cause | Response |
|---|---|---|
| Claim has no evidence ref | Summary was authored before source mapping | Add or remove the claim; do not imply support. |
| Blocked evidence is presented as pass | Status was collapsed for readability | Preserve `blocked` and explain missing proof. |
| Uncertainty disappears | Reduction favored brevity over fidelity | Restore uncertainty and resolution options. |
| Authority lock is true | Authoring confused evidence with permission | Set it false and identify the separate contract required. |
| Template is batch-validated | Template was placed under fixtures | Move it back to `docs/architecture/templates`. |
| Warning is treated as approval | Validation semantics were widened | Review the warning; validation is not authority. |

## 23. Forbidden Interpretations

Do not interpret this guide or its template as:

- a packet generator
- runtime reducer behavior
- runtime validator behavior
- Codexify ingestion
- Execution Ledger truth
- WorkOrder mutation
- execution, dispatch, merge, or provider authorization
- Pi Loop support or plan execution support
- UI support or a dev-build test button
- CI/default release gating or release support expansion

## 24. Bottom Line

Author packets to preserve evidence and bounded interpretation, not to manufacture certainty. The template and guide make static authoring repeatable; they do not add runtime behavior, authority, ingestion, persistence, UI, execution, CI gating, or release support.
