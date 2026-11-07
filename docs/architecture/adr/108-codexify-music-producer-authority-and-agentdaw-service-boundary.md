---
tags:
  - architecture
  - adr
  - music
  - studio
  - agentdaw
  - service-plugin
  - proposed
aliases:
  - ADR-108
  - Codexify Music Producer Authority and Agent-DAW Service Boundary
---

# ADR-108: Codexify Music Producer Authority and Agent-DAW Service Boundary

## Status

Proposed

## Date

2026-11-04

## Canonicalization history

ADR-102 is allocated to `102-saved-widget-identity-and-revision-boundary.md`
and is **not** available for this proposal. The highest allocated slot on
`main` at the time of writing is ADR-107
(`107-ordinary-memory-lifecycle-transition-semantics.md`). This draft takes
ADR-108. If a concurrent allocation claims ADR-108 before acceptance, this
document renumbers to the next free slot with its Proposed status, date, and
semantics unchanged, following the precedent in ADR-101.

This document **supersedes an earlier withdrawn draft** that was numbered
ADR-102 in a working directory and proposed a normalized
`studio_arrangements` / `studio_tracks` / `studio_clips` / `studio_midi_notes`
schema as Codexify-owned durable composition truth. That schema was written
before the Music Producer surface existed, and it is withdrawn — see
"Superseded proposal" below. The reason for withdrawal is itself part of this
decision.

## Source anchors

All paths are relative to `main` unless a revision is stated.

- `guardian/routes/music_projects.py` — the `/api/music` facade
- `guardian/skills/music-producer/SKILL.md` — the Producer skill doctrine
- `guardian/db/migrations/versions/a7d4c9e2f1b3_add_music_projects_table.py`
- `config/supported_profiles/v1-music-producer.yaml`
- `plugins/agentdaw/manifest.json` — service-plugin manifest
- `guardian/core/plugins.py` — the plugin invoke contract and timeout
- `docs/Future-Features/PLAN.md` — the Codexify Studio v1 plan
- `docker-compose.yml` — the `agentdaw` service definition
- `guardian/command_bus/manifest.py`, `guardian/tools/derive.py` — tool derivation
- `docs/architecture/thread-lenses-view-layer-contract.md`
- `docs/architecture/00-current-state.md`
- `AGENTS.md`

External:

- `Resonant-Jones/Agent-DAW` — the producer engine. The authoritative
  default build tag is the `CODEXIFY_AGENTDAW_BUILD_CONTEXT` fallback in
  `docker-compose.yml`, not this ADR. PR #1005 moved that default to `v0.1.6`
  on 2026-11-05 so async jobs retain the project context needed for artifact
  registration. This dated provenance note is not a separate version pin.
- `spec/Brief.schema.json`, `spec/SessionSpec.schema.json`,
  `spec/PatchSpec.schema.json`, `spec/Macros.schema.json` — the published
  specification contract

Provenance: PR #988 (`feat/music-projects`) merged to `main` on 2026-11-04
and carries the surface, the skill, the profile, and the migration. The
migration's `down_revision` is `d91e4fa6702b`, which `00-current-state.md`
records as the current single Alembic head.

## Context

### What was built

The Music Producer surface is implemented, not merely planned. It has four
parties with four different kinds of authority:

1. **The Artist** — the human. States intent in words, locks tempo, key, bar
   count, and length, approves what they accept.
2. **The Producer** — an LLM persona inside Agent-DAW that compiles a brief
   into a specification and renders it. It is not a Codexify agent.
3. **Codexify** — the host. Owns identity, project containment, the durable
   record of musical state, artifact custody, and the permission gate.
4. **REAPER** — the DAW. Receives the handoff: a `.rpp` project, standard
   MIDI, rendered stems, and a mix.

The engine is a separate repository and a separate container. `docker-compose.yml`
builds `agentdaw` from the tagged Agent-DAW release declared by the
`CODEXIFY_AGENTDAW_BUILD_CONTEXT` default (or an explicitly configured override),
behind the optional `music` Compose profile. Its output root is bind-mounted so
the host DAW can open what the service produced. Codexify never imports
Agent-DAW; the dependency runs in the other direction, over HTTP, on the
canonical service-plugin protocol (`POST {base_url}/invoke` with a versioned
envelope, `PROTOCOL_VERSION = "1.0"`, `PLUGIN_ID = "agentdaw"`,
`CAPABILITY = "music"`).

### Two design constraints that are already load-bearing

