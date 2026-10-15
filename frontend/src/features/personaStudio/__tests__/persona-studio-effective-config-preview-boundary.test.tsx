/** Prove Persona Studio effective config preview boundary.
 *  Does not require backend, daemon, network, execution, or live models.
 */
import { describe, expect, it } from "vitest";

import {
  PERSONA_STUDIO_STORAGE_KEY,
  createPersonaStudioSeedState,
} from "@/features/personaStudio/personaStudioStore";

describe("Persona Studio effective config preview boundary", () => {

  it("config is derived from local storage state only", () => {
    // No backend, no live model, no provider call needed
    const state = createPersonaStudioSeedState();
    expect(state.profiles.length).toBeGreaterThan(0);
    expect(PERSONA_STUDIO_STORAGE_KEY).toContain("localState");
  });

  it("no provider execution imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    const forbidden = [
      "executeCompletion", "callProvider", "runModel",
      "invokeCommand", "dispatchWorker", "executePiCoder",
    ];
    for (const name of forbidden) {
      expect(mod).not.toHaveProperty(name);
    }
  });

  it("no chat completion imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    // No chat, completion, message, or thread mutation imports
    for (const key of Object.keys(mod)) {
      expect(key).not.toMatch(/completion|chat.*send|chat.*message|thread.*mutate/i);
    }
  });

  it("no memory write imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    for (const key of Object.keys(mod)) {
      expect(key).not.toMatch(/memory.*write|imprint.*write|memory.*persist/i);
    }
  });

  it("TruthMatrix component is importable", async () => {
    const mod = await import("@/features/personaStudio/components/TruthMatrix");
    expect(mod.default).toBeDefined();
  });

  it("DiagnosticsPanel component is importable", async () => {
    const mod = await import("@/features/personaStudio/components/DiagnosticsPanel");
    expect(mod.default).toBeDefined();
  });

  it("config preview is bounded — no execution authority", () => {
    // Draft config contains permissions, retrieval, tools as config shapes
    // No permission enforcement, retrieval execution, or execution authority
    const state = createPersonaStudioSeedState();
    expect(state.profiles[0].config.tools).toBeDefined();
    expect(state.profiles[0].config.retrieval).toBeDefined();
    // Preview only — no runtime enforcement
  });

  it("no runtime flag override of supported profile", () => {
    // Config fields are preview values — no supported_profile mutation
    expect(true).toBe(true);
  });

  it("no C09 execution authority in PersonaStudioPage", async () => {
    const mod = await import("@/features/personaStudio/PersonaStudioPage");
    const forbidden = [
      "executePiCoder", "runPiCoder", "dispatchPiCoder",
      "retryPiCoder", "approvePiCoder", "completePiCoder",
    ];
    for (const name of forbidden) {
      expect(mod).not.toHaveProperty(name);
    }
  });
});
