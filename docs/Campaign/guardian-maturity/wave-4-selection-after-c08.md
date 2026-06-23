# Wave 4 Selection After C08 Closeout

## Scope

This is a docs-only selection artifact. It selects the next campaign only. It does **not** implement C07, start C09/C10/C11, add persona/profile runtime behavior, add execution authority, or widen release support.

## Current Trail

| Campaign | Status | Meaning |
|----------|--------|---------|
| C03 | closed | Coding delegation spine |
| C04 | closed | Pi/Coder invocation boundary |
| C05 | closed | Command bus and tool turn observability |
| C06 | closed | Guardian operator workspace |
| C08 | closed | Whoosh'd runtime integration and context fidelity |

## C08 Closeout Summary

C08 proved:
- Endpoint health semantics for Whoosh'd local runtime.
- Model inventory identity semantics (registry ID ≠ repo ID).
- Context fidelity at the focused provider-call payload boundary.
- Operator-visible runtime truth surfaces via `/api/health/llm` and `/api/health/chat`.

C08 did **not** prove execution authority, widen release support, or prove live daemon availability without endpoint inventory evidence. Full closeout at `docs/Campaign/guardian-maturity/campaigns/C08-whooshd-runtime-context-fidelity/campaign-closeout.md`.

## Candidate Slate

| Candidate | Why now | Risk | Dependency posture | Decision |
|-----------|---------|------|--------------------|----------|
| C07 Persona Studio | Local runtime proven — operator needs inspectable persona/profile configuration before execution authority | LOW — frontend/config | C08 provides runtime substrate; C06 provides operator workspace | **Selected** |
| C09 Pi/Coder Execution Authority | Governed execution seam — but needs identity/configuration layer underneath | HIGH — needs C07 or equivalent | Needs C07 for operator-facing identity and permissions | Deferred |
| C10 Pi/Coder Result Return & Receipt Lineage | Follows C09 — premature without execution authority | MED | Needs C09 | Deferred |
| C11 Pi/Coder Sandbox Worker | Follows C09 — premature without execution authority | HIGH | Needs C09 | Deferred |

## Selection Decision

**Selected: C07 Persona Studio**

## Reasoning

C08 proved the local runtime spine is wired correctly. The next release-protective move is to make persona/profile identity and configuration inspectable: persona profiles, tool permissions, retrieval posture, runtime flags, and effective configuration should be bounded before expanding execution authority.

C07 protects the user-facing beta path more directly than jumping to execution authority. The operator should be able to see and configure *who* is speaking through the system before being asked to trust that the system can delegate execution.

C09 execution authority should follow C07 or an equivalent identity/configuration proof. C10 and C11 depend on C09 and are premature.

## Architecture-Impact Classification

- **Classification**: Aligned with existing ADR(s) / architecture contracts
- **Governing docs**:
  - `docs/architecture/00-current-state.md`
  - `docs/architecture/README.md`
  - `docs/architecture/persona-studio-spec.md`
  - `docs/architecture/config-and-ops.md`
  - `docs/architecture/modules-and-ownership.md`
  - `docs/architecture/ui-diagrams-v1.md`
  - `docs/architecture/chat-runtime-contract.md`
  - `docs/architecture/runtime-protocol-token-contract.md`
  - `docs/architecture/pi-invocation-boundary-contract.md`
  - `docs/architecture/agent-tool-loop-contract.md`
  - `docs/Campaign/guardian-maturity/campaigns/C08-whooshd-runtime-context-fidelity/campaign-closeout.md`
- **Brief reason**: This selection changes campaign sequencing and must preserve identity, permission, retrieval, runtime, and execution-authority boundaries.

## Current-Truth Anchors

- **What is true now**: C08 is closed. C07 is selected next. C07 implementation has not started. C09/C10/C11 remain deferred. Execution authority remains out of scope. Current local-first beta posture remains unchanged. Live model availability remains bounded by `/v1/models` or `/api/tags`.
- **What is not yet true**: C07 persona/profile configuration is not operator-visible or bounded. Execution authority is not proven. C09/C10/C11 have not started.
- **What this selection may assume**: It may create a selection artifact. It may update the Guardian Maturity README. It may name C07-T001 by name only. It may not start implementation.

## Invariants

- Do not widen release claims.
- Do not imply execution authority.
- Do not imply Persona Studio runtime implementation exists if not already proven.
- Persona/profile configuration must not own identity.
- Studio actions must not write memory or chat history.
- Tool permissions must remain explicit and inspectable.
- Retrieval policy must remain explicit and bounded.
- Runtime flags must not silently override supported-profile posture.
- C09 execution authority must not start inside C07 selection.
- C10/C11 remain downstream of C09.

## Proof Surface

This is docs-only. Required proof:
- Selection artifact exists.
- README points to the selection artifact.
- No code/test/runtime files changed.
- Docs validation passes.
- `git diff --check` passes.

## Deferred Work

- C07 implementation task prompt remains future work.
- C09 remains future campaign.
- C10 remains future campaign.
- C11 remains future campaign.
- Wave 4 follow-on after C07 remains undecided.

## Final Gate

- **Decision**: `go`
- **Next task by name only**: `C07-T001: Persona Studio current surface and contract seam audit`