**The facade must live in the Guardian process even though the engine does
not.** Codexify derives its model-callable tools from its own OpenAPI schema
(`guardian/command_bus/manifest.py` → `guardian/tools/derive.py`), so the
model can only call a route that exists in the Guardian application. The
route module states this explicitly: the module owns the contract and the
forwarding, the service owns the music. This is why `/api/music` is mounted
in the backend while `agentdaw` runs as its own service.

**Operation timing is asymmetric and the asymmetry is enforced by the
transport.** A plugin invoke uses a 10-second timeout
(`INVOKE_TIMEOUT_SECONDS` in `guardian/core/plugins.py`), while a compose
takes roughly 107 seconds — the Producer's own model call is the long pole and
the render is only about two. Compose therefore returns a job handle
immediately and the caller polls `GET /api/music/jobs/{job_id}`; preview,
render, measure, and anchors return inline.

### Two doctrines that must not be eroded by a design document

**The Producer never authors DSP units.** The skill forbids writing a filter
cutoff in Hz, a reverb time in ms, a gain in dB, or a Q. The Artist thinks in
words — "warm", "tight", "harsh" — and the Producer translates that into a
semantic description; the engine owns every number. Tempo and key are the
exceptions, and only because the Artist states them. The engine's macro-to-
parameter map is pure and total, which is what makes this enforceable rather
than aspirational.

**A revision replaces whole state.** When the Artist corrects something, the
Producer sends the whole spec back with their words. Everything they did not
mention stays as it was. Specs are never patched field by field and a revision
is never half-specified: a complete new state with all six timbre axes, a
full spectrum, a full envelope, and a full LFO.

### The state model that already exists

`music_projects` is 1:1 with `projects`; `project_id` is both primary key and
foreign key, so attaching a Music Project to a Project and detaching it are
the same operation. `current_spec` is a JSONB column holding the complete
session state, with scalar columns beside it — `bpm`, `musical_key`,
`musical_mode`, `bars`, `time_signature`, `length_seconds`, `library_path` —
as a queryable projection of the same values, deliberately not indexed because
the table is small and is almost always reached by `project_id`.

`projects.system_role` was considered and rejected: its CHECK constraint
allows only `general` and `imports`, and the partial unique index
`uq_projects_user_id_system_role` is unique over `(user_id, system_role)`
where `system_role IS NOT NULL`, so a user could hold exactly one music
project under it. It is a column for "the system made this", not for "this
has a domain".

### Where the current wording is ambiguous

The two authoritative descriptions of the same column do not agree.

- The migration states that `current_spec` "is the complete session state and
  is the source of truth."
- The route module states that "the Producer owns the music; this side owns
  the record of it."

Read together, these describe two different authorities. The migration
wording invites the reading that Codexify's copy is truth; the route wording
is the opposite. Nothing in the shipped code resolves it, because in the
happy path the values agree — Codexify writes back what Agent-DAW produced,
whole, on each compose and revise. The ambiguity surfaces the first time the
artist edits the `.rpp` in REAPER after handoff and the two diverge.

### The original request

The originating product request was that Studio sessions be recorded in the
normal Postgres conversation tables and appear in the normal Codexify
application, tagged as Studio Sessions — chat there, but able to do Studio
work only when the Studio surface is attached. That requirement is
partially satisfied and partially open, and is carried into this ADR as an
explicit open decision rather than being asserted as done.

## Decision

### 1. Four parties, four authorities, one direction of dependency

Codexify owns identity, project containment, the durable record of musical
state, artifact custody, and the permission gate. Agent-DAW owns the
specification and the render — it is the authority on what the music *is*.
REAPER owns DAW and timeline state in the handoff artifact. The Artist owns
intent, locked values, and acceptance.

The dependency direction is Codexify → Agent-DAW over HTTP. Codexify does not
import Agent-DAW, and Agent-DAW does not read Codexify's database. The
specification contract crosses the boundary as published JSON Schema, not as
a shared table.

### 2. `music_projects.current_spec` is a record, not a second truth

`current_spec` is the Codexify-side **record** of the musical state. It is not
an independent truth and must never be treated as one. The authority on spec
content is Agent-DAW.

Every write is whole-state. Codexify writes the complete spec the engine
returned; it never patches fields, never merges, and never derives a partial
update. This mirrors the Producer's own revision discipline so that the two
sides cannot disagree about what a revision means.

