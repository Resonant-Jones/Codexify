# Electron bundled Chromium Browser Host candidate proof

## Executive result

- Terminal candidate status: `environment_blocked`.
- Candidate: `codexify-electron-bundled-chromium-v1` (`bundled_chromium_electron`).
- Mandatory cases: 89; status totals: {"inconclusive": 68, "passed": 21}.
- Evidence totals: {"live-cleanup-proven": 4, "proven-repository": 14, "proven-test": 3, "unknown": 68}.
- `proof_complete` means terminal evidence coverage only. Electron was not selected, no candidate was ranked, and Gate C remains closed.

## Source, dependencies, and official research

- Source root: `/Volumes/Dev_SSD/Codexify-main/browser_host_candidates/electron`; package root: `/Volumes/Dev_SSD/Codexify-main/browser_host_candidates/electron`.
- Electron `43.2.0`; Chromium `150.0.7871.129`; bundled Node `24.18.0`; V8 `15.0.1240245-electron.0`.
- Playwright `1.62.1` (official Electron support is experimental); packager `20.0.4`.
- Official-source research is recorded in `official-source-research.json`; framework capability is not Codexify proof.

## Trust, session, and IPC topology

- Trusted main owns the synthetic credential, navigation policy, capture lifecycle, Browser Context Envelope, Guardian-stub request, and safe diagnostics.
- Trusted shell loads local HTML with a narrow immutable `contextBridge` API; it receives no credential or filesystem path.
- Remote renderer is a separate `BrowserWindow` with no preload, Node integration disabled, context isolation enabled, renderer sandbox enabled, and webview tags disabled.
- Remote session is one run-scoped non-persistent partition with permission checks and requests denied, popups denied, and downloads cancelled.
- IPC channels are candidate-owned fixed channels only; sender id, local frame URL, run, state, generation, and bounded arguments are validated.

## Build, package, and interaction

- Build/check command: `['npm', 'run', 'check', '&&', 'npm', 'test']`; return code `0`.
- Package command: `['npm', 'run', 'package']`; return code `0`.
- Package posture: unsigned, development-only, not release-qualified, not distributable product proof; package result is recorded in `artifact-hashes.json`.
- Launch result: Playwright Electron could not establish a candidate runtime in this host; the bounded attempt and omission reason are recorded in `candidate-runtime-attempt.json` and `trace-omission.json`.
- No live renderer isolation, native-authority, capture, attachment, navigation, failure, or accessibility behavior is claimed; those mandatory cases remain terminally `inconclusive`.
- No alternate automation framework or private candidate API was substituted after the Playwright launch failure.

## Capture and containment results

- No live capture, attachment, prompt-injection, sensitive-field, navigation, or renderer-failure result is claimed.
- Static source, test, package, and official-source evidence must not be read as live runtime proof.

## Accessibility and resources

- Accessibility results are in `accessibility-results.json`; no live trusted-shell accessibility inspection was possible, so accessibility cases remain terminally `inconclusive`.
- Resource measurements are in `resource-measurements.json`; no candidate process was established, so live timing, memory, and process-count trials remain unavailable. No score is produced.

## Ownership, repository boundary, and cleanup

- The candidate has no direct Codexify production imports and is independent of root package manifests and locks.
- Electron/Chromium update owner, Playwright proof-driver owner, signing, updater, crash reporting, profile migration, rollback, vulnerability response, and supported-platform ownership remain unknown or unassigned; framework cadence does not resolve them.
- Cleanup removes candidate processes, loopback servers, the synthetic credential, temporary user data, and generated residue under task ownership; the cleanup receipt is retained.

## Warnings, failures, unknowns, and non-claims

- Unknown: Playwright Electron could not establish a candidate runtime; see candidate-runtime-attempt.json.
- Unknown: Electron or Playwright could not establish a meaningful candidate runtime.
- Unknown: No live production Guardian compatibility
- Unknown: No integrated single-window UX
- Unknown: Electron/Chromium maintenance and security ownership
- Non-claim: proof_complete means terminal evidence coverage, not architecture approval
- Non-claim: Electron was not selected and no candidate was ranked
- Non-claim: No repository split, ADR, release, signing, updater, or rollback decision was made
- Non-claim: No production frontend, extension, Guardian, Tauri candidate, or root package files were modified
- Non-claim: No live production Guardian compatibility or provider invocation was proven
- Non-claim: Gate C remains closed

## ADR impact

- Aligned with ADR-051, ADR-021, ADR-039, ADR-040, ADR-003, ADR-004, ADR-005 and the governing Browser Authority, canonical-token, account-export, chat-runtime, and agent-tool-loop contracts.
- No ADR was created or modified. The next prerequisite is a technology-neutral comparative summary of the Tauri and Electron terminal packets plus an ADR-readiness reassessment.
- Production frontend, extension, Guardian, Tauri candidate, Tauri packet, root manifests, and production runtime were unchanged. No live production Guardian compatibility was proven.

## Mandatory case table

