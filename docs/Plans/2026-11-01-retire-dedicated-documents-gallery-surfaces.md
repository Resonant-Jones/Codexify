# Retiring the Dedicated Documents and Gallery Surfaces — Plan

> **Status:** Plan (not yet implemented). Pre-implementation baseline.
> **Goal:** Remove the Documents and Gallery entries from the product menu bar while
> keeping both surfaces' code intact, and determine — with evidence — whether the
> dedicated `/documents` and `/gallery` surfaces become obsolete once the menu
> links are gone.
> **Grounding:** every claim below was read out of the working tree on 2026-11-01
> (branch `feat/auto-20261101-9e7a08eb`, HEAD `42db74479`). Locations are cited
> inline as `path:line`. **No source file has been modified by this document.**
> **Ratio boundary:** this document is a plan only. It authorizes no code change,
> no test change, no contract change, and no release-truth file change.

---

## 0. The question, and the short answer

**Question.** Once the Documents and Gallery links leave the menu bar, are the
dedicated surfaces obsolete — will no code call them?

**Short answer: no. Not yet.** Removing the menu-bar links leaves four live
callers behind (§3), one of which — the Dashboard "See All" buttons — is ordinary
user-facing navigation, not a dead path. The conditional in the request
("IF THAT is the case, THEN mark legacy") is therefore **not** met by the link
removal alone.

**The end state you want is real, reachable, and already prescribed.** The repo
says so itself in `docs/architecture/library-projects-spaces-product-surface-contract.md`:

> ### Documents and Gallery become Library modes
>
> The current **Documents** and **Gallery** application surfaces should converge
> into Library presentation modes rather than remain permanent peer application
> destinations.

That contract is marked *user-approved product direction*, last updated
2026-10-16, with the four-filter taxonomy (All | Images | Documents | Widgets)
approved the same day. So this work is not a new direction — it is the
execution of a direction already approved. The plan below is sequenced to make
the code match the contract without ever breaking a bookmark.

**One premise needs correcting.** The working hypothesis was that the Library
representations and the dedicated representations are "just two different
versions projecting from the same database." That is **true for Documents** and
**false for Gallery**:

- The Documents page and Library's Documents filter read the **same endpoint with
  the same scope** and render the **same component**.
- The Gallery page **never reads the server at all**. Library's Images filter does.

That asymmetry decides which of the two surfaces is actually legacy (§2.3).

---

## 1. What exists today (verified 2026-11-01)

### 1.1 Surface map

| Surface | Route | Shell | Center component | Data source |
|---|---|---|---|---|
| **Documents** | `/documents` | DocumentsSidebar \| center \| workspace drawer | `DocumentsView` | `GET /media/document-artifacts` + `documentsScope` |
| **Library** | `/library` | **identical** DocumentsSidebar \| center \| workspace drawer | `LibraryView` | `GET /media/images` (two `tag` calls) + `GET /media/document-artifacts`, same scope |
| **Gallery** | `/gallery` | single `FrameCard` | inline grid written inside AppShell | **none — browser-local only** |

Citations:

- `/documents` branch — `frontend/src/components/persona/layout/AppShell.tsx:3999-4258`
- `/library` branch — `frontend/src/components/persona/layout/AppShell.tsx:4240-4257`
- `/gallery` branch — `frontend/src/components/persona/layout/AppShell.tsx:4264-4328`
- Library reuses the Documents component —
  `frontend/src/components/library/LibraryView.tsx:3-4` (imports), `:380-384` (renders `<DocumentsView>`)
- Library reuses the gallery grid — `LibraryView.tsx:3` (imports `GalleryGrid`)
- Library's transport — `frontend/src/components/library/libraryResourceProjection.ts:222-241`

### 1.2 The two shells are already identical

`/documents` and `/library` render **the same left rail, the same center lane,
and the same workspace drawer**. Both mount `SidebarRoot` with the same thread
and project scope handlers (`AppShell.tsx:4207-4223` for Library,
`:4073-4089` for Documents) and both resolve `workspaceProjectId` from
`documentsScope` (`AppShell.tsx:3083-3086`).

The **only** difference between the two routes is the component in the center
column: `DocumentsView` versus `LibraryView`.

