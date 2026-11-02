# Retiring the Dedicated Documents and Gallery Surfaces — Plan

> **Status:** Plan (approved in scope; not yet implemented). Pre-implementation baseline.
> **Goal:** Remove the Documents and Gallery entries from the product menu bar and
> converge user-facing browsing into Library, while establishing — with evidence —
> whether the dedicated `/documents` and `/gallery` application destinations
> become obsolete, and on what terms.
> **Scope decision (Resonant, 2026-11-01):** **full retirement** (Option B below) —
> Phases 1-5, not links-only. Resonant's stated reason: the Dashboard is itself
> slated to become a Feed (an activity feed), and the Dashboard currently feels
> redundant because Library already embeds several of the same projections into a
> unified interface. See §6.
> **Ownership boundary (clarified 2026-11-01):** Library replaces the *application
> destinations* Documents and Gallery. It does **not** replace the underlying
> **document and image archival resource families**. Documents and Images remain
> independently meaningful resource concepts backed by their existing canonical
> persistence, ownership, provenance, and retrieval systems. Full retirement
> therefore retires **navigation and page shells**, never archives, server-backed
> capabilities, shared Library presentation components, or canonical
> persistence/provenance relationships. See §7.
> **Refinement (Resonant, 2026-11-01, after accepting the reconciliation):**
> three technical details are carried into the later safety and cleanup work —
> (a) `cfy.gallery` is **browser-scoped, not account-scoped** (§2.2.1a);
> (b) the content classification is by **verified server counterpart**, with the
> introducing event kept as an attribute (§2.2.1); (c) the browser-local safety
> gate governs the `/gallery` route and local-only content, and **does not**
> block the `GalleryView.tsx` cleanup (§2.2.2, §2.3, Phase 4). None of these
> delays Phase 1.
> **Grounding:** every claim below was read out of the working tree on 2026-11-01
> on branch `feat/auto-20261101-9e7a08eb` (application source inspected at
> `42db74479`; the only commits ahead are plan-only — `3ed073996`, `b64a3df02`).
> Locations are cited inline as `path:line`. **No application source file has
> been modified by this document.**
> **Evidence posture:** code-path evidence and documented contract. Nothing here
> is live-runtime proof, and this document must not be read as promoting any
> plan finding into runtime qualification.
> **Ratio boundary:** this document is a plan only. It authorizes no code change,
> no test change, no contract change, no backend/schema/API change, no release
> claim, and no Feed implementation.

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
- The Gallery page **never reads the server for images at all**. Library's Images
  filter does.

That asymmetry decides which of the two surfaces is actually legacy (§2.2), and
it is the reason this plan carries a browser-local data safety gate (§2.2.2)
rather than treating Gallery as simply superseded.

**A second, correction-in-place note.** An earlier draft of this plan also
claimed that *anything visible in Gallery is already visible in Library*. That
claim is **withdrawn** — it holds for server-backed content only. The Gallery
page can display browser-local content (including images whose upload failed
and was never persisted) that a server projection provably cannot show. §2.2.1
supersedes the claim with a classification by **verified server counterpart**,
§2.2.1a records that the local store is **browser-scoped rather than
account-scoped**, and §2.2.2 installs a hard safety gate before any `/gallery`
redirect or removal of access to local-only content.

---

## 1. What exists today (verified 2026-11-01)

### 1.1 Surface map

| Surface | Route | Shell | Center component | Data source |
|---|---|---|---|---|
| **Documents** | `/documents` | DocumentsSidebar \| center \| workspace drawer | `DocumentsView` | `GET /media/document-artifacts` + `documentsScope` |
| **Library** | `/library` | **identical** DocumentsSidebar \| center \| workspace drawer | `LibraryView` | `GET /media/images` (two `tag` calls) + `GET /media/document-artifacts`, same scope |
| **Gallery** | `/gallery` | single `FrameCard` | inline grid written inside AppShell | **none — browser-local state only** (four content classes; see §2.2.1) |

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

The same holds for the other shared Library presentation components:

- **`GalleryGrid`** (`frontend/src/components/gallery/GalleryGrid.tsx`) is
  rendered by `LibraryView.tsx:3`. It is a live Library component and is
  **not** a retirement target.
- **The server-backed Images projection** (`libraryResourceProjection.ts`) is the
  canonical image-family projection and **is not** a retirement target.
- **The document and image archival resource families themselves** — the
  `UploadedDocument` / document-artifact / image records, their ownership,
  provenance, and retrieval paths — are **out of scope entirely**. This plan
  retires application destinations, not resources.

Preserving the **Gallery concept** (a visual image view inside Library, per the
governing contract) does **not** require preserving the specific file
`GalleryView.tsx` — see §2.3 and Phase 4 for the conditional, dependency-gated
treatment.

### 2.2 Gallery: a different projection, with a browser-local residue

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

#### 2.2.1 Correction: Gallery content is **not** fully represented in Library

