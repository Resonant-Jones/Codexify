# ADR-046: Axis Node Portable Reasoning Interface Contract

## Context

Codexify has authoritative current-state, architecture, identity, operational, collaborator, and proof materials, but lacked one repo-native interface that makes their hierarchy and task-generation doctrine portable. A persona prompt or one chat session cannot safely become implicit project authority.

## Decision

Adopt `docs/axis-node/` as documentation-backed shared reasoning infrastructure. It defines the **Axis role**, **Axis Node** package, an **Axis instance**, and a possible **Axis harness** as distinct terms. Current implementation is docs/context infrastructure only.

`00-current-state.md` governs short-horizon release truth; accepted ADRs and current contracts govern their scope; runtime proof outranks docs-only aspiration. Resonant Jones and Zac retain authorship and approval authority. Axis instances may recommend and generate bounded tasks but may not approve or execute their own architecture recommendations.

## Source authority and human authority boundary

The source hierarchy is: current operational truth, accepted ADRs, current architecture contracts, bounded runtime proof, design canon, product specifications, and generated steering artifacts. `00-current-state.md` remains the short-horizon override. Resonant Jones and Zac retain final approval authority; an Axis instance cannot convert a report, proposal, or its own recommendation into approval.

## Invocation Contract

The canonical invocation contract is [`docs/axis-node/invocation-protocol.md`](../../axis-node/invocation-protocol.md). Its mode sequence is `ORIENT -> EXPLORE or REPORT -> DECIDE -> human selection -> TASK -> human approval -> EXECUTE -> PROOF`; not every interaction requires every mode. Modes constrain behavior but do not grant harness capabilities, and the Orientation Receipt records verified repository context, scope, unavailable capabilities, and human gates.

## Identity sovereignty, portability, and consequences

Axis Node is a consent-bound, version-controlled shared frame, not an identity authority, hidden memory, consciousness claim, or provider-owned persona. It uses canonical links and a machine-readable manifest for portability across suitable models or future harnesses. This improves inspectability and onboarding, while requiring maintenance when sources move and preserving uncertainty when a source is unavailable. Identity and personal-context changes remain subject to the identity-precedence and IDDB policies.

Zac's collaborator directory and Axis Node are complementary: the former is person-oriented onboarding and contribution context; the latter is shared reasoning infrastructure and source-governance context.

## Rejected alternatives

- Copying all architecture documents into a parallel KB.
- Storing Axis only as a large persona prompt.
- Treating one chat session as Axis's sole canonical identity.
- Mounting Axis into runtime before governance is defined.
- Allowing Axis to approve or execute its own architecture recommendations.
- Merging Zac's collaborator lane and Axis Node into one undifferentiated directory.

## Future runtime integration gate and non-goals

Any runtime ingestion, retrieval, model binding, profile, command, API, worker, queue, UI, memory write, or autonomous task-selection work requires a separate architecture-impact task with explicit Guardian/Pi ownership, authorization, proof, and release-boundary review. This ADR makes no runtime implementation or supported-beta claim.