### 1.3 Library's filter is not addressable — the enabling gap

`LibraryView` holds its filter in component-local state
(`frontend/src/components/library/LibraryView.tsx:120`), and there is **no**
query-parameter support anywhere in `AppShell` (no `URLSearchParams` /
`location.search` usage). So today there is no way to address
"Library ▸ Documents" or "Library ▸ Images" as a URL.

This matters for sequencing: any plan that points existing callers at a
*specific* Library filter has to close this gap first (§4, Phase 2).

---

## 2. Documents vs. Gallery — they are not the same kind of thing

### 2.1 Documents: redundant, not distinct

Library's Documents filter and the dedicated Documents page agree on:

| | `/documents` page | Library → Documents |
|---|---|---|
| Transport | `GET /media/document-artifacts` | same |
| Scope query | `getDocumentScopeQuery(documentsScope)` | same (`libraryResourceProjection.ts:28-30`) |
| Rendered component | `DocumentsView` | `DocumentsView` — *the same file* |

Evidence: `AppShell.tsx:1938` and `libraryResourceProjection.ts:223` are the same
path; `LibraryView.tsx:380-384` renders `<DocumentsView>` with `onOpenInThread`
and `onDeleteDocument` threaded through.

The dedicated page adds exactly one thing Library does not: *documents only, with
no filter row*. Everything else — data, scope, component, shell — is shared.

**Therefore `DocumentsView` itself must not be marked legacy.** It is live,
shared, and it is what Library's Documents filter renders. Marking it legacy
would be factually wrong and would mislead the next reader.

### 2.2 Gallery: strictly weaker than Library's Images filter

The Gallery page is fed **entirely from browser-local state**. In
`AppShell.tsx` there are exactly two authenticated reads: `GET /api/projects`
(`:1878`) and `GET /media/document-artifacts` (`:1938`). **There is no
`/media/images` read.**

The gallery state is assembled from:

- `localStorage["cfy.gallery"]` — `AppShell.tsx:2567-2597`
- three seeded demo assets, `SEEDED_GALLERY_ITEMS` (`:645-669`) — `/peekaboo-demo/*`
- in-session upload events only — `cfy:gallery:add` (`:2691-2718`) and the
  uploader's `onImages` (`:2745+`)

Consequences, each a real user-visible difference:

1. The Gallery page **ignores project/thread scope entirely**.
2. It **cannot show an image uploaded on another device or browser** — only what
   was uploaded in this browser session.
3. It **renders three seeded demo assets as gallery tiles**, which Library's
   projection explicitly rejects as `synthetic_record`
   (`libraryResourceProjection.ts:298-302`).

Library's Images filter, by contrast, is server-authoritative, scope-bound, and
covers both uploaded and generated families
(`libraryResourceProjection.ts:230-237`).

**So Gallery is the genuinely legacy projection.** Anything visible in Gallery
is already visible in Library, and Library is strictly more complete.

### 2.3 One file is already dead

`frontend/src/components/gallery/GalleryView.tsx` (386 lines) is imported
**only** by its own tests (`components/gallery/__tests__/GalleryView.test.tsx:32`,
`tests/gallery_auth.spec.tsx:4`) and as a *type* provider
(`LibraryView.tsx:2` — `import type { GalleryItem }`). The `/gallery` route does
not render it; `AppShell` draws its own inline grid instead
(`AppShell.tsx:4282-4318`).

It is **already dead production code** and is not made deader by removing a menu
link. See Phase 4 — this one is a deletion candidate, not a "mark legacy"
candidate, because marking dead code as legacy preserves a false claim.

---

## 3. Who still calls the dedicated surfaces after the menu links go

Removing the two desktop pills at `AppShell.tsx:3888-3907` leaves these callers
alive:

1. **Dashboard "See All" buttons** —
   `components/dashboard/DashboardView.tsx:443` (Recent Documents card) and
   `:509` (image gallery card), wired at `AppShell.tsx:4462-4463` and
   `:4475-4476`. This is ordinary user navigation.
2. **Phone app menu** — `PHONE_NAVIGATION_DESTINATIONS`
   (`AppShell.tsx:284-291`) lists Documents and Gallery as **primary**
   destinations, consumed at `AppShell.tsx:3595` (`MobileAppSidebarDrawer`) and
   `:4390` (Guardian app sidebar). This is the same product menu on a phone.
