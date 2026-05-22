# Codex Entry Policy Hardening

Purpose: Record the implementation and post-implementation hardening proof for
the Codex Entry command-first and advisory semantic suggestion flows.

Last updated: 2026-05-21

## Scope

This document records the Codex Entry policy arc and edge-case hardening only.
It does not assert new architectural decisions, widen product behavior, or
introduce changes to identity, memory, persona, or retrieval-setting behavior.
All policy rules recorded here are implementations of ADR-029 and ADR-030.
It is not a new ADR and does not change accepted architecture.

## Related ADRs and Contracts

- ADR-029: Codex Entry Command-First Draft Flow
- ADR-030: Codex Entry Semantic Suggestion Flow
- Account Export + Restore Contract
- Retrieval Router Decision Table
- Runtime Protocol Token Contract
- Canonical Token Philosophy

## Commit Chain

Branch: `codex/codex_entry_policy`

| Commit | Layer |
|--------|-------|
| `a7b9d9bbd` | Add Codex entry save and draft endpoints |
| `9eb04ee19` | Add Codex Entry draft flow and retrieval filtering |
| `8519c646b` | Seal Codex Entry command-flow proof |
| `312c3111d` | Add advisory Codex Entry semantic suggestions |
| `be7235fe6` | Fix `_message_id` falsy-0 bug in semantic suggestions classifier |

`be7235fe6` is a narrow hardening commit on top of ADR-030. It fixes an
edge-case bug in the deterministic classifier's `_message_id` helper where
message id `0` was treated as falsy and silently dropped from source ranges.
The fix is a single `is None` check replacement with no behavioral widening.

## Implemented Behavior

1. **Command-first draft flow**: `/codex_entry` triggers draft generation from
   prior thread context; draft card renders with Save/Download/Dismiss;
   `trigger_message_id` records the command; `source_message_ids` records
   the prior messages that fed the draft.

2. **Retrieval exclusion**: `ContextBroker._filter_codex_entries` drops
   codex_entry items from all retrieval lanes (`semantic`, `obsidian`,
   `docs`, `memory`) unless `retrieval_enabled` is exactly `true`.
   Default is `retrieval_enabled: false`.

3. **Advisory semantic suggestions**: `POST /api/codex/entries/suggest`
   returns a transient suggestion contract from a deterministic capture-language
   classifier. Suggestions render a `CodexSuggestionCard` in the chat lane
   with Draft/Dismiss actions. No auto-save. User-confirmed save reuses the
   existing draft→save seam with `created_from: semantic_suggestion`.
   Repeated suggestions are suppressed via stable `suppressionKey`.

4. **Save lineage**: All saved entries carry `created_from` (`slash_command`
   or `semantic_suggestion`), `retrieval_enabled`, and optional lineage fields
   (`project_id`, `persona_id`, `source_thread_id`, `source_message_id`,
   `trigger_message_id`) persisted to frontmatter.

5. **Protocol tokens**: `CodexEntryCreatedFrom` and `CodexEntrySuggestionReason`
   are canonical tokens in `guardian/protocol_tokens.py` with frozenset exports
   and contract tests.

## Hardening Fix: `_message_id` id=0

Commit: `be7235fe6`

**Bug**: `_message_id` in `guardian/codex/semantic_suggestions.py` used `or`
which treated message id `0` as falsy, cascading to the `message_id` fallback
(usually `None`) and silently dropping valid source messages from the
suggestion range.

```python
# Before (broken): `or` treats 0 as falsy
value = message.get("id") or message.get("message_id")

# After (fixed): explicit None check preserves id=0
value = message.get("id")
if value is None:
    value = message.get("message_id")
```

**Validation**: Direct Python module tests confirmed capture-language matching,
suppression key stability, chronological source ordering, id=0 handling, and
non-dict filtering. 8/8 frontend component tests passed (`CodexSuggestionCard`,
`CodexDraftCard`).

**Scope**: Edge-case correctness fix only. No product behavior, semantics, or
policy boundary was widened.

## Invariants

Non-negotiable rules that must remain true for any Codex Entry change:

1. Command-first behavior remains distinct from semantic suggestion behavior.
2. `/codex_entry` is trigger lineage, not source body.
3. Semantic suggestions are advisory-only.
4. User confirmation is required before persistence.
5. Saved entries preserve lineage.
6. Saved entries default to `retrievalEnabled: false`.
7. Retrieval exclusion is policy/broker enforced, not UI-only.
8. The `_message_id` id=0 fix is an edge-case correctness fix, not a feature expansion.
9. No identity, memory, persona, or retrieval-setting behavior was widened.
10. No new ADR is required for the hardening note.
