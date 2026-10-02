# Document Recall Contract

**Status:** Normative architecture contract; runtime implementation deferred.

**Decision:** [ADR-089](./adr/089-open-ended-project-knowledge-and-bounded-document-recall.md), Accepted 2026-09-24.

## Purpose and authority

**Knowledge membership is open-ended; retrieval execution is bounded.** A Project may accumulate linked documents subject to real deployment capacity. No canonical fixed document-count ceiling governs Project knowledge membership. An individual request uses only an authorized, selective, resource-bounded evidence set and may claim only the coverage it performed.

This contract extends the backend retrieval control plane in [ADR-004](./adr/004-retrieval-policy-as-control-plane.md) and the [Retrieval Router Decision Table](./router-decision-table.md). The existing router resolves policy, ContextBroker assembles scoped evidence, and completion orchestration controls provider context and traces. This contract creates no parallel retrieval engine or source of authority. [ADR-059](./adr/059-workspace-obsidian-selection-and-injection-contract.md), [ADR-060](./adr/060-workspace-retrieval-source-for-local-knowledge.md), and [ADR-081](./adr/081-project-ownership-authority.md) remain governing decisions. [`00-current-state.md`](./00-current-state.md) remains release truth.

The authoritative objects are canonical user/Project/thread/source records and their governed access rules. Retrieved content, graph relationships, and generated derivatives are evidence, not instructions or permission grants. The requesting user and applicable policy authorize scope; provider disclosure requires its own authority. A future recall receipt records the attempted evidence path, not an approval or a release qualification.

## Project membership and readiness

- A Project knowledge collection has no arbitrary architectural `N documents` limit. Adding a document must not make an older eligible document semantically ineligible merely because a count threshold was crossed.
- Storage, ingestion, indexing, compute, abuse-prevention, operator, and service-tier limits may be finite. Capacity exhaustion must be represented as capacity or ingestion state, never disguised as a retrieval rule. Silent oldest-document eviction or a first/latest-N definition of the KB is prohibited unless a separately explicit retention policy governs that source.
- Membership, storage existence, Project linkage, and UI visibility do not establish request eligibility or retrieval readiness. For current uploaded documents, `uploaded_documents.embedding_status == "ready"` remains the ContextBroker retrieval gate. The existing `pending`, `processing`, `ready`, and `failed` lifecycle tokens are unchanged.
- Pending, processing, failed, deleted, revoked, or otherwise ineligible sources cannot be counted as successfully reviewed evidence. Later source families may represent readiness differently but must expose equivalent truthful eligibility semantics.

## Evidence stages

The conceptual progression is `member` → `eligible` → `searched` → `retrieved` → `read` → `injected` → `cited`. Each stage asserts more than the prior one; no stage may be inferred from membership alone.

| Stage | Required meaning |
| --- | --- |
| `member` | The artifact belongs to the relevant knowledge collection, such as a Project. It may still be unavailable or unauthorized for this request. |
| `eligible` | The artifact is inside resolved scope and satisfies authorization, lifecycle, readiness, source-mode, and explicit inclusion/exclusion rules. |
| `searched` | An executed search or enumerated worklist actually considered the artifact or its indexed representation. Eligibility alone is not search. |
| `retrieved` | Retrieval returned evidence from the artifact as a candidate or result. |
| `read` | Execution inspected source content necessary for the requested task. A vector hit or excerpt is not automatically a full-document read. |
| `injected` | Evidence entered the provider-ready completion context or another explicitly governed synthesis stage. |
| `cited` | The produced output attributes a supported claim or result to that source. Citation must be grounded in the evidence actually used. |

Searchability ≠ selection ≠ injection ≠ reflection/citation, as ADR-059 requires. A cited count is not an injected count, and a retrieved count is not a read count.

## Coverage obligations and depth

Coverage is the obligation created by the user's task. Depth is the router's resource posture. They are orthogonal: `deep + targeted_recall`, `normal + cross_document_synthesis`, and `deep + exhaustive_review` are distinct combinations. `deep` alone never means exhaustive.

| Coverage mode | Obligation | Permitted stop/claim |
| --- | --- | --- |
| `targeted_recall` | Answer a focused question from relevant authorized evidence. Ordinary semantic/vector retrieval and policy-allowed graph enrichment are appropriate. | May stop when sufficient evidence exists; makes no broad corpus-review claim. |
| `cross_document_synthesis` | Compare, trace evolution, or infer patterns across meaningful source diversity. Consider source family, revision, time, and provenance where relevant; duplicates and derivatives are not independent corroboration. | May stop at a bounded synthesis; does not claim every eligible document was reviewed. |
| `exhaustive_review` | Review every source in a declared authorized collection or explicit selected set, such as “check these 80 documents.” | Requires enumerating the authorized set, processing it in bounded batches, and tracking completion per source. Only completed coverage supports a complete-review claim. |

