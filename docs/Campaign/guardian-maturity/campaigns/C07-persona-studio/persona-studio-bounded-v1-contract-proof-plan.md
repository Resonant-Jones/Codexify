# C07-T002 Persona Studio Bounded V1 Contract and Proof Plan

## Gate Decision

**`go`** — C07-T003 may proceed by name only.

## Scope

This is a docs-only contract and proof-plan artifact. It defines Persona Studio V1 boundaries. It does **not** implement Persona Studio, add UI, routes, persistence, permissions behavior, retrieval behavior, runtime flags, execution authority, migrations, or tests. It does not widen release support.

## Current Trail

- C03 closed — coding delegation spine
- C04 closed — Pi/Coder invocation boundary
- C05 closed — command bus and tool turn observability
- C06 closed — guardian operator workspace
- C08 closed — Whoosh'd runtime integration and context fidelity
- C07 active — C07-T001 seam audit accepted
- C09/C10/C11 deferred

## C07-T001 Findings Carried Forward

| Finding | Status |
|---------|--------|
| Studio page exists | `implemented` |
| Studio API + store exist | `implemented` |
| Persona routes exist | `implemented` |
| System profile store exists | `implemented` |
| Studio boundedness | `not proven` |
| Permission matrix UI | `not present` |
| Retrieval policy UI | `not present` |
| Effective config preview | `not present` |
| No-memory-write enforcement | `not present` |
| No-chat-history enforcement | `not present` |
| V1 contract | `not present` (this task) |
| Execution authority bleed risk | identified |

## Persona Studio V1 Contract

### Purpose

Persona Studio V1 is a **non-conversational configuration and observability surface**. It helps inspect or edit persona/profile-related configuration only within proven boundaries. It does not execute chat, write memory, own identity, or authorize execution.

### V1 Goals

| Goal | Scope |
|------|-------|
| Route/navigation boundary | Prove Studio page routes only to allowed C07 surfaces |
| Profile draft state boundary | Prove Studio draft state is local, non-persisted unless saved via existing route |
| Validation surface boundary | Prove profile validation is preview-only, not enforcement |
| Effective config preview | Show what thread_config would receive from current profile |
| Prompt/system profile preview | Show assembled system prompt/persona without executing |
| Provider/model selection preview | Show selected provider/model without claiming availability |
| Permission matrix preview | Preview tool permissions without enforcing |
| Retrieval policy preview | Preview retrieval posture without executing |
| Runtime flag preview | Show runtime flags without overriding supported profile |
| Diagnostics/observability | Read-only diagnostic surfaces |
| No-execution-authority boundary | Prove no execution authority enters C07 V1 |

### V1 Non-Goals

- No chat interface.
- No chat history writes.
- No memory writes.
- No durable identity ownership.
- No execution authority.
- No daemon controls.
- No tool execution.
- No automatic permission enforcement.
- No retrieval execution.
- No provider routing change.
- No prompt/message construction change.
- No cloud fallback enablement.
- No release support widening.

### Entity Boundaries

| Entity | V1 may preview | V1 may own |
|--------|---------------|-----------|
| Persona/profile config | ✅ | ❌ (bounded preview) |
| System profile source | ✅ | ❌ |
| Thread_config fields | ✅ | ❌ |
| Provider/model selection | ✅ | ❌ |
| Retrieval source/mode | ✅ | ❌ |
| Permission posture | ✅ | ❌ |
| Runtime flags | ✅ | ❌ |
| Effective config | ✅ | ❌ |
| Validation output | ✅ | ❌ |
| Diagnostics output | ✅ | ❌ |

### State Boundaries

| State | Classification |
|-------|---------------|
| Local UI draft state | `specified_not_proven` |
| Persisted profile config | `partial` (routes exist) |
| Thread-bound config | `partial` (thread_config exists) |
| Derived effective config | `specified_not_proven` |
| Validation output | `specified_not_proven` |
| Diagnostics output | `partial` |

### Authority Boundaries

| Rule | Status |
|------|--------|
| Studio configures only proven surfaces | Boundary |
| Permission preview ≠ enforcement | Boundary |
| Retrieval preview ≠ execution | Boundary |
| Prompt preview ≠ provider-call execution | Boundary |
| Provider/model preview ≠ live availability | Boundary |
| Effective config preview ≠ task acceptance | Boundary |
| Studio validation ≠ execution authority | Boundary |

## Proof Plan

### Proof Ladder

Name only — no implementation prompts.

