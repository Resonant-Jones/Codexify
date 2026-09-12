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

The prototype's Sources mode exposes these nine documents as bounded summaries and, on explicit request, renders their embedded derived snapshots in the existing reader. The renderer presents frontmatter, headings, lists, tables, blockquotes, code, standard links, and Obsidian wiki links without copying the corpus into a second editable truth surface. Repository-document links remain inside the reader.

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
- Inspector modes are `entity`, `relationship`, and `document`. Source actions load full Markdown in one click; the projection, search, selection, viewport, and list scroll remain in place. Root Back restores the prior entity/relationship inspector and opening-control focus.
- On desktop, the inspector opens at its pre-change `350px` width and exposes a focusable left-edge separator. Pointer dragging, Left/Right Arrow keys in `32px` increments, Home, and double-click resizing clamp between `350px` and `min(960px, viewport - 680px Atlas floor - 18px shell chrome)` without refitting or resetting the graph.
- The chosen inspector width is presentation-only state in the existing namespaced local-storage record. It survives entity, relationship, document, view, and reload transitions; blocked, missing, malformed, or out-of-range values fall back or clamp safely. The existing `294px` responsive column and stacked narrow layout remain authoritative below the desktop resize breakpoint.
- Explicit full-document rendering for approved repository-relative paths from the embedded snapshot bundle. Raw HTML is escaped, unsafe link schemes are rejected, and a failed or unsupported document read does not fall back to raw Markdown navigation.
- Document mode adds an explicit **Full screen** action. It moves the same live reader between the inspector and an opaque full-viewport modal, so rendered content, internal links, source provenance, reader-local history, and scroll position remain one stateful reading path. Modal Close returns to the inspector; reader Back remains document-history navigation.
- Exact local selection, search, view, edge, and viewport restoration after Galaxy return.
- Namespaced local presentation storage limited to card positions, viewport, and inspector width, with safe fallback for missing, blocked, malformed, or out-of-range storage.
- Reduced-motion handling and a 390px stacked projection/inspector layout without page-level horizontal overflow.
- A non-scrolling canvas clip boundary so keyboard focus cannot create a hidden horizontal scroll offset on narrow screens.
- Persistent `Architecture document snapshot · design prototype · no live connections` disclosure.
- No automatic or external network requests. Opening a full source document resolves from the embedded derived snapshot bundle.

The persistent hierarchy rail, tree rendering, hierarchy-only controls, and synthetic local hierarchy model remain absent. No replacement tree, file explorer, drawer, permanent list, or permanent legend was added.

## Architecture and ADR impact

No ADR impact. This change derives a visualization from accepted maintained sources. It changes no subsystem seam, authority boundary, runtime behavior, persistence rule, release claim, or architecture contract.

Codexify's constitutional distinctions remain explicit: documentation is evidence rather than runtime proof; a dependency is not authority; a key anchor is not exhaustive ownership; experimental does not mean production-ready; selection does not change runtime state; and Galaxy proximity grants no access.

## Validation and browser proof

### Inspector reading flow

The former source action → summary overlay → full-document sequence is replaced by source action → full document in the existing inspector. Sources has one `Read source document` action. Modules and relationships use `Open source note`. The modal positioning, dialog semantics, summary rendering, and second-step toggle were removed; the same reader markup and Markdown renderer now live inside the inspector.

Document mode has one independently scrolling body and a compact header with Back, title, path, source status, and original-Markdown link. A local stack stores document URL, source ID, and document scroll position. Back traverses linked documents first, then restores the metadata inspector. Selecting another object intentionally returns to entity/relationship mode. No browser-history navigation is used.

Prior inspector-reader verification: all 28 focused Node tests passed, including executable loader/history round trips for Atlas, Directory, and Sources with both entity and relationship origins, scroll restoration, unchanged search/selection/viewport, offline reads, and unsafe/out-of-repository link rejection. Documentation validation, diff checks, and the 90-document offline freshness check passed. The refresh helper and embedded corpus were not changed.

### Expandable inspector and full-screen reader

