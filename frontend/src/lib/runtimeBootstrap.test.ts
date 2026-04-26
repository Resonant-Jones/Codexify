import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/lib/runtimeConfig", async () => {
  const actual = await vi.importActual<typeof import("@/lib/runtimeConfig")>(
    "@/lib/runtimeConfig"
  );
  return {
    ...actual,
    isTauriRuntime: vi.fn(() => true),
    invokeTauriCommand: vi.fn(),
    openExternalUrl: vi.fn(),
  };
});

import {
  NativeBridgeUnavailableError,
} from "@/lib/runtimeConfig";
import {
  mapRuntimePreflightFailureToState,
  runRuntimeBootstrapPreflight,
  type RuntimePreflight,
} from "@/lib/runtimeBootstrap";
import {
  NATIVE_BRIDGE_FAILURE_KIND,
  invokeTauriCommand,
  isTauriRuntime,
} from "@/lib/runtimeConfig";

describe("runtime bootstrap preflight", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(isTauriRuntime).mockReturnValue(true);
  });

  it("classifies a native bridge import failure separately from Docker failures", async () => {
    vi.mocked(invokeTauriCommand).mockRejectedValue(
      new NativeBridgeUnavailableError(
        "Module name, '@tauri-apps/api/core' does not resolve to a valid URL."
      )
    );

    const result = await runRuntimeBootstrapPreflight();

    expect(result.failureKind).toBe(NATIVE_BRIDGE_FAILURE_KIND);
    expect(result.checksExecuted).toBe(false);
    expect(result.dockerCliInstalled).toBeNull();
    expect(result.dockerComposeAvailable).toBeNull();
    expect(result.dockerDaemonReachable).toBeNull();
    expect(result.detail).toContain("@tauri-apps/api/core");
  });

  it("preserves the existing Docker Desktop guidance when Docker CLI is actually missing", () => {
    const preflight: RuntimePreflight = {
      dockerCliInstalled: false,
      dockerComposeAvailable: false,
      dockerDaemonReachable: false,
      ready: false,
      failureKind: "docker-cli-unavailable",
      detail: "docker missing",
      checksExecuted: true,
    };

    const state = mapRuntimePreflightFailureToState(preflight);

    expect(state.title).toBe("Docker Desktop is required");
    expect(state.message).toContain("Install Docker Desktop");
  });

  it("renders a dedicated native bridge diagnosis instead of Docker missing", () => {
    const preflight: RuntimePreflight = {
      dockerCliInstalled: null,
      dockerComposeAvailable: null,
      dockerDaemonReachable: null,
      ready: false,
      failureKind: NATIVE_BRIDGE_FAILURE_KIND,
      detail: "Module name, '@tauri-apps/api/core' does not resolve to a valid URL.",
      checksExecuted: false,
    };

    const state = mapRuntimePreflightFailureToState(preflight);

    expect(state.title).toBe("Desktop native bridge unavailable");
    expect(state.message).toContain("Open Codexify from the desktop app");
    expect(state.message).not.toContain("Docker Desktop is required");
  });
});
