import { buildAuthenticatedFetchInit } from "@/lib/api";
import { resolveApiUrl } from "@/lib/runtimeConfig";
import type { OnboardingState } from "./onboardingTypes";

async function request(
  method: "GET" | "PATCH",
  changes?: Partial<OnboardingState>
): Promise<OnboardingState> {
  // Reuse account credentials without the global axios 401/logout or outage fuse.
  const response = await fetch(
    resolveApiUrl("/api/onboarding"),
    buildAuthenticatedFetchInit({
      method,
      headers: { "Content-Type": "application/json" },
      body: changes ? JSON.stringify(changes) : undefined,
      signal: AbortSignal.timeout(10000),
    })
  );
  if (!response.ok)
    throw new Error(
      `Onboarding ${method.toLowerCase()} failed (${response.status}). Progress was not saved.`
    );
  return response.json();
}
export const fetchOnboarding = () => request("GET");
export const patchOnboarding = (changes: Partial<OnboardingState>) => request("PATCH", changes);
