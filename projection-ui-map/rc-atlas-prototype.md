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
- Originating design: Zac’s spatial Home / Room / Chat / World Spine interaction model, including warm paper-like surfaces, draggable spatial cards, contextual inspection, document browsing, and an explicitly entered full-screen Galaxy.
- Architecture translation: Resonant Jones’s HomeBase terminology and the proposed `User or Organization → HomeBase → Space → Room → Thread → Message` hierarchy.

The task text said a separately supplied `codexify_space_nz_florida_no_autoboot.html` should be compared with the repository reference. No separate HTML attachment was available in the supplied attachment directory, so no byte or material-difference comparison could be performed. The unchanged repository artifact above was used as the sole visual and interaction baseline.

## Reviewed repository sources

The prototype contains bounded excerpts or explanatory summaries from:

- `docs/architecture/home-room-thread-world-packet-framework.md` — proposed living framework; reviewed excerpt.
- `docs/architecture/space-runtime-and-federated-experience-architecture.md` — proposed living architecture; reviewed excerpt.
- `docs/architecture/atlas-v0-1-interaction-contract.md` — governing V0.1 planning contract; reviewed excerpt.
- `docs/architecture/architecture-atlas.md` — authoritative KB reading guide; explanatory summary.
- `docs/architecture/adr/055-threadspace-whispermesh-managed-service-boundary.md` — proposed ADR; reviewed excerpt.

Every source panel records its repository path, inspected commit, source status, content origin, representation class, and `runtime evidence: not evaluated`. The embedded material is a reading aid and does not replace the source documents.

## Interactive behavior

- Spatial Atlas with typed cards, labeled selectable edges, drag, pan, zoom, and Reset view.
- Searchable flat hierarchy and relationship directory equivalent to the graph destinations.
- Breadcrumb and Back navigation through HomeBase, Space, Room workspace, and Thread detail.
- A Room workspace that keeps Threads, documents/artifacts, and the source Project visibly separate.
- Two independently selectable fixture Threads in the Atlas Orientation Room, each with distinct fixture Messages and provenance labels.
- Full-width source-document reading that returns to the prior navigation, selection, search, and viewport state.
- Explicit Galaxy confirmation and return to the previous local presentation state.
- Namespaced local presentation storage for viewport and card positions only, with fail-open fallback for missing, blocked, or malformed storage.
- Keyboard-operable controls, visible focus, reduced-motion handling, and a narrow-screen stacked fallback.

## Intentional departures from the source artifact

- Person-named Homes and mixed Home/node categories were replaced by stable prototype IDs and explicit entity kinds.
- Private-vault/archive fixture material was not carried forward.
- Misleading `Repo implemented`, `logged in`, `online`, and live-connection language was replaced by snapshot or simulation labels.
- The Room is no longer presented as one flattened conversation. Proposed Threads, fixture Messages, documents, and Project source are distinct.
- The active composer was replaced by an explicit unavailable state because this artifact has no provider or live collaboration path.
- Galaxy content was reduced to clearly synthetic archetypes and retains manual entry.

## Architecture boundary and ADR impact

No ADR impact. This standalone prototype illustrates a proposed v2 hierarchy without accepting it as runtime architecture or superseding the Room-first V0.1 compatibility contract. The current contract still preserves one canonical backing Thread per Hosted Room. ADR-055 remains proposed and supplies a design constraint—connectivity is not collaboration authority—not implementation evidence.

## Validation and proof

Validation results recorded on 2026-09-10:

- `node --test projection-ui-map/rc-atlas-prototype.test.cjs` — passed, 12 tests.
- `python3 scripts/validate_docs.py` — passed.
- `git diff --check` — passed before final staging.
- Desktop browser journey — passed in the Codex in-app browser. Exercised HomeBase → Contributor Portal Space → Atlas Orientation Room → both sample Threads, Back navigation, and Room-state restoration.
- Desktop visual inspection — passed at 1440×1000. The repository source artifact and implementation were captured with the Playwright CLI and inspected at original resolution with the workspace image viewer.
- Narrow viewport — passed at 390×844 in the Codex in-app browser. The layout stacked the navigation and main experience without horizontal overflow; controls remained visible and named.
- Keyboard navigation — passed. The Directory view was activated with Enter, and controls, search, hierarchy rows, and document return remained native keyboard targets with visible focus styling.
- Empty search — passed. An unmatched query showed explicit entity and relationship recovery states; clearing the field restored the complete directory.
- Document expansion and return — passed. The hierarchy-framework source opened in a full-width reader with path, status, snapshot representation, inspected commit, runtime-evidence boundary, readable hierarchy block, explicit source link, and Back control. Returning preserved the Room context.
- Galaxy explicit entry and return — passed. The initial page remained local; Enter Galaxy opened a confirmation gate; the Galaxy identified itself as illustrative and synthetic; Return restored the prior Directory view and selected Project-projection edge.
- Reduced motion — passed with Playwright media emulation. `prefers-reduced-motion: reduce` matched, and computed animation and transition durations were both `1e-05s`.
- Storage failure recovery — passed. Both malformed namespaced storage and a browser-injected `Storage.getItem()` exception loaded successfully and recovered to `home-rc`. The pure model test also proves unrelated keys such as memberships are ignored.
- Invalid selection recovery — passed. Loading `#missing-selection` recovered to the sample HomeBase.
- Console inspection — passed with 0 errors and 0 warnings after prototype load and storage-failure exercises.
- Network inspection — passed. Three reload-related requests were observed, all `GET http://127.0.0.1:8765/rc-atlas-prototype.html`; no external requests were made.
- Direct `file://` browser opening — unrun. The in-app browser’s URL safety policy rejected local-file navigation, and that policy was not bypassed. Inline-script syntax, absence of external dependencies, and localhost static-server behavior were validated, but these are not presented as direct-file browser proof.

### Fidelity ledger

| Comparison point | Source evidence | Implementation evidence | Result |
|---|---|---|---|
| Palette | Cream paper, white panels, charcoal text, muted blue/green/amber/violet | Same token family and background temperature | Matched |
| Shell | 292px left rail, compact topbar/tabs, spatial center, contextual right rail | Same desktop container model and density | Matched |
| Canvas | Fine 28px grid, draggable cards, labeled dashed/solid edges | Same grid scale, spatial card grammar, pan/zoom/reset, selectable edge labels | Matched and extended |
| Typography | System UI chrome with serif reading/inspection hierarchy | Same system/serif/monospace role separation | Matched |
| Card treatment | Thin colored borders, gentle radii, restrained shadows, compact metadata | Same border, radius, shadow, type-glyph, and metadata language | Matched |
| Galaxy | Explicitly entered dark full-screen context | Explicit confirmation, dark full-screen synthetic discovery, preserved return state | Matched with claim-safe content |
| Responsive behavior | Source is primarily desktop-oriented | Added task-required stacked narrow fallback at 390×844 | Intentional extension |
| Source reading | Existing inspector/document browsing | Full-width, provenance-labeled reviewed excerpts with readable code/paths | Intentional extension |

The above-the-fold copy comparison found only intentional task-authorized changes: `RC Atlas`, contributor-orientation framing, Directory and Sources navigation, the simulation-boundary banner, hierarchy context, About, and explicit Galaxy labeling. No unrelated product or runtime claims were added. Material issues found during review—the banner covering header controls, an unlabeled narrow Galaxy control, a hidden narrow About label, and duplicated “reviewed” provenance wording—were repaired before closeout.

The implementation was faithfully verified against the repository source artifact. No remaining visual mismatch rises to a design-review blocker for this bounded contributor prototype.

## Deferred work

Production HomeBase/Space/Room hierarchy, multi-thread Room persistence, Room publication, authorization, World Packet synchronization, federation, Work Graph, contributor task claiming, Linear/GitHub synchronization, intranet hosting, and deployment all require separate architecture-impact work and proof. This prototype changes none of those surfaces.