> **Superseded claim.** An earlier draft of this plan asserted that *anything
> visible in Gallery is already visible in Library, and Library is strictly more
> complete.* **That claim is not established and is withdrawn.** It holds for
> server-backed content only.

Library's Images filter is strictly more complete **for records that exist on
the server**. It is not a superset of everything the Gallery page can display.

**Classification axis: does the item have a verified server counterpart?** The
introducing *event* is a secondary attribute, not a class in its own right —
the same item can be both an in-session event and a server-backed record, or
both an in-session event and browser-local-only. Classifying by event would
double-count and mislabel. The decisive question for the safety gate is
whether a server counterpart **can be verified**:

| Axis | How it is determined | Server counterpart? | Visible in Library → Images? |
|---|---|---|---|
| **Server-backed** | `src` resolves to a server-hosted asset **and** the item carries a verifiable server identity (`src_url` / id) — e.g. the uploader's success path (`useUploader.ts:487-488`) | Yes | Yes — same family, same records |
| **Browser-local-only** | `src` is a local `data:` URL or other non-server path, **or** no server counterpart can be verified | **No** | **No** |
| **Synthetic / seeded** | `SEEDED_GALLERY_ITEMS` (`:645-669`), `mock: true`, `/peekaboo-demo/*` | No — synthetic | No — explicitly rejected as `synthetic_record` |

**Event provenance is retained as an attribute, not as a class.** For
reference, the items arrive through three mechanisms: the uploader's success
and failure paths, the `cfy:gallery:add` window event (`:2691-2718`), and the
persisted `cfy.gallery` cache. A *successful* upload is simultaneously an
in-session event **and** server-backed. A *failed* upload is simultaneously an
in-session event **and** browser-local-only. Only the server-counterpart axis
determines whether content is at risk.

**Browser-local-only content is the real data-loss risk.**
`useUploader.ts:486-494` shows that when an image upload *fails*, the uploader
does not discard the file — it falls back to a local `data:` URL and marks the
item `mock: true`:

```ts
// Use server response URL (persisted) or fall back to local data URL (preview-only)
const imageUrl = uploadedOk
  ? toAbsoluteMediaUrl(uploadedImage.src_url)
  : (await readAsDataUrl(f));
imgs.push({ src: imageUrl, prompt: f.name, mock: !uploadedOk, ... });
```

A user whose upload failed while the upload endpoint was unhealthy therefore has
an image that exists **only** as a browser-local `data:` URL in `cfy.gallery`.
Library, being a server projection, provably cannot show it.

#### 2.2.1a `cfy.gallery` is browser-scoped, not account-scoped

`localStorage` belongs to a **browser origin and profile**. It is not
inherently bound to an authenticated Codexify account. Three consequences the
safety gate must respect:

1. **Server-side account inspection cannot establish that every browser has
   been checked.** A gate phrased as "enumerate `cfy.gallery` per account" is
   not answerable from the server. The enumeration is inherently a
   browser-side check, and it can only ever cover the browser performing it.
2. **The same browser profile may carry items from more than one authenticated
   account.** Unless the application explicitly isolates local state by
   account, locally retained images can outlive or cross an account switch.
3. **Browser ownership and authenticated resource ownership are different
   things.** Remediation must distinguish them: a locally retained image must
   **never** be automatically migrated into whichever account happens to be
   logged in at remediation time. Any transfer requires explicit, attributable
   user action.

The safety gate below is therefore written as a browser-side inspection with an
explicit account-boundary rule, not as a server-side account query.

**When this residue is visible.** `AppShell.tsx:2914-2917` decides what the
Gallery page renders:

```ts
const galleryItemsToRender = useMemo(() => {
  const realGallery = gallery.filter((item) => !item.mock);
  return realGallery.length > 0 ? realGallery : gallery;
}, [gallery]);
```

So mock items — which include the failed-upload data URLs — are **hidden when
any server-backed item exists**, and **shown (with a visible "Mock" badge,
`:4303-4315`) when the set contains only mock items**. The content is persisted
in `cfy.gallery` either way; visibility depends on whether other items exist.

Practical bound: `cfy.gallery` is `localStorage` (`:2588-2596`), and the write
path trims on quota error, so the volume of browser-local-only image data is
bounded by the storage quota. That bounds the blast radius — it does not make
the loss acceptable, and it does not make the residue non-existent.

#### 2.2.2 Safety gate (prerequisite to retiring the `/gallery` route or removing local-only content)

**Scope of the gate.** The gate governs exactly two things:

- redirecting the `/gallery` route, and
- removing access to browser-local-only gallery content.

**The gate does *not* govern deletion of `GalleryView.tsx`.** Per §2.3, that
component is not the code that renders browser-local images today — the inline
Gallery branch inside `AppShell` is. Deleting an otherwise-unused component is
dead-code cleanup, and coupling it to a potentially complicated browser-data
migration would create a dependency that serves neither concern. The gate and
the `GalleryView.tsx` cleanup are therefore **independent work items**; see
Phase 4, where the deletion conditions deliberately omit the gate.

