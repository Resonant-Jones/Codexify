# C07-T001 Persona Studio Current Surface and Contract Seam Audit

## Gate Decision

**`go`** — C07-T002 may proceed by name only.

## Scope

This is a docs-only audit. It does **not** implement Persona Studio, add UI, routes, persistence, permissions, retrieval policy, runtime flags, execution authority, or migrations. It does not widen release support. It starts C07 only as an audit campaign.

## Current Trail

- C03 closed — coding delegation spine
- C04 closed — Pi/Coder invocation boundary  
- C05 closed — command bus and tool turn observability
- C06 closed — guardian operator workspace
- C08 closed — Whoosh'd runtime integration and context fidelity
- Wave 4 post-C08 selected C07
- C09/C10/C11 deferred

## Source Map

| Path | Status | Relevance | Confidence |
|------|--------|-----------|------------|
| `docs/architecture/persona-studio-spec.md` | Present | Contract spec | HIGH |
| `frontend/src/features/personaStudio/` | Present | Frontend feature dir | HIGH |
| `frontend/src/features/personaStudio/PersonaStudioPage.tsx` | Present | Main page component | HIGH |
| `frontend/src/features/personaStudio/personaStudioApi.ts` | Present | API client | HIGH |
| `frontend/src/features/personaStudio/personaStudioStore.ts` | Present | State management | HIGH |
| `guardian/routes/persona_profiles.py` | Present | Backend persona routes | HIGH |
| `guardian/routes/personal_facts.py` | Present | Personal facts routes | HIGH |
| `guardian/cognition/system_prompt_builder.py` | Present | System prompt assembly | HIGH |
| `guardian/cognition/system_profiles/` | Present | Profile store + resolver | HIGH |
| `guardian/core/supported_profile.py` | Present | Supported profile posture | MED |
| `guardian/core/config.py` | Present | Runtime config | MED |
| `guardian/db/models.py` | Present | DB models — contains persona tables? | LOW |

## Persona Studio Contract Summary

### What Governing Docs + Code Prove

| Claim | Status | Evidence |
|-------|--------|----------|
| Persona Studio is configuration layer | `specified_not_proven` | `persona-studio-spec.md` describes Studio as configuration surface; frontend feature exists but boundedness not tested |
| Runtime chat is execution layer | `specified_not_proven` | Chat completion is proven (C08-T004), but separate from Studio |
| Memory is external system | `specified_not_proven` | No Studio-memory write path visible |
| Studio must not maintain chat history | `not present` | No enforcement visible |
| Studio must not write memory | `not present` | No enforcement visible |
| Studio outputs saved profile/config only | `partial` | `personaStudioStore.ts` and `persona_profiles.py` suggest saving but not proven bounded |
| Effective config inspectable before execution | `specified_not_proven` | `persona-studio-spec.md` requires this; C08-T005 proved operator truth surfaces but not Studio-specific config view |

## Current Implementation Surface Map

| Surface | Path | Status | Evidence | Risk | Next Task |
|---------|------|--------|----------|------|-----------|
| Frontend Studio page | `PersonaStudioPage.tsx` | `implemented` | File exists | Unclear boundaries | C07-T003 |
| Studio API client | `personaStudioApi.ts` | `implemented` | API helpers exist | May call unproven routes | C07-T003 |
| Studio state store | `personaStudioStore.ts` | `implemented` | Zustand store exists | Profile state persistence unclear | C07-T004 |
| Backend persona routes | `persona_profiles.py` | `implemented` | Backend routes exist | Profile CRUD boundaries unproven | C07-T003 |
| Personal facts routes | `personal_facts.py` | `implemented` | Backend routes exist | Memory-adjacent — boundary risk | C07-T006 |
| System prompt builder | `system_prompt_builder.py` | `implemented` | Prompt assembly exists | Studio-to-prompt seam unproven | C07-T005 |
| System profile store | `system_profiles/store.py` | `implemented` | Profile persistence exists | Schema boundary unproven | C07-T004 |
| Supported profile posture | `supported_profile.py` | `implemented` | Supported profile config | Studio enforcement unproven | C07-T005 |
| Thread profile fallback | `thread_config` fields | `implemented` | C08-T004 context assembly | Studio interaction unproven | C07-T005 |
| Permission matrix UI | Not found | `not present` | No permission UI visible | Gap | C07-T006 |
| Retrieval policy UI | Not found | `not present` | No retrieval UI visible | Gap | C07-T006 |
| Effective config preview | Not found | `not present` | No unified config preview | Gap | C07-T005 |
| Studio tests | `__tests__/` | `implemented` | Test directory exists | Coverage uncalibrated | C07-T003 |

