import api from "@/lib/api";

/* ── types ── */

export type PiCoderDryRunRequest = {
  source_thread_id: string;
  source_message_id: string;
  invocation_id?: string;
  harness_id: string;
  harness_version: string;
  guardian_boundary?: Record<string, unknown>;
  provider_lane?: Record<string, unknown>;
  requested_permissions?: Array<Record<string, unknown>>;
  granted_permissions?: Array<Record<string, unknown>>;
  validation_metadata?: Record<string, unknown>;
};

export type PiCoderDryRunResponse = {
  dry_run: boolean;
  accepted: boolean;
  state: string;
  validation_status: string;
  errors: string[];
  warnings: string[];
  redaction_state: string;
  release_support: string;
  execution_performed: boolean;
  persistence_performed: boolean;
  invocation_id?: string | null;
  source_thread_id?: string | null;
  source_message_id?: string | null;
  harness_id?: string | null;
  permission_posture?: string | null;
};

/* ── helpers ── */

/** Call the Pi/Coder validation-only dry-run route.
 *
 * This route accepts an invocation envelope and returns safe dry-run
 * validation evidence. It does NOT execute, persist, or enqueue work.
 */
export async function validatePiCoderDryRun(
  request: PiCoderDryRunRequest,
): Promise<PiCoderDryRunResponse> {
  const resp = await api.post<PiCoderDryRunResponse>(
    "/api/agents/pi-invocation/dry-run",
    request,
  );
  return resp.data;
}
