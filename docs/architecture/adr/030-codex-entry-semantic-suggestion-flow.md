# Codex Entry — Advisory Semantic Suggestion Flow

**Status**: accepted
**Date**: 2026-05-21
**Deciders**: resonant-jones

## Context

ADR-029 accepted the command-first `/codex_entry` draft flow and explicitly scoped semantic detection out of that slice. Codexify now needs a narrow follow-up path where the chat surface may recognize high-confidence capture moments and offer a transient Codex Entry suggestion without changing the command-first contract.

This ADR defines advisory semantic suggestions as a separate flow from slash commands. It preserves local-first beta posture, existing Codex save infrastructure, default retrieval exclusion, and explicit user confirmation before any artifact is persisted.

## Decision

1. **Semantic detection is advisory-only.** The detector may return a transient suggestion candidate, but it must not persist Codex Entries, write memory, mutate identity/persona state, or change retrieval settings.

2. **User confirmation is required before save.** A suggestion can render a chat-local `CodexSuggestionCard`; the user must choose `Draft Codex Entry`, then explicitly use the existing draft-card `Save to Codex` action before persistence.

3. **Saved semantic-suggestion entries reuse the existing Codex save seam.** Persistence continues through `POST /api/codex/entries` and `guardian/codex/service.py`; no second storage schema or save pipeline is introduced.

4. **Lineage remains explicit.** Semantic suggestions carry a bounded source message range, thread id, nullable project id, nullable persona id, and optional suggestion metadata. Saved entries use `createdFrom: semantic_suggestion` and `retrievalEnabled: false`.

5. **Retrieval stays disabled by default.** Saved semantic-suggestion Codex Entries remain excluded from context assembly unless explicitly opted in through the existing `retrieval_enabled: true` path.

6. **Repeated suggestions are suppressed within a bounded active-thread window.** The backend returns a stable `suppressionKey` for the source range, and the frontend tracks shown, drafted, or dismissed keys for the active session.

7. **No global or persistent trigger UI is introduced.** Suggestion and draft controls render only in the chat conversation lane and act only on an already-detected candidate.

8. **Semantic suggestions do not imply alias settings or display-label aliasing.** Slash aliases remain exact command aliases under ADR-029.

9. **Semantic suggestions do not create durable identity or memory traits.** Any future identity/memory promotion requires a separate consent and governance contract.

## Consequences

- **Positive**: Captures reusable conversation patterns without making Codex Entry creation fully manual.
- **Positive**: Keeps artifact creation user-confirmed and lineage-preserving.
- **Positive**: Reuses existing draft card, download, save route, and retrieval-exclusion policy.
- **Negative**: The MVP deterministic classifier may miss softer capture opportunities.
- **Neutral**: Semantic suggestion metadata is advisory lineage context, not a new durable memory layer.

## Implementation

| Layer | Component | File |
|-------|-----------|------|
| Helper | deterministic advisory classifier | `guardian/codex/semantic_suggestions.py` |
| Route | `POST /api/codex/entries/suggest` | `guardian/routes/codex.py` |
| Route | draft route accepts bounded semantic source lineage | `guardian/routes/codex.py` |
| Save | existing Codex save seam | `guardian/codex/service.py` |
| Tokens | `semantic_suggestion`, `capture_language` | `guardian/protocol_tokens.py` |
| API | suggestion and semantic draft helpers | `frontend/src/api/codex.ts` |
| Chat | suggestion state and suppression | `frontend/src/features/chat/GuardianChat.tsx` |
| Chat | conversation-lane rendering | `frontend/src/features/chat/ChatView.tsx` |
| Card | advisory suggestion controls | `frontend/src/features/chat/components/CodexSuggestionCard.tsx` |
| Card | existing draft preview/save/download/dismiss | `frontend/src/features/chat/components/CodexDraftCard.tsx` |

## Related

- ADR-029: `docs/architecture/adr/029-codex-entry-command-first-draft-flow.md`
- Account export / restore contract: `docs/architecture/account-export-restore-contract.md`
- Retrieval router decision table: `docs/architecture/router-decision-table.md`
- Runtime protocol token contract: `docs/architecture/runtime-protocol-token-contract.md`
- Canonical token philosophy: `docs/architecture/canonical-token-philosophy.md`
