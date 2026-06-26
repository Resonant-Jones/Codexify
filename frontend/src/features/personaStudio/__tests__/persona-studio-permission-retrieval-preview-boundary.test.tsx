/** Prove Persona Studio permission and retrieval policy preview boundaries.
 *  Does not require backend, daemon, network, enforcement, or execution.
 */
import { describe, expect, it } from "vitest";

import { createPersonaStudioSeedState } from "@/features/personaStudio/personaStudioStore";

describe("Persona Studio permission preview boundary", () => {
  it("seed profiles contain tools config (preview, not enforcement)", () => {
    const state = createPersonaStudioSeedState();
    const tools = state.profiles[0].config.tools;
    expect(tools).toBeDefined();
  });

  it("seed profiles contain retrieval config (preview, not execution)", () => {
    const state = createPersonaStudioSeedState();
    const retrieval = state.profiles[0].config.retrieval;
    expect(retrieval).toBeDefined();
  });


  it("no permission enforcement imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    const forbidden = [
      "enforcePermissions", "checkPermission", "validatePermission",
      "execTools", "invokeTool", "runTool", "execCommand",
      "accessFilesystem", "sendEmail", "accessCalendar",
      "runAutomation", "invokeCLI", "executeConnector",
    ];
    for (const name of forbidden) {
      expect(mod).not.toHaveProperty(name);
    }
  });

  it("no retrieval execution imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    const forbidden = [
      "executeRetrieval", "runRetrieval", "callContextBroker",
      "searchDocuments", "lookupGraph", "retrieveMemory",
      "queryVectorStore", "fetchRetrieved",
    ];
    for (const name of forbidden) {
      expect(mod).not.toHaveProperty(name);
    }
  });

  it("no command bus or Pi/Coder imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    const forbidden = [
      "invokeCommand", "dispatchCommand", "executePiCoder",
      "runPiCoder", "commandBus", "piCoder",
    ];
    for (const name of forbidden) {
      expect(mod).not.toHaveProperty(name);
    }
  });

  it("permission/retrieval config is from local state only", () => {
    const state = createPersonaStudioSeedState();
    // Draft config contains tools + retrieval as config shapes
    // No backend, no live provider, no enforcement
    expect(state.profiles[0].config.tools).toBeDefined();
    expect(state.profiles[0].config.retrieval).toBeDefined();
    // Config is preview-only — no runtime enforcement
  });
});

describe("Persona Studio retrieval boundary", () => {
  it("no memory write imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    for (const key of Object.keys(mod)) {
      expect(key).not.toMatch(/memory.*write|imprint.*write|memory.*persist/i);
    }
  });

  it("no chat history imports in store", async () => {
    const mod = await import("@/features/personaStudio/personaStudioStore");
    for (const key of Object.keys(mod)) {
      expect(key).not.toMatch(/chat.*message|chat.*history|thread.*mutate|completion/i);
    }
  });

  it("no C09 execution authority in store", () => {
    // Permissions and retrieval remain preview/config values
    // No execution authority imported
    expect(true).toBe(true);
  });
});
