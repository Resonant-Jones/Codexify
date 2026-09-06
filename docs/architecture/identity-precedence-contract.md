# Identity Precedence Contract

Purpose: define the canonical identity-layer and selection model for Codexify
so prompt assembly, accepted-task execution, inspector surfaces, Imprint, and
Persona Profile work share one explicit authority boundary.

Last updated: 2026-09-05

Source anchors:

- docs/architecture/adr/058-imprint-ui-deprecation-and-identity-ownership.md
- docs/architecture/adr/082-persona-profile-manifest-and-binding-authority.md
- guardian/cognition/identity_contract.py
- guardian/cognition/identity_resolution.py
- guardian/cognition/system_prompt_builder.py
- guardian/cognition/modular_prompt_builder.py
- guardian/cognition/system_profiles/manifest.py
- guardian/cognition/system_profiles/store.py
- guardian/cognition/system_profiles/resolver.py
- guardian/core/chat_completion_service.py
- guardian/tasks/types.py
- guardian/workers/chat_worker.py
- guardian/routes/imprint.py
- guardian/routes/persona_profiles.py
- guardian/routes/chat.py
- frontend/src/features/settings/api/systemPrompt.ts
- frontend/src/features/settings/components/SystemPromptInspector.tsx
- frontend/src/features/settings/hooks/useSystemPromptInspector.ts

## Contract summary

Codexify implements identity layering, not identity replacement.

- Guardian is the stable first-person platform actor.
- Canonical Persona Profiles express authored configuration for how Guardian
  may operate; they do not replace Guardian or own durable user identity.
- Imprint is derived relational/presentation synthesis; it does not author a
  Persona Profile or grant authority.
- System documents provide supporting context.
- Request-local and scratchpad guidance shape one request only.
- Base safety and policy rules remain immutable across all higher layers.

ADR-082 governs canonical Persona Profile authority. ADR-058 governs the
ownership boundary among Guardian, durable identity, canonical Persona
Profiles, Imprint, Settings, Persona Studio, and Diagnostics.

## Canonical authority layers

The following order describes authority and selection boundaries. It must not
be confused with the current prompt-segment render order documented later.

### 1. Immutable Guardian base identity

The base system prompt establishes Guardian as the stable actor.

Properties:

- sole stable first-person actor in the current runtime;
- non-editable through Persona, Imprint, thread configuration, or a request
  override; and
- authoritative over higher-layer conflicts involving actor identity, safety,
  or base policy.

Persona or Imprint may shape Guardian's behavior or presentation, but neither
may rebind `I` to a different stable actor.

### 2. Canonical Persona Profile selection and resolution

`PersonaProfileManifest` is the canonical authored Persona configuration object
under ADR-082. It can persist authored identity/display intent, prompt, model,
voice, capability, and retrieval requests without granting account, Project,
participant, connector, retrieval, capability, provider, or execution
authority.

Canonical persistence and selection use:

- a stable `PersonaProfile` registry;
- immutable `PersonaProfileRevision` manifest snapshots;
- server-owned `PersonaProfileBinding` account ownership;
- thread `active_profile_id` and `active_profile_revision` pins; and
- exact account-scoped revision resolution.

The currently runtime-bearing canonical projection is limited to:

1. profile name/display intent;
2. system prompt;
3. model provider;
4. model identifier; and
5. temperature.

Other manifest fields remain authored intent until an individually authorized
and proven runtime enforcement seam exists.

Canonical Persona configuration may shape tone, directives, model request, and
response stance. It may not replace Guardian, override base safety, or become
durable user identity.

### 3. Imprint relational/presentation resolution

Imprint is a derived relational/presentation layer. Current resolution selects:

1. active Imprint for the current user/Project scope;
2. user-default Imprint with `project_id = null`; then
3. system-default Imprint fallback.

An Imprint may contribute `guardian_name`, `preferred_name`, `style`,
`grammar_prefs`, `metrics`, `heat_score`, and other authorized
interaction-shaping guidance.

Imprint may not:

- replace Guardian;
- become an authored Persona Profile or second system-prompt editor;
- own durable user identity or memory; or
- grant model, tool, connector, Project, participant, retrieval, capability, or
  execution authority.

### 4. System documents

System documents add bounded supporting context. Their inclusion is evidence or
guidance for the current prompt; it is not actor identity, authored Persona
state, Imprint state, durable identity, or an authority grant.

### 5. Request-local and scratchpad guidance

Scratchpad and request-local fields may add one-turn guidance, depth hints,
profile guidance, retrieval hints, and other transient context. They do not
persist or mutate canonical Persona Profiles, Imprint, durable identity, or
Guardian actor semantics.

## Persisted, resolved, acceptance-time, and executed state

These four state classes are distinct and must not be conflated.

### Persisted state

Persisted state answers what exists durably. It includes:

- canonical Persona Profile registry, immutable revisions, and account binding;
- thread profile ID/revision pins;
- active Imprint rows and proposal/review records;
- legacy active Persona rows during migration; and
- other saved thread configuration or compatibility records.

Persistence alone does not prove which state was accepted or executed for a
particular task.

### Resolved state

Resolved state is the deterministic selection produced from persisted state,
scope, compatibility rules, and request inputs. It answers which canonical
profile revision, Imprint, legacy compatibility Persona, system documents, and
request-local guidance would be selected at a named resolution point.

