import { afterEach, describe, expect, it, vi } from "vitest";

import {
  NATIVE_BRIDGE_FAILURE_KIND,
  NativeBridgeUnavailableError,
  invokeTauriCommand,
} from "@/lib/tauriBridge";

describe("tauri bridge", () => {
  afterEach(() => {
    delete (window as any).__TAURI_IPC__;
    delete (window as any).__TAURI_INTERNALS__;
    delete (window as any).__CFY_TAURI_CORE__;
  });

  it("classifies browser-mode command access as native bridge unavailable", async () => {
    delete (window as any).__TAURI_IPC__;
    delete (window as any).__TAURI_INTERNALS__;
    delete (window as any).__CFY_TAURI_CORE__;

    await expect(invokeTauriCommand("desktop_get_runtime_config")).rejects.toMatchObject(
      {
        code: NATIVE_BRIDGE_FAILURE_KIND,
      }
    );
  });

  it("uses the injected core when present", async () => {
    const invoke = vi.fn().mockResolvedValue("ok");
    (window as any).__TAURI_IPC__ = {};
    (window as any).__CFY_TAURI_CORE__ = { invoke };

    await expect(invokeTauriCommand("desktop_get_api_key")).resolves.toBe("ok");
    expect(invoke).toHaveBeenCalledWith("desktop_get_api_key", undefined);
  });

  it("exposes the native bridge error class for packaged diagnostics", () => {
    const error = new NativeBridgeUnavailableError("boom");
    expect(error.code).toBe(NATIVE_BRIDGE_FAILURE_KIND);
    expect(error.name).toBe("NativeBridgeUnavailableError");
  });
});
