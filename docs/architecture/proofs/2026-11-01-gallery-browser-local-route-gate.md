# Gallery browser-local route gate — 2026-11-01

Date: 2026-11-02

Scope: the `/gallery` → `/library?filter=images` compatibility alias and the
persisted `cfy.lastView = "gallery"` destination, as implemented in the Library
Surface Consolidation.

This receipt records a **jsdom unit proof** and a **partial browser-runtime
proof**. It is not release qualification, and it is not a claim that any browser
other than the one under inspection is free of browser-local residue.

> **Correction — 2026-11-02 (later the same day).** The first version of this
> gate classified an entry as safe when its `src` merely *looked* like a server
> address (absolute `http(s)://`, protocol-relative, or root-relative) and it
> was not flagged `mock`. **That classification was insufficiently justified and
> has been withdrawn.** A syntactically valid server address does not establish
> that the **authorized Library Images projection** contains the corresponding
> resource for the current account and scope. The historical observations below
> are preserved as recorded, but the server-addressed canonicalization they
> describe is no longer permitted. See **Correction: fail closed on unverified
> server references** at the end of this receipt for the corrected rule and the
> new evidence.

## Why this receipt exists

The Gallery route was the last dedicated application destination still live. It
remained live because it can expose **browser-local** content that Library's
server-backed Images projection cannot retrieve: when an image upload fails, the
uploader falls back to a local `data:` URL and marks the item `mock: true`
(`frontend/src/hooks/useUploader.ts`). The local Gallery cache (`cfy.gallery`)
is browser-origin/profile scoped, **not** account scoped, so no server-side or
single-browser inspection can establish the absence of such content across every
browser.

Retiring the route without a guard would therefore be able to hide user-created
content silently. The implemented guard keeps the legacy Gallery reachable
exactly where that risk exists, per browser.

## What was implemented

> **Superseded in part.** The classification table below is the **first**
> version. Its `server` class — a server-shaped address treated as a verified
> counterpart — was withdrawn on 2026-11-02. See the correction at the end of
> this receipt.

`isGalleryCanonicalizationSafe()` in
`frontend/src/components/persona/layout/AppShell.tsx` decides, **for the browser
performing the navigation**, whether `/gallery` may canonicalize to
`/library?filter=images`.

It is a **read-only** decision. It does not write, migrate, upload, attribute,
remove, or log anything, and it never infers ownership from the signed-in
account. It introduces no new persistent inventory and no new ownership
authority.

Classification is per persisted entry, by whether the entry could represent
content **without a server counterpart**:

| Class | Rule | Navigation result |
|---|---|---|
| `seeded` | A known demonstration asset, recognized by identity against the seeded asset list | canonicalize |
| `server` | A server address (absolute `http(s)://`, protocol-relative, or root-relative) and not flagged `mock` | canonicalize |
| `local` | A `data:` or `blob:` reference | retain Gallery |
| `unknown` | Anything else, including an arbitrary `mock: true` entry on an unrecognized path | retain Gallery |

Two rules deliberately fail toward retaining the Gallery:

- **`mock: false` is never treated as proof that an item exists on the server.**
  Only the address is.
- **Arbitrary `mock: true` entries are not treated as synthetic.** Only the
  known demonstration assets are recognized as such.

The whole decision fails closed: an unreadable store, malformed JSON, a
non-array payload, or any unclassifiable entry keeps the legacy Gallery
reachable.

The same rule governs a persisted `cfy.lastView = "gallery"`: a safe browser
restores Library/Images; a browser with residue or uncertain state restores the
Gallery destination. The completed Documents persisted-view normalization is
unchanged.

## Safety conditions tested

> **Superseded in part.** The conditions below are the **first** version. The
> server-addressed cases are no longer safe; see the correction at the end of
> this receipt for the corrected table and the new evidence.

Verified in `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`
through the real routing mechanism (`resolveRoute` / `resolveInitialRoute` /
`syncRouteState`), never through a mocked navigation callback.

