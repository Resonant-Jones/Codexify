# Golden Task Suite

## Scope
This suite is the first executable evaluation layer for the supported beta path. It only covers backend seams that already exist in the local Docker Compose posture:
- chat completion acceptance at the queue boundary
- latest RAG trace retrieval and isolation
- supported retrieval availability through builtin-help startup seeding

## Interpretation Rule
A golden task passing means the supported-path contract still holds at the backend seam under test. It does not imply the whole system is healthy, the worker has finished, or the broader runtime path has been exercised end to end.

## Golden Tasks

| Task | What it proves | What it does not prove | Test anchor | Runtime relevance |
| --- | --- | --- | --- | --- |
| Completion acceptance contract | `POST /api/chat/{thread_id}/complete` returns a queue-acceptance payload with `acceptance_status`, `acceptance_warnings`, `task_id`, and the supported trace/messages URLs. It proves accepted work is queued, not terminally completed. | It does not prove worker execution, assistant persistence, or final completion payloads. | `tests/golden/test_supported_beta_golden_tasks.py::test_golden_completion_acceptance_contract` | Prevents acceptance/completion ambiguity in the supported beta flow. |
| RAG trace latest and isolation | Latest RAG trace is returned when completion evidence exists, untouched threads return the empty trace shape, and thread-local traces do not bleed across thread IDs. | It does not prove production retriever ranking, live persistence backends, or browser-visible debug UI. | `tests/golden/test_supported_beta_golden_tasks.py::test_golden_rag_trace_latest_and_isolation` | Protects the debug/proof surface used to verify thread-scoped retrieval behavior. |
| Supported retrieval path | Builtin help is seeded at backend startup and is retrievable through the supported backend route seam. | It does not prove the full upload -> parse -> embed -> retrieve pipeline or broader corpus coverage. | `tests/golden/test_supported_beta_golden_tasks.py::test_golden_supported_retrieval_path` | Confirms the supported local stack boots with retrievable system docs. |

## Extension Notes
Keep this suite small. Add a new golden task only when a supported-path contract is being promoted from ad hoc tests into a release gate.

Do not turn this into a checklist of every backend behavior. If a future release needs to cover a new seam, add a narrowly scoped golden task with a single explicit proof target and a clearly stated non-goal.

Prefer route/service-level evidence that already exists in the repo. If a proposed golden task would require a new harness, it probably belongs in a separate focused test file first.
