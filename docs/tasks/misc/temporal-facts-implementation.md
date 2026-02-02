# Codex Task: Temporal Message Ordering + Correctable Personal Facts

## Summary

Implement temporal message ordering (`event_at`, chronological retrieval, temporal decay) and a correctable Personal Facts system with multi-evidence support, revision history, and user correction flows.

## Reference Plan

See: `~/.claude/plans/logical-kindling-graham.md`

## V1 Policy Decisions (Locked)

1. **Key inference:** Deterministic keys only. Format: `import.bio.<source_message_id>` or content hash. No LLM keying.
2. **Runtime extraction:** Only from explicit markers/bio channel. Auto-extraction from general chat is deferred.
3. **Conflict resolution:** Never auto-overwrite verified facts. Create new candidate for user resolution.

---

## Implementation Phases

### Phase 1: Schema Migration

**Commit message:** `feat(db): add temporal fields and personal facts tables`

**Files:**

- `guardian/db/migrations/versions/xxxx_add_temporal_and_facts.py` (NEW)
- `guardian/db/models.py`

**Tasks:**

1. Create Alembic migration that:
   - Adds `event_at TIMESTAMPTZ`, `kind VARCHAR(32)`, `extra_meta JSONB` to `chat_messages`
   - Backfills `event_at = created_at` for existing rows
   - Creates `personal_facts` table with `is_active` constraint and `last_confirmed_at`
   - Creates `personal_fact_evidence` table with `evidence_meta JSONB`
   - Creates `personal_fact_revisions` table
   - Creates all indexes

2. Update `guardian/db/models.py`:
   - Add `event_at`, `kind`, `extra_meta` to `ChatMessage` model
   - Add `PersonalFact` model (with `last_confirmed_at`)
   - Add `PersonalFactEvidence` model (with `evidence_meta`)
   - Add `PersonalFactRevision` model

**extra_meta schema:**
```json
{
  "origin": "pre_codexify_import" | "native",
  "external": {"provider": "chatgpt_export", "conversation_id": "...", "message_id": "...", "parent_id": "..."},
  "persona_id": "...",
  "source_created_at": "2024-03-30T12:00:00Z",
  "modality": "typed" | "voice_asr"
}
```

**evidence_meta schema:**
```json
{
  "origin": "pre_codexify_import" | "native",
  "external": {"provider": "chatgpt_export", "conversation_id": "...", "message_id": "..."},
  "persona_id": "...",
  "asr_confidence": 0.95,
  "transcription_note": "possible mishearing"
}
```

**Status + is_active invariant:**
| status | is_active | Retrieval |
| ------ | --------- | --------- |
| candidate | true | Included (tentative) |
| verified | true | Included (confident) |
| disputed | true | EXCLUDED (shown in review UI only) |
| archived | false | EXCLUDED |

**Tests:** `tests/test_migration_temporal_facts.py`

- Verify migration runs without error
- Verify backfill populates `event_at`
- Verify constraints work (unique active fact per key)

---

### Phase 2: Database Operations (Messages)

**Commit message:** `feat(db): update message ops for temporal ordering`

**Files:**

- `guardian/core/pgdb.py`
- `guardian/core/db.py`

**Tasks:**

1. Update `create_message()`:
   - Add `event_at`, `kind`, `extra_meta` parameters
   - Default `event_at` to `created_at` if not provided
   - Validate `kind` values

2. Update `list_messages()`:
   - Change ORDER BY to `event_at ASC, id ASC`
   - Add `exclude_kinds` filter parameter

3. Add `list_messages_by_date_range(thread_id, start_date, end_date, limit)`

**Tests:** `tests/test_temporal_ordering.py`

- Messages ordered by `event_at` not `created_at`
- Out-of-order imports sort correctly
- `exclude_kinds` filter works
- Date range query works

---

### Phase 3: Database Operations (Facts)

**Commit message:** `feat(db): add personal facts CRUD operations`

**Files:**

- `guardian/core/pgdb.py`
- `guardian/core/db.py`

**Tasks:**

1. Add fact operations:
   - `create_fact(user_id, key, value, status, confidence) -> int`
   - `get_fact(fact_id) -> dict | None`
   - `list_facts(user_id, status, active_only, limit) -> list[dict]`
   - `update_fact(fact_id, value, status, confidence, actor, reason) -> dict` (creates revision)
   - `deactivate_fact(fact_id, actor, reason)`
   - `get_fact_by_key(user_id, key, active_only) -> dict | None`

2. Add evidence operations:
   - `add_fact_evidence(fact_id, source_message_id, excerpt, modality, confidence, source_type) -> int`
   - `list_fact_evidence(fact_id) -> list[dict]`
   - `get_evidence_by_message(source_message_id) -> list[dict]`

3. Add revision operations:
   - `create_revision(fact_id, actor, action, field_changed, old_value, new_value, reason) -> int`
   - `get_fact_revisions(fact_id) -> list[dict]`

**Tests:** `tests/test_personal_facts_crud.py`

- Create fact creates revision
- Update fact stores old value in revision
- Deactivate sets `is_active=false`
- Only one active fact per key enforced
- Evidence links to fact and source message

---

### Phase 4: API Routes

**Commit message:** `feat(api): add personal facts endpoints`

**Files:**

- `guardian/routes/personal_facts.py` (NEW)
- `guardian/routes/chat.py`
- `guardian/main.py` (register router)

**Tasks:**

