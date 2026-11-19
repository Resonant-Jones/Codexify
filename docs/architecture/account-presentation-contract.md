# Account presentation for Web and Scout

This task implements Chris's approved account-owned greeting and presentation
request. It follows ADR-058's separation of identity from Imprint, ADR-079's
account ownership, ADR-088/092's canonical account session and credential-purpose
boundaries, and ADR-064's independent material controls. It activates no private
Bio/Guardian retrieval capability and makes no general Beta release claim.

The existing GET/PATCH `/api/auth/scout/profile` is authoritative only for an
explicit `greeting_name`. Empty/cleared means neutral. Username, display name,
email, browser nickname and memories are never fallback sources. Display-name
semantics are unchanged. Reads do not create profiles or save inferred values.

GET/PATCH `/api/auth/scout/profile/presentation?workspace_id=<UUID>` projects or
authors seven allowlisted fields: `theme_mode` (system/light/dark), `base_color`
(six-digit hex), `background_depth` and `background_fade` (0–1), `surface_depth`
(integer 0–100), `surface_warmth` (integer −100–100), and `glass_treatment`
(refractive/frosted/solid). PATCH supplies the UUID in its JSON body. Unknown,
null and out-of-range values are rejected without echoing submitted values.
No provider secrets, biography, thread state, device permissions or arbitrary
browser keys belong to this contract. OS accessibility overrides affect local
rendering without rewriting the stored choice. Native materials adapt to iOS;
this does not promise identical WebGL and SwiftUI pixels.

Account appearance is the default. `workspace_unique: true` explicitly snapshots
the shared appearance into an account-owned UUID namespace. Subsequent edits
apply there. Rejoining with false resumes shared settings without promoting the
unique values; opting out again restores the last unique appearance. Greeting
name remains account-wide. Current clients use one opaque UUID per browser or
Scout installation, not a Project ID. Only that identifier is stored locally;
legacy browser/device preferences are preserved but not silently imported.
At most sixteen unique workspace records are allowed per account.

GET/PUT `/api/auth/scout/profile/presentation/wallpaper?workspace_id=<UUID>` uses
the same owner and scope. PUT accepts a raw, validated still PNG/JPEG/WebP up to
5 MiB and 16 megapixels. The DB holds private image bytes, not an external or
signed URL. PATCH `clear_wallpaper: true` clears the effective scope. Responses
are no-store/no-referrer; image reads add nosniff. Authenticated clients retrieve
the bytes and discard them on account change. URL version hashes aid refresh
without granting access. GET never creates presentation rows.

All routes use canonical `scope.account_id`, a live stored account session with
matching signed subject/purpose, existing Preview ingress and exact native
method/path admission. Client owner IDs confer no authority. Cookie writes
require same Origin; conflicting transports are rejected. A User row lock
serializes partial preference merges, including first creation. No migration
backfills any person's preferences or greeting.

Migration `f3a9c7d2b8e1`, parent `d2e7a9b4c1f6`, adds only `user_presentation`.
Downgrade drops this new table; export/restore of the PostgreSQL database
preserves its JSON settings and private wallpaper bytes. Broad private Bio and
Guardian field/task-scoped authentication requests remain a separate candidate.

Web and Scout refresh while foregrounded and after returning to the app. They
retain drafts on failed saves, discard stale account responses, and use neutral
defaults until the signed-in account has loaded. Transport or endpoint absence
is an unavailable account-setting state; it never promotes local profile data.

Qualification requires the migration round trip, ownership/session/ingress and
canonical-ID tests, exact native admission, no-write GETs, binary constraints,
concurrent partial-update proof, Web lifecycle and rendered browser checks, and
Scout package/build checks. Deployment remains separately evidenced; source
implementation and synthetic tests alone do not prove a live owner greeting.

The mainline compatibility candidate preserves d2/f3 and main's e723 lineage
through the no-DDL a3f8c2d6e901 merge (145 revisions). Its
[synthetic reconciliation proof](proofs/2026-11-18-account-presentation-mainline-reconciliation.md)
does not authorize a live migration or broader profile/voice activation.
