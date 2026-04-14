# Codexify Workspace Profile Schema Spec

**Status:** Draft
**Purpose:** Define the minimum viable schema for Workspace Profiles in Codexify, supporting hot-swappable knowledge bases, per-workspace project filtering, persona binding, and future role/preset overlays without duplicating underlying data.

---

## 1. Overview

Codexify is evolving beyond simple persona switching toward **Workspace Profiles**.

A Workspace Profile is **not** a separate container of duplicated data. It is a **policy-bound projection** over existing projects, knowledge sources, and assistant behavior.

This enables:

* **Hot-swappable knowledge bases**
* **Per-workspace project filtering**
* **Per-workspace persona defaults**
* **Future role/preset overlays**
* **Context separation without data duplication**

This design is conceptually similar to Apple Focus Modes, but applied to knowledge, retrieval, and interaction state.

---

## 2. Core Design Principles

### 2.1 Workspace is a projection, not a container

A workspace selects and shapes data visibility. It does not own separate copies of projects or knowledge.

### 2.2 Persona is attachable, not baked in

A persona may be bound to a workspace, but remains reusable across workspaces.

### 2.3 Knowledge sources are mountable

Obsidian vaults, ChatGPT imports, project docs, and future connectors are modeled as independently attachable knowledge sources.

### 2.4 Projects remain first-class

Projects exist independently and may appear in multiple workspaces through filtering.

### 2.5 Retrieval must respect workspace boundaries

Workspace filtering is not just a UI concern. The retrieval pipeline must honor workspace-scoped visibility.

---

## 3. Conceptual Model

```text
User
 ├─ has many WorkspaceProfiles
 ├─ has many Personas
 ├─ has many Projects
 └─ has many KnowledgeSources

WorkspaceProfile
 ├─ references visible Projects
 ├─ references active KnowledgeSources
 ├─ references a Persona
 ├─ may apply a RolePreset
 └─ defines retrieval and memory policy

Project
 └─ may appear in many WorkspaceProfiles

KnowledgeSource
 └─ may be active in many WorkspaceProfiles

Persona
 └─ may be reused across many WorkspaceProfiles

RolePreset
 └─ may be attached per workspace to alter behavior without mutating the base persona
```

---

## 4. Primary Use Cases

### 4.1 Work vs Personal separation

A user may maintain:

* a **Work** workspace with business projects and work-specific knowledge sources
* a **Personal** workspace with personal notes, journaling, or household projects

Both workspaces may reuse the same persona or use different personas.

### 4.2 Low-friction onboarding

A user can attach an Obsidian vault as a knowledge source and test Codexify without first importing ChatGPT history.

### 4.3 Hot-swappable knowledge bases

A user may switch from one vault or knowledge source set to another at runtime, without reconfiguring the full application identity.

### 4.4 Same persona, different role/preset

A user may keep one base persona but apply different behavioral presets in different workspaces.

---

## 5. Canonical Definitions

### 5.1 Workspace Profile

A Workspace Profile is a **policy-bound projection over projects, knowledge sources, and assistant behavior**, allowing users to switch contexts without duplicating underlying data.

### 5.2 Knowledge Source

A Knowledge Source is a mounted source of retrievable knowledge, such as an Obsidian vault, ChatGPT import, project document set, or future connector-backed corpus.

### 5.3 Role Preset

A Role Preset is an operational overlay that modifies behavior without redefining the assistant’s core persona.

---

## 6. Type System

### 6.1 KnowledgeSourceType

```ts
type KnowledgeSourceType =
  | "obsidian_vault"
  | "chatgpt_import"
  | "project_docs"
  | "manual_notes"
  | "web_archive"
  | "google_drive"
  | "notion"
  | "other";
```

### 6.2 WorkspaceKind

```ts
type WorkspaceKind =
  | "personal"
  | "work"
  | "research"
  | "client"
  | "custom";
```

### 6.3 MemoryWriteScope

```ts
type MemoryWriteScope =
  | "workspace_only"
  | "global_allowed"
  | "project_only"
  | "disabled";
```

### 6.4 RetrievalMode

```ts
type RetrievalMode =
  | "workspace_scoped"
  | "workspace_plus_global"
  | "explicit_sources_only";
```

### 6.5 RolePresetType

```ts
type RolePresetType =
  | "operator"
  | "assistant"
  | "researcher"
  | "writer"
  | "strategist"
  | "companion"
  | "custom";
```

