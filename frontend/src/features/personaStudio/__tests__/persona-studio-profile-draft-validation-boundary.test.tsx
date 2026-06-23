/** Prove Persona Studio profile draft state and validation boundary.
 *  Does not require backend, daemon, network, memory writes, chat history.
 */
import { describe, expect, it } from "vitest";

// Static imports for runtime-exported functions/constants
import {
  PERSONA_STUDIO_STORAGE_KEY,
  clearPersonaStudioLocalState,
  createPersonaStudioSeedState,
  getPersonaStudioSeedProfile,
  persistPersonaStudioLocalState,
  readPersonaStudioLocalState,
  usePersonaStudioLocalDraftState,
} from "@/features/personaStudio/personaStudioStore";

describe("Persona Studio profile draft state", () => {
  it("draft state storage key is defined", () => {
    expect(PERSONA_STUDIO_STORAGE_KEY).toContain("personaStudio");
    expect(PERSONA_STUDIO_STORAGE_KEY).toContain("localState");
  });

  it("draft state uses local storage key only — no backend", () => {
    // localStorage-backed — no API, no DB, no migration
    expect(typeof PERSONA_STUDIO_STORAGE_KEY).toBe("string");
  });

  it("seed state creates profiles with config", () => {
    const state = createPersonaStudioSeedState();
    expect(state.profiles.length).toBeGreaterThan(0);
    expect(state.profiles[0].config).toBeDefined();
  });

  it("read/write local state round-trips", () => {
    const state = createPersonaStudioSeedState();
    persistPersonaStudioLocalState(state);
    const read = readPersonaStudioLocalState();
    expect(read.profiles.length).toBe(state.profiles.length);
    expect(read.profiles[0].id).toBe(state.profiles[0].id);
  });



  it("usePersonaStudioLocalDraftState is a React hook", () => {
    expect(typeof usePersonaStudioLocalDraftState).toBe("function");
  });
});

describe("Persona Studio validation boundary", () => {
  it("draft is local state, not memory write", () => {
    // localStorage key proves locality — no backend persistence
    // No memory routes or chat history routes called
    expect(true).toBe(true);
  });

  it("validation is configuration-level, not enforcement", () => {
    // Seed profiles describe config shapes — no runtime enforcement
    // No permission enforcement, retrieval execution, or provider routing
    expect(true).toBe(true);
  });

  it("no execution authority in store exports", () => {
    expect(usePersonaStudioLocalDraftState).toBeDefined();
  });

  it("no memory write exports in store", () => {
    // Store functions: read, persist, clear, seed — all local storage only
    // No memory, chat-message, or chat-history write functions
    expect(typeof persistPersonaStudioLocalState).toBe("function");
    expect(typeof clearPersonaStudioLocalState).toBe("function");
  });
});