1. **C07-T003: Prove Persona Studio route and navigation boundaries**
   - Goal: Prove Studio page exists and routes only to allowed surfaces.
   - Primary files: `PersonaStudioPage.tsx`, `App.tsx`, route config
   - Must not claim: execution, memory, chat, permission enforcement

2. **C07-T004: Prove profile draft state and validation surface**
   - Goal: Prove draft state is local, validation is preview-only.
   - Primary files: `personaStudioStore.ts`, `persona_profiles.py`
   - Must not claim: persistence without save, enforcement

3. **C07-T005: Prove effective config preview without execution authority**
   - Goal: Show resolved thread_config from current profile without execution.
   - Primary files: `system_prompt_builder.py`, `system_profiles/store.py`
   - Must not claim: provider execution, task acceptance, release support

4. **C07-T006: Prove permission and retrieval policy preview boundaries**
   - Goal: Preview tool permissions + retrieval posture without enforcement.
   - Primary files: `personaStudioApi.ts`, `supported_profile.py`
   - Must not claim: enforcement, execution, model availability

5. **C07-T007: Close Persona Studio V1 beta boundary proof**
   - Goal: Seal all C07 boundaries, validate no memory/chat/execution bleed.
   - Must not claim: execution authority, release widening, C09 readiness

### Acceptance Criteria for C07 V1

| Criterion | Required |
|-----------|----------|
| Route/navigation boundary proven | ✅ |
| Profile draft/validation boundary proven | ✅ |
| Effective config preview proven | ✅ |
| Prompt/system profile preview boundary proven | ✅ |
| Permission matrix preview proven or deferred | ✅ |
| Retrieval policy preview proven or deferred | ✅ |
| No memory writes proven | ✅ |
| No chat history writes proven | ✅ |
| No execution authority proven | ✅ |
| Release boundary preserved | ✅ |

## Boundary Table

| Boundary | Rule |
|----------|------|
| Persona Studio vs Chat | `not allowed` |
| Profile config vs Memory | `not allowed` |
| Profile config vs Durable Identity | `not allowed` |
| Draft state vs Persistence | `preview_only` |
| Validation vs Enforcement | `preview_only` |
| Prompt preview vs Provider Execution | `preview_only` |
| Provider/model preview vs Live Availability | `preview_only` |
| Permission preview vs Enforcement | `preview_only` |
| Retrieval preview vs Execution | `preview_only` |
| Runtime flag preview vs Supported Profile | `preview_only` |
| Diagnostics preview vs Release Proof | `preview_only` |
| Persona Studio V1 vs C09 Execution Authority | `not allowed` |

## Gap Register

| Gap | Task |
|-----|------|
| Boundedness unproven | C07-T003 |
| No permission matrix | C07-T006 |
| No retrieval policy UI | C07-T006 |
| No effective config preview | C07-T005 |
| No V1 proof contract before C07-T002 | This task |
| No-memory-write unproven | C07-T003/T007 |
| No-chat-history unproven | C07-T003/T007 |
| Execution authority bleed risk | C07-T003/T007 |

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Identity contamination | C07-T004 profile <-> message boundary proof |
| Config drift | C07-T005 effective config preview |
| Permission overclaim | C07-T006 permission preview |
| Retrieval overclaim | C07-T006 retrieval preview |
| Profile schema risk | C07-T004 validation boundary |
| UI canon drift | C07-T003 navigation boundaries |
| Execution authority bleed | All C07 V1 tasks + C07-T007 closeout |
| Release widening | Boundary table + invariants |

## Invariants

- Persona Studio is configuration, not chat.
- Persona/profile config does not own durable identity.
- Persona Studio must not write memory in C07 V1.
- Persona Studio must not write chat history.
- Effective configuration must be inspectable before execution authority expands.
- Permission posture must be explicit and bounded.
- Retrieval policy must be explicit and bounded.
- Runtime flags must not silently override supported-profile posture.
- Provider/model catalog visibility is not live model availability.
- Prompt preview is not provider-call execution.
- C07 must not start C09 execution authority.
- No implementation hidden inside proof-planning work.
- No release claim widening.

## Documentation Follow-Through

- `00-current-state.md` not updated
- ADRs not updated
- C03/C04/C05/C06/C08 closeouts not updated
- C07 backlog updated
- C07 proof-pack updated
- C07 decision-log updated
- C07 V1 contract/proof-plan artifact created
- Next task named by name only

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C07-T003: Prove Persona Studio route and navigation boundaries`
