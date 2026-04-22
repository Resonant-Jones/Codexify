# Capabilities Audit Gap Analysis

**Date:** 2026-04-21
**Source:** `docs/architecture/capabilities-audit.md`

## Purpose

Track delta between stated capabilities audit and runtime proof over time.
Interpretation rule: runtime truth wins over documentation claims.

---

## Gap Summary

| Category | Count |
|---|---|
| ✅ Working (runtime-verified) | 6 |
| ⚠️ Partial | 2 |
| ❌ Aspirational / Not Implemented | 6 |

---

## Working Capabilities (Runtime-Verified)

| Capability | Audit Status | Evidence |
|---|---|---|
| Project Container System | runtime-active | `routes/projects.py` exists and functional |
| Threaded Interaction Layer | runtime-active | `routes/threads.py` - persistent thread identity |
| Conversational Interface | runtime-active | `routes/chat.py` - chat completion endpoints |
| Persona / Agent Layer | runtime-active, limited | `routes/persona_profiles.py`, `guardian/agents/` |
| Agent UI Panels | runtime-active | Frontend persona configuration surfaces |
| Mode Awareness | visible | `frontend/src/features/chat/hooks/useInferenceRequestState.ts` implements lifecycle states |

**State Machine Evidence:** Frontend hook `useInferenceRequestState.ts` defines `INFERENCE_LIFECYCLE_STATE` with values: `IDLE`, `QUEUED`, `AWAITING_MODEL`, `AWAITING_FIRST_TOKEN`, `STREAMING`, `COMPLETED`, `PROVIDER_ERROR`, `DEGRADED`, `CANCELLED`. This closely matches the canonical `ChatRequestState` defined in `chat-runtime-contract.md`.

---

## Partial Capabilities

| Capability | Audit Status | Gap |
|---|---|---|
| Workspace Visualization | runtime-active | Only returns thread metadata and linked documents (`routes/workspace.py`). No file system state visualization. |
| System Coherence | critical invariant | Distributed across UI components. No dedicated enforcement layer. |

---

## Aspirational / Not Implemented

| Capability | Audit Status | Evidence |
|---|---|---|
| Mode Switching | early/partial | ❌ No mode switching mechanism found in codebase |
| Execution Intent Recognition | early/partial | ❌ No intent detection system |
| Safe Execution Loop | early/partial | ❌ No bounded execution loop |
| File Interaction | constrained / mocked | ❌ No file read/write affordances in routes |
| Directory Binding | presentation-only | ❌ No directory binding implementation |
| Multi-Agent Routing | latent / internal | ❌ No multi-agent dispatch system |
| Intent Visibility | visible | ❌ No explicit intent surface |

---

## Evidence Sources

### Backend Routes Audited
- `guardian/routes/projects.py` - Project CRUD
- `guardian/routes/threads.py` - Thread management
- `guardian/routes/chat.py` - Chat completion
- `guardian/routes/workspace.py` - Workspace aggregation
- `guardian/routes/persona_profiles.py` - Persona configuration

### Frontend Hooks Audited
- `frontend/src/features/chat/hooks/useInferenceRequestState.ts` - Request lifecycle
- `frontend/src/features/chat/hooks/useProviderState.ts` - Provider state

### Key Implementation Files
- `guardian/core/capability_issuance.py` - Capability grant system
- `guardian/core/public_exposure.py` - Route exposure allowlist
- `guardian/protocol_tokens.py` - Executor state tokens

### Documentation Referenced
- `docs/architecture/chat-runtime-contract.md` - Canonical state definitions
- `docs/architecture/chat-runtime-gap-analysis.md` - Contract rationale

---

## Key Findings

1. **Chat Runtime Contract is Frontend-Implemented:** The canonical `ChatRequestState` and `ProviderRuntimeState` from the contract are implemented in `useInferenceRequestState.ts`, not enforced by backend.

2. **Action Thread Mode Section is Aspirational:** The entire "Action Thread Mode" section of the audit (Mode Switching, Execution Intent Recognition, Safe Execution Loop) has no runtime implementation.

3. **File System Layer is Mocked:** Workspace visualization returns DB-backed thread/doc metadata only—no actual file system interaction.

4. **Multi-Agent Routing Not Found:** No dispatcher or coordinator for multiple agents exists in current routes.

---

## Next Review Triggers

- [ ] Mode Switching implementation begins
- [ ] File read/write capability added
- [ ] Multi-agent dispatch system created
- [ ] Intent detection surfaces

---

## Change Log

| Date | Auditor | Summary |
|---|---|---|
| 2026-04-21 | big-pickle | Initial gap analysis vs `capabilities-audit.md` |