3. **Deep links** — `resolveViewFromPathname` still maps `/documents` and
   `/gallery` (`AppShell.tsx:332-334`); `pathForView` still emits them
   (`:346-351`). Bookmarks and shared URLs keep working.
4. **`cfy:project-kb:open` listener** — `AppShell.tsx:2720-2743` routes to
   "documents". **No production dispatcher remains**: the sidebar's
   "Open Project Knowledge Base" action was replaced by a dismissible *notice*
   (`components/sidebar/SidebarRoot.tsx:623-663`). Only
   `AppShell.test.tsx:1393` dispatches the event. This is a dangling listener —
   a real defect that is independent of the menu change and worth reporting on
   its own.
5. **`cfy.lastView`** — written on every view change (`AppShell.tsx:1509`) and
   read back for any unrecognized pathname (`:1381-1384`). A stale
   `cfy.lastView: "gallery"` restores the Gallery view on an unknown URL.

---

## 4. The plan

Sequenced so that **nothing breaks at any point**: every phase is shippable on
its own, and the menu-bar change (the actual ask) lands first and independently.

### Phase 1 — Remove the menu-bar links (the ask; no modules removed)

- `AppShell.tsx:3888-3907` — delete the two `PhonePressButton` nav pills
  (Documents, Gallery). The desktop rail becomes
  **Guardian | Dashboard | Library | Lens**.
- `AppShell.tsx:284-291` — drop the `documents` and `gallery` entries from
  `PHONE_NAVIGATION_DESTINATIONS` (the phone app menu is the same menu on a
  different form factor; leaving them means a phone user still has a top-level
  Documents/Gallery destination).
- Routes `/documents` and `/gallery` **stay live**. `DocumentsView`,
  `GalleryGrid`, `GalleryView` stay in place, untouched.

**Test impact (Phase 1):**

| File | Line(s) | What changes |
|---|---|---|
| `components/persona/layout/__tests__/AppShell.test.tsx` | 1198-1224 | nav-order assertion → `["Guardian","Dashboard","Library","Lens"]`; drop the two `getByRole("button", {name:"Documents"/"Gallery"})` expectations |
| same | 862-870 | `applicationDestinations` equality assertion |
| same | 893-906 | two "Documents" button-presence assertions |
| same | 1426 | clicks the "Documents" nav button to switch views → retarget to "Library" |
| `components/persona/layout/__tests__/MobileAppSidebarDrawer.test.tsx` | 12-18, 133-137 | destination list + order assertion |
| `components/persona/layout/__tests__/GuardianMobileSidebarAppMenu.test.tsx` | 20-26, 271-275 | destination list + order assertion |
| `components/persona/layout/__tests__/GuardianChatWithSidebar.mobile-nav.test.tsx` | 23-29 | destination list |

These last three are *test-local* fixture arrays, not production code — they
mirror `PHONE_NAVIGATION_DESTINATIONS` so they must be updated to match.

**Not affected** (they exercise the routes, not the menu, and the routes stay):
`AppShell.test.tsx:951-956` (narrow-route frame shell), `:1008-1012`,
`:1129-1136` (deep links), `:1383-1406` (`cfy:project-kb:open`).

### Phase 2 — Make the Library filter addressable (enabler)

Add `?filter=all|images|documents|widgets` support to `/library`, so
`/library?filter=documents` is a real, shareable address.

- Read the filter from the query string on entry; write it back on change.
- Validate against `LIBRARY_FILTERS` (`libraryResourceProjection.ts:37-41`);
  an unknown value falls back to `all` rather than erroring.
- `LibraryView.tsx:120` stops being the sole owner of the filter; the URL
  becomes the source of truth so a deep link and a click agree.

Without this, Phase 3 has nowhere correct to point the Dashboard buttons.

### Phase 3 — Close the remaining callers