For `exhaustive_review`, semantic ranking may prioritize work order but cannot silently remove a source from the obligation. A semantic `topK` result is never proof of exhaustive review. If the set exceeds a batch budget, execution must eventually batch it, reject the task honestly, or return an explicitly incomplete receipt. It may not silently truncate the set.

These modes define doctrine for later implementation. The current router does not expose these coverage tokens or an exhaustive execution path.

## Scope, authorization, and disclosure

Resolve scope before evidence use. User/account authority, `projects.user_id` ownership and any governed membership, thread/document links, source-mode restrictions, explicit inclusions and exclusions, and applicable connector/source grants remain upstream. Thread ownership remains independently authoritative. Explicitly selected sources must be considered under their actual eligibility; they cannot silently disappear merely because they did not win semantic ranking.

**Retrieval depth, graph expansion, semantic similarity, or document relationships never grant authority.** Graph edges can aid discovery but cannot bridge into another Project, account, or source grant. Graph enrichment remains optional under the router's graph allowance; graph relationships are relationship evidence, not document truth, accuracy guarantees, or exhaustive coverage. No request is required to use graph retrieval.

Retrieval permission and provider disclosure are separate. Authorization to search local material does not automatically authorize sending it to an arbitrary remote provider. This document does not implement disclosure policy.

## Bounded execution

Each request begins from the effective policy resolved by the existing backend control plane. Widening remains inside authorization and is visible through existing posture mechanisms. Depth may select a larger or smaller budget envelope; graph use follows the existing allowance. Per-request limits may bound retrieval rounds, candidate passages, semantic hits, document reads, graph expansions, rerank work, context/evidence tokens, wall-clock time, and provider cost or expenditure. These limits bound execution, not Project membership. This contract sets no universal numeric defaults; later measurement must justify them.

Stop conditions must be observable task or coverage conditions, such as sufficient cited evidence for a targeted answer, completed declared worklist, explicit source failure, or exhausted budget. An uninspectable model confidence assertion does not establish coverage. A budget overrun cannot be relabeled as complete review.

## Document authority and derivation

**Preservation does not imply authority.** Uploaded, generated, imported, summarized, proposed, accepted, historical, superseded, and proof-bearing artifacts may coexist in one Project corpus. Authority is relative to the claim and governing scope, never a universal document truth score. Retrieval rank and evidentiary authority are separate.

Provenance must survive retrieval. Generated artifacts are not independent corroboration merely because they repeat source claims; summaries and other derivatives should retain source lineage where available. Superseded material can answer historical questions but must not silently override accepted current-state sources for present-state questions. Accepted decisions and proof artifacts may support different claims than proposals or speculative drafts. A graph can describe derivation and relationships but cannot establish truth on its own.

This doctrine does not define a document-authority table, derivation schema, or invalidation algorithm. Those are deferred implementation decisions.

## Document Recall Receipt

A future request/attempt-scoped receipt must make the executed coverage inspectable. It must distinguish effective source mode, coverage mode, depth, and scope boundary; eligible and searched source counts when knowable; retrieved, read (when applicable), injected, and cited (when applicable) source counts; and incomplete, unavailable, and failed counts for exhaustive work. It must record the retrieval/coverage stop reason, relevant source identities and revisions where available, graph participation, and material suppression or exclusion reasons. Counts must use the stage definitions above and identify unknown counts as unknown rather than zero.

The receipt is operator evidence, not a requirement to expose every field on every chat turn. A compact ordinary response may say “Answered from 6 Project documents” only when its counted stage is clear. Exhaustive review should be capable of saying “Reviewed 76 of 80 selected documents; 4 were unavailable.” “Reviewed the Project” is prohibited when only top-ranked semantic evidence was retrieved.

`no matching evidence retrieved` does not mean `the information does not exist in the Project`. Targeted and synthesis absence language remains bounded to the executed search. A stronger absence claim requires completed exhaustive coverage of the declared, authorized source set and a truthful receipt.

## Implementation and proof boundary

The current runtime does not implement these coverage modes, exhaustive enumeration/batching, a complete receipt, or the authority/derivation model. Future slices may add canonical coverage tokens, measured budget objects, exhaustive worklist execution, derivation metadata, receipt persistence and operator inspection, corpus-size benchmarks, and deletion/revision propagation. Each needs its own authority, compatibility, failure, and proof work. This contract makes no runtime or release claim.