1. Create `personal_facts.py` with endpoints:
   - `GET /personal-facts` (list with filters)
   - `POST /personal-facts` (create)
   - `GET /personal-facts/{id}` (get with evidence)
   - `PATCH /personal-facts/{id}` (update)
   - `POST /personal-facts/{id}/confirm`
   - `POST /personal-facts/{id}/dispute`
   - `GET /personal-facts/{id}/evidence`
   - `POST /personal-facts/{id}/evidence`
   - `GET /personal-facts/{id}/revisions`

2. Update `chat.py`:
   - Add `include_fact_evidence: bool = False` query param to message listing
   - Exclude `kind='fact_evidence'` by default

**Tests:** `tests/routes/test_personal_facts_routes.py`

- All endpoints return correct status codes
- PATCH creates revision
- Confirm sets status='verified'
- Dispute sets status='disputed'

---

### Phase 5: Context Broker Integration

**Commit message:** `feat(context): add temporal weighting and facts source`

**Files:**

- `guardian/context/broker.py`

**Tasks:**

1. Add `_fetch_personal_facts(user_id, include_candidates=True) -> dict`:
   - Returns `{"verified": [...], "tentative": [...]}`
   - Excludes disputed/inactive

2. Add temporal weighting helper using `compute_time_decay` from memoryos:
   - Chat: 168-hour (7-day) half-life
   - Facts: 2160-hour (90-day) half-life

3. Update `assemble()`:
   - Add `personal_facts` to returned bundle
   - Apply temporal weighting to semantic search results

4. Add facts formatting for system prompt injection

**Tests:** `tests/test_context_broker_facts.py`

- Verified facts in bundle
- Candidate facts labeled tentative
- Disputed facts excluded
- Temporal decay applied correctly

---

### Phase 6: ChatGPT Import Enhancement

**Commit message:** `feat(import): map event_at and extract facts from bio`

**Files:**

- `backend/rag/chatgpt_migration.py`

**Tasks:**

1. Map `create_time` from export to `event_at`
2. Detect `recipient="bio"` messages:
   - Store with `kind='fact_evidence'`
   - Create `personal_fact` with status='candidate'
   - Create `personal_fact_evidence` linking to message
   - Create initial revision

**Tests:** `tests/test_chatgpt_import_facts.py`

- `event_at` mapped from `create_time`
- `recipient="bio"` creates candidate fact
- Evidence links to source message
- Revision created with actor='import'

---

### Phase 7: Chat Worker Updates

**Commit message:** `feat(worker): inject facts with hedging behavior`

**Files:**

- `guardian/workers/chat_worker.py`

**Tasks:**

1. Retrieve facts via context broker
2. Format facts for system prompt:
   - Verified facts stated confidently
   - Candidate facts with hedging instruction
3. Ensure disputed/inactive facts never injected

**Tests:** `tests/test_chat_worker_facts.py`

- Facts appear in context
- Hedging instruction present for candidates

---

### Phase 8: Maintenance Script

**Commit message:** `chore(scripts): add fact sanity checks to pg_verify`

**Files:**

- `scripts/maintenance/pg_verify.sh`

**Tasks:**

Add checks:

- Count messages by `kind`
- Count facts by `status`
- Count facts missing evidence
- Count orphaned evidence
- Sample last N messages ordered by `event_at, id`

---

### Phase 9: Frontend (Stub)

**Commit message:** `feat(ui): add facts panel stub`

**Files:**

- `frontend/src/features/facts/FactsPanel.tsx` (NEW)
- `frontend/src/features/facts/FactCard.tsx` (NEW)
- `frontend/src/features/facts/index.ts` (NEW)

**Tasks:**

1. Create stub components with basic structure
2. Fetch facts from API
3. Display with status badges
4. Add confirm/dispute buttons (wired to API)

**Note:** Full UI polish can be follow-up work.

---

## Acceptance Checklist

### Data Integrity

- [ ] `event_at` populated for all chat_messages
- [ ] `kind` defaults to 'chat' for existing messages
- [ ] Facts have evidence with provenance
- [ ] Revision history preserved for all changes

### Retrieval Behavior

- [ ] Chat transcript excludes `kind='fact_evidence'` by default
- [ ] Context broker injects facts as separate source
- [ ] Verified facts stated confidently
- [ ] Candidate facts labeled tentative
- [ ] Disputed/inactive facts excluded
- [ ] Temporal decay: facts 90-day, chat 7-day half-life

### User Correction

- [ ] Edit fact value creates revision
- [ ] Confirm sets status='verified', confidence=1.0
- [ ] Dispute sets status='disputed'
- [ ] No destructive overwrites

### Assistant Behavior

- [ ] Hedging language for candidate facts
- [ ] Corrections reflected immediately
- [ ] Facts don't pollute thread-specific contexts

---

## Open Questions (Decide During Implementation)

1. **Key inference for imported facts:** Use generic keys like `imported_fact_N` initially; defer LLM extraction to follow-up
2. **Runtime extraction:** Only from explicit markers initially; auto-extraction is follow-up
3. **Conflict resolution:** Log conflict, don't create duplicate; let user resolve

---

## Running Tests

```bash
# Run all new tests
pytest tests/test_temporal_ordering.py tests/test_personal_facts_crud.py tests/routes/test_personal_facts_routes.py tests/test_context_broker_facts.py tests/test_chatgpt_import_facts.py -v

# Run migration
alembic upgrade head

# Verify with sanity script
./scripts/maintenance/pg_verify.sh
```