The pre-change CSS and browser-computed desktop inspector width were both exactly `350px`. That remains the default and minimum. The desktop maximum is `min(960px, viewport width - 680px minimum Atlas width - 18px shell padding/gap)`: this yields `742px` at 1440px and `960px` at 1680px, leaving 680px and 702px primary surfaces respectively after shell geometry.

The document article now gives prose a comfortable `72ch` maximum while letting table wrappers and code blocks consume the wider reader surface. Full-screen presentation is opaque `#080d15`/`#111827`, makes the underlying application inert, and reuses the exact reader DOM rather than introducing another parser, store, router, or history.

The resize boundary uses an invisible `18px` hit strip wholly inside the inspector and a single centered `3px × 48px` rounded grabber. The prior separator extended `7px` outside an overflow-clipped inspector, while its visible line ran nearly the full inspector height; focus then outlined that rounded, clipped hit target and produced the misleading elongated-D silhouette. The neutral grabber is now geometrically complete, with restrained accent-only hover, focus, and active-drag feedback confined to the short pill.

Targeted browser follow-up at 1440×1000 and 1680×1050 confirmed complete resting, hover/focus, and active-drag grabber geometry with no clipped-card or D silhouette. Pointer resize reached `600px`, `742px`, and `960px`; Arrow keys remained `32px` steps, Home and double-click reset to `350px`, reload retained the chosen width, graph transform and selection did not change during drag, and the established `680px`/`702px` Atlas floors remained intact. At 390×844 the handle remained absent and page horizontal overflow remained zero. Console inspection reported zero errors or warnings, and all browser requests stayed on the local prototype URL.

Current verification: 34 focused Node tests cover width bounds, grabber geometry, transparent hit-target presentation, malformed persistence, pointer/keyboard/cancellation/reset contracts, state-isolated resize behavior, mobile preview and sheet-state projections, the single-reader modal contract, existing Markdown safety, offline freshness parity, reader history, Galaxy, and prior Atlas semantics. Browser checks at 1680×1050 and 1440×1000 verified exact default/minimum width, intermediate pointer width (`748px`), maximum width (`960px` with a `702px` main surface), keyboard increments and Home reset, width persistence across reload and module-to-module Directory review, unchanged graph transform during resize, a real wide Markdown table, and full-screen scroll preservation at `650px`. In full-screen mode, ADR Index → ADR-001 → reader Back returned to ADR Index while the modal remained open; modal Close separately returned the same document, inspector width, selection, and graph transform. At 390×844 the handle was absent, the stacked inspector used the available `378px`, and page horizontal overflow was zero. A clean reduced-motion session computed the transition duration to `1e-05s`, reported zero console errors or warnings, and made only local prototype requests.

### Mobile graph-first review flow

The existing `820px` narrow breakpoint now treats the graph as the primary surface. The selected-object preview keeps only the category/source eyebrow, full selected-object title with a two-line maximum, and one descriptor line. Stable ID, paths, commit SHA, dependencies, blast radius, provenance, controls, and relationship detail remain in the inspector. At 390×844 the default module preview fell from `123.875px` to `49.046875px`, or 39.6% of its prior height. A deliberately long relationship title remained bounded to two title lines plus one descriptor line at `65.84375px` on the 360px-wide check.

The mobile inspector is a two-state bottom sheet. `peek` uses `clamp(150px, 21svh, 178px)` and renders a separate non-interactive summary; the full inspector is `display: none`, inert, and `aria-hidden` in that state. `expanded` uses `min(72svh, calc(100dvh - 184px))`, retains a visible Atlas strip, and gives metadata or document content its own scroll container. A compact inline dual-chevron button has an exact `44px × 44px` touch target, controls `#inspector`, reflects state through `aria-expanded`, and exposes `Expand details` / `Collapse details` labels. Enter-key activation returns focus to the same control. Reduced-motion computed both animation and transition durations as `1e-05s`.

Module and relationship choices made from the graph start a new cycle in `peek`; choices made from the expanded inspector retain `expanded`. Sheet transitions preserve projection, search, selection, pan, zoom, and reader history. In browser proof, a blank-canvas drag changed the world transform from `translate(-145px, 110px) scale(0.4)` to `translate(-187px, 82px) scale(0.4)`, wheel zoom changed it to `translate(-285px, 24.6px) scale(0.48)`, and both transform and the `context` search survived expand/collapse.

