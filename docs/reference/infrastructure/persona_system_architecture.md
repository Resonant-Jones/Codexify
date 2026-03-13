# Memory‑Aware Persona System Architecture

This document provides a visual overview of the **Memory‑Aware Persona System** used in Codexify. The diagrams are written in **Mermaid** syntax, which is supported by GitHub, VS Code, and many Markdown viewers.

---

## 1. Rust‑Side Data Flow Diagram

```mermaid
flowchart TD
    %% Front‑end entry point (Tauri invoke)
    subgraph Frontend
        FE[TS Frontend<br/>invoke('generate_with_memory')]
    end

    %% Backend modules
    subgraph RustBackend ["Rust Backend (Tauri)"]
        direction LR
        PE[persona_engine.rs] -->|load_persona| P[Persona struct]
        PE -->|load_memory| MF[memory_fabric.rs]
        MF -->|get_fragments_by_tags| MFStruct[MemoryFragment]
        MFStruct -->|assemble| Prompt[Prompt Assembly]
        Prompt -->|route| LM[local_model.rs]
        Prompt -->|route| RM[remote_model.rs]
        LM -->|generate| GR[GenerationResult]
        RM -->|generate| GR
        PE -->|return| GR
    end

    %% Data flow
    FE -->|invoke| PE
    PE --> MF
    MF -->|returns| MFStruct
    MFStruct -->|used in| Prompt
    Prompt -->|calls| LM
    Prompt -->|calls| RM
    LM -->|result| GR
    RM -->|result| GR
    GR -->|return to| FE

    classDef rust fill:#f9f9f9,stroke:#333,stroke-width:1px;
    class PE,MF,LM,RM,GR fill:#e8f5e9;
    class FE fill:#e0f7fa;
```

**Explanation**  
1. **Frontend** calls the Tauri command `generate_with_memory`.  
2. `persona_engine.rs` loads the selected **Persona** definition.  
3. `memory_fabric.rs` retrieves **MemoryFragment** objects matching the requested tags.  
4. The **Prompt Assembly** concatenates the persona’s system prompt, the memory block, and the user’s input.  
5. The assembled prompt is routed to either **local_model.rs** (on‑device) or **remote_model.rs** (cloud) based on configuration.  
6. The model returns a **GenerationResult** containing the completion, the persona used, and the injected memory fragments, which is sent back to the frontend.

---

## 2. React/TS Component Hierarchy

```mermaid
graph TD
    subgraph Frontend
        PP[PersonaProvider.tsx]:::provider
        PP -->|provides| PC[PersonaContext]
        PC -->|consumes| PPnl[PersonaPanel.tsx]
        PC -->|consumes| TPB[ThreadPromptBox.tsx]
        PC -->|consumes| MFc[MemoryFragments.tsx]
        PC -->|consumes| TS[TagSelector.tsx]

        %% Component interactions
        TPB -->|invoke generateWithMemory| FE[PersonaEngine.ts]
        TS -->|invoke getAllTags| FE
        MFc -->|display fragments| PC
        TS -->|update tags| PC
        PPnl -->|select persona| PC
    end

    classDef provider fill:#e0f7fa,stroke:#333,stroke-width:2px;
    class PP fill:#e0f7fa;
    class PC fill:#fff3e0;
    class PPnl,TPB,MFc,TS fill:#f9f9f9;
```

**Explanation**  
- **`PersonaProvider`** creates a React context (`PersonaContext`) that holds the active persona, selected memory tags, recent tags, and debug mode.  
- **`PersonaPanel`** lets the user select a persona and shows a preview (tone, avatar).  
- **`ThreadPromptBox`** is the chat input; it calls `generateWithMemory` (via `PersonaEngine.ts`) to get a model response.  
- **`TagSelector`** fetches all tags (`getAllTags`) and lets the user add or remove tags, updating the context.  
- **`MemoryFragments`** reads the current memory fragments from the context and displays them (debug mode only).  
All components read/write the shared `PersonaContext`, ensuring a single source of truth for persona and memory state.

---

## 3. Cross‑Language Tauri Interface Diagram

```mermaid
flowchart LR
    %% Frontend
    subgraph TS_Frontend [TypeScript Frontend]
        direction LR
        TS1[TagSelector.tsx] -->|invoke('list_tags')| TS2[PersonaEngine.ts]
        TS3[ThreadPromptBox.tsx] -->|invoke('generate_with_memory')| TS2
    end

    %% Tauri Bridge
    subgraph Tauri_Bridge [Tauri Bridge (Rust)]
        direction LR
        RC1[commands.rs] -->|register| RC2[generate_with_memory]
        RC2 -->|calls| RE[persona_engine.rs]
        RE -->|calls| MF[memory_fabric.rs]
        RE -->|calls| LM[local_model.rs]
        RE -->|calls| RM[remote_model.rs]
        RE -->|returns| GR[GenerationResult]
        RC2 <--|returns| TS3
        RC1 <--|list_tags| TS1
    end

    %% Data flow
    TS1 -->|invoke| RC1
    TS3 -->|invoke| RC1

    classDef ts fill:#e0f7fa,stroke:#333;
    class TS1,TS3,TS2 fill:#e0f7fa;
    class RC1,RC2,RE,MF,LM,RM,GR fill:#e8f5e9;
```

**Explanation**  
- The **TypeScript** frontend uses `window.__TAURI__.invoke` to call Rust‑side Tauri commands.  
- `commands.rs` registers the `generate_with_memory` command (and others like `list_tags`).  
- The command invokes `persona_engine.rs`, which orchestrates memory retrieval (`memory_fabric.rs`) and model routing (`local_model.rs` or `remote_model.rs`).  
- The final `GenerationResult` is returned through the Tauri bridge back to the TypeScript frontend, where it is displayed in the UI.

---

## 📚 Rendering Mermaid Diagrams

- **GitHub**: Mermaid diagrams are rendered automatically in Markdown files on GitHub and GitHub Pages.  
- **VS Code**: Install the **“Markdown Preview Mermaid Support”** extension (or use the built‑in preview in recent VS Code versions). Open the `.md` file and press `Ctrl+Shift+V` to preview.  
- **Other Tools**: Use the online Mermaid Live Editor (https://mermaid.live) to edit or preview diagrams.  
- **Static Site Generators**: If you use a static site generator (e.g., Docusaurus, MkDocs), ensure the Mermaid plugin/extension is enabled.

---

✅ **Diagrams committed to `docs/reference/infrastructure/persona_system_architecture.md`**
