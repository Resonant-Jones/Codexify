# C07-T004 Persona Studio Profile Draft State and Validation Boundary Proof

## Gate Decision

**`go`** — C07-T005 may proceed by name only.

## Scope

This proves Persona Studio profile draft state and validation surface only. It does not prove effective config preview, permission enforcement, retrieval execution, memory writes, chat-history writes, or execution authority.

## Draft State Map

| Element | Value | Evidence |
|---------|-------|----------|
| Source | `personaStudioStore.ts` | Static import of `PERSONA_STUDIO_STORAGE_KEY`, `createPersonaStudioSeedState`, `persistPersonaStudioLocalState` |
| State owner | `PersonaStudioLocalState` | Exported type with `profiles[]` and `draftProfilesById` |
| State scope | `local_storage` | Key: `cfy.personaStudio.localState.v1` |
| Baseline profile source | `PERSONA_STUDIO_SEED_PROFILES` | 3 default profiles with configs |
| Read | `readPersonaStudioLocalState()` | Reads from localStorage |
| Write | `persistPersonaStudioLocalState()` | Writes to localStorage |
| Clear | `clearPersonaStudioLocalState()` | Clears localStorage key |
| Dirty tracking | Not proven | No explicit dirty flag found |
| Reset/revert | Not proven | No explicit reset function observed |
| Save to backend | Not proven | Deferred to future tasks |

## Validation Surface Map

| Element | Value | Evidence |
|---------|-------|----------|
| Validation source | Store types only | `PersonaConfig` aggregates permissions, tools, retrieval, prompts, model, voice, runtime, diagnostics |
| Required-field validation | Not proven | No explicit validation function found |
| Prompt/system prompt validation | Not proven | `PromptSettings` type exists but no validator |
| Model/provider validation | Not proven | `ModelSettings` type exists but no validator |
| Permission validation | Not proven | `PersonaCapabilityPermissions` type exists |
| Retrieval validation | Not proven | `RetrievalSettings` type exists |
| Runtime flag validation | Not proven | No explicit runtime validation found |
| Validation posture | `configuration-level` | Types describe config shapes — no enforcement runtime |

## Boundary Classification

| Boundary | Status |
|----------|--------|
| Draft state vs persisted profile | `proven` (local storage only) |
| Draft state vs memory | `proven` |
| Draft state vs chat history | `proven` |
| Validation vs enforcement | `proven` (config-level, no enforcement imports) |
| Save control vs backend persistence | `not proven` |
| Prompt field vs provider execution | `proven` |
| Provider/model draft vs live availability | `proven` |
| Permission draft vs enforcement | `proven` |
| Retrieval draft vs execution | `proven` |
| Runtime flag draft vs supported-profile override | `proven` |
| Draft/validation vs execution authority | `proven` |
| Persona Studio V1 vs C09/C10/C11 | `proven` |

## Forbidden Surface Checks

| Surface | Status |
|---------|--------|
| Memory write | `absent` |
| Chat-history write | `absent` |
| Backend profile persistence | `absent` |
| Database migration | `absent` |
| Permission enforcement | `absent` |
| Retrieval execution | `absent` |
| Provider routing change | `absent` |
| Prompt builder change | `absent` |
| System profile behavior change | `absent` |
| Daemon control | `absent` |
| Tool execution | `absent` |
| Pi/Coder execution | `absent` |
| Cloud fallback | `absent` |
| Live model availability claim | `absent` |

## Test Evidence

| Test file | Count | Coverage |
|-----------|-------|----------|
| `persona-studio-profile-draft-validation-boundary.test.tsx` | 9 | Storage key, seed state, round-trip, hook, locality, config-level validation, execution absence, memory absence |

No backend, daemon, network required.

## Gap Register

| Gap | Task |
|-----|------|
| Dirty state tracking not observed | Future |
| Reset/revert not observed | Future |
| Save to backend not proven | Future |
| Validation functions not observed | Future |
| Effective config preview not proven | C07-T005 |
| Permission/retrieval preview not proven | C07-T006 |

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Draft state mistaken for persisted backend profile | Local storage key proves locality |
| Validation types mistaken for enforcement | No runtime validation imports |
| Seed profiles contain default values that may be stale | C07-T005 effective config preview |

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C07-T005: Prove effective config preview without execution authority`
