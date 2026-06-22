# C08-T001 Seam Audit: Whoosh'd Runtime Configuration & Model Inventory

## Gate Decision

**`go`** — C08-T002 may proceed by name only.

## Scope

This is a seam audit only. It does **not** change runtime behavior, provider routing, context injection, model inventory behavior, prompt construction, frontend controls, Whoosh'd daemon behavior, environment variables, secrets, migrations, ADRs, or release claims.

## Current Truth Summary

### What Is True Now

- **Whoosh'd sidecar provider** exists at `guardian/providers/whooshd_sidecar.py` with full lifecycle management: detect, launch, health-poll, stop. Communicates over HTTP. Respects ownership (external vs Codexify-launched).
- **Whoosh'd model profiles** exist at `guardian/core/whooshd_model_profiles.py` with file-backed registry at `config/whooshd/model-profiles/`.
- **Local runtime presets** exist at `guardian/core/local_runtime_presets.py` with `whooshd-mlx` preset, `WHOOSHD_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"`, and alias support.
- **MLX server** exists at `services/mlx_server/app.py`.
- **Provider registry** (`guardian/core/provider_registry.py`), **LLM catalog** (`guardian/core/llm_catalog.py`), and **AI router** (`guardian/core/ai_router.py`) handle provider selection.
- **Chat completion service** (`guardian/core/chat_completion_service.py`) handles completion routing.
- **Runtime config** (`guardian/config/core.py`) handles environment variables.
- **Docker Compose** files include Whoosh'd service definitions.

### What Is NOT True (and must not be claimed)

- Whoosh'd context fidelity is not proven at call site.
- Whoosh'd system identity delivery is not proven.
- Whoosh'd model inventory truth is not operator-visible.
- Operator cannot inspect runtime/provider truth for Whoosh'd in the workspace.
- Local-only posture proof at the model call boundary is not audited.

## File Inventory

| File | Seam Group | Current Role | Confidence | Notes |
|------|-----------|-------------|------------|-------|
| `guardian/providers/whooshd_sidecar.py` | Provider | Whoosh'd sidecar lifecycle: detect, launch, health-poll, stop | HIGH | Proven implementation |
| `guardian/core/whooshd_model_profiles.py` | Model inventory | File-backed model profile registry | HIGH | Profiles at `config/whooshd/model-profiles/` |
| `guardian/core/local_runtime_presets.py` | Runtime config | Preset definitions: `whooshd-mlx`, model IDs, aliases | HIGH | `WHOOSHD_MODEL` + `WHOOSHD_ALIAS_MODEL` |
| `services/mlx_server/app.py` | Provider endpoint | MLX server (HTTP API) | HIGH | Backing server for Whoosh'd |
| `guardian/core/provider_registry.py` | Provider routing | Provider registration/lookup | MED | Needs inspection for context injection |
| `guardian/core/llm_catalog.py` | Provider routing | Model-to-provider catalog | MED | Lists "coder" provider, needs Whoosh'd model audit |
| `guardian/core/ai_router.py` | Provider routing | Routes completion calls to providers | MED | Context bundle boundary |
| `guardian/core/chat_completion_service.py` | Context fidelity | Constructs completion requests, injects messages | MED | System identity + context assembly point |
| `guardian/config/core.py` | Runtime config | Environment variable management | HIGH | Config source of truth |
| `guardian/routes/chat.py` | Context fidelity | Chat completion endpoint | MED | Upstream caller |
| `guardian/core/provider_state.py` | Runtime truth | Provider state tracking | MED | Truth surface for provider status |
| `frontend/src/features/personaStudio/` | Runtime config UI | Persona configuration, model selection | MED | Model picker, profile UI |
| `docker-compose.yml` | Runtime config | Whoosh'd service definition | HIGH | Deployment config |
| `CHANGELOG.md` | Docs | Release notes mentioning Whoosh'd | LOW | Docs — not runtime proof |

## Runtime Configuration Map

| Config Element | Source | Default/Value | Consuming Code | Drift Risk |
|---------------|--------|---------------|----------------|------------|
| `WHOOSHD_ALIAS_MODEL` | `local_runtime_presets.py` | `mlx-community/Llama-3.2-3B-Instruct-4bit` | Provider registry, sidecar | Model name drift between preset and profile |
| Whoosh'd sidecar port | Environment/docker-compose | `8000` (from compose) | `whooshd_sidecar.py` | Port mismatch between compose and local |
| MLX server endpoint | `services/mlx_server/` | HTTP | Sidecar communicates with MLX | MLX server vs sidecar URL mismatch |
| Model profile directory | `whooshd_model_profiles.py` | `config/whooshd/model-profiles/` | Profile registry | Missing profile files |
| Local-only mode | `guardian/config/core.py` | Configurable | Provider selection | Cloud fallback not blocked |
| Runtime preset | `local_runtime_presets.py` | `whooshd-mlx` | Provider selection | Preset name drift |
| Provider catalog | `llm_catalog.py` | "coder" provider listed | Provider routing | Whoosh'd not explicitly listed in catalog |

## Model Inventory Map

