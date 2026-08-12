# DLG Phase 4A ADR Number-Collision Canonicalization Review

## Status

Proof / governance review — Proposed, pending human canonicalization decision.

This artifact is **not** an ADR. It is not a proposed architectural decision. It is a
Phase 4A governance review/proof artifact authored under the [Document Lifecycle Graph
(DLG) Phase 4 doctrine](../../document-lifecycle-graph-contract.md) ("Phase 4: human
canonicalization"). Its "Proposed" label refers to the **review recommendations** —
advisory, bounded, and awaiting one explicit human decision per collision — and does
**not** modify or propose any ADR status. It is non-destructive: no ADR body, status,
index entry, DLG node, DLG relation, or generated projection is altered by this review.

Recommendations are advisory. Canonicalization remains pending. No canonicalization is
executed by this artifact.

## Scope

This artifact records a decision-grade review of the seven ADR-number collisions
detected by Phase 3A in the main `docs/architecture/adr/` directory (prefixes 005,
016, 024, 039, 041, 053, 055), plus one material Phase 4 governance finding:
a **third** ADR-041 claimant under `docs/architecture/adr/proposed/`, outside the
direct Phase 3A collision report's main-directory scope.

It does **not**:

- execute any file rename, rewrite, or tombstone;
- modify `adr-index.md`, `00-current-state.md`, any ADR body, ADR-056, ADR-057, the
  DLG contract, product lanes and boundaries, DLG node records, DLG relations, or
  any generated Phase 3 projection or Agent Reading Packet;
- create a DLG node for any ADR;
- accept or reject any ADR status on the human maintainer's behalf;
- widen release claims or alter `00-current-state.md`;
- invent replacement ADR numbers;
- select a canonical ADR number for any collision;
- create a compatibility pointer, tombstone, or supersession edge;
- renumber, supersede, retire, or otherwise move any ADR body.

## Governing doctrine

- [ADR-056](../../adr/056-document-lifecycle-graph-control-plane.md) — Document
  Lifecycle Graph Control Plane (Accepted 2026-08-07). Phase 4 doctrine governs
  human canonicalization of duplicate or competing authority.
- [ADR-057](../../adr/057-product-architecture-ontology-dlg-integration.md) —
  Product Architecture Ontology as a DLG Extension (Accepted 2026-08-07). Its
  "Governing ADRs and alignment" section (lines 127-141) explicitly names a subset
  of the 14 main-directory collision files and is treated as scoped post-collision
  governance evidence within this review. ADR-057 itself is **not** altered by this
  review.
- [DLG Contract](../../document-lifecycle-graph-contract.md) — Phase 0 inventory,
  Phase 1 classify, Phase 2 connect, Phase 3 validate and generate, **Phase 4 human
  canonicalization**, Phase 5 rewrite canonical documents, Phase 6 replace duplicate
  authority, Phase 7 retrieval integration, Phase 8 optional projections.

This review sits inside Phase 4 and does not authorize Phase 5 or Phase 6 globally.
Phase 5 and Phase 6 work may only proceed after a separately approved implementation
task triggered by an explicit human canonicalization decision for the relevant
collision.

## Canonical base

All evidence was gathered against canonical `origin/main` revision
`a2b0a1482775884f6f5574d1cdcf75c5eaf34505` (Phase 4A evidence commit,
2026-08-08). The original review was authored in an isolated detached worktree rooted
at that commit; this corrected review preserves the same evidence base.

## Evidence posture and methodology

This review is grounded in the following evidence classes, applied per-collision:

| Evidence class            | What it examines                                                                                              |
|---------------------------|---------------------------------------------------------------------------------------------------------------|
| **Status classification** | Accepted vs Proposed; a Proposed ADR that shares a number with an Accepted ADR is a de facto number-conflict resolution signal. |
| **Git history**           | Introduction date, chronological precedence, renumbering chains, merge adjudications, deletion/restore patterns. |
| **Explicit governance citations** | ADR-057 (Accepted 2026-08-07) explicitly names a subset of the 14 ADRs by title, establishing post-collision governance preference. `architecture/README.md` and the ADR index also provide annotated canonical pointers. |
| **Direct-path reference surface** | Non-collision files that link to a specific collision ADR path (outside `docs/architecture/adr/`). A file with zero external path references has low known repository-local rewrite risk if renumbered or tombstoned. |
| **Numeric-token reference surface** | Non-collision files that refer to `ADR-NNN` with or without a disambiguating title. Numeric references without disambiguating title are ambiguous and introduce downstream reachability risk when a number is reassigned. |
| **Semantic relationship classification** | Whether the two collision files are independent decisions on unrelated architecture scopes, related/complementary decisions, or true duplicate decisions where two files address the same topic. |

**Repository-local reference inspection cannot prove the absence of external
citations, bookmarks, issues, downstream clones, or human notes.**

**Source corpus:** 14 main-directory ADR files (7 prefixes × 2 files each) +
`adr-index.md` + ADR-057 + `architecture/README.md` + the third Proposed ADR-041
under `docs/architecture/adr/proposed/` + all other tracked `docs/**` files.
Baseline validators (Phase 3A `validate_and_generate_dlg.py validate`, Phase 3B
`generate_representative_arps.py validate`, `make docs`) pass at the canonical
repository revision `a2b0a1482`.

## Collision summary

| Prefix | Claimants                                                                                                                                               | Relationship classification                | Current explicit statuses                                            | Preferred existing-number holder (advisory)            | Recommended treatment (advisory)                                | Known repository-local rewrite risk | Human approval state |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|----------------------------------------------------------------------|--------------------------------------------------------|---------------------------------------------------------------|--------------------------------------|---------------------|
| 005    | `005-imprint-ui-deprecation-and-identity-ownership.md`, `005-runtime-mode-and-account-boundary-invariants.md`                                          | Independent decisions; numeric collision   | Proposed (Imprint UI) / Accepted (Runtime Mode)                      | Runtime Mode (Accepted, ADR-057-cited)                 | Imprint UI: independent Proposed ADR; renumber after approval   | Known low for Imprint UI; `adr-index.md` rewrite required | pending             |
| 016    | `016-continuity-governance-surface-contract.md`, `016-workspace-retrieval-source-for-local-knowledge.md`                                                | Independent decisions; numeric collision   | Accepted (Continuity Governance) / Accepted (Workspace Retrieval)    | Continuity Governance (Accepted, ref-convergence)      | Workspace Retrieval: renumber after approval; preserve Accepted | Known medium (2 path refs, 7 numeric refs need update) | pending             |
| 024    | `024-context-command-active-connector-semantics.md`, `024-workspace-obsidian-selection-and-injection-contract.md`                                       | Related but distinct; numeric collision    | Accepted (Context Command) / Accepted (Workspace Obsidian)            | Context Command (Accepted, ref-convergence)            | Workspace Obsidian: renumber after approval; preserve Accepted | Known low for Workspace Obsidian      | pending             |
| 039    | `039-capability-oriented-mesh-architecture.md`, `039-operator-user-access-boundary.md`                                                                  | Status-gated + governance-anchored; numeric | Accepted (Capability Mesh) / Proposed (Operator/User)                | Operator/User (Proposed, ADR-057-cited, chronology)    | Capability Mesh: renumber after approval; preserve Accepted    | Known low for Capability Mesh         | pending             |
| 041    | `041-provider-capability-model-contract.md`, `041-vaultnode-canonical-machine-and-audit-authority.md`, `proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` | Three-claimant; numeric collision (main: two-way, proposed/: third) | Proposed (Provider Capability) / Accepted (VaultNode) / Proposed (Pi Loop Manager) | VaultNode (Accepted, ADR-057-cited)                    | Provider Capability: renumber; Pi Loop Manager: separately renumber; preserve each identity | Known low for Provider Capability; known reference surface for Pi Loop Manager | pending             |
| 053    | `053-node-hosted-room-access-boundary.md`, `053-threadspace-whispermesh-managed-service-boundary.md`                                                    | Explicitly-adjudicated near-duplicate      | Proposed (Node-Hosted Room) / Proposed (ThreadSpace/WhisperMesh)     | Node-Hosted Room (merge adjudication, ADR-057-cited)   | ThreadSpace/WhisperMesh 053 copy: Phase 6 cleanup candidate; preserve governance chain to 055 | Known low                              | pending             |
| 055    | `055-orthogonal-ui-material-personalization.md`, `055-threadspace-whispermesh-managed-service-boundary.md`                                             | Governance-intent collision                | Accepted (Orthogonal UI) / Proposed (ThreadSpace/WhisperMesh)        | ThreadSpace/WhisperMesh (ADR-057-cited, commit-chain)  | Orthogonal UI: renumber after approval; preserve Accepted       | Known medium (3 numeric refs need update) | pending             |

Human approval state is **pending** for all seven collisions. No ADR has been
canonicalized by this review.

## ADR-005 review

### Facts

| File                                                              | Status   | Date       | Lines | Author          |
|-------------------------------------------------------------------|----------|------------|-------|-----------------|
| `005-imprint-ui-deprecation-and-identity-ownership.md`            | Proposed | 2026-04-15 | 172   | resonant-jones  |
| `005-runtime-mode-and-account-boundary-invariants.md`             | Accepted | 2026-04-19 | 135   | resonant-jones  |

### History

Imprint UI was introduced first but never moved past Proposed. The file itself has a
self-documenting closing note (line 172): *"If this decision has already been
formally ratified in-repo, change Status from `Proposed` to `Accepted`."* Runtime Mode
was introduced four days later and Accepted.

### Governance citations

ADR-057 line 133 explicitly cites "**ADR-005** (Runtime Mode and Account Boundary
Invariants)." The ADR index lists both files under the same reading-order index
entry, noting Imprint UI is "retained as the legacy identity-ownership UI boundary
note" (line 42). All 17 external numeric `ADR-005` references unambiguously point to
Runtime Mode (they cite "runtime mode," "account boundary invariants," or link to
the runtime-mode file path). Zero external references point to the Imprint UI path
or title by name.

