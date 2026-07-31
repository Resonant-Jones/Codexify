# Electron bundled Chromium Browser Host candidate proof

## Executive result

- Terminal candidate status: `proof_complete`.
- Candidate: `codexify-electron-bundled-chromium-v1` (`bundled_chromium_electron`).
- Mandatory cases: 89; status totals: {"inconclusive": 4, "passed": 85}.
- Evidence totals: {"code-path-only": 2, "live-cleanup-proven": 4, "live-measurement": 4, "live-measurement-unavailable": 2, "live-runtime-proven": 59, "proven-repository": 14, "proven-test": 4}.
- `proof_complete` means terminal evidence coverage only. Electron was not selected, no candidate was ranked, and Gate C remains closed.

## Source, dependencies, and official research

- Source root: `/Volumes/Dev_SSD/Codexify-main/browser_host_candidates/electron`; package root: `/Volumes/Dev_SSD/Codexify-main/browser_host_candidates/electron`.
- Frozen source snapshot: `source-manifest.json` with tree hash `378b8426fd8ef74db940db977c41d704048b47b9094a68683d525304b55965ef`; unchanged during proof: `True`.
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
- Playwright drove trusted-shell clicks, real fixture navigation, real visible text selection, separate preview and attachment actions, failure recovery, keyboard focus, screenshots, and clean shutdown.

## Capture and containment results

- Selected-text and visible-page capture were live-tested; main-process metadata and hashing author the Browser Context Envelope.
- Sensitive password, text-input, hidden-input, scripts/styles, cookies/storage, and cross-origin iframe bodies were excluded from the captured preview.
- Prompt-injection instructions remained fixture evidence only; they did not change policy or grant authority.
- Navigation, origin change, stale capture invalidation, popup denial, permission denial, download cancellation, deterministic attachment failure, companion continuity, and bounded renderer degradation are recorded per case.

## Accessibility and resources

- Accessibility results are in `accessibility-results.json`; native controls, names, visible focus, logical DOM order, and non-color-only state were exercised. Live 200 percent scaling remains inconclusive.
- Resource measurements are in `resource-measurements.json`; raw trials, medians, minima, maxima, process observations, and measurement scope are retained. No score is produced.

## Ownership, repository boundary, and cleanup

- The candidate has no direct Codexify production imports and is independent of root package manifests and locks.
- Electron/Chromium update owner, Playwright proof-driver owner, signing, updater, crash reporting, profile migration, rollback, vulnerability response, and supported-platform ownership remain unknown or unassigned; framework cadence does not resolve them.
- Cleanup removes candidate processes, loopback servers, the synthetic credential, temporary user data, and generated residue under task ownership; the cleanup receipt is retained.

## Warnings, failures, unknowns, and non-claims

