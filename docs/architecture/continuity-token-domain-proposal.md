# Continuity Token Domain Proposal

> Classification: docs-only token-domain proposal
> Status: proposed
> Implementation status: no runtime tokens exist, no registry files created
> Normative language: "must", "must not", "should", "candidate", and "proposed" are intentional.

Purpose: Define the candidate canonical token domains for the Continuity Protocol Suite before any runtime implementation, storage schema, worker behavior, UI surface, browser capture, graph mount, sync protocol, or provider-routing change. This is a docs-only proposal per ADR-030's token-domain gate. It does not create backend or frontend token modules, does not add database constraints, and does not implement runtime behavior.

Last updated: 2026-06-25

## Purpose

The Continuity Protocol Suite introduces a large vocabulary of repeated, contract-bearing concepts: packet kinds, scope boundaries, confidence levels, commit triggers, open-loop statuses, rejected-path states, Pulse brief types, browser packet kinds, cache states, and implementation gate phases.

If these concepts land in runtime code as ad hoc strings, they will scatter across routes, workers, queues, frontend components, database constraints, API responses, and export artifacts. Renaming them casually would break system understanding across every layer. Inventing nearby synonyms would create silent semantic drift. Every future agent that touches continuity would reinvent the same vocabulary slightly differently.

This proposal applies the Canonical Token Philosophy to the continuity domain before any runtime code is written. It identifies which concepts must become canonical tokens, proposes candidate values, recommends future registry placement, and distinguishes candidate vocabulary from prose description.

This is step 1 of ADR-030's approved implementation order: token-domain proposal before backend contract types, before schema, before compiler behavior, before any runtime implementation.

## Non-Goals

This proposal does not, and must not be interpreted as:

- implementing any runtime behavior
- creating a backend token module (`guardian/*.py`)
- creating a frontend token module (`frontend/src/contracts/*.ts`)
- adding database constraints, enum types, or check clauses
- adding a schema migration
- emitting worker events or task payloads with continuity tokens
- returning continuity tokens in API responses
- rendering continuity tokens in UI surfaces
- enabling graph writes or promoting graph mounts
- implementing sync behavior
- changing provider routing
- widening the supported beta release promise
- creating a single giant continuity enum

## Token Promotion Rule

A continuity concept must become a canonical token when it meets **two or more** of the following criteria, per the Canonical Token Philosophy:

| Criterion | Example for Continuity Domain |
|---|---|
| Appears in more than one file | Packet `kind` used in packet builder, compiler, storage, export, and UI |
| Appears in more than one layer | Confidence used in compiler logic, API response, DB constraint, and UI rendering |
| Distinguishes lifecycle or system state | Open loop status transitions from `open` → `blocked` → `resolved` |
| Is API-visible | Reality Commit trigger returned in `/api/continuity/commits/{id}` |
| Is UI-visible | Project Pulse surface kind rendered as tab or card title |
| Is logged for operator diagnosis | Cache state logged as `stale` or `invalidated` for debugging |
| Is stored durably | Packet sensitivity stored in a database column with constrained values |
| Is tested | Contract test asserts exact `ContextPacketKind` enum values |
| Would be dangerous to rename casually | Renaming `manual` trigger would break stored Reality Commits |
| Is likely to be reinvented by future agents | Every agent would invent its own open-loop vocabulary |

Concepts that meet zero or only one criterion may remain as prose descriptions rather than canonical tokens.

**Promote immediately** when the concept is: API-visible, UI-visible, event-named, error-coded, storage-constrained, or health/degradation state.

## Candidate Domain Map

The following table maps every proposed continuity token domain, its purpose, its owning future layer, its likely registry location, whether it may become storage-constrained or API-visible, and its current implementation status.

