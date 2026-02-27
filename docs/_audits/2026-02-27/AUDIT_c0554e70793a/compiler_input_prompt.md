You are the deterministic Campaign Compiler.

Mode:
- Output JSON only.
- Output exactly one object conforming to `campaign_set.schema.json`.
- Do not write files.
- Do not include prose, markdown fences, or explanation.

Inputs:
- Repo root: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Stage-A audit JSON: {
  "audit_id": "AUDIT_c0554e70793a",
  "repo": {
    "path": "/Users/resonant_jones/Keep/Resonant_Constructs/Codexify",
    "branch": "rescue/phase2-20260226-004130",
    "commit": "3532e63bae53d88a522699e48f1f37c8873f94cc"
  },
  "generated_at": "2026-02-27T04:37:45Z",
  "agent": {
    "name": "Codex",
    "model": "gpt-5.3-codex",
    "mode": "audit"
  },
  "reports": [
    {
      "report_id": "security_system_audit",
      "type": "system_audit",
      "path": "docs/reports/codexify-system-audit-2026-02-27.md",
      "severity_summary": {
        "RISK": 0,
        "WARN": 3,
        "INFO": 0
      },
      "focus": "security-and-determinism"
    },
    {
      "report_id": "mvp_roadmap",
      "type": "mvp_roadmap",
      "path": "docs/codexify-mvp-roadmap-2026-02-27.md",
      "severity_summary": null,
      "focus": "core-loop-closure"
    }
  ],
  "runner_ready_findings": [
    {
      "finding_id": "FINDING-2026-02-27-001",
      "area": "other",
      "severity": "WARN",
      "title": "WORKTREE-DRIFT",
      "description": "The worktree is not clean due to untracked Stage-A audit input files under docs/_audits. Campaign tasks require a clean preflight state and will stop when git status is non-empty.",
      "evidence": [
        {
          "file": "docs/_audits/2026-02-27/AUDIT_c0554e70793a/audit_input_prompt.md",
          "lines": "untracked"
        },
        {
          "file": "docs/_audits/2026-02-27/AUDIT_c0554e70793a/run_inputs.json",
          "lines": "untracked"
        },
        {
          "file": "docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md",
          "lines": "L22-L23"
        }
      ],
      "relates_to_core_loop": "none",
      "suggested_task_outcome": "Preflight checks pass with an empty `git status --porcelain -uall` before runner execution.",
      "suggested_commands": [
        "git status --porcelain -uall",
        "git stash push -u -m preflight-AUDIT_c0554e70793a",
        "git status --porcelain -uall"
      ],
      "dependencies": [],
      "notes": "If these files are required artifacts, commit them intentionally in a scoped docs change instead of stashing."
    },
    {
      "finding_id": "FINDING-2026-02-27-002",
      "area": "docs-drift",
      "severity": "WARN",
      "title": "MISSING-SUPERSEDING-MVP-MATRIX",
      "description": "The archived MVP roadmap declares docs/reports/mvp-core-loop-closure-matrix.md as the authoritative successor, but that target file is absent in the repository. This leaves the archive pointer unresolved.",
      "evidence": [
        {
          "file": "docs/codexify-mvp-roadmap.md",
          "lines": "L6-L13"
        },
        {
          "file": "docs/reports/mvp-core-loop-closure-matrix.md",
          "lines": "missing"
        }
      ],
      "relates_to_core_loop": "none",
      "suggested_task_outcome": "A real authoritative core-loop status document exists at the superseding path (or all superseding references are updated to an existing path).",
      "suggested_commands": [
        "test -f docs/reports/mvp-core-loop-closure-matrix.md",
        "test -f docs/codexify-mvp-roadmap-2026-02-24.md",
        "rg -n \"mvp-core-loop-closure-matrix.md\" docs/codexify-mvp-roadmap.md docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md docs/tasks/TASK_2026_02_17_003_docs_and_scope_followup.md"
      ],
      "dependencies": [],
      "notes": "Current repository contains docs/codexify-mvp-roadmap-2026-02-24.md and docs/reports/codexify-system-audit-2026-02-24.md, which may be candidate authoritative targets."
    },
    {
      "finding_id": "FINDING-2026-02-27-003",
      "area": "testing",
      "severity": "WARN",
      "title": "CORE-LOOP-TASK-CHECKLIST-REFERENCES-MISSING-FILE",
      "description": "Task 004 checklist in the core-loop campaign still requires grepping docs/reports/mvp-core-loop-closure-matrix.md. Because that file is missing, those checklist commands cannot be satisfied as-written even though the aggregate harness script and CI hook exist.",
      "evidence": [
        {
          "file": "docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md",
          "lines": "L107-L117"
        },
        {
          "file": "scripts/validate_core_loops.sh",
          "lines": "L42-L57"
        },
        {
          "file": ".github/workflows/guardian-ci.yml",
          "lines": "L165-L183"
        },
        {
          "file": "docs/reports/mvp-core-loop-closure-matrix.md",
          "lines": "missing"
        }
      ],
      "relates_to_core_loop": "none",
      "suggested_task_outcome": "Task 004 checklist references only existing artifacts, and `rg` validation commands succeed against committed files.",
      "suggested_commands": [
        "test -f docs/reports/mvp-core-loop-closure-matrix.md",
        "bash scripts/validate_core_loops.sh --dry-run",
        "rg -n \"validate_core_loops.sh|mvp-core-loop-closure-matrix.md\" docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md .github/workflows/guardian-ci.yml"
      ],
      "dependencies": [
        "docs/reports/mvp-core-loop-closure-matrix.md"
      ],
      "notes": "Inference: checklist failure is deterministic when the missing matrix path is referenced by rg commands."
    }
  ],
  "campaign_derivation_rules": {
    "strategy": "Group WARN findings by operational impact: preflight hygiene first, then docs/testing traceability needed for deterministic core-loop execution.",
    "group_by": [
      "area",
      "relates_to_core_loop"
    ],
    "priority_order": [
      "RISK",
      "WARN",
      "INFO"
    ]
  },
  "derived_campaigns": [
    {
      "campaign_id": "2026-02-27::worktree_hygiene_preflight::001",
      "campaign_type": "followup",
      "source_findings": [
        "FINDING-2026-02-27-001"
      ]
    },
    {
      "campaign_id": "2026-02-27::core_loop_traceability_docs::002",
      "campaign_type": "mvp",
      "source_findings": [
        "FINDING-2026-02-27-002",
        "FINDING-2026-02-27-003"
      ]
    }
  ]
}

Hard constraints:
1. `audit_id` must be copied exactly from Stage-A JSON.
2. Emit `campaigns` as 0..N entries.
3. For each campaign:
   - `campaign_id` must match: `YYYY-MM-DD::<campaign_slug>::<seq3>`
   - `campaign_slug` must be lower snake case.
   - `depends_on` must reference valid campaign ids when used.
   - `campaign_markdown` must be complete markdown content.
4. For each task:
   - Include required fields only.
   - `risk` must be `HIGH|MED|LOW`.
   - `files[]` must be repo-relative (no absolute paths, no `..`).
   - Do not include any artifact path fields.
5. If a campaign has no tasks:
   - `tasks` must be `[]`
   - `discovery_reason` must be non-empty and explicit.

Policy:
- Do not infer filesystem layout.
- Do not include git commit instructions.
- Do not include model instructions to edit campaign/task mapping files.
- Keep tasks independently mergeable and deterministic.

Return one valid JSON object for `campaign_set.schema.json`.
