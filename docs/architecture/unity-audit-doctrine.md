# Unity Audit Doctrine

Purpose: define Codexify's first canonical coherence audit layer across runtime truth, architecture doctrine, operator reality, governance boundaries, extension discipline, and outward-facing narrative without claiming a fully implemented runtime audit engine.
Last updated: 2026-05-22
Source anchors:
- docs/architecture/00-current-state.md
- docs/architecture/README.md
- docs/architecture/kb-validity-matrix.md
- docs/architecture/architecture-atlas.md
- docs/architecture/tech-debt-and-risks.md
- docs/architecture/modules-and-ownership.md
- docs/architecture/data-and-storage.md
- docs/architecture/flows.md
- docs/architecture/chat-runtime-contract.md
- docs/architecture/self-extending-agent-plugin-system.md
- docs/architecture/agent-protocol-operations.md
- docs/architecture/router-decision-table.md
- docs/architecture/account-export-restore-contract.md
- docs/architecture/persona-studio-spec.md
- docs/iddb_policy_v1.md

## Purpose

Codexify now has multiple strong truth surfaces:

- current-state release truth
- runtime contracts
- architecture doctrine
- governance and identity doctrine
- operational audits and proof artifacts
- extension and export contracts
- community-facing narrative and claim surfaces

Those surfaces are individually useful, but they can drift apart while each still looks locally reasonable. The Unity Audit exists to detect that fragmentation before architectural, operational, or social drift compounds.

Coherence is now treated as an architectural concern.

## What the Unity Audit Is

The Unity Audit is Codexify's doctrine for evaluating whether the system still tells one consistent story across:

- runtime truth
- architecture contracts
- operator-facing reality
- governance boundaries
- extension behavior
- release-safe narrative

It is a synthesis layer, not a replacement for proof, ADRs, or current-state truth.

## Why It Exists

Codexify has matured into a corpus where no single green endpoint, no single architecture note, and no single audit artifact is enough to establish system integrity.

Coherence is not aesthetic polish. It is alignment between runtime truth, doctrine, operator reality, and user-facing narrative.

A green health endpoint alone is insufficient.
Documentation presence alone is insufficient.
People understanding what Codexify actually is is a legitimate system concern.

## What Coherence Means in Codexify

In this doctrine, coherence means that:

- live runtime evidence does not materially contradict the release-truth layer
- architecture contracts do not silently diverge from implemented or supported behavior
- operator surfaces do not imply success, readiness, or authority that the runtime does not actually provide
- governance doctrine still matches what the system allows, persists, exports, and presents
- extension surfaces do not shadow or dilute canonical boundaries
- community-facing narrative remains evidence-bound, release-safe, and legible

Coherence does not require every surface to say the same thing. It requires each surface to say the right thing for its layer without misleading adjacent layers.

## Distinctions That Must Stay Explicit

The Unity Audit does not collapse different truth classes into one bucket.

- `runtime proof`: live or test-backed evidence that a supported or implemented path behaves as claimed
- `documentation coherence`: whether architecture docs, indices, specs, and contract notes agree about what is implemented, supported, internal, planned, or quarantined
- `governance coherence`: whether identity, export, plugin, permission, and policy surfaces still enforce the doctrine they claim to enforce
- `release truth`: the short-horizon operational truth about what is currently supported, blocked, or outside the release promise
- `social/community coherence`: whether people encountering Codexify from outside the implementation core can still understand what it is without being misled by hype, stale language, or mixed maturity signals

## Participating Architectural Surfaces

The Unity Audit may draw evidence from:

- `00-current-state.md` and supported-path live proof artifacts
- runtime contracts such as chat/runtime, routing, export/restore, and extension doctrine
- architecture KB routing and validity rules
- risk registers, operational audits, and daily audit artifacts
- operator surfaces, health surfaces, and diagnostic proof notes
- identity and governance doctrine
- product and configuration surfaces that shape operator or user expectations
- community-facing claim and narrative surfaces when evaluating release-safe outward coherence

The Unity Audit is strongest when these surfaces agree for the same reason, not merely by wording similarity.

## Drift Classes the Unity Audit Detects

### Fragmentation Signals

Fragmentation Signals are evidence that one or more truth surfaces are beginning to tell different stories about Codexify.

Examples:

- current-state says a surface is internal-only while adjacent docs present it as public-ready
- operator panels suggest authority or execution that governance docs still prohibit
- a planning document starts being read as release truth because KB routing is weak

### Coherence Debt

Coherence Debt is the accumulated cost of unresolved mismatches between runtime truth, doctrine, operator understanding, and narrative framing.

It often appears before a hard failure, then later amplifies release confusion, audit fatigue, or governance mistakes.