## Contract Gap Register

| Gap | Evidence | Blast Radius | Proposed Task |
|-----|----------|-------------|---------------|
| Studio boundedness not proven | Page/API/store exist but boundaries unverified | Studio could be mistaken for execution surface | C07-T003 |
| Profile persistence boundaries unproven | `persona_profiles.py` + `system_profiles/store.py` exist | Profile writes may leak | C07-T004 |
| Effective config preview absent | No unified config surface | Operator cannot inspect Studio-affected runtime config | C07-T005 |
| Permission matrix not inspectable | No tool permission UI found | Operator cannot verify permissions before execution | C07-T006 |
| Retrieval policy not inspectable | No retrieval config UI found | Operator cannot verify retrieval posture | C07-T006 |
| System prompt preview absent | No prompt preview in Studio | Profile → prompt mapping is opaque | C07-T005 |
| No-memory-write enforcement unproven | `personal_facts.py` is memory-adjacent | Studio could write memory | C07-T006 |
| No-chat-history enforcement unproven | Studio page may route to chat | Studio could be mistaken for chat | C07-T003 |
| Export/import boundary unproven | No export/import tested for profiles | Profile portability untested | Future |
| V1 contract not defined | No bounded Studio contract exists | Implementation drifts without contract | C07-T002 |

## Risk Register

| Risk | Evidence | Mitigation |
|------|----------|------------|
| Identity contamination | Studio configures persona profiles; thread uses them | C07-T004 must prove profile <-> message boundary |
| Config drift | Studio store + backend routes independent | C07-T005 effective config preview |
| Permission overclaim | No permission matrix visible | C07-T006 permission preview |
| Retrieval overclaim | No retrieval policy visible | C07-T006 retrieval preview |
| Profile persistence risk | Schema unclear | C07-T004 profile validation |
| UI canon drift | Studio page may route to unrelated surfaces | C07-T003 navigation boundaries |
| Execution authority bleed | Studio may be mistaken for execution | Boundary table + C07 contract |

## Boundary Table

| Boundary | Status |
|----------|--------|
| Persona Studio is not chat | Explicit |
| Profile config is not memory | Explicit |
| Profile config is not durable identity | Explicit |
| System prompt preview is not execution | Explicit |
| Permission preview is not enforcement | Explicit |
| Retrieval preview is not execution | Explicit |
| Provider/model selection is not live availability | Explicit |
| Catalog presence is not release support | Explicit |
| Persona Studio audit is not C09 execution authority | Explicit |
| C07 audit does not widen beta release promise | Explicit |

## Initial C07 Backlog Proposal

Name only — no implementation prompts.

1. `C07-T001: Persona Studio current surface and contract seam audit` ← THIS TASK
2. `C07-T002: Define Persona Studio bounded V1 contract and proof plan`
3. `C07-T003: Prove Persona Studio route and navigation boundaries`
4. `C07-T004: Prove profile draft state and validation surface`
5. `C07-T005: Prove effective config preview without execution authority`
6. `C07-T006: Prove permission and retrieval policy preview boundaries`
7. `C07-T007: Close Persona Studio V1 beta boundary proof`

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C07-T002: Define Persona Studio bounded V1 contract and proof plan`
