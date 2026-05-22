# Codex Entry Policy Hardening

> Classification: architecture note
> Status: normative
> Last updated: 2026-05-21

Records the implementation and hardening chain for Codex Entry policy, from
save/draft endpoints through retrieval exclusion, command-first draft flow,
advisory semantic suggestions, and the follow-up hardening fix.

## Policy Arc

The Codex Entry policy now consists of six linked layers:

### 1. Save and Draft Endpoints

`POST /api/codex/entries` persists a Codex Entry artifact with frontmatter
lineage fields. `POST /api/codex/entries/draft` generates a transient draft
from thread context without persisting. Both live in `guardian/routes/codex.py`
and delegate save semantics to `guardian/codex/service.py`.

### 2. Command-First Draft Flow (ADR-029)

The `/codex_entry` slash command triggers draft generation from prior thread
context. The draft card renders inline in the chat conversation lane with
Save/Download/Dismiss actions. Save reuses the existing `POST /api/codex/entries`
seam. Lineage is explicit: `trigger_message_id` records the command invocation;
`source_message_ids` records the prior messages that fed the draft.

ADR: `docs/architecture/adr/029-codex-entry-command-first-draft-flow.md`

### 3. Retrieval Filtering and Default Exclusion

Codex entries are excluded from context assembly unless explicitly opted in.
`ContextBroker._filter_codex_entries` drops items with `source_type == "codex_entry"`
or `type == "codex_entry"` from all retrieval lanes (`semantic`, `obsidian`,
`docs`, `memory`) unless `retrieval_enabled` is exactly `true`. The default for
all newly saved entries is `retrieval_enabled: false`.

### 4. Command-Flow Proof

Focused tests in `tests/routes/test_codex_draft_routes.py` lock in:
draft-from-prior-context derivation, no-persist-on-draft guarantee,
empty-source and no-context edge cases, semantic-suggestion source lineage
acceptance, and save-persists-created-from/retrieval-enabled behaviors.
Retrieval exclusion tests in `tests/context/test_codex_entries_retrieval_policy.py`
verify the `_filter_codex_entries` and `_filter_codex_from_doc_buckets` methods.

### 5. Advisory Semantic Suggestion Flow (ADR-030)

A deterministic classifier (`guardian/codex/semantic_suggestions.py`) recognizes
explicit capture-language phrases and returns a transient suggestion contract
via `POST /api/codex/entries/suggest`. The suggestion renders a `CodexSuggestionCard`
in the chat lane with Draft/Dismiss actions. Drafting transitions to the existing
draft→save seam with bounded source message IDs. Saved entries carry
`created_from: semantic_suggestion` and `retrieval_enabled: false`. Repeated
suggestions within an active session are suppressed via stable `suppressionKey`.

ADR: `docs/architecture/adr/030-codex-entry-semantic-suggestion-flow.md`

### 6. Follow-Up Hardening Fix

`_message_id` in `semantic_suggestions.py` used `or` which treated message id `0`
as falsy, silently dropping valid source messages. Fixed to use explicit `is None`
check. This was an edge-case bug fix only — it did not widen product behavior,
introduce new semantics, or alter any policy boundary. Validated via direct
Python module tests and 8/8 frontend component tests.

Commit: `be7235fe6`

## Protocol Tokens

| Token Domain | Values |
|-------------|--------|
| `CodexEntryCreatedFrom` | `slash_command`, `semantic_suggestion` |
| `CodexEntrySuggestionReason` | `capture_language` |

Defined in `guardian/protocol_tokens.py`. Frozenset exports and contract tests
in `tests/contracts/test_protocol_tokens.py`.

## Cross-References

- ADR-029: `docs/architecture/adr/029-codex-entry-command-first-draft-flow.md`
- ADR-030: `docs/architecture/adr/030-codex-entry-semantic-suggestion-flow.md`
- Export/restore contract: `docs/architecture/account-export-restore-contract.md`
- Retrieval router: `docs/architecture/router-decision-table.md`
- Protocol token contract: `docs/architecture/runtime-protocol-token-contract.md`
- Canonical token philosophy: `docs/architecture/canonical-token-philosophy.md`
- Implementation: `guardian/routes/codex.py`, `guardian/codex/service.py`, `guardian/codex/semantic_suggestions.py`, `guardian/context/broker.py`
