export const STEP_KEYS = [
  "welcome",
  "identity",
  "username",
  "navigation",
  "core_surfaces",
  "help",
] as const;
export type StepKey = (typeof STEP_KEYS)[number];
export type OnboardingState = {
  onboarding_version: number;
  status: "not_started" | "in_progress" | "skipped" | "completed";
  last_step_key: StepKey | null;
  desktop_tour_completed: boolean;
  mobile_tour_completed: boolean;
  contextual_tips_enabled: boolean;
};
export const DEFAULT_STATE: OnboardingState = {
  onboarding_version: 1,
  status: "not_started",
  last_step_key: null,
  desktop_tour_completed: false,
  mobile_tour_completed: false,
  contextual_tips_enabled: true,
};
