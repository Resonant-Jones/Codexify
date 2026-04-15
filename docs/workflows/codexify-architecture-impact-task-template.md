# Codexify Architecture-Impact Task Template

## Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

This task is **architecture-impacting**.
Use this template when the change affects one or more of the following:

* runtime semantics
* retrieval policy or routing doctrine
* identity boundaries or message/attempt semantics
* control-plane behavior
* observability truth surfaces
* canonical token domains
* queue / worker / acceptance contracts
* documented system invariants

This template exists so Codexify changes follow:

```text
current truth → ADR check → contract check → implementation → proof → doc alignment
```

---

## Required pre-read

Before making any change, read the current truth and decision context.

### Always read first

1. `/docs/architecture/00-current-state.md`
2. `/docs/architecture/adr/ADR Index.md`
3. `/docs/architecture/README.md` or the current KB entrypoint

### Then read the most relevant governing docs for this task

Examples:

* runtime / chat loop work

  * `/docs/architecture/chat-runtime-contract.md`
  * `/docs/architecture/completion_pipeline.md`
  * `/docs/architecture/flows.md`

* retrieval / routing / posture work

  * `/docs/architecture/router-decision-table.md`
  * `/docs/architecture/flows.md`
  * `/docs/architecture/system-overview.md`

* storage / invariants / lineage work

  * `/docs/architecture/data-and-storage.md`
  * `/docs/architecture/account-export-restore-contract.md`

* UI / diagnostics / observability surfaces

  * `/docs/architecture/architecture-atlas.md`
  * `/docs/architecture/runtime-diagrams-v1.md`
  * `/docs/architecture/ui-diagrams-v1.md`

---

## ADR impact check

Before implementation, explicitly classify ADR impact.

Choose one:

* `No ADR impact`
* `Aligned with existing ADR(s)`
* `Requires new ADR`
* `Supersedes existing ADR`

### Required ADR section in output

```text
ADR impact:
- classification: <one of the four above>
- governing ADRs: <list ADR ids/titles, or "none">
- reason: <1–3 sentences>
```

If the task changes a previously accepted architectural decision, do **not** silently mutate history.
Add a new ADR and mark the previous one as superseded in the decision log.

---

## Current-truth anchor

State exactly which current-truth claims govern this task.

### Required section

```text
Current-truth anchors:
- <claim from 00-current-state.md>
- <claim from another current/runtime doc if needed>
```

This section must answer:

* what is true right now
* what is explicitly **not** yet true
* what this task is allowed to assume

---

## Scope

This change belongs in:

* `/path/to/file.ext`
* `/path/to/another/file.ext`

Do not modify files outside this scope unless the task explicitly requires it.

If a new ADR is required, include:

* `/docs/architecture/adr/NNN-short-title.md`

---

## Goal

Describe the architectural outcome in one paragraph.

This must answer:

* what system seam is changing
* what invariant must remain intact
* what truth surface will now become stronger, clearer, or more deterministic

---

## Invariants that must remain true

List the non-negotiable rules this task must preserve.

Examples:

* route acceptance must not imply completion
* provider state and request state remain separate
* retrieval policy must not be derived from prompt text
* thread-first retrieval must remain intact
* identity boundaries must not be widened
* frontend must not invent a second backend truth surface
* canonical tokens must remain the source of repeated semantic literals

### Required section

```text
Invariants:
1. ...
2. ...
3. ...
```

---

## Required changes

Break the task into small, explicit architectural steps.

### For each step, include

* purpose
* file(s)
* exact boundary being modified
* what must not change

Example format:

#### 1. Add bounded contract type

This change belongs in:

* `/path/to/file`

Requirements:

* ...
* ...
* ...

#### 2. Thread contract through existing seam

This change belongs in:

* `/path/to/file`

Requirements:

* ...
* ...
* ...

#### 3. Preserve trace / observability truth

This change belongs in:

* `/path/to/file`

Requirements:

* ...
* ...
* ...

---

## Scope boundaries

Do **not**:

* change unrelated runtime behavior
* widen supported product claims
* smuggle in prompt-based logic
* invent parallel truth surfaces
* replace policy with override
* add speculative future architecture
* silently rename or fork canonical tokens
* alter docs outside declared scope unless explicitly required

Keep the blast radius narrow.

---

## Proof requirements

This task must identify the exact proof surface that validates the change.

Choose one or more:

* backend seam tests
* frontend contract tests
* live runtime proof
* docs-only validation
* route seam truth
* trace/debug seam truth
* broker seam truth
* supported-path evidence

### Required section

```text
Proof surface:
- primary:
- secondary:
- not required:
```

---

## Validation steps

List the exact commands to run.

Examples:

```bash
pytest -v tests/routes/test_chat_source_mode.py tests/routes/test_chat_profile_trace.py
```

```bash
pnpm --dir frontend/src exec vitest run features/commandCenter/__tests__/CommandCenterPage.test.tsx
```

If the task is docs-only, explicitly state:

```text
No automated tests apply
```

But still require:

* link/path sanity check
* markdown well-formedness
* header hierarchy sanity if relevant

---

## Documentation follow-through

State which docs must be updated if the architectural meaning changes.

Possible targets:

* `/docs/architecture/00-current-state.md`
* `/docs/architecture/adr/ADR Index.md`
* `/docs/architecture/architecture-atlas.md`
* `/docs/architecture/README.md`
* `/docs/architecture/router-decision-table.md`
* `/docs/architecture/chat-runtime-contract.md`
* `/docs/architecture/tech-debt-and-risks.md`

### Required rule

If the task changes:

* architecture meaning
* runtime truth
* policy doctrine
* operator truth surfaces

…then the relevant doc update must be included in the same task or explicitly deferred with a reason.

---

## If checks pass

```bash
git add <modified files>
git commit -m "<concise architectural change summary>"
```

---

## Output must include

1. Summary of changes

   * files changed
   * key contracts/helpers/components/routes updated

2. ADR impact

   * classification
   * governing ADRs
   * whether a new ADR was added or not

3. Validation results

   * exact command results
   * explicit “no automated tests apply” when true

4. Documentation follow-through

   * what was updated
   * what was intentionally not updated

5. Git commit hash

---

## Trigger rule

Use this template when **any one** of the following is true:

1. The change alters a contract or system invariant.
2. The change modifies retrieval or routing behavior.
3. The change affects an operator-visible truth surface.
4. The change touches queue / worker / acceptance semantics.
5. The change would be dangerous to forget in three months.

If none of those are true, use the standard Codexify task template instead.