### Narrative Drift

Narrative Drift is when public, internal, or community-facing explanations of Codexify widen beyond what runtime truth and governance evidence justify.

### Operator Truth Fracture

Operator Truth Fracture is when operator-visible health, status, or inspection surfaces imply a cleaner or more complete reality than the runtime can currently prove.

### Contract Shadowing

Contract Shadowing is when a newer surface, convenience note, UI behavior, or repeated habit starts functionally replacing a canonical contract without explicit governance ratification.

### Governance Drift

Governance Drift is when identity, permission, provenance, export, extension, or release-boundary doctrine no longer matches actual system behavior or accepted operational interpretation.

## Canonical Audit Lenses

### 1. Runtime Truth

Purpose:
Determine whether the live or test-backed runtime still matches Codexify's claimed supported behavior and release-truth posture.

Example evidence sources:

- `00-current-state.md`
- supported-path live proof artifacts
- `flows.md`
- health and catalog proof notes
- runtime-focused audits and regression outputs

Drift patterns:

- green health or provider reachability standing in for full runtime truth
- supported-path wording lagging behind current runtime behavior
- internal/manual paths being mistaken for supported release surfaces

Failure examples:

- queue acceptance is interpreted as completion
- a warming or degraded model is labeled offline or healthy in the wrong way
- a successful internal artifact lane is described as release-supported user flow

Proof expectations:

- supported-path claims need live or recent proof
- runtime claims must distinguish implemented, proven, partial, and internal-only
- operator-visible status must not outrank current-state truth

Non-goals:

- scoring architecture prose quality
- treating route presence or type definitions as proof
- widening release readiness based on optimistic runtime interpretation

### 2. Contract Integrity

Purpose:
Check that canonical contracts still align with each other and with the actual meaning of runtime semantics, state models, and persistence guarantees.

Example evidence sources:

- `chat-runtime-contract.md`
- `router-decision-table.md`
- `account-export-restore-contract.md`
- `data-and-storage.md`
- `agent-protocol-operations.md`

Drift patterns:

- implementation or operator habits collapsing distinct state machines
- new local patterns shadowing canonical contracts
- persistence or lineage semantics drifting from declared invariants

Failure examples:

- provider state and request state are treated as one state machine
- retries are presented as new messages rather than new attempts
- export or restore behavior silently drops provenance while docs still promise preservation

Proof expectations:

- contract-bearing claims should map to code, tests, or explicit doctrine scope
- contradictions between contracts must be surfaced, not normalized away
- the canonical contract must remain easy to identify

Non-goals:

- replacing ADRs
- inventing new semantics to reconcile ambiguous docs
- using doctrine wording to overwrite runtime evidence

### 3. Surface Coherence

Purpose:
Evaluate whether user-facing and operator-facing surfaces expose system state in ways that remain truthful across runtime, diagnostics, and workflow boundaries.

Example evidence sources:

- `flows.md`
- `tech-debt-and-risks.md`
- operator manuals and proof notes
- health surfaces and diagnostic routes
- persona and shell-facing surface docs where they shape expectations

Drift patterns:

- operator UI implying execution, readiness, or authority beyond what the backend proves
- diagnostic surfaces being mistaken for durable truth
- adjacent product surfaces describing the same state with incompatible meaning

Failure examples:

- a panel looks green while downstream worker return-path proof is absent
- a debug trace is read as release signoff
- a configuration surface implies durable identity or memory mutation that it does not own

Proof expectations:

- surface semantics must be checked against the runtime layer they summarize
- visibility proof does not substitute for execution proof
- operator-facing truth should be explicit about scope, lag, and limitations

Non-goals:

- design polish review
- visual consistency scoring
- requiring one single-pane operator dashboard before doctrine can exist

### 4. Governance Integrity

Purpose:
Verify that identity, provenance, permissions, export, and release-boundary doctrine still match actual system commitments and allowed behavior.

Example evidence sources:

- `kb-validity-matrix.md`
- `account-export-restore-contract.md`
- `docs/iddb_policy_v1.md`
- current-state release truth
- governance-oriented audits and risk registers

Drift patterns:

- release-safe labels falling out of sync with documentation or operator assumptions
- provenance or ownership guarantees being weakened in practice
- governance terms being reused loosely in product copy or implementation notes

Failure examples:

- docs imply export completeness that the runtime has not proven
- identity surfaces are described as conversationally mutable when doctrine says otherwise
- a planning-only note begins functioning as a support commitment

Proof expectations:

- governance claims must stay evidence-bound
- provenance, ownership, and release-boundary claims need contract-level specificity
- short-horizon release truth must outrank broader or older governance prose when support scope is the question

Non-goals:

- magical governance automation
- replacing human judgment for release or policy decisions
- treating terminology presence as enforcement proof

### 5. Extension Discipline

Purpose:
Determine whether extension-related surfaces still preserve Codexify's bounded, sovereignty-aware governance instead of drifting toward implicit self-modification or authority widening.

Example evidence sources:

- `self-extending-agent-plugin-system.md`
- plugin or capability governance notes
- agent protocol guidance
- permission and binding doctrine

Drift patterns:

- extension language implying autonomous runtime execution that does not exist
- generated capability notes bypassing install, review, or lineage doctrine
- convenience integrations shadowing canonical extension boundaries

Failure examples:

- a plugin narrative implies runtime autonomy where only proposal or registry surfaces exist
- extension outputs are treated as if they can rewrite identity or core runtime law
- a helper note starts functioning as the de facto extension contract

Proof expectations:

- extension claims must distinguish proposal, contract, implemented backend seams, and unsupported future lanes
- install, scope, lineage, and permission boundaries must remain explicit
- extension surfaces must not dilute canonical governance docs

Non-goals:

- proving every future extension lane today
- claiming sandbox or autonomous orchestration exists because doctrine names it
- collapsing Pi-like invocation doctrine into plugin runtime truth

### 6. Narrative Readiness

Purpose:
Assess whether Codexify can be described to operators, collaborators, and the community in a way that is accurate, evidence-bound, and aligned with real system maturity.

Example evidence sources:

- `00-current-state.md`
- architecture README and atlas routing
- current proof artifacts and audit summaries
- governance doctrine and release-truth docs
- community-facing claim surfaces when present

Drift patterns:

- polished narrative outrunning proof
- internal capability lanes leaking into public identity
- stale legacy framing confusing present product identity

Failure examples:

- community-facing copy implies cloud or autonomous support outside the current release promise
- architecture notes present speculative future lanes as current product identity
- contributors cannot explain what Codexify currently is without contradicting the current-state layer

Proof expectations:

- outward narrative should be traceable back to current-state truth and supporting evidence
- supported, internal-only, planning, and speculative surfaces must remain clearly separated
- narrative safety is stronger when multiple truth surfaces reconcile without hand-waving

Non-goals:

- marketing optimization
- aesthetic brand review
- replacing runtime proof with persuasive writing

## What the Unity Audit Explicitly Does Not Claim

The Unity Audit does not claim:

- a fully implemented runtime scoring system
- an automated governance oracle
- a single number that proves architecture health
- AI-based authority to overrule current-state truth, proofs, or ADRs
- automatic release readiness
- a replacement for daily audits, live proof, or operator judgment

## Relationship to Existing Truth Layers

The Unity Audit sits above, and depends on, existing truth layers.

- `00-current-state.md` remains the short-horizon release-truth override
- live proof artifacts remain the source for supported-path runtime claims
- architecture contracts remain the source for semantics and invariants
- ADRs remain the source for decision rationale
- audits and risk registers remain evidence inputs, not superseded outputs

The Unity Audit asks whether those layers still reconcile. It does not replace their authority inside their own scopes.

## Current Reality

The Unity Audit is initially doctrine-first.

- existing daily audits, proof artifacts, and architecture docs are inputs
- no unified scoring engine yet exists
- no automated governance oracle exists
- no magical AI evaluator exists behind this doctrine
- the current value is a coherence framework that makes fragmentation legible earlier

## Future-Compatible Surfaces

Future integration may include any of the following, if separately designed and proven:

- audit aggregation
- proof indexing
- runtime topology comparison
- operator deck integration
- governance regression checks
- release-readiness synthesis
- community-facing health snapshots

These are compatibility directions only. They are not implementation claims in this doctrine.

## ADR Impact

Classification: aligned with existing ADRs and contracts

Governing ADRs and contracts:

- runtime truth doctrine
- KB validity matrix
- chat runtime contract
- account export + restore contract
- self-extending plugin governance
- identity and sovereignty doctrine

Reason:

- this doctrine introduces a unification and governance interpretation layer over existing architecture contracts
- it does not alter runtime semantics, release criteria, identity policy, export semantics, or extension authority

## Invariants

- Do not invent runtime implementation that does not exist.
- Do not silently redefine release readiness.
- Do not collapse runtime truth into documentation truth.
- Do not replace ADR governance with narrative language.
- Do not introduce magical AI governance claims.
- Preserve the doctrine that live runtime evidence outranks docs alone.

## Maintenance Rule

Update this doctrine when:

- a new truth surface becomes architecturally important
- a new audit class materially changes coherence expectations
- current-state release truth or governance doctrine adds a new boundary the audit must evaluate

Do not update this doctrine merely to make an unsupported surface sound more unified.