| Element | Source | Semantics | Risk |
|---------|--------|-----------|------|
| Model ID | `WHOOSHD_MODEL` | HuggingFace repo ID: `mlx-community/Llama-3.2-3B-Instruct-4bit` | Repo ID = registry ID — stable but not operator-visible |
| Model alias | `WHOOSHD_ALIAS_MODEL` | Same as model ID (alias = canonical) | No display-name separation |
| Profile-based models | `config/whooshd/model-profiles/*.json` | File-backed model definitions | Not swept for operator-facing inventory |
| Provider catalog entry | `llm_catalog.py` | "coder" provider — Whoosh'd not explicitly listed | Whoosh'd identity hidden in catalog |
| `/v1/models` | Unknown | May or may not be queried by sidecar | Not audited for this task |
| Model family labeling | None found | MLX, GGUF, Ollama, LM Studio not labeled | Operator cannot distinguish runtime families |
| Collision risk | Medium — HuggingFace repo IDs | Same model served by multiple providers possible | No provider-specific model differentiation |
| Model inventory operator visibility | None found in workspace | No Whoosh'd-specific model inventory in C06 workspace | Gap |

## Context Fidelity Map

| Seam | Location | Status | Risk |
|------|----------|--------|------|
| System identity assembly | `chat_completion_service.py` | Known entry point | Not proven for Whoosh'd call boundary |
| Context bundle assembly | `chat_completion_service.py` | Known entry point | Not proven for Whoosh'd call boundary |
| Retrieval evidence injection | `chat_completion_service.py` or upstream | Assembly point | Must be verified for Whoosh'd path |
| Provider dispatch | `ai_router.py` → `whooshd_sidecar.py` | Routing chain | Context may drop before sidecar receives it |
| Message construction | `chat_completion_service.py` | System/user/assistant/tool ordering | Must be verified at Whoosh'd call site |
| Identity delivery proof | None found | No explicit verification layer | Context may arrive at Whoosh'd without Codexify identity markers |
| C04 provider-lane integration | `guardian/pi/tokens.py` | `PiProviderLaneClass.LOCAL` | Lane concept exists but Whoosh'd lane compliance not proven |

## Runtime Truth Surface Map

| Surface | Location | Whoosh'd Visibility | Gap |
|---------|----------|--------------------|------|
| Provider state | `provider_state.py` | Provider status tracking | Whoosh'd-specific state visible? |
| Model inventory UI | `personaStudio/` | Model picker | Whoosh'd models distinguishable? |
| Operator workspace | C06 | General provider/runtime cards | No Whoosh'd-specific runtime truth card |
| Health endpoints | Backend health routes | Provider health | Whoosh'd-specific health check visible? |
| Sidecar status | `whooshd_sidecar.py` | Internal — not exposed to operator | Sidecar state not operator-visible |
| Model warming status | `whooshd_sidecar.py` (`WhooshdState.MODEL_WARMING`) | Internal | Operator cannot see warming state |
| Local-only posture | Config | Not operator-visible at call boundary | Operator cannot verify local-only is enforced |

## Gap Register

| Gap | Severity | Evidence |
|-----|----------|----------|
| Whoosh'd model identity not operator-visible | HIGH | No Whoosh'd-specific model inventory in C06 workspace |
| Context fidelity not proven at Whoosh'd call boundary | HIGH | No explicit verification layer |
| System identity delivery not proven | HIGH | No identity markers verified in Whoosh'd request |
| Whoosh'd not explicitly in provider catalog | MED | "coder" entry in `llm_catalog.py` — no Whoosh'd entry |
| Local-only posture not proven at call site | MED | Config exists, enforcement not audited |
| Model warming state not operator-visible | MED | `WhooshdState.MODEL_WARMING` is internal only |
| Sidecar ownership state not operator-visible | LOW | PID/session tracking is internal |
| `/v1/models` support status unknown | MED | Not audited for this task |
| Whoosh'd model profile collision risks unknown | LOW | Multiple profiles referencing same model untested |

## Risk Register

| Risk | Blast Radius | Mitigation (future task by name) |
|------|-------------|----------------------------------|
| Model ID ambiguity between preset, profile, and runtime | Operator sees wrong model connected | C08-T002 endpoint config proof |
| Context bundle dropped before Whoosh'd | Model operates without retrieval/identity context | C08-T004 context bundle proof |
| System identity absent from Whoosh'd messages | Model has no Codexify identity markers | C08-T004 system identity proof |
| Local-only silently falls back to cloud | Provider routes to cloud without operator awareness | C08-T002 local-only posture proof |
| Model warming state hidden from operator | Operator sees "offline" when model is loading | C08-T005 runtime truth surface |
| Whoosh'd model inventory invisible | Operator cannot confirm loaded model | C08-T003 model inventory proof |
| Provider catalog entry missing for Whoosh'd | Provider selection UI may omit Whoosh'd | C08-T003 catalog entry proof |

## C08 Task Candidate List

Name only — no implementation details.

1. `C08-T001: Whoosh'd runtime configuration and model inventory seam audit` ← THIS TASK
2. `C08-T002: Prove Whoosh'd endpoint configuration and health-check semantics`
3. `C08-T003: Prove Whoosh'd model inventory identity semantics`
4. `C08-T004: Prove Whoosh'd context bundle and system identity delivery`
5. `C08-T005: Expose Whoosh'd runtime truth in operator diagnostics`
6. `C08-T006: Close C08 Whoosh'd runtime context fidelity proof`

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C08-T002: Prove Whoosh'd endpoint configuration and health-check semantics`
