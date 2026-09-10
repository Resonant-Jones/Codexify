# Resonant Constructs Atlas contributor prototype

## Purpose and evidence posture

This isolated HTML prototype lets a contributor explore the proposed hierarchy:

```text
User or Organization
└── HomeBase
    └── Space
        └── Room
            └── Thread
                └── Message
```

It is an interactive design artifact, not a production Codexify integration. The topology, conversations, collaborators, Node availability, Project projection, publication, trust, and Galaxy discovery cards are synthetic examples. Runtime behavior, authorization, persistence, provider execution, synchronization, federation, and deployment were not evaluated.

## Source and design lineage

- Source artifact: `projection-ui-map/codexify_space_nz_florida_no_autoboot (1).html`
- Source artifact SHA-256: `0f5cc1be4614e9c3b9a24b03b2b741c0c714c058f2e2219156767756d7e06ee4`
- Inspected repository commit: `40e538cfd232bb30692dde1f9008e3fdeda3562b`
- Architecture handoff: `projection-ui-map/Codexify_Federation_Galaxy_Integration_Handoff.md`
- Originating design: Zac’s spatial Home / Room / Chat / World Spine interaction model, including draggable spatial cards, contextual inspection, document browsing, and an explicitly entered full-screen Galaxy. The original warm-paper palette remains comparison evidence rather than the current material treatment.
- Architecture translation: Resonant Jones’s HomeBase terminology and the proposed `User or Organization → HomeBase → Space → Room → Thread → Message` hierarchy.

The task text said a separately supplied `codexify_space_nz_florida_no_autoboot.html` should be compared with the repository reference. No separate HTML attachment was available in the supplied attachment directory, so no byte or material-difference comparison could be performed. The unchanged repository artifact above was used as the sole visual and interaction baseline.

## Codexify material translation

The standalone prototype defines a bounded local copy of the current Codexify material vocabulary. It imports no React, TypeScript, Tailwind, runtime stylesheet, production font, or dependency.

- Canonical geometry from `frontend/src/theme/index.ts` and the UI Token Constitution: `--radius-micro: 12px`, `--radius-tile: 19px`, `--card-radius: 19px`, `--edge-chrome: 6px`, `--frame: 1.5px`, `--bezel: 6px`, `--rim: 1.5px`, and `--card-pad: 12px`.
- Material and text vocabulary: translucent `--panel-bg`, `--panel-sheet: #1f1f22`, `--panel-border`, `--panel-bezel`, `--panel-sheet-border`, `--chip-bg: #262629`, `--chip-border`, `--text`, `--muted`, `--text-subtle`, `--surface-hover`, and `--surface-soft`.
- Accent vocabulary: `--accent: #8ec5ff` and `--accent-strong: #5ab7ff` drive selected cards, active controls, focus, and restrained glow.
- FrameCard visual contract, re-created rather than copied: one shared major radius, clipped decorative layers, translucent bezel, inset content face, depth shadow, selected accent rim, and a small hover lift.

Entity hues remain as secondary wayfinding on glyphs, route lines, and subtle card tint. Entity kind, stable ID, synthetic/proposed state, authority details, runtime evidence, and relationship evidence remain in accessible labels, native hover titles, the Directory, or the inspector instead of being printed across every default graph card.

## Reviewed repository sources

The prototype contains bounded excerpts or explanatory summaries from:

- `docs/architecture/home-room-thread-world-packet-framework.md` — proposed living framework; reviewed excerpt.
- `docs/architecture/space-runtime-and-federated-experience-architecture.md` — proposed living architecture; reviewed excerpt.
- `docs/architecture/atlas-v0-1-interaction-contract.md` — governing V0.1 planning contract; reviewed excerpt.
- `docs/architecture/architecture-atlas.md` — authoritative KB reading guide; explanatory summary.
- `docs/architecture/adr/055-threadspace-whispermesh-managed-service-boundary.md` — proposed ADR; reviewed excerpt.

Every source panel records its repository path, inspected commit, source status, content origin, representation class, and `runtime evidence: not evaluated`. The embedded material is a reading aid and does not replace the source documents.

## Interactive behavior

- Spatial Atlas with compact glyph/name/descriptor cards, discoverable relationship detail nodes, drag, pan, zoom, and Reset view.
- Searchable flat hierarchy and relationship directory equivalent to the graph destinations.
- Breadcrumb and Back navigation through HomeBase, Space, Room workspace, and Thread detail.
- A Room workspace that keeps Threads, documents/artifacts, and the source Project visibly separate.
- Two independently selectable fixture Threads in the Atlas Orientation Room, each with distinct fixture Messages and provenance labels.
- Full-width source-document reading that returns to the prior navigation, selection, search, and viewport state.
- Explicit Galaxy confirmation, a local-only pull-back transition into the larger field, and return to the exact previous local navigation, selection, search, and viewport state.
- Namespaced local presentation storage for viewport and card positions only, with fail-open fallback for missing, blocked, or malformed storage.
- Keyboard-operable controls, visible focus, reduced-motion handling, and a narrow-screen stacked fallback.

## Intentional departures from the source artifact

- Person-named Homes and mixed Home/node categories were replaced by stable prototype IDs and explicit entity kinds.
- Private-vault/archive fixture material was not carried forward.
- Misleading `Repo implemented`, `logged in`, `online`, and live-connection language was replaced by snapshot or simulation labels.
- The Room is no longer presented as one flattened conversation. Proposed Threads, fixture Messages, documents, and Project source are distinct.
- The active composer was replaced by an explicit unavailable state because this artifact has no provider or live collaboration path.
- Galaxy content was reduced to clearly synthetic archetypes and retains manual entry.
- Warm documentation-diagram surfaces were replaced by the current Codexify glass, bezel, inset-face, depth, chip, and accent grammar without changing the Atlas composition.
- Default graph taxonomy was reduced to a glyph, name, short descriptor, and selected/explore state. Architectural precision remains in the inspector, Directory, Sources, accessible labels, and hover detail.