| Browser state | Expected | Result |
|---|---|---|
| No `cfy.gallery` entry | canonicalize | ✅ `/library?filter=images` |
| Known demonstration assets only | canonicalize | ✅ `/library?filter=images` |
| `data:` URL with `mock: true` | retain | ✅ `/gallery` stays, no Library view |
| `data:` URL stored but hidden by other entries | retain | ✅ `/gallery` stays |
| Unknown local or remote reference | retain | ✅ `/gallery` stays |
| Arbitrary `mock: true` entry on an unrecognized path | retain | ✅ `/gallery` stays |
| Malformed `cfy.gallery` payload | retain (fail closed) | ✅ `/gallery` stays |
| `cfy.gallery` read throws | retain (fail closed) | ✅ `/gallery` stays |
| Persisted `cfy.lastView = "gallery"`, safe browser | restore Library/Images | ✅ |
| Persisted `cfy.lastView = "gallery"`, browser with residue | restore Gallery | ✅ |

Also verified:

- **Canonicalization adds no history entry.** `pushState` is never called;
  `replaceState` is called exactly once with `"/library?filter=images"`.
- **No redirect loop.** After canonicalization, Back returns to the previous
  address, and the canonical address is not itself an alias.
- **Browser-local data is byte-for-byte unchanged by the navigation.** The
  stored payload is captured after the gallery hydrator settles and compared
  across the navigation.
- **The Documents alias does not regress.** `/documents` still canonicalizes to
  `/library?filter=documents` with the Documents filter selected.
- **The legacy Gallery still renders for a retained browser.** Local content
  remains visible under `/gallery`.

## Which browser states retain legacy access

- Any entry with a `data:` or `blob:` reference, regardless of its `mock` flag.
- Any entry that cannot be classified: a relative path, another URL scheme, a
  missing or non-string source, a non-object entry.
- Any entry flagged `mock: true` whose path is **not** a known demonstration
  asset.
- A malformed `cfy.gallery` payload.
- A `cfy.gallery` value that cannot be read at all.

## Which browser states canonicalize to Library

> **Superseded in part.** As first recorded, a server-addressed entry also
> canonicalized. Under the corrected rule only a missing key, a valid empty
> array, and entries that are entirely recognized seeded demonstration assets
> canonicalize. See the correction at the end of this receipt.

- No `cfy.gallery` entry at all.
- An empty `cfy.gallery` array.
- A `cfy.gallery` array in which every entry is either a known demonstration
  asset or a server-addressed, non-`mock` entry.

## Was a real-browser check performed?

