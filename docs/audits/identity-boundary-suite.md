# Identity Boundary Suite

## Scope
<<<<<<< codex/add-identity-boundary-suite

This registry covers the first executable identity-boundary evaluation pack for the current broker-level retrieval seam.
It is intentionally narrow: it validates scope, exclusion, and trace visibility in retrieval behavior, not durable identity modeling.

## Interpretation Rule

Read these tests as broker-level contracts.
If a claim is not directly asserted by the retrieval result, candidate search order, or trace metadata, do not infer it from this suite.

## Identity Boundary Table

| Boundary | What it proves | What it does not prove | Test anchor | Release relevance |
| --- | --- | --- | --- | --- |
| Project scope stays local | Project mode resolves the active thread first, then widens only within the same user and same project. Cross-project candidates do not enter project-mode widening. | It does not prove global memory access, cross-persona sharing, or durable identity synthesis. | `test_identity_boundary_project_scope_stays_local` | Prevents project-scoped retrieval from leaking unrelated project context into completions. |
| Personal knowledge widening is explicit, not ambient | Personal knowledge mode is opt-in at the seam, keeps same-user constraints, and can widen across projects only when the broker says it may. The widened reason stays visible in trace metadata. | It does not prove universal memory, cross-user access, or any persistent identity graph. | `test_identity_boundary_personal_knowledge_widening_is_explicit` | Prevents accidental broadening of retrieval scope when a request is not explicitly in personal-knowledge mode. |
| Excluded material does not participate | Archived threads, `exclude_from_identity` threads, `modeling_excluded` threads, and other-user threads are filtered out of widening candidates before retrieval happens. | It does not prove data deletion, retention policy, or downstream sanitization outside the broker seam. | `test_identity_boundary_excludes_archived_and_other_user_threads` | Prevents stale or forbidden threads from contaminating identity-bearing retrieval. |
| Contract language stays honest | Invalid source-mode input normalizes back to project scope, active-thread search stays first, and the trace remains narrow instead of implying broader access. | It does not prove persona behavior, deep identity modeling, or any expanded default-memory contract. | `test_identity_boundary_active_thread_first_contract` | Prevents false narrative drift when request metadata is malformed or ambiguous. |

## Extension Notes

- Add future identity tests only when a new backend seam makes the claim directly observable.
- Keep assertions on concrete retrieval results, namespace order, and explicit trace fields.
- Do not promote retrieval proofs into claims about durable identity modeling unless the storage or modeling layer itself is tested.
- Do not infer cross-persona or cross-user sharing from project-local widening behavior.
- If a future test needs to prove identity state, anchor it at the storage or modeling boundary, not this retrieval suite.
=======
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
>>>>>>> main
