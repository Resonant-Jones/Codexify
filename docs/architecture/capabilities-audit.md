# Codexify — Capabilities Audit (Signal Build Assessment)

## 1. Title + Framing

This is an audit, not a feature list.
It classifies runtime capability exposure, not speculative architecture.

- Operational Capabilities: behaviors the runtime can actually perform.
- Exposed Capabilities: operational behaviors intentionally surfaced at the operator boundary.
- Latent Capabilities: real system capabilities that remain withheld, mocked, partial, or protected.

Interpretation rule: short-horizon truth still comes from the operational source of truth; if this audit conflicts with current runtime truth, runtime truth wins.
UI canon can shape presentation expectations, but it does not overwrite runtime truth.

## 2. Core System Capabilities (Operational Reality)

| Capability | What it enables | Status | Risk Level | Release classification |
|---|---|---|---|---|
| Project Container System | Project-scoped ownership, context continuity, and bounded work organization. | runtime-active | low | FULLY EXPOSE |
| Threaded Interaction Layer | Persistent thread identity, turn continuity, and history-aware collaboration. | runtime-active | low | FULLY EXPOSE |
| Conversational Interface | Direct dialogue with the system through the supported chat surface. | runtime-active | low | FULLY EXPOSE |
| Persona / Agent Layer | Role-scoped presentation and configuration framing without broadening runtime authority. | runtime-active, limited | medium | EXPOSE VISUALLY (LIMIT FUNCTIONALITY) |

## 3. Execution-Oriented Capabilities

### Action Thread Mode

This parent section is early/partial, high risk, and limited to sandboxed exposure.

| Capability | What it enables | Status | Risk Level | Release classification | Release strategy |
|---|---|---|---|---|---|
| Mode Switching | Moving between standard conversation and action-oriented operation. | early/partial | high | EXPOSE | limited/sandboxed exposure only |
| Execution Intent Recognition | Detecting that a user message is intended to trigger action, not just discussion. | early/partial | high | HOLD BACK | limited/sandboxed exposure only |
| Safe Execution Loop | Constraining action execution into a bounded, observable, recoverable loop. | early/partial | high | HOLD BACK | limited/sandboxed exposure only |

## 4. Workspace / File System Layer

Workspace surface canon applies here as presentation guidance. It defines presentation expectations, not runtime authority.

| Capability | What it enables | Status | Risk Level | Release classification |
|---|---|---|---|---|
| Workspace Visualization | Visible workspace state, selection context, and user-orienting presentation. | runtime-active | low | FULLY EXPOSE |
| File Interaction | File read/write affordances under constrained surface rules. | constrained / mocked | high | LIMIT or MOCK |
| Directory Binding | UI-level association of workspace context with a directory target. | presentation-only | medium | IMPLY via UI |

## 5. Agent Configuration Layer

| Capability | What it enables | Status | Risk Level | Release classification |
|---|---|---|---|---|
| Agent UI Panels | Visual configuration surfaces for agent-related settings and state. | runtime-active | medium | EXPOSE VISUALLY |
| Multi-Agent Routing | Dispatching and coordinating work across multiple agents. | latent / internal | high | HOLD BACK |

## 6. System Architecture Capabilities (Protected Layer)

DO NOT EXPOSE.

These map to core runtime layers such as retrieval, provider routing, and execution orchestration. They are internal system responsibilities and remain outside the release surface.

| Capability | What it enables | Status | Risk Level | Release classification |
|---|---|---|---|---|
| Context packing / retrieval strategy | Selecting, ordering, and shaping the context that enters model execution. | internal | high | DO NOT EXPOSE |
| Execution orchestration logic | Dispatch, sequencing, retry, and completion control for operational flows. | internal | high | DO NOT EXPOSE |
| Persona engine internals | Internal resolution of persona state, precedence, and configuration binding. | internal | high | DO NOT EXPOSE |
| Model routing / adapter layer | Provider selection and adapter mediation behind the runtime boundary. | internal | high | DO NOT EXPOSE |

## 7. UX-Level Capabilities

| Capability | What it enables | Status | Risk Level | Release classification |
|---|---|---|---|---|
| System Coherence | A consistent surface model across modes, panes, and state transitions. | critical invariant | high | CRITICAL |
| Mode Awareness | Clear visibility into the current operating mode. | visible | medium | EXPOSE CLEARLY |
| Intent Visibility | Surface-level clarity about what the system believes the user is asking for. | visible | medium | EXPOSE |

## 8. Release Matrix

This matrix is derived from the classifications above. It is not a separate architecture layer.

### FULLY EXPOSE

| Capability | Source section | Why it is here |
|---|---|---|
| Project Container System | Core System Capabilities | Already runtime-active and safe to present directly. |
| Threaded Interaction Layer | Core System Capabilities | Core collaboration path and stable user-facing behavior. |
| Conversational Interface | Core System Capabilities | Primary supported interaction model. |
| Workspace Visualization | Workspace / File System Layer | Presentation surface only; no hidden authority. |
| System Coherence | UX-Level Capabilities | Critical invariant that must remain legible everywhere. |

### EXPOSE (LIMITED / PARTIAL)

| Capability | Source section | Why it is here |
|---|---|---|
| Persona / Agent Layer | Core System Capabilities | Visible, but functional breadth stays constrained. |
| Mode Switching | Execution-Oriented Capabilities | Exposed only in a sandboxed, bounded form. |
| File Interaction | Workspace / File System Layer | Present, but limited or mocked. |
| Directory Binding | Workspace / File System Layer | Implied through UI context, not treated as authority. |
| Agent UI Panels | Agent Configuration Layer | Visual configuration surface only. |
| Mode Awareness | UX-Level Capabilities | Must be surfaced clearly, but not overclaimed. |
| Intent Visibility | UX-Level Capabilities | Needs to be visible without exposing internals. |

### HOLD BACK

| Capability | Source section | Why it is here |
|---|---|---|
| Execution Intent Recognition | Execution-Oriented Capabilities | Early/partial and high risk; keep sandboxed. |
| Safe Execution Loop | Execution-Oriented Capabilities | Early/partial and high risk; keep sandboxed. |
| Multi-Agent Routing | Agent Configuration Layer | Internal coordination logic stays latent. |

Protected system architecture capabilities remain outside the matrix because they are DO NOT EXPOSE.

## 9. Strategic Insight

- Protection of velocity, not code: the goal is to keep the operator moving quickly without exposing incomplete control surfaces that would slow decisions or create false confidence.
- Exposure vs copyability framing: the surface should reveal enough to be legible and usable, but not enough to hand over the internal mechanisms that make the system hard to reproduce.

## 10. Final Test

If someone cloned what I'm showing today, would they still be behind me in 2 weeks?
