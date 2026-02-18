# Codexify UI Design Map

Purpose: Provide a deterministic, implementation-accurate map of all major frontend UI components so automated agents (Claude, Codex, etc.) can extract structure, behavior, and design semantics without parsing the entire src/ tree blindly.

Last updated: 2026-02-18

---

## 1. Frontend Entry Points

Source anchors:
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/persona/layout/AppShell.tsx`

### 1.1 App Root

- Bootstraps React app.
- Provides global providers (PersonaProvider, routing, API client).
- Establishes the UI shell boundary.

### 1.2 AppShell

Primary structural container.

Responsibilities:
- Layout scaffolding (panels, gutters, slabs)
- View switching (threads, documents, settings)
- Global UI chrome

Design invariants:
- All major panels must use `GlassSlab.tsx` tokens.
- 8px gutter spacing between slab edges.
- Layered glass aesthetic is canonical.

---

## 2. Core Layout Components

Source anchors:
- `frontend/src/components/persona/layout/`
- `frontend/src/components/ui/GlassSlab.tsx`

> Note: A deprecated copy exists at `frontend/src/components/deprecated/GlassSlab.tsx` — do not reference it.

### 2.1 GlassSlab

Purpose:
- Canonical card/panel container.
- Encodes visual token system (bezel, blur, layering).

Agents must:
- Copy visual tokens directly from implementation.
- Not reinterpret border, blur, or spacing rules.

### 2.2 Panel Structure

All panels follow:

```
GlassSlab
├─ Header
├─ Content
└─ Footer (optional)
```

Spacing:
- 8px minimum slab-to-slab spacing.
- No edge collision between slabs.

---

## 3. Conversation UI Stack

Source anchors:
- `frontend/src/components/persona/ThreadPromptBox.tsx`
- `frontend/src/components/chat/ChatBubble.tsx`
- `frontend/src/components/chat/Composer.tsx`

> Note: `MessageList.tsx` and `MessageItem.tsx` are not yet implemented. The chat rendering layer is currently handled by `ChatBubble.tsx` and `Composer.tsx` in `components/chat/`.

### 3.1 ThreadPromptBox

Responsibilities:
- User input capture
- Persona-aware invocation
- Completion trigger

Calls:
- `generateWithMemory`
- `/api/chat/{thread_id}/complete`

### 3.2 ChatBubble

Responsibilities:
- Render ordered chat messages.
- Preserve role distinctions (user/assistant/system).

### 3.3 Composer

Responsibilities:
- Role-based styling
- Content rendering (markdown, attachments)

---

## 4. Persona System UI

Source anchors:
- `frontend/src/components/persona/PersonaProvider.tsx`
- `frontend/src/components/persona/TagSelector.tsx`

> Note: `PersonaPanel.tsx` and `MemoryFragments.tsx` are not yet implemented.

### 4.1 PersonaProvider

Global state container:
- Active persona
- Memory tags
- Debug mode

Single source of truth.

### 4.2 TagSelector

UI control for:
- Persona selection
- Persona preview (tone/avatar)

### 4.3 MemoryFragments (Debug Surface) — _not yet implemented_

Planned: Visible only in debug mode. Displays injected memory fragments.

---

## 5. Document Workspace UI

Source anchors:
- `frontend/src/components/documents/DocumentsView.tsx`
- `frontend/src/components/documents/DocumentTile.tsx`
- `guardian/routes/documents.py` (behavior reference)

Responsibilities:
- Autosave document rendering
- LLM-generated document display
- Thread linkage visualization

Relation types:
- autosave
- attached
- reference

---

## 6. Global Design Constraints

Derived from:
- UI Rendering Protocol
- Structural Layout Specification
- System Overview

Invariants:

- All major UI panels use GlassSlab (`components/ui/GlassSlab.tsx`).
- Gutter spacing is consistent (8px edge-to-edge).
- No implicit layout nesting without explicit slab boundary.
- Persona context is global, not component-local.
- Chat completion is async; UI must respect task state.

---

## 7. What This Document Is For

This file is the canonical extraction entrypoint.

Agents should:
- Read this file first.
- Traverse only referenced anchors.
- Generate structured UI documentation.
- Never attempt to infer layout from raw src without this map.

---

End of Document
