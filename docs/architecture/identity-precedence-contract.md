# Identity Precedence Contract

Purpose: define the canonical identity-layer model for Codexify so runtime
behavior, prompt assembly, inspector surfaces, and future persona-switching
work all share one explicit rule set for who may claim first-person identity
and how lower and higher identity layers interact.

Last updated: 2026-04-09

Source anchors:
- guardian/cognition/identity_contract.py
- guardian/cognition/identity_resolution.py
- guardian/cognition/system_prompt_builder.py
- guardian/cognition/modular_prompt_builder.py
- guardian/core/chat_completion_service.py
- guardian/routes/imprint.py
- guardian/routes/chat.py
- frontend/src/features/settings/api/systemPrompt.ts
- frontend/src/features/settings/components/SystemPromptInspector.tsx
- frontend/src/features/settings/hooks/useSystemPromptInspector.ts

## Contract Summary

Codexify currently implements **identity layering**, not identity replacement.

The stable actor is the core platform identity:

- Guardian is the only stable first-person actor in the runtime.
- Persona and imprint are additive layers that shape voice, style, and
  presentation.
- Thread-scoped persona overrides are request-scoped selectors, not actor
  replacement.
- Safety and base-system rules are immutable and cannot be overridden by
  persona, imprint, or thread/request selection.

This is the current runtime truth.

## Canonical Runtime Posture

Current posture:

- `actor_plus_role`

Meaning:

- The core platform identity remains Guardian.
- Persona is a role, mask, or instruction layer borrowed by Guardian.
- Imprint is a style/presentation layer borrowed by Guardian.
- Request-scoped persona selection can change which persona instructions are
  resolved for a request, but it does not replace the stable actor.

Future or unsupported postures:

- `persona_switching` as true actor replacement is not current runtime truth.
- `identity_rebinding` is not implemented.
- Any future posture that makes a persona the stable first-person actor must be
  treated as a new contract, not as an implied extension of the current one.

## Identity Layers

### Core platform identity

The base system prompt establishes the stable actor:

- `You are Guardian...`

Properties:

- Stable actor
- First-person authority
- Non-editable through persona, imprint, thread config, or request override
- Base for all higher layers

Allowed claim:

- Guardian may speak in first person as Guardian

Disallowed:

- Rebinding `I` to a different persona or imprint
- Replacing Guardian with a different named entity

### Persona identity

Persona is the user-facing voice/instruction layer.

Current runtime behavior:

- Persona content is inserted after the base prompt and after imprint content.
- Persona can be persisted as an active record per user/project.
- Persona can also be supplied at request time by thread config selection.
- Persona may be resolved from a persisted record by id or supplied inline as a
  runtime override string.

Persona may:

- Shape tone, directives, and response stance
- Bias how Guardian speaks
- Select a persisted persona record for a request

Persona may not:

- Replace the stable actor
- Override base safety or policy rules
- Claim first-person identity as a different speaker under this contract

### Imprint identity/style layer

Imprint is the style, presentation, and naming layer.

Current runtime behavior:

- Imprint is resolved independently from persona.
- Imprint uses active scope, then user-default scope, then system default.
- Imprint contributes style data such as `guardian_name`, `preferred_name`,
  `style`, `grammar_prefs`, `metrics`, and `heat_score`.

Imprint may:

- Influence presentation, tone, and address forms
- Set a presentation name for Guardian
- Shape how the actor is described to the user

Imprint may not:

- Claim a separate first-person identity
- Replace Guardian as the actor
- Override base safety or policy rules

## Persisted, Resolved, Used-In-Request

These three states are different and must not be conflated.

### Persisted state

Persisted state is what lives in storage:

- active persona rows
- active imprint rows
- thread config values such as `personaId`
- saved persona/imprint drafts and review records

Persisted state answers:

- What exists in the database?
- What is currently active for a scope?

### Resolved state

Resolved state is the deterministic selection produced after precedence rules
are applied.

Resolved state answers:

- Which persona body did the request actually use?
- Which imprint values were selected?
- Which source token explains that selection?

