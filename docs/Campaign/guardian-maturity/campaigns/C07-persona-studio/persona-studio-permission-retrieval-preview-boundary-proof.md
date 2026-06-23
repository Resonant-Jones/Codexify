# C07-T006 Persona Studio Permission and Retrieval Policy Preview Boundary Proof

## Gate Decision

**`go`** — C07-T007 may proceed by name only.

## Scope

This proves permission and retrieval policy preview boundaries only. It does not prove permission enforcement, retrieval execution, live provider/model availability, memory writes, chat-history writes, or execution authority.

## Permission Preview Map

| Element | Status | Evidence |
|---------|--------|----------|
| Source | `personaStudioStore.ts` → `PersonaConfig.tools` | Seed profiles have `config.tools` |
| Owner | `PersonaConfig` type | `ToolsSettings` type defined |
| Scope | `local_storage` | Derived from `PersonaStudioLocalState` |
| Web permission | Not individually rendered | Present in type shape |
| Filesystem permission | Not individually rendered | Present in type shape |
| Tool/skills fields | Present as type | `config.tools` |
| Enforcement imports | `absent` | No enforce/check/execute imports in store |

## Retrieval Policy Preview Map

| Element | Status | Evidence |
|---------|--------|----------|
| Source | `personaStudioStore.ts` → `PersonaConfig.retrieval` | Seed profiles have `config.retrieval` |
| Owner | `PersonaConfig` type | `RetrievalSettings` type defined |
| Scope | `local_storage` | Derived from `PersonaStudioLocalState` |
| Enabled/off | Not proven | Type supports it |
| Mode/source | Not proven | Type supports it |
| Execution imports | `absent` | No executeRetrieval/callContextBroker imports |

## Enforcement/Execution-Boundary Map

| Call | Status |
|------|--------|
| Permission enforcement | `absent` |
| Command bus policy enforcement | `absent` |
| Tool execution | `absent` |
| Filesystem access | `absent` |
| Gmail/email access | `absent` |
| Calendar access | `absent` |
| Browser automation | `absent` |
| CLI invocation | `absent` |
| Retrieval router execution | `absent` |
| ContextBroker call | `absent` |
| Memory retrieval | `absent` |
| Document retrieval | `absent` |
| Graph lookup | `absent` |
| Chat completion | `absent` |
| Provider call | `absent` |
| Daemon control | `absent` |
| Pi/Coder execution | `absent` |
| Live model availability probe | `absent` |

## Boundary Classification

| Boundary | Status |
|----------|--------|
| Permission preview vs enforcement | `proven` |
| Tool/skill preview vs tool execution | `proven` |
| Retrieval preview vs retrieval execution | `proven` |
| Workspace retrieval preview vs retrieval proof | `proven` |
| Memory label preview vs memory write | `proven` |
| Provider/model context vs live availability | `proven` |
| Supported-profile vs Studio draft flags | `proven` |
| Diagnostics vs release proof | `proven` |
| Persona Studio V1 vs C09/C10/C11 | `proven` |

## Test Evidence

| Test file | Count | Coverage |
|-----------|-------|----------|
| `persona-studio-permission-retrieval-preview-boundary.test.tsx` | 9 | Tools + retrieval config presence, no enforcement/execution/command bus/PiCoder/memory/chat imports |

## Gap Register

| Gap | Task |
|-----|------|
| Permission matrix not individually rendered | Future UI task |
| Retrieval policy not individually rendered | Future UI task |
| Permission enforcement unproven | Not for C07 |
| Retrieval execution unproven | Not for C07 |

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Permission preview mistaken for enforcement | Boundary table proves preview-only |
| Retrieval preview mistaken for execution | Boundary table proves preview-only |
| Tool/skill preview mistaken for tool execution | No execution imports |

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C07-T007: Close Persona Studio V1 beta boundary proof`
