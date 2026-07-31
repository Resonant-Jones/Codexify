"""Mandatory comparative Browser Host candidate case catalog.

Each bullet in specification section 12 has a stable case identifier. Candidate
receipts for enrolled implementations must contain every identifier with a
terminal status. A terminal status records evidence completion; it is not the
same thing as a passing architecture evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateCase:
    case_id: str
    lane: str
    assertion: str


def _lane(lane: str, assertions: dict[str, str]) -> tuple[CandidateCase, ...]:
    return tuple(CandidateCase(case_id, lane, assertion) for case_id, assertion in assertions.items())


MANDATORY_CANDIDATE_CASES: tuple[CandidateCase, ...] = (
    *_lane("static_boundary_inspection", {
        "static_privileges_capabilities": "Declared privileges and capabilities are inventoried.",
        "static_host_commands_ipc": "Host commands and IPC surfaces are inventoried.",
        "static_remote_content": "Remote-content configuration is explicit.",
        "static_credential_location": "Credential location is explicit.",
        "static_csp_policy": "CSP or equivalent policy is explicit.",
        "static_package_configuration": "Package configuration is explicit.",
        "static_dependency_versions": "Dependency versions are locked.",
        "static_webview_engine": "Browser engine version is recorded when knowable.",
    }),
    *_lane("build_and_package", {
        "build_clean_exact_command": "Clean build command and duration are recorded.",
        "build_artifact_hash_size": "Artifact path, hash, and size are recorded.",
        "build_generated_inventory": "Generated files are inventoried.",
        "package_command_or_unsupported": "Package result or explicit unsupported state is recorded.",
        "build_owned_cleanup": "Owned generated residue is declared and cleanup-safe.",
    }),
    *_lane("launch_and_navigation", {
        "launch_success": "Candidate launches within the deadline.",
        "navigation_one_remote_page": "Exactly one proof fixture page is active per renderer.",
        "navigation_state": "Title, URL, origin, loading, ready, and failure state are observable.",
        "navigation_same_cross_origin": "Same-origin and allowed cross-origin navigation are exercised.",
        "navigation_history_reload": "Back, forward, reload, or scoped equivalent is exercised.",
    }),
    *_lane("renderer_credential_isolation", {
        "credential_page_read_denied": "Remote page cannot read the sentinel.",
        "credential_page_message_denied": "Remote page cannot infer the sentinel through messages.",
        "credential_authenticated_request_denied": "Remote page cannot authenticate to Guardian stub.",
        "credential_global_state_absent": "Sentinel is absent from page-visible global state.",
        "credential_console_absent": "Sentinel is absent from page console output.",
        "credential_logs_absent": "Sentinel is absent from ordinary logs.",
    }),
    *_lane("native_authority_isolation", {
        "native_unrelated_command_denied": "Remote page cannot invoke unrelated native commands.",
        "native_filesystem_denied": "Remote page cannot access host filesystem.",
        "native_process_denied": "Remote page cannot start processes or shells.",
        "native_environment_secret_denied": "Remote page cannot access environment secrets.",
        "native_command_bus_denied": "Remote page cannot invoke Command Bus.",
        "native_permission_widening_denied": "Remote page cannot widen permissions.",
    }),
    *_lane("explicit_context_capture", {
        "capture_selected_text": "Selected visible text capture is exercised.",
        "capture_visible_page_text": "Bounded visible-page text capture is exercised.",
        "capture_explicit_user_gesture": "Capture begins from explicit trusted-shell action.",
        "capture_preview": "Preview or clear source indication is presented.",
        "capture_envelope_valid": "Browser Context Envelope validates.",
        "capture_single_request_attempt": "Attachment targets one explicit request attempt.",
        "capture_no_silent_persistence": "Captured content is not silently persisted.",
    }),
    *_lane("origin_document_integrity", {
        "integrity_origin_mismatch_rejected": "Origin mismatch is rejected.",
        "integrity_document_change_invalidates": "Document change invalidates pending capture.",
        "integrity_stale_navigation_rejected": "Stale capture after navigation is rejected.",
        "integrity_cross_origin_iframe_excluded": "Cross-origin iframe body is excluded.",
        "integrity_source_metadata_matches": "Source URL and title match captured document.",
    }),
    *_lane("sensitive_field_exclusion", {
        "sensitive_password_excluded": "Password values are excluded.",
        "sensitive_text_input_excluded": "Ordinary text-input values are excluded.",
        "sensitive_hidden_input_excluded": "Hidden-input values are excluded.",
        "sensitive_scripts_styles_excluded": "Scripts and styles are excluded.",
        "sensitive_cookies_storage_excluded": "Cookies and browser storage are excluded.",
    }),
    *_lane("prompt_injection_resistance", {
        "injection_host_policy_unchanged": "Page text cannot alter host policy.",
        "injection_browser_authority_denied": "Page text cannot grant browser actions.",
        "injection_command_bus_denied": "Page text cannot grant Command Bus authority.",
        "injection_credential_retrieval_denied": "Page text cannot retrieve Guardian credentials.",
        "injection_content_remains_evidence": "Captured page text remains evidence, not instruction.",
    }),
    *_lane("permission_failure_behavior", {
        "failure_observation_permission_denied": "Denied observation permission fails closed.",
        "failure_permission_revoked": "Revoked permission fails closed.",
        "failure_protected_target": "Protected or unsupported targets fail closed.",
        "failure_oversized_truncated": "Oversized capture is rejected or explicitly truncated.",
        "failure_malformed_response": "Malformed capture response is rejected.",
        "failure_capture_cancelled": "Capture cancellation clears pending state.",
        "failure_guardian_attachment": "Guardian-stub attachment failure is bounded.",
        "failure_companion_continuity": "Companion continuity after failure is recorded.",
    }),
    *_lane("renderer_failure_containment", {
        "renderer_failure_credential_safe": "Renderer crash or hang does not expose credentials.",
        "renderer_failure_native_safe": "Renderer failure does not grant native authority.",
        "renderer_failure_companion_bounded": "Trusted companion remains alive or degrades explicitly.",
        "renderer_failure_clean_termination": "Candidate terminates cleanly after renderer failure.",
    }),
    *_lane("observability_redaction", {
        "observability_correlations": "Run, case, candidate, capture, context, and request IDs correlate.",
        "observability_state_failure_codes": "State transitions and bounded failure codes are recorded.",
        "observability_raw_body_absent": "Raw page bodies are absent from evidence.",
        "observability_credentials_absent": "Credentials are absent from evidence.",
        "observability_form_storage_absent": "Cookies, form values, storage, and profiles are absent.",
    }),
    *_lane("accessibility", {
        "accessibility_keyboard_controls": "Keyboard-only access covers critical controls.",
        "accessibility_visible_focus": "Visible focus is present.",
        "accessibility_names": "Controls have accessible names.",
        "accessibility_focus_order": "Logical focus order is present.",
        "accessibility_text_scaling": "Text scaling behavior is inspected.",
        "accessibility_not_color_only": "Security state is not conveyed only by color.",
    }),
    *_lane("resource_measurement", {
        "resource_build_duration": "Build duration is measured.",
        "resource_artifact_size": "Package or artifact size is measured.",
        "resource_cold_launch": "Cold-launch duration is measured.",
        "resource_idle_memory": "Idle memory is measured.",
        "resource_one_tab_memory": "One-tab memory is measured.",
        "resource_capture_latency": "Capture latency is measured.",
        "resource_shutdown_duration": "Shutdown duration is measured.",
        "resource_process_count": "Process count or equivalent observation is recorded.",
    }),
    *_lane("cleanup", {
        "cleanup_candidate_processes": "No candidate process remains.",
        "cleanup_harness_servers": "No fixture or Guardian server remains.",
        "cleanup_credential_removed": "Synthetic credential is removed.",
        "cleanup_browser_profile": "No unauthorized browser-profile state remains.",
        "cleanup_worktree_scope": "No unrelated worktree change is introduced.",
        "cleanup_generated_residue": "Generated residue is removed or explicitly owned.",
    }),
)

MANDATORY_CANDIDATE_CASE_IDS: frozenset[str] = frozenset(
    case.case_id for case in MANDATORY_CANDIDATE_CASES
)

if len(MANDATORY_CANDIDATE_CASE_IDS) != len(MANDATORY_CANDIDATE_CASES):
    raise RuntimeError("duplicate Browser Host candidate case identifier")
