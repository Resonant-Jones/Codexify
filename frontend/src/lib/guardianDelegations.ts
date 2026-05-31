import api from "@/lib/api";
import type { GuardianDelegationTranscriptResponse } from "@/contracts/guardianDelegationTranscript";

export type GuardianDelegationTranscriptErrorKind =
  | "not_found"
  | "unavailable";

export class GuardianDelegationTranscriptError extends Error {
  kind: GuardianDelegationTranscriptErrorKind;
  status: number | null;
  originalError: unknown;

  constructor(
    kind: GuardianDelegationTranscriptErrorKind,
    message: string,
    options: { originalError?: unknown; status?: number | null } = {}
  ) {
    super(message);
    this.name = "GuardianDelegationTranscriptError";
    this.kind = kind;
    this.status = options.status ?? null;
    this.originalError = options.originalError;
  }

  static isInstance(value: unknown): value is GuardianDelegationTranscriptError {
    return value instanceof GuardianDelegationTranscriptError;
  }
}

function normalizeIntentId(intentId: string): string {
  return encodeURIComponent(intentId.trim());
}

function getErrorStatus(error: unknown): number | null {
  const status = (error as { response?: { status?: unknown } } | null)
    ?.response?.status;
  return typeof status === "number" ? status : null;
}

function getErrorDetail(error: unknown): string | null {
  const detail = (error as { response?: { data?: { detail?: unknown } } } | null)
    ?.response?.data?.detail;
  return typeof detail === "string" ? detail : null;
}

function classifyTranscriptError(
  error: unknown
): GuardianDelegationTranscriptError | null {
  const status = getErrorStatus(error);
  const detail = getErrorDetail(error);

  if (status === 404 && detail === "guardian_delegation_intent_not_found") {
    return new GuardianDelegationTranscriptError(
      "not_found",
      "Guardian delegation intent was not found.",
      { originalError: error, status }
    );
  }

  if (status === 403 || status === 404 || status === 405 || status === 501 || status === 503) {
    return new GuardianDelegationTranscriptError(
      "unavailable",
      "Guardian delegation transcript inspection is unavailable in this runtime posture.",
      { originalError: error, status }
    );
  }

  return null;
}

export async function getGuardianDelegationTranscript(
  intentId: string
): Promise<GuardianDelegationTranscriptResponse> {
  const normalizedIntentId = normalizeIntentId(intentId);
  if (!normalizedIntentId) {
    throw new GuardianDelegationTranscriptError(
      "not_found",
      "Guardian delegation intent id is required."
    );
  }

  try {
    const response = await api.get<GuardianDelegationTranscriptResponse>(
      `/api/guardian/delegations/${normalizedIntentId}/transcript`
    );
    return response.data;
  } catch (error) {
    const classified = classifyTranscriptError(error);
    if (classified) throw classified;
    throw error;
  }
}
