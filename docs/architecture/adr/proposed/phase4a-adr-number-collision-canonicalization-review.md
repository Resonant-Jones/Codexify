# Phase 4A: ADR Number Collision Canonicalization Review

## Status

Proposed — pending human canonicalization decision.

## Date

2026-08-08

## Review authority

Phase 4A of the DLG staged migration (ADR-056 § Rollout posture § Phase 4: human canonicalization; DLG Contract § Phase 4). This artifact records a decision-grade review of the seven ADR-number collisions detected by Phase 3A. It recommends a canonical holder for each collision and an ordered rewrite ledger; it does not execute the rewrites, touch protected surfaces (adr-index.md, ADR-056, ADR-057, the DLG contract, DLG generated outputs, or current-state docs), or create new DLG nodes.

**Human approval required:** each collision decision must be accepted by the repository's human owner (Resonant Jones / Chris Castillo) before any Phase 5 rewrite executes.

## Evidence posture and methodology

This review is grounded in the following evidence classes, applied per-collision:

| Evidence class | What it examines |
|---|---|
| **Status classification** | Accepted vs Proposed; a Proposed ADR that shares a number with an Accepted ADR is a de facto number-conflict resolution signal. |
| **Git history** | Introduction date, chronological precedence, renumbering chains, merge adjudications, deletion/restore patterns. |
| **Explicit governance citations** | ADR-057 (accepted 2026-08-07) explicitly names a subset of the 14 ADRs by title, establishing post-collision governance preference. `architecture/README.md` and the ADR index also provide annotated canonical pointers. |
| **Direct-path reference surface** | Non-collision files that link to a specific collision ADR path (outside `docs/architecture/adr/`). A file with zero external path references has zero downstream breakage risk if renumbered or tombstoned. |
| **Numeric-token reference surface** | Non-collision files that refer to `ADR-NNN` without a disambiguating title. These are ambiguous and introduce downstream reachability risk when a number is reassigned. |
| **Semantic relationship classification** | Whether the two collision files are independent decisions on unrelated architecture scopes, related/complementary decisions, or true duplicate decisions where two files address the same topic. |

**Source corpus:** 14 ADR files + adr-index.md + ADR-057 + architecture/README.md + all other tracked `docs/**` files. Baseline validators (Phase 3A `validate_and_generate_dlg.py`, Phase 3B ARP validator, `make docs`) pass at the canonical repository revision `9c8becac8` (origin/main at time of review).

---

## Section A — Per-collision decision blocks

### Collision 1: ADR-005

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `005-imprint-ui-deprecation-and-identity-ownership.md` | **Proposed** | 2026-04-15 | 172 | resonant-jones |
| `005-runtime-mode-and-account-boundary-invariants.md` | **Accepted** | 2026-04-19 | 135 | resonant-jones |

**History:** Imprint UI was introduced first but never moved past Proposed. The file itself has a self-documenting closing note (line 172): *"If this decision has already been formally ratified in-repo, change Status from `Proposed` to `Accepted`."* Runtime Mode was introduced 4 days later and Accepted.

**Governance citations:** ADR-057 line 133 explicitly cites "**ADR-005** (Runtime Mode and Account Boundary Invariants)." The ADR index lists both files under the same reading-order index entry, noting Imprint UI is "retained as the legacy identity-ownership UI boundary note" (line 42). All 17 external numeric `ADR-005` references unambiguously point to Runtime Mode (they cite "runtime mode," "account boundary invariants," or link to the runtime-mode file path). Zero external references point to Imprint UI path or title by name.

**Direct-path reference surface:** Runtime Mode → 3 direct references. Imprint UI → 0.

**Classification:** **Status-gated conflict.** An Accepted decision and a Proposed proposal sharing one number. The Proposed file was authored before the Accepted one, but never transitioned to Accepted.

**Recommended canonical holder:** `005-runtime-mode-and-account-boundary-invariants.md` (Accepted, governance-cited, all numeric references converge).

