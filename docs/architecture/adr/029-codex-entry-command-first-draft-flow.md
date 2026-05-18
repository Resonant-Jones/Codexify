# Codex Entry — Command-First Draft Flow

**Status**: accepted  
**Date**: 2026-05-18  
**Deciders**: resonant-jones

## Context

Users need a lightweight way to capture conversation highlights as structured Markdown artifacts without breaking their chat flow. The artifact type already exists (`CodexEntry` / `.cdx` files), but creation required external tooling. This ADR defines a chat-native `/codex_entry` slash command that generates a transient draft card from the immediately preceding thread context, without persisting anything until the user explicitly saves.

## Decision

1. **`/codex_entry` is the trigger**, not a standalone button. No persistent global or page-level "Codex Entry" trigger button exists.

2. **Draft body comes from prior thread context**, not from the command text itself. The `/codex_entry` message is recorded as `trigger_message_id` lineage; the prior message range is recorded as `source_message_ids`.

3. **Draft is transient** — rendered as a `CodexDraftCard` in the chat conversation lane with three actions:
   - **Save to Codex** — persists through `POST /api/codex/entries` with `createdFrom: slash_command` and `retrievalEnabled: false`
   - **Download** — client-side Markdown export, no persistence
   - **Dismiss** — clears the draft locally, no persistence

4. **Save pipeline reuses the existing codex save seam** (`guardian/codex/service.py` → `save_codex_entry`). No new storage schema.

5. **Retrieval is disabled by default** — enforced in the context broker through `retrieval_enabled: false` filtering. Codex entries are excluded from RAG results unless explicitly opted in.

6. **Lineage preserves distinct trigger/source separation**:
   - `trigger_message_id` — the message that invoked `/codex_entry`
   - `source_message_id` (or `source_message_ids` range) — the prior messages whose content fed the draft
   - `thread_id` is required; `project_id` and `persona_id` are nullable

Slash aliases are exact command aliases only. They do not imply semantic detection, display-label aliasing, or automatic Codex Entry creation.

## Consequences

- **Positive**: Chat-native, no new UI chrome, reuses existing codex infrastructure
- **Positive**: Retrieval exclusion by default prevents codex entries from polluting RAG context without explicit opt-in
- **Negative**: Draft generation is a separate API call after the `/codex_entry` message is sent (not a pure completion-side effect), adding one round-trip
- **Neutral**: Semantic detection of "save-worthy" content is out of scope; the user must explicitly invoke the command

## Implementation

| Layer | Component | File |
|-------|-----------|------|
| Route | `POST /api/codex/entries` (save) | `guardian/routes/codex.py` |
| Route | `POST /api/codex/entries/draft` (generate) | `guardian/routes/codex.py` |
| Model | `CodexEntry` with trigger/source/retrieval fields | `guardian/codex/models.py` |
| Service | `save_codex_entry()` | `guardian/codex/service.py` |
| Broker | `_filter_codex_entries()` retrieval exclusion | `guardian/context/broker.py` |
| Slash | `/codex_entry` (aliases: `/codex`, `/entry`, `/artifact`) | `frontend/src/contracts/slashCommands.ts` |
| Card | `CodexDraftCard` (Save/Download/Dismiss) | `frontend/src/features/chat/components/CodexDraftCard.tsx` |
| API | `generateCodexDraft()`, `saveCodexEntry()`, `downloadCodexDraftAsMarkdown()` | `frontend/src/api/codex.ts` |
| Chat | Draft state + handlers in GuardianChat | `frontend/src/features/chat/GuardianChat.tsx` |
| Chat | Card rendering in ChatView | `frontend/src/features/chat/ChatView.tsx` |
| Composer | Generalized slash intent parsing | `frontend/src/features/chat/components/Composer.tsx` |

## Related

- Codex entry lineage contract: `guardian/codex/lineage.py`
- Account export / restore contract: `docs/architecture/account-export-restore-contract.md`
- Codexify API server: `guardian/server/codexify_api.py`
