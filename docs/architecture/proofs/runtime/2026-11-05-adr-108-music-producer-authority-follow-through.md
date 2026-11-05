# ADR-108 follow-through — Music Producer authority boundary

Date: 2026-11-05. Disposition: **the ADR's own follow-through items are
satisfied except the `PLAN.md` pointer, which lands with this receipt.**
Release: **HOLD**. This is a documentation-and-proof artifact for a
quarantined surface. It qualifies nothing, widens no release gate, and does
not make the Music Producer a supported path.

## Revision custody and scope

| Source | Verified revision |
| --- | --- |
| Base of this branch | `68c9e52361c5b6169dd18d5d44b39495f7a15f49` (`origin/main` at branch creation) |
| ADR-108 as merged | `docs/architecture/adr/108-codexify-music-producer-authority-and-agentdaw-service-boundary.md` |
| ADR-108 status on `main` | `Proposed` — recorded as proposed in `adr-index.md`, `docs/architecture/README.md`, and `docs/architecture/00-current-state.md` |

Files belonging to this change:

- `docs/Future-Features/PLAN.md` — the authority-boundary pointer the ADR
  asked for.
- `docs/architecture/proofs/runtime/2026-11-05-adr-108-music-producer-authority-follow-through.md`
  — this receipt.

No schema edit, no migration revision, no runtime code change, and no
release gate moved by this artifact.

## What the ADR asked for, and where each item stands

ADR-108's "Follow-through" section lists five items. Their state against
`main` at the base revision:

| # | Item | State | Evidence |
| --- | --- | --- | --- |
| 1 | Add the entry to `docs/architecture/adr/adr-index.md` | **Done** | `adr-index.md` line 134, merged in PR #994 |
| 2 | Add a pointer in `docs/architecture/README.md` | **Done** | `README.md` line 81, merged in PR #994 |
| 3 | Update `docs/Future-Features/PLAN.md` to point at ADR-108 | **This change** | The pointer below |
| 4 | Correct the `current_spec` wording conflict between the migration docstring and the route module docstring | **Done** | PR #997; `tests/routes/test_music_projects.py::test_a_whole_state_write_replaces_and_a_partial_one_clears` |
| 5 | Retire the working-directory stub for the withdrawn ADR-102 draft | **Moot** | See below |

### Item 5 is moot, and the reason is worth recording

The ADR says the withdrawn draft's file "remains in the working directory
only as a stub pointing here". No such stub exists in either checkout of
this repository. The only ADR-102 on `main` is
`102-saved-widget-identity-and-revision-boundary.md`, which is a legitimate
unrelated decision, and a search of both checkouts for the withdrawn
draft's distinctive identifiers (`studio_arrangements`, `studio_tracks`,
`studio_clips`, `studio_midi_notes`) returns nothing.

There is therefore no stub to retire, and no stub to point at ADR-108. The
item is satisfied by the absence of the artifact rather than by an action.
The ADR's own prose describing the stub as present is therefore inaccurate
about the state of the repository, and this receipt records that rather
than leaving it to be discovered later.

## The PLAN.md pointer

`docs/Future-Features/PLAN.md` describes the Studio v1 plan: a Node/TypeScript
harness, a ReaPack add-on bundle, a separate Studio UI package, the Strudel
engine path, an action ledger, and a licensing model. It predates the Music
Producer surface entirely, and read alone it implies that Codexify owns the
DAW-side session model.

The pointer now says, in the plan's own first section:

1. **The authority split is recorded in ADR-108**, and where the plan and the
   ADR could be read as disagreeing, the ADR governs.
2. **Codexify does not own a normalized composition schema.** The withdrawn
   `studio_arrangements` / `studio_tracks` proposal was a duplicate truth
   plane over Agent-DAW's published specification contract. Codexify keeps
   the whole-state *record* of what the Producer produced and writes it
   whole.
3. **The Music Producer surface is merged code behind a quarantining
   supported profile** — `guardian/routes/music_projects.py` forwarding to an
   Agent-DAW service over the canonical service-plugin protocol — and is not
   a qualified supported path.
4. **The Studio v1 plan itself is not implemented.** The pointer says so
   explicitly, so that the plan's presence cannot be read as a description
   of shipped behaviour.

## Code-path proof vs runtime proof

The ADR requires each follow-through item to produce a proof artifact that
distinguishes code-path proof from runtime proof.

**Code-path proof.** The pointer is a documentation artifact. The repository's
documentation validator (`scripts/validate_docs.py`) resolves the local
links it checks, and the ADR-108 pointer it introduces resolves to two
existing files on `main`:

- `docs/architecture/adr/108-codexify-music-producer-authority-and-agentdaw-service-boundary.md`
- `docs/architecture/00-current-state.md`

The `PLAN.md` change adds no code path, so no runtime test applies to it
beyond the link resolution.

**Runtime proof.** None is claimed for this artifact. The Music Producer
surface is behind the `v1-music-producer` profile, which is not a qualified
supported path; `docs/architecture/00-current-state.md` remains the release
authority, and it records ADR-108 as *proposed*. A documentation pointer to a
proposed ADR neither accepts it nor widens the surface.

## What this receipt does not do

- It does not accept ADR-108. The ADR's status stays `Proposed`, and the six
  open decisions it lists remain human-owned.
- It does not implement the Studio v1 plan, the Node/TypeScript harness, the
  ReaPack bundle, the Studio UI, the Strudel path, the action ledger, or the
  licensing model.
- It does not qualify the `v1-music-producer` profile, and it does not
  change the default profile's route posture.
- It does not move any release gate. Release stays **HOLD**.
