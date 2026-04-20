export type FlowBuilderMode = "process" | "expertise";

export const FLOW_BUILDER_PATHNAME = "/flow-builder";
export const FLOW_BUILDER_MODE_QUERY_KEY = "mode";
export const DEFAULT_FLOW_BUILDER_MODE: FlowBuilderMode = "process";

export function isFlowBuilderMode(value: unknown): value is FlowBuilderMode {
  return value === "process" || value === "expertise";
}

export function parseFlowBuilderMode(search: string): FlowBuilderMode | null {
  const params = new URLSearchParams(search);
  const rawMode = params.get(FLOW_BUILDER_MODE_QUERY_KEY);
  return isFlowBuilderMode(rawMode) ? rawMode : null;
}

export function hasFlowBuilderModeQuery(search: string): boolean {
  const params = new URLSearchParams(search);
  return params.has(FLOW_BUILDER_MODE_QUERY_KEY);
}

export function getFlowBuilderPath(mode: FlowBuilderMode): string {
  const params = new URLSearchParams();
  params.set(FLOW_BUILDER_MODE_QUERY_KEY, mode);
  return `${FLOW_BUILDER_PATHNAME}?${params.toString()}`;
}