| Domain | Purpose | Owning Layer | Backend Registry (Future) | Frontend Registry (Future) | Storage-Constrained? | API-Visible? | Status |
|---|---|---|---|---|---|---|---|
| `ContextPacketKind` | Discriminates packet payload shape and compilation treatment | Context Packet Protocol | `guardian/continuity/tokens.py` or `guardian/protocol_tokens.py` | `frontend/src/contracts/continuityTokens.ts` | Yes (FK or CHECK constraint) | Yes (packet responses) | Candidate only |
| `ContextPacketSensitivity` | Governs caching, export, and sync eligibility | Context Packet Protocol | `guardian/continuity/tokens.py` | Not directly rendered (policy-driven) | Yes (CHECK constraint) | Yes (packet metadata) | Candidate only |
| `ContextPacketRetention` | Governs how long a packet remains in the active working set | Context Packet Protocol | `guardian/continuity/tokens.py` | Not directly rendered | Yes (CHECK constraint) | Yes (packet metadata) | Candidate only |
| `RealityScope` | Discriminates Reality State scope boundary | Reality State Contract | `guardian/continuity/tokens.py` | `frontend/src/contracts/continuityTokens.ts` | Yes (FK or CHECK constraint) | Yes (state responses) | Candidate only |
| `RealityStateConfidence` | Annotates compiled assertion confidence | Continuity Compiler | `guardian/continuity/tokens.py` | `frontend/src/contracts/continuityTokens.ts` | Yes (CHECK constraint) | Yes (state responses) | Candidate only |
| `RealityCommitTrigger` | Records why a Reality Commit was created | Reality Commit Protocol | `guardian/continuity/tokens.py` | Not directly rendered (metadata) | Yes (CHECK constraint) | Yes (commit responses) | Candidate only |
| `RealityCommitKind` | Discriminates Reality Commit type | Reality Commit Protocol | `guardian/continuity/tokens.py` | Not directly rendered (metadata) | Yes (CHECK constraint) | Yes (commit responses) | Candidate only |
| `DiscoveryCommitTrigger` | Records what conceptual shift caused the Discovery Commit | Discovery Commit Protocol | `guardian/continuity/tokens.py` | Not directly rendered (metadata) | Yes (CHECK constraint) | Yes (commit responses) | Candidate only |
| `OpenLoopStatus` | Tracks unresolved question/task lifecycle | Open Loop Engine | `guardian/continuity/tokens.py` | `frontend/src/contracts/continuityTokens.ts` | Yes (CHECK constraint) | Yes (state responses) | Candidate only |
| `RejectedPathStatus` | Tracks rejected path lifecycle and reopen eligibility | Reality State Contract | `guardian/continuity/tokens.py` | `frontend/src/contracts/continuityTokens.ts` | Yes (CHECK constraint) | Yes (state responses) | Candidate only |
| `ProjectPulseSurfaceKind` | Discriminates UI brief surface type | Project Pulse Surface | Not stored (UI routing only) | `frontend/src/contracts/continuityTokens.ts` | No | Yes (UI rendering) | Candidate only |
| `BrowserContextPacketKind` | Discriminates browser-sourced packet type | Browser Context Provider | `guardian/continuity/tokens.py` | Not directly rendered | Yes (CHECK constraint) | Yes (packet responses) | Candidate only |
| `GraphMountMode` | Governs graph enrichment posture | Optional Graph Mount | `guardian/continuity/tokens.py` or config-driven | Not directly rendered | Yes (config or CHECK) | Yes (config/health) | Candidate only |
| `ContinuityCacheState` | Tracks compiled packet cache freshness | Continuity Cache | `guardian/continuity/tokens.py` | Frontend diagnostics only | No (ephemeral) | Yes (diagnostic) | Candidate only |
| `PinnedModelStateKind` | Tracks ephemeral model runtime optimization state | Provider/Runtime | `guardian/protocol_tokens.py` (existing) | `frontend/src/contracts/runtimeTokens.ts` (existing) | No (ephemeral) | Yes (provider health) | Candidate only |
| `ContinuityProofSurface` | Labels proof surface categories for continuity implementation | Implementation governance | Not stored (docs/test labels) | Not rendered | No | No (internal labeling) | Candidate only |
| `ContinuityImplementationGate` | Labels gate phases per ADR-030 | Implementation governance | Not stored (docs/task labels) | Not rendered | No | No (internal labeling) | Candidate only |