---

## 7. Core Interfaces

### 7.1 WorkspaceProfile

```ts
interface WorkspaceProfile {
  id: string;
  userId: string;

  name: string;
  slug: string;
  kind: WorkspaceKind;

  description?: string;
  icon?: string;
  color?: string;

  defaultPersonaId?: string;
  defaultRolePresetId?: string;

  retrievalMode: RetrievalMode;
  memoryWriteScope: MemoryWriteScope;

  isDefault: boolean;
  isArchived: boolean;
  sortOrder: number;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Defines the workspace boundary and default assistant behavior for that workspace.

---

### 7.2 Persona

```ts
interface Persona {
  id: string;
  userId: string;

  name: string;
  slug: string;

  systemPrompt?: string;
  description?: string;

  isDefault: boolean;
  isArchived: boolean;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Represents a reusable assistant identity layer.

---

### 7.3 RolePreset

```ts
interface RolePreset {
  id: string;
  userId: string;

  name: string;
  type: RolePresetType;

  description?: string;

  promptOverlay?: string;
  temperatureOverride?: number | null;
  maxContextTokensOverride?: number | null;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Provides a workspace-specific operational mode without mutating the underlying persona.

---

### 7.4 Project

```ts
interface Project {
  id: string;
  userId: string;

  name: string;
  slug: string;
  description?: string;

  isArchived: boolean;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Represents a canonical project that may appear in multiple workspaces.

---

### 7.5 KnowledgeSource

```ts
interface KnowledgeSource {
  id: string;
  userId: string;

  name: string;
  slug: string;
  type: KnowledgeSourceType;

  description?: string;

  uri?: string;
  localPath?: string;
  connectorId?: string | null;

  indexStatus: "unindexed" | "indexing" | "ready" | "error";
  lastIndexedAt?: string | null;
  lastSyncAt?: string | null;

  docCount?: number | null;
  chunkCount?: number | null;
  embeddingNamespace?: string | null;

  isArchived: boolean;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Defines a mountable, independently indexable retrieval source.

---

## 8. Junction Models

### 8.1 WorkspaceProject

```ts
interface WorkspaceProject {
  workspaceId: string;
  projectId: string;

  pinned: boolean;
  sortOrder: number;

  createdAt: string;
}
```

**Intent:**
Controls which projects appear in a workspace and in what order.

---

### 8.2 WorkspaceKnowledgeSource

```ts
interface WorkspaceKnowledgeSource {
  workspaceId: string;
  knowledgeSourceId: string;

  isActive: boolean;
  priority: number;

  createdAt: string;
}
```

**Intent:**
Controls which knowledge sources are active in a workspace and their source precedence.

---

### 8.3 WorkspacePersonaOverride

```ts
interface WorkspacePersonaOverride {
  workspaceId: string;
  personaId: string;

  promptPrefix?: string;
  promptSuffix?: string;

