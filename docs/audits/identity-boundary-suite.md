# Identity Boundary Suite

## Scope
This suite is the first executable evaluation layer for the supported identity-boundary path. It only covers backend seams already present in the local Docker Compose posture and stays at the broker/route level:
- project-scoped widening remains local to the active user and project
- personal-knowledge widening is explicit and still same-user bound
- archived, `exclude_from_identity`, and other-user threads are excluded from identity-bearing widening
- active-thread-first remains the default contract even when widening is eligible

## Interpretation Rule
A passing identity boundary task means the current backend seam still enforces the intended scope boundary. It does not mean identity modeling is globally implemented, that persona sharing is live across surfaces, or that broader memory behavior has been proven end to end.

## Identity Boundary Tasks

| Boundary | What it proves | What it does not prove | Test anchor | Release relevance |
| --- | --- | --- | --- | --- |
| Project scope stays local | Project mode searches the active thread first and only widens inside the same project. Cross-project candidates are not searched in project mode. | It does not prove cross-project identity sharing, durable persona binding, or broad memory propagation. | `tests/identity/test_identity_boundary_contract.py::test_identity_boundary_project_scope_stays_local` | Prevents project-local retrieval from drifting into a broader identity scope. |
| Personal knowledge widening is explicit | Personal-knowledge mode can widen beyond the active thread only through the explicit supported seam, and the trace reports that widening reason. | It does not prove ambient global memory access or user-to-user sharing. | `tests/identity/test_identity_boundary_contract.py::test_identity_boundary_personal_knowledge_widening_is_explicit` | Keeps the broader mode honest about when widening is actually invoked. |
| Excluded material does not participate | Archived threads, `exclude_from_identity` threads, and other-user threads are not considered eligible widening candidates. | It does not prove a universal policy across every future retrieval path or every storage backend. | `tests/identity/test_identity_boundary_contract.py::test_identity_boundary_excludes_archived_and_other_user_threads` | Protects the release boundary from hidden identity leaks. |
| Contract language stays honest | Invalid or non-supported source-mode input falls back to the narrow supported project contract while still searching the active thread first. | It does not prove new source modes, richer persona semantics, or a stronger identity model than the broker seam exposes. | `tests/identity/test_identity_boundary_contract.py::test_identity_boundary_active_thread_first_contract` | Prevents narrative drift where fallback behavior gets described as broader identity capability. |

## Extension Notes
Add future identity tests only when a current backend seam becomes provable with the same level of evidence. Keep each new task narrow, backend-only, and scoped to a single boundary claim.

Do not overclaim beyond the seam under test. If a future behavior is only observable at the broker, route, or service layer, describe it at that layer and avoid presenting it as a full identity system guarantee.
