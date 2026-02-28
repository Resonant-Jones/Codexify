You are the deterministic Campaign Compiler.

Mode:
- Output JSON only.
- Output exactly one object conforming to `campaign_set.schema.json`.
- Do not write files.
- Do not include prose, markdown fences, or explanation.

Inputs:
- Repo root: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Stage-A audit JSON: {
  "audit_id": "AUDIT_8848aca3c103",
  "repo": {
    "path": "/Users/resonant_jones/Keep/Resonant_Constructs/Codexify",
    "branch": "rescue/phase2-20260226-004130",
    "commit": "e2c40fcec5b0fe2f4708f92cf47c17f5c23fa119"
  },
  "generated_at": "2026-02-27T21:54:39Z",
  "agent": {
    "name": "Codex",
    "model": "gpt-5.3-codex",
    "mode": "audit"
  },
  "reports": [],
  "runner_ready_findings": [
    {
      "finding_id": "FINDING-2026-02-27-001",
      "area": "other",
      "severity": "WARN",
      "title": "WORKTREE-DRIFT-BLOCKS-PREFLIGHT",
      "description": "The worktree is dirty due to untracked Stage-A audit inputs. Core-loop campaign tasks require an empty preflight status and will halt while these files are present.",
      "evidence": [
        {
          "file": "docs/_audits/2026-02-27/AUDIT_8848aca3c103/audit_input_prompt.md",
          "lines": "untracked"
        },
        {
          "file": "docs/_audits/2026-02-27/AUDIT_8848aca3c103/run_inputs.json",
          "lines": "untracked"
        },
        {
          "file": "docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md",
          "lines": "L22-L23"
        }
      ],
      "relates_to_core_loop": "none",
      "suggested_task_outcome": "Preflight checks pass with an empty `git status --porcelain -uall` before deterministic runner execution.",
      "suggested_commands": [
        "git status --porcelain -uall",
        "git stash push -u -m preflight-AUDIT_8848aca3c103",
        "git status --porcelain -uall"
      ],
      "dependencies": [],
      "notes": "If audit artifacts must be preserved in-repo, commit them explicitly in a scoped docs change instead of stashing."
    },
    {
      "finding_id": "FINDING-2026-02-27-002",
      "area": "docs-drift",
      "severity": "WARN",
      "title": "MISSING-SUPERSEDING-MVP-MATRIX",
      "description": "The archived roadmap points to `docs/reports/mvp-core-loop-closure-matrix.md` as the authoritative source, but that file is missing from the repository.",
      "evidence": [
        {
          "file": "docs/codexify-mvp-roadmap.md",
          "lines": "L6-L13"
        },
        {
          "file": ".gitignore",
          "lines": "L127"
        },
        {
          "file": "docs/reports/mvp-core-loop-closure-matrix.md",
          "lines": "missing"
        }
      ],
      "relates_to_core_loop": "none",
      "suggested_task_outcome": "A committed authoritative MVP matrix exists at the superseding path, or all references are updated to an existing committed document.",
      "suggested_commands": [
        "test -f docs/reports/mvp-core-loop-closure-matrix.md",
        "ls docs/reports",
        "rg -n \"mvp-core-loop-closure-matrix.md\" docs/codexify-mvp-roadmap.md docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md docs/tasks/TASK_2026_02_17_003_docs_and_scope_followup.md"
      ],
      "dependencies": [],
      "notes": "Evidence indicates path drift between roadmap supersession metadata and committed docs inventory."
    },
    {
      "finding_id": "FINDING-2026-02-27-003",
      "area": "testing",
      "severity": "WARN",
      "title": "TASK-CHECKLIST-REFERENCES-MISSING-MATRIX",
      "description": "Task 004 checklist requires grep checks against `docs/reports/mvp-core-loop-closure-matrix.md`; those checks cannot pass as written because the file is absent.",
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
      "suggested_task_outcome": "Checklist commands and traceability checks reference only committed artifacts and succeed without manual path substitutions.",
      "suggested_commands": [
        "test -f docs/reports/mvp-core-loop-closure-matrix.md",
        "bash scripts/validate_core_loops.sh --dry-run",
        "rg -n \"validate_core_loops.sh|mvp-core-loop-closure-matrix.md\" docs/tasks/TASK_2026_02_17_002_mvp_core_loop_closure.md .github/workflows/guardian-ci.yml"
      ],
      "dependencies": [
        "docs/reports/mvp-core-loop-closure-matrix.md"
      ],
      "notes": "Inference: checklist determinism is broken specifically by the missing matrix dependency."
    },
    {
      "finding_id": "FINDING-2026-02-27-004",
      "area": "testing",
      "severity": "INFO",
      "title": "CI-SELECTOR-ENV-DRIFT",
      "description": "CI exports `CORE_LOOP_*_SELECTOR` variables and echoes them, but the harness executes a hard-coded selector list and does not read those variables.",
      "evidence": [
        {
          "file": ".github/workflows/guardian-ci.yml",
          "lines": "L168-L183"
        },
        {
          "file": "scripts/validate_core_loops.sh",
          "lines": "L42-L57"
        }
      ],
      "relates_to_core_loop": "none",
      "suggested_task_outcome": "Either the harness consumes `CORE_LOOP_*_SELECTOR` vars, or CI stops exporting unused selector vars to avoid misleading trace output.",
      "suggested_commands": [
        "rg -n \"CORE_LOOP_\" .github/workflows/guardian-ci.yml scripts/validate_core_loops.sh",
        "bash scripts/validate_core_loops.sh --dry-run"
      ],
      "dependencies": [],
      "notes": "Inference from static code search: current workflow output can imply configurability that is not actually wired."
    }
  ],
  "campaign_derivation_rules": {
    "strategy": "Prioritize deterministic runner unblockers first, then repair docs/testing traceability for core-loop governance.",
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
      "campaign_id": "2026-02-27::preflight_worktree_hygiene::001",
      "campaign_type": "followup",
      "source_findings": [
        "FINDING-2026-02-27-001"
      ]
    },
    {
      "campaign_id": "2026-02-27::mvp_docs_traceability_repair::002",
      "campaign_type": "mvp",
      "source_findings": [
        "FINDING-2026-02-27-002",
        "FINDING-2026-02-27-003"
      ]
    },
    {
      "campaign_id": "2026-02-27::ci_harness_selector_alignment::003",
      "campaign_type": "followup",
      "source_findings": [
        "FINDING-2026-02-27-004"
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