### Direct-path reference surface

Runtime Mode → 3 direct references. Imprint UI → 0.

### Classification

**Independent decisions sharing only a number.** Imprint UI is Proposed and concerns
identity-ownership UI boundary semantics; Runtime Mode is Accepted and concerns
runtime-mode and account-boundary invariants. They are distinct architectural
subjects. The collision is **numerical, not identity continuity**.

Status classification is one input: Runtime Mode is Accepted; Imprint UI is Proposed.
ADR-057 governance citation is one input: ADR-057 names Runtime Mode.

### Recommended existing-number holder (advisory)

`005-runtime-mode-and-account-boundary-invariants.md` (Accepted, governance-cited,
all numeric references converge). The recommendation is supported by status posture
and post-collision governance citation but **does not authorize any implementation**.

### Recommended non-holder treatment (advisory)

`005-imprint-ui-deprecation-and-identity-ownership.md` should be preserved as an
**independent Proposed ADR** and **renumbered after human approval** to a future
unoccupied number. The Proposed posture must be preserved. Candidate future
number: **not assigned in Phase 4A**.

**A compatibility pointer from Imprint UI to Runtime Mode is not recommended.**
Imprint UI and Runtime Mode are independent decisions; pointer_to semantics would
imply a continuity of identity that the evidence does not establish. Collision
evidence alone does not authorize retirement of the Imprint UI proposal; any
retirement would require its own separate human disposition and is **not** part of
this review's recommendation.

### Known repository-local rewrite risk

For Imprint UI: zero external path-references; zero numeric-references by name or
title. Only `adr-index.md` would need a path entry update if the file were renamed.
Known repository-local rewrite risk: **low**. External-reference risk: **unknown /
not evaluated**.

## ADR-016 review

### Facts

| File                                                  | Status   | Date       | Lines | Author          |
|-------------------------------------------------------|----------|------------|-------|-----------------|
| `016-continuity-governance-surface-contract.md`       | Accepted | 2026-04-28 | 264   | resonant-jones  |
| `016-workspace-retrieval-source-for-local-knowledge.md` | Accepted | 2026-04-27 | 56    | resonant-jones  |

### History

Workspace Retrieval was introduced first (Apr 27) but received the same number as
Continuity Governance (Apr 28). Both are Accepted.

### Governance citations

ADR-057 does not explicitly cite ADR-016. The ADR index lists both files under the
same reading-order entry (line 53). `architecture/README.md` line 95 points to
Continuity Governance.

### Semantic relationship

**Independent decisions.** Continuity Governance defines a user-governed control
plane for continuity scope, intensity, decay, import treatment, exclusions,
inspection, and reset. Workspace Retrieval defines `retrievalSource="workspace"` as a
live backend source mode for chat completions. They address different architecture
layers (continuity governance vs retrieval source semantics), do not reference each
other, and have no content overlap. This is a **pure numbering collision between two
independent Accepted decisions**.

### Numeric reference ambiguity

14 numeric `ADR-016` references cite "continuity governance" (Continuity Governance);
7 cite "Workspace Retrieval Source" (Workspace Retrieval). Both have meaningful
downstream citation chains. In particular,
`023-workspace-e2e-proof-harness-contract.md` and
`024-workspace-obsidian-selection-and-injection-contract.md` both link to the
Workspace Retrieval path as a governing dependency.

### Direct-path reference surface

Continuity Governance → 2 direct refs. Workspace Retrieval → 0 direct refs from
outside `docs/architecture/adr/` (the 023 and 024 references appear as path links
within those ADR bodies and are recorded as numeric-reference surface for
Workspace Retrieval).

### Classification

**Independent-accepted collision.** Two unrelated Accepted decisions on the same
number. Ref-convergence (14 vs 7) and README anchor decide the advisory
recommendation; this is a tiebreaker, not identity continuity.

### Recommended existing-number holder (advisory)

`016-continuity-governance-surface-contract.md` (Accepted, higher numeric-token
reference convergence, explicit README anchor, larger content scope with continuity
*governance* semantics that apply across the system). The recommendation does not
authorize any implementation.

### Recommended non-holder treatment (advisory)

`016-workspace-retrieval-source-for-local-knowledge.md` should be preserved as an
**independent Accepted ADR** and **renumbered after human approval**. The Accepted
status must be preserved. Candidate future number: **not assigned in Phase 4A**.
Workspace Retrieval's reference chain to
`023-workspace-e2e-proof-harness-contract.md` and
`024-workspace-obsidian-selection-and-injection-contract.md` would need target-path
updates as part of any future renumbering.

### Known repository-local rewrite risk

For Workspace Retrieval: 2 internal path-references in its own body and the
external `023`/`024` path links must be updated on renumber. Numeric references
include a disambiguating title, so they survive renumbering with contextual intent
intact. Known repository-local rewrite risk: **medium**. External-reference risk:
**unknown / not evaluated**.

## ADR-024 review

### Facts