Resolution must report source and failure truthfully. A missing, foreign, or
unavailable canonical revision must not silently fall forward to the latest
revision.

### Acceptance-time state

For canonical Persona Profiles, queue acceptance captures server-resolved
selection in the frozen `PersonaSelectionSnapshot` carried by
`ChatCompletionTask`. The snapshot records:

- `profile_id`; and
- `profile_revision` when the selected profile is a canonical immutable
  revision.

The server captures this state after acquiring the turn lock and overwrites any
caller-supplied snapshot. Unreadable or invalid canonical selection blocks
acceptance. Task serialization preserves the snapshot through the queue.

An explicit no-profile snapshot remains distinct from a historical task that
predates snapshot support. Revisionless built-in, environment, and Flow profile
classes may be captured with `profile_revision = null`; they are compatibility
runtime classes, not canonical account-owned Persona revisions.

### Executed request state

Executed request state is what the worker actually resolves and supplies to the
provider for one attempt. The worker must prefer the accepted
`PersonaSelectionSnapshot` over mutable current thread state, load the exact
owned Persona revision, and apply its runtime-bearing prompt/model/temperature
projection. Retries retain the same accepted revision even if the thread
selection changes or a later profile revision is created.

Missing or foreign accepted revisions fail closed before provider invocation.
Historical tasks with no snapshot retain their explicit compatibility behavior
and may resolve the thread's current selection; that exception must not be
misrepresented as canonical snapshot semantics.

No current status or inspector surface proves executed-request state unless it
reads execution evidence that explicitly records that state.

## Current compatibility and migration debt

Canonical Persona Profiles are not the only Persona-shaped code path still
executing. The following legacy behavior remains current compatibility debt:

- `guardian/routes/imprint.py:accept_imprint()` calls the legacy
  `persona_store.set_persona()` after activating an Imprint;
- `POST /api/imprint/persona` directly mutates legacy Persona rows;
- `GET /api/imprint/status` reports an active legacy Persona row;
- `guardian/cognition/identity_resolution.py:resolve_persona()` still resolves
  request overrides and mutable legacy Persona rows;
- thread execution still copies revisionless legacy `persona_id` selection into
  `bundle["requested_persona"]` for that resolver; and
- Settings and `useImprintZero` still read or write legacy Persona state through
  the Imprint API family.

The legacy resolver's current compatibility precedence is:

1. request-scoped override;
2. active legacy Persona for the current user/Project scope;
3. user Project-default legacy Persona with `project_id = null`; then
4. system-default Persona text.

Numeric request overrides may select a scoped legacy Persona row; nonnumeric
overrides may become inline request-only Persona text. This compatibility chain
does not supersede canonical Persona Profile revisions, bindings, thread pins,
or accepted-task snapshots. Legacy active rows are not silently canonicalized.

## Current prompt assembly order

Authority precedence and prompt rendering are separate concerns. The current
modular render order remains:

1. immutable Guardian base system prompt;
2. Imprint block;
3. Persona/profile block;
4. system documents block;
5. skills block when applicable; and
6. scratchpad block.

This order is fixed by `guardian/cognition/modular_prompt_builder.py`. It does
not grant higher authority to a later segment, and it does not permit actor
replacement. Canonical profile guidance and legacy Persona compatibility may
both still enter the current assembly path until migration work removes the
overlap.

## Safe overwrite rules

All higher layers are additive and bounded.

- Canonical Persona Profiles add authored configuration intent.
- Imprint adds derived relational presentation.
- System documents add supporting context.
- Skills and scratchpad add bounded execution or request-local guidance.

None may overwrite Guardian's stable actor identity, base safety rules, or the
authority decisions of account, Project, participant, Connections, capability,
retrieval, provider, memory, or execution control planes.

## Inspector surface contract

Diagnostics and System Prompt Inspector are observational only.

Current compatibility surfaces include:

- `GET /api/imprint/status`, which reports active Imprint and legacy Persona
  rows plus resolved prompt metadata; and
- `GET /api/system_prompt/summary`, which reports token and segment summaries
  for a resolved prompt preview.

The current `SystemPromptInspector` merges those surfaces into a read-only
preview. It may report the persisted or resolved state it actually observes,
segment presence, source metadata, token estimates, and truncation hints. It may
not claim exact acceptance-time or executed-request state without direct
evidence, mutate any layer, or become identity authority.

Future consolidation into one canonical inspection endpoint is separate
implementation work.

## Current runtime truth and limits

Code and focused tests at the 2026-09-05 acceptance revision support these
bounded statements:

- Guardian remains the stable actor.
- Canonical Persona Profile manifests, immutable revisions, account binding,
  thread revision pins, acceptance snapshots, and exact worker execution exist.
- Imprint continues to resolve as an additive presentation layer.
- Legacy Imprint-to-Persona mutation and legacy Persona resolution remain
  active migration debt.
- Diagnostics remain read-only projections.

This contract does not claim legacy convergence, broader manifest-field
enforcement, Default Guardian Profile semantics, a canonical inspection
endpoint, or any Beta/support expansion.

## Maintenance rule

If code changes Guardian actor semantics, Persona/Profile selection,
acceptance-time snapshotting, worker execution, Imprint ownership, prompt order,
or inspector evidence claims, update this contract and the governing ADR in the
same authorized architecture-impact change and add proof for the affected
surface.