**No redirect of `/gallery`, and no removal of access to browser-local-only
content, may proceed until this gate is discharged.** The gate is a
**browser-side** inspection (see §2.2.1a), not a server-side account query, and
it must establish against real data rather than by inspection alone:

1. **Does browser-local-only user content exist?** Enumerate the entries in
   `cfy.gallery` **in the browser being inspected** and classify each by the
   server-counterpart axis in §2.2.1 — server-backed vs browser-local-only vs
   synthetic. Because the store is browser-scoped (§2.2.1a), this is a
   per-browser inspection; it cannot be satisfied by an account-level server
   query, and a negative result covers only the browser that produced it.
2. **Is it visible today, or merely retained?** Using the
   `realGallery.length > 0` rule above, determine whether affected items are
   currently displayed or only stored-but-hidden — because "stored but hidden"
   still means the user believes the content is reachable.
3. **Which account does it belong to, if any?** Because the store is not
   account-scoped, determine whether the affected entries are attributable to
   the currently authenticated account at all. Entries that are not
   attributable must be treated as belonging to the browser, not to the signed-in
   account.
4. **What remediation is required?** Options, to be decided by the user, not by
   this plan:
   - a one-time export/download of browser-local-only images before redirect;
   - a retained local-only compatibility route;
   - an explicit, consented disclosure of what will disappear;
   - re-upload by the user.
5. **Recording.** The gate result — including a negative result, and including
   the browser scope it covered — must be recorded as a dated note before
   Phase 3's redirect lands.

**Account-boundary rule.** Remediation must distinguish browser ownership from
authenticated resource ownership. A browser-local image must **never** be
automatically migrated into, or claimed by, whichever account happens to be
logged in. Any transfer requires explicit, attributable user action.

**No silent data loss and no silent disappearance of user-created content is
acceptable.** This gate is a hard prerequisite for the two things it governs —
not a risk to be accepted and moved past. **No migration is designed or
implemented in this document.**

#### 2.2.3 Implemented strategy: a per-browser gate on the `/gallery` alias

**Recorded 2026-11-01.** The gate above is now a **runtime, per-browser
decision** rather than a one-off inspection. The `/gallery` alias to
`/library?filter=images` is applied **only when the browser performing the
navigation can establish that nothing browser-local would be hidden**. When it
cannot, `/gallery` stays functional and is not redirected.

The decision is made by `isGalleryCanonicalizationSafe()` in
`frontend/src/components/persona/layout/AppShell.tsx`. It:

- **reads** `cfy.gallery` and never writes, migrates, uploads, attributes, or
  removes anything;
- **fails closed** — an unreadable store, malformed JSON, a non-array payload,
  or any unclassifiable entry keeps the legacy Gallery reachable;
- is a statement about **this browser only**. It never asserts that any other
  browser, profile, or account is free of residue, and it never infers
  ownership from the signed-in account.

Each persisted entry is classified by whether it could represent content
**without a server counterpart**:

| Class | Rule | Effect |
|---|---|---|
| `seeded` | A **known** demonstration asset, recognized by identity against the seeded asset list | safe |
| `server` | A server address (absolute `http(s)://`, protocol-relative, or root-relative) and not flagged `mock` | safe |
| `local` | A `data:` or `blob:` reference — no server projection can ever retrieve it | **retains Gallery** |
| `unknown` | Any other value, including an arbitrary `mock: true` entry on an unrecognized path | **retains Gallery** |

**`mock: false` is never treated as proof that an item exists on the server** —
only the address is. **Arbitrary `mock: true` entries are not treated as
synthetic** — only the known demonstration assets are. Both rules fail toward
retaining the Gallery.

The same rule governs a persisted `cfy.lastView = "gallery"`: a safe browser
restores Library/Images, a browser with residue or uncertain state restores the
Gallery destination. The completed Documents persisted-view normalization is
unchanged.

**What this strategy does not establish.** A safe decision in one browser says
nothing about any other browser, profile, or account. The gate is therefore
**not** the global absence-of-content proof the plan originally contemplated —
it is a local guard that keeps the legacy Gallery reachable exactly where
browser-local content might be hidden. The account-scoped sweep across browsers
remains outstanding; see the dated gate note
`docs/architecture/proofs/2026-11-01-gallery-browser-local-route-gate.md`.

### 2.3 `GalleryView.tsx`: unreferenced in production, but not dependency-free

`frontend/src/components/gallery/GalleryView.tsx` (386 lines) is imported
**only** by its own tests (`components/gallery/__tests__/GalleryView.test.tsx:32`,
`tests/gallery_auth.spec.tsx:4`) and as a *type* provider. The `/gallery` route
does not render it; `AppShell` draws its own inline grid instead
(`AppShell.tsx:4282-4318`).

Three dependencies must be accounted for before it can be called free:

