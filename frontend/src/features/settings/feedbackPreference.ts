export const GUARDIAN_FEEDBACK_OPT_IN_STORAGE_KEY =
  "cfy.guardian.feedback.optIn";

export function readGuardianFeedbackOptIn(): boolean {
  if (typeof window === "undefined") return false;

  try {
    return window.localStorage.getItem(GUARDIAN_FEEDBACK_OPT_IN_STORAGE_KEY) ===
      "true";
  } catch {
    return false;
  }
}

export function writeGuardianFeedbackOptIn(enabled: boolean): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(
      GUARDIAN_FEEDBACK_OPT_IN_STORAGE_KEY,
      String(enabled)
    );
  } catch {
    // Preferences remain best-effort when browser storage is unavailable.
  }
}
