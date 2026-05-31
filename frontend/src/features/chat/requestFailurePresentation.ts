import {
  PROVIDER_FAILURE_KINDS,
  PROVIDER_TRANSPORT_CLASSIFICATIONS,
} from "@/contracts/runtimeTokens";

export const GENERIC_PROVIDER_FAILURE_DETAIL_TEXT =
  "Provider error: try again or switch to a faster mode.";

export const PROVIDER_TIMEOUT_DETAIL_TEXT =
  "Provider request timed out. Try again or switch to a faster mode.";

export const PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT =
  "Provider timed out after accepting the request and before the first token. Try again or switch to a faster mode.";

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

  if (isFirstTokenTimeout(payload)) {
    return PROVIDER_FIRST_TOKEN_TIMEOUT_DETAIL_TEXT;
  }

  if (hasProviderTimeoutClassification(payload)) {
    return PROVIDER_TIMEOUT_DETAIL_TEXT;
  }

  return GENERIC_PROVIDER_FAILURE_DETAIL_TEXT;
}