1. **A live type dependency.** Two different `GalleryItem` types exist:
   - `frontend/src/types/ui.ts:69` — `{ src, prompt, mock? }`, consumed by
     `AppShell.tsx:83` and `DashboardView.tsx:7`;
   - `frontend/src/components/gallery/GalleryView.tsx:17` — a richer shape,
     consumed by **`GalleryGrid.tsx:13`** and **`LibraryView.tsx:2`**, both
     type-only imports.

   Deleting `GalleryView.tsx` without first relocating that exported type
   breaks two **live Library components**. The type must be moved (for example
   into `types/ui.ts` or a dedicated gallery types module) as a prerequisite.
2. **Test ownership.** `components/gallery/__tests__/GalleryView.test.tsx` and
   `tests/gallery_auth.spec.tsx` exercise this component. If it is removed,
   those assertions must be preserved by folding them into the AppShell-level
   coverage that exercises the live gallery path — otherwise coverage silently
   drops rather than moving.
3. **A server-backed implementation it carries.** `GalleryView.tsx:96-149`
   contains a `/api/media/images` fetch across the `uploaded` / `generated` /
   `unclassified` tags with its own dedupe and filter UI. That implementation is
   **superseded by**, not unique to, this file: `libraryResourceProjection.ts`
   performs the same two-family server-backed image projection for Library.
   Deleting the file therefore does **not** remove the server-backed Images
   capability — but that substitution must be confirmed, not assumed.

**So `GalleryView.tsx` remains a conditional deletion candidate, not a
"mark legacy" candidate** — marking unreferenced code as legacy dignifies a
false claim, and deleting it without the type relocation and test-folding above
would break live Library components. See Phase 4, which is explicitly
evidence-gated.

**This deletion is independent of the §2.2.2 browser-local safety gate.**
`GalleryView.tsx` is not the code that renders browser-local images today; the
inline Gallery branch inside `AppShell` is (§2.2.1). The gate governs the
`/gallery` route and access to local-only content — not the removal of an
otherwise-unused component whose dependencies have been resolved.

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
   "documents". **No production dispatcher was found inside this repository**:
   the sidebar's "Open Project Knowledge Base" action was replaced by a
   dismissible *notice* (`components/sidebar/SidebarRoot.tsx:623-663`), and
   only `AppShell.test.tsx:1391-1392` dispatches the event. **This is not evidence
   that the event is dead.** A window event is a published contract surface that
   may be dispatched by an older build, a bookmarklet, a native shell, or an
   integration outside this repository. The listener must therefore be
   **retargeted, not removed** — removal is only defensible if the dispatcher's
   absence is established beyond the repository boundary.
5. **`cfy.lastView`** — written on every view change (`AppShell.tsx:1509`) and
   read back for any unrecognized pathname (`:1381-1384`). A stale
   `cfy.lastView: "gallery"` restores the Gallery view on an unknown URL.

---

## 4. The plan

The dependency order is fixed and each phase is independently verifiable:

1. **Phase 1** — remove the desktop and mobile menu destinations.
2. **Phase 2** — make Library filters URL-addressable.
3. **Phase 3** — retarget the remaining navigation callers and establish safe
   compatibility redirects.
4. **Phase 4** — classify or remove redundant frontend shells and unused
   components, after dependency verification.
5. **Phase 5** — update the governing contract and capture proof.

Sequenced so that **nothing breaks at any point**: every phase is shippable on
its own, and the menu-bar change (the actual ask) lands first and independently.
Phase 3's `/gallery` alias is the single exception — it is blocked until the
§2.2.2 safety gate is discharged. Phase 4's deletions are evidence-gated and
may legitimately conclude "retain" for every candidate.

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

**Route-retention constraint for Phase 1 (load-bearing).** Removing Gallery from
the menu does **not** delete browser-local-only images — it only makes them
harder to discover. So `/gallery` **must remain functional and reachable
throughout Phase 1**, by direct URL, so that any user who needs their
browser-local content can still reach it. The route-retention requirement is
what makes Phase 1 safe to land before the §2.2.2 safety gate has run.

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

**Implemented convention (2026-11-01).** Phase 2 is implemented; this is the
convention Phase 3 must inherit for its compatibility redirects.

- The canonical address for the default filter is **`/library`**. `?filter=all`
  is accepted and resolves to `all`, but the shell never emits it. Every
  non-default filter is emitted as `?filter=<value>`.
- **The URL is the only source of the filter.** `LibraryView` holds no filter
  state at all — it receives `filter` as a prop and reports changes through
  `onFilterChange`. The shell writes the change to the URL and its route sync
  reads the filter back from `window.location.search` on every route change, so
  the address bar and the rendered filter cannot disagree.
- A filter change pushes a **new history entry**, so Back/Forward moves between
  filters.
- The mapping lives in `frontend/src/components/library/libraryFilterRoute.ts`
  (`parseLibraryFilter`, `readLibraryFilterFromSearch`,
  `buildLibraryFilterSearch`) — deliberately outside both the resource
  projection (which owns the taxonomy) and the view (which owns presentation).