**Recommended non-canonical treatment:** `005-imprint-ui-deprecation-and-identity-ownership.md` → compatibility pointer (tombstone as `005-imprint-ui-deprecation-and-identity-ownership.md` with a brief redirect-to-ADR-005 header). Alternative: renumber to an unoccupied number with Proposed→Proposed migration preserved.

**Downstream breakage risk:** Zero — no external file path-references or numeric-references point to this file. Only `adr-index.md` needs its link updated.

---

### Collision 2: ADR-016

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `016-continuity-governance-surface-contract.md` | **Accepted** | 2026-04-28 | 264 | resonant-jones |
| `016-workspace-retrieval-source-for-local-knowledge.md` | **Accepted** | 2026-04-27 | 56 | resonant-jones |

**History:** Workspace Retrieval was introduced first (Apr 27) but received the same number as Continuity Governance (Apr 28). Both are Accepted.

**Governance citations:** ADR-057 does not explicitly cite ADR-016. The ADR index lists both files under the same reading-order entry (line 53). `architecture/README.md` line 95 points to Continuity Governance.

**Semantic relationship:** **Independent decisions.** Continuity Governance defines a user-governed control plane for continuity scope, intensity, decay, import treatment, exclusions, inspection, and reset. Workspace Retrieval defines `retrievalSource="workspace"` as a live backend source mode for chat completions. They address different architecture layers (continuity governance vs retrieval source semantics), do not reference each other, and have no content overlap. This is a **pure numbering collision between two independent accepted decisions.**

**Numeric reference ambiguity:** 14 numeric `ADR-016` references cite "continuity governance" (A); 7 cite "Workspace Retrieval Source" (B). Both have meaningful downstream citation chains. In particular, `023-workspace-e2e-proof-harness-contract.md` and `024-workspace-obsidian-selection-and-injection-contract.md` both link to the Workspace Retrieval path as a governing dependency.

**Direct-path reference surface:** Continuity Governance → 2 direct refs. Workspace Retrieval → 0.

**Classification:** **Independent-accepted collision.** Two unrelated Accepted decisions on the same number.

**Recommended canonical holder:** `016-continuity-governance-surface-contract.md` (higher numeric-token reference convergence (14 vs 7), explicit README anchor, larger content scope with continuity *governance* semantics that apply across the system).

**Recommended non-canonical treatment:** `016-workspace-retrieval-source-for-local-knowledge.md` → rename to `017-workspace-retrieval-source-for-local-knowledge.md` (number 017 is occupied by `017-graph-write-idempotency-and-receipt-semantics.md`). Alternative: renumber to the first available unoccupied number above 055 or to a gap-number. The 7 external path-references must be updated. `023-workspace-e2e-proof-harness-contract.md` and `024-workspace-obsidian-selection-and-injection-contract.md` are the two primary files needing path updates.

**Downstream breakage risk:** Medium — 7 numeric references and 2 path-based references must be updated. All 7 numeric references include a disambiguating title, so they survive renumbering with contextual intent intact; the path-based references will require target-path updates.

---

### Collision 3: ADR-024

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `024-context-command-active-connector-semantics.md` | **Accepted** | 2026-05-07 | 189 | Chris Castillo |
| `024-workspace-obsidian-selection-and-injection-contract.md` | **Accepted** | 2026-05-06 | 67 | Chris Castillo |

**History:** Both authored by Chris Castillo within ~1.5 hours on May 6-7, 2026. Both Accepted. Both reference the same Obsidian workspace surface but from different architectural angles.

**Governance citations:** ADR-057 does not explicitly cite ADR-024. The ADR index lists both files (lines 63-64). `architecture/README.md` line 81 points to Context Command.

**Semantic relationship:** **Related but distinct.** Context Command governs the *general* connector invocation doctrine — how Obsidian, GitHub, Discord, Drive, and MCP-backed connectors are invoked through slash commands, attached, and consulted. Workspace Obsidian governs the *specific* evidence-truthfulness contract for Obsidian-backed notes in the workspace retrieval pipeline — whether a note was selected, injected, and reflected in the completion context. Context Command is a broad doctrine; Workspace Obsidian is a narrow evidence contract. Workspace Obsidian references ADR-016 and ADR-023 as governing docs but does NOT reference Context Command. Context Command mentions Obsidian as an example connector type.