The scalar columns beside `current_spec` are a **queryable projection** of the
same values, never an independent input. Writing them is part of the same
whole-state write.

### 3. The `/api/music` facade stays thin and stays in the Guardian process

`guardian/routes/music_projects.py` owns the contract, the forwarding, and
the record. It does not render, synthesize, or decide anything musical. This
is required by the tool-derivation rule, not a stylistic preference: the
route must exist in the application whose OpenAPI schema produces the model's
tool list.

The facade must not grow musical logic over time. Any logic that decides
tempo, key, form, instrumentation, patch design, or note arrangement belongs
to Agent-DAW.

### 4. Operation timing asymmetry is a contract, not an implementation detail

Compose is asynchronous by construction and returns a job handle; the caller
polls. Preview, render, measure, and anchors are synchronous. The 10-second
plugin invoke timeout is a hard boundary, and the asynchronous shape exists
because of it rather than in spite of it.

Any future Agent-DAW operation whose expected duration exceeds the invoke
timeout must follow the same shape. An operation that blocks past the
timeout is a defect, not a slow path.

### 5. Capability is gated by its own supported profile

The surface is enabled by the `v1-music-producer` supported profile, which
enables the `music_projects` route label. Every other supported profile keeps
that label quarantined, so the Producer is absent rather than broken wherever
it was not asked for, and a test asserts that invariant.

The default profile is byte-frozen and is a release promise, so a new
capability gets its own profile rather than a change to the default one.
This ADR does not widen the default profile.

### 6. Memory vault posture for the music profile is a deliberate quarantine

The music profile quarantines the memory vault. The Producer's accumulated
knowledge — patch library, retrieval anchors, delta revisions — lives inside
Agent-DAW, not in Codexify's memory store. Codexify's memory systems retain
their own authority and are not extended by this surface.

This ADR preserves the quarantine. Any proposal to let the music surface
write to the Codexify memory vault is a separate decision with its own proof
requirements.

### 7. Artifact custody belongs to the Project, not the Thread

Produced files are registered as the host's own `media_assets`, scoped to
their project. This holds even when the originating thread is absent or not
resolvable: files must not be lost over a missing thread. The Project is the
durable home; the Thread is provenance.

Registration must therefore never depend on a thread lookup succeeding. The
shipped implementation warns explicitly when files were produced without a
project, and refuses to register artifacts against a non-numeric project id.

### 8. The Producer is a skill, not an agent

The Producer is a skill (`guardian/skills/music-producer/SKILL.md`) invoked
through the ordinary model-callable tool surface. It does not introduce a
second agent, a second inference path, a second identity, or a second
authority chain.

The role split — the human is the Artist, the assistant is the Producer — is
a division of labor inside one agentic system, not the creation of another
system. Guardian remains the primary runtime and assistant authority.

### 9. The semantic-axis discipline is normative

The Producer emits semantic descriptions, never DSP units. The engine owns
every number. Tempo, key, bar count, and length are artist-locked and must
never be reinterpreted, improved, or silently changed; a request that
conflicts with a locked value is surfaced to the Artist rather than resolved
silently.

The Producer reports measurements, never adjectives, and states plainly when
the measurements do not support what was asked for.

This ADR records the discipline as normative because it is enforced
structurally — by the published spec schema, the macro-to-parameter map, and
the skill text — not merely by prompt.

### 10. REAPER integration is artifact handoff in v1; live control is not

What exists is a handoff: Agent-DAW writes a REAPER `.rpp` project, standard
MIDI, rendered stems, and a mix to a bind-mounted output root, and the host
opens them in REAPER. The `.rpp` writer is checked against a REAPER-written
project and opens in REAPER.

The live control path described in `docs/Future-Features/PLAN.md` — ReaPack
bundle, ReaScript execution, OSC telemetry, MIDI fallback, macro-bank control
of a running REAPER — is a later milestone and is **not** implemented. No part
of this ADR may be read as asserting live DAW control, and no documentation
may describe the handoff artifact as a live session.

## Superseded proposal

An earlier draft, numbered ADR-102 in a working directory, proposed that
Codexify introduce a normalized durable composition model of its own:
`studio_arrangements`, `studio_tracks`, `studio_clips`, `studio_audio_clips`,
`studio_midi_clips`, `studio_midi_notes`, `studio_automation_lanes`,
`studio_automation_points`, `studio_inserts`, and `studio_renders` — tick-based
time, a tempo map, per-kind discriminated detail tables, and a shared
automation shape.

