# CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP

## Campaign-ID
CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP

## Purpose
Convert the 2026-02-04 audit into a deterministic set of small, independently mergeable tasks that resolve RISK items first, then WARN/INFO follow-ups.

## Task Index (Ordered)
1. TASK-2026-02-05-001_remove_env_and_align_templates
2. TASK-2026-02-05-002_enforce_auth_documents_share
3. TASK-2026-02-05-003_frontend_send_x_api_key
4. TASK-2026-02-05-004_fix_chatgpt_import_path_auth
5. TASK-2026-02-05-005_wire_document_embed_worker
6. TASK-2026-02-05-006_rag_upload_endpoint_resolution
7. TASK-2026-02-05-007_embeddings_dummy_behavior
8. TASK-2026-02-05-008_image_gen_placeholder_handling
9. TASK-2026-02-05-009_doc_list_backend_source
10. TASK-2026-02-05-010_rag_trace_dev_only_label
11. TASK-2026-02-05-011_fix_make_test_target
12. TASK-2026-02-05-012_chat_embedding_background_queue

## Mapping (fill after each task completes)
Format EXACT: TASK-2026-02-05-NNN_<slug> -> [<commitA>, <commitB>]

- TASK-2026-02-05-001_remove_env_and_align_templates -> [c3e306f1, <commitB>]
- TASK-2026-02-05-002_enforce_auth_documents_share -> [24b6f81b, e41d0578]
- TASK-2026-02-05-003_frontend_send_x_api_key -> [c08e50a1, 768f26cb]
- TASK-2026-02-05-004_fix_chatgpt_import_path_auth -> [e472ea71, 42f9189b]
- TASK-2026-02-05-005_wire_document_embed_worker -> [1a85797e, <commitB>]
- TASK-2026-02-05-006_rag_upload_endpoint_resolution -> [<commitA>, <commitB>]
- TASK-2026-02-05-007_embeddings_dummy_behavior -> [<commitA>, <commitB>]
- TASK-2026-02-05-008_image_gen_placeholder_handling -> [<commitA>, <commitB>]
- TASK-2026-02-05-009_doc_list_backend_source -> [<commitA>, <commitB>]
- TASK-2026-02-05-010_rag_trace_dev_only_label -> [<commitA>, <commitB>]
- TASK-2026-02-05-011_fix_make_test_target -> [<commitA>, <commitB>]
- TASK-2026-02-05-012_chat_embedding_background_queue -> [<commitA>, <commitB>]

## Completion Rules
- A blocked task is marked BLOCKED and does not stop the rest of the campaign.
- Campaign is DONE only when all tasks are DONE or explicitly DEFERRED with a documented decision.
