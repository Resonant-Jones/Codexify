# DLG Architecture Control Plane Phase 0 Inventory

## Status

- Phase: DLG staged migration Phase 0 — inventory
- Review posture: reviewed repository inspection
- Inventory date: 2026-08-08
- Repository revision: `a38865a6c3c3a509fbe59f2516b27fe24aadce2b`
- Corpus size: 9 files
- Governing architecture:
  - ADR-056 — Accepted
  - ADR-057 — Accepted

This receipt is canonical evidence of the bounded Phase 0 inspection at the recorded repository revision. It is not a canonical DLG node corpus and does not assign document IDs, authority, lifecycle, freshness, evidence, retrieval policy, or graph relationships.

## Purpose

This pilot inventories the architecture control plane — nine documents whose meaning and authority are already well understood — before any Phase 1 classification. The goal is to establish a small calibration corpus whose files and repository properties are objectively known before any semantic classification occurs.

## Scope

Exactly nine governed document-like files:

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/README.md`
3. `docs/architecture/adr/adr-index.md`
4. `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md`
5. `docs/architecture/document-lifecycle-graph-contract.md`
6. `docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md`
7. `docs/architecture/product-lanes-and-boundaries.md`
8. `docs/architecture/proofs/2026-08-07-dlg-pao-canonical-history-publication-proof.md`
9. `docs/axis-node/README.md`

## Explicit exclusions

This inventory does not cover:

- the rest of `docs/architecture`
- all ADRs except for the repository-wide numeric collision check
- source code
- tests
- schemas as inventory members
- runtime/operator docs
- design canon
- campaigns
- product specs
- historical archives
- proofs other than the specifically scoped publication proof
- the full Axis corpus

The DLG schema and example are pre-read references, not inventory members.

## Inventory methodology

- **Repository revision**: `git rev-parse HEAD` at inventory time.
- **Tracked-file check**: `git ls-files --error-unmatch` for each path.
- **Regular-file/symlink check**: `test -f` plus `test ! -L` for each path.
- **H1 extraction**: first line starting with `# ` in the source bytes, decoded as UTF-8.
- **Byte-size method**: Python `Path.read_bytes()` plus `len()`.
- **SHA-256 method**: Python `hashlib.sha256(data).hexdigest()` over the exact governed source bytes.
- **Git blob method**: `git hash-object -- $path` over the working-tree file.
- **Last-touch commit method**: `git log -1 --format='%H' -- $path`.
- **Git filter inspection**: `git check-attr filter -- $path`.
- **LFS pointer detection**: whether the source bytes start with `version https://git-lfs.github.com/spec/v1\n`.
- **Title duplicate method**: H1-to-path mapping within the nine-file corpus.
- **ADR-number collision method**: read-only `docs/architecture/adr/*.md` glob, regex `^(\d{3})-` prefix extraction, duplicate-prefix detection.
- **Rename/alias review method**: `git log --follow --name-status -- $path` for each scoped file; only `R` status codes or explicit source-document statements qualify as evidence.

## Inventory table

