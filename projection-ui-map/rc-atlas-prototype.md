# RC Atlas — Codexify architecture projection

## Purpose and evidence posture

This standalone contributor prototype projects Codexify's maintained architecture documentation at subsystem resolution. It is a read-only design artifact, not canonical architecture storage, exhaustive source indexing, live-runtime proof, or a production Atlas integration.

The projection was extracted from canonical `origin/main` commit:

`cb551de1866715ef421026203ffe2a87cec8aaca`

Work began after the hierarchy-rail removal was validated and committed at branch HEAD `1e8799099be3f3d06621e25740ada93f2c29dde4`. The topology-bearing source files were byte-identical between that branch state and the inspected `origin/main` snapshot; the ADR index differed but supplies decision context rather than projected node or edge data.

`docs/architecture/00-current-state.md` remains short-horizon release and operational truth. The browser rendering does not prove supported release posture, live connectivity, current process state, provider execution, persistence, authorization, synchronization, or federation.

## Source set and eligibility

The required documents were read from the inspected commit in this order:

1. `docs/architecture/00-current-state.md` — short-horizon release truth.
2. `docs/architecture/adr/adr-index.md` — decision context; no ADR was changed.
3. `docs/architecture/README.md` — architecture KB routing.
4. `docs/architecture/kb-validity-matrix.md` — source eligibility.
5. `docs/architecture/architecture-atlas.md` — peer reading guide.
6. `docs/architecture/modules-and-ownership.md` — primary subsystem dataset.
7. `docs/architecture/system-overview.md` — coarse runtime topology clarification.
8. `docs/architecture/flows.md` — runtime-flow evidence.
9. `docs/architecture/data-and-storage.md` — persistence and storage clarification.

The prototype's Sources mode exposes these nine documents as provenance links and bounded summaries. It does not copy them into a second editable truth surface.

The KB validity rules excluded `supplementary_verify_against_code`, `design_canon_not_runtime_truth`, `historical_archive`, and `misleading_identity_drift` material from topology extraction. In particular, legacy GuardianOS, Threadspace, `guardian-backend_v2`, obsolete installer, future federation, and historical audit documents were not used as present subsystem evidence. Visual material continues to follow the already accepted Codexify prototype treatment; design canon is not used as runtime topology evidence.

## Module projection rules

- Exactly one primary graph node is created for each current row in the maintained `Subsystem Matrix`.
- The projection contains 20 subsystem nodes: 7 `core loop`, 10 `supporting`, 2 `experimental`, and 1 `retired`.
- Every node preserves the source row's subsystem name, class, responsibilities, key code anchors, human-readable dependency fields, downstream dependents, and blast radius.
- Every node carries the repository-relative source path, source section, `authoritative_now` classification, inspected commit, and `documentation_snapshot` authority marker.
- Stable prototype IDs normalize subsystem names for interaction only. They do not redefine subsystem identity or architecture ownership.
- Source files, routes, functions, classes, tests, migrations, and arbitrary directories are not graph nodes.
- The UI uses the label `Key code anchors`. These paths are the source document's inspection starting points, not an exhaustive claim about every file contained by a module.
- Documentation-backed modules are the default local Atlas. The prior synthetic HomeBase/Space/Room fixture is no longer current topology data. Galaxy remains an explicitly entered synthetic illustration and is visually and textually separated from the architecture snapshot.

## Visual and relationship vocabulary

Node classes use the exact broad source vocabulary:

- `CORE LOOP` — blue glyph and rim accent.
- `SUPPORTING` — green glyph and rim accent.
- `EXPERIMENTAL` — amber glyph and rim accent.
- `RETIRED` — gray glyph and rim accent.

Cards retain one shared Codexify material shell. Category color is subordinate to the written class label, consistent glyph, compact name and responsibility preview, and selected-state treatment.

The bounded edge registry contains:

- `dependency` — 20 solid blue directional relationships labeled `depends on`, sourced from confidently mapped `Subsystem Matrix` dependency text.
- `runtime_flow` — 7 dashed violet directional relationships labeled `runtime flow`, sourced only from explicit sequences in `docs/architecture/flows.md`.

Each relationship resolves two valid module IDs and carries an evidence path, section, source classification, inspected commit, evidence type, normalization note, explanation, and caution. Selecting an edge expands those details in the inspector. Arrow direction, readable labels, stroke pattern, and inspector copy carry meaning; color is never the only carrier.

The optional Legend is a dismissible overlay rather than a persistent sidebar. Directory remains the flat searchable route to every module, and Sources remains the documentation-reading route.

## Conservative normalization and omissions

Human-readable dependency phrases were converted into module-to-module edges only when a named subsystem row could be identified confidently. `direct_documented` marks an explicit named subsystem relationship. `bounded_normalization` marks a documented phrase or flow step normalized to the maintained subsystem resolution; it is not inferred architectural similarity.

The following were intentionally left as inspector text rather than invented nodes or speculative edges:

- external Redis, Postgres, browser storage, provider credentials, external network, environment configuration, and model-server dependencies;
- generic API-bootstrap references to configuration, dependencies, middleware, or “all routers”;
- context-broker references to memory stores or optional graph adapters that do not name another current subsystem row;
- provider-setting, credential, and network requirements;
- Sync API references to process-local buses and models;
- broad `Depended on by` prose when mapping it would duplicate or over-interpret a more precise forward dependency;
- any plausible runtime transition not explicitly present in the maintained flow source.

No maintained sources produced a contradictory named subsystem boundary in the selected projection. Ambiguous prose was omitted rather than adjudicated in prototype data.

## Preserved interaction and boundary behavior

- Spatial pan, pointer-centered wheel zoom, draggable cards, geometry-derived useful fit, and Reset view.
- Keyboard-operable graph cards, edge labels, tabs, search, Directory, Sources, Legend, source reader, and Galaxy gate.
- Search over module names, responsibilities, dependency text, and key code anchors.
- Module and relationship selection with contextual inspector updates and back history.
- Exact local selection, search, view, edge, and viewport restoration after Galaxy return.
- Namespaced local presentation storage limited to card positions and viewport, with safe fallback for missing, blocked, or malformed storage.
- Reduced-motion handling and a 390px single-surface layout without page-level horizontal overflow.
- A non-scrolling canvas clip boundary so keyboard focus cannot create a hidden horizontal scroll offset on narrow screens.
- Persistent `Architecture document snapshot · design prototype · no live connections` disclosure.
- No automatic external network requests.

The persistent hierarchy rail, tree rendering, hierarchy-only controls, and synthetic local hierarchy model remain absent. No replacement tree, file explorer, drawer, permanent list, or permanent legend was added.

## Architecture and ADR impact

No ADR impact. This change derives a visualization from accepted maintained sources. It changes no subsystem seam, authority boundary, runtime behavior, persistence rule, release claim, or architecture contract.

Codexify's constitutional distinctions remain explicit: documentation is evidence rather than runtime proof; a dependency is not authority; a key anchor is not exhaustive ownership; experimental does not mean production-ready; selection does not change runtime state; and Galaxy proximity grants no access.

## Validation and browser proof

Validation recorded on 2026-09-11:

- `node --test projection-ui-map/rc-atlas-prototype.test.cjs` — passed, 23 tests. The suite parses the maintained Subsystem Matrix directly and proves exact name/class parity, exact row-field and key-anchor provenance, non-duplication, valid attributable edges, bounded relationship types, text-plus-color meaning, Directory parity, source reachability, synthetic separation, selection/inspector behavior, useful fit, storage fallback, Galaxy state, reduced motion, and absence of hierarchy UI.
- `python3 scripts/validate_docs.py` — passed.
- `git diff --check` — passed.
- 1680×1050 wide desktop — passed: 20 graph cards, zero hierarchy/tree elements, canvas expanded to 1310px beside the 350px inspector, geometry-derived 70% fit, and no horizontal overflow.
- 1440×1000 desktop — passed: geometry-derived 65% first-load fit, module and edge selection, Key code anchors, solid dependency edge, dashed runtime-flow edge, Legend open/close, Directory, all nine Sources cards, keyboard mode switching, and empty-search recovery.
- Search — passed for module name (`Sync API`), responsibility (`collaboration permissions`), and anchor (`guardian/vector/store.py`), each returning the intended module.
- Canvas — passed: a wheel gesture changed the fitted view from 65% to 73%; empty-canvas drag changed the viewport translation; Reset view restored the geometry-derived fit.
- Galaxy — passed under normal and reduced motion. The confirmation gate remained mandatory; return restored the exact selected module, query, and viewport. Reduced-motion transition duration computed to `1e-05s` and entry/return completed without the animated delay.
- 390×844 narrow viewport — passed: `scrollWidth === innerWidth === 390`, 20 Atlas cards, 20 Directory rows, nine Sources cards, keyboard module selection, and no hierarchy/tree surface. Focusing a spatially off-screen module left canvas `scrollLeft === 0`, preserving the contextual summary.
- Console — passed with 0 errors and 0 warnings.
- Network — five deliberate localhost page reloads were recorded, all `GET http://127.0.0.1:8765/rc-atlas-prototype.html` → `200`; no external request occurred.

Captured browser review images:

- `/tmp/atlas-codexify-default-1440.png` — default real Codexify module graph.
- `/tmp/atlas-codexify-module-selected.png` — selected core-loop module with documented inspector detail.
- `/tmp/atlas-codexify-edge-selected.png` — selected dependency with provenance and normalization.
- `/tmp/atlas-codexify-legend.png` — optional node/edge legend.
- `/tmp/atlas-codexify-mobile.png` — narrow Atlas with contained contextual summary.

These captures are human product-review evidence only, not live-runtime proof.

## Deferred work

Exhaustive module-to-file membership, AST/import/call-graph indexing, automatic code scanning, code-derived topology reconciliation, Neo4j ingestion, live telemetry, production Atlas integration, Work Graph, contributor task claiming, GitHub/Linear work synchronization, Galaxy federation, and deployment remain separate future slices. No production frontend or architecture source document was changed.

Modules are places on the map. Files are details about the place.