## Context Packet Token Candidates

### `ContextPacketKind`

Proposed candidate values. These determine packet payload shape and how the Continuity Compiler treats each packet.

| Candidate Value | Meaning | Packet Source | Compilation Treatment |
|---|---|---|---|
| `thread` | Thread-level continuity event | Chat thread activity, decision, summary | Feeds thread-scoped Reality State |
| `project_reality` | Compiled Project Reality change | Reality Commit, project goal shift | Direct input to Project Reality compilation |
| `browser` | Browser context capture | URL visit, selected text, page summary | Temporal context; decays faster than code artifacts |
| `git` | Git activity context | Commit, branch switch, staged changes | Feeds project-level continuity; git-commit-adjacent trigger source |
| `artifact` | Generated or uploaded artifact change | Document created, image generated, codex entry saved | Feeds active artifacts list; may trigger artifact-change Reality Commit |
| `persona` | Persona configuration change | Profile switch, persona update, permission change | Feeds persona-scoped Reality State only; not project-scoped |
| `provider` | Provider lane state change | Model switch, provider degraded, warmup completed | Runtime diagnostic; does not compile into Reality State |
| `retrieval` | Retrieval evidence packet | Local note match, vector hit, memory recall | Evidence source for compiler; annotated with broker provenance |
| `discovery` | Mental model shift | New abstraction, assumption overturned, thesis sharpened | Triggers Discovery Commit; highest compilation weight |
| `open_loop` | Unresolved question or task | Pending decision, incomplete exploration, blocked task | Feeds open-loops list; tracked across Reality Commits |
| `rejected_path` | Direction explicitly discarded | Rejected architecture, abandoned refactor, closed exploration | Feeds rejected-paths list; prevents accidental reopening |

All values are candidate only. They must not appear in runtime code, database constraints, API responses, or UI components until a future implementation task promotes them.

### `ContextPacketSensitivity`

Proposed candidate values governing caching, export eligibility, and sync behavior.

| Candidate Value | Meaning | Caching Allowed | Export Allowed | Sync Allowed |
|---|---|---|---|---|
| `local` | Packet never leaves the local node | No | No | No |
| `private` | Packet is scoped to the user's account | Yes (local only) | Yes (full-account only) | No |
| `syncable` | Packet may be synchronized across the user's trusted nodes | Yes | Yes | Yes (user-owned nodes only) |
| `shared` | Packet may be shared with collaborators or team scope | Yes | Yes | Yes (team scope, trust-policy dependent) |
| `restricted` | Packet carries sensitive content with explicit access restrictions | No | Conditional (must be explicit opt-in) | No |

Retention and sensitivity are orthogonal dimensions. A syncable packet may still decay rapidly; a private packet may persist indefinitely.

### `ContextPacketRetention`

Proposed candidate values governing active working-set lifetime.

| Candidate Value | Active Lifetime | After Expiry |
|---|---|---|
| `ephemeral` | Current session only | Evicted; never written to durable storage |
| `session` | Until session end | Decayed to archival storage |
| `project` | Life of the project | Decayed when project is archived |
| `account` | Life of the account | Survives project archival |
| `exportable` | Indefinite (user-governed) | Exported with account; retains provenance |
| `expires` | Explicit expiry timestamp | Evicted at `expires_at` |

## Reality Scope Token Candidates

Proposed candidate values for `RealityScope`. The scope determines which Reality State boundary the compiler applies.