| Case | Status | Evidence |
|---|---|---|
| `accessibility_focus_order` | `inconclusive` | `unknown` |
| `accessibility_keyboard_controls` | `inconclusive` | `unknown` |
| `accessibility_names` | `inconclusive` | `unknown` |
| `accessibility_not_color_only` | `inconclusive` | `unknown` |
| `accessibility_text_scaling` | `inconclusive` | `unknown` |
| `accessibility_visible_focus` | `inconclusive` | `unknown` |
| `build_artifact_hash_size` | `passed` | `proven-repository` |
| `build_clean_exact_command` | `passed` | `proven-test` |
| `build_generated_inventory` | `passed` | `proven-repository` |
| `build_owned_cleanup` | `passed` | `proven-repository` |
| `capture_envelope_valid` | `inconclusive` | `unknown` |
| `capture_explicit_user_gesture` | `inconclusive` | `unknown` |
| `capture_no_silent_persistence` | `inconclusive` | `unknown` |
| `capture_preview` | `inconclusive` | `unknown` |
| `capture_selected_text` | `inconclusive` | `unknown` |
| `capture_single_request_attempt` | `inconclusive` | `unknown` |
| `capture_visible_page_text` | `inconclusive` | `unknown` |
| `cleanup_browser_profile` | `passed` | `live-cleanup-proven` |
| `cleanup_candidate_processes` | `passed` | `live-cleanup-proven` |
| `cleanup_credential_removed` | `passed` | `live-cleanup-proven` |
| `cleanup_generated_residue` | `passed` | `proven-repository` |
| `cleanup_harness_servers` | `passed` | `live-cleanup-proven` |
| `cleanup_worktree_scope` | `passed` | `proven-repository` |
| `credential_authenticated_request_denied` | `inconclusive` | `unknown` |
| `credential_console_absent` | `inconclusive` | `unknown` |
| `credential_global_state_absent` | `inconclusive` | `unknown` |
| `credential_logs_absent` | `inconclusive` | `unknown` |
| `credential_page_message_denied` | `inconclusive` | `unknown` |
| `credential_page_read_denied` | `inconclusive` | `unknown` |
| `failure_capture_cancelled` | `inconclusive` | `unknown` |
| `failure_companion_continuity` | `inconclusive` | `unknown` |
| `failure_guardian_attachment` | `inconclusive` | `unknown` |
| `failure_malformed_response` | `inconclusive` | `unknown` |
| `failure_observation_permission_denied` | `inconclusive` | `unknown` |
| `failure_oversized_truncated` | `inconclusive` | `unknown` |
| `failure_permission_revoked` | `inconclusive` | `unknown` |
| `failure_protected_target` | `inconclusive` | `unknown` |
| `injection_browser_authority_denied` | `inconclusive` | `unknown` |
| `injection_command_bus_denied` | `inconclusive` | `unknown` |
| `injection_content_remains_evidence` | `inconclusive` | `unknown` |
| `injection_credential_retrieval_denied` | `inconclusive` | `unknown` |
| `injection_host_policy_unchanged` | `inconclusive` | `unknown` |
| `integrity_cross_origin_iframe_excluded` | `inconclusive` | `unknown` |
| `integrity_document_change_invalidates` | `inconclusive` | `unknown` |
| `integrity_origin_mismatch_rejected` | `inconclusive` | `unknown` |
| `integrity_source_metadata_matches` | `inconclusive` | `unknown` |
| `integrity_stale_navigation_rejected` | `inconclusive` | `unknown` |
| `launch_success` | `inconclusive` | `unknown` |
| `native_command_bus_denied` | `inconclusive` | `unknown` |
| `native_environment_secret_denied` | `inconclusive` | `unknown` |
| `native_filesystem_denied` | `inconclusive` | `unknown` |
| `native_permission_widening_denied` | `inconclusive` | `unknown` |
| `native_process_denied` | `inconclusive` | `unknown` |
| `native_unrelated_command_denied` | `inconclusive` | `unknown` |
| `navigation_history_reload` | `inconclusive` | `unknown` |
| `navigation_one_remote_page` | `inconclusive` | `unknown` |
| `navigation_same_cross_origin` | `inconclusive` | `unknown` |
| `navigation_state` | `inconclusive` | `unknown` |
| `observability_correlations` | `inconclusive` | `unknown` |
| `observability_credentials_absent` | `inconclusive` | `unknown` |
| `observability_form_storage_absent` | `inconclusive` | `unknown` |
| `observability_raw_body_absent` | `inconclusive` | `unknown` |
| `observability_state_failure_codes` | `inconclusive` | `unknown` |
| `package_command_or_unsupported` | `passed` | `proven-test` |
| `renderer_failure_clean_termination` | `inconclusive` | `unknown` |
| `renderer_failure_companion_bounded` | `inconclusive` | `unknown` |
| `renderer_failure_credential_safe` | `inconclusive` | `unknown` |
| `renderer_failure_native_safe` | `inconclusive` | `unknown` |
| `resource_artifact_size` | `passed` | `proven-repository` |
| `resource_build_duration` | `passed` | `proven-test` |
| `resource_capture_latency` | `inconclusive` | `unknown` |
| `resource_cold_launch` | `inconclusive` | `unknown` |
| `resource_idle_memory` | `inconclusive` | `unknown` |
| `resource_one_tab_memory` | `inconclusive` | `unknown` |
| `resource_process_count` | `inconclusive` | `unknown` |
| `resource_shutdown_duration` | `inconclusive` | `unknown` |
| `sensitive_cookies_storage_excluded` | `inconclusive` | `unknown` |
| `sensitive_hidden_input_excluded` | `inconclusive` | `unknown` |
| `sensitive_password_excluded` | `inconclusive` | `unknown` |
| `sensitive_scripts_styles_excluded` | `inconclusive` | `unknown` |
| `sensitive_text_input_excluded` | `inconclusive` | `unknown` |
| `static_credential_location` | `passed` | `proven-repository` |
| `static_csp_policy` | `passed` | `proven-repository` |
| `static_dependency_versions` | `passed` | `proven-repository` |
| `static_host_commands_ipc` | `passed` | `proven-repository` |
| `static_package_configuration` | `passed` | `proven-repository` |
| `static_privileges_capabilities` | `passed` | `proven-repository` |
| `static_remote_content` | `passed` | `proven-repository` |
| `static_webview_engine` | `passed` | `proven-repository` |

_Generated by Codexify Browser Host Harness v0.1.0._
