# CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0

## Metadata

- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Repo: <REPO_ROOT>
- Branch: feat/flow-compiler-v0
- Baseline commit (HEAD at campaign start): <BASELINE_COMMIT_HASH>
- Runner Protocol: Runner_Protocol.md
- Constraints:
  - Manual commits required (index.lock may block git add/commit in Runner env)
  - Two-phase commit per task:
    - Commit A = implementation/test/config
    - Commit B = docs finalize (task artifact + campaign mapping)
  - Commit policy: --no-verify (branch-contained)

## Goal

Implement a Flow Builder foundation: FlowSpec schema + primitive contracts + Flow Compiler + Flow Runner + two-stage NL→FlowSpec (Guardian tool interface), with API endpoints, examples, and tests.

## Definition of Done

- All tasks completed with mapping: TASK-ID -> [CommitA, CommitB]
- Working tree clean after each task (no out-of-scope artifacts)
- Any generated artifacts are reverted/removed unless explicitly allowed

## Global definitions (apply to all tasks)

### FlowSpec v0.1 invariants

- Deterministic execution: runtime routing is driven by FlowSpec, not LLM.
- LLM only allowed inside typed primitives (e.g., summarize/classify/plan) and must return schema-valid output.
- Budgets enforced: max_steps, max_tokens, timeout_seconds.
- Idempotency enforced via idempotency.key (template or explicit).
- Audit trace mandatory per run.
- Escalation: if confidence < threshold OR compiler warnings exist, require user confirmation (no side effects).

## Task Index
>
> Each task has a task artifact at docs/tasks/<TASK_ARTIFACT>.md  
> Each task maps to two commits: [CommitA, CommitB]

1. TASK-2026-02-12-001_repo_scaffold
   - Task artifact: `docs/tasks/TASK_2026_02_12_001_repo_scaffold.md`
   - Task mapping: `TASK-2026-02-12-001_repo_scaffold -> [<commitA>, <commitB>]`

2. TASK-2026-02-12-002_flowspec_models_and_schema_export
   - Task artifact: `docs/tasks/TASK_2026_02_12_002_flowspec_models_and_schema_export.md`
   - Task mapping: `TASK-2026-02-12-002_flowspec_models_and_schema_export -> [<commitA>, <commitB>]`

3. TASK-2026-02-12-003_primitive_contracts_and_registry
   - Task artifact: `docs/tasks/TASK_2026_02_12_003_primitive_contracts_and_registry.md`
   - Task mapping: `TASK-2026-02-12-003_primitive_contracts_and_registry -> [<commitA>, <commitB>]`

4. TASK-2026-02-12-004_flow_compiler_normalize_validate
   - Task artifact: `docs/tasks/TASK_2026_02_12_004_flow_compiler_normalize_validate.md`
   - Task mapping: `TASK-2026-02-12-004_flow_compiler_normalize_validate -> [<commitA>, <commitB>]`

5. TASK-2026-02-12-005_flow_runner_execute_trace
   - Task artifact: `docs/tasks/TASK_2026_02_12_005_flow_runner_execute_trace.md`
   - Task mapping: `TASK-2026-02-12-005_flow_runner_execute_trace -> [<commitA>, <commitB>]`

6. TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating
   - Task artifact: `docs/tasks/TASK_2026_02_12_006_guardian_nl_to_flowspec_two_stage_gating.md`
   - Task mapping: `TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating -> [<commitA>, <commitB>]`

7. TASK-2026-02-12-007_flow_builder_api_endpoints
   - Task artifact: `docs/tasks/TASK_2026_02_12_007_flow_builder_api_endpoints.md`
   - Task mapping: `TASK-2026-02-12-007_flow_builder_api_endpoints -> [<commitA>, <commitB>]`

8. TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec
   - Task artifact: `docs/tasks/TASK_2026_02_12_008_examples_utterances_to_compiled_flowspec.md`
   - Task mapping: `TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec -> [<commitA>, <commitB>]`

9. TASK-2026-02-12-009_tests_and_smoke_script
   - Task artifact: `docs/tasks/TASK_2026_02_12_009_tests_and_smoke_script.md`
   - Task mapping: `TASK-2026-02-12-009_tests_and_smoke_script -> [<commitA>, <commitB>]`

## Final Mapping (authoritative)
>
> Update this section as each task completes.

- TASK-2026-02-12-001_repo_scaffold -> [f532d9b7, <commitB>]
- TASK-2026-02-12-002_flowspec_models_and_schema_export -> [1fcf4f05, <commitB>]
- TASK-2026-02-12-003_primitive_contracts_and_registry -> [c77f26de, <commitB>]
- TASK-2026-02-12-004_flow_compiler_normalize_validate -> [42ee1f1b, <commitB>]
- TASK-2026-02-12-005_flow_runner_execute_trace -> [<commitA>, <commitB>]
- TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating -> [<commitA>, <commitB>]
- TASK-2026-02-12-007_flow_builder_api_endpoints -> [<commitA>, <commitB>]
- TASK-2026-02-12-008_examples_utterances_to_compiled_flowspec -> [<commitA>, <commitB>]
- TASK-2026-02-12-009_tests_and_smoke_script -> [<commitA>, <commitB>]