| Candidate Value | Scope Boundary | Notes |
|---|---|---|
| `thread` | Single chat thread | Thread Reality |
| `task` | Single task or sub-task within a project | Scoped below project; candidate only |
| `project` | Single project | Project Reality (primary compilation scope) |
| `workspace` | User's local workspace (Obsidian, local files) | Workspace Reality |
| `user` | Single user account | Cross-project user Reality |
| `node` | Local Codexify node | Node Reality (federation boundary) |
| `team` | Named team or organization | Future scope; requires multi-user architecture |
| `dyad` | Two-person reciprocal reality | Candidate-only; must not imply shared reality runtime support |

`dyad` and `team` are explicitly candidate-only. They must not be promoted to storage-constrained values until the architecture proves multi-user Reality State synchronization, trust-policy integration, and persona/identity separation in team scope.

## Reality Commit Token Candidates

### `RealityCommitTrigger`

Proposed candidate values for what caused a Reality Commit to be created.

| Candidate Value | Trigger Source | Implementation Status |
|---|---|---|
| `manual` | User explicitly creates a Reality Commit | Not implemented; MVP candidate |
| `semantic_delta` | Continuity Compiler detects a meaningful change in compiled state | Not implemented; requires compiler runtime |
| `heartbeat` | Periodic compilation produces a checkpoint | Not implemented; requires heartbeat worker |
| `artifact_change` | Document, codex entry, or artifact created/materially changed | Not implemented; requires artifact-change hook |
| `git_commit_adjacent` | Git commit occurs and compiler determines project reality shifted | Not implemented; requires git hook integration |
| `pause_thread` | Thread is paused | Not implemented; requires thread-pause hook |
| `resume_thread` | Thread is resumed | Not implemented; requires thread-resume hook |

Heartbeat, semantic_delta, artifact_change, and git_commit_adjacent triggers require worker infrastructure. They must not be implemented until the manual commit path is proven.

### `RealityCommitKind`

Proposed candidate values discriminating what changed in this commit.

| Candidate Value | What Changed |
|---|---|
| `state_update` | General Reality State update |
| `decision_added` | A new decision was accepted |
| `open_loop_added` | A new open loop was identified |
| `open_loop_resolved` | An open loop was resolved |
| `rejected_path_added` | A direction was explicitly rejected |
| `artifact_linked` | An artifact was linked to the project reality |
| `assumption_changed` | A working assumption was added, modified, or removed |
| `risk_changed` | A risk was added, escalated, downgraded, or resolved |

## Discovery Commit Token Candidates

Discovery Commits are specialized Reality Commits (every Discovery Commit is a Reality Commit, but not vice versa). The trigger discriminates the type of conceptual shift.

| Candidate Value | Conceptual Shift | Example |
|---|---|---|
| `new_abstraction` | User names a new concept | "Let's call this the 'packet envelope pattern'" |
| `assumption_overturned` | A working assumption is proven false | "Turns out queue acceptance IS proof of eventual completion in this path — our earlier assumption was wrong" |
| `concepts_merged` | Two previously separate ideas are recognized as one | "Context Packet and Reality Packet collapse into the same envelope with a `kind` discriminator" |
| `architecture_direction_changed` | A decision reorients the project's structural direction | "We're moving from Redis-backed compilation to Postgres-backed" |
| `protocol_boundary_discovered` | A previously invisible seam becomes explicit | "The compiler and the broker are separate layers with a typed contract between them" |
| `product_thesis_sharpened` | The project's core bet is refined | "Codexify doesn't sell model access — it sells continuity" |

Discovery Commits carry additional metadata (before/after conceptual state, impact radius) beyond standard Reality Commits. This metadata shape is deferred to the Discovery Commit contract task.

## Open Loop and Rejected Path Token Candidates

### `OpenLoopStatus`

Proposed candidate lifecycle states for unresolved questions, tasks, decisions, and explorations.