## Architecture boundary and ADR impact

No ADR impact. This standalone prototype illustrates a proposed v2 hierarchy without accepting it as runtime architecture or superseding the Room-first V0.1 compatibility contract. The current contract still preserves one canonical backing Thread per Hosted Room. ADR-055 remains proposed and supplies a design constraint—connectivity is not collaboration authority—not implementation evidence.

## Validation and proof

Validation results recorded on 2026-09-10:

- `node --test projection-ui-map/rc-atlas-prototype.test.cjs` — passed, 15 tests, including local token geometry, clipped card material, progressive disclosure, and Galaxy transition contracts.
- `python3 scripts/validate_docs.py` — passed.
- `git diff --check` — passed before final staging.
- Desktop visual inspection — passed at 1440×1000. The untouched semantic baseline at commit `45ebd555bd5b66ee0f955cac70684d08150a1ac0`, originating prototype, reskinned Atlas, card hover, Directory, source reader, Galaxy, and 130% high-zoom card state were captured with Playwright and inspected at original resolution.
- Current Codexify comparison — current `theme/index.ts`, `AppShell.tsx`, `FrameCard.tsx`, `index.css`, and the UI Token Constitution supplied the geometry and material rules. Representative repository AppShell Guardian and dark Settings reference images were also inspected. This is material-family comparison, not a claim that a production AppShell runtime was exercised.
- Narrow viewport — passed at 390×844. The layout stacked navigation and the main experience with `scrollWidth === clientWidth === 390`; search remained visible and the icon-only Galaxy control retained `aria-label="Enter Galaxy"`.
- Card material — passed at default and 130% graph zoom. The card computed to a 19px outer radius with hidden overflow, a 16px inset face, intact hard clipping, readable text, selected accent rim, and restrained hover lift.
- Hierarchy navigation — passed. Atlas Orientation Room opened as a Room workspace with two distinct Threads, separate documents/artifacts, and separate Project source. The second Thread opened with two fixture Messages, the `thread-boundaries` inspector ID, and disabled Send.
- Empty search — passed. An unmatched query showed explicit entity and relationship recovery states; clearing the field restored the complete directory.
- Document expansion and return — passed. The hierarchy-framework source opened in a full-width material reader with path, status, snapshot representation, inspected commit, runtime-evidence boundary, readable hierarchy block, explicit source link, and Return control.
- Galaxy explicit entry and return — passed under normal motion. The initial page stayed local, the confirmation gate remained mandatory, and the Galaxy retained the illustrative/synthetic disclaimer. Return reproduced the recorded local state exactly: Atlas view, `home-rc` selection, empty query, and `translate(35px, 12px) scale(0.8)` viewport.
- Reduced motion — passed with Playwright media emulation. The media query matched, App/Galaxy transition durations computed to `1e-05s`, the Galaxy transform computed to `none`, and entry/return settled without the scale/depth effect.
- Storage failure and invalid-selection recovery — passed in the pure model suite; the storage format and recovery code were not changed by this visual slice.
- Console inspection — passed in a fresh final browser session with 0 errors and 0 warnings. A self-contained data-URL favicon prevents a browser-generated `/favicon.ico` 404.
- Network inspection — passed. The fresh final session recorded one static request, `GET http://127.0.0.1:8765/rc-atlas-prototype.html` → `200`; no external request was made.
- Direct `file://` browser opening — unchanged from the semantic baseline and not re-run. The prior in-app-browser URL safety policy rejected local-file navigation and was not bypassed; self-containment remains covered by static tests and localhost behavior.

### Fidelity ledger

| Comparison point | Source evidence | Implementation evidence | Result |
|---|---|---|---|
| Palette | Cream paper with muted entity hues | Dark Codexify panel/sheet/chip vocabulary with sky accent; entity hues remain subordinate | Intentional material translation |
| Shell | 292px left rail, compact topbar/tabs, spatial center, contextual right rail | Same information shell, recast as three clipped 19px glass frames with 6px scene gaps | Structure preserved |
| Canvas | Fine 28px grid, draggable cards, labeled dashed/solid edges | Same grid and routes; labels collapse to detail nodes until hover/focus/selection | Matched with progressive disclosure |
| Typography | System UI chrome with serif reading/inspection hierarchy | Codexify system UI hierarchy with monospace retained for IDs and paths | Intentional material translation |
| Card treatment | Thin colored borders, gentle radii, compact metadata | 19px bezel/rim shell, 16px inset face, depth shadow, accent selection, hover lift, clipped layers | Re-skinned, semantics preserved |
| Galaxy | Explicitly entered dark full-screen context | Explicit confirmation plus pull-back/expansion transition, synthetic disclaimer, exact local-state return, reduced-motion simplification | Extended within local simulation boundary |
| Responsive behavior | Source is primarily desktop-oriented | Added task-required stacked narrow fallback at 390×844 | Intentional extension |
| Source reading | Existing inspector/document browsing | Full-width, provenance-labeled reviewed excerpts with readable code/paths | Intentional extension |

The reskin changes material and information density rather than information architecture. No product, authority, availability, or runtime claim was added. The prototype remains visibly spatial and keeps the originating composition, while the canvas no longer reads like an always-expanded ADR index.

## Deferred work

Production HomeBase/Space/Room hierarchy, multi-thread Room persistence, Room publication, authorization, World Packet synchronization, federation, Work Graph, contributor task claiming, Linear/GitHub synchronization, intranet hosting, and deployment all require separate architecture-impact work and proof. This prototype changes none of those surfaces.