- Scope, authorization, and the resource projections are unchanged: a filter
  change re-reads the same scope and never re-scopes a request.

### Phase 3 — Close the remaining callers, with safe compatibility redirects

| Caller | Action |
|---|---|
| Dashboard "Recent Documents → See All" (`DashboardView.tsx:443`) | → `/library?filter=documents` (navigation retarget only — the card and its endpoint stay; see §6) |
| Dashboard image card "See All" (`DashboardView.tsx:509`) | → `/library?filter=images` (same) |
| Phone app menu | already handled in Phase 1 |
| `cfy:project-kb:open` listener (`AppShell.tsx:2720-2743`) | **Retarget** to `/library?filter=documents` and keep the listener. It is a published window-event contract surface; the absence of an in-repo dispatcher does not establish that no dispatcher exists. Removal requires evidence from beyond the repository boundary, not from this repository alone. |
| Deep link `/documents` | Redirect to `/library?filter=documents` — a **migration-safe navigation alias**, per the governing contract's Stage 1 requirement for "migration-safe navigation aliases and explicit compatibility tests" (`library-projects-spaces-product-surface-contract.md:554-555`). The old URL must keep resolving to the equivalent Library mode. |
| Deep link `/gallery` | Redirect to `/library?filter=images` — **conditional on the per-browser gate** (§2.2.3). When the browser's own state establishes that no browser-local content would be hidden, the alias applies and the address is canonicalized in place with `replaceState`. When content or uncertain state is present, `/gallery` stays functional and is **not** redirected, so nothing is hidden. The account-scoped sweep across browsers remains outstanding. |
| `cfy.lastView` | written on every view change (`AppShell.tsx:1509`), read back for any unrecognized pathname (`:1381-1384`). Once `/documents` and `/gallery` are aliased, a stale `cfy.lastView` must not resurrect the retired destinations: the write and read must be reconciled so a retired view name resolves to its Library alias. |

**Compatibility is a preservation obligation, not an optional extra.** Existing
deep links, existing navigation paths, and the published `cfy:project-kb:open`
contract all keep working after this phase. The governing contract's Stage 1
gate is explicit: *"existing Documents and Gallery workflows remain reachable
and resource identity/provenance is unchanged."*

### Phase 4 — Classify or remove redundant shells and unused components (evidence-gated)

This is where the "mark legacy" request lands — and it needs three
distinctions that the request's phrasing currently blurs.

**Phase 4 deletion is evidence-gated, not unconditional.** Nothing is removed
because it *looks* unused; every candidate must pass a dependency check that
enumerates production references, type dependencies, and test ownership.

- **Mark as compatibility code (not "legacy capability"):** the two *page
  shells* in `AppShell.tsx` — the `view === "documents"` branch (`:3999-4258`)
  and the `view === "gallery"` branch (`:4264-4328`) — once nothing navigates
  to them. The comment must state accurately what the code is: a **retired
  application destination retained as a deep-link compatibility shell**, not an
  assertion that documents or images, or the image/document resource families,
  are legacy. Compatibility code may be identified as such **without
  mischaracterizing canonical resource capabilities**.
- **Do NOT mark legacy:** `frontend/src/components/documents/DocumentsView.tsx`.
  It is live and shared — it is what Library's Documents filter renders
  (§2.1). Marking it legacy would be a false claim about live code.
- **Do NOT retire as part of this work:** `GalleryGrid`, the server-backed
  Images projection, and the document/image archival resource families. These
  remain live Library capabilities (§2.1).
- **Conditional deletion candidate:** `frontend/src/components/gallery/GalleryView.tsx`.
  Deletion is permitted **only** once all of the following are established:
  1. **Zero production references**, re-verified at deletion time (§2.3).
  2. **Type dependency resolved** — the exported `GalleryItem` type it provides
     to `GalleryGrid.tsx:13` and `LibraryView.tsx:2` has been relocated so no
     live Library component loses a type.
  3. **Test ownership preserved** — `components/gallery/__tests__/GalleryView.test.tsx`
     and `tests/gallery_auth.spec.tsx` assertions are folded into coverage that
     exercises the live gallery path, so coverage moves rather than silently
     disappearing.
  4. **Capability substitution confirmed** — the server-backed image projection
     it carries (`GalleryView.tsx:96-149`) is confirmed as supplied by
     `libraryResourceProjection.ts`, not lost with it.

  If any of the four cannot be established, the file is **retained** and, if
  it is retained with no production purpose, labelled as an unreferenced
  component — it is not deleted on an assumption.

  **The §2.2.2 safety gate is deliberately NOT one of these conditions.**
  `GalleryView.tsx` is not the component that renders browser-local images
  today — the inline Gallery branch inside `AppShell` is (§2.2). Coupling
  dead-code cleanup to a potentially complicated browser-data migration would
  create a dependency that serves neither concern. This deletion and the
  safety gate are **independent work items** and may proceed concurrently.

**Not in scope for Phase 4:** any backend route, schema, migration, or API
change. `GET /media/images`, `GET /media/document-artifacts`, and
`GET /media/documents` all remain exactly as they are.