| Candidate Value | Meaning | Lifecycle Rules |
|---|---|---|
| `open` | Active and unresolved | Initial state; may transition to `blocked`, `deferred`, `resolved`, or `stale` |
| `blocked` | Cannot progress until another open loop resolves | Must reference blocking loop IDs; transitions to `open` when unblocked |
| `deferred` | Intentionally postponed | Carries deferral reason; may transition back to `open` |
| `resolved` | Completed or answered | Terminal state; carries resolution summary |
| `stale` | No activity beyond retention window | System-classified; may transition to `cancelled` or back to `open` on user action |
| `cancelled` | Explicitly abandoned | Terminal state; carries cancellation reason |

### `RejectedPathStatus`

Proposed candidate lifecycle states for explicitly discarded directions.

| Candidate Value | Meaning | Lifecycle Rules |
|---|---|---|
| `rejected` | Conclusively discarded | Terminal; must carry rejection reason |
| `superseded` | Replaced by a newer, preferred direction | Must reference the superseding path or decision |
| `reconsider_allowed` | Discarded but explicitly flagged as reopenable | Carries conditions under which reconsideration is appropriate |
| `do_not_reopen` | Conclusively rejected with explicit instruction to never reopen | Strongest rejection signal; compiler must respect this across sessions |

Why these must be canonical: open loop status and rejected path status are storage-constrained (database CHECK constraints), API-visible (returned in Reality State responses), UI-visible (rendered in Project Pulse open-loops brief), and would be dangerous to rename casually. If an agent writes `"pending"` instead of `"open"`, the system silently breaks.

## Project Pulse Token Candidates

### `ProjectPulseSurfaceKind`

Proposed candidate values for UI brief surfaces. These are UI routing tokens, not storage values.

| Candidate Value | UI Brief Content |
|---|---|
| `where_was_i` | Primary resume signal: what the user was working on |
| `daily_brief` | Summary of recent activity since the last session |
| `recent_work` | List of recent commits, artifact changes, and thread activity |
| `last_commits` | Most recent Reality Commits and/or Git commits |
| `open_loops` | Unresolved questions, tasks, and decisions needing attention |
| `active_threads` | Threads currently in use with brief context |
| `paused_threads` | Threads set aside with at-pause context and suggested resume action |
| `resume_actions` | What the system recommends the user do next |

Project Pulse surface kind is not a storage token. It governs which brief surface to render. It lives in the frontend token registry only. It must follow UI token/layout law in any future implementation.

## Browser Context Token Candidates

### `BrowserContextPacketKind`

Proposed candidate values for browser-sourced packets. These are packet kind values that carry a source of `browser` and a more specific sub-kind.

| Candidate Value | What Is Captured |
|---|---|
| `page_identity` | URL, page title, domain |
| `selected_text` | User-explicit text selection with surrounding context |
| `visible_dom_digest` | Lightweight page structure (headings, links, key content regions) |
| `page_summary` | AI-generated page synopsis (future model-dependent) |
| `tab_binding` | Which Codexify project or thread this tab relates to |
| `user_action` | Browser interaction event (click, form submit, navigation, bookmark) |

Any future browser packet capture requires explicit consent review, scope configuration, and user-visibility guarantees before implementation. No browser automation is implied by these token candidates.

## Graph Mount Token Candidates

### `GraphMountMode`

Proposed candidate values governing graph enrichment posture for continuity.

| Candidate Value | Meaning | Baseline Continuity Works? |
|---|---|---|
| `disabled` | No graph system mounted | Yes (required path) |
| `inspect_only` | Graph available for operator inspection but does not feed into compilation | Yes |
| `enrichment_allowed` | Graph may provide relationship traversal to enrich compilation | Yes; graph errors must not block compilation |
| `preferred_enrichment` | Graph is the preferred enrichment source but compilation still works without it | Yes; graph-off path must prove identical core output |

All modes above `disabled` require graph-off baseline tests before acceptance. Graph mount mode must remain a runtime configuration choice, not a schema-compile-time constant.

## Cache and Runtime Optimization Token Candidates

### `ContinuityCacheState`

Proposed candidate values for compiled packet cache freshness. Ephemeral only; not durable.