| File                                                       | Status   | Date       | Lines | Author          |
|------------------------------------------------------------|----------|------------|-------|-----------------|
| `024-context-command-active-connector-semantics.md`        | Accepted | 2026-05-07 | 189   | Chris Castillo  |
| `024-workspace-obsidian-selection-and-injection-contract.md` | Accepted | 2026-05-06 | 67    | Chris Castillo  |

### History

Both authored by Chris Castillo within ~1.5 hours on May 6-7, 2026. Both Accepted.
Both reference the same Obsidian workspace surface but from different architectural
angles.

### Governance citations

ADR-057 does not explicitly cite ADR-024. The ADR index lists both files
(lines 63-64). `architecture/README.md` line 81 points to Context Command.

### Semantic relationship

**Related but distinct.** Context Command governs the *general* connector invocation
doctrine — how Obsidian, GitHub, Discord, Drive, and MCP-backed connectors are
invoked through slash commands, attached, and consulted. Workspace Obsidian governs
the *specific* evidence-truthfulness contract for Obsidian-backed notes in the
workspace retrieval pipeline — whether a note was selected, injected, and reflected
in the completion context. Context Command is a broad doctrine; Workspace Obsidian is
a narrow evidence contract. Workspace Obsidian references ADR-016 and ADR-023 as
governing docs but does NOT reference Context Command. Context Command mentions
Obsidian as an example connector type.

### Numeric reference ambiguity

All 5 external `ADR-024` numeric references unambiguously cite Context Command.

### Direct-path reference surface

Context Command → 5 direct refs. Workspace Obsidian → 0.

### Classification

**Strongly-asymmetric accepted collision.** One file holds general connector doctrine
with 5 converging numeric references; the other is a narrow evidence-truth contract
with zero external references. The asymmetry makes the advisory canonical holder
unambiguous without collapsing identity.

### Recommended existing-number holder (advisory)

`024-context-command-active-connector-semantics.md` (general doctrine, 5 converging
citations, README anchor). The recommendation does not authorize any implementation.

### Recommended non-holder treatment (advisory)

`024-workspace-obsidian-selection-and-injection-contract.md` should be preserved as an
**independent Accepted ADR** and **renumbered after human approval**. The
Accepted status must be preserved. Candidate future number: **not assigned in
Phase 4A**. Its internal references to
`016-workspace-retrieval-source-for-local-knowledge.md` and
`023-workspace-e2e-proof-harness-contract.md` (line 58) would need target-path
updates on renumber.

### Known repository-local rewrite risk

For Workspace Obsidian: only one internal path reference (line 58). Zero external
files reference this path by name. Known repository-local rewrite risk: **low**.
External-reference risk: **unknown / not evaluated**.

## ADR-039 review

### Facts

| File                                          | Status                          | Date       | Lines | Author          |
|-----------------------------------------------|---------------------------------|------------|-------|-----------------|
| `039-capability-oriented-mesh-architecture.md` | Accepted (Architectural Principle) | 2026-06-30 | 483   | Resonant Jones  |
| `039-operator-user-access-boundary.md`         | Proposed                        | 2026-06-30 | 148   | Resonant Jones  |

### History

Operator/User was originally introduced as `038-operator-user-access-boundary.md` on
Jun 30 16:30 by Resonant Jones, then renumbered from 038→039 at 18:27 (`9f985d05`
"Renumber operator user boundary ADR"); the old 038 file was deleted at 18:29
(`4163ddb4` "Remove superseded operator boundary ADR number"); and a tombstone was
placed at 038 at 18:51 (`c8189ac4` "Mark superseded operator ADR duplicate") pointing
readers to ADR-039. The Capability Mesh ADR was introduced at 19:02 (`de9e08ad`
"docs: add capability-oriented mesh ADR") — **after** Operator/User had taken 039
by explicit renumbering. This is a chronological-precedence collision where both
authors acted independently within a 2-hour window.

### Governance citations

ADR-057 line 139 explicitly cites "**ADR-039** (Operator/User Access Boundary)."
`architecture/README.md` line 55 points to Operator/User. 9 external numeric
references cite Operator/User (by title or linked path); 0 cite Capability Mesh.

### Direct-path reference surface

Operator/User → 3 direct refs. Capability Mesh → 0.

### Classification

**Unusual evidence conflict.** Capability Mesh is Accepted; Operator/User is
Proposed. Yet Operator/User carries chronology-by-renumbering precedence, an
existing 038 tombstone precedent by the same author, an ADR-057 governance citation,
README anchor, and 9 converging numeric references. Capability Mesh is Accepted and
substantial (483 lines, governs networking mesh/capability authorization) but
arrived later and has zero external references.

This is the only collision pair where the **Proposed** file has the post-collision
governance citation and chronological precedence while the **Accepted** file
arrived later. The recommendation treats this as advisory but does **not** describe
it as mechanically settled — the unusual evidence conflict is an explicit human
disposition.

### Recommended existing-number holder (advisory)

`039-operator-user-access-boundary.md` (Proposed but governance-cited by ADR-057,
README anchor, clear chronological precedence through renumbering, 9 converging
numeric references, existing 038 tombstone precedent from Resonant Jones). The
recommendation does not authorize any implementation.

### Recommended non-holder treatment (advisory)

`039-capability-oriented-mesh-architecture.md` should be preserved as an
**independent Accepted ADR** and **renumbered after human approval**. Its content
remains Accepted and substantial. Candidate future number: **not assigned in
Phase 4A**. Capability Mesh has zero external references, so its known
repository-local rewrite risk is low.

### Known repository-local rewrite risk

For Capability Mesh: zero external path-references; zero numeric references.
Operator/User keeps the number and is therefore not at rewrite risk from this
review's recommendation. Known repository-local rewrite risk: **low**. External-
reference risk: **unknown / not evaluated**.

## ADR-041 review

### Facts — three claimants

| File                                                                                              | Status   | Date       | Lines | Author          |
|---------------------------------------------------------------------------------------------------|----------|------------|-------|-----------------|
| `041-provider-capability-model-contract.md`                                                       | Proposed | 2026-06-30 | 195   | Resonant Jones  |
| `041-vaultnode-canonical-machine-and-audit-authority.md`                                          | Accepted | 2026-07-10 | 299   | Resonant Jones  |
| `proposed/041-pi-loop-manager-campaign-runner-gate-graph.md`                                       | Proposed | 2026-07-03 | 216   | (per file)      |

### Third ADR-041 finding

The file
`docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md`
exists under the `proposed/` subdirectory, outside the Phase 3A main-directory
collision report. It is referenced by
`docs/specs/campaign-runner/PI_LOOP_RECEIPT_COMPATIBILITY_AUDIT.md` and therefore
has its own known repository-local reference surface that must not be silently
renumbered as collateral work.

This makes ADR-041 a **three-claimant canonicalization case**, not a two-way case.
The Phase 3A collision report's two-way framing is therefore not complete.

### History

Provider Capability arrived first (Jun 30) as Proposed. Pi Loop Manager (proposed
subdirectory, Jul 3) arrived second, also Proposed. VaultNode arrived third (Jul 10)
as Accepted. Chronologically, Provider Capability had first claim on the number
but never transitioned to Accepted.

### Governance citations