`Open source note` expresses reading intent and promotes the sheet directly to `document + expanded`. The mobile reader fills the sheet: the Modules and Ownership document measured `505px` of visible body against `5332px` of scrollable content, reached `320px` internal scroll while page scroll stayed zero, and preserved full-screen scroll state. Architecture Atlas → ADR Index → reader Back restored Architecture Atlas at its prior `240px` position; full-screen Close restored the same document at `480px`; leaving the root document restored Sources and returned the sheet to `peek` without changing the selected module.

Fresh browser checks passed at 390×844, 360×800, 430×932, and 1440×1000. At 390×844 the graph was `484.765625px` high versus a `177.234375px` peek sheet, the expand target was `44px × 44px`, the compact module preview was `49.046875px`, hidden full-inspector controls had zero visible focusable descendants, and horizontal overflow was zero. At 360×800 the long-relationship preview was `65.84375px`, graph `450px`, peek `168px`, and overflow zero. At 430×932 the graph was `572px`, peek `178px`, and overflow zero. The 1440×1000 desktop layout retained its `350px` inspector and 1072px main surface; keyboard resize reached `382px` and double-click reset to `350px` without horizontal overflow. The clean browser session reported zero console errors or warnings and only same-origin prototype/document requests.

Served browser checks at 1440×1000 and 390×844 verified module and relationship source reading, Sources and Directory remaining visible, rendered tables, and keyboard Back. Desktop retained a 1070px canvas alongside a 348px reader. Document keyboard scrolling reached 1706px while page scroll stayed zero and graph transform remained `translate(64px, 86px) scale(0.6421)`. Narrow mode had zero horizontal overflow and a 298px document body. ADR-001 → Back returned to ADR Index at 519px document scroll within Sources. Console inspection reported zero errors/warnings. HTTP requests remained local; direct-file visual verification remains unavailable under the browser tool's file-URL policy, with offline behavior covered by executable tests.

Pi delegation was attempted through the catalog preflight only: zero available model rows, no selected provider/model, and no inference.

### Local rendered-document preview

Atlas carries a compressed, generated embedded snapshot of all nine Sources documents and the ADR directory (90 documents). The reader resolves a known bundled document from that snapshot first under `file:`, `http:`, and `https:`; it does not require `/docs/**` to be served over HTTP. The reader labels the result as an embedded document snapshot, because canonical repository Markdown remains authoritative.

**Open original Markdown** remains a secondary escape hatch. It can reach current repository Markdown when the repository root is deliberately served, but a host that serves only the Atlas artifact may return a safe 404 for that secondary link. Primary reading and linked-document navigation must never depend on that route. Unbundled, unsafe, external, or out-of-repository document requests fail closed in the reader.

Refresh the derived bundle after canonical bundled-document changes with `node projection-ui-map/refresh-atlas-documents.cjs`; use `--check` as the freshness gate. The refresh helper is deterministic and does not make the snapshot an editable source of truth. Direct canonical Markdown serving remains a possible later architecture, not current prototype truth.

The standalone/local artifact remains `projection-ui-map/rc-atlas-prototype.html`. Private-preview repository wiring mounts that exact file read-only at the intended `/atlas/` route; no copied hosted edition exists. That static configuration proof is separate from runtime and external qualification, so `/atlas/` is not claimed live while the private-preview Chroma recovery/deployment lane remains blocked.

To read current repository content instead of the embedded snapshot, optionally serve the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory .
```

Then open `http://127.0.0.1:8765/projection-ui-map/rc-atlas-prototype.html`. The reader still renders bundled documents first; the server only makes the optional original-Markdown links reachable. No server is required for the embedded reader.

Correction validation: the focused Node suite exercises the actual asynchronous reader for bundled sources under `file:`, `http:`, and `https:`, including ADR navigation, reader Back, fail-closed paths, decompression, and bundle parity with canonical files. `node projection-ui-map/refresh-atlas-documents.cjs --check` validates all 90 embedded documents. The browser automation URL policy blocks attaching to `file://` tabs, so direct-file visual verification could not be completed through that tool; HTTP proof does not establish file-mode visual proof.

