# Inline Citation Badges for Guardian Chat

## Summary

Add citation badges to the Guardian Chat Interface that show which RAG sources influenced a completion response. When a completion uses Retrieval-Augmented Generation to answer from stored documents or database content, users should see small clickable citation markers showing the source documents.

---

## Context

When a completion uses RAG (Retrieval-Augmented Generation) to answer questions from stored documents or database content, users want to know which sources influenced the response. Currently, RAG trace data exists (documents with `id`, `title`, `score`, `snippet`) but is only surfaced in a debug panel (`RAGTracePanel.tsx`) that requires a dev flag to enable.

The goal: show citation badges inline below assistant messages when RAG sources were used, making the response's provenance transparent without requiring special flags.

---

## Existing Infrastructure (Reuse These)

| What | Where |
|------|-------|
| `RagDocument` type | `frontend/src/types/rag.ts:8-13` |
| `fetchLatestRagTrace()` API | `frontend/src/lib/api.ts:1012` |
| Document rendering in RAGTracePanel | `frontend/src/features/chat/panels/RAGTracePanel.tsx:212-244` (DocumentCard) |
| ChatBubble assistant rendering | `frontend/src/features/chat/components/ChatBubble.tsx:625-700` |
| `requestWorkspaceOpen()` for click-to-open | `frontend/src/features/workspace/state/useWorkspaceState` |

**No backend changes required.** The `rag_trace` already contains `documents: [{id, title, score, snippet}]` and is accessible via the existing debug endpoint.

---

## Implementation

### Phase 1: CitationBadge Component

**File:** `frontend/src/features/chat/components/CitationBadge.tsx` (new)

A small superscript-style badge that:
- Displays `[N]` where N is the 1-based citation index
- Shows a tooltip on hover with document title and score
- Clicking opens the document in workspace via `requestWorkspaceOpen()`

Design matches the existing execution badge styling in `ChatBubble.tsx:659-671`:
```typescript
// Styling reference from execution badge
borderColor: "color-mix(in srgb, var(--panel-border) 70%, transparent)",
color: "var(--muted)",
background: "color-mix(in srgb, var(--panel-sheet, var(--panel-bg)) 90%, transparent)"
```

### Phase 2: useCitations Hook

**File:** `frontend/src/features/chat/hooks/useCitations.ts` (new)

```typescript
export function useCitations(threadId: number | null, isCompleting: boolean):
  { documents: RagDocument[]; loading: boolean }
```

- Calls `fetchLatestRagTrace(threadId)` after `isCompleting` transitions false
- Returns cached `documents: RagDocument[]`
- Handles 404 gracefully (no trace yet = no citations)

### Phase 3: ChatBubble Modification

**File:** `frontend/src/features/chat/components/ChatBubble.tsx`

Add `citations?: RagDocument[]` prop. When `isGuardian` and `citations` is non-empty:
- Render compact citation badges below the message content (after execution badge area, lines 657-698)
- Reuse `CitationBadge` component with index mapping

### Phase 4: ChatView Wiring

**File:** `frontend/src/features/chat/ChatView.tsx`

- Import and use `useCitations` hook
- After completion (`completionState.isCompleting` → false), pass `citations` prop to the latest assistant `ChatBubble`
- Citations only apply to the most recent assistant message

---

## Files to Create

1. **`frontend/src/features/chat/components/CitationBadge.tsx`** — New component
2. **`frontend/src/features/chat/hooks/useCitations.ts`** — New hook

## Files to Modify

1. **`frontend/src/features/chat/components/ChatBubble.tsx`** — Add `citations` prop and render badges
2. **`frontend/src/features/chat/ChatView.tsx`** — Wire up `useCitations` hook

---

## Verification

1. **Backend test** (existing - no changes): `pytest -v tests/integration/test_chat_completion_context.py -k "rag_trace"`
2. **Frontend test** (manual): Start a chat, upload a document, ask a question about it, verify citation badges appear below the assistant response
3. **Click test**: Click a citation badge, verify the document opens in workspace
4. **Streaming test**: Start a completion, verify badges appear after streaming completes (not during)
5. **No-RAG test**: Ask a general question that doesn't use RAG, verify no citation badges appear

---

## Summary Table

| File | Action |
|------|--------|
| `frontend/src/features/chat/components/CitationBadge.tsx` | **Create** |
| `frontend/src/features/chat/hooks/useCitations.ts` | **Create** |
| `frontend/src/features/chat/components/ChatBubble.tsx` | **Modify** - add `citations` prop |
| `frontend/src/features/chat/ChatView.tsx` | **Modify** - wire `useCitations` |