That proposal is withdrawn. It was written before the Music Producer surface
existed, and it would have been wrong on the central question:

- The composition truth already exists and is owned by Agent-DAW, expressed as
  the published `SessionSpec` / `PatchSpec` / `Brief` / `Macros` contract.
- A second normalized schema in Codexify Postgres would be a second truth
  plane over that spec — precisely the duplicate-authority shape the
  repository's doctrine rejects.
- It would have competed with `music_projects.current_spec`, which is the
  record of exactly this state, already 1:1 with `projects`.
- Its "tick-based time with a tempo map" model duplicates tempo, bar, and key
  handling that Agent-DAW already owns in its spec schema.

What survives from that draft, and is carried here rather than discarded:
the discriminated-union *principle* is real and is already implemented
differently and better — as separate JSON Schemas per artifact kind
(`SessionSpec` for the session, `PatchSpec` for a patch, `Macros` for the
engine's semantic axes) rather than as normalized relational tables. The
equal-standing treatment of audio and MIDI survives as the engine's native
distinction between rendered stems and standard MIDI output, which are
first-class outputs of the same compose operation.

The withdrawn draft's file remains in the working directory only as a stub
pointing here.

## Naming layers

Codexify separates product language from internal implementation from
canonical authority. The music surface follows the same discipline, and it
introduces a fourth vocabulary that the other surfaces do not have.

| Layer | Vocabulary | Examples |
| --- | --- | --- |
| Product language | **Codexify Studio**, **Artist**, **Producer** | the surface, the human role, the assistant role |
| Internal implementation | **music**, **music_projects**, **agentdaw** | route label, table prefix, service and plugin id |
| Canonical authority (engine) | **Brief**, **SessionSpec**, **PatchSpec**, **Macros** | the published JSON Schema contract in Agent-DAW |
| Canonical authority (host) | **Project**, **Media Asset**, **Persona Profile** | `projects`, `media_assets`, ADR-082 |

"Studio" is now load-bearing in three distinct places — the Lens Editor
(product language for persona and configuration authoring, internally still
`personaStudio` and not a simplification target), the Codexify Studio product
surface, and the internal `personaStudio` module tree. They are distinct
surfaces with distinct authority. Documentation, identifiers, and interface
copy must not let a reader infer that configuring a Lens configures a Studio,
or that a Music Project is a Lens.

The internal `music` vocabulary is deliberately not `studio`. Codexify Studio
is the product; `music` is the current capability under it. Future Studio
capabilities that are not musical should not be forced into a `music_`
namespace.

## Governing contracts and ADRs

| Authority | Relationship |
| --- | --- |
| ADR-001 Queue-Based Completion Acceptance Model | Async compose returns a job handle; acceptance is not execution |
| ADR-002 Dual State Machine Model | Requested versus effective configuration remain distinct |
| ADR-005 Runtime Mode and Account Boundary Invariants | The surface inherits runtime-mode and account boundaries; no widening |
| ADR-069 Codexify Beta Runtime Support Boundary | The music surface is not Beta-supported by this ADR |
| ADR-081 Project Ownership Authority | `music_projects` inherits ownership through `projects`; no competing owner column |
| ADR-082 Persona Profile Manifest and Binding Authority | Producer scope follows persona authority; naming-layers precedent |
| ADR-087 Accepted Chat Task Execution Deadline | Compose is a Studio job, not a chat task |
| Thread Lenses View-Layer Contract | Governs how music sessions may appear in the normal application |
| Codexify Constitutional Heuristic | Capability does not imply authority; execution does not imply approval |
| `AGENTS.md` | Architecture-impact lane; canonical registries for new tokens |

## Open decisions requiring human ratification

1. **Music sessions in the normal application.** The originating request was
   that Studio sessions appear in the normal Codexify app, tagged as Studio
   Sessions — chat there, actionable only when the Studio surface is attached.
   Sessions are ordinary `chat_threads` rows and `chat_threads.active_profile_id`
   already records the active profile, so a derived view over the thread graph
   is available without new persistence. What is undecided is whether the
   music profile's memory-vault quarantine permits that view, and whether
   music sessions should be discoverable in an instance running the *default*
   profile, where `/api/music` is quarantined entirely.
2. **Divergence after handoff.** When the artist edits the `.rpp` in REAPER
   after handoff, Agent-DAW's spec and Codexify's record disagree. Which is
   authoritative, and does the Codexify record need a staleness marker, a
   source revision, or a content hash to make the disagreement visible rather
   than silent?
3. **Licensing and entitlement.** `docs/Future-Features/PLAN.md` describes a
   paid add-on with a perpetual local license token and advisory backend
   integrity checks. None of that is implemented. Whether entitlement becomes
   a Codexify authority, a local-only concern, or a capability-registration
   mechanism is undecided.
4. **Live REAPER control for v1.** The handoff path works today. Whether v1
   includes the ReaScript/OSC live-control path, and if so whether it is
   served by Agent-DAW or by a Codexify-side bridge, is undecided.
5. **Multi-agent delegated producer roles.** Not started in Agent-DAW. If
   pursued, delegated roles must not become a second agent authority inside
   Codexify, and this ADR would need to be extended rather than interpreted
   around.
6. **Generative audio adapters.** Stable Audio 3.0 and Lyria 3 adapters are
   written with no API key exercised. Adopting them changes the provider and
   credential posture and is therefore a separate decision.

## Non-goals

- A second agent, a second inference path, or a second identity inside Codexify.
- A parallel conversation, memory, or project system.
- A Codexify-owned normalized composition schema. See "Superseded proposal".
- Treating `music_projects.current_spec` as an independent truth.
- Live REAPER control claims.
- Any change to the default supported profile.
- Any widening of the memory vault's authority.
- Any release claim, Beta support widening, or qualification assertion.
- The paid add-on packaging and licensing model, which is unimplemented.

## Current-truth boundary

This ADR is a proposal. It does not change runtime behavior, data, routes,
contracts, or release support.

What is stated as *existing* above was verified against `main` on 2026-11-04
via the GitHub API: the `/api/music` route module, the Producer skill, the
`v1-music-producer` profile, the `a7d4c9e2f1b3` migration, and the
`plugins/agentdaw/manifest.json` are present on `main`; PR #988 merged
2026-11-04; the highest allocated ADR on `main` is ADR-107; and
`docs/architecture/00-current-state.md` (last updated 2026-11-04) records the
release gate as `HOLD`, with the stock Compose startup unqualified and the
supported-Compose qualification covering the source-matched launcher startup
only at a frozen revision.

The music surface is merged code behind a quarantining supported profile. It
is **not** a qualified supported path, and this ADR does not make it one.
`docs/architecture/00-current-state.md` remains the release authority.

Every statement in the Decision section is design intent awaiting
ratification. The authority clarifications in Decision 2 and the naming
discipline in Decision 9 are documentation of behavior that already exists;
the remaining decisions are proposals.

## Follow-through

On acceptance:

- Add to `docs/architecture/adr/adr-index.md` in the established reading-order
  format:

  ```text
  108. [[108-codexify-music-producer-authority-and-agentdaw-service-boundary|ADR-108 Codexify Music Producer Authority and Agent-DAW Service Boundary]] — Proposed decision recording the four-party authority split for the Music Producer surface: Codexify owns identity, project containment, the durable record of musical state, artifact custody, and the permission gate; Agent-DAW owns the specification and the render; REAPER owns DAW and timeline state in the handoff artifact; the Artist owns intent, locked values, and acceptance. Establishes `music_projects.current_spec` as a whole-state record rather than an independent truth, keeps the `/api/music` facade thin and in-process because model-callable tools are derived from the Guardian application's own OpenAPI schema, preserves the semantic-axis discipline and the music profile's memory-vault quarantine, and withdraws the earlier normalized Codexify composition schema as a duplicate truth plane. Architecture proposal only; the music surface is merged code behind a quarantining supported profile, is not a qualified supported path, and [[../00-current-state|00 Current State]] remains release authority.
  ```

- Add a pointer in `docs/architecture/README.md` under the doc map.
- Update `docs/Future-Features/PLAN.md` to point at ADR-108 for the authority
  boundary, so the plan and the ADR do not drift.
- Correct the `current_spec` wording conflict between the migration docstring
  and the route module docstring so both say the same thing.
- Retire the working-directory stub for the withdrawn ADR-102 draft.

## Validation expectations

No automated runtime tests apply to this proposal, which is a documentation
artifact.

When the implementation items in the Follow-through section are taken up, each
must produce its own proof artifact distinguishing code-path proof from
runtime proof, per the repository's convention. In particular, the
`current_spec` wording correction must be validated by a test that asserts a
whole-state write and rejects a partial one, and the authority assertions
about artifact custody must be validated by a test that registers artifacts
against a project with no resolvable originating thread.