| Candidate Value | Meaning |
|---|---|
| `missing` | No cache entry exists for this scope |
| `fresh` | Cache entry is valid and reflects current Reality State |
| `stale` | Cache entry exists but Reality State has changed since it was compiled |
| `invalidated` | Cache entry was explicitly evicted by policy or user action |

Continuity cache state is a diagnostic token, not a storage token. It may appear in operator debug surfaces but must not leak into user-facing Pulse briefs.

### `PinnedModelStateKind`

Proposed candidate values for ephemeral provider/runtime model optimization state. Not continuity-specific; applies to any model inference surface.

| Candidate Value | Meaning |
|---|---|
| `not_pinned` | Model is not pinned or cached |
| `warming` | Model is loading into memory or cache is being populated |
| `warm` | Model is loaded and ready for inference |
| `expired` | Cached state has expired via TTL or LRU eviction |
| `unavailable` | Pinning is not supported by the current provider lane |

These are runtime optimization states, not durability states. They must never be confused with Reality State, Continuity Cache, or compiled truth. They are provider-lane properties, similar to existing `ProviderRuntimeState` tokens.

## Implementation Gate Token Candidates

### `ContinuityImplementationGate`

Proposed candidate values for ADR-030 gate phases. These label governance checkpoints and do not become runtime tokens.

| Candidate Value | Gate Description |
|---|---|
| `token_domain_review` | All repeated contract-bearing values reviewed for canonical token eligibility |
| `storage_contract_review` | Entity lifecycle, retention, index strategy, and migration rollback reviewed |
| `provenance_export_review` | Reality State and Reality Commits verified for export/restore compatibility |
| `retrieval_router_review` | Continuity Compiler verified not to replace Context Broker or widen retrieval scope |
| `identity_consent_review` | Project continuity verified separate from persona identity and deep-identity consent |
| `operator_truth_review` | Operator-visible surfaces verified to not leak diagnostics into user-facing Pulse |
| `graph_optionality_review` | No-graph baseline verified; graph mount confirmed as enrichment only |
| `ui_diagnostics_review` | Project Pulse verified to follow UI token law and diagnostics boundary |
| `migration_rollback_review` | Every schema migration verified with tested upgrade and downgrade path |
| `proof_surface_review` | Required proof surfaces defined and contract tests in place per implementation slice |

These gate labels are governance tokens — they label task phases and proof checkpoints. They are not runtime tokens, not storage tokens, and not UI tokens.

## Future Registry Placement

When a future implementation task promotes candidate tokens to canonical tokens, the following placement guidance applies.

### Backend Registry

Continuity protocol tokens should live in a bounded registry, not scattered across modules. Recommended patterns:

- **Continuity-specific tokens** (`ContextPacketKind`, `RealityScope`, `RealityCommitTrigger`, `OpenLoopStatus`, etc.): Place in a continuity-specific module such as `guardian/continuity/tokens.py`. This keeps the continuity domain self-contained and avoids bloating the existing `guardian/protocol_tokens.py`.
- **Runtime-visible continuity tokens** (error codes, event types, health states emitted by continuity workers): May also be exported from `guardian/protocol_tokens.py` if they become part of the general runtime contract surface. Duplicate registration in both registries is not permitted.
- **Config-driven tokens** (`GraphMountMode`): May be expressed as environment variables or config constants rather than a Python enum, but the mapping between config values and internal logic must use canonical tokens, not ad hoc string comparisons.

### Frontend Registry

Frontend token consumption should be narrow:

- **UI-visible tokens** (`ProjectPulseSurfaceKind`, `OpenLoopStatus`, `RejectedPathStatus`, `RealityStateConfidence`): Place in a frontend contract module such as `frontend/src/contracts/continuityTokens.ts`. Import only the tokens that the UI actually renders or branches on.
- **Diagnostic-only tokens** (`ContinuityCacheState`): Should appear only in developer/operator tooling, not in the primary user-facing UI.
- **Provider/runtime tokens** (`PinnedModelStateKind`): Should extend the existing `frontend/src/contracts/runtimeTokens.ts` rather than creating a new continuity-specific frontend registry.

