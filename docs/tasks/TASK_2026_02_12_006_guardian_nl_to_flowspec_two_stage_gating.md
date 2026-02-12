
---

### TASK 006 — Guardian NL→FlowSpec two-stage gating

```markdown
# TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating: Guardian 2-stage NL→FlowSpec compiler (tool interface)

## Metadata
- Task-ID: TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating
- Campaign-ID: CAMPAIGN-2026-02-12-001_FLOW_COMPILER_V0
- Branch: feat/flow-compiler-v0
- Repo root: <REPO_ROOT>
- Task artifact: docs/tasks/TASK_2026_02_12_006_guardian_nl_to_flowspec_two_stage_gating.md
- Owner: resonant_jones
- Risk: HIGH
- Commit mode: two-phase

## Objective
Implement a two-stage compiler: Stage 1 draft FlowSpec from NL with confidence, Stage 2 validate/normalize + confirmation gating.

## Scope
### In-scope
- Stage 1: draft_flow_from_text(text, user_context) -> draft_flow_spec + confidence + clarifying_questions[]
- Stage 2: compile_flow(draft) + gating:
  - if confidence < threshold OR compiler warnings -> needs_confirmation=true and block side effects
- Produce human-readable summary/diff of proposed FlowSpec

### Out-of-scope
- Full conversational agent design; focus is the tool interface
- New GUIs

## Allowed files (STRICT)
- guardian/flows/nl_compiler.py
- guardian/flows/compiler.py (only if needed for warnings outputs)
- guardian/flows/spec.py
- guardian/flows/primitives.py
- guardian/routes/flows.py (only if wiring tool endpoint)
- docs/tasks/TASK_2026_02_12_006_guardian_nl_to_flowspec_two_stage_gating.md
- docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md

## Preconditions (NO GUESSING)
```bash
cd <REPO_ROOT>
git status --porcelain -uall
```

# EXPECTED: (no output)

Execution plan (copy/paste)
cd <REPO_ROOT>
git status --porcelain -uall

# implement stage1+stage2 in guardian/flows/nl_compiler.py

python -c "from guardian.flows.nl_compiler import draft_flow_from_text; print('ok')"

git status --porcelain -uall

Expected results (explicit)

Import check prints ok

Draft output contains a numeric confidence score (0..1)

Low-confidence drafts set needs_confirmation and include clarifying_questions

Rollback / cleanup
cd <REPO_ROOT>
git checkout -- guardian/flows/nl_compiler.py guardian/flows/compiler.py guardian/flows/spec.py guardian/flows/primitives.py guardian/routes/flows.py

Commit plan (MANUAL; index.lock workaround)
Commit A (implementation) — two-phase only

Commit message (EXACT):

“TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating: NL->FlowSpec stage1+stage2 gating”

Manual commands (explicit paths only):

cd <REPO_ROOT>
git status --porcelain -uall
git add guardian/flows/nl_compiler.py guardian/flows/compiler.py guardian/flows/spec.py guardian/flows/primitives.py guardian/routes/flows.py
git commit --no-verify -m "TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating: NL->FlowSpec stage1+stage2 gating"
git log -1 --oneline
git status --porcelain -uall

Commit A hash: b4d688b4

Commit B (docs finalize + mapping) — two-phase only

Commit message (EXACT):

“TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating: docs finalize + mapping”

Manual commands:

cd <REPO_ROOT>
git status --porcelain -uall
git add docs/tasks/TASK_2026_02_12_006_guardian_nl_to_flowspec_two_stage_gating.md docs/Campaign/CAMPAIGN_2026_02_12_001_FLOW_COMPILER_V0.md
git commit --no-verify -m "TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall

Campaign mapping (SOURCE OF TRUTH)

TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating -> [b4d688b4, <commitB>]

Completion Summary (fill after completion)

Status: DONE

What changed:

- Implemented Stage-1 `draft_flow_from_text()` to produce draft FlowSpec, numeric confidence score, and clarifying questions.
- Implemented Stage-2 `compile_draft_with_gating()` to run `compile_flow()`, evaluate warnings/confidence threshold, and set `needs_confirmation`.
- Added human-readable proposal summary plus a draft-vs-compiled normalization diff.

Commands run:

git status --porcelain -uall
.venv/bin/python -c "from guardian.flows.nl_compiler import draft_flow_from_text; print('ok')"
.venv/bin/python -c "from guardian.flows.nl_compiler import draft_flow_from_text, compile_draft_with_gating; d=draft_flow_from_text('maybe summarize this'); r=compile_draft_with_gating(d); print(type(d.confidence).__name__, d.confidence, r.needs_confirmation, len(d.clarifying_questions))"
git add guardian/flows/nl_compiler.py guardian/flows/compiler.py guardian/flows/spec.py guardian/flows/primitives.py guardian/routes/flows.py
git commit --no-verify -m "TASK-2026-02-12-006_guardian_nl_to_flowspec_two_stage_gating: NL->FlowSpec stage1+stage2 gating"

Tests:

.venv/bin/python -c "from guardian.flows.nl_compiler import draft_flow_from_text; print('ok')" (pass)

Scope check:

git status clean before starting: yes

Only allowed files modified: yes

Commit info:

Commit mode: two-phase

Commit A hash (impl): b4d688b4

Commit B hash (docs finalize): recorded in campaign mapping

Campaign mapping updated: yes

Notes / gotchas:

System `python` is missing required dependencies in this shell, so runtime checks were executed via `.venv/bin/python`.