### Phase 5 — Contract + proof

- Update `docs/architecture/library-projects-spaces-product-surface-contract.md`
  to record that the convergence was executed and to name the surviving
  compatibility surface. **That contract is not changed by this document** — it
  is updated only after implementation, as described here.
- Record a short proof note under `docs/architecture/proofs/` stating what was
  exercised (deep link → alias, Dashboard See All → filtered Library, menu
  absence, safety-gate result) and what remains **code-path only** rather than
  runtime-proven.
- **No release claim is created or widened by any phase.** Release truth remains
  governed by `docs/architecture/00-current-state.md`, which this document does
  not touch.

### Phase independence

Each phase is **independently verifiable** and can be landed and validated on
its own:

| Phase | Independently verifiable because |
|---|---|
| 1 | Menu-entry absence is observable without touching routes or data; the route tests keep passing unchanged |
| 2 | Filter URL round-trip is observable in isolation, with no navigation change required |
| 3 | Each alias and retarget is observable per URL and per button; the `/gallery` alias is separately gated |
| 4 | Classification and any deletion are observable by reference/type/test enumeration; **the phase may legitimately conclude "retain"** for every candidate |
| 5 | Contract and proof-note diffs are observable on their own |

No phase depends on a later phase having landed, and no phase is blocked by a
later phase's uncertainty — except the single, explicit exception of the
`/gallery` alias, which is gated by §2.2.2.

---

## 5. Options for how far this pass goes

**Decision (Resonant, 2026-11-01): Option B — full retirement.** The Dashboard's
own redundancy (§6) was the deciding factor: with the Dashboard slated to become
a Feed, keeping three documents projections alive would preserve exactly the
ambiguity this pass is meant to close. Option A and Option C are recorded below
for audit, not for selection.

**Option A — links only.** Phase 1. The dedicated pages become unlinked but stay
reachable via deep link and the Dashboard "See All" buttons. Nothing is
labelled legacy, because nothing is legacy yet. Smallest blast radius; leaves
two projections alive. **Not selected.**

**Option B — full retirement (recommended).** Phases 1-5. The dedicated pages
stop being navigable, Library becomes the single projection, and the page
shells are labelled as compatibility code against a contract that already says
they should be. Larger, but it finishes the job the contract started and leaves
the codebase with one honest story instead of three. **Selected.**

**What "full retirement" means here — and what it explicitly does not mean.**
The phrase describes the *application destination*, not the resource family:

*Full retirement DOES mean:*

- removing dedicated top-level navigation for Documents and Gallery;
- converging user-facing browsing into Library;
- preserving compatible navigation from the old URLs (migration-safe aliases,
  not broken links);
- retiring the redundant dedicated page shells when that is safe;
- eliminating obsolete frontend code only where it is **proven** unreferenced
  and safe to remove.

*Full retirement does NOT mean:*

- deleting document archives or image archives;
- removing server-backed document and image capabilities;
- removing shared Library presentation components (`DocumentsView`,
  `GalleryGrid`, the server-backed Images projection);
- altering canonical persistence, ownership, provenance, or retrieval
  relationships;
- changing any backend route, schema, migration, or API.

**Documents and Images remain first-class archival resource concepts.** Library
is a *presentation and discovery* surface over them, not a replacement for
them. See §7.

**Option C — Gallery first, Documents later.** Do Phase 1 for both, but retire
only `/gallery` (which §2.2 shows is strictly weaker than Library) and leave
`/documents` as a deliberate, unlinked, second documents surface. Preserves a
documents-only view that Library's filter row does not currently reproduce in
one click. Not selected — it keeps the ambiguous "two documents surfaces" state
open indefinitely.

---

## 6. The Dashboard is a third, weaker documents projection

Resonant's scope decision cited the Dashboard's own redundancy. The evidence
supports it more strongly than the Dashboard → Feed framing suggests.

**The Dashboard's "Recent Documents" card reads a different endpoint than
everything else.**

| Surface | Endpoint | Families covered | Scope |
|---|---|---|---|
| Documents page | `GET /media/document-artifacts` | uploaded + generated | project/thread scope |
| Library → Documents | `GET /media/document-artifacts` | uploaded + generated (`libraryResourceProjection.ts:239-242`) | project/thread scope |
| **Dashboard → Recent Documents** | **`GET /media/documents`, `limit: 4`** | **uploaded only** | unscoped beyond the request |

- Dashboard fetch — `components/dashboard/DashboardView.tsx:246`
- `/media/documents` queries the `UploadedDocument` table only
  (`guardian/routes/media.py:3007-3033`) — it cannot return generated documents.
- `/media/document-artifacts` is the richer artifact view
  (`guardian/routes/media.py:2848-2896`), the one Library and the Documents page
  both use.
- **`/media/documents` has exactly one production caller in the whole
  frontend** — the Dashboard card. Every other consumer (Documents page,
  Library, workspace shelf, workspace inspector, chat attachments) uses
  `/media/document-artifacts`.