**Yes — a partial one, on 2026-11-02.** A headless Chromium run against the
production frontend build, served as a static SPA with a history fallback, with
**no backend**. Each scenario used a **disposable browser context** (an
isolated profile, never the user's browser) seeded with **synthetic** Gallery
data only.

What the browser run established:

| Scenario | Result |
|---|---|
| No `cfy.gallery` entry | → `/library?filter=images` |
| Empty `cfy.gallery` | → `/library?filter=images` |
| Known demonstration assets only | → `/library?filter=images` |
| Server-addressed entry | → `/library?filter=images` |
| `data:` URL with `mock: true` | → `/gallery` retained |
| `data:` URL hidden by other entries | → `/gallery` retained |
| Arbitrary `mock: true` entry on an unrecognized path | → `/gallery` retained |
| Unknown local reference | → `/gallery` retained |
| `blob:` reference | → `/gallery` retained |
| Malformed payload | → `/gallery` retained |

And, in the same browser:

- **The browser-local payload was unchanged by the navigation in every
  scenario** — the stored value was compared before and after each navigation
  and was byte-for-byte identical every time.
- **The app's canonicalization added no history entry.** `history.length` was
  14 before the app's action and 14 after it.
- **Back did not loop.** Back landed on the previous address
  (`/chat`), never on the retired `/gallery`; Forward returned to
  `/library?filter=images`.
- **The persisted gallery destination obeys the same rule.** With a safe
  browser, `cfy.lastView = "gallery"` restored Library with the Images filter
  selected and the persisted value was rewritten to `library`. With a browser
  holding a local `data:` URL, the Gallery destination was retained, the local
  image **was still rendered** (`img[alt="Local only"]` present), the persisted
  value stayed `gallery`, and the stored local entry was still present.
- **The Documents alias does not regress.** A direct load of `/documents`
  canonicalized to `/library?filter=documents` with the Documents tab selected.

The desktop nav in that same browser read **Guardian | Dashboard | Library |
Lens**, confirming the Phase 1 removal in a real runtime rather than only in
jsdom.

### What the browser run does *not* establish

- **No backend was running.** The run proves client-side routing, storage
  behaviour, and history behaviour only. It proves nothing about
  server-backed image listing, scope, or authorization.
- **The gallery content itself was synthetic.** No real user image was read,
  exported, or inspected, and no private browser profile was touched.
- **One browser engine, one profile shape, one moment in time.** Storage
  partitioning, quota eviction, extension interference, and multi-profile
  behaviour are not exercised by a single headless context.
- **The account-scoped sweep is still not done.** See below.

## What remains unknown about other browsers

Every browser, profile, and account is unexamined except the one performing the
navigation. `cfy.gallery` is browser-origin scoped, so a safe decision in one
browser says nothing about any other. **No global absence-of-content claim is
made, and none is supported by this work.**

The account-scoped sweep that would be needed to retire the route everywhere —
determining, per account, which browsers hold browser-local-only images — is
still outstanding. It requires a mechanism that does not exist today: the server
has no visibility into a browser's local storage.

## What remediation remains deferred

No remediation is implemented, and none is designed here. The options remain
the ones recorded in the consolidation plan (§2.2.2), all of which require
explicit, attributable user action:

- a one-time export/download of browser-local-only images before redirect;
- a retained local-only compatibility route;
- an explicit, consented disclosure of what will disappear;
- re-upload by the user.

**No browser-local image is ever migrated automatically into the signed-in
account, assigned a canonical resource identity, or uploaded to a server by this
work.** Browser-local ownership stays unknown.

## What was deliberately not changed

- The `/gallery` route, its inline renderer, and the seeded demonstration
  assets.
- The Gallery browser-local state: nothing is written, rewritten, or deleted
  by the navigation decision.
- `DocumentsView`, `GalleryGrid`, and the server-backed Library Images
  projection.
- The document and image archival resource families, and every backend route.
- The governing contract, `docs/architecture/00-current-state.md`, and release
  claims.

Full Gallery retirement is **not** complete: the route remains live and
functional, and the account-scoped sweep has not been performed.

## Evidence pointers

- Gate implementation — `frontend/src/components/persona/layout/AppShell.tsx`
  (`classifyGalleryEntry`, `isGalleryCanonicalizationSafe`,
  `LEGACY_LIBRARY_ALIASES`, `resolveInitialRoute`)
- Focused tests — `frontend/src/components/persona/layout/__tests__/AppShell.test.tsx`
  (`AppShell legacy Gallery route gate`)
- Consolidation plan — `docs/Plans/2026-11-01-retire-dedicated-documents-gallery-surfaces.md`
  (§2.2.2, §2.2.3, Phase 3)
- Upload fallback that creates local-only content —
  `frontend/src/hooks/useUploader.ts`
- Server-backed projection that cannot retrieve it —
  `frontend/src/components/library/libraryResourceProjection.ts`

---

## Correction: fail closed on unverified server references (2026-11-02)

### What was wrong

The first gate classified a persisted entry as **server-backed** when its `src`
was a server address — absolute `http(s)://`, protocol-relative, or
root-relative — and it was not flagged `mock: true`. On that basis the entry
was allowed to canonicalize, and `/gallery` was replaced by
`/library?filter=images`.

That classification was **insufficiently justified**. A syntactically valid
server address does not establish that the current account's **authorized
Library Images projection** contains the corresponding resource. The gate could
therefore hide browser-local content that only looked server-shaped.

### Why no server identity was available to check

The persisted Gallery entry carries only `{ src, prompt, mock }`.

`frontend/src/hooks/useUploader.ts` pushes a much richer object into the
gallery on a successful upload — canonical `id`, `filename`, `src_url`,
`project_id`, `thread_id`, `source_tag`, `kind`. **None of it survives
storage**: `normalizeGalleryItem` in
`frontend/src/components/persona/layout/AppShell.tsx` reduces every entry to
`{ src, prompt, mock }` before it is persisted, and `GalleryItem` in
`frontend/src/types/ui.ts` is declared with exactly those three fields.

So a persisted entry contains **no authoritative server identity** to check.
Per the governing rule — *if the existing persisted entry does not already
carry sufficient authoritative identity evidence, classify it as uncertain and
retain Gallery* — an unverified reference is uncertain by construction.

### The corrected rule

The classification now distinguishes four things:

| Class | Rule | Effect |
|---|---|---|
| **Verified server-backed identity** | Not reachable from a persisted entry | — |
| `seeded` | A **known** demonstration asset, recognized by identity against the seeded asset list | **safe** |
| `server_shaped` | A server-*shaped* address with no verified identity behind it | **retains Gallery** |
| `local` | A `data:` or `blob:` reference | **retains Gallery** |
| `uncertain` | Any other value, including malformed entries | **retains Gallery** |

Canonicalization is permitted for exactly three states: a **missing** Gallery
storage key, a **valid empty** Gallery array, and a Gallery array whose entries
are **entirely recognized seeded demonstration assets**.

`mock: false` does not override uncertain provenance, and arbitrary
`mock: true` entries are still not treated as seeds. No API lookup, identity
registry, resource cache, or asynchronous route-resolution mechanism was
introduced: the bounded gate simply declines to hide anything it cannot prove.
**Conservative false negatives are acceptable; false positives that hide
content are not.**

### New unit evidence (jsdom, real routing mechanism)

Added to `AppShell legacy Gallery route gate`:

| Scenario | Result |
|---|---|
| Unverified server-shaped (root-relative) entry | retains Gallery |
| Unverified external HTTPS entry | retains Gallery |
| Unverified protocol-relative entry | retains Gallery |
| Unverified first-party HTTPS entry | retains Gallery |
| `mock: false` on a server-shaped entry | retains Gallery |
| Missing Gallery key | canonicalizes |
| Valid empty Gallery array | canonicalizes |
| Recognized seeded assets only | canonicalizes |

The previously recorded test that implied URL shape alone proves server-backed
identity was **replaced**, not kept. The byte-for-byte storage test was also
retargeted: it now asserts that a server-shaped entry keeps the Gallery
retained **and** that the stored bytes are untouched.

### New browser evidence (2026-11-02, disposable Chromium, synthetic data)

A second headless Chromium run against the production build (static SPA, **no
backend**), disposable context per scenario, synthetic Gallery entries only.
The service worker cache from the first run was cleared first — otherwise the
old build would have been served and the correction would have appeared not to
apply.

| Scenario | Result |
|---|---|
| Empty Gallery state | → `/library?filter=images`, Library rendered with the **Images** filter selected |
| Known-seed-only state | → `/library?filter=images`, Library rendered with the **Images** filter selected |
| External HTTPS image reference | → `/gallery` retained, Library view absent |
| First-party HTTPS image reference | → `/gallery` retained, Library view absent |
| Root-relative image reference | → `/gallery` retained, Library view absent |
| Protocol-relative URL | → `/gallery` retained, Library view absent |
| `mock: false` server-shaped entry | → `/gallery` retained, Library view absent |
| Local `data:` URL | → `/gallery` retained, Library view absent |

Also confirmed in the browser:

- **The Gallery surface renders when retained.** `gallery-primary-frame` was
  present and the Library view was absent.
- **The app added no history entry** in any scenario.
- **The stored bytes were unchanged** in every scenario; the local `data:` entry
  was still present in storage afterwards.
- **`/documents` still canonicalizes** to `/library?filter=documents` with the
  Documents tab selected.

### What the browser run still does not establish

- **No backend was running.** It proves client-side routing, storage, and
  history behaviour only. It proves nothing about server-backed image listing,
  scope, authorization, or the existence of a canonical record.
- **Image bytes did not paint in the retained case.** The gallery rendered the
  surface, but the item displayed the "Image unavailable" state, because
  `useRenderableMediaSrc` acquires media through the desktop media bridge,
  which is absent in a plain browser. That is pre-existing gallery rendering
  behaviour in a backend-less browser, unrelated to this gate. The gate
  guarantees *access* — the route and the surface stay reachable — not that the
  bytes paint in an environment with no media backend.
- **The earlier observation is retained as history, not as permission.** The
  first run's server-addressed canonicalizations are recorded above precisely
  because they are what the correction withdraws.

### The account-scoped sweep is still outstanding

Nothing here changes the position recorded above: a safe decision in one
browser says nothing about any other browser, profile, or account, and the
server has no visibility into a browser's local storage. Full Gallery
retirement remains incomplete.
