import { afterEach, expect, it, vi } from "vitest";
import { fetchOnboarding, patchOnboarding } from "../onboardingApi";
import { claimSocialIdentityUsername } from "@/lib/direct-messages";
const mocks = vi.hoisted(() => ({
  put: vi.fn(),
  build: vi.fn((init: RequestInit) => ({ ...init, credentials: "include" })),
}));
vi.mock("@/lib/api", () => ({
  default: { put: mocks.put },
  buildAuthenticatedFetchInit: mocks.build,
}));
vi.mock("@/lib/runtimeConfig", () => ({ resolveApiUrl: (path: string) => path }));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});
it("uses existing social-identity PUT and returns its server profile", async () => {
  const profile = { username: "alias", username_state: "active" };
  mocks.put.mockResolvedValue({ data: { profile } });
  expect(await claimSocialIdentityUsername("alias")).toEqual(profile);
  expect(mocks.put).toHaveBeenCalledWith("/api/profile/social-identity", { username: "alias" });
});
it("sends authenticated bounded partial progress", async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "skipped" }) });
  vi.stubGlobal("fetch", fetch);
  await patchOnboarding({ status: "skipped" });
  expect(fetch).toHaveBeenCalledWith(
    "/api/onboarding",
    expect.objectContaining({
      method: "PATCH",
      body: '{"status":"skipped"}',
      credentials: "include",
    })
  );
});
it("reports 401 locally without using the shared axios client", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 401 }));
  await expect(fetchOnboarding()).rejects.toThrow("401");
  expect(mocks.put).not.toHaveBeenCalled();
});

it("displays server username validation without changing onboarding state", async () => {
  mocks.put.mockRejectedValue({
    response: {
      status: 409,
      data: {
        detail: { error: "username_taken", message: "Username is already taken on this node" },
      },
    },
  });
  await expect(claimSocialIdentityUsername("alias")).rejects.toThrow(
    "Username is already taken on this node"
  );
});

it("renders backend request validation messages", async () => {
  mocks.put.mockRejectedValue({ response: { status: 422, data: { detail: [{ msg: "String should have at least 1 character" }] } } });
  await expect(claimSocialIdentityUsername("")).rejects.toThrow("String should have at least 1 character");
});