Historical pre-inspector validation recorded on 2026-09-11 (superseded for reader layout by the inspector checks above):

- `node --test projection-ui-map/rc-atlas-prototype.test.cjs` — passed, 26 tests. The suite parses the maintained Subsystem Matrix directly and proves exact name/class parity, exact row-field and key-anchor provenance, non-duplication, valid attributable edges, bounded relationship types, text-plus-color meaning, Directory parity, source reachability, bounded Markdown rendering and escaping, same-origin document loading, synthetic separation, selection/inspector behavior, useful fit, storage fallback, source-reader origin and local-context restoration, Galaxy state, reduced motion, and absence of hierarchy UI.
- `python3 scripts/validate_docs.py` — passed.
- `git diff --check` — passed.
- 1680×1050 wide desktop — passed: 20 graph cards, zero hierarchy/tree elements, canvas expanded to 1310px beside the 350px inspector, geometry-derived 70% fit, and no horizontal overflow.
- 1440×1000 desktop — passed: geometry-derived 65% first-load fit, module and edge selection, Key code anchors, solid dependency edge, dashed runtime-flow edge, Legend open/close, Directory, all nine Sources cards, keyboard mode switching, and empty-search recovery.
- Source reader at 1440×1000 — passed: Sources returned to Sources with the `docs` query and opening-card focus intact; Directory returned to Directory with inspector selection intact; Atlas returned to Atlas with the exact selected module and `translate(-127.275px, 71.5274px) scale(0.5)` viewport intact. Reader close passed with click, `Enter`, and `Escape` activation, and the URL did not change.
- Rendered ADR reader — passed: the ADR Index presented frontmatter, headings, 77 ordered entries with source numbering, and formatted body content rather than raw Markdown. Its first Obsidian wiki link rendered ADR-001 inside the same reader while the Atlas URL remained unchanged.
- Search — passed for module name (`Sync API`), responsibility (`collaboration permissions`), and anchor (`guardian/vector/store.py`), each returning the intended module.
- Canvas — passed: a wheel gesture changed the fitted view from 65% to 73%; empty-canvas drag changed the viewport translation; Reset view restored the geometry-derived fit.
- Galaxy — passed under normal and reduced motion. The confirmation gate remained mandatory; return restored the exact selected module, query, and viewport. Reduced-motion transition duration computed to `1e-05s` and entry/return completed without the animated delay.
- 390×844 narrow viewport — passed: `scrollWidth === innerWidth === 390`, 20 Atlas cards, 20 Directory rows, nine Sources cards, keyboard module selection, rendered ADR content without reader or page overflow, and no hierarchy/tree surface. Focusing a spatially off-screen module left canvas `scrollLeft === 0`, preserving the contextual summary. The Sources reader round trip preserved the `docs` query, exact page scroll position (`988px`), source-card focus, and Sources projection under keyboard-only `Enter` / `Space` activation.
- Console — passed with 0 errors and 0 warnings.
- Network — the clean reader-regression session recorded the prototype request plus explicit same-origin Markdown document requests; no external request or browser-history navigation occurred.

Captured browser review images:

- `/tmp/atlas-codexify-default-1440.png` — default real Codexify module graph.
- `/tmp/atlas-codexify-module-selected.png` — selected core-loop module with documented inspector detail.
- `/tmp/atlas-codexify-edge-selected.png` — selected dependency with provenance and normalization.
- `/tmp/atlas-codexify-legend.png` — optional node/edge legend.
- `/tmp/atlas-codexify-mobile.png` — narrow Atlas with contained contextual summary.

These captures are human product-review evidence only, not live-runtime proof.

## Deferred work

The conceptual minimap/frame-map, media preview, inspector dismissal, and subsequent Sources-density refinement remain deferred.

Exhaustive module-to-file membership, AST/import/call-graph indexing, automatic code scanning, code-derived topology reconciliation, Neo4j ingestion, live telemetry, production Atlas integration, Work Graph, contributor task claiming, GitHub/Linear work synchronization, Galaxy federation, and deployment remain separate future slices. No production frontend or architecture source document was changed.

Modules are places on the map. Files are details about the place.