| Path | H1 title | Bytes | SHA-256 | Git blob | Last-touch commit | Git filter | LFS pointer | Finding |
|---|---|---|---:|---|---|---|---|---|
| `docs/architecture/00-current-state.md` | *(missing)* | 6983 | `ec822ec0cd5ece547917e35d3b1036fdf7837ba0b7cae20d2d7ba111be01f8c4` | `cc3dfa367d06cc0adaa7c9af0ab211c15ca1b813` | `c03ce771faf089a9648fcb4267ca84fa7c05efa5` | unspecified | false | Missing H1 title |
| `docs/architecture/README.md` | Codexify Architecture KB | 87397 | `527e0087d127ddf087a4cafcc0518d6c0a8bec2f7a8d80e894e56ec5836c32de` | `6d87876531b8a669287bd75821c0165a4e2b6b0e` | `a38865a6c3c3a509fbe59f2516b27fe24aadce2b` | unspecified | false | none |
| `docs/architecture/adr/adr-index.md` | ADR Index | 30349 | `e273efcbf095d0f2ae7b83e1f4909c4ba9260d80011b8c9763864356b1430503` | `2bd7e3234ec13db91bc954995f129f90644924bc` | `a38865a6c3c3a509fbe59f2516b27fe24aadce2b` | unspecified | false | none |
| `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md` | ADR-056: Document Lifecycle Graph Control Plane | 6882 | `3cd9e3e3ec9e86adc41f55e1fb439451f3667ef6ce447894a0cecb639894f9aa` | `c249edd52158de2b1146663f4fac3a5034748961` | `397f73c8b55d6655b3143249c095b7c2fd965fc1` | unspecified | false | none |
| `docs/architecture/document-lifecycle-graph-contract.md` | Document Lifecycle Graph Contract | 27480 | `60b0296549077fbd7e1cbda30976e43d12f404573ce65c7eb87e261a4a1377b8` | `06b21b1559f6e617ea37e667bd36e6677792ed5b` | `a38865a6c3c3a509fbe59f2516b27fe24aadce2b` | unspecified | false | none |
| `docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md` | ADR-057: Product Architecture Ontology as a Document Lifecycle Graph Extension | 12451 | `c555995be833d45cffd739892f84afce512a230f21e896900a29106538303d12` | `f929cea1e96ba2a2e7bea6cbe052784f3414537e` | `a38865a6c3c3a509fbe59f2516b27fe24aadce2b` | unspecified | false | none |
| `docs/architecture/product-lanes-and-boundaries.md` | Product Lanes and Boundaries | 27715 | `12ce5c58ed63efcad55363695344fc92a2f3f2a0b278e9212209dc785b21a8e2` | `3a2cf56d246859f6562201290d27f5ae4952e749` | `a38865a6c3c3a509fbe59f2516b27fe24aadce2b` | unspecified | false | none |
| `docs/architecture/proofs/2026-08-07-dlg-pao-canonical-history-publication-proof.md` | DLG / PAO Canonical History Publication Proof | 4458 | `a7a21363992ec0bbdba7e56e954682882c8f844e9b678e079fc3253591fc45b2` | `bfe44657af7a1019419e9fcd0830da46b13500d4` | `fe296e2d5bc3f58f5adf33c40ef2357bd56ca2c3` | unspecified | false | none |
| `docs/axis-node/README.md` | Axis Node | 5196 | `94cfcae9b3cbd1f8d85d997729c7d895901c522eaa184e67b9654ef2cfb2ba09` | `37c9b8d83b3d1f29009461f97a8209baf629b3d9` | `a38865a6c3c3a509fbe59f2516b27fe24aadce2b` | unspecified | false | none |

## Scoped duplicate findings

### Duplicate paths

None observed. All nine scoped paths are unique.

### Duplicate H1 titles

None observed within the nine-file corpus. All extracted H1 titles are distinct.

### Byte-identical files

None observed. All nine SHA-256 digests are unique within the corpus.

## ADR-number collision findings

Repository-wide read-only scan of `docs/architecture/adr/*.md` for duplicate numeric prefixes:

| ADR number | Paths |
|---|---|
| 005 | `docs/architecture/adr/005-imprint-ui-deprecation-and-identity-ownership.md`<br>`docs/architecture/adr/005-runtime-mode-and-account-boundary-invariants.md` |
| 016 | `docs/architecture/adr/016-continuity-governance-surface-contract.md`<br>`docs/architecture/adr/016-workspace-retrieval-source-for-local-knowledge.md` |
| 024 | `docs/architecture/adr/024-context-command-active-connector-semantics.md`<br>`docs/architecture/adr/024-workspace-obsidian-selection-and-injection-contract.md` |
| 039 | `docs/architecture/adr/039-capability-oriented-mesh-architecture.md`<br>`docs/architecture/adr/039-operator-user-access-boundary.md` |
| 041 | `docs/architecture/adr/041-provider-capability-model-contract.md`<br>`docs/architecture/adr/041-vaultnode-canonical-machine-and-audit-authority.md` |
| 053 | `docs/architecture/adr/053-node-hosted-room-access-boundary.md`<br>`docs/architecture/adr/053-threadspace-whispermesh-managed-service-boundary.md` |
| 055 | `docs/architecture/adr/055-orthogonal-ui-material-personalization.md`<br>`docs/architecture/adr/055-threadspace-whispermesh-managed-service-boundary.md` |

