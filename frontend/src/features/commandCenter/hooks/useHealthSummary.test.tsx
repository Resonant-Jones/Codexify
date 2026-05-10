import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import useHealthSummary from "@/features/commandCenter/hooks/useHealthSummary";
import * as runtimeConfig from "@/lib/runtimeConfig";

function makeRuntimeConfig(
  overrides: Partial<runtimeConfig.RuntimeConfig> = {}
): runtimeConfig.RuntimeConfig {
  return {
    apiBaseUrl: "/api",
    authMode: "local",
    backendBaseUrl: "",
    mode: "web",
    sharePublicBaseUrl: "",
    sseUrl: "/api/events",
    ...overrides,
  };
}

describe("useHealthSummary endpoint resolution", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses browser-safe relative health endpoints in web mode", () => {
    vi.stubEnv("VITE_PROXY_TARGET", "http://backend:8888");
    vi.spyOn(runtimeConfig, "getRuntimeConfigSync").mockReturnValue(
      makeRuntimeConfig({
        backendBaseUrl: "",
        mode: "web",
      })
    );

    const { result } = renderHook(() => useHealthSummary({ enabled: false }));
    const endpoints = result.current.healthItems.map((item) => item.endpoint);

    expect(endpoints).toContain("/health");
    expect(endpoints).toContain("/health/deps");
    expect(endpoints).toContain("/health/vector");
    expect(endpoints).toContain("/health/memory");
    expect(endpoints).not.toContain("http://backend:8888/health");
    expect(endpoints.every((endpoint) => !endpoint.includes("backend:8888"))).toBe(
      true
    );
  });

  it("uses explicit backend URL resolution in tauri mode", () => {
    vi.spyOn(runtimeConfig, "getRuntimeConfigSync").mockReturnValue(
      makeRuntimeConfig({
        apiBaseUrl: "http://127.0.0.1:8888/api",
        backendBaseUrl: "http://127.0.0.1:8888",
        mode: "tauri",
        sharePublicBaseUrl: "http://127.0.0.1:5173",
        sseUrl: "http://127.0.0.1:8888/api/events",
      })
    );

    const { result } = renderHook(() => useHealthSummary({ enabled: false }));
    const endpoints = result.current.healthItems.map((item) => item.endpoint);

    expect(endpoints).toContain("http://127.0.0.1:8888/health");
    expect(endpoints).toContain("http://127.0.0.1:8888/health/deps");
  });
});
