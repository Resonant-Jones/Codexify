# CAMPAIGN_2026_02_03  Runner Audit Output

## Campaign Intent

Produce runner-ready audit artifacts for recent campaign compliance and task indexing. Documentation-only scope; no code changes.

## Global Notes

- Apply the Runner Protocol strictly: one task = one change set, only edit allowed files, run checks before commit, and produce a task artifact per task.
- All outputs must live under `artifacts/audit-runs/2026-02-03/` and `docs/work/tasks/`.

---

## TASK_2026_02_03_001_runner_protocol_audit_report

### Goal / Objective

Create a Runner Protocol compliance audit for campaigns dated 2026-01-23 and 2026-02-02 with explicit findings and remediation notes.

### Allowed Files (only)

- artifacts/audit-runs/2026-02-03/runner_protocol_audit_report.md
- docs/work/tasks/2026/02/TASK_2026_02_03_001_runner_protocol_audit_report.md

### Checks to Run

```bash
rg -n "Allowed Files|Checks to Run|Commit Mode" docs/work/campaigns/2026/02/CAMPAIGN_2026_02_02_TEST_INFRA_STABILIZATION_+_RUNNER_HYGIENE.md
rg -n "Allowed Files|Checks to Run|Commit Mode" docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
git diff --check
```

Commit Mode

one-commit

Commit Message Template

  TASK_2026_02_03_001: add runner protocol audit report

Task Prompt (for docs/work/tasks artifact)

Create artifacts/audit-runs/2026-02-03/runner_protocol_audit_report.md with sections:
- Metadata (date, repo, agent, runner)
- Scope (campaign docs reviewed)
- Checklist (allowed files, checks, commit mode, artifact requirements)
- Findings (FINDING-2026-02-03-001+ with evidence tied to campaign sections)
- Remediation Notes
- Summary

---

## TASK_2026_02_03_002_campaign_task_index

### Goal / Objective

Build a normalized index of February 2026 campaign tasks for runner intake.

### Allowed Files (only)

- artifacts/audit-runs/2026-02-03/campaign_task_index.md
- docs/work/tasks/2026/02/TASK_2026_02_03_002_campaign_task_index.md

### Checks to Run

```bash
rg -n "^## TASK_" docs/work/campaigns/2026/02/CAMPAIGN_2026_02_02_TEST_INFRA_STABILIZATION_+_RUNNER_HYGIENE.md
rg -n "^## TASK_" docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_AUDIT_HARDENING_FOUNDATION.md
rg -n "^## TASK_" docs/work/campaigns/2026/01/CAMPAIGN_2026_01_23_CORE_LOOP_ROADMAP.md
git diff --check
```

Commit Mode

one-commit

Commit Message Template

  TASK_2026_02_03_002: add campaign task index

Task Prompt (for docs/work/tasks artifact)

Create artifacts/audit-runs/2026-02-03/campaign_task_index.md with a table containing:
- task_id
- campaign_doc
- goal (short)
- allowed_files_count
- checks_count
- commit_mode

---

Completion Mapping Requirement

After completing all tasks, output a mapping:
  TASK_... -> <commit_hash>