So the codebase currently carries **three** documents projections of different
strength, and the weakest one is on the surface that is about to be replaced:

1. `/documents` page — full projection, but a redundant second surface.
2. Library → Documents — the canonical projection.
3. Dashboard → Recent Documents — an uploaded-only, four-item subset.

The Gallery side has a related but distinct shape: the Dashboard's Gallery card
is also **fed from** the browser-local gallery state (it receives the same
`gallery` prop, `DashboardView.tsx:155`, and filters `!item.mock` at `:309`),
while Library's Images filter is server-authoritative. The difference is that
the Dashboard card **always drops** mock items, whereas the Gallery page falls
back to showing them when no server-backed item exists (§2.2.1) — so the
browser-local residue is a **Gallery-page** exposure, not a Dashboard one. This
document does not change either card's contents (§6).

### What this means for the sequence

- **The Feed overhaul is a separate, larger change and is out of scope here.**
  It needs its own contract and plan. This document must not pre-empt it.
- **This pass must not block it.** Concretely: retarget the Dashboard's two
  "See All" buttons to filtered Library URLs (Phase 3) rather than deleting the
  cards. Deleting them would be a Feed-overhaul decision made in the wrong
  document; retargeting them removes the last caller of the retired surfaces
  *now*, and the Feed overhaul can later replace those cards outright —
  including deciding whether the Feed embeds Library projections directly.
- **Retiring `/media/documents` is a Feed-overhaul decision**, not this pass's.
  It becomes a single-caller dead endpoint once the Dashboard card is replaced.
  Worth flagging to that plan rather than deleting the route here.

### Feed boundaries this plan must not cross

Dashboard is planned to become **Feed** — an activity feed supporting
heterogeneous data types and a substantial presentation redesign. This
retirement plan deliberately prescribes **none** of the following, because
they belong to the Feed workstream's own contract:

- Feed **layout**
- Feed **card architecture**
- Feed **ordering or ranking**
- Feed **resource composition**
- Feed **personalization**
- Feed **data aggregation contracts**

What this plan does with the Dashboard is narrow and navigation-only:

- the two existing "See All" **navigation buttons** are retargeted to Library
  once filtered URLs exist (Phase 2 → Phase 3);
- the **current Dashboard card contents are left intact** — the Recent
  Documents card, the Gallery card, their data, and their underlying endpoints
  (`/media/documents` and the browser-local gallery state) are **not** changed,
  redesigned, or retired by this plan.

**In particular, `/media/documents` is not retired as part of this
consolidation.** Its possible replacement belongs to the future Feed work.

---

## 7. Canonical ownership and authority boundaries

### 7.1 Library is a presentation and discovery surface, not a persistence authority

Converging navigation into Library must not quietly promote Library into an
alternative document or image store. The governing contract already draws this
line, and this plan keeps it:

> **Library** is the canonical user-facing resource surface for Codexify.
>
> *[…]*
>
> Library does not replace the canonical storage or ownership model. Postgres,
> object/file storage, and other governed persistence systems remain
> authoritative for their respective records and bytes.
>
> A Library entry is therefore a view/reference over an authoritative resource,
> not a second copy and not a second ownership system.
>
> — `library-projects-spaces-product-surface-contract.md:42-57`

So the following are **preserved unchanged** by every phase of this plan:

| Boundary | What it means here |
|---|---|
| **Guardian ownership and authorization** | Account scope continues to come from the existing authenticated transport. Library never accepts, derives, or forwards a client-supplied user identity (`contract:121`). |
| **Project/thread scope** | Every source request carries the same selected scope — one project, one thread, or unscoped, matching the existing Documents scope contract (`contract:120-124`). No phase changes scope resolution. |
| **Resource identity** | Canonical source IDs are preserved unchanged and unmodified. Presentation keys stay source-family qualified; cross-family dedupe by raw ID stays prohibited (`contract:107-114`). |
| **Uploaded / generated distinctions** | Provenance is a separate axis from resource type, read only from authoritative metadata, and `unknown` stays `unknown` (`contract:83-103`). The four-filter taxonomy is unchanged: **All, Images, Documents, Widgets**. |
| **Provenance and source lineage** | Provenance survives every projection and presentation path unchanged (`contract:95`). No phase flattens a provenance claim into a resource-type claim. |
| **Export / restore relationships** | Explicit references and publication records are preferred over hidden copying (`contract:447-471`). No phase introduces a copy of a record outside its authoritative source. |

**Feed must not become another archival authority.** Feed is a presentation of
activity. Like Library, it is a view over authoritative records; it does not
acquire ownership, persistence, or a second copy of documents or images. Feed's
own contract will need to state this — but nothing in this plan grants it.

**No backend, schema, or API change is authorized by this plan.** The following
routes and their behavior are untouched by every phase:

- `GET /media/images` — server-backed image family projection
- `GET /media/document-artifacts` — server-backed document artifact projection
- `GET /media/documents` — the Dashboard card's endpoint, left intact (§6)
- `POST /api/media/upload/image`, `POST /api/media/upload/document` — upload
  persistence and ownership

### 7.2 ADR and contract alignment

Checked against `docs/architecture/adr/adr-index.md` and
`docs/architecture/README.md` on 2026-11-01.

- **The governing document is a product-surface contract, not an ADR.**
  `library-projects-spaces-product-surface-contract.md` is recorded in
  `README.md:78` as a *"user-approved product-direction contract"* that
  *"does not implement or widen release support."* This clarification is
  therefore **aligned with** it and does not contradict it.
- **No ADR governs Library surface convergence**, so no ADR is amended,
  superseded, or newly required by this documentation clarification. The
  contract's own ADR-impact section says *"No new ADR is required merely to
  record this product-surface distinction"*
  (`contract:604-608`), and reserves a new/amended ADR for runtime work that
  introduces canonical Library persistence or ownership semantics
  (`contract:610-624`) — **which this plan does not do**.
- **ADR-102** explicitly *preserves* the Library contract unchanged
  (`adr-index.md:288`). This plan does not alter it.
- **The contract's Stage 1 gate already matches this plan's shape**: *"Make
  Gallery and Documents Library modes before deleting legacy routes"* and
  *"Add migration-safe navigation aliases and explicit compatibility tests"*
  (`contract:554-555`), with the gate *"existing Documents and Gallery
  workflows remain reachable and resource identity/provenance is unchanged"*
  (`contract:558`). Phase 2 → Phase 3 → Phase 4 is that ordering.
- **No contradiction with accepted architecture was found.** One item is worth
  recording as an observation rather than a conflict: the contract states
  *"Library performs no mutation. Upload, delete, preview, and Workspace
  behavior remain owned by their existing surfaces"* (`contract:125`, `:206`),
  while `LibraryView.tsx:132-138` and `:189-199` do own upload and delete
  behavior. That is a pre-existing contract/implementation question about
  Library's own mutation posture — **outside this consolidation**, and not
  altered here. It is flagged here so the next reader does not mistake it for
  something this plan introduced.

---

## 8. Risks and honest limits

- **This plan is code-path evidence, not runtime proof.** Nothing here has been
  exercised in a live browser or against a running backend. Phases 1-3 change
  user-visible navigation; they should be verified in the running app before
  being called done. Documentation validation is not runtime proof.
- **Browser-local Gallery content is not fully characterised.** §2.2.1 proves
  that browser-local-only content *can* exist — a failed upload persists as a
  local `data:` URL with no server counterpart — and that Library cannot show
  it. It does **not** prove how much of it exists, and it cannot: `cfy.gallery`
  is **browser-scoped, not account-scoped** (§2.2.1a), so the question is only
  answerable by a browser-side inspection, and a negative result covers only
  the browser that produced it. The §2.2.2 safety gate is what establishes
  this, and it must run before the `/gallery` alias lands. This is the one open
  item in this plan that can change what Phase 3 is allowed to do — and it
  deliberately does **not** gate the `GalleryView.tsx` cleanup (§2.3, Phase 4).
- **The `cfy:project-kb:open` dispatcher may exist outside the repository**
  (an older build, a bookmarklet, a native shell, an integration). The repo
  contains no dispatcher; that is the whole of the evidence. This is why the
  listener is retargeted rather than removed (§3 item 4).
- **`GalleryView.tsx` deletion may legitimately conclude "retain."** Five
  conditions must be established (§2.3, Phase 4); if any fails, the file stays.
  A plan that assumed deletion was guaranteed would be wrong.
- **Backend is not affected.** `/media/images` and `/media/document-artifacts`
  are shared by Library, the workspace shelf, and the chat attachment flow.
  No backend route, schema, or migration is touched by any phase here.
- **Release posture is unchanged.** `docs/architecture/00-current-state.md`
  remains release truth and is not touched by this document. Nothing here is
  release qualification, and no phase widens support.

---

## 9. Deferred work (explicitly not authorized here)

| Deferred | Owner | Why not here |
|---|---|---|
| Feed layout, card architecture, ordering/ranking, resource composition, personalization, aggregation contracts | Future Feed workstream | §6 — a different contract |
| Replacement or retirement of `/media/documents` | Future Feed workstream | §6 — its only caller is a Dashboard card this plan does not remove |
| Any data migration for browser-local gallery content | To be decided by the user after the §2.2.2 gate | §2.2.2 — the gate defines the problem; the remedy is a product decision, and it must respect the browser-vs-account ownership boundary (§2.2.1a) |
| `GalleryView.tsx` type relocation and test folding | Phase 4 | §2.3, Phase 4 — independent of the safety gate; may proceed concurrently |
| Contract update recording the executed convergence | Phase 5, after implementation | §7.2 — the contract is updated after the code lands, not before |
| Runtime/browser proof of the navigation changes | Phase 5 proof note | §8 — code-path evidence is not runtime proof |