- Warning: Playwright Electron support is experimental and is used only as a proof driver.
- Warning: The trusted shell and remote fixture use separate Electron windows; integrated child-view UX is not proven.
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
| `accessibility_focus_order` | `passed` | `live-runtime-proven` |
| `accessibility_keyboard_controls` | `passed` | `live-runtime-proven` |
| `accessibility_names` | `passed` | `live-runtime-proven` |
| `accessibility_not_color_only` | `passed` | `live-runtime-proven` |
| `accessibility_text_scaling` | `inconclusive` | `code-path-only` |
| `accessibility_visible_focus` | `passed` | `live-runtime-proven` |
| `build_artifact_hash_size` | `passed` | `proven-repository` |
| `build_clean_exact_command` | `passed` | `proven-test` |
| `build_generated_inventory` | `passed` | `proven-repository` |
| `build_owned_cleanup` | `passed` | `proven-repository` |
| `capture_envelope_valid` | `passed` | `live-runtime-proven` |
| `capture_explicit_user_gesture` | `passed` | `live-runtime-proven` |
| `capture_no_silent_persistence` | `passed` | `live-runtime-proven` |
| `capture_preview` | `passed` | `live-runtime-proven` |
| `capture_selected_text` | `passed` | `live-runtime-proven` |
| `capture_single_request_attempt` | `passed` | `live-runtime-proven` |
| `capture_visible_page_text` | `passed` | `live-runtime-proven` |
| `cleanup_browser_profile` | `passed` | `live-cleanup-proven` |
| `cleanup_candidate_processes` | `passed` | `live-cleanup-proven` |
| `cleanup_credential_removed` | `passed` | `live-cleanup-proven` |
| `cleanup_generated_residue` | `passed` | `proven-repository` |
| `cleanup_harness_servers` | `passed` | `live-cleanup-proven` |
| `cleanup_worktree_scope` | `passed` | `proven-repository` |
| `credential_authenticated_request_denied` | `passed` | `live-runtime-proven` |
| `credential_console_absent` | `passed` | `live-runtime-proven` |
| `credential_global_state_absent` | `passed` | `live-runtime-proven` |
| `credential_logs_absent` | `passed` | `live-runtime-proven` |
| `credential_page_message_denied` | `passed` | `live-runtime-proven` |
| `credential_page_read_denied` | `passed` | `live-runtime-proven` |
| `failure_capture_cancelled` | `passed` | `live-runtime-proven` |
| `failure_companion_continuity` | `passed` | `live-runtime-proven` |
| `failure_guardian_attachment` | `passed` | `live-runtime-proven` |
| `failure_malformed_response` | `inconclusive` | `code-path-only` |
| `failure_observation_permission_denied` | `passed` | `live-runtime-proven` |
| `failure_oversized_truncated` | `passed` | `live-runtime-proven` |
| `failure_permission_revoked` | `passed` | `live-runtime-proven` |
| `failure_protected_target` | `passed` | `live-runtime-proven` |
| `injection_browser_authority_denied` | `passed` | `live-runtime-proven` |
| `injection_command_bus_denied` | `passed` | `live-runtime-proven` |
| `injection_content_remains_evidence` | `passed` | `live-runtime-proven` |
| `injection_credential_retrieval_denied` | `passed` | `live-runtime-proven` |
| `injection_host_policy_unchanged` | `passed` | `live-runtime-proven` |
| `integrity_cross_origin_iframe_excluded` | `passed` | `live-runtime-proven` |
| `integrity_document_change_invalidates` | `passed` | `live-runtime-proven` |
| `integrity_origin_mismatch_rejected` | `passed` | `proven-test` |
| `integrity_source_metadata_matches` | `passed` | `live-runtime-proven` |
| `integrity_stale_navigation_rejected` | `passed` | `live-runtime-proven` |
| `launch_success` | `passed` | `live-runtime-proven` |
| `native_command_bus_denied` | `passed` | `live-runtime-proven` |
| `native_environment_secret_denied` | `passed` | `live-runtime-proven` |
| `native_filesystem_denied` | `passed` | `live-runtime-proven` |
| `native_permission_widening_denied` | `passed` | `live-runtime-proven` |
| `native_process_denied` | `passed` | `live-runtime-proven` |
| `native_unrelated_command_denied` | `passed` | `live-runtime-proven` |
| `navigation_history_reload` | `passed` | `live-runtime-proven` |
| `navigation_one_remote_page` | `passed` | `live-runtime-proven` |
| `navigation_same_cross_origin` | `passed` | `live-runtime-proven` |
| `navigation_state` | `passed` | `live-runtime-proven` |
| `observability_correlations` | `passed` | `live-runtime-proven` |
| `observability_credentials_absent` | `passed` | `live-runtime-proven` |
| `observability_form_storage_absent` | `passed` | `live-runtime-proven` |
| `observability_raw_body_absent` | `passed` | `live-runtime-proven` |
| `observability_state_failure_codes` | `passed` | `live-runtime-proven` |
| `package_command_or_unsupported` | `passed` | `proven-test` |
| `renderer_failure_clean_termination` | `passed` | `live-runtime-proven` |
| `renderer_failure_companion_bounded` | `passed` | `live-runtime-proven` |
| `renderer_failure_credential_safe` | `passed` | `live-runtime-proven` |
| `renderer_failure_native_safe` | `passed` | `live-runtime-proven` |
| `resource_artifact_size` | `passed` | `proven-repository` |
| `resource_build_duration` | `passed` | `proven-test` |
| `resource_capture_latency` | `passed` | `live-measurement` |
| `resource_cold_launch` | `passed` | `live-measurement` |
| `resource_idle_memory` | `inconclusive` | `live-measurement-unavailable` |
| `resource_one_tab_memory` | `inconclusive` | `live-measurement-unavailable` |
| `resource_process_count` | `passed` | `live-measurement` |
| `resource_shutdown_duration` | `passed` | `live-measurement` |
| `sensitive_cookies_storage_excluded` | `passed` | `live-runtime-proven` |
| `sensitive_hidden_input_excluded` | `passed` | `live-runtime-proven` |
| `sensitive_password_excluded` | `passed` | `live-runtime-proven` |
| `sensitive_scripts_styles_excluded` | `passed` | `live-runtime-proven` |
| `sensitive_text_input_excluded` | `passed` | `live-runtime-proven` |
| `static_credential_location` | `passed` | `proven-repository` |
| `static_csp_policy` | `passed` | `proven-repository` |
| `static_dependency_versions` | `passed` | `proven-repository` |
| `static_host_commands_ipc` | `passed` | `proven-repository` |
| `static_package_configuration` | `passed` | `proven-repository` |
| `static_privileges_capabilities` | `passed` | `proven-repository` |
| `static_remote_content` | `passed` | `proven-repository` |
| `static_webview_engine` | `passed` | `proven-repository` |

_Generated by Codexify Browser Host Harness v0.1.0._