### Database Constraints

When a future schema task adds continuity tables:

- **CHECK constraints** should reference exact token values from the backend registry.
- **FK constraints** should reference lookup tables if the token set is expected to grow or carry metadata per value; CHECK constraints if the set is stable and bounded.
- **Migration downgrade paths** must be tested for every constraint addition.

### Warning: Do Not Create One Giant Continuity Enum

Do not place all continuity tokens in a single global enum or registry. Keep registries bounded by domain:

- Packet-domain tokens (`kind`, `sensitivity`, `retention`) → one registry
- State-domain tokens (`scope`, `confidence`, `status`) → one registry
- Commit-domain tokens (`trigger`, `kind`) → one registry
- UI-domain tokens (`pulse_surface_kind`) → frontend only
- Provider/runtime tokens (`pinned_model_state`) → existing runtime registry
- Governance tokens (`implementation_gate`, `proof_surface`) → docs/task labels only

## Storage and API Visibility Guidance

### Domains Most Likely to Become Storage-Constrained

These domains govern columns that Postgres must validate. They are the highest-priority candidates for backend token registries:

| Domain | Why Storage-Constrained | Migration Impact |
|---|---|---|
| `ContextPacketKind` | Packet type discriminator column in `continuity_packets` | Adds CHECK constraint or FK to lookup table |
| `ContextPacketSensitivity` | Governs export/sync/cache behavior | Adds CHECK constraint |
| `ContextPacketRetention` | Governs TTL/decay behavior | Adds CHECK constraint |
| `RealityScope` | Scope discriminator in `reality_state` | Adds CHECK constraint or FK |
| `RealityStateConfidence` | Confidence column in `reality_state` assertions | Adds CHECK constraint |
| `RealityCommitTrigger` | Trigger source column in `reality_commits` | Adds CHECK constraint |
| `RealityCommitKind` | Commit type discriminator in `reality_commits` | Adds CHECK constraint |
| `DiscoveryCommitTrigger` | Trigger source column in `discovery_commits` | Adds CHECK constraint |
| `OpenLoopStatus` | Status column in `open_loops` or inline in `reality_state` | Adds CHECK constraint |
| `RejectedPathStatus` | Status column in `rejected_paths` or inline in `reality_state` | Adds CHECK constraint |

### Domains Most Likely to Become API-Visible

Almost all continuity token domains are API-visible (returned in packet metadata, commit responses, or Reality State payloads). The following are explicitly API-visible domains:

- `ContextPacketKind`, `ContextPacketSensitivity`, `ContextPacketRetention` (packet CRUD responses)
- `RealityScope`, `RealityStateConfidence` (Reality State GET responses)
- `RealityCommitTrigger`, `RealityCommitKind` (Reality Commit GET responses)
- `DiscoveryCommitTrigger` (Discovery Commit GET responses)
- `OpenLoopStatus`, `RejectedPathStatus` (Reality State detail, open-loop/closed-path endpoints)

### Domains Most Likely to Become UI-Visible

These domains directly render in user-facing surfaces:

- `ProjectPulseSurfaceKind` — rendered as Pulse tab or card labels
- `OpenLoopStatus` — rendered as status badges or filter options in Pulse open-loops brief
- `RejectedPathStatus` — rendered as status indicators in rejected-paths brief
- `RealityStateConfidence` — rendered as confidence indicators (high/medium/low) in Pulse and Reality State views
- `ContinuityCacheState` — diagnostic only; never renders in user-facing Pulse

## Relationship to Existing Contracts

### `continuity-protocol-suite.md`

The protocol suite defines the vocabulary. This proposal defines which vocabulary terms become canonical tokens. Every token domain in this proposal maps to a section in the protocol suite contract.

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030 requires token-domain review as the first gate before runtime implementation. This proposal is that review. It satisfies gate 1 ("Canonical Token / Domain Review") in ADR-030's Runtime Gate section.

