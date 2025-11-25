### Current state (recon)
- **System prompt assembly:** `prompts.py:get_guardian_system_prompt` builds a system string from the immutable `_base_codexify_system_prompt`, depth hint, stubbed Imprint_Zero style block, stubbed persona block, and optional RAG hint. It does *not* touch storage; imprint/persona blocks are pseudocode.
- **LLM call path:** `guardian/routes/chat.py::chat_complete` gathers messages from `chatlog_db.list_messages`, builds `context`, optionally assembles a RAG bundle via `ContextBroker`, and prepends a system message. If `codexify.prompts` is importable, it calls `get_guardian_system_prompt(user_id, depth, project_id, bundle)` and attaches the result as a single system message before user/assistant turns. `_groq_complete` may add an extra system message for detailed RAG context but does not supply persona/immutable core itself.
- **RAG bundle:** Built in `ContextBroker.assemble(thread_id, query, depth, user_id)`, includes semantic/memory/graph/sensors depending on depth; passed to `_groq_complete`.
- **Imprint_Zero artifacts:** `guardian/imprint_zero_onboarding.py`, `guardian/agents/imprint_zero.py`, CLI helpers, and `frontend/src/persona/ImprintName.ts` (deterministic name generator). No persistent imprint/persona/doc storage yet.
- **Front-end touchpoints:** Persona naming helper in `ImprintName.ts`; no current UI for persona/system-doc configuration or token warnings. Guardian chat uses the backend system prompt; messages fetched via `/chat/{id}/messages`.

### Target architecture
- **Immutable core:** Keep `_base_codexify_system_prompt()` in `prompts.py` untouched and non-editable.
- **Data storage (new)**
  - `imprints` table: per-(user_id, project_id) inferred style/name/preferred_name, grammar_prefs JSONB, metrics JSONB, heat_score, status (`draft|active|superseded`), timestamps. Enforce one active per (user_id, project_id).
  - `personas` table: per-(user_id, project_id) user-editable persona text, source (`user|imprint_zero_seed|imported_doc|…`), is_active flag, timestamps. Latest active wins.
  - `system_docs` table + link table `system_doc_links` ((user_id, project_id, doc_id), is_enabled) to attach long-form “system docs” per user/project; docs have scope (`global|project|user`), title, slug, content, is_enabled, timestamps.
- **Stores/services (Python)**
  - `codexify/imprints/store.py`: `get_active_imprint(user_id, project_id)`, `save_imprint(...)`, `activate_imprint(...)` (supersede prior actives).
  - `codexify/personas/store.py`: `get_active_persona(user_id, project_id)`, `set_persona(...)`.
  - `codexify/system_docs/store.py`: `get_docs_for(user_id, project_id)`, `estimate_token_cost_for_docs` (heuristic len/4 if tokenizer unavailable).
  - Unit tests per store.
- **Prompt builder (new module, e.g., `codexify/system_prompt_builder.py`):**
  - Orchestrates storage calls (imprint, persona, docs) and constructs a single system prompt string by calling `get_guardian_system_prompt` with structured inputs (already-fetched imprint/persona/docs and depth/bundle hints).
  - Concatenates system docs with clear delimiters `=== System Document: {title} ===`.
  - Returns `(system_prompt, meta)` where meta includes `total_chars`, `estimated_tokens`, `docs_count`, segment breakdown.
- **`prompts.py` refactor:**
  - Keep `_base_codexify_system_prompt` immutable.
  - Change `_imprint_zero_style_block` and `_user_persona_block` to accept data objects instead of doing lookups.
  - Add `_system_docs_block` to render concatenated docs text.
  - `get_guardian_system_prompt` accepts structured args (imprint/persona/system_docs_text/depth/bundle) and emits one primary system message.
- **Chat integration:**
  - In `guardian/routes/chat.py::chat_complete`, fetch user_id/project_id from thread, build bundle via `ContextBroker`, then call `build_guardian_system_prompt(...)` (new builder) to prepend the single system message. `_groq_complete` may still add an extra system message for RAG context only.
  - Record prompt meta (token estimate) for UI warnings.
- **Imprint_Zero flow:**
  - Onboarding logic gathers style metrics, generates draft imprints; exposes `/api/imprint/proposal`, `/api/imprint/accept`, `/api/imprint/reject`. Accept activates imprint and may seed a persona row (source=`imprint_zero_seed`); user edits always override.
  - Frontend toast/modal watches for proposal, allows Accept/Edit/Reject; persona edits win over generated content.
- **Token-cost awareness:**
  - Builder returns estimated_tokens; add `/api/system_prompt/summary` to expose counts/breakdown.
  - Frontend settings surface shows estimated size and warns when over threshold (e.g., >1500–2000 tokens); allows disabling docs or editing persona to shrink prompt.

### Call points and data availability
- **System message build & pass-through:** `chat_complete` constructs `messages_for_llm` and prepends system prompt. `_groq_complete` receives `messages` + `context` bundle (RAG).
- **User/project IDs:** From `chatlog_db.get_chat_thread(thread_id)` inside `chat_complete`; project_id parsed to int if present.
- **RAG bundle:** `ContextBroker.assemble(thread_id, query=latest_user_msg, depth, user_id)`; passed to `_groq_complete` and should also be provided to the prompt builder for light hints.

### Pending work (next steps)
1) Add migrations for imprints/personas/system_docs/system_doc_links with constraints (one active imprint per user/project; unique doc slugs per scope).  
2) Implement store modules with tests.  
3) Refactor `prompts.py` + add `system_prompt_builder.py`; wire into `chat_complete`.  
4) Implement Imprint_Zero proposal APIs + frontend toast/modal; add persona/docs UI plus token warning.  
5) Document in `docs/system_prompts_and_imprints.md`; expose `/api/system_prompt/summary` for UI.