Canonical source tokens:

- `request_override`
- `active_scope`
- `project_default`
- `user_default`
- `system_default`

### Used-in-request state

Used-in-request state is the transient bundle and prompt composition used for a
single completion turn.

Used-in-request state answers:

- What actually entered the prompt for this request?
- Which request-scoped selector was copied into the bundle?

Current status surfaces do not prove the full last-request payload unless the
backend explicitly surfaces that request-only state.

## Precedence Rules

### Persona resolution precedence

Current precedence order:

1. Request-scoped override
   - In current runtime this is the thread config `personaId` copied into the
     completion bundle as `requested_persona`.
   - If the override is numeric, it resolves to a persisted persona record by
     id after user and scope checks.
   - If the override is a non-numeric string, it is treated as inline runtime
     persona text and becomes a request-only override with no persisted record.
2. Active persona for the current user/project scope
3. Project-default persona for the current user with `project_id = null`
4. System default persona text

Important:

- A request-scoped override can select a persona record that is not currently
  active.
- A request-scoped override does not deactivate or replace the persisted active
  persona.

### Imprint resolution precedence

Current precedence order:

1. Active imprint for the current user/project scope
2. User-default imprint with `project_id = null`
3. System default imprint fallback

### Prompt assembly precedence

The final system prompt is assembled in this deterministic order:

1. Base system prompt
2. Imprint block
3. Persona block
4. System documents block
5. Scratchpad block

This order is fixed by `guardian/cognition/modular_prompt_builder.py`.

## Safe Overwrite Rules

These layers are additive, not substitutive:

- Persona adds instruction and voice shaping.
- Imprint adds style and presentation shaping.
- System docs add supporting context.
- Scratchpad adds request-local guidance, depth hints, profile guidance, and
  RAG hints.

These layers are not allowed to:

- Overwrite base safety rules
- Replace Guardian as the first-person actor
- Pretend to be a different stable identity

If a layer conflicts with base safety rules, the base rules win.

## Inspector Surface Contract

The inspector/status surfaces are allowed to claim only what they actually see.

Current surfaces:

- `GET /api/imprint/status` returns persisted active imprint/persona rows plus
  resolved system prompt metadata.
- `GET /api/system_prompt/summary` returns token and segment summary for the
  resolved prompt.
- `SystemPromptInspector` merges those surfaces into a read-only preview.

What those surfaces may claim:

- Persisted active records
- Resolved prompt preview
- Segment presence, token estimates, and truncation hints

What those surfaces may not claim unless a request-only field is explicitly
surfaced:

- Exact last-request payload
- Proof of the raw request-time selector beyond the resolved preview
- Identity replacement

## Current Runtime Truth

Verified by code today:

- Base identity authoritative: yes
- Identity layering: yes
- Actor-plus-role semantics: yes
- Identity replacement: no
- Persona switching as a new stable actor: no

Current precedence order in practice:

1. Immutable base system prompt
2. Request-scoped persona override, if present
3. Active persona for the current scope
4. Project-default persona
5. System default persona
6. Active imprint for the current scope
7. User-default imprint
8. System default imprint
9. System docs
10. Scratchpad

Note:

- Persona and imprint resolution are separate precedence chains.
- Prompt assembly order is fixed and does not imply actor replacement.

## Implementation Anchors

- `guardian/cognition/identity_resolution.py`
- `guardian/cognition/system_prompt_builder.py`
- `guardian/cognition/modular_prompt_builder.py`
- `guardian/core/chat_completion_service.py`
- `guardian/routes/imprint.py`
- `guardian/routes/chat.py`
- `frontend/src/features/settings/components/SystemPromptInspector.tsx`
- `frontend/src/features/settings/hooks/useSystemPromptInspector.ts`
- `frontend/src/features/settings/api/systemPrompt.ts`

## Maintenance Rule

If code changes the actor, the prompt order, or the meaning of request-scoped
persona selection, update this document in the same change set and add a test
that proves the new behavior.
