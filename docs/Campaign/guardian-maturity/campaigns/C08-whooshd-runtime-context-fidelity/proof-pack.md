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

---

## C08-T001-R1: README Consistency Closeout (2026-06-20 03:35 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `58c8eec27` | **Worktree**: clean
- **Prior `next-proof-needed` reason**: Guardian Maturity README not updated with C08 active status.

### Consistency Fixed
- `README.md`: C08 updated to `active — C08-T001 seam audit accepted` in Wave Status table
- Campaign index: not applicable (no `campaigns/README.md` exists)
- All other C08 docs remain consistent

### Gate Decision
**`go`** — C08-T001-R1 accepted. C08-T002 may proceed.

### Next Task
**C08-T002: Prove Whoosh'd endpoint configuration and health-check semantics**

---

## C08-T001-R2: Final Docs Validation Closeout (2026-06-20 03:40 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `f3f621e2c` | **Worktree**: clean
- **Prior `next-proof-needed` reason**: `python3 scripts/validate_docs.py` not reported after R1 README consistency commit.

### Final Validation
- `python3 scripts/validate_docs.py`: **passed**
- `git diff --check`: clean
- All C08 governance docs consistent: README, backlog, proof-pack, decision-log
- Campaign index: not applicable

### Gate Decision
**`go`** — C08-T001-R2 accepted. C08-T002 may proceed.

### Next Task
**C08-T002: Prove Whoosh'd endpoint configuration and health-check semantics**

---

## C08-T002: Endpoint Health Proof (2026-06-20 03:50 UTC)

### Context
- **Branch**: `codex/campaignOS` | **Commit**: `b86423175` | **Worktree**: clean

### Files Created
- `tests/providers/test_whooshd_endpoint_health_semantics.py` — 16 tests
- `endpoint-health-proof.md` — endpoint config, health map, truth table, boundary table, gaps, risks

### Proof Summary
Base URL from `WHOOSHD_HOST`:`WHOOSHD_PORT`. Health probes: `/health` → `/health/runtime` → `/v1/models` → `/api/tags`. Timeout 5s. States: OFFLINE → ERROR → RUNTIME_AVAILABLE → MODEL_WARMING → READY. Ownership: NONE/EXTERNAL/MANAGED. All proven without real daemon.

### Validation
```
endpoint health tests: 16 passed
git diff --check: clean
python3 scripts/validate_docs.py: passed
```

### Gate Decision
**`go`** — C08-T002 accepted. C08-T003 may proceed.

### Next Task
**C08-T003: Prove Whoosh'd model inventory identity semantics**
