import { buildAuthenticatedFetchInit } from "@/lib/api";
import { resolveApiUrl } from "@/lib/runtimeConfig";

export type HeartbeatStatusResponse = {
  latest_date: string | null;
  heartbeat_report_path: string | null;
  staged_outbox_path: string | null;
  review_status: string;
  outbox_status: string;
  publication_enabled: boolean;
  publication_targets: string[];
  generated_files: string[];
  warnings: string[];
  failures: string[];
  manual_commands: string[];
};

export async function fetchHeartbeatStatus(): Promise<HeartbeatStatusResponse> {
  const url = resolveApiUrl("/api/heartbeat/status");
  const init = buildAuthenticatedFetchInit({ method: "GET" });
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`Heartbeat status fetch failed: ${response.status}`);
  }
  return response.json();
}
