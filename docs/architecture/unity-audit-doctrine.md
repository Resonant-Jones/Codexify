# Unity Audit Doctrine

Purpose: define the first canonical coherence audit doctrine for Codexify so the architecture corpus can be evaluated as one system story across runtime truth, contracts, operator reality, governance, extensions, and public-facing narrative without collapsing those surfaces into one score or one claim.

Classification: doctrine-first architecture note aligned with existing contracts and release-truth rules.

## Why This Exists

Codexify's architecture corpus has matured into multiple truth surfaces:

- runtime proof and supported-path evidence
- architecture contracts and ADRs
- operator-facing health, risk, and audit surfaces
- governance and identity doctrine
- extension-boundary doctrine
- community-facing and release-facing narrative surfaces

That growth is healthy, but it creates a new failure mode: fragmentation. A subsystem can remain locally well-documented while the overall system stops telling one consistent story.

The Unity Audit exists to detect that fragmentation before architectural, operational, or social drift compounds.

Coherence is now an architectural concern.

## What The Unity Audit Is

The Unity Audit is a coherence framework for Codexify.

It asks whether runtime truth, doctrine, operator reality, and user-facing narrative still align closely enough that:

- operators can reason about the real system
- contributors can follow the governing contracts
- release claims stay narrower than the evidence
- community-facing explanation does not drift away from what actually exists

Coherence is not aesthetic polish. It is alignment between runtime truth, doctrine, operator reality, and user-facing narrative.

A green health endpoint alone is insufficient.

Documentation presence alone is insufficient.

People understanding what Codexify actually is is treated as a legitimate system concern.

## What Coherence Means In Codexify

Inside Codexify, coherence means:

- live runtime evidence outranks documentation alone
- release truth stays distinct from structural architecture description
- governance language does not silently redefine runtime semantics
- operator surfaces describe real failure boundaries rather than comforting summaries
- extension narratives do not overreach sovereignty, identity, or capability boundaries
- community-facing explanation does not imply support, autonomy, or readiness beyond proof

Coherence does not require every surface to say the same thing in the same words. It requires the surfaces to be mutually interpretable without misleading people about what Codexify is, what it can do, and what has actually been proven.

## Participating Architectural Surfaces

The first canonical Unity Audit input surfaces are:

- `00-current-state.md` for short-horizon release and operational truth
- live proof artifacts and daily audit outputs for supported-path runtime evidence
- architecture KB docs for structure, contracts, and subsystem boundaries
- ADRs and contract docs for normative meaning
- governance doctrine for identity, sovereignty, export, and extension boundaries
- operator-facing health, risk, and manual surfaces
- release-facing and community-facing narrative surfaces when they make product claims

## What Drift It Detects

The Unity Audit is intended to detect:

- runtime truth drift: supported-path behavior no longer matches docs or release language
- contract drift: implementation and docs no longer preserve the same meaning
- surface drift: operator, UI, and documentation surfaces describe conflicting realities
- governance drift: identity, sovereignty, or permission boundaries weaken in practice or in narrative
- extension drift: plugins, tools, or agent surfaces imply authority outside bounded doctrine
- narrative drift: external explanation outruns proof, release posture, or governance truth

## What It Explicitly Does Not Claim

The Unity Audit does not claim:

- a fully implemented runtime subsystem
- a unified scoring engine
- an automated governance oracle
- a magical AI evaluator that can settle architecture disputes
- that coherence replaces runtime proof
- that narrative alignment can override contracts, tests, or live evidence

It is a coherence framework, not a magical AI evaluator.

## Distinctions The Audit Must Preserve

The Unity Audit explicitly distinguishes:

- runtime proof: live supported-path or test-backed evidence about what the system actually does
- documentation coherence: whether the architecture corpus stays internally consistent and accurately bounded
- governance coherence: whether identity, sovereignty, permission, and export doctrines remain aligned across surfaces
- release truth: what the project currently claims as supported, ready, or in-bounds
- social and community coherence: whether outside-facing explanation still matches the narrower architectural and runtime truth

These are related surfaces, not interchangeable ones.

## Canonical Audit Lenses

### 1. Runtime Truth

Purpose:
Confirm that live runtime evidence, supported-path claims, and current-state framing still describe the same system.

Example evidence sources:

- `docs/architecture/00-current-state.md`
- supported-path live proof artifacts
- daily audit artifacts
- health surfaces such as `/health`, `/health/chat`, `/api/health/llm`, `/api/health/retrieval`
- targeted runtime tests when they are explicitly scoped as proof for a seam

Drift patterns:

- green endpoint used as a proxy for full runtime readiness
- supported path shifts but docs or proof artifacts lag
- code-path-only capability described as release-proven

Failure examples:

- provider warmup or queue coupling presented as simple offline/online truth
- a route exists and is therefore narrated as shipped
- stale proof is still used as current release evidence

Proof expectations:

- prefer fresh live supported-path evidence when release readiness is implicated
- distinguish test-backed seam proof from live runtime proof
- treat `00-current-state.md` as the short-horizon override for release claims

Non-goals:

- replace subsystem-specific operational audits
- infer social readiness from runtime proof alone

### 2. Contract Integrity

Purpose:
Check that normative contracts, ADRs, token vocabularies, and implementation seams still preserve the same meanings.

Example evidence sources:

- `chat-runtime-contract.md`
- `kb-validity-matrix.md`
- `account-export-restore-contract.md`
- `router-decision-table.md`
- `self-extending-agent-plugin-system.md`
- related ADRs and token-domain contracts

Drift patterns:

- runtime states collapsed into simpler but misleading binaries
- message identity, request identity, and run identity blurred together
- planning notes or old docs shadow current contract terms

Failure examples:

- request acceptance narrated as completion
- export semantics described in ways that weaken provenance guarantees
- retrieval posture language that bypasses explicit router doctrine

Proof expectations:

- contract-bearing language should match canonical docs or explicitly declare a proposed change
- contradictions should be called out instead of silently normalized

Non-goals:

- replace ADR process
- bless code-path-only behavior as canonical contract by repetition

### 3. Surface Coherence

Purpose:
Check whether docs, operator surfaces, UI framing, and runtime status surfaces still describe compatible realities.

Example evidence sources:

- architecture KB docs
- operator manuals
- risk register entries
- runtime diagrams
- frontend status wording and shell surfaces when they encode system meaning

Drift patterns:

- operator diagnosis requires crossing multiple surfaces that contradict each other
- UI wording flattens nuance preserved in the contracts
- diagrams or overviews keep legacy topology after the supported path narrows

Failure examples:

- the shell implies autonomy or readiness that the runtime docs explicitly bound away
- a current risk is absent from the surfaces most operators actually use
- a legacy overview still dominates understanding after the runtime moved on

Proof expectations:

- identify which surface is authoritative for which question
- prefer cross-surface consistency checks over single-doc correctness

Non-goals:

- enforce identical phrasing across docs
- replace subsystem UX review or copy review

### 4. Governance Integrity

Purpose:
Check whether identity, sovereignty, permission, export, and accountability doctrines remain aligned across architecture and release language.

Example evidence sources:

- identity and runtime-mode doctrine
- `account-export-restore-contract.md`
- IDDB policy surfaces
- extension governance docs
- release or support claims that touch authority, privacy, or accountability

Drift patterns:

- identity boundaries weakened in UI or narrative language
- capability claims outrun explicit permission or provenance rules
- operator convenience language erodes sovereignty guarantees

Failure examples:

- persona or plugin surfaces implied to own identity
- export/restore language that obscures lineage guarantees
- release notes that imply broader authority than governance docs allow

Proof expectations:

- governance claims must remain auditable in explicit contracts
- enforcement in code and boundary docs outranks prompt-only or narrative assurances

Non-goals:

- replace security review
- turn governance doctrine into marketing language

### 5. Extension Discipline

Purpose:
Check whether extension, plugin, tool, and agent-adjacent surfaces stay inside Codexify's bounded sovereignty and runtime doctrine.

Example evidence sources:

- `self-extending-agent-plugin-system.md`
- command-bus and tool-loop doctrine
- Pi invocation boundary docs
- delegation and operator docs

Drift patterns:

- extension proposals implied to have runtime powers they do not have
- command-bus or plugin surfaces described as autonomous where they are bounded or manual
- future harness concepts narrated as current runtime support

Failure examples:

- a plugin narrative implies direct identity mutation authority
- a coding-agent seam is described as a general autonomous agent runtime
- extension capability summaries omit review, registration, or bounded execution rules

Proof expectations:

- extension claims must identify current implementation status versus contract-only surfaces
- bounded execution seams must preserve authority, lineage, and review discipline

Non-goals:

- replace extension-specific implementation audits
- promise future orchestration simply because doctrine exists

### 6. Narrative Readiness

Purpose:
Check whether public, release-facing, investor-facing, community-facing, or onboarding narratives still match runtime truth and governance boundaries closely enough to be safely repeated.

Example evidence sources:

- `00-current-state.md`
- supported-profile proof artifacts
- architecture overview docs
- release notes, demos, onboarding decks, and community-facing summaries

Drift patterns:

- conceptual doctrine presented as shipped capability
- internal-only surfaces described as public release posture
- social explanation narrows ambiguity by overstating capability

Failure examples:

- community copy implies decentralization or autonomy beyond the supported path
- a future-facing architecture note is reused as if it were release truth
- operator-only capability is retold as end-user-ready product behavior

Proof expectations:

- public claims should be traceable back to narrower runtime or governance truth
- release-facing language must remain bounded by fresh evidence

Non-goals:

- replace product strategy
- optimize copy style or marketing tone by itself

## Fragmentation Signals

The Unity Audit should treat the following as fragmentation signals:

- one surface says "supported" while another says "experimental"
- release language depends on stale proof
- operator manuals require contradictions to be hand-waved away
- community-facing explanation routinely needs caveats that the architecture docs already know
- governance doctrine is explicit but UI or docs imply a looser reality
- old docs shadow the current meaning of canonical contracts

## Coherence Debt

Coherence debt is the accumulated cost of leaving cross-surface contradictions unresolved.

It appears when:

- truth is locally maintained but globally inconsistent
- operators need tribal knowledge to reconcile official surfaces
- release posture has to be re-explained from scratch too often
- governance or extension boundaries are technically intact but narratively blurred

Coherence debt is not the same as missing polish. It is architecture debt expressed across meaning surfaces.

## Narrative Drift

Narrative drift is the gap between what Codexify can currently prove and what people repeat about it.

Typical causes include:

- future-facing design canon reused as present-state explanation
- stale demos or release notes
- social simplifications that erase supported-path boundaries

## Operator Truth Fracture

Operator truth fracture occurs when the surfaces an operator must use to diagnose the system no longer compose into one reliable mental model.

Typical examples include:

- health surfaces, runtime docs, and risk docs disagreeing about the main failure boundary
- status wording that collapses provider warmup, queue lag, and execution failure into one story

## Contract Shadowing

Contract shadowing occurs when a weaker, older, or more convenient surface starts informally redefining a stronger canonical contract.

Typical sources include:

- old architecture notes
- route or UI presence treated as contract proof
- convenience summaries that erase message-versus-request or authority boundaries

## Governance Drift

Governance drift occurs when identity, sovereignty, permission, or provenance commitments remain documented but are no longer consistently reflected in implementation, operator practice, or outward explanation.

## Current Reality

Right now, the Unity Audit is doctrine-first.

- existing daily audits, proof artifacts, and architecture docs are inputs
- no unified scoring engine yet exists
- no automated governance oracle exists
- no runtime-wide Unity Audit execution surface is claimed here
- this is a coherence framework, not a magical AI evaluator

## Relation To Existing Audits, Proofs, ADRs, And Truth Layers

The Unity Audit does not replace:

- live runtime proof
- subsystem-specific audits
- ADR governance
- release gating
- risk registers
- the KB validity matrix

Instead, it provides a synthesis lens over them.

Its job is to ask whether those surfaces still compose into one intelligible and truthful system story.

## Future-Compatible Surfaces

Future integrations may include:

- audit aggregation
- proof indexing
- runtime topology comparison
- operator deck integration
- governance regression checks
- release-readiness synthesis
- community-facing health snapshots

These are future-compatible surfaces only. This doctrine does not claim that any of them are implemented today.

## ADR Impact

- Classification: aligned with existing ADRs and contracts
- Governing ADRs and contracts:
  - runtime truth doctrine
  - KB validity matrix
  - chat runtime contract
  - account export + restore contract
  - self-extending plugin governance
  - identity and sovereignty doctrine
- Brief reason:
  - this doctrine introduces a unification and governance interpretation layer over existing architecture surfaces without changing runtime semantics, release rules, or contract authority