### `canonical-token-philosophy.md`

This proposal applies the Canonical Token Philosophy to the continuity domain. It uses the promotion criteria (appears-in-multiple-files, contract-bearing, dangerous-to-rename), the bounded-registry principle (no giant enum swamps), and the promote-immediately rule (API-visible, UI-visible, storage-constrained).

### `runtime-protocol-token-contract.md`

When continuity tokens are promoted to runtime code, they must follow the same discipline as existing protocol tokens: registered in a canonical module before use, imported by consumers, tested, and never invented as ad hoc literals inline.

### `chat-runtime-contract.md`

Continuity tokens are not chat runtime tokens. They do not redefine provider runtime states, request lifecycle states, or message/attempt identity. They sit at a different layer (above turn-level completion) and must not be confused with chat runtime vocabulary.

### `account-export-restore-contract.md`

When continuity tokens become storage-constrained, the entities they constrain must be exportable and restorable. Export must preserve provenance. Restore must not silently drop compiled truth or collapse Reality Commits into raw message history. Sensitivity tokens like `restricted` and `private` directly affect export eligibility.

### `router-decision-table.md`

Continuity compilation consumes broker output but does not modify retrieval intent. Retrieval-scoped packets (`kind = "retrieval"`) carry broker provenance. The compiler must not silently widen retrieval scope.

### `data-and-storage.md`

Storage-constrained continuity tokens will produce CHECK constraints or FK relationships in Postgres. They must follow existing lifecycle conventions (soft delete via `deleted_at` where applicable, cascade semantics aligned with parent entities). The migration path must include tested downgrade scripts.

### `codexify_workspace_surface_spec_v_1.md`

Project Pulse tokens govern UI brief surfaces. When Pulse is implemented, it must follow Workspace token/layout law, card hierarchy, and view-specific behavior rules. Pulse is a future UI surface, not part of the current Workspace spec.

## Required Follow-Up Before Runtime Use

Before any candidate token in this proposal becomes runtime behavior, a future implementation task must:

1. **Create bounded registry**: Add a backend Python module (e.g., `guardian/continuity/tokens.py`) and/or frontend TypeScript module (e.g., `frontend/src/contracts/continuityTokens.ts`) with typed exports.
2. **Add typed exports**: Use `StrEnum`, `Literal`, or equivalent typed constructs so misuse is caught at development time.
3. **Add contract tests**: Lock in exact enum values, membership, and forbidden ad hoc literals.
4. **Migrate consumers**: Replace any inline string literals with registry imports.
5. **Update docs**: Reference the canonical registry as the source of truth for continuity token values.
6. **Define migration path**: If storage-constrained, add Alembic migration with CHECK constraint or FK to lookup table; include tested downgrade.
7. **Prove graph-off baseline**: If graph-adjacent (`GraphMountMode`), prove that the no-graph path compiles valid Reality State.
8. **Update API contracts**: If API-visible, document token values in API response schemas.

No implicit promotion is allowed. A candidate value in this proposal becomes a canonical token only after an explicit implementation task registers it.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this proposal:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No backend token module has been created.
- [ ] No frontend token module has been created.
- [ ] No database constraints have been added.
- [ ] No release promise has been widened beyond `00-current-state.md`.
- [ ] All token values are explicitly marked as candidate only.
- [ ] Graph optionality is preserved; `GraphMountMode` `disabled` is the required baseline.
- [ ] `dyad` and `team` scope candidates are explicitly marked as candidate-only and do not imply shared reality runtime support.
- [ ] Project Pulse tokens are limited to UI/output surface and not treated as storage tokens.
- [ ] `PinnedModelStateKind` and `ContinuityCacheState` are clearly distinguished from durable Reality State.
- [ ] Token domains are kept bounded; no single giant continuity enum is proposed.
- [ ] Required follow-up steps are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
