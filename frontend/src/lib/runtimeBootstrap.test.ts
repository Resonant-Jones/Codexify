import { afterEach, describe, expect, it, vi, beforeEach } from "vitest";
import { act } from "@testing-library/react";

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
  getBootstrapDisplayCopy,
  getBootstrapRecoveryActions,
  formatRuntimeReadinessResult,
  runPullRuntimeImages,
  runRuntimeBootstrapPreflight,
  waitForRuntimeReady,
  normalizeRuntimeReadiness,
  type RuntimePreflight,
} from "@/lib/runtimeBootstrap";
import {
  NATIVE_BRIDGE_FAILURE_KIND,
  invokeTauriCommand,
  isTauriRuntime,
} from "@/lib/runtimeConfig";

const flushPromises = async () => {
  await Promise.resolve();
  await vi.advanceTimersByTimeAsync(0);
};

describe("runtime bootstrap preflight", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(isTauriRuntime).mockReturnValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
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

  it("renders packaged registry image missing guidance", () => {
    const preflight: RuntimePreflight = {
      dockerCliInstalled: true,
      dockerComposeAvailable: true,
      dockerDaemonReachable: true,
      ready: false,
      failureKind: "runtime-images-missing",
      detail: "runtime images state missing",
      checksExecuted: true,
    };

    const state = mapRuntimePreflightFailureToState(preflight);
    const displayCopy = getBootstrapDisplayCopy(state);

    expect(state.title).toBe("Codexify needs to download its local runtime images");
    expect(displayCopy.message).toContain("Retry setup checks");
    expect(getBootstrapRecoveryActions(state)).toEqual(["retry"]);
  });

  it("renders packaged registry image pull failure guidance", () => {
    const preflight: RuntimePreflight = {
      dockerCliInstalled: true,
      dockerComposeAvailable: true,
      dockerDaemonReachable: true,
      ready: false,
      failureKind: "runtime-image-pull-failed",
      detail: "docker compose pull failed",
      checksExecuted: true,
    };

    const state = mapRuntimePreflightFailureToState(preflight);
    const displayCopy = getBootstrapDisplayCopy(state);

    expect(state.title).toBe("Runtime image pull failed");
    expect(displayCopy.message).toContain("registry credentials");
  });

  it("invokes the packaged registry image pull command", async () => {
    vi.mocked(invokeTauriCommand).mockResolvedValue({
      ok: true,
      step: "pull-images",
      detail: "pulled registry images",
    });

    const result = await runPullRuntimeImages();

    expect(invokeTauriCommand).toHaveBeenCalledWith(
      "desktop_pull_registry_runtime_images"
    );
    expect(result.step).toBe("pull-images");
    expect(result.ok).toBe(true);
  });

  it("normalizes and formats packaged readiness diagnostics from the native dispatcher", () => {
    const readiness = normalizeRuntimeReadiness({
      ok: true,
      ready: true,
      backendReachable: true,
      startupReady: true,
      redisReady: true,
      chatReady: true,
      llmReady: true,
      probeContext: "host-native",
      llmStatus: "ok",
      llmDetailsStatus: "online",
      llmDetailsOk: true,
      llmProvider: "local",
      llmModel: "library2/ministral-3:8b",
      llmProviderRuntimeAvailable: true,
      llmEndpointResolutionState: "available",
      llmFailureReason: null,
      checks: [
        {
          endpoint: "http://127.0.0.1:8888/api/health/llm",
          ok: true,
          statusCode: 200,
          detail: "HTTP/1.1 200 OK",
          responseExcerpt: "{\"status\":\"ok\"}",
        },
      ],
    });

    expect(readiness.llmReady).toBe(true);
    expect(readiness.probeContext).toBe("host-native");
    expect(readiness.llmStatus).toBe("ok");
    expect(readiness.llmDetailsStatus).toBe("online");
    expect(readiness.llmDetailsOk).toBe(true);
    expect(readiness.llmProvider).toBe("local");
    expect(readiness.llmModel).toBe("library2/ministral-3:8b");
    expect(readiness.llmProviderRuntimeAvailable).toBe(true);
    expect(readiness.llmEndpointResolutionState).toBe("available");

    const rendered = formatRuntimeReadinessResult(readiness);
    expect(rendered).toContain("probeContext=host-native");
    expect(rendered).toContain("llmStatus=ok");
    expect(rendered).toContain("llmDetailsStatus=online");
    expect(rendered).toContain("llmDetailsOk=true");
    expect(rendered).toContain("llmProvider=local");
    expect(rendered).toContain("llmModel=library2/ministral-3:8b");
    expect(rendered).toContain("llmProviderRuntimeAvailable=true");
    expect(rendered).toContain("llmEndpointResolutionState=available");
    expect(rendered).toContain("llmReady=true");
  });

  it("keeps the startup gate moving when readiness turns green after an earlier red poll", async () => {
    vi.useFakeTimers();
    vi.mocked(invokeTauriCommand)
      .mockResolvedValueOnce({
        ok: false,
        ready: false,
        step: "health-check",
        backendReachable: true,
        startupReady: true,
        redisReady: true,
        chatReady: true,
        llmReady: false,
        probeContext: "host-native",
        llmStatus: "ok",
        llmDetailsStatus: "online",
        llmDetailsOk: false,
        llmProvider: "local",
        llmModel: "library2/ministral-3:8b",
        llmProviderRuntimeAvailable: false,
        llmEndpointResolutionState: "unavailable",
        llmFailureReason: "provider_runtime.available=false",
        checks: [],
      })
      .mockResolvedValueOnce({
        ok: true,
        ready: true,
        step: "health-check",
        backendReachable: true,
        startupReady: true,
        redisReady: true,
        chatReady: true,
        llmReady: true,
        probeContext: "host-native",
        llmStatus: "ok",
        llmDetailsStatus: "online",
        llmDetailsOk: true,
        llmProvider: "local",
        llmModel: "library2/ministral-3:8b",
        llmProviderRuntimeAvailable: true,
        llmEndpointResolutionState: "available",
        checks: [],
      });

    const readinessPromise = waitForRuntimeReady({
      timeoutMs: 6_000,
      intervalMs: 500,
    });

    await act(async () => {
      await flushPromises();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
      await flushPromises();
    });

    const result = await readinessPromise;

    expect(result.ok).toBe(true);
    expect(result.attempts).toBe(2);
    expect(result.lastCheck.llmReady).toBe(true);
    expect(result.lastCheck.llmFailureReason).toBeUndefined();
  });
});
