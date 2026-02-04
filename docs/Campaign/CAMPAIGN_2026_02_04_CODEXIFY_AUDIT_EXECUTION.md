# CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Purpose

Convert the Senior Architect System Audit (2026-02-04) into a sequence of small, independently mergeable tasks that close the highest-risk gaps first (secrets + auth + missing worker wiring), then stabilize core loops and DX.

## Inputs (Authoritative)

- Repo root: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Audit report: docs/reports/codexify-system-audit-2026-02-04.md
- Environment: macOS + zsh
- Git limitation: .git/index.lock may occur; ALL commits are manual by human.
- Two-phase commit protocol:
  - Commit A = implementation/test/config changes
  - Commit B = docs finalize: task artifact + campaign mapping update
- Out-of-scope discipline:
  - Do not generate/modify reports or artifacts outside allowed files per task.
  - If tools generate artifacts (Playwright reports, etc.), revert/remove immediately before proceeding.

## Global Stop Conditions (applies to every task)

- If `git status --porcelain -uall` shows out-of-scope files:
  1) STOP.
  2) Revert/remove out-of-scope files.
  3) Re-run status until clean.
- Do not proceed with a task until working tree is clean.

## Task Index (Ordered)

1. TASK-2026-02-04-001_secrets_untrack_env_and_align_templates
2. TASK-2026-02-04-002_security_require_api_key_documents_and_share
3. TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy
4. TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth
5. TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose
6. TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly
7. TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage
8. TASK-2026-02-04-008_dx_fix_make_test_target

## Mapping (fill after each task completes)

Format EXACT: TASK-ID -> [<commitA>, <commitB>]

- TASK-2026-02-04-001_secrets_untrack_env_and_align_templates -> [<commitA>, <commitB>]
- TASK-2026-02-04-002_security_require_api_key_documents_and_share -> [<commitA>, <commitB>]
- TASK-2026-02-04-003_auth_frontend_attach_x_api_key_without_dev_proxy -> [<commitA>, <commitB>]
- TASK-2026-02-04-004_migration_fix_chatgpt_import_api_path_and_auth -> [<commitA>, <commitB>]
- TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose -> [<commitA>, <commitB>]
- TASK-2026-02-04-006_embeddings_remove_surprising_dummy_default_or_flag_clearly -> [<commitA>, <commitB>]
- TASK-2026-02-04-007_docgen_ui_use_backend_documents_list_not_localstorage -> [<commitA>, <commitB>]
- TASK-2026-02-04-008_dx_fix_make_test_target -> [<commitA>, <commitB>]
