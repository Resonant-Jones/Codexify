# Identity Boundary Suite

## Scope

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
