# Incumbent Tauri Browser Host candidate proof

- **Run ID:** `tauri-proof-79fdb67b`
- **Receipt kind:** `candidate_proof`
- **Harness version:** `0.1.0`
- **Fixture version:** `1.0.0`
- **Guardian stub version:** `0.1.0`
- **Started:** 2026-07-31T09:12:21.709157+00:00
- **Completed:** 2026-07-31T09:14:46.767775+00:00

- **Candidate ID:** `codexify-tauri-os-webview-incumbent-v1`
- **Candidate family:** `os_webview_tauri`

## Candidate Status: `proof_complete`

## Case Results

| Case | Status |
|------|--------|
| `accessibility_focus_order` | `passed` |
| `accessibility_keyboard_controls` | `passed` |
| `accessibility_names` | `passed` |
| `accessibility_not_color_only` | `passed` |
| `accessibility_text_scaling` | `inconclusive` |
| `accessibility_visible_focus` | `passed` |
| `build_artifact_hash_size` | `passed` |
| `build_clean_exact_command` | `passed` |
| `build_generated_inventory` | `passed` |
| `build_owned_cleanup` | `passed` |
| `capture_envelope_valid` | `inconclusive` |
| `capture_explicit_user_gesture` | `inconclusive` |
| `capture_no_silent_persistence` | `inconclusive` |
| `capture_preview` | `inconclusive` |
| `capture_selected_text` | `inconclusive` |
| `capture_single_request_attempt` | `inconclusive` |
| `capture_visible_page_text` | `inconclusive` |
| `cleanup_browser_profile` | `passed` |
| `cleanup_candidate_processes` | `passed` |
| `cleanup_credential_removed` | `passed` |
| `cleanup_generated_residue` | `passed` |
| `cleanup_harness_servers` | `passed` |
| `cleanup_worktree_scope` | `passed` |
| `credential_authenticated_request_denied` | `inconclusive` |
| `credential_console_absent` | `inconclusive` |
| `credential_global_state_absent` | `inconclusive` |
| `credential_logs_absent` | `inconclusive` |
| `credential_page_message_denied` | `inconclusive` |
| `credential_page_read_denied` | `inconclusive` |
| `failure_capture_cancelled` | `inconclusive` |
| `failure_companion_continuity` | `blocked` |
| `failure_guardian_attachment` | `blocked` |
| `failure_malformed_response` | `inconclusive` |
| `failure_observation_permission_denied` | `blocked` |
| `failure_oversized_truncated` | `inconclusive` |
| `failure_permission_revoked` | `blocked` |
| `failure_protected_target` | `blocked` |
| `injection_browser_authority_denied` | `inconclusive` |
| `injection_command_bus_denied` | `inconclusive` |
| `injection_content_remains_evidence` | `inconclusive` |
| `injection_credential_retrieval_denied` | `inconclusive` |
| `injection_host_policy_unchanged` | `inconclusive` |
| `integrity_cross_origin_iframe_excluded` | `inconclusive` |
| `integrity_document_change_invalidates` | `inconclusive` |
| `integrity_origin_mismatch_rejected` | `inconclusive` |
| `integrity_source_metadata_matches` | `blocked` |
| `integrity_stale_navigation_rejected` | `inconclusive` |
| `launch_success` | `passed` |
| `native_command_bus_denied` | `inconclusive` |
| `native_environment_secret_denied` | `inconclusive` |
| `native_filesystem_denied` | `inconclusive` |
| `native_permission_widening_denied` | `inconclusive` |
| `native_process_denied` | `inconclusive` |
| `native_unrelated_command_denied` | `inconclusive` |
| `navigation_history_reload` | `blocked` |
| `navigation_one_remote_page` | `inconclusive` |
| `navigation_same_cross_origin` | `blocked` |
| `navigation_state` | `inconclusive` |
| `observability_correlations` | `passed` |
| `observability_credentials_absent` | `passed` |
| `observability_form_storage_absent` | `passed` |
| `observability_raw_body_absent` | `passed` |
| `observability_state_failure_codes` | `passed` |
| `package_command_or_unsupported` | `passed` |
| `renderer_failure_clean_termination` | `blocked` |
| `renderer_failure_companion_bounded` | `blocked` |
| `renderer_failure_credential_safe` | `blocked` |
| `renderer_failure_native_safe` | `blocked` |
| `resource_artifact_size` | `passed` |
| `resource_build_duration` | `passed` |
| `resource_capture_latency` | `blocked` |
| `resource_cold_launch` | `inconclusive` |
| `resource_idle_memory` | `inconclusive` |
| `resource_one_tab_memory` | `inconclusive` |
| `resource_process_count` | `passed` |
| `resource_shutdown_duration` | `passed` |
| `sensitive_cookies_storage_excluded` | `inconclusive` |
| `sensitive_hidden_input_excluded` | `inconclusive` |
| `sensitive_password_excluded` | `inconclusive` |
| `sensitive_scripts_styles_excluded` | `inconclusive` |
| `sensitive_text_input_excluded` | `inconclusive` |
| `static_credential_location` | `passed` |
| `static_csp_policy` | `passed` |
| `static_dependency_versions` | `passed` |
| `static_host_commands_ipc` | `passed` |
| `static_package_configuration` | `passed` |
| `static_privileges_capabilities` | `passed` |
| `static_remote_content` | `passed` |
| `static_webview_engine` | `passed` |

## Cleanup: `passed`

## Warnings

- A separate remote Tauri window was used; embedded child-webview UX is not proven.
- macOS Tauri renderer interaction remained blocked without an approved WebDriver lane.

## Explicit Non-Claims

- proof_complete means terminal evidence coverage, not architectural approval
- Tauri was not selected as a technology winner
- no repository, release, or engine ownership decision was made
- no production Guardian credential or command was used
- Gate C remains closed

---
*Generated by Codexify Browser Host Harness v0.1.0*
