import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import {
  __resetRuntimeRouteCapabilitiesForTests,
  markRuntimeRouteUnavailableIfNotFound,
  useRuntimeRouteCapability,
} from "@/lib/runtimeRouteCapabilities";

function mockHealthPayload(payload: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => payload,
    }))
  );
}

describe("runtimeRouteCapabilities", () => {
  beforeEach(() => {
    __resetRuntimeRouteCapabilitiesForTests();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("treats mounted routes as authoritative", async () => {
    mockHealthPayload({
      supported_profile: {
        routes: {
          mounted: [SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT],
          declared: {
            [SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT]: "quarantined",
            [SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS]: "enabled",
          },
        },
      },
    });

    const { result } = renderHook(() =>
      useRuntimeRouteCapability(SUPPORTED_PROFILE_ROUTE_LABELS.IMPRINT)
    );

    await waitFor(() => {
      expect(result.current.ready).toBe(true);
    });

    expect(result.current.state).toBe("available");
  });

  it("ignores declared status for behavior when a route is not mounted", async () => {
    mockHealthPayload({
      supported_profile: {
        routes: {
          mounted: [],
          declared: {
            [SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS]: "enabled",
          },
        },
      },
    });

    const { result } = renderHook(() =>
      useRuntimeRouteCapability(SUPPORTED_PROFILE_ROUTE_LABELS.CONNECTORS)
    );

    await waitFor(() => {
      expect(result.current.ready).toBe(true);
    });

    expect(result.current.state).toBe("unavailable");
  });

  it("returns unknown when /health lacks supported profile route data", async () => {
    mockHealthPayload({ status: "ok" });

    const { result } = renderHook(() =>
      useRuntimeRouteCapability(SUPPORTED_PROFILE_ROUTE_LABELS.SYSTEM_PROMPT)
    );

    await waitFor(() => {
      expect(result.current.ready).toBe(true);
    });

    expect(result.current.state).toBe("unknown");
  });

  it("demotes unknown routes to unavailable after a 404", async () => {
    mockHealthPayload({ status: "ok" });

    const { result } = renderHook(() =>
      useRuntimeRouteCapability(
        SUPPORTED_PROFILE_ROUTE_LABELS.AGENT_ORCHESTRATION_CHAT
      )
    );

    await waitFor(() => {
      expect(result.current.ready).toBe(true);
    });

    expect(result.current.state).toBe("unknown");

    markRuntimeRouteUnavailableIfNotFound(
      SUPPORTED_PROFILE_ROUTE_LABELS.AGENT_ORCHESTRATION_CHAT,
      { response: { status: 404 } }
    );

    await waitFor(() => {
      expect(result.current.state).toBe("unavailable");
    });
  });
});
