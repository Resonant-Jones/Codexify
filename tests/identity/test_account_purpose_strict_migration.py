"""Frozen ADR-092 account-purpose registration and credential proof.

The inventory below is a literal snapshot of the accepted 238-registration
classification. It is intentionally independent of route discovery at test time.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import json
import time
from collections import Counter
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.core import auth, dependencies

ROOT = Path(__file__).resolve().parents[2]

# file, method/protocol, full path, handler, frozen implementation shape
FROZEN_ACCOUNT_REGISTRATIONS = (
    ('guardian/connections/google_drive/router.py', 'POST', '/api/connect/google-drive/start', 'start_google_drive_oauth', 'get_request_user_id,require_api_key'),
    ('guardian/connections/google_drive/router.py', 'GET', '/api/connect/google-drive/status', 'google_drive_status', 'get_request_user_id,require_api_key'),
    ('guardian/connections/google_drive/router.py', 'POST', '/api/connect/google-drive/validate', 'validate_google_drive', 'get_request_user_id,require_api_key'),
    ('guardian/connections/google_drive/router.py', 'POST', '/api/connect/google-drive/disconnect', 'disconnect_google_drive', 'get_request_user_id,require_api_key'),
    ('guardian/connections/google_drive/router.py', 'GET', '/api/knowledge/google-drive/search', 'google_drive_content_search', 'get_request_user_id,require_api_key'),
    ('guardian/connections/google_drive/router.py', 'GET', '/api/knowledge/google-drive/read/{object_id}', 'google_drive_content_read', 'get_request_user_id,require_api_key'),
    ('guardian/connections/notion/router.py', 'POST', '/api/connect/notion/configure', 'configure_notion', 'get_request_user_id,require_api_key'),
    ('guardian/connections/notion/router.py', 'POST', '/api/connect/notion/validate', 'validate_notion', 'get_request_user_id,require_api_key'),
    ('guardian/connections/notion/router.py', 'GET', '/api/connect/notion/status', 'notion_status', 'get_request_user_id,require_api_key'),
    ('guardian/connections/notion/router.py', 'POST', '/api/connect/notion/disconnect', 'disconnect_notion', 'get_request_user_id,require_api_key'),
    ('guardian/connections/notion/router.py', 'GET', '/api/knowledge/notion/search', 'notion_content_search', 'get_request_user_id,require_api_key'),
    ('guardian/connections/notion/router.py', 'GET', '/api/knowledge/notion/read/{object_id}', 'notion_content_read', 'get_request_user_id,require_api_key'),
    ('guardian/connectors/google.py', 'GET', '/api/connect/google/start', 'start_connect', 'get_current_user'),
    ('guardian/connectors/google.py', 'GET', '/api/connect/google/status', 'status', 'get_current_user'),
    ('guardian/connectors/google.py', 'POST', '/api/connect/google/disconnect', 'disconnect', 'get_current_user'),
    ('guardian/connectors/minimax.py', 'POST', '/api/connect/minimax/start', 'start_connect', 'get_current_user'),
    ('guardian/connectors/minimax.py', 'POST', '/api/connect/minimax/poll', 'poll_connect', 'get_current_user'),
    ('guardian/connectors/minimax.py', 'POST', '/api/connect/minimax/disconnect', 'disconnect', 'get_current_user'),
    ('guardian/connectors/minimax.py', 'GET', '/api/connect/minimax/status', 'connection_status', 'get_current_user'),
    ('guardian/guardian_api.py', 'POST', '/api/tasks/{task_id}/cancel', 'request_task_cancel', 'require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'POST', '/api/agents/coding/execute', 'execute_coding_task', 'get_current_user,require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'POST', '/api/agents/runs/{run_id}/cancel', 'cancel_run', 'get_current_user,require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'GET', '/api/agents/runs/{run_id}/coding', 'get_coding_run', 'get_current_user,require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'GET', '/api/agents/runs/{run_id}', 'get_run', 'get_current_user,require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'GET', '/api/chat/{thread_id}/coding-runs', 'list_coding_runs_via_chat', 'get_current_user,require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'GET', '/api/agents/runs/{run_id}/events', 'stream_run_events', 'require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'GET', '/api/agents/chat/{thread_id}/agent-runs', 'list_thread_runs', 'require_api_key'),
    ('guardian/routes/agent_orchestration.py', 'GET', '/api/chat/{thread_id}/agent-runs', 'list_thread_runs_via_chat', 'require_api_key'),
    ('guardian/routes/api_exports.py', 'GET', '/exports/threads.ndjson', 'export_threads', 'require_user'),
    ('guardian/routes/api_exports.py', 'GET', '/exports/account.zip', 'export_account_zip', 'require_user'),
    ('guardian/routes/api_exports.py', 'GET', '/exports/chatgpt.zip', 'export_chatgpt_zip', 'require_user'),
    ('guardian/routes/channels.py', 'GET', '/api/channels/configs', 'list_configs', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'POST', '/api/channels/configs', 'upsert_config', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'DELETE', '/api/channels/configs/{channel}', 'delete_config', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'GET', '/api/channels/allowlist/{channel}', 'list_allowlist', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'POST', '/api/channels/allowlist/{channel}', 'add_allowlist_entry', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'DELETE', '/api/channels/allowlist/{channel}/{external_id}', 'delete_allowlist_entry', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'GET', '/api/channels/pairings/{channel}', 'list_pairings', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'POST', '/api/channels/pairings/{channel}', 'create_pairing', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'PATCH', '/api/channels/pairings/{channel}/{external_id}', 'update_pairing', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/channels.py', 'GET', '/api/channels/messages/{channel}', 'list_messages', 'router require_api_key; each handler _current_user → get_request_user_id'),
    ('guardian/routes/chat.py', 'POST', '/chat/threads/{thread_id}/move', 'chat_move_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/chat/threads', 'chat_create_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/threads', 'chat_list_threads', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/threads/{thread_id}', 'chat_get_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/threads/{thread_id}/tasks', 'chat_list_tasks', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/chat/{thread_id}/messages', 'chat_post_message', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/chat/messages', 'chat_post_message_create_on_send', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/{thread_id}/messages', 'chat_list_messages', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/chat/{thread_id}/complete', 'chat_complete', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/{thread_id}/profile', 'chat_get_thread_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/chat/{thread_id}/profile', 'chat_switch_thread_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'DELETE', '/chat/{thread_id}/messages/{message_id}', 'chat_delete_message', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/chat/{thread_id}/branch', 'branch_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/chat/{thread_id}', 'update_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/chat/threads/{thread_id}', 'patch_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/chat/threads/{thread_id}/config', 'patch_thread_config', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'DELETE', '/chat/{thread_id}', 'delete_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/threads', 'list_threads', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/threads', 'create_thread_alias', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/thread/{thread_id}', 'get_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/thread/{thread_id}/children', 'get_child_threads', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/thread/{thread_id}/summary', 'get_thread_summary', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/thread', 'create_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/debug/rag-trace/{thread_id}/latest', 'get_latest_rag_trace', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/{thread_id}/debug/candidate-trace/latest', 'get_latest_candidate_trace', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/{thread_id}/debug/graph-write/latest', 'get_latest_graph_write_inspection_route', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/debug/evals/{thread_id}/latest', 'get_latest_eval_diagnostics_route', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/debug/retrieval-posture/{thread_id}/latest', 'get_latest_retrieval_posture_endpoint', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/{thread_id}/debug/retrieval-posture/history', 'get_retrieval_posture_history_endpoint', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat/threads', 'api_chat_create_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/threads', 'api_chat_list_threads', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat/{thread_id}/messages', 'api_chat_post_message', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/threads/{thread_id}', 'api_chat_get_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat/messages', 'api_chat_post_message_create_on_send', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/{thread_id}/messages', 'api_chat_list_messages', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat/{thread_id}/complete', 'api_chat_complete', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/{thread_id}/profile', 'api_chat_get_thread_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/api/chat/{thread_id}/profile', 'api_chat_switch_thread_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/debug/rag-trace/{thread_id}/latest', 'api_get_latest_rag_trace', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/{thread_id}/debug/candidate-trace/latest', 'api_get_latest_candidate_trace', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/{thread_id}/debug/graph-write/latest', 'api_get_latest_graph_write_inspection_route', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/debug/retrieval-posture/{thread_id}/latest', 'api_get_latest_retrieval_posture', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/debug/evals/{thread_id}/latest', 'api_get_latest_eval_diagnostics_route', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'GET', '/api/chat/{thread_id}/debug/retrieval-posture/history', 'api_get_retrieval_posture_history', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'DELETE', '/api/chat/{thread_id}/messages/{message_id}', 'api_chat_delete_message', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat/{thread_id}/branch', 'api_branch_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/api/chat/{thread_id}', 'api_update_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/api/chat/threads/{thread_id}', 'api_patch_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'PATCH', '/api/chat/threads/{thread_id}/config', 'api_patch_thread_config', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat/threads/{thread_id}/move', 'api_chat_move_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'DELETE', '/api/chat/threads/{thread_id}', 'api_delete_thread', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/chat.py', 'POST', '/api/chat', 'api_chat_root', 'require_api_key,verify_api_key'),
    ('guardian/routes/chat.py', 'POST', '/chat', 'simple_chat_entrypoint', 'verify_api_key'),
    ('guardian/routes/chat.py', 'GET', '/chat/stream', 'simple_chat_stream', 'verify_api_key'),
    ('guardian/routes/command_bus.py', 'POST', '/api/guardian/commands/invoke', 'invoke_command', 'get_current_user,require_api_key'),
    ('guardian/routes/command_bus.py', 'GET', '/api/guardian/commands/activation/inspect', 'inspect_activation', 'get_current_user,require_api_key'),
    ('guardian/routes/command_bus.py', 'GET', '/api/guardian/commands/runs/{run_id}', 'get_run', 'get_current_user,require_api_key'),
    ('guardian/routes/command_bus.py', 'GET', '/api/guardian/commands/tool-turns/{message_id}/observability', 'get_tool_turn_observability', 'get_current_user,require_api_key'),
    ('guardian/routes/command_bus.py', 'GET', '/api/guardian/commands/runs/{run_id}/events', 'stream_run_events', 'get_current_user,require_api_key'),
    ('guardian/routes/command_bus.py', 'GET', '/api/guardian/commands/manifest', 'get_manifest', 'require_api_key'),
    ('guardian/routes/command_bus.py', 'GET', '/api/guardian/commands/search', 'search_command_manifest', 'require_api_key'),
    ('guardian/routes/connections.py', 'GET', '/api/connections', 'list_connections', 'get_request_user_id,require_api_key'),
    ('guardian/routes/connections.py', 'GET', '/api/connections/{connection_id}', 'get_connection_details', 'get_request_user_id,require_api_key'),
    ('guardian/routes/dashboard.py', 'GET', '/api/dashboard/snapshot', 'dashboard_snapshot', 'require_api_key'),
    ('guardian/routes/direct_messages.py', 'PUT', '/api/profile/social-identity', 'put_social_identity', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/profile/social-identity', 'get_social_identity', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/direct-messages/profiles', 'search_profiles', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'POST', '/api/direct-messages/relationships', 'resolve_relationship', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/direct-messages/relationships', 'list_relationships', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'POST', '/api/direct-messages/relationships/{relationship_id}/conversations', 'create_relationship_conversation', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/direct-messages/relationships/{relationship_id}/conversations', 'list_relationship_conversations', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'PATCH', '/api/direct-messages/conversations/{conversation_id}/placement', 'move_conversation_placement', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/direct-messages/conversations', 'list_conversations', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/direct-messages/conversations/{conversation_id}', 'get_conversation', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'GET', '/api/direct-messages/conversations/{conversation_id}/messages', 'read_messages', 'get_request_user_scope'),
    ('guardian/routes/direct_messages.py', 'POST', '/api/direct-messages/conversations/{conversation_id}/messages', 'send_message', 'get_request_user_scope'),
    ('guardian/routes/documents.py', 'POST', '/api/documents/autosave', 'autosave_document', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/documents.py', 'POST', '/api/documents/generate', 'generate_document', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/documents.py', 'GET', '/api/threads/{thread_id}/documents', 'get_thread_documents', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/documents.py', 'GET', '/api/documents/{document_id}', 'get_uploaded_document_detail', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/federation_context.py', 'POST', '/api/federation/context/search', 'search_context', 'require_user'),
    ('guardian/routes/federation_context.py', 'GET', '/api/federation/context/peers', 'get_peers', 'require_user'),
    ('guardian/routes/federation_context.py', 'POST', '/api/federation/context/peers/{peer_id}/trust', 'set_peer_trust', 'require_user'),
    ('guardian/routes/hosted_rooms.py', 'POST', '/api/hosted-rooms', 'create_room', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'GET', '/api/hosted-rooms', 'list_rooms', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'GET', '/api/hosted-rooms/{room_id}', 'get_room', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'PATCH', '/api/hosted-rooms/{room_id}', 'update_room', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'POST', '/api/hosted-rooms/{room_id}/close', 'close_room', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'POST', '/api/hosted-rooms/{room_id}/invites', 'create_invite', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'GET', '/api/hosted-rooms/{room_id}/invites', 'list_invites', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'POST', '/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke', 'revoke_invite', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'POST', '/api/hosted-rooms/{room_id}/actors/{participant_id}/invoke', 'owner_invoke_guardian', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'GET', '/api/hosted-rooms/{room_id}/messages', 'owner_list_messages', 'get_request_user_scope'),
    ('guardian/routes/hosted_rooms.py', 'POST', '/api/hosted-rooms/{room_id}/messages', 'owner_post_message', 'get_request_user_scope'),
    ('guardian/routes/iddb.py', 'GET', '/api/iddb/settings', 'get_settings', 'get_current_user,require_api_key'),
    ('guardian/routes/iddb.py', 'POST', '/api/iddb/settings', 'update_settings', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'GET', '/api/imprint/status', 'get_imprint_status', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'POST', '/api/imprint/proposal', 'create_imprint_proposal', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'POST', '/api/imprint/accept', 'accept_imprint', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'POST', '/api/imprint/reject', 'reject_imprint', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'GET', '/api/system_prompt/inspect', 'inspect_system_prompt', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'GET', '/api/system_prompt/summary', 'system_prompt_summary', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'GET', '/api/system_docs', 'list_system_docs', 'get_current_user,require_api_key'),
    ('guardian/routes/imprint.py', 'POST', '/api/system_docs/toggle', 'toggle_system_doc', 'get_current_user,require_api_key'),
    ('guardian/routes/intents.py', 'POST', '/api/guardian/intents/dispatch', 'dispatch_intent', 'get_current_user,require_api_key'),
    ('guardian/routes/media.py', 'POST', '/api/media/upload/image', 'upload_image', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/images/{image_id}', 'get_image', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'DELETE', '/api/media/images/{image_id}', 'delete_image', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'POST', '/api/media/upload/document', 'upload_document', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'POST', '/api/media/upload/file', 'upload_document', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'POST', '/api/media/generate/image', 'generate_image', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'POST', '/api/media/tts/synthesize', 'synthesize_speech', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/tts/{tts_id}', 'get_tts_audio', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/resolve', 'resolve_media_asset', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/images', 'list_images', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/document-artifacts', 'list_document_artifacts', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/document-artifacts/{artifact_id}', 'get_document_artifact', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/documents', 'list_documents', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'GET', '/api/media/documents/{document_id}', 'get_document', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/media.py', 'DELETE', '/api/media/documents/{document_id}', 'delete_document', '_require_media_api_key,get_request_user_scope'),
    ('guardian/routes/memory.py', 'GET', '/api/memory/{silo}', 'memory_list', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'POST', '/api/memory/{silo}', 'memory_create', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'PATCH', '/api/memory/{silo}/{entry_id}', 'memory_update', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'DELETE', '/api/memory/{silo}/{entry_id}', 'memory_delete', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'GET', '/api/memory/health/memory', 'health_memory', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'GET', '/api/github/search', 'github_memory_search', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'GET', '/search', 'search', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'GET', '/history', 'history', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'POST', '/log', 'log_entry', 'get_current_user,require_api_key'),
    ('guardian/routes/memory.py', 'POST', '/summarize', 'summarize_entry', 'get_current_user,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/imports/openai-account', 'create_openai_account_import', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/imports/openai-account/{job_id}/files', 'upload_openai_account_import_batch', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/imports/openai-account/{job_id}/commit', 'commit_openai_account_import', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'GET', '/api/imports/openai-account/{job_id}', 'get_openai_account_import', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/imports/openai-account/{job_id}/retry', 'retry_openai_account_import', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/imports/account/metadata', 'import_account_metadata', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/imports/account/metadata', 'import_account_metadata', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/upload-chatgpt-export', 'upload_chatgpt_export', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/upload-chatgpt-export', 'upload_chatgpt_export', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/api/retry-chatgpt-import-embeddings', 'retry_chatgpt_import_embeddings', 'get_request_user_id,require_api_key'),
    ('guardian/routes/migration.py', 'POST', '/retry-chatgpt-import-embeddings', 'retry_chatgpt_import_embeddings', 'get_request_user_id,require_api_key'),
    ('guardian/routes/persona_profiles.py', 'GET', '/api/persona-profiles', 'list_profiles', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/persona_profiles.py', 'GET', '/api/persona-profiles/{profile_id}', 'read_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/persona_profiles.py', 'POST', '/api/persona-profiles', 'create_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/persona_profiles.py', 'PATCH', '/api/persona-profiles/{profile_id}', 'update_profile', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/personal_facts.py', 'GET', '/personal-facts', 'list_personal_facts', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'POST', '/personal-facts', 'create_personal_fact', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'GET', '/personal-facts/{fact_id}', 'get_personal_fact', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'PATCH', '/personal-facts/{fact_id}', 'update_personal_fact', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'POST', '/personal-facts/{fact_id}/confirm', 'confirm_personal_fact', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'POST', '/personal-facts/{fact_id}/dispute', 'dispute_personal_fact', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'POST', '/personal-facts/candidates/{fact_id}/approve', 'approve_candidate', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'POST', '/personal-facts/candidates/{fact_id}/reject', 'reject_candidate', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'GET', '/personal-facts/{fact_id}/evidence', 'list_fact_evidence', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'POST', '/personal-facts/{fact_id}/evidence', 'add_fact_evidence', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'GET', '/personal-facts/{fact_id}/revisions', 'list_fact_revisions', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'GET', '/personal-facts/candidates', 'list_fact_candidates', 'get_current_user,require_api_key'),
    ('guardian/routes/personal_facts.py', 'GET', '/personal-facts/candidates/debug/recent', 'debug_recent_candidates', 'get_current_user,require_api_key'),
    ('guardian/routes/projects.py', 'GET', '/projects', 'list_projects', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'GET', '/api/projects', 'list_projects', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'POST', '/projects', 'create_project', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'POST', '/api/projects', 'create_project', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'POST', '/api/projects/repository-import', 'import_repository_candidate_route', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'GET', '/api/projects/{project_id}/repository/search', 'search_project_repository_route', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'PATCH', '/projects/{project_id}', 'patch_project', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'PATCH', '/api/projects/{project_id}', 'patch_project', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'DELETE', '/projects/{project_id}', 'delete_project_and_eject', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/projects.py', 'DELETE', '/api/projects/{project_id}', 'delete_project_and_eject', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/share.py', 'POST', '/api/share', 'create_share_link', 'get_request_user_scope,require_api_key'),
    ('guardian/routes/threads.py', 'GET', '/api/threads', 'list_threads', 'THREAD_API_KEY_DEP,THREAD_REQUEST_USER_SCOPE_DEP'),
    ('guardian/routes/threads.py', 'POST', '/api/threads', 'create_thread', 'THREAD_API_KEY_DEP,THREAD_REQUEST_USER_SCOPE_DEP'),
    ('guardian/routes/threads.py', 'GET', '/api/threads/{thread_id}', 'get_thread', 'THREAD_API_KEY_DEP,THREAD_REQUEST_USER_SCOPE_DEP'),
    ('guardian/routes/threads.py', 'GET', '/threads', 'list_threads', 'THREAD_API_KEY_DEP,THREAD_REQUEST_USER_SCOPE_DEP'),
    ('guardian/routes/threads.py', 'POST', '/threads', 'create_thread', 'THREAD_API_KEY_DEP,THREAD_REQUEST_USER_SCOPE_DEP'),
    ('guardian/routes/threads.py', 'GET', '/threads/{thread_id}', 'get_thread', 'THREAD_API_KEY_DEP,THREAD_REQUEST_USER_SCOPE_DEP'),
    ('guardian/routes/tts.py', 'POST', '/api/tts/render', 'render_tts_voiceover', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'GET', '/api/tts/backends', 'list_tts_backends', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'GET', '/api/tts/profiles', 'list_tts_profiles', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'POST', '/api/tts/profiles', 'create_tts_profile', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'GET', '/api/tts/profiles/{profile_id}', 'get_tts_profile', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'PATCH', '/api/tts/profiles/{profile_id}', 'patch_tts_profile', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'DELETE', '/api/tts/profiles/{profile_id}', 'delete_tts_profile', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'POST', '/api/tts/profiles/{profile_id}/set-default', 'set_tts_profile_default', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'POST', '/api/tts/profiles/{profile_id}/preview', 'preview_tts_profile', 'get_request_user_scope'),
    ('guardian/routes/tts.py', 'GET', '/api/tts/previews/{filename}', 'stream_tts_preview', 'get_request_user_scope'),
    ('guardian/routes/user_profile.py', 'GET', '/api/user/profile', 'get_profile', 'get_request_user_scope'),
    ('guardian/routes/user_profile.py', 'PATCH', '/api/user/profile', 'update_profile', 'get_request_user_scope'),
    ('guardian/routes/voice.py', 'GET', '/api/voice/providers', 'list_voice_providers', 'require_api_key'),
    ('guardian/routes/voice.py', 'GET', '/api/voice/providers/{provider_id}', 'voice_provider_capability', 'require_api_key'),
    ('guardian/routes/voice.py', 'GET', '/api/voice/providers/{provider_id}/voices', 'voice_provider_selectable_voices', 'require_api_key'),
    ('guardian/routes/voice.py', 'POST', '/api/voice/preview', 'preview_voice', 'require_api_key'),
    ('guardian/routes/voice.py', 'GET', '/api/voice/capabilities', 'voice_capabilities', 'require_api_key'),
    ('guardian/routes/voice.py', 'GET', '/api/voice/audio/{asset_id}', 'stream_audio_asset', 'require_api_key'),
    ('guardian/routes/voice.py', 'POST', '/api/voice/turn', 'voice_turn', 'require_api_key'),
    ('guardian/routes/voice.py', 'POST', '/api/voice/messages/{message_id}/speak', 'speak_message', 'require_api_key'),
    ('guardian/routes/websocket.py', 'WEBSOCKET', '/api/ws/rpc', 'websocket_rpc', 'authenticate_websocket'),
    ('guardian/ws/router.py', 'WEBSOCKET', '/api/ws/rpc', 'websocket_rpc', 'authenticate_websocket'),

)


def test_frozen_inventory_and_declarations() -> None:
    rows = FROZEN_ACCOUNT_REGISTRATIONS
    assert len(rows) == 238
    assert len({row[0] for row in rows}) == 32
    assert len(set(row[:4] for row in rows)) == 238
    assert sum(row[1] == "WEBSOCKET" for row in rows) == 2
    assert all("account_observability.py" not in row[0] for row in rows)
    assert all(not row[2].endswith("/events") or "agent" in row[2] or "commands" in row[2] for row in rows)

    for file, method, path, handler, shape in rows:
        source = (ROOT / file).read_text()
        tree = ast.parse(source)
        functions = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == handler
        ]
        assert functions, (file, method, path, handler)
        assert any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr.upper() == method
            and decorator.args
            and isinstance(decorator.args[0], ast.Constant)
            and isinstance(decorator.args[0].value, str)
            and path.endswith(decorator.args[0].value)
            for fn in functions
            for decorator in fn.decorator_list
        ), (file, method, path, handler)
        route_gate_symbols = (
            "require_account_session", "require_api_key", "verify_api_key", "get_current_user",
            "get_request_user_scope", "get_request_user_id", "require_user",
            "_current_user", "THREAD_API_KEY_DEP", "THREAD_REQUEST_USER_SCOPE_DEP",
        )
        direct_gate = any(
            symbol in ast.unparse(function.args)
            or any(symbol in ast.unparse(decorator) for decorator in function.decorator_list)
            for function in functions
            for symbol in route_gate_symbols
        )
        if not direct_gate:
            router_gated = (
                (file == "guardian/routes/agent_orchestration.py" and path == "/api/chat/{thread_id}/agent-runs")
                or (file == "guardian/routes/command_bus.py" and path in {
                    "/api/guardian/commands/manifest", "/api/guardian/commands/search"
                })
                or file == "guardian/routes/dashboard.py"
            )
            websocket_gated = method == "WEBSOCKET" and "authenticate_websocket" in ast.unparse(functions[0])
            assert router_gated or websocket_gated, (file, method, path, handler)
        for symbol in (
            "get_request_user_id", "get_request_user_scope", "get_current_user",
            "require_api_key", "require_user", "verify_api_key", "authenticate_websocket",
            "_require_media_api_key", "THREAD_API_KEY_DEP", "THREAD_REQUEST_USER_SCOPE_DEP",
            "_current_user",
        ):
            if symbol in shape:
                assert symbol in source, (file, method, path, symbol)

        if method == "WEBSOCKET":
            continue
        if file in {
            "guardian/routes/api_exports.py",
            "guardian/routes/federation_context.py",
        }:
            assert "require_user" in shape
            continue
        if file == "guardian/guardian_api.py":
            assert "Depends(require_account_session)" in ast.unparse(functions[0])
            continue

        dependency_imports = {
            alias.asname or alias.name: alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "guardian.core.dependencies"
            for alias in node.names
        }
        expected = {
            "get_request_user_id": "get_account_user_id",
            "get_request_user_scope": "get_account_user_scope",
            "get_current_user": "get_account_user",
            "require_api_key": "require_account_session",
            "verify_api_key": "verify_account_session",
        }
        for generic, strict in expected.items():
            if generic not in shape:
                continue
            if file == "guardian/routes/dashboard.py" and generic == "get_request_user_scope":
                # This direct lookup follows the router's account-session gate.
                assert dependency_imports["require_api_key"] == "require_account_session"
            elif file in {"guardian/routes/memory.py", "guardian/routes/personal_facts.py"} and generic == "get_current_user":
                assert dependency_imports["get_request_user_id"] == "get_account_user_id"
                assert "Depends(get_request_user_id)" in source
            elif file == "guardian/routes/memory.py" and generic == "require_api_key":
                assert dependency_imports["core_require_api_key"] == strict
            else:
                assert dependency_imports[generic] == strict, (file, method, path)
        if file == "guardian/routes/threads.py":
            assert dependency_imports["require_api_key"] == "require_account_session"
            assert dependency_imports["get_request_user_scope"] == "get_account_user_scope"
        if file == "guardian/routes/media.py":
            assert dependency_imports["verify_api_key"] == "verify_account_session"

    assert "resolve_account_session_subject" in ast.unparse(
        ast.parse((ROOT / "guardian/core/dependencies.py").read_text())
    )
    assert "resolve_account_session_subject" in ast.unparse(
        ast.parse((ROOT / "guardian/core/auth.py").read_text())
    )
    auth_source = (ROOT / "guardian/core/auth.py").read_text()
    assert "subject = resolve_account_session_subject(token or \"\")" in auth_source
    ws = (ROOT / "guardian/ws/auth.py").read_text()
    assert "verify_session_token_for_purpose" in ws
    assert "ACCOUNT_SESSION_PURPOSE" in ws


class _Store:
    def __init__(self, mapping: dict[str, str] | None = None):
        self.mapping = mapping or {}
        self.calls = 0

    def verify(self, token: str) -> str | None:
        self.calls += 1
        return self.mapping.get(token)


def _legacy_token(subject: str, *, purpose: str | None, expires: int | None = None) -> str:
    claims = {
        "subject": subject,
        "exp": expires or int(time.time()) + 3600,
        "nonce": "frozen-purpose-test",
    }
    if purpose is not None:
        claims["purpose"] = purpose
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(b"test-session-secret", payload, hashlib.sha256).digest()
    return ".".join((
        base64.urlsafe_b64encode(payload).decode().rstrip("="),
        base64.urlsafe_b64encode(signature).decode().rstrip("="),
    ))


@pytest.fixture
def session_context(monkeypatch: pytest.MonkeyPatch) -> _Store:
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    store = _Store()
    monkeypatch.setattr("guardian.core.session_store.get_session_store", lambda: store)
    monkeypatch.setattr("guardian.core.auth_dependencies.get_session_store", lambda: store)
    return store


@pytest.mark.parametrize("purpose", [None, "operator_session", "hosted_room_guest_session", "unrelated"])
def test_wrong_purpose_precedes_store(session_context: _Store, purpose: str | None) -> None:
    token = _legacy_token("account-a", purpose=purpose)
    session_context.mapping[token] = "account-a"
    with pytest.raises(HTTPException) as error:
        auth.resolve_account_session_subject(token)
    assert error.value.status_code == 401
    assert session_context.calls == 0


def test_valid_account_and_store_mismatch(session_context: _Store) -> None:
    token = _legacy_token("account-a", purpose="account_session")
    session_context.mapping[token] = "account-a"
    assert auth.resolve_account_session_subject(token) == "account-a"
    session_context.mapping[token] = "account-b"
    with pytest.raises(HTTPException) as error:
        auth.resolve_account_session_subject(token)
    assert error.value.status_code == 401


@pytest.mark.parametrize("token", ["malformed", "", "not.a.signed.token"])
def test_malformed_token_rejected_before_store(session_context: _Store, token: str) -> None:
    with pytest.raises(HTTPException) as error:
        auth.resolve_account_session_subject(token)
    assert error.value.status_code == 401
    assert session_context.calls == 0


def test_expired_token_rejected_before_store(session_context: _Store) -> None:
    token = _legacy_token("account-a", purpose="account_session", expires=int(time.time()) - 3600)
    session_context.mapping[token] = "account-a"
    with pytest.raises(HTTPException) as error:
        auth.resolve_account_session_subject(token)
    assert error.value.status_code == 401
    assert session_context.calls == 0


def test_legacy_reauthentication_keeps_account(session_context: _Store) -> None:
    legacy = _legacy_token("account-a", purpose=None)
    fresh, _ = auth.issue_session_token(subject="account-a", purpose=auth.ACCOUNT_SESSION_PURPOSE)
    session_context.mapping[legacy] = "account-a"
    session_context.mapping[fresh] = "account-a"
    with pytest.raises(HTTPException):
        auth.resolve_account_session_subject(legacy)
    assert auth.resolve_account_session_subject(fresh) == "account-a"


def test_remote_account_http_auth_rejects_other_purposes(session_context: _Store) -> None:
    token = _legacy_token("account-a", purpose="account_session")
    session_context.mapping[token] = "account-a"
    assert dependencies.verify_account_session(None, None, f"Bearer {token}", None) == token
    assert dependencies._account_scope_gate(None, f"Bearer {token}", None) is None
    assert auth.require_auth(None, authorization=f"Bearer {token}") == "session:account-a"
    for purpose in (None, "operator_session", "hosted_room_guest_session", "unrelated"):
        wrong = _legacy_token("account-a", purpose=purpose)
        session_context.mapping[wrong] = "account-a"
        before = session_context.calls
        for authenticate in (
            lambda: dependencies.verify_account_session(None, None, f"Bearer {wrong}", None),
            lambda: dependencies._account_scope_gate(None, f"Bearer {wrong}", None),
            lambda: auth.require_auth(None, authorization=f"Bearer {wrong}"),
        ):
            with pytest.raises(HTTPException) as error:
                authenticate()
            assert error.value.status_code == 401
        assert session_context.calls == before


def test_account_scope_gate_precedes_generic_resolution_and_business_logic(
    session_context: _Store,
) -> None:
    app = FastAPI()
    calls: list[str] = []

    def generic_scope() -> dependencies.RequestUserScope:
        calls.append("account-scope")
        return dependencies.RequestUserScope(
            user_id="account-a", subject_id="account-a", account_id="account-a",
            multi_user_enabled=True,
        )

    app.dependency_overrides[dependencies.get_request_user_scope] = generic_scope

    @app.get("/probe")
    def probe(scope: dependencies.RequestUserScope = Depends(dependencies.get_account_user_scope)):
        calls.append("business")
        return {"user_id": scope.user_id}

    wrong = _legacy_token("account-a", purpose="operator_session")
    session_context.mapping[wrong] = "account-a"
    with TestClient(app, headers={"X-API-Key": ""}) as client:
        denied = client.get("/probe", headers={"Authorization": f"Bearer {wrong}"})
        assert denied.status_code == 401
        assert calls == []
        assert session_context.calls == 0

        valid = _legacy_token("account-a", purpose="account_session")
        session_context.mapping[valid] = "account-a"
        accepted = client.get("/probe", headers={"Authorization": f"Bearer {valid}"})
        assert accepted.status_code == 200
        assert accepted.json() == {"user_id": "account-a"}
        assert calls == ["account-scope", "business"]


def test_private_preview_requires_approved_stored_account(
    session_context: _Store, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "account-a@example.com")
    monkeypatch.delenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", raising=False)
    app = FastAPI()

    @app.get("/probe")
    def probe(_credential: str = Depends(dependencies.require_account_session)):
        return {"ok": True}

    token = _legacy_token("account-a@example.com", purpose="account_session")
    with TestClient(app, headers={"X-API-Key": ""}) as client:
        assert client.get("/probe", headers={"Authorization": f"Bearer {token}"}).status_code == 401
        session_context.mapping[token] = "account-a@example.com"
        assert client.get("/probe", headers={"Authorization": f"Bearer {token}"}).status_code == 200

        session_context.mapping[token] = "account-b@example.com"
        assert client.get("/probe", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_account_scope_keeps_existing_local_dependency_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    app = FastAPI()
    app.dependency_overrides[dependencies.get_request_user_scope] = lambda: (
        dependencies.RequestUserScope(user_id="local-user")
    )

    @app.get("/probe")
    def probe(scope: dependencies.RequestUserScope = Depends(dependencies.get_account_user_scope)):
        return {"user_id": scope.user_id}

    with TestClient(app, headers={"X-API-Key": ""}) as client:
        response = client.get("/probe")
    assert response.status_code == 200
    assert response.json() == {"user_id": "local-user"}