  temperatureOverride?: number | null;
  maxContextTokensOverride?: number | null;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Allows workspace-local persona shading while preserving the canonical base persona.

---

## 9. Retrieval-Facing Models

### 9.1 IndexedDocument

```ts
interface IndexedDocument {
  id: string;
  userId: string;

  knowledgeSourceId: string;
  projectId?: string | null;

  sourcePath: string;
  title: string;

  rawHash?: string | null;
  metadataJson?: Record<string, unknown>;

  createdAt: string;
  updatedAt: string;
}
```

**Intent:**
Represents a document ingested from a knowledge source.

---

### 9.2 IndexedChunk

```ts
interface IndexedChunk {
  id: string;
  userId: string;

  documentId: string;
  knowledgeSourceId: string;
  projectId?: string | null;

  chunkIndex: number;
  content: string;

  tokenCount?: number | null;

  embeddingId?: string | null;
  embeddingNamespace?: string | null;

  metadataJson?: Record<string, unknown>;

  createdAt: string;
}
```

**Intent:**
Represents a retrieval unit tied explicitly to a knowledge source and optionally a project.

---

## 10. Runtime Resolution Contract

### 10.1 ResolvedWorkspaceContext

```ts
type ResolvedWorkspaceContext = {
  workspace: WorkspaceProfile;
  persona: Persona | null;
  rolePreset: RolePreset | null;
  visibleProjectIds: string[];
  activeKnowledgeSourceIds: string[];
  retrievalMode: RetrievalMode;
  memoryWriteScope: MemoryWriteScope;
};
```

### 10.2 Resolution Requirements

When a workspace is active, the runtime must resolve:

1. The workspace profile itself
2. The default persona
3. The role preset, if present
4. The workspace-visible projects
5. The workspace-active knowledge sources
6. The retrieval and memory policy

### 10.3 Retrieval Constraint

All retrieval operations must be scoped by the active workspace’s resolved project and knowledge source filters unless explicitly overridden.

---

## 11. Runtime Flow

```text
User Query
   ↓
Workspace Resolver
   ↓
ContextBroker
   ├─ Filter visible Projects
   ├─ Filter active KnowledgeSources
   ├─ Apply Persona binding
   ├─ Apply RolePreset overlay
   └─ Apply Retrieval + Memory policy
   ↓
Retriever
   ↓
LLM
```

---

## 12. Example Workspace Configurations

### 12.1 Work Workspace

```json
{
  "name": "Work",
  "kind": "work",
  "defaultPersonaId": "persona-axis",
  "defaultRolePresetId": "preset-operator",
  "retrievalMode": "workspace_scoped",
  "memoryWriteScope": "workspace_only"
}
```

Example active resources:

* Projects: `client-a`, `codexify-biz`, `roadmap`
* Knowledge sources: `work-obsidian`, `meeting-imports`, `docs-drive`

---

### 12.2 Personal Workspace

```json
{
  "name": "Personal",
  "kind": "personal",
  "defaultPersonaId": "persona-axis",
  "defaultRolePresetId": "preset-reflective",
  "retrievalMode": "workspace_plus_global",
  "memoryWriteScope": "workspace_only"
}
```

Example active resources:

* Projects: `journal`, `family`, `philosophy`
* Knowledge sources: `personal-vault`, `chat-history-import`

---

## 13. Non-Goals

The following are **not** goals of this spec:

* Duplicating projects per workspace
* Duplicating knowledge sources per workspace
* Binding personas permanently to only one workspace
* Treating workspace as only a visual UI layer
* Replacing existing retrieval architecture with flat markdown-only traversal

---

## 14. Explicit Anti-Patterns

### 14.1 Do not bind Project directly to one Workspace

```ts
Project { workspaceId: string }
```

This prevents reuse and forces duplication.

### 14.2 Do not bind KnowledgeSource directly to one Workspace

```ts
KnowledgeSource { workspaceId: string }
```

This breaks hot-swapping and cross-workspace reuse.

### 14.3 Do not bind Persona directly to one Workspace

```ts
Persona { workspaceId: string }
```

This causes unnecessary persona fragmentation.

---

## 15. Phased Implementation Guidance

### Phase 1 — Minimum viable support

Implement:

* `workspace_profiles`
* `knowledge_sources`
* `workspace_projects`
* `workspace_knowledge_sources`

Also ensure:

* `activeWorkspaceId` exists in runtime state
* `knowledgeSourceId` exists on indexed documents and chunks
* `projectId` may optionally exist on indexed documents and chunks

### Phase 2 — Identity and behavior overlays

Implement:

* `role_presets`
* `workspace_persona_overrides`
* more nuanced retrieval and memory rules

---

## 16. Strategic Rationale

This schema supports the user experience goal of **switching contexts without rebuilding identity or duplicating knowledge**.

It also supports Codexify’s broader conceptual trajectory:

* from persona switching
* toward workspace-bound context orchestration

This allows the same core assistant identity to operate differently across filtered domains such as:

* work
* personal life
* research
* client-specific spaces

without corrupting the underlying memory model.

---

## 17. Canonical Summary

> A Workspace Profile is a policy-bound projection over projects, knowledge sources, and assistant behavior, allowing users to switch contexts without duplicating underlying data.

---

## 18. Future Extension Surface

This spec is intentionally shaped to support future additions without rewrite, including:

* connector-backed knowledge sources
* workspace-scoped memory logs
* multi-workspace retrieval policies
* per-workspace UI layouts
* focus-mode-like notification or visibility rules
* workspace-specific thread rails
* more advanced permissioning and collaboration models

---

## 19. Storage Recommendation

Suggested filename:

`codexify_workspace_profile_schema_spec.md`

Suggested tags:

* `codexify`
* `schema`
* `workspace-profiles`
* `knowledge-sources`
* `retrieval`
* `persona`
* `architecture`
