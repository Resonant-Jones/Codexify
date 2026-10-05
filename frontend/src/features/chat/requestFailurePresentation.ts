import {
  PROVIDER_FAILURE_KINDS,
  PROVIDER_TRANSPORT_CLASSIFICATIONS,
  TOOL_LOOP_STOP_REASONS,
  TOOL_TURN_STATES,
  type ToolCommandFailureReason,
} from "@/contracts/runtimeTokens";

export const GENERIC_PROVIDER_FAILURE_DETAIL_TEXT =
  "Provider error: try again or switch to a faster mode.";

export const PROVIDER_TIMEOUT_DETAIL_TEXT =
  "Provider request timed out. Try again or switch to a faster mode.";

export const PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT =
  "Provider timed out after accepting the request and before the first token. Try again or switch to a faster mode.";

export const ACCEPTED_TASK_ORPHAN_DETAIL_TEXT =
  "No completed response was recorded. This request was closed after its recovery deadline. Send a new request to try again.";

export const ACCEPTED_TASK_DEADLINE_DETAIL_TEXT =
  "The request reached its execution time limit. Try again.";

export const TOOL_COMMAND_FAILED_DETAIL_TEXT =
  "The requested action failed. Guardian could not finish this reply.";

export const TOOL_COMMAND_BLOCKED_DETAIL_TEXT =
  "The requested action was not authorized. Guardian could not finish this reply.";

export function getToolCommandFailureReason(
  payload: Record<string, unknown> | null | undefined
): ToolCommandFailureReason | null {
  if (isRetryableAcceptedTaskFailure(payload)) return null;
  if (
    (payload?.toolTurnState ?? payload?.tool_turn_state) !== TOOL_TURN_STATES.FAILED
  ) {
    return null;
  }
  const reason = payload?.loopStopReason ?? payload?.loop_stop_reason;
  return reason === TOOL_LOOP_STOP_REASONS.TOOL_COMMAND_FAILED ||
    reason === TOOL_LOOP_STOP_REASONS.TOOL_COMMAND_BLOCKED
    ? reason
    : null;
}

export function isAcceptedTaskDeadlineFailure(
  payload: Record<string, unknown> | null | undefined
): boolean {
  // Existing Guardian ErrorCode; presentation must follow typed failure truth.
  return payload?.failure_code === "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED";
}

export function isAcceptedTaskOrphanFailure(
  payload: Record<string, unknown> | null | undefined
): boolean {
  return payload?.failure_code === "CHAT_ACCEPTED_TASK_ORPHANED";
}

export function isRetryableAcceptedTaskFailure(
  payload: Record<string, unknown> | null | undefined
): boolean {
  return isAcceptedTaskOrphanFailure(payload) || isAcceptedTaskDeadlineFailure(payload);
}

function normalizeToken(value: unknown): string {
  return String(value ?? "").trim().toLowerCase();
}

function normalizeBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  const normalized = normalizeToken(value);
  if (normalized === "true") return true;
  if (normalized === "false") return false;
  return null;
}

function hasProviderTimeoutClassification(payload: Record<string, unknown>): boolean {
  const failureKind = normalizeToken(
    payload.failure_kind ?? payload.provider_failure_kind
  );
  const transportClassification = normalizeToken(
    payload.transport_classification
  );
  return (
    failureKind === PROVIDER_FAILURE_KINDS.PROVIDER_TIMEOUT ||
    transportClassification === PROVIDER_TRANSPORT_CLASSIFICATIONS.TIMEOUT
  );
}

function isFirstTokenTimeout(payload: Record<string, unknown>): boolean {
  if (!hasProviderTimeoutClassification(payload)) {
    return false;
  }

  const failedAfterState = normalizeToken(payload.failed_after_state).replace(
    /[\s-]+/g,
    "_"
  );
  const providerRequestStarted = normalizeBoolean(
    payload.provider_request_started
  );
  const firstOutputObserved = normalizeBoolean(payload.first_output_observed);

  return (
    failedAfterState === "awaiting_first_token" &&
    providerRequestStarted === true &&
    firstOutputObserved === false
  );
}

export function describeTaskFailureDetailText(
  payload: Record<string, unknown> | null | undefined
): string {
  if (!payload) {
    return GENERIC_PROVIDER_FAILURE_DETAIL_TEXT;
  }

  if (isAcceptedTaskOrphanFailure(payload)) {
    return ACCEPTED_TASK_ORPHAN_DETAIL_TEXT;
  }
  if (isAcceptedTaskDeadlineFailure(payload)) {
    return ACCEPTED_TASK_DEADLINE_DETAIL_TEXT;
  }

  const toolFailure = getToolCommandFailureReason(payload);
  if (toolFailure === TOOL_LOOP_STOP_REASONS.TOOL_COMMAND_FAILED) {
    return TOOL_COMMAND_FAILED_DETAIL_TEXT;
  }
  if (toolFailure === TOOL_LOOP_STOP_REASONS.TOOL_COMMAND_BLOCKED) {
    return TOOL_COMMAND_BLOCKED_DETAIL_TEXT;
  }

  if (isFirstTokenTimeout(payload)) {
    return PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT;
  }

  if (hasProviderTimeoutClassification(payload)) {
    return PROVIDER_TIMEOUT_DETAIL_TEXT;
  }

  return GENERIC_PROVIDER_FAILURE_DETAIL_TEXT;
}