| Caller | Action |
|---|---|
| Dashboard "Recent Documents → See All" (`DashboardView.tsx:443`) | → `/library?filter=documents` |
| Dashboard image card "See All" (`DashboardView.tsx:509`) | → `/library?filter=images` |
| Phone app menu | already handled in Phase 1 |
| `cfy:project-kb:open` listener (`AppShell.tsx:2720-2743`) | no dispatcher exists — either remove the listener + its test, or retarget it to `/library?filter=documents` and keep it. **Recommend: retarget**, because the event name is a published contract surface and a future dispatcher may exist. |
| Deep links `/documents`, `/gallery` | leave working in Phase 3 (no redirect yet) so bookmarks never break; redirect to `/library?filter=documents` / `/library?filter=images` **after** Phase 2 is proven |
| `cfy.lastView` | if `/documents` and `/gallery` are retired, ensure the persisted value can no longer resurrect them (the write at `:1509` and the read at `:1381-1384` are the two lines to reconcile) |

### Phase 4 — Mark legacy, truthfully (only after Phase 3)

This is where the "mark legacy" request lands — and it needs a distinction that
the request's phrasing currently blurs:

- **Mark legacy:** the two *page shells* in `AppShell.tsx` — the
  `view === "documents"` branch (`:3999-4258`) and the `view === "gallery"`
  branch (`:4264-4328`) — once nothing navigates to them. A `LEGACY:` header
  comment stating: superseded by Library per
  `docs/architecture/library-projects-spaces-product-surface-contract.md`;
  retained only for deep-link compatibility; no menu entry; not the
  authoritative projection.
- **Do NOT mark legacy:** `frontend/src/components/documents/DocumentsView.tsx`.
  It is live and shared — it is what Library's Documents filter renders
  (§2.1). Marking it legacy would be a false claim about live code.
- **Delete, don't mark:** `frontend/src/components/gallery/GalleryView.tsx`.
  It is already unreferenced in production (§2.3). "Legacy" would dignify
  dead code. Deleting it also requires removing
  `components/gallery/__tests__/GalleryView.test.tsx` and
  `tests/gallery_auth.spec.tsx`, or folding their assertions into the
  AppShell-level coverage that actually exercises the live gallery path.

### Phase 5 — Contract + proof

- Update `docs/architecture/library-projects-spaces-product-surface-contract.md`
  to record that the convergence was executed and to name the surviving
  compatibility surface.
- Record a short proof note under `docs/architecture/proofs/` stating what was
  exercised (deep link → redirect, Dashboard See All → filtered Library, menu
  absence) and what remains **code-path only** rather than runtime-proven.

---

## 5. Options for how far this pass goes

**Option A — links only.** Phase 1. The dedicated pages become unlinked but stay
reachable via deep link and the Dashboard "See All" buttons. Nothing is
labelled legacy, because nothing is legacy yet. Smallest blast radius; leaves
two projections alive.

**Option B — full retirement (recommended).** Phases 1-5. The dedicated pages
stop being navigable, Library becomes the single projection, and the page
shells are labelled legacy against a contract that already says they should be.
Larger, but it finishes the job the contract started and leaves the codebase
with one honest story instead of three.

**Option C — Gallery first, Documents later.** Do Phase 1 for both, but retire
only `/gallery` (which §2.2 shows is strictly weaker than Library) and leave
`/documents` as a deliberate, unlinked, second documents surface. Preserves a
documents-only view that Library's filter row does not currently reproduce in
one click. Not recommended: it keeps the ambiguous "two documents surfaces"
state open indefinitely.

---

## 6. Risks and honest limits

- **This plan is code-path evidence, not runtime proof.** Nothing here has been
  exercised in a live browser or against a running backend. Phases 1-3 change
  user-visible navigation; they should be verified in the running app before
  being called done.
- **The `cfy:project-kb:open` dispatcher may exist outside the repository**
  (an older build, a bookmarklet, an integration). The repo contains no
  dispatcher; that is the whole of the evidence.
- **`cfy.gallery` local data is user-visible state.** Retiring the Gallery
  surface without a migration path discards a browser-local cache that the
  server projection may not fully replicate (seeded demo items and any
  browser-session-only uploads). Worth checking against real account data
  before Phase 3's redirect lands.
- **Backend is not affected.** `/media/images` and `/media/document-artifacts`
  are shared by Library, the workspace shelf, and the chat attachment flow.
  No backend route, schema, or migration is touched by any phase here.