7 collision groups detected. All require later human review. ADR-056 explicitly notes these pre-existing collisions. No repairs are attempted in Phase 0.

## Alias and rename observations

No evidence-backed alias or rename candidates identified within the bounded corpus.

`git log --follow --name-status` for each scoped file showed no `R` (rename) status codes. No scoped source document contains an explicit statement identifying itself as an alias for or rename of another document.

## Git/LFS findings

| Path | Git filter | LFS pointer | Note |
|---|---|---|---|
| `docs/architecture/00-current-state.md` | unspecified | false | — |
| `docs/architecture/README.md` | unspecified | false | — |
| `docs/architecture/adr/adr-index.md` | unspecified | false | — |
| `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md` | unspecified | false | — |
| `docs/architecture/document-lifecycle-graph-contract.md` | unspecified | false | — |
| `docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md` | unspecified | false | — |
| `docs/architecture/product-lanes-and-boundaries.md` | unspecified | false | — |
| `docs/architecture/proofs/2026-08-07-dlg-pao-canonical-history-publication-proof.md` | unspecified | false | — |
| `docs/axis-node/README.md` | unspecified | false | — |

All nine files have unspecified Git `filter` attributes and contain actual source bytes (not LFS pointers). No file requires special LFS handling before Phase 1.

## Inventory anomalies

- **Missing H1 title**: `docs/architecture/00-current-state.md` opens with `## Purpose` and contains no `# ` heading. The file is otherwise a well-formed Markdown document. This is recorded as an objective inventory fact, not as a content defect. Does not block Phase 1 classification.

No unexpected symlinks, untracked files, unreadable files, hash failures, or unexpected LFS pointers were observed.

## Phase 1 classification queue

All nine files are eligible for reviewed Phase 1 classification:

1. `docs/architecture/00-current-state.md` *(note: missing H1 title)*
2. `docs/architecture/README.md`
3. `docs/architecture/adr/adr-index.md`
4. `docs/architecture/adr/056-document-lifecycle-graph-control-plane.md`
5. `docs/architecture/document-lifecycle-graph-contract.md`
6. `docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md`
7. `docs/architecture/product-lanes-and-boundaries.md`
8. `docs/architecture/proofs/2026-08-07-dlg-pao-canonical-history-publication-proof.md`
9. `docs/axis-node/README.md`

This section means: *eligible for reviewed Phase 1 classification*.

It does not mean: accepted as canonical DLG nodes, assigned IDs, assigned authority, assigned lifecycle, assigned freshness, assigned evidence class, or accepted graph relationships.

No file requires human review before Phase 1. The missing H1 title on `00-current-state.md` is a noted observation, not a Phase 1 blocker.

## Deferred work

The following are explicitly deferred to later DLG phases or tasks:

1. stable `codexify:doc:*` identity assignment
2. DLG node-record creation
3. kind classification
4. authority classification and scopes
5. lifecycle state
6. freshness state and triggers
7. disposition
8. evidence class
9. ownership
10. source anchors
11. retrieval policy
12. temporal metadata
13. `governing_adr_posture`
14. PAO `architecture_scope`
15. canonical relations
16. duplicate resolution
17. ADR collision resolution
18. supersession decisions
19. contradiction decisions
20. compatibility pointers
21. generated graph/report creation
22. deterministic resolver
23. ARP generation
24. corpus-wide inventory
25. runtime/retrieval/database integration

## Phase 0 conclusion

The nine-file architecture-control-plane calibration corpus is ready for a separate reviewed DLG Phase 1 classification task.
