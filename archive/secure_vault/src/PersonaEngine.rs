export interface MemoryFragment {
    id: string;
    persona_id: string;
    timestamp: number;
    tags: string[];
    content: string;
    embedding?: number[];
  }
  
  export async function generateWithMemory(
    input_prompt: string,
    persona_id: string,
    memory_tags: string[]
  ): Promise<{
    completion: string;
    persona_used: string;
    memory_fragments: MemoryFragment[];
  }> {
    return await window.__TAURI__.invoke('generate_with_memory', {
      input_prompt,
      persona_id,
      memory_tags,
    });
  }