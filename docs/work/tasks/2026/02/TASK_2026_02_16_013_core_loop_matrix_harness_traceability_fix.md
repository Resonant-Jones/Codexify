Preflight: git status --porcelain -uall must be empty

If preflight is not empty, STOP and run exactly:
- git status --porcelain -uall
- git stash push -u -m "preflight-TASK-2026-02-16-013"
- git status --porcelain -uall

# TASK-2026-02-16-013  Core-loop matrix/harness traceability fix
- Risk: MED
- Findings: FINDING-2026-02-16-012
- Allowed files:
  - docs/work/reports/mvp-core-loop-closure-matrix.md
  - scripts/validate_core_loops.sh
  - scripts/verification/rag_loop_validation.sh
  - scripts/verification/migration_loop_validation.sh
  - scripts/validate_doc_upload_embedding.sh
  - scripts/validate_image_gallery.sh
  - scripts/validate_doc_gen.sh
- Dependencies/Prereqs:
  - command -v bash
  - command -v rg
- Command checklist:
  1. rg -n "PASS|validate_core_loops.sh" docs/work/reports/mvp-core-loop-closure-matrix.md
  2. Add missing scripts/validate_core_loops.sh referencing committed validators/selectors.
  3. Update matrix claims so each PASS/FAIL maps to runnable artifacts.
  4. bash scripts/validate_core_loops.sh --dry-run
- Scope guard:
  - git diff --name-only
  - If any changed file is outside Allowed files, STOP and run exactly:
    - git restore --staged --worktree -- .
    - git clean -fd
    - git status --porcelain -uall
- Expected outputs:
  - validate_core_loops.sh exists and runs in dry-run mode.
  - Matrix no longer references missing validation script.
- Rollback / cleanup commands:
  - git restore --staged --worktree -- docs/work/reports/mvp-core-loop-closure-matrix.md scripts/validate_core_loops.sh scripts/verification/rag_loop_validation.sh scripts/verification/migration_loop_validation.sh scripts/validate_doc_upload_embedding.sh scripts/validate_image_gallery.sh scripts/validate_doc_gen.sh
  - git status --porcelain -uall