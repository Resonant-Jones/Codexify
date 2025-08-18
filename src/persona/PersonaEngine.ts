/**
 * Detect if we are running inside a Tauri desktop runtime.
 */
function isTauri(): boolean {
  // @ts-ignore – injected by Tauri
  return typeof (window as any).__TAURI_IPC__ !== "undefined";
}

/**
 * Represents a memory fragment returned from the memory fabric.
 */
export interface MemoryFragment {
  id: string;
  persona_id: string;
  timestamp: number;
  tags: string[];
  content: string;
  embedding?: number[];
}

/**
 * Result returned from generateWithMemory.
 */
export interface GenerationResult {
  completion: string;
  persona_used: string;
  memory_fragments: MemoryFragment[];
}

/**
 * Tag statistics returned by getAllTags.
 */
export interface TagStats {
  tag: string;
  count: number;
}

/**
 * PersonaEngine – bridge to the backend memory system and model interface.
 */
export const PersonaEngine = {
  /**
   * Generate a memory-aware response using the active persona and memory tags.
   */
  async generateWithMemory(
    input_prompt: string,
    persona_id: string,
    memory_tags: string[]
  ): Promise<GenerationResult> {
    if (isTauri()) {
      const { invoke } = await new Function('return import("@tauri-apps/api/tauri")')();
      return await invoke<GenerationResult>("generate_with_memory", {
        inputPrompt: input_prompt,
        personaId: persona_id,
        memoryTags: memory_tags,
      });
    }
    return {
      completion: "Mock response for web preview.",
      persona_used: persona_id,
      memory_fragments: [],
    };
  },

  /**
   * Retrieve all tags for the given persona, along with their usage counts.
   */
  async getAllTags(persona_id: string): Promise<TagStats[]> {
    if (isTauri()) {
      const { invoke } = await new Function('return import("@tauri-apps/api/tauri")')();
      return await invoke<TagStats[]>("get_all_tags", {
        personaId: persona_id,
      });
    }
    return [
      { tag: "example", count: 1 },
      { tag: "mock", count: 2 },
    ];
  },
};