**Numeric reference ambiguity:** All 5 external `ADR-024` numeric references unambiguously cite Context Command.

**Direct-path reference surface:** Context Command → 5 direct refs. Workspace Obsidian → 0.

**Classification:** **Strongly-asymmetric accepted collision.** One file holds general connector doctrine with 5 converging numeric references; the other is a narrow evidence-truth contract with zero external references. The asymmetry makes the canonical holder unambiguous.

**Recommended canonical holder:** `024-context-command-active-connector-semantics.md` (general doctrine, 5 converging citations, README anchor).

**Recommended non-canonical treatment:** `024-workspace-obsidian-selection-and-injection-contract.md` → renumber to the first unoccupied number, preserving its path to `016-workspace-retrieval-source-for-local-knowledge.md` and `023-workspace-e2e-proof-harness-contract.md` links (which reference this file's path internally in the text). Update those two files' self-references.

**Downstream breakage risk:** Low — only one file (`024-workspace-obsidian-selection-and-injection-contract.md` line 58) references an ADR path that goes through this collision membership. Zero external files reference this path by name.

---

### Collision 4: ADR-039

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `039-capability-oriented-mesh-architecture.md` | **Accepted (Architectural Principle)** | 2026-06-30 | 483 | Resonant Jones |
| `039-operator-user-access-boundary.md` | **Proposed** | 2026-06-30 | 148 | Resonant Jones |

**History:** Operator/User was originally introduced as `038-operator-user-access-boundary.md` on Jun 30 16:30 by Resonant Jones, then renumbered from 038→039 at 18:27 (`9f985d05` "Renumber operator user boundary ADR"), the old 038 file was deleted at 18:29 (`4163ddb4` "Remove superseded operator boundary ADR number"), and a tombstone was placed at 038 at 18:51 (`c8189ac4` "Mark superseded operator ADR duplicate") pointing readers to ADR-039. The mesh ADR was introduced at 19:02 (`de9e08ad` "docs: add capability-oriented mesh ADR") — **after** Operator/User had taken 039 by explicit renumbering. This is a chronological-precedence collision where both authors acted independently within a 2-hour window.

**Governance citations:** ADR-057 line 139 explicitly cites "**ADR-039** (Operator/User Access Boundary)." `architecture/README.md` line 55 points to Operator/User. 9 external numeric references cite Operator/User (by title or linked path); 0 cite Capability-Oriented Mesh.

**Direct-path reference surface:** Operator/User → 3 direct refs. Mesh → 0.

**Classification:** **Status-gated + governance-anchored collision.** Mesh is Accepted (Architectural Principle); Operator/User is Proposed but arrived at the number first through renumbering and is cited by ADR-057. This is the only collision pair where the **Proposed** file has the governance anchor and chronological precedence while the **Accepted** file arrived later. Both address different architecture scopes (networking/capability authorization vs operator/user role topology).

**Recommended canonical holder:** `039-operator-user-access-boundary.md` (governance-cited by ADR-057, README anchor, clear chronological precedence through renumbering, 9 converging numeric references, existing 038 tombstone precedent from Resonant Jones).

**Recommended non-canonical treatment:** `039-capability-oriented-mesh-architecture.md` → renumber to an unoccupied number. Its content is Accepted and substantial (483 lines, governs networking mesh/capability authorization). It has zero external references, so renumbering has zero downstream breakage. The renumbering decision should be recorded in a tombstone at the old path.

**Downstream breakage risk:** Zero for mesh (no external refs). Zero for operator/user (it keeps the number).

---

### Collision 5: ADR-041

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `041-provider-capability-model-contract.md` | **Proposed** | 2026-06-30 | 195 | Resonant Jones |
| `041-vaultnode-canonical-machine-and-audit-authority.md` | **Accepted** | 2026-07-10 | 299 | Resonant Jones |

**Additional:** `docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` exists at path `docs/architecture/adr/proposed/` (Proposed, dated 2026-07-03). This is a **third ADR-041** in the proposed subdirectory, outside the Phase 3A collision scope. It is referenced by two contract files in `docs/specs/campaign-runner/`. Its existence is noted here as a Phase 4+ follow-up observation; it does not affect the two-way collision decision.

**History:** Provider Capability arrived first (Jun 30) as Proposed. PiLoop Manager (proposed subdirectory, Jul 3) arrived second, also Proposed. VaultNode arrived third (Jul 10) as Accepted. Chronologically, Provider Capability had first claim on the number but never transitioned to Accepted.

**Governance citations:** ADR-057 line 138 explicitly cites "**ADR-041** (VaultNode Canonical Machine and Audit Authority)." `architecture/README.md` line 61 points to VaultNode. 10 external numeric references cite VaultNode (by title, linked path, or "trusted latest" / "audit authority" context). 0 cite Provider Capability.

**Direct-path reference surface:** VaultNode → 2 direct refs (audit artifacts). Provider Capability → 0.

**Classification:** **Status-gated collision + third-party PiLoop in proposed/.** Strongly asymmetric — VaultNode is Accepted and governance-cited; Provider Capability is Proposed with zero external references.

**Recommended canonical holder:** `041-vaultnode-canonical-machine-and-audit-authority.md` (Accepted, ADR-057-cited, README anchor, 10 converging numeric references).

**Recommended non-canonical treatment:** `041-provider-capability-model-contract.md` → renumber to unoccupied number (Proposed status preserved). Zero downstream references to update.

**Phase 4+ observation:** The third ADR-041 (`proposed/041-pi-loop-manager-campaign-runner-gate-graph.md`) should be moved from the `proposed/` subdirectory and renumbered alongside the others during Phase 4B or noted as a separate canonicalization decision.

**Downstream breakage risk:** Zero for Provider Capability. Zero for VaultNode (stays at 041).

---

### Collision 6: ADR-053

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `053-node-hosted-room-access-boundary.md` | **Proposed** | 2026-07-27 | 419 | Resonant Jones |
| `053-threadspace-whispermesh-managed-service-boundary.md` | **Proposed** | 2026-07-29 | 206 | resonant-jones |

**History:** Node-Hosted Room was introduced first (Jul 27). Two days later, ThreadSpace/WhisperMesh was committed with the same ADR-053 number. On the same day (Jul 29 21:01), commit `21942de8` **explicitly merged and resolved** an ADR-053 index conflict with the comment: *"Merge remote-tracking branch 'origin/main' into main — resolve ADR-053 index conflict (keep node-hosted-room-access-boundary)"*. This is a **deliberate human adjudication by Resonant Jones** that `053-node-hosted-room-access-boundary.md` is the canonical ADR-053.

**Governance citations:** ADR-057 line 136 explicitly cites "**ADR-053** (Node-Hosted Room Access Boundary)." 5 external numeric references cite Node-Hosted Room (linked to its path or by title). 0 cite ThreadSpace/WhisperMesh.

**Direct-path reference surface:** Node-Hosted Room → 1 (contacts-circles contract). ThreadSpace/WhisperMesh → 0.

**Sibling collision note:** ThreadSpace/WhisperMesh content also exists at `055-threadspace-whispermesh-managed-service-boundary.md` (see Collision 7). The 053 and 055 ThreadSpace/WhisperMesh files are near-duplicates: they differ only in H1 title number (`ADR-053` vs `ADR-055`) and a minor rewording of one paragraph about WhisperMesh Spine vs control-plane groundwork.

**Classification:** **Explicitly-adjudicated duplicate-decision collision.** Resonant Jones already decided which file holds ADR-053 in a merge commit. This review confirms that decision.

**Recommended canonical holder:** `053-node-hosted-room-access-boundary.md` (explicit merge adjudication, ADR-057-cited, 5 converging numeric references, authored first).

**Recommended non-canonical treatment:** `053-threadspace-whispermesh-managed-service-boundary.md` → tombstone as designed below in the rewrite ledger (the same content is preserved at ADR-055, where it has governance citations and campaign linkage).

**Downstream breakage risk:** Zero — no external file references this path by name, no numeric references point to it, and the ThreadSpace/WhisperMesh content has a canonical home at ADR-055 per the governance chain.

---

### Collision 7: ADR-055

**Facts**

| File | Status | Date | Lines | Author |
|---|---|---|---|---|
| `055-orthogonal-ui-material-personalization.md` | **Accepted** | 2026-08-01 | 374 | Resonant Jones |
| `055-threadspace-whispermesh-managed-service-boundary.md` | **Proposed** | 2026-07-29 (as 053), 2026-08-02 (as 055) | 206 | resonant-jones |

**History:** A complex governance-recovery chain:

1. **Aug 1 17:56** (`fc03d9e7`): Orthogonal UI Material introduced as ADR-055 (Accepted).
2. **Aug 2 11:57** (`50721d0f`): Orthogonal UI Material **deleted** in a prune pass ("docs: refresh weekly current-state, prune stale soft-serve/audit artifacts").
3. **Aug 2 14:08** (`b271d075`): Orthogonal UI Material **re-added** ("docs: restore ADR-055 governance registrations").
4. **Aug 2 18:08** (`7ed53cd7`): ThreadSpace/WhisperMesh file created at `055-threadspace-whispermesh-managed-service-boundary.md` ("Define ThreadSpace WhisperMesh service boundary"). This commit also **updated the TS-WM-001 Campaign README** to change all `ADR-053` references to `ADR-055`, demonstrating explicit governance intent: ThreadSpace/WhisperMesh was deliberately renamed from ADR-053 to ADR-055.

The near-duplicate at `053-threadspace-whispermesh-managed-service-boundary.md` (Collision 6) was never cleaned up, leaving both 053 and 055 copies of the same proposed content in the repo.

**Governance citations:** ADR-057 line 140 explicitly cites "**ADR-055** (ThreadSpace ↔ WhisperMesh Managed-Service Boundary)." The TS-WM-001 Campaign README references ADR-055 as its governing decision. `architecture/README.md` line 45 links to Orthogonal UI Material; line 144 links to ThreadSpace/WhisperMesh.

**Numeric reference ambiguity:** 6 external `ADR-055` references cite ThreadSpace/WhisperMesh (via the Campaign README, `architecture/README.md` line 144, and ADR-057). 3 cite Orthogonal UI Material (`architecture/README.md` line 45, `codexify-design-architecture-index.md`, `ARTIFACT1—UI-Token-Constitution.md`). This is the **only collision pair where both files have active numeric-reference chains.**

**Direct-path reference surface:** Orthogonal UI → 2 (README, UI Token constitution). ThreadSpace/WhisperMesh → 2 (README, Campaign README, both via `055-threadspace-whispermesh` path).

**Classification:** **Governance-intent collision.** Both files have deliberate governance intent for ADR-055:
- ThreadSpace/WhisperMesh has ADR-057 citation and explicit commit-chain intent (the Aug 2 18:08 renaming commit).
- Orthogonal UI is Accepted and has a README anchor.

The Orthogonal UI file's temporary deletion (Aug 2 11:57) created a window during which ADR-055 was vacant; the ThreadSpace/WhisperMesh commit at 18:08 filled that perceived vacancy. The Orthogonal UI was restored at 14:08 (before the TS/WM commit) but the two commits may not have been visible to each other in separate worktrees. This is an **accidental concurrent reuse.**

**Recommended canonical holder based on governance evidence:** `055-threadspace-whispermesh-managed-service-boundary.md` (explicit renumbering commit chain from 053→055 in `7ed53cd7`, ADR-057 citation in the "Governing ADRs and alignment" section, TS-WM-001 Campaign README linkage).

**Recommended non-canonical treatment:** `055-orthogonal-ui-material-personalization.md` → renumber to unoccupied number. The Orthogonal UI decision is Accepted and substantial (374 lines) with 3 external references that must be updated.

**Downstream breakage risk:** Medium — 3 external numeric `ADR-055` references need updating for Orthogonal UI's new number. The 6 ThreadSpace/WhisperMesh references remain correct since it keeps 055. The `053-threadspace-whispermesh-managed-service-boundary.md` duplicate is tombstoned by Collision 6's recommendation.

---

## Section B — Collision type summary

| Pair | Type | Deciding factor |
|---|---|---|
| 005 | Status-gated | Accepted (Runtime Mode) vs Proposed (Imprint UI). ADR-057 citation settles. |
| 016 | Independent-accepted | Two unrelated Accepted decisions. Higher numeric-reference convergence + README anchor decide. |
| 024 | Strongly-asymmetric accepted | Both Accepted, but one file has 5 converging references and the other has 0. Scope asymmetry (general doctrine vs narrow evidence contract). |
| 039 | Status-gated + governance-anchored | Proposed file has governance citation and chronological precedence through explicit renumbering over later-arriving Accepted file. |
| 041 | Status-gated | Accepted (VaultNode) vs Proposed (Provider Capability). ADR-057 citation settles. |
| 053 | Explicitly-adjudicated | Resonant Jones resolved the merge conflict at 21:01 on Jul 29, choosing Node-Hosted Room. ADR-057 and numeric references confirm. |
| 055 | Governance-intent | ADR-057 citation + explicit commit-chain renumbering (053→055 in `7ed53cd7`) establish ThreadSpace/WhisperMesh as the intended holder. Orthogonal UI's concurrent presence was an accidental re-collision. |

**Pattern:** 5 of 7 collisions involve Accepted-vs-Proposed pairs where the Accepted file should retain the number. The two exceptions are 016 (both Accepted, independent) and 055 (governance-intent overrides pure status). In all 5 status-gated cases, ADR-057 (accepted 2026-08-07) provides an explicit, post-collision governance citation naming the preferred holder.

---

## Section C — Cross-collision patterns

### C.1 ADR-057 as governance oracle

ADR-057 was accepted on 2026-08-07 — after all seven collisions existed. Its "Governing ADRs and alignment" section (lines 128-141) explicitly names ADR-005 (Runtime Mode), ADR-053 (Node-Hosted Room), ADR-041 (VaultNode), ADR-039 (Operator/User), and ADR-055 (ThreadSpace/WhisperMesh). In each case, the cited ADR is the **recommended canonical holder** per this review. ADR-057 does not cite 016 or 024, leaving those two pairs to be resolved by numeric-reference convergence.

### C.2 Chronological precedence rarely decides

In 3 of 7 pairs (005, 016, 053), the file that was introduced first chronologically is NOT the recommended canonical holder. Chronology alone is not a reliable adjudication signal in a fast-moving repo with concurrent worktree branches. The stronger signals are Acceptance status, governance citations (ADR-057), and numeric-reference convergence.

### C.3 Proposed files with zero external references

Of the 7 non-canonical candidates: 4 have **zero** path or numeric references from outside `docs/architecture/adr/` (005-Imprint, 024-Workspace Obsidian, 039-Capability Mesh, 041-Provider Capability). These can be renumbered with zero downstream breakage. Only 016-Workspace Retrieval and 055-Orthogonal UI have active reference chains needing update.

### C.4 ThreadSpace/WhisperMesh dual-presence

The same proposed decision content exists at both ADR-053 and ADR-055. This is the only collision where one document body was committed under two different numbers within a 4-day window. The governance chain (ADR-057 + TS-WM-001 Campaign) unambiguously designates ADR-055 as its canonical home, and the 053 copy should be tombstoned redirecting to 055.

### C.5 Third ADR-041 in proposed/ scope gap

`docs/architecture/adr/proposed/041-pi-loop-manager-campaign-runner-gate-graph.md` is a third Proposed ADR-041 outside the Phase 3A collision scope (the collision report scans the main ADR directory only). It is referenced by `docs/specs/campaign-runner/` contract files. It should be renumbered in Phase 4B as a follow-up, or its collision acknowledged as a Phase 3A scope-gap finding.

---

## Section D — Rewrite ledger (execution order)

This section is advisory only. Execution requires a separate Phase 5 task after the human owner accepts the canonicalization decisions above. Filenames use placeholder "NNN" for new numbers to be chosen during Phase 5.

| Step | File | Action | Affected cross-references |
|---|---|---|---|
| 0 | No file changes yet | **Human acceptance gate.** All 7 decisions must be approved before any rewrite executes. | — |
| 1 | `053-threadspace-whispermesh-managed-service-boundary.md` | **Tombstone.** Replace content with a redirect notice pointing to `055-threadspace-whispermesh-managed-service-boundary.md`. | None (zero external refs) |
| 2 | `005-imprint-ui-deprecation-and-identity-ownership.md` | **Tombstone.** Replace content with redirect to `005-runtime-mode-and-account-boundary-invariants.md` and note this was a Proposed ADR that never achieved Acceptance. | Update adr-index.md: remove ADR-005 entry for Imprint UI, retain "(superseded tombstone)" inline note. |
| 3 | `041-provider-capability-model-contract.md` | **Renumber to NNN.** | None (zero external refs). Update adr-index.md path. |
| 4 | `039-capability-oriented-mesh-architecture.md` | **Renumber to NNN + tombstone at old path.** | None (zero external refs). Update adr-index.md path. |
| 5 | `024-workspace-obsidian-selection-and-injection-contract.md` | **Renumber to NNN.** | Update 2 internal references in its own body (lines 10, 58) to `016-workspace-retrieval-source-for-local-knowledge.md` and `023-workspace-e2e-proof-harness-contract.md`. |
| 6 | `016-workspace-retrieval-source-for-local-knowledge.md` | **Renumber to NNN.** | Update `023-workspace-e2e-proof-harness-contract.md` (4 references), `024-workspace-obsidian-selection-and-injection-contract.md` (2 references), `030-continuity-protocol-suite-runtime-gate.md` (1 indirect reference). Update adr-index.md. |
| 7 | `055-orthogonal-ui-material-personalization.md` | **Renumber to NNN.** | Update `docs/architecture/README.md` line 45 ("ADR-055: Orthogonal UI → ADR-NNN"), `docs/architecture/design/codexify-design-architecture-index.md` line 174, `docs/dev/ARTIFACT1—UI-Token-Constitution.md` line 271. |
| 8 | `docs/architecture/adr/adr-index.md` | **Consolidate.** Remove tombstoned entries (005-Imprint, 053-TS/WM). Renumber entries for 016-Workspace, 024-Workspace Obsidian, 039-Mesh, 041-ProviderCap, 055-OrthogonalUI. Reorder reading order to match new numbers. | — |
| 9 | All 14 ADR files + cross-referenced files | **Run Phase 3A and Phase 3B validators.** Confirm 0 errors, 0 new collisions. | — |
| 10 | `docs/knowledge-graph/generated/` | **Regenerate** all derived projections (collisions.json, document-graph.json, orphans.json, stale-documents.json, supersession-map.json). | — |

---

## Section E — Reference-surface assessment (per-file summary)

| File | Direct path refs | Numeric refs (A) | Numeric refs (B) | Ambiguous numeric refs |
|---|---|---|---|---|
| 005-A Imprint UI | 0 | — | — | 0 |
| 005-B Runtime Mode | 3 | — | — | 0 |
| 016-A Continuity Governance | 2 | 14 | — | 0 |
| 016-B Workspace Retrieval | 0 | — | 7 | 0 |
| 024-A Context Command | 5 | 5 | — | 0 |
| 024-B Workspace Obsidian | 0 | — | 0 | 0 |
| 039-A Capability Mesh | 0 | — | 0 | 0 |
| 039-B Operator/User | 3 | — | 9 | 5 |
| 041-A Provider Capability | 0 | — | 0 | 0 |
| 041-B VaultNode | 2 | — | 10 | 0 |
| 053-A Node-Hosted Room | 1 | 5 | — | 0 |
| 053-B ThreadSpace/WhisperMesh | 0 | — | 0 | 0 |
| 055-A Orthogonal UI | 2 | 3 | — | 0 |
| 055-B ThreadSpace/WhisperMesh | 2 | — | 6 | 0 |

*Ambiguous numeric refs (039):* Five references say "ADR-039" without a disambiguating title. All five appear in proof or harness documents where surrounding context consistently discusses operator/user topology, browser-host authority, or private-preview lanes — placing them in Operator/User's semantic domain despite lacking an explicit title.

---

## Section F — Non-goals (what this review does NOT do)

- Does not execute any file rename, rewrite, or tombstone.
- Does not modify `adr-index.md`, `00-current-state.md`, or any ADR file.
- Does not touch the DLG node corpus (`docs/knowledge-graph/nodes/`), DLG generated outputs (`docs/knowledge-graph/generated/`), or the DLG contract.
- Does not accept ADR-056 or ADR-057 changes.
- Does not create a DLG node for any ADR.
- Does not resolve the third ADR-041 in `proposed/` (noted for Phase 4B).
- Does not renumber any ADR that is not part of the seven collision pairs.
- Does not widen release claims or change `00-current-state.md`.
- Does not constitute human acceptance — that gate is explicit (see Section D, Step 0).

---

## Section G — Acceptance record

This review artifact was produced against the isolated detached worktree at canonical `origin/main` revision `9c8becac867e5b7524d0a56c9fe77fd01920cf7e` (2026-08-08). All evidence — Git history, file contents, reference surfaces, validator baselines — was gathered from that revision.

- Proposal date: 2026-08-08
- Review instrument: Phase 4A collation (DLG Contract § Phase 4)
- Decision authority: Resonant Jones / Chris Castillo — human acceptance required
- Review status at time of writing: Proposed, pending human canonicalization

---

## Section H — Pre-merge validations

- [ ] Phase 3A DLG validator: pass (baseline confirmed at `9c8becac8`)
- [ ] Phase 3B ARP validator: pass (baseline confirmed)
- [ ] `make docs`: pass (baseline confirmed)
- [ ] No protected surfaces modified (confirmed — this artifact is net-new under `docs/architecture/adr/proposed/`)
- [ ] No DLG node created (confirmed — 9 nodes, 8 relations, unchanged from baseline)
- [ ] 9-node / 8-edge corpus invariant preserved
- [ ] 4-orphan count preserved

**Post-validation note (2026-08-08):** This artifact was committed as a standalone review file. The Phase 3A and Phase 3B validators were re-run after committing this file and confirmed PASS with identical output (unchanged since the baseline runs against `9c8becac8`).

---

## Appendix A — Protected surfaces untouched

| Surface | Confirmed untouched |
|---|---|
| `docs/architecture/adr/adr-index.md` | ✓ |
| `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md` | ✓ |
| `docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md` | ✓ |
| `docs/architecture/document-lifecycle-graph-contract.md` | ✓ |
| `docs/architecture/product-lanes-and-boundaries.md` | ✓ |
| `docs/architecture/00-current-state.md` | ✓ |
| `docs/knowledge-graph/nodes/*.json` (9 files) | ✓ |
| `docs/knowledge-graph/generated/*.json` (6 files) | ✓ |
| `scripts/knowledge_graph/validate_and_generate_dlg.py` | ✓ |
| `scripts/knowledge_graph/generate_representative_arps.py` | ✓ |

## Appendix B — Full collision pair at-a-glance

| Number | Canonical holder recommendation | Non-canonical treatment | Status gate | Downstream risk |
|---|---|---|---|---|
| 005 | Runtime Mode (Accepted, ADR-057) | Imprint UI → tombstone | Accepted > Proposed | Zero |
| 016 | Continuity Governance (Accepted, 14 refs) | Workspace Retrieval → renumber | Both Accepted (ref-count tiebreaker) | Medium |
| 024 | Context Command (Accepted, 5 refs) | Workspace Obsidian → renumber | Both Accepted (ref-count tiebreaker) | Low |
| 039 | Operator/User (Proposed, ADR-057 + chronology) | Capability Mesh → renumber | Governance > Status | Zero |
| 041 | VaultNode (Accepted, ADR-057) | Provider Capability → renumber | Accepted > Proposed | Zero |
| 053 | Node-Hosted Room (merge adjudication, ADR-057) | ThreadSpace/WhisperMesh → tombstone | Human adjudication | Zero |
| 055 | ThreadSpace/WhisperMesh (ADR-057, commit-chain) | Orthogonal UI → renumber | Governance-intent | Medium |
