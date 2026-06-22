# C08 Proof Pack: Whoosh'd Runtime Integration & Context Fidelity

---

## C08-T001: Seam Audit (2026-06-20 03:30 UTC)

### Files Created
- `runtime-config-model-inventory-seam-audit.md` — 17 files, 7 gaps, 7 risks, 6-task backlog
- `backlog.md` — 6 tasks, C08-T002 next
- `proof-pack.md` — this file
- `decision-log.md` — C08-D001 entry

### Discovery Commands Run
1. `rg -n "Whoosh|whoosh|whooshd|mlx|gguf|ollama|..."` — 30+ files found
2. `rg -n "system_identity|context_bundle|retrieval_evidence|..."` — 10+ files found
3. Targeted file reads: `whooshd_sidecar.py`, `whooshd_model_profiles.py`, `local_runtime_presets.py`

### Key Findings
- **Whoosh'd sidecar provider** (`guardian/providers/whooshd_sidecar.py`) — full lifecycle: detect, launch, health-poll, stop. Implements `WhooshdState.OFFLINE/STARTING/RUNTIME_AVAILABLE/MODEL_WARMING`.
- **Model profiles** (`guardian/core/whooshd_model_profiles.py`) — file-backed at `config/whooshd/model-profiles/`.
- **Local runtime presets** (`guardian/core/local_runtime_presets.py`) — `whooshd-mlx` preset, `WHOOSHD_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"`.
- **7 gaps**: model identity invisibility, context fidelity unproven, system identity unproven, catalog entry missing, local-only posture unproven, warming state hidden, `/v1/models` status unknown.
- **7 risks** with name-only mitigations.

### Gate Decision
**`go`** — C08-T001 accepted. C08-T002 may proceed.

### Next Task
**C08-T002: Prove Whoosh'd endpoint configuration and health-check semantics**
