export const SUPPORTED_PROFILE_ROUTE_LABELS = {
  IMPRINT: "imprint",
  SYSTEM_PROMPT: "system_prompt",
  SYSTEM_DOCS: "system_docs",
  CONNECTORS: "connectors",
  CODEX: "codex",
  UI_SESSION: "ui_session",
  AGENT_ORCHESTRATION_CHAT: "agent_orchestration_chat",
} as const;

export type SupportedProfileRouteLabel =
  (typeof SUPPORTED_PROFILE_ROUTE_LABELS)[keyof typeof SUPPORTED_PROFILE_ROUTE_LABELS];

export type RuntimeRouteCapabilityState =
  | "available"
  | "unavailable"
  | "unknown";

export const ALL_SUPPORTED_PROFILE_ROUTE_LABELS: SupportedProfileRouteLabel[] =
  Object.values(SUPPORTED_PROFILE_ROUTE_LABELS);

const SUPPORTED_PROFILE_ROUTE_LABEL_SET = new Set<SupportedProfileRouteLabel>(
  ALL_SUPPORTED_PROFILE_ROUTE_LABELS
);

export function isSupportedProfileRouteLabel(
  value: unknown
): value is SupportedProfileRouteLabel {
  return (
    typeof value === "string" &&
    SUPPORTED_PROFILE_ROUTE_LABEL_SET.has(value as SupportedProfileRouteLabel)
  );
}