ADR-057 line 138 explicitly cites "**ADR-041** (VaultNode Canonical Machine and
Audit Authority)." `architecture/README.md` line 61 points to VaultNode. 10
external numeric references cite VaultNode (by title, linked path, or "trusted
latest" / "audit authority" context). 0 cite Provider Capability. The Pi Loop
Manager file does not appear in the external numeric reference surface counted for
ADR-041, but it is linked from `docs/specs/campaign-runner/PI_LOOP_RECEIPT_COMPATIBILITY_AUDIT.md`.

### Direct-path reference surface

VaultNode → 2 direct refs (audit artifacts). Provider Capability → 0. Pi Loop
Manager → 1 confirmed (`PI_LOOP_RECEIPT_COMPATIBILITY_AUDIT.md`).

### Classification

**Three-claimant governance case.**

- VaultNode is Accepted, ADR-057-cited, README-anchored, and has 10 converging
  numeric references. The evidence supports VaultNode retaining the number, but
  **no canonicalization is approved** by this review.
- Provider Capability is Proposed and Proposed-only. It addresses provider
  capability semantics and must retain its independent identity unless future
  evidence proves otherwise.
- Pi Loop Manager is Proposed, lives outside the main ADR directory, addresses
  Campaign Runner Pi Loop Manager receipt semantics, and has its own reference
  surface. It must retain its independent identity unless future evidence proves
  otherwise.

**No `pointer_to`, `supersedes`, or merge relationship is inferred** between any
two of the three ADR-041 claimants. VaultNode, Provider Capability, and Pi Loop
Manager are **distinct architectural subjects**.

### Recommended existing-number holder (advisory)

`041-vaultnode-canonical-machine-and-audit-authority.md` (Accepted, ADR-057-cited,
README anchor, 10 converging numeric references). The recommendation does not
authorize any implementation.

### Recommended non-holder treatment (advisory)

`041-provider-capability-model-contract.md` should be preserved as an independent
Proposed ADR and **renumbered after human approval** (Proposed status preserved).
Candidate future number: **not assigned in Phase 4A**.

`proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` should be preserved
as an independent Proposed ADR and **renumbered after human approval** as a
**separate canonicalization task** from Provider Capability — its known
reference surface (the Campaign Runner compatibility audit) must not be silently
renumbered as collateral work for the Provider Capability renumbering.
Candidate future number: **not assigned in Phase 4A**.

### Known repository-local rewrite risk

For Provider Capability: zero external references; known repository-local rewrite
risk: **low**. For Pi Loop Manager: 1 known direct-path reference that would need
a target update on renumber; known repository-local rewrite risk: **low** (but
non-zero; reference must be tracked separately). External-reference risk for both:
**unknown / not evaluated**.

## ADR-053 review

### Facts

| File                                                  | Status   | Date       | Lines | Author          |
|-------------------------------------------------------|----------|------------|-------|-----------------|
| `053-node-hosted-room-access-boundary.md`             | Proposed | 2026-07-27 | 419   | Resonant Jones  |
| `053-threadspace-whispermesh-managed-service-boundary.md` | Proposed | 2026-07-29 | 206   | resonant-jones  |

### History

Node-Hosted Room was introduced first (Jul 27). Two days later, ThreadSpace/
WhisperMesh was committed with the same ADR-053 number. On the same day
(Jul 29 21:01), commit `21942de8` **explicitly merged and resolved** an ADR-053
index conflict with the comment: *"Merge remote-tracking branch 'origin/main'
into main — resolve ADR-053 index conflict (keep
node-hosted-room-access-boundary)"*. This is a **deliberate human adjudication
by Resonant Jones** that `053-node-hosted-room-access-boundary.md` is the
canonical ADR-053.

### Governance citations

ADR-057 line 136 explicitly cites "**ADR-053** (Node-Hosted Room Access Boundary)."
5 external numeric references cite Node-Hosted Room (linked to its path or by
title). 0 cite ThreadSpace/WhisperMesh.

### Direct-path reference surface

Node-Hosted Room → 1 (contacts-circles contract). ThreadSpace/WhisperMesh → 0.

### Sibling collision note

ThreadSpace/WhisperMesh content also exists at
`055-threadspace-whispermesh-managed-service-boundary.md` (see ADR-055 review).
The 053 and 055 ThreadSpace/WhisperMesh files are near-duplicates: they differ
only in H1 title number (`ADR-053` vs `ADR-055`) and a minor rewording of one
paragraph about WhisperMesh Spine vs control-plane groundwork.

### Classification

**Explicitly-adjudicated near-duplicate.** Resonant Jones already decided which
file holds ADR-053 in a merge commit. This review preserves that adjudication as
strong historical evidence.

However, the explicit adjudication governs the **number holder**. The ThreadSpace/
WhisperMesh 053 copy is the **same content** as the ADR-055 ThreadSpace/WhisperMesh
file; the 053 copy's existence creates duplicate-authority material within the
`docs/architecture/adr/` namespace. This is a Phase 6 duplicate-authority cleanup
candidate, **distinct** from number-canonicalization. An eventual tombstone at the
053 path is appropriate Phase 6 work but **does not** follow automatically from
the merge adjudication — it requires its own human disposition.

### Recommended existing-number holder (advisory)

`053-node-hosted-room-access-boundary.md` (explicit merge adjudication,
ADR-057-cited, 5 converging numeric references, authored first). The
recommendation does not authorize any implementation.

### Recommended non-holder treatment (advisory)

`053-threadspace-whispermesh-managed-service-boundary.md` is a **Phase 6
duplicate-authority cleanup candidate** because the same content lives at ADR-055
with governance citations and campaign linkage. Phase 6 cleanup (tombstone /
compatibility pointer / retirement) is **not** part of this review's recommended
canonicalization. Any Phase 6 work must be separately approved and must not be
executed casually during Phase 5 rewrites.

### Known repository-local rewrite risk

For ThreadSpace/WhisperMesh 053 copy: no external file references this path by
name; no numeric references point to it; content has a canonical home at ADR-055
per the governance chain. Known repository-local rewrite risk: **low**.
External-reference risk: **unknown / not evaluated**.

## ADR-055 review

### Facts

| File                                                        | Status   | Date                                              | Lines | Author          |
|-------------------------------------------------------------|----------|---------------------------------------------------|-------|-----------------|
| `055-orthogonal-ui-material-personalization.md`              | Accepted | 2026-08-01                                        | 374   | Resonant Jones  |
| `055-threadspace-whispermesh-managed-service-boundary.md`    | Proposed | 2026-07-29 (as 053), 2026-08-02 (as 055)          | 206   | resonant-jones  |

### History

A complex governance-recovery chain:

1. **Aug 1 17:56** (`fc03d9e7`): Orthogonal UI Material introduced as ADR-055
   (Accepted).
2. **Aug 2 11:57** (`50721d0f`): Orthogonal UI Material **deleted** in a prune
   pass ("docs: refresh weekly current-state, prune stale soft-serve/audit
   artifacts").
3. **Aug 2 14:08** (`b271d075`): Orthogonal UI Material **re-added** ("docs:
   restore ADR-055 governance registrations").
4. **Aug 2 18:08** (`7ed53cd7`): ThreadSpace/WhisperMesh file created at
   `055-threadspace-whispermesh-managed-service-boundary.md` ("Define ThreadSpace
   WhisperMesh service boundary"). This commit also **updated the TS-WM-001
   Campaign README** to change all `ADR-053` references to `ADR-055`,
   demonstrating explicit governance intent: ThreadSpace/WhisperMesh was
   deliberately renamed from ADR-053 to ADR-055.

The near-duplicate at `053-threadspace-whispermesh-managed-service-boundary.md`
(see ADR-053 review) was never cleaned up, leaving both 053 and 055 copies of the
same proposed content in the repo.

### Governance citations

ADR-057 line 140 explicitly cites "**ADR-055** (ThreadSpace ↔ WhisperMesh
Managed-Service Boundary)." The TS-WM-001 Campaign README references ADR-055
as its governing decision. `architecture/README.md` line 45 links to Orthogonal UI
Material; line 144 links to ThreadSpace/WhisperMesh.

### Numeric reference ambiguity

6 external `ADR-055` references cite ThreadSpace/WhisperMesh (via the Campaign
README, `architecture/README.md` line 144, and ADR-057). 3 cite Orthogonal UI
Material (`architecture/README.md` line 45,
`codexify-design-architecture-index.md`, `ARTIFACT1—UI-Token-Constitution.md`).
This is the **only collision pair where both files have active numeric-reference
chains.**

### Direct-path reference surface

Orthogonal UI → 2 (README, UI Token constitution). ThreadSpace/WhisperMesh → 2
(README, Campaign README, both via `055-threadspace-whispermesh` path).

### Classification

**Governance-intent collision.** Both files have deliberate governance intent for
ADR-055:

- ThreadSpace/WhisperMesh has ADR-057 citation and explicit commit-chain intent
  (the Aug 2 18:08 renaming commit).
- Orthogonal UI is Accepted and has a README anchor.

The Orthogonal UI file's temporary deletion (Aug 2 11:57) created a window during
which ADR-055 was vacant; the ThreadSpace/WhisperMesh commit at 18:08 filled that
perceived vacancy. The Orthogonal UI was restored at 14:08 (before the TS/WM
commit) but the two commits may not have been visible to each other in separate
worktrees. This is an **accidental concurrent reuse**.

The architectural meaning of Orthogonal UI (additive material axes, Surface
Temperature, Paper Tone, separate persistence responsibilities, accessibility-
bounded personalization) is **not** downgraded by this collision. Its Accepted
posture and architectural scope remain intact.

### Recommended existing-number holder (advisory, strong but pending)

`055-threadspace-whispermesh-managed-service-boundary.md` (explicit renumbering
commit chain from 053→055 in `7ed53cd7`, ADR-057 citation in the "Governing ADRs
and alignment" section, TS-WM-001 Campaign README linkage). The recommendation is
**strong but pending human approval** — it does not authorize any implementation.

### Recommended non-holder treatment (advisory)

`055-orthogonal-ui-material-personalization.md` should be preserved as an
**independent Accepted ADR** and **renumbered after human approval**. Its Accepted
status and architectural meaning (374 lines, governs additive UI material axes)
must not be downgraded. Candidate future number: **not assigned in Phase 4A**.

### Known repository-local rewrite risk

For Orthogonal UI: 3 external numeric `ADR-055` references would need updating
on renumber. The 6 ThreadSpace/WhisperMesh references remain correct since it
keeps 055. The `053-threadspace-whispermesh-managed-service-boundary.md` duplicate
is a separate Phase 6 cleanup candidate (see ADR-053 review). Known repository-
local rewrite risk: **medium**. External-reference risk: **unknown / not
evaluated**.

## Cross-collision findings

### C.1 ADR-057 as scoped post-collision governance oracle

ADR-057 was accepted on 2026-08-07 — after all seven collisions existed. Its
"Governing ADRs and alignment" section (lines 128-141) explicitly names
ADR-005 (Runtime Mode), ADR-053 (Node-Hosted Room), ADR-041 (VaultNode),
ADR-039 (Operator/User), and ADR-055 (ThreadSpace/WhisperMesh). In each of these
five cases, the cited ADR is the **advisory recommended canonical holder** per this
review.

ADR-057 does not cite ADR-016 or ADR-024. Those two pairs are resolved
advisory-wise by Accepted status, numeric-reference convergence, and README anchor
— not by ADR-057.

ADR-057's citation is treated as scoped post-collision governance evidence within
this review. ADR-057 itself is **not** altered by this review.

### C.2 Status classification summary (corrected from the original review)

The original review's status-pair summary was incorrect. Its collision-by-collision
status classifications remain valid, but its cross-collision summary overcounted
Accepted-vs-Proposed pairs.

Recomputed from the seven collision blocks above, the Accepted-vs-Proposed status
pair classifications are:

| Status pair                                            | Count | Prefixes   |
|--------------------------------------------------------|-------|------------|
| Accepted-vs-Proposed (Accepted holder recommendation)  | 4     | 005, 039, 041, 055 |
| Accepted-vs-Accepted                                   | 2     | 016, 024   |
| Proposed-vs-Proposed                                   | 1     | 053        |

Therefore: **4 of 7 collisions are Accepted-vs-Proposed** under the advisory
recommendation. The remaining three are either both-Accepted (016, 024) or both-
Proposed (053).

The original review's summary statement claiming the Accepted-vs-Proposed count
was higher is incorrect. There are 4 status-gated cases (005, 039, 041, 055).
The "governance > status" pattern in 039 and the "explicit adjudication" pattern
in 053 are not pure status-gated cases.

This correction applies to Section B "Pattern" of the original review. The
underlying collision evidence is unchanged.

### C.3 Chronological precedence rarely decides

In 3 of 7 pairs (005, 016, 053), the file that was introduced first
chronologically is NOT the advisory recommended canonical holder. Chronology
alone is not a reliable adjudication signal in a fast-moving repo with concurrent
worktree branches. The stronger signals are acceptance status, governance
citations (ADR-057), and numeric-reference convergence.

### C.4 Proposed files with zero external references

Of the non-canonical candidates: **4 have zero path or numeric references from
outside `docs/architecture/adr/`** in the inspected repository-local scope:

- 005 Imprint UI
- 024 Workspace Obsidian
- 039 Capability Mesh
- 041 Provider Capability

These can be renumbered with **low known repository-local rewrite risk**, pending
human approval. **External-reference risk remains unknown / not evaluated.**

The remaining non-canonical candidates do have known reference surfaces and
require their references to be tracked through any future renumbering.

### C.5 ThreadSpace/WhisperMesh dual-presence

The same proposed decision content exists at both ADR-053 and ADR-055. This is
the only collision where one document body was committed under two different
numbers within a 4-day window. The governance chain (ADR-057 + TS-WM-001
Campaign) unambiguously designates ADR-055 as its canonical home, and the 053
copy is a Phase 6 duplicate-authority cleanup candidate (see ADR-053 review).
A Phase 6 tombstone at the 053 path is appropriate but **not** approved by this
review.

### C.6 Third ADR-041 in proposed/ is material

`docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md`
is a third Proposed ADR-041 outside the Phase 3A collision report's main-
directory scope. It is referenced by `docs/specs/campaign-runner/PI_LOOP_RECEIPT_COMPATIBILITY_AUDIT.md`.
**This makes ADR-041 a three-claimant canonicalization case**, not a two-way
case. Any Phase 4B or later implementation must include the third claimant and
its reference surface.

### C.7 Medium-risk collision count (corrected from the original review)

The original review implied multiple "zero" or "low" risk cases. Recomputed from
the seven detailed blocks:

| Known repository-local rewrite risk | Count | Prefixes   |
|-------------------------------------|-------|------------|
| Low                                | 5     | 005, 024, 039, 041 (Provider Capability only), 053 |
| Medium                             | 2     | 016, 055   |

Note: ADR-041 is counted twice (VaultNode keeps the number; Provider Capability and
Pi Loop Manager are the non-holders). For Provider Capability, known rewrite risk
is low; for Pi Loop Manager, known rewrite risk is low but non-zero because of
its known `PI_LOOP_RECEIPT_COMPATIBILITY_AUDIT.md` reference.

External-reference risk is **unknown / not evaluated** for every collision.

### C.8 ADR-057 explicit-citation count (corrected from the original review)

ADR-057's "Governing ADRs and alignment" section explicitly names five ADRs from
the seven collision prefixes: 005 (Runtime Mode), 039 (Operator/User), 041
(VaultNode), 053 (Node-Hosted Room), 055 (ThreadSpace/WhisperMesh). That is
**5 explicit governance citations** spanning the seven collision prefixes.

ADR-016 and ADR-024 are not cited. They are resolved advisory-wise by other
evidence (Accepted status, ref-convergence, README anchor).

## Repository rewrite ledger (advisory only — execution requires separate approved tasks)

This ledger is **advisory**. Each entry assumes a separately approved
implementation task triggered by an explicit human canonicalization decision for
the relevant collision. **No entry is approved by this review.** Execution
sequencing respects the staged DLG phases:

- **Phase 4** — human canonicalization decisions (this review produces the
  evidence for these decisions; this review executes none of them).
- **Phase 5** — rewrite accepted canonical documents into consistent shape where
  approved.
- **Phase 6** — replace duplicate authority using compatibility pointers,
  retirement, tombstones, superseded-source exclusion, where separately approved.

| Phase | Action                                                                                                    | Affected collision | Notes                                                                                                                                                  |
|-------|-----------------------------------------------------------------------------------------------------------|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| 4     | Human acceptance gate                                                                                     | All seven          | Each collision requires its own explicit human approval. See "Human decisions required" below.                                                         |
| 5     | Number/path canonicalization tasks (separately authorized per collision)                                  | 005, 016, 024, 039, 041 (×2), 055 | Each renumbering is its own bounded task. No mass renumber.                                                                                            |
| 5     | Reference/index rewrites associated with approved renumberings                                             | 005, 016, 024, 039, 041, 055 | Path/number changes must update external references and `adr-index.md` per collision in the same authorized task.                                    |
| 5     | DLG reclassification/revalidation as separately authorized (after canonical source changes)               | All seven          | Future DLG node records for these ADRs must follow approved renumbering. Until then, no DLG node records are created for these ADRs by this review.    |
| 6     | Duplicate-authority replacement only where identity/lineage decisions actually justify pointer/tombstone behavior | 053, 055 (053↔055 dual-presence) | Phase 6 work is **distinct** from Phase 5 renumbering and is **not** approved by this review.                                                           |
| 6     | Regeneration of derived projections after canonical source changes                                         | All seven          | `docs/knowledge-graph/generated/*.json` regenerate after canonical source changes. Not authorized by this review.                                     |

Per-collision future action classification (advisory):

| Collision | Likely future action                                                                                                                   |
|-----------|----------------------------------------------------------------------------------------------------------------------------------------|
| 005       | Simple renumber candidate (Imprint UI)                                                                                                 |
| 016       | Simple renumber candidate (Workspace Retrieval) — track external refs                                                                  |
| 024       | Simple renumber candidate (Workspace Obsidian)                                                                                          |
| 039       | Simple renumber candidate (Capability Mesh)                                                                                             |
| 041       | Two independent renumber candidates + identity-preservation gate (Provider Capability, Pi Loop Manager)                                 |
| 053       | Identity/lineage review (ThreadSpace/WhisperMesh 053 ↔ 055 dual-presence) — Phase 6 candidate                                          |
| 055       | Simple renumber candidate (Orthogonal UI) — track 3 numeric refs; Phase 6 cleanup tied to 053                                          |

No action is approved by this review. No action is executed by this review.

## DLG migration implications

- No collision is resolved by this review.
- Unresolved numbering should be addressed **before** mechanically assigning first
  DLG identities to these ADRs where practical.
- Stable future DLG identity must not be derived solely from the current colliding
  filename. Renumbering a document **before** first DLG classification avoids
  creating avoidable path-alias migration.
- If a DLG identity is already assigned later, path moves must preserve document
  ID rather than creating a replacement identity (per DLG Contract § "Stable
  document identity" and § "Lifecycle transitions").
- `pointer_to` compatibility pointers are appropriate only where **genuine
  locator/identity continuity** exists. Semantically independent decisions must
  not point to one another merely because they once shared a number.
- Phase 5 rewrite and Phase 6 duplicate-authority replacement are **distinct
  staged activities** under the DLG Contract. Phase 6 work must not be casually
  embedded inside Phase 5 rewrites.
- Generated projections (`docs/knowledge-graph/generated/`) are derived and
  non-authoritative. They may be regenerated only after canonical source changes
  are approved and committed.

## Recommended execution order (advisory)

The recommended execution order respects the DLG staged migration phases:

1. **Human approval gates.** Seven explicit human decisions, one per collision.
2. **Separately authorized number/path canonicalization tasks** for each approved
   collision, scoped one-at-a-time.
3. **Reference/index rewrites** associated with each approved renumbering, in the
   same authorized task.
4. **DLG reclassification/revalidation** as separately authorized, after canonical
   source changes land.
5. **Phase 6 duplicate-authority replacement** only where identity/lineage
   decisions actually justify pointer/tombstone behavior (e.g., 053↔055 dual-
   presence). Each Phase 6 action is a separate authorized task.
6. **Regeneration of derived projections** after canonical source changes.

No execution is approved by this review. The order is **advisory** for human
disposition only.

## Human decisions required

Each collision requires one explicit human approval. Approvals are non-transferable
between collisions; one decision does not authorize another. All seven are
**pending**.

### 1. ADR-005

**Recommended existing-number holder (advisory):** `005-runtime-mode-and-account-boundary-invariants.md` (Accepted, ADR-057-cited).

**Proposed treatment of the other claimant:** `005-imprint-ui-deprecation-and-identity-ownership.md` should be preserved as an independent Proposed ADR and **renumbered after human approval**. No compatibility pointer between Imprint UI and Runtime Mode is recommended.

**Unresolved identity/lifecycle question:** Imprint UI is independent of Runtime Mode. They are distinct architectural subjects. Collision evidence alone does not authorize retirement of the Imprint UI proposal.

**Approval question:**

> Approve `005-runtime-mode-and-account-boundary-invariants.md` retaining ADR-005
> as the advisory canonical holder, and authorize a separate canonicalization
> task to renumber `005-imprint-ui-deprecation-and-identity-ownership.md` while
> preserving its independent Proposed identity?

### 2. ADR-016

**Recommended existing-number holder (advisory):** `016-continuity-governance-surface-contract.md` (Accepted, ref-convergence, README anchor).

**Proposed treatment of the other claimant:** `016-workspace-retrieval-source-for-local-knowledge.md` should be preserved as an independent Accepted ADR and **renumbered after human approval**. Accepted status preserved.

**Unresolved identity/lifecycle question:** Continuity Governance and Workspace Retrieval are independent decisions on unrelated architecture scopes. Their acceptance statuses are equal; ref-convergence is the tiebreaker.

**Approval question:**

> Approve `016-continuity-governance-surface-contract.md` retaining ADR-016 as the
> advisory canonical holder, and authorize a separate canonicalization task to
> renumber `016-workspace-retrieval-source-for-local-knowledge.md` while
> preserving its Accepted status?

### 3. ADR-024

**Recommended existing-number holder (advisory):** `024-context-command-active-connector-semantics.md` (Accepted, ref-convergence, README anchor).

**Proposed treatment of the other claimant:** `024-workspace-obsidian-selection-and-injection-contract.md` should be preserved as an independent Accepted ADR and **renumbered after human approval**. Accepted status preserved.

**Unresolved identity/lifecycle question:** Context Command (general connector doctrine) and Workspace Obsidian (specific evidence contract) are related but distinct. Their acceptance statuses are equal; ref-convergence is the tiebreaker.

**Approval question:**

> Approve `024-context-command-active-connector-semantics.md` retaining ADR-024 as
> the advisory canonical holder, and authorize a separate canonicalization task to
> renumber `024-workspace-obsidian-selection-and-injection-contract.md` while
> preserving its Accepted status?

### 4. ADR-039

**Recommended existing-number holder (advisory):** `039-operator-user-access-boundary.md` (Proposed, but ADR-057-cited, chronology-by-renumbering, README anchor, 9 numeric refs).

**Proposed treatment of the other claimant:** `039-capability-oriented-mesh-architecture.md` should be preserved as an independent Accepted ADR and **renumbered after human approval**. Accepted status preserved.

**Unresolved identity/lifecycle question:** Unusual evidence conflict — Capability Mesh is Accepted and substantial; Operator/User is Proposed but has the post-collision governance citation and chronological precedence. The recommendation treats this as advisory and **does not** describe it as mechanically settled.

**Approval question:**

> Approve `039-operator-user-access-boundary.md` retaining ADR-039 as the
> advisory canonical holder despite Capability Mesh's Accepted status, and
> authorize a separate canonicalization task to renumber
> `039-capability-oriented-mesh-architecture.md` while preserving its Accepted
> status?

### 5. ADR-041 (three-claimant)

**Recommended existing-number holder (advisory):** `041-vaultnode-canonical-machine-and-audit-authority.md` (Accepted, ADR-057-cited, README anchor, 10 numeric refs).

**Proposed treatment of the other claimants:**

- `041-provider-capability-model-contract.md` (main directory, Proposed) — preserve independent identity and renumber after human approval.
- `proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` (proposed subdirectory, Proposed) — preserve independent identity and renumber **as a separate canonicalization task** from Provider Capability. The Pi Loop Manager file's known reference (`docs/specs/campaign-runner/PI_LOOP_RECEIPT_COMPATIBILITY_AUDIT.md`) must be tracked independently.

**Unresolved identity/lifecycle question:** Three claimants, not two. VaultNode, Provider Capability, and Pi Loop Manager are distinct architectural subjects (machine/audit authority, provider capability model, Campaign Runner Pi Loop Manager). No `pointer_to`, `supersedes`, or merge relationship is inferred between any two of them.

**Approval question:**

> Approve `041-vaultnode-canonical-machine-and-audit-authority.md` retaining
> ADR-041 as the advisory canonical holder, and authorize two **separate**
> canonicalization tasks — one to renumber `041-provider-capability-model-contract.md`
> (Proposed) preserving its independent identity, and one to renumber
> `proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` (Proposed)
> preserving its independent identity and tracking its reference surface
> independently?

### 6. ADR-053

**Recommended existing-number holder (advisory):** `053-node-hosted-room-access-boundary.md` (explicit merge adjudication `21942de8`, ADR-057-cited, 5 numeric refs).

**Proposed treatment of the other claimant:** `053-threadspace-whispermesh-managed-service-boundary.md` — the explicit merge adjudication is preserved as strong historical evidence for the **number holder**. The 053 copy's existence creates **duplicate-authority material** within the ADR directory because the same content also lives at ADR-055 with governance citations. Phase 6 duplicate-authority cleanup (tombstone / compatibility pointer / retirement) at the 053 path is appropriate but is **distinct** from number-canonicalization and is **not** approved by this review.

**Unresolved identity/lifecycle question:** Distinguish (a) the historical human choice that Node-Hosted Room should retain ADR-053, (b) later Phase 6 cleanup of duplicate ThreadSpace/WhisperMesh material, and (c) any future tombstone/pointer work. The eventual tombstone is not approved merely because the number holder was previously adjudicated.

**Approval question:**

> Approve treating the explicit merge adjudication selecting
> `053-node-hosted-room-access-boundary.md` as the human canonical decision for
> the ADR-053 number, and approve that the duplicate
> `053-threadspace-whispermesh-managed-service-boundary.md` content may proceed
> to a separately governed Phase 6 duplicate-authority cleanup (tombstone /
> compatibility pointer / retirement) only via its own authorized task?

### 7. ADR-055

**Recommended existing-number holder (advisory, strong but pending):** `055-threadspace-whispermesh-managed-service-boundary.md` (explicit renumbering commit chain 053→055 in `7ed53cd7`, ADR-057-cited, TS-WM-001 Campaign README linkage).

**Proposed treatment of the other claimant:** `055-orthogonal-ui-material-personalization.md` should be preserved as an independent Accepted ADR and **renumbered after human approval**. Its Accepted architectural meaning (additive UI material axes, Surface Temperature, Paper Tone, separate persistence responsibilities, accessibility-bounded personalization) must not be downgraded.

**Unresolved identity/lifecycle question:** Both files have deliberate governance intent for ADR-055. The Orthogonal UI file's temporary Aug 2 deletion created a window during which the ThreadSpace/WhisperMesh commit filled the perceived vacancy — accidental concurrent reuse. The 053↔055 dual-presence is a separate Phase 6 concern.

**Approval question:**

> Approve `055-threadspace-whispermesh-managed-service-boundary.md` retaining
> ADR-055 based on the explicit 053→055 governance chain (`7ed53cd7`) and the
> ADR-057 citation, and authorize a separate canonicalization task to renumber
> `055-orthogonal-ui-material-personalization.md` while preserving its Accepted
> architectural meaning?

## Explicit non-actions

This review explicitly does not:

- execute any file rename, rewrite, or tombstone;
- modify `adr-index.md`, `00-current-state.md`, or any ADR body;
- modify ADR-056, ADR-057, the DLG contract, or product lanes and boundaries;
- touch the DLG node corpus (`docs/knowledge-graph/nodes/`), DLG generated outputs
  (`docs/knowledge-graph/generated/`), or any Agent Reading Packet;
- create a DLG node for any ADR;
- create a DLG relation for any ADR;
- accept ADR-056 or ADR-057 changes;
- accept any ADR status change on the human maintainer's behalf;
- resolve the third ADR-041 by treating it as a Phase 3A scope-gap deferral;
- renumber any ADR that is not part of the seven collision pairs;
- widen release claims or change `00-current-state.md`;
- constitute human acceptance — that gate is explicit (see "Human decisions
  required" above);
- select a canonical ADR number for any collision;
- create a compatibility pointer, tombstone, or supersession edge;
- convert reference count into architecture authority;
- convert chronology into architecture authority;
- treat absence of repository-local references as proof that no external
  references exist;
- treat distinct architectural subjects as one identity merely because they
  collided numerically.

## Validation record

This review artifact was produced against the canonical `origin/main` revision
`a2b0a1482775884f6f5574d1cdcf75c5eaf34505` (2026-08-08). All evidence — Git
history, file contents, reference surfaces, validator baselines — was gathered from
that revision in an isolated detached worktree.

- Proposal date: 2026-08-08
- Correction date: 2026-08-08
- Review instrument: Phase 4A collation (DLG Contract § Phase 4)
- Decision authority: Resonant Jones / Chris Castillo — human acceptance required
- Review status at time of writing: Proposed, pending human canonicalization

### Pre-correction validations

- Phase 3A DLG validator (`python3 scripts/knowledge_graph/validate_and_generate_dlg.py validate`) — pass at canonical base.
- Phase 3B ARP validator (`python3 scripts/knowledge_graph/generate_representative_arps.py validate`) — 4/4 at canonical base.
- `make docs PYTHON=python3` — pass at canonical base (existing duplicate Make-target warnings may remain non-failing).
- 14 direct collision ADR files unchanged (byte-identical via git blob + SHA-256 capture).
- Third proposed ADR-041 unchanged (byte-identical via git blob + SHA-256 capture).
- ADR-056, ADR-057, DLG contract, ADR index unchanged.
- 9-node / 8-relation graph invariant preserved; relation predicate counts (`depends_on: 2`, `governed_by: 2`, `evidence_for: 4`) unchanged.
- Phase 3 generated projections unchanged.
- No protected architecture surface modified.

### Post-correction validations

- The corrected artifact exists at `docs/architecture/proofs/2026-08-08-dlg-phase4a-adr-number-collision-canonicalization-review.md`.
- The original path `docs/architecture/adr/proposed/phase4a-adr-number-collision-canonicalization-review.md` no longer exists.
- `git status` in the isolated worktree shows only the rename + bounded corrections.
- All seven human decisions remain **pending**.
- Zero replacement ADR numbers are assigned in Phase 4A.
- Zero compatibility pointers, tombstones, or supersession edges are created.
- Zero canonicalization actions are executed.

## Phase 4A conclusion

Phase 4A evidence collection is complete after correction. The seven direct
collision cases have decision-grade recommendations, but **canonicalization
remains pending seven explicit human decisions**. ADR-041 additionally requires
its discovered third claimant to be included in any implementation task.

No collision is canonicalized by this review. No ADR is renumbered, renamed,
superseded, retired, or tombstoned by this review. No ADR status is changed by
this review. No DLG node or relation is created or modified by this review. No
generated projection is regenerated by this review. No release claim is widened
by this review. No compatibility pointer or tombstone is created by this review.

Phase 4 is **not** complete; this review is evidence for Phase 4 human decisions,
not the decisions themselves. Phase 5 may not begin globally. Phase 6 work is
explicitly distinct from Phase 5 work and may not be casually embedded in Phase 5
rewrites.

**Canonical base:** `a2b0a1482775884f6f5574d1cdcf75c5eaf34505` (Phase 4A
evidence commit, 2026-08-08).

**Original review path:** `docs/architecture/adr/proposed/phase4a-adr-number-collision-canonicalization-review.md` (removed by this correction).

**Corrected path:** `docs/architecture/proofs/2026-08-08-dlg-phase4a-adr-number-collision-canonicalization-review.md` (proof/governance namespace, not the proposed-ADR namespace).

**Git operation:** recognized as a rename by Git at the canonical base.

## Appendix A — Protected surfaces untouched

| Surface                                                          | Confirmed untouched |
|------------------------------------------------------------------|---------------------|
| `docs/architecture/adr/adr-index.md`                             | ✓                   |
| `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md` | ✓                |
| `docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md` | ✓            |
| `docs/architecture/document-lifecycle-graph-contract.md`         | ✓                   |
| `docs/architecture/product-lanes-and-boundaries.md`              | ✓                   |
| `docs/architecture/00-current-state.md`                          | ✓                   |
| 14 main-directory collision ADR files (7 prefixes × 2 files)      | ✓                   |
| Third proposed ADR-041 at `docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` | ✓ |
| `docs/knowledge-graph/nodes/*.json` (9 files)                    | ✓                   |
| `docs/knowledge-graph/generated/*.json` (6 files + 4 ARPs)       | ✓                   |
| `scripts/knowledge_graph/validate_and_generate_dlg.py`           | ✓                   |
| `scripts/knowledge_graph/generate_representative_arps.py`        | ✓                   |

## Appendix B — Per-collision at-a-glance (advisory)

| Number | Recommended existing-number holder                  | Recommended non-holder treatment                                | Status pair | Known repo-local rewrite risk | External-reference risk | Human approval state |
|--------|----------------------------------------------------|-----------------------------------------------------------------|-------------|--------------------------------|-------------------------|---------------------|
| 005    | Runtime Mode (Accepted, ADR-057-cited)             | Imprint UI: independent Proposed ADR; renumber                   | Accepted-vs-Proposed | Low (Imprint UI)          | Unknown / not evaluated | pending             |
| 016    | Continuity Governance (Accepted, ref-convergence)  | Workspace Retrieval: renumber; preserve Accepted                | Accepted-vs-Accepted | Medium                       | Unknown / not evaluated | pending             |
| 024    | Context Command (Accepted, ref-convergence)        | Workspace Obsidian: renumber; preserve Accepted                 | Accepted-vs-Accepted | Low                          | Unknown / not evaluated | pending             |
| 039    | Operator/User (Proposed, ADR-057-cited, chronology) | Capability Mesh: renumber; preserve Accepted                    | Accepted-vs-Proposed | Low (Capability Mesh)      | Unknown / not evaluated | pending             |
| 041    | VaultNode (Accepted, ADR-057-cited)                | Provider Capability: renumber (Proposed); Pi Loop Manager: renumber separately (Proposed) | Accepted-vs-Proposed (×3 claimants) | Low (Provider Capability, Pi Loop Manager) | Unknown / not evaluated | pending             |
| 053    | Node-Hosted Room (merge adjudication, ADR-057-cited) | ThreadSpace/WhisperMesh 053: Phase 6 cleanup candidate; preserve governance chain to 055 | Proposed-vs-Proposed | Low                          | Unknown / not evaluated | pending             |
| 055    | ThreadSpace/WhisperMesh (ADR-057-cited, commit-chain) | Orthogonal UI: renumber; preserve Accepted architectural meaning | Accepted-vs-Proposed | Medium                       | Unknown / not evaluated | pending             |

## Appendix C — Phase 4A correction receipt (after this correction)

- Accepted-vs-Proposed pair count under advisory recommendation: **4 of 7** (005, 039, 041, 055).
- Accepted-vs-Accepted pair count: **2 of 7** (016, 024).
- Proposed-vs-Proposed pair count: **1 of 7** (053).
- ADR-041 claimant count: **3** (Provider Capability, VaultNode, Pi Loop Manager).
- Explicit human decisions: **7** (one per collision).
- Concrete future ADR numbers assigned by this review: **0**.
- Compatibility pointers created: **0**.
- Tombstones created: **0**.
- Supersession edges created: **0**.
- Canonicalization actions executed: **0**.
- ADR renumberings executed: **0**.
- ADR status changes: **0**.
- DLG node changes: **0**.
- DLG relation changes: **0**.
- Generated projection changes: **0**.

## Appendix D — Artifact classification

- This artifact is a **proof/governance review** under
  `docs/architecture/proofs/`, not a **proposed ADR** under
  `docs/architecture/adr/proposed/`. The original `adr/proposed/` location was
  incorrect for this artifact type and is corrected by this relocation.
- This artifact does **not** carry `accepted_adr` authority class. It is
  `proof` (or `evidence_only`) by its nature — a decision-grade review with
  recommendations pending human disposition.
- Future DLG node records for collision ADRs (if any) should follow the canonical
  renumbering rather than the colliding filenames. Stable document IDs survive
  path moves per the DLG Contract.
