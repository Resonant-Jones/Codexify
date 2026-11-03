# PFP-03A — Automatic Personal Fact Collection: Consent and Candidate-Authority Proof

**Campaign:** PFP-001 ([#889](https://github.com/Resonant-Jones/Codexify/issues/889)) · **Execution issue:** [#919](https://github.com/Resonant-Jones/Codexify/issues/919) · **Prerequisite:** PR [#895](https://github.com/Resonant-Jones/Codexify/pull/895) (merged) · **Release posture:** HOLD (unchanged)

**Task kind:** bounded diagnostic proof. **No runtime file, migration, test, ADR, or canonical current-state document was modified.** The only file added by this task is this report.

---

## 0. Provenance and method

| Item | Value |
|---|---|
| Inspected `origin/main` | `07069740e63107413b8e324d4b4fb99e8beb25a8` (Merge PR #917, "proof/agent-run-cancellation-authority") |
| Merge base for this branch | `07069740e63107413b8e324d4b4fb99e8beb25a8` (branched directly from current `origin/main`) |
| PR #895 merge commit on `main` | `8837777d85f1b25ef8b0f6956e90107b52dfdef3` (merged 2026-10-27T14:29:24Z) |
| Worktree | clean, freshly fetched, branched from `origin/main` |
| Method | source reading of the merged tree; **synthetic fixtures only** — no live account read, no production data inspected or written |
| Authority | GitHub `main` is accepted source authority (ADR-041); VaultNode remains runtime/audit authority and was **not** used as acceptance |

### 0.1 PFP-01 merged source behavior confirmed

| PFP-01 acceptance behavior | Merged `main` | Evidence |
|---|---|---|
| Candidate route precedes the integer fact route | yes | `guardian/routes/personal_facts.py:317` `@router.get("/candidates")` precedes `:454` `@router.get("/{fact_id}")` |
| SQL-level pagination and counting | yes | `guardian/core/pgdb.py` `list_facts` / `count_facts` / `list_fact_evidence_for_facts` |
| Archived inactive visibility | yes | candidate handler computes `active_only = status != "archived"` |
| Fail-closed evidence reads | yes | evidence-loader failure → sanitized HTTP 500, static event token, no chained cause |
| Account isolation | yes | account identity derived from the authenticated principal |
| Published proof artifacts | present | `docs/Campaign/personal-fact-pipeline-baseline.md` (997 lines, unmodified), `tests/routes/test_personal_fact_candidates_pagination.py`, `tests/mcp/test_candidates_guardian_integration.py` |

---

## 1. Findings matrix

Legend — **IMP**: implemented and wired · **DEF-UNWIRED**: defined but nothing reads it · **MISSING**: no implementation of the contract concept exists · **UNPROVEN**: implemented in code but not demonstrated at runtime.

| # | Finding | Classification | Primary evidence |
|---|---|---|---|
| F1 | `automatic_memory_suggestions` (unset \| enabled \| paused \| declined) has **no implementation anywhere** — it exists only as contract prose | **MISSING** | `grep -rn "automatic_memory_suggestions"` over the whole tree returns exactly one hit: `docs/architecture/unified-memory-store-contract.md:2521` |
| F2 | The **live-chat path performs no consent check** before automatic candidate creation | **MISSING** | `guardian/routes/chat.py:1177-1211` — the only gate is `if role == "user" and db_content:`; no settings, consent, or exclusion read |
| F3 | The **imported-history path performs no consent check** either | **MISSING** | `backend/rag/chatgpt_migration.py:386-431` calls the guardrail classifier unconditionally, with no consent read |
| F4 | A durable account preference surface **does** exist (`user_settings` table) and is read in production — but it carries **`memory_mode`, not collection consent** | **IMP (different control)** | `guardian/db/models.py:4376-4405`; `guardian/db/migrations/versions/8f1a2c3d4e5b_add_user_settings_table.py`; read via `guardian/services/iddb_settings_service.py:125` |
| F5 | `memory_mode = 'none'` gates **identity / imprint modelling only**, not Personal Fact candidate collection | **IMP (different control)** | `guardian/routes/imprint.py:185` `_identity_updates_allowed()`; no candidate path consults it |
| F6 | `guardian/cognition/user_settings/store.py` is an **in-memory shim imported by nothing** | **DEF-UNWIRED (dead code)** | `grep -rn "cognition.user_settings"` over the tree returns no importer |
| F7 | There is **no exclusion mechanism** for memory collection (no opt-out, skip, or suppression surface) | **MISSING** | Only `no_memory_store` exists, in `guardian/context/broker.py:1542`, and is unrelated to collection consent |
| F8 | There is **no consent vocabulary** in the protocol token registry | **MISSING** | `grep -niE "consent\|suggestion" guardian/protocol_tokens.py` returns nothing |
| F9 | Live-chat candidates are created **without guardrail classification** | **IMP (gap)** | `guardian/fact_candidate_pipeline.py:453-459` calls `create_fact(...)` with no `guardrail_metadata`; the module never imports `guardrail_policy` |
| F10 | Live-chat candidates are created **without `source_role`** | **IMP (gap)** | `guardian/fact_candidate_pipeline.py:228-252` `_build_evidence_meta` has no `source_role` key |
| F11 | Live-chat candidates carry **no reason codes, no disposition, and no quarantine posture** | **IMP (gap)** | same as F9/F10; `guardrail_metadata` remains `NULL` |
| F12 | Live-chat candidates are **persisted to the legacy `personal_facts` table** | **IMP (transitional deviation)** | `guardian/fact_candidate_pipeline.py:453` → `create_fact`; contract §4.16.12: the legacy projection "remains a read-only view of `personal_facts`, **not authority for a newly extracted raw candidate**" |
| F13 | The UMS `candidate_unreviewed_fact` species exists **only as a read projection** over legacy rows | **IMP (read-only)** | `guardian/core/memory_compatibility.py:701-740` `read_candidate_personal_fact_projection`; the module contains no candidate write path |
| F14 | ADR-084 **explicitly permits** the legacy read path as a transition "until a separately authorized, verified migration" | **IMP (documented transition)** | `docs/architecture/adr/084-unified-account-owned-memory-store.md:103-106` |
| F15 | Candidates and quarantined facts **cannot become ambient provider context** | **IMP (verified)** | `guardian/context/broker.py:1894-1910` reads `status="verified", active_only=True` and applies `_is_verified_active_personal_fact` (`:232-244`); the UMS candidate projection sets `ambient_eligible = False` |
| F16 | Live-chat candidate creation is **synchronous inside the chat request path** (mis-labelled "fire-and-forget") | **IMP (behavioural note)** | `guardian/routes/chat.py:1176-1211` — the call is in-line after `create_message`; errors are swallowed inside the pipeline, but the work is not deferred |
| F17 | Live-chat "sensitive key" detection **logs only** and stores the candidate anyway, with no persisted flag | **IMP (gap)** | `guardian/fact_candidate_pipeline.py:404-412` — "log but don't block … we still store for review, just with a flag"; no flag is written to the fact or evidence row |

---

## 2. Path A — live chat

### 2.1 Trace

```
POST message (user role)
  └─ guardian/routes/chat.py
       ├─ owner = _resolve_thread_owner_hint(...)            (chat.py:174-188)
       │     └─ account_id from the authenticated RequestUserScope;
       │        a requested user_id that differs → HTTP 403
       ├─ chatlog_db.create_message(thread_id, role, db_content)   → durable message id `mid`
       ├─ chatlog_db.write_audit_log("create", "chat_message", mid, user_id=str(owner))
       └─ if role == "user" and db_content:                  (chat.py:1177)
            └─ _process_fact_candidates(                      (chat.py:1199)
                 chatlog_db=…, user_id=str(owner), thread_id, message_id=mid,
                 persona_id, project_id, text=db_content)
                 └─ guardian/fact_candidate_pipeline.py::process_user_message  (:317)
                      1. extract          _extract_candidates_from_text (:258)  — regex rules
                      2. sensitive-key    _is_sensitive_candidate (:219) → log only, still stored
                      3. dedup            list_facts(user_id, active_only=True, limit=1000)
                                         → skip if any active fact has the same key
                      4. create_fact(..., status="candidate", confidence=…)   (:453)  ← NO guardrail_metadata
                      5. add_fact_evidence(fact_id, int(mid), excerpt,
                                           modality="text", confidence,
                                           source_type="runtime_extraction",
                                           evidence_meta=_build_evidence_meta(…))  (:486-495)
```

### 2.2 Account principal and source role

- **Account principal:** `owner` → `_resolve_thread_owner_hint()` → the **authenticated account id** from the request user scope. A caller-supplied `user_id` that differs from the authenticated account is rejected with **403**. Account ownership is therefore derived from the authenticated principal, never from operator credentials (ADR-039 satisfied). ✅
- **Source role:** the call site is gated on `role == "user"`, so the *effective* role is user — but the role is **not recorded anywhere**. `_build_evidence_meta` emits `source`, `source_type`, `user_id`, `thread_id`, `source_message_id`, `detector_rule`, `fact_candidate_key`, `fact_candidate_value`, and optional `persona_id` / `project_id` — **no `source_role`**.

### 2.3 What a live-chat candidate retains

| Field | Retained? | Where |
|---|---|---|
| `source_role` | **No** | absent from `_build_evidence_meta` (`:228-252`) |
| `source_message_id` | **Yes** | evidence column **and** `evidence_meta["source_message_id"]` |
| `source_type` | **Yes** | `"runtime_extraction"` (`:51`) |
| source evidence | **Yes** | evidence row with excerpt, modality, confidence, `detector_rule` |
| guardrail disposition | **No** | `create_fact` called without `guardrail_metadata`; column stays `NULL` |
| reason codes | **No** | classifier never invoked |
| explicit runtime exclusion | **By status only** | candidate status excludes it from provider context; there is **no per-candidate exclusion field** |

### 2.4 Why the missing source role is a correctness gap, not only a metadata gap

The Personal Facts Guardrails Contract requires:

> "If an assistant turn contains a claim about the user, it must be flagged with a source-role reason and held in quarantine…" (§15, line 143)
>
> "**Ambiguous authorship must fail closed** into quarantine or discard, not promotion. When the source role is missing, unclear, or contradictory: … The candidate must be quarantined with a source-role reason." (§, lines 168-170)

The classifier already encodes this — `_check_source_role` (`guardian/personal_facts/guardrail_policy.py:156-174`) raises `GuardrailReason.SOURCE_ROLE_AMBIGUOUS` with `block=True` for an empty role, and `SOURCE_ROLE_ASSISTANT` / `SOURCE_ROLE_SYSTEM_LIKE` for those roles (`guardian/personal_facts/guardrail_tokens.py:19-21`).

**The live-chat path never calls that classifier.** It therefore writes a candidate with no disposition, no source role, and no quarantine posture, into the account's own candidate table. The live-chat extractor only ever sees *user* turns, so the assistant/system-like cases cannot arise today — but the **missing source role means the fail-closed rule cannot be exercised at all**, and a future change that widens the extractor to non-user turns would have no guard to stop it.

---

## 3. Path B — imported history

### 3.1 Trace

```
account import (ChatGPT / Claude export)
  └─ backend/rag/chatgpt_migration.py
       ├─ _canonicalize_claude_role / _map_role      (:320, :1357) → canonical role + raw role
       ├─ extract_personal_fact_candidates(...)  (backend/rag/personal_fact_extraction.py:348)
       └─ _classify_import_candidates(candidates, source_role=…, source_type=…, source_label=…)  (:386)
            └─ classify_personal_fact_candidate(CandidateInput(…, source_role=source_role, …))  (:404)
                 └─ disposition == "discard" → dropped (skipped_discard)      (:417)
                 └─ otherwise attach to the candidate dict:                    (:422-425)
                      _guardrail_disposition
                      _guardrail_reasons
                      _guardrail_promotion_blocked
                      _guardrail_review_required
            └─ persist_personal_fact_candidates(chatlog_db, user_id=…, message=…, candidates=…)  (extraction.py:497)
                 ├─ guardrail_meta = _extract_guardrail_metadata(candidate)   (extraction.py:292)
                 ├─ create_fact(..., status="candidate", confidence=…,
                 │              guardrail_metadata=guardrail_meta)            (extraction.py:593-599)
                 └─ add_fact_evidence(…, source_type="chatgpt_import",
                                      evidence_meta=_build_evidence_meta(…))  (extraction.py:655-665)
```

### 3.2 Account principal and source role

- **Account principal:** the `user_id` passed into `persist_personal_fact_candidates` (`:500`) — the importing account.
- **Source role:** canonicalised from the imported message role and **recorded** in `evidence_meta["source_role"]` (`:333`).

### 3.3 What an imported-history candidate retains

| Field | Retained? | Where |
|---|---|---|
| `source_role` | **Yes** | `evidence_meta["source_role"]` (`:333`) |
| `source_message_id` | **Yes** | `source_message_export_id` + `source_message_db_id` |
| `source_type` | **Yes** | `"chatgpt_import"` (`:17`) |
| source evidence | **Yes** | evidence row + import provenance (`import_source`, `import_profile`, `source_created_at`, `turn_index`, …) |
| guardrail disposition | **Yes** | `guardrail_metadata` on the fact row: `disposition`, `reasons`, `review_required`, `promotion_blocked` (`:292-311`) |
| reason codes | **Yes** | canonical `GuardrailReason` tokens inside `guardrail_metadata` |

### 3.4 The two paths side by side

| Dimension | Live chat | Imported history |
|---|---|---|
| Trigger | after durable user message commit, in-request | account import operation |
| Account principal | authenticated account id (403 on mismatch) | importing account id |
| Guardrail classifier | **not called** | **called** |
| `source_role` | **absent** | present |
| `guardrail_metadata` | **NULL** | populated |
| Reason codes | none | canonical tokens |
| Discarded candidates | n/a (no classification) | removed before persistence |
| Quarantine posture | none | `quarantined` / `promotion_blocked` recorded |
| `source_type` | `runtime_extraction` | `chatgpt_import` |
| Dedup | active facts by key (`limit=1000`) | `_find_existing_fact` / `_existing_evidence_matches` |
| Consent gate | **none** | **none** |
| Writes to | legacy `personal_facts` | legacy `personal_facts` |

The guardrail-vocabulary backfill tooling (`guardian/personal_facts/guardrail_backfill.py`, plus `guardian/core/db.py:1846-1866` "facts lacking `guardrail_metadata`" and `:1867` `set_fact_guardrail_metadata`) exists precisely because **live-chat rows are the unclassified population** — it is a pure planning seam over candidate/disputed rows with `guardrail_metadata IS NULL`, applied only by the operator-run `scripts/personal_facts/backfill_guardrail_metadata.py` with `--apply`.

---

## 4. Consent state — what is implemented, defined-but-unwired, missing, or unproven

### 4.1 The governing contract

`docs/architecture/unified-memory-store-contract.md` §8.1 (line ~2521) specifies a versioned account-user preference:

```text
automatic_memory_suggestions = unset | enabled | paused | declined
consent_policy_version
consent_recorded_by_user_id
consent_recorded_at
consent_updated_at
```

and states:

- "Onboarding may recommend `enabled`, but **the classifier cannot run until the user saves that choice**."
- "`unset`, `paused`, and `declined` **prevent classifier enqueue**."
- "Pausing capture does not delete existing records."
- "Explicit remember commands remain available."

§8.2 then conditions the classifier on consent: "After a durable user message commits, an event may enqueue classification **only when consent is enabled and exclusions permit it**."

### 4.2 Classification of every candidate consent surface

| Surface | Classification | Why |
|---|---|---|
| `automatic_memory_suggestions` preference | **MISSING** | no column, no model, no service, no route, no token — the only occurrence in the entire repository is the contract line itself |
| Consent read at the live-chat call site | **MISSING** | `chat.py:1177-1211` reads no settings, consent, or exclusion |
| Consent read at the import path | **MISSING** | `chatgpt_migration.py:386-431` classifies unconditionally |
| `user_settings.memory_mode` | **IMPLEMENTED, DIFFERENT CONTROL** | gates identity/imprint modelling (`imprint.py:185`), not candidate collection; values `none\|light\|deep`, default `deep` |
| `user_settings.diary_requires_unlock`, `allow_sensitive_modeling` | **IMPLEMENTED, DIFFERENT CONTROL** | identity modelling gates, not collection consent |
| `guardian/cognition/user_settings/store.py` | **DEFINED-BUT-UNWIRED** | in-memory shim, "replace with durable persistence"; imported by nothing |
| Exclusion mechanism (skip / opt-out / suppression) | **MISSING** | no such surface exists |
| Consent vocabulary in `guardian/protocol_tokens.py` | **MISSING** | no consent or suggestion token |
| `capture consent` in `chat.py:5720,5741` | **UNRELATED** | this is provider-request-capture *service capability* ("Service capability can check existing consent, never create it"), a different concept |
| `automatic_memory_suggestions` runtime behaviour | **UNPROVEN** | cannot be unproven — there is no implementation to exercise |

**Conclusion.** The governing consent preference does not exist in code. Automatic candidate collection from live chat therefore runs **unconditionally**, on every persisted user message, with no account-level switch that could stop it. The contract's §8.1/§8.2 precondition — "the classifier cannot run until the user saves that choice" — is **not satisfied**, and the invariant "no automatic collection without the governing consent" is **not currently upheld** for the live-chat path.

The PFP-00 baseline recorded the same two live-chat gaps (`source_role` and guardrail disposition absent) and additionally noted that live-chat candidates carry no guardrail disposition and no `source_role`. **Those findings are confirmed unchanged on merged `main` at `07069740e…`.**

---

## 5. Which storage authority owns newly created candidates

### 5.1 What ADR-084 and the UMS contract require

- **ADR-084** (`:98-106`): "The single UMS `candidate_unreviewed_fact` record owns raw proposal, evidence links, guardrail disposition, quarantine, and account-user review before promotion. **No `personal_facts` row is required for candidate review or quarantine.**" (`:98-102`) But: "Legacy pre-promotion rows continue to be read through the existing compatibility path **until a separately authorized, verified migration reconciles them into the UMS candidate authority**." (`:103-106`)
- **UMS contract §3.4** (`:134-190`): "Before promotion, the single `candidate_unreviewed_fact` UMS record is the review, guardrail, and quarantine authority. Its state and evidence **do not require a `personal_facts` row**."
- **UMS contract §4.16.12** ("Compatibility reader relationship to persistence", heading at `:2117`; statement at `:2285-2286`): "The existing legacy candidate compatibility projection remains a **read-only view of `personal_facts`, not authority for a newly extracted raw candidate**."
- **UMS contract §4.13** (`:1025-1040`): the compatibility-read matrix "describes existing legacy compatibility reads, **not the target authority for newly extracted Personal Fact candidates under §3.4**".

### 5.2 What is implemented

- `guardian/core/memory_compatibility.py:701-740` — `read_candidate_personal_fact_projection` is the **only** candidate function in the compatibility layer. It is a **read-only** projection over legacy `personal_facts` rows (`status ∈ {candidate, disputed, archived}` or `is_active = false`) and sets `ambient_eligible = False`. There is **no candidate write path** in that module.
- Both ingestion paths write new candidates into the **legacy `personal_facts` table** via `create_fact` (`guardian/core/db.py:1618`), with `guardrail_metadata` present only for the import path.

### 5.3 Alignment / discrepancy

**This is a documented transition, not an unresolved choice between co-authorities.** The contract and ADR-084 both state that legacy rows remain the *read* compatibility path until a separately authorized, verified migration. The audited import-readiness note agrees: "This is an explicitly documented transition, not an unresolved choice between co-authorities."

The precise current state:

| Question | Answer |
|---|---|
| What **stores** newly created candidates today? | legacy `personal_facts` + `personal_fact_evidence` |
| What is the **target** pre-promotion authority? | a single UMS `candidate_unreviewed_fact` record (not implemented) |
| Does the existing UMS candidate code own writes? | **no** — read-only projection |
| Is there a **parallel mutable** candidate authority? | **no** — one legacy store, one read projection over it; no second writable candidate table exists |
| Does ADR-084 permit the present state? | **yes, as an explicit transition** pending "a separately authorized, verified migration" |
| Is the present state a contract violation? | **no** — but the contract is explicit that the legacy projection "is not authority for a newly extracted raw candidate", so the **target** remains unimplemented and both paths write outside the target authority |

**ADR-084 alignment:** no second candidate authority exists; ownership is single; the deviation is a documented, bounded transition. The gap is the *unimplemented target* (§3.4 candidate record), not a co-authority conflict. Migrating it is a non-goal of this task and requires separate authorization plus a qualified migration.

---

## 6. Runtime eligibility and approval boundaries — preserved

| Invariant | State | Evidence |
|---|---|---|
| Only verified, active, user-scoped facts enter provider context | upheld | `guardian/context/broker.py:1894-1910` (`status="verified"`, `active_only=True`) + `_is_verified_active_personal_fact` (`:232-244`) — ADR-013 |
| Candidates and quarantined facts cannot become ambient provider context | upheld | candidate status is excluded by the same predicate; UMS candidate projection sets `ambient_eligible = False` |
| Evidence and revision lineage protected | upheld | evidence rows are written for both paths; PFP-01's fail-closed read protects the review surface |
| Promotion/approval is a separate, explicit path | upheld | live chat only writes `status="candidate"`; promotion stays in `POST /candidates/{fact_id}/approve` and `POST /{fact_id}/confirm`, which require the account principal |
| No promotion without a disposition | **not upheld for live chat** | live-chat rows carry no disposition, so the review surface cannot distinguish "reviewable" from "should have been quarantined" without a backfill |
| Account owns memory; consent cannot be supplied by a model or Operator | upheld for ownership | account id derives from the authenticated principal; no model/operator input path writes candidates |

---

## 7. Selected next bounded implementation slice

> **The contract places consent *before* classification.** §8.1: "the classifier cannot run until the user saves that choice"; §8.2: classification is enqueued "only when consent is enabled and exclusions permit it". Wiring the guardrail classifier into live chat *before* a consent gate exists would enable classified automatic collection with no consent — strictly worse than today. Therefore the consent gate is the prerequisite, and the guardrail wiring is sequenced after it.

### Selected slice — **PFP-03B: durable collection-consent preference and a live-chat collection gate**

**Required authority**

1. A versioned, durable, **account-user** preference carrying exactly the contract vocabulary: `automatic_memory_suggestions ∈ {unset, enabled, paused, declined}`, plus `consent_policy_version`, `consent_recorded_by_user_id`, `consent_updated_at` (and `consent_recorded_at`). It must be account-scoped, durable, and writable **only** by the authenticated account principal — never by a model, an Operator, or an import.
2. A single authoritative read seam returning the effective consent state for an account, defaulting to `unset` (deny), so that an absent preference is fail-closed.
3. A gate at the **one** automatic-collection entry point (`guardian/routes/chat.py:1177`), so that candidate creation is possible only when the effective state is `enabled`.

**Scope boundaries**

- Add the preference and its read/write seam; add the gate at the live-chat call site. Nothing else changes.
- `unset` / `paused` / `declined` must all prevent automatic candidate creation; `paused` must not delete existing records; explicit remember commands stay available.
- The import path is **out of scope for this slice** — an explicit, operator-initiated account import is a user-initiated act, not automatic collection, and gating it would change import semantics. It is recorded as a separate decision below.
- No classifier wiring, no `source_role` change, no `guardrail_metadata` change, no UMS migration, no schema or API redesign beyond the preference itself, no frontend.

**Required proof**

1. With effective consent `unset`, `paused`, or `declined`, a persisted user message produces **zero** new `personal_facts` rows and **zero** evidence rows.
2. With effective consent `enabled`, the same message produces the candidate and evidence rows the current pipeline produces — byte-for-byte the same shape, so this slice changes no candidate content.
3. Consent is account-scoped: account A's `enabled` state does not permit collection for account B, and the account principal used to write the preference is the authenticated account.
4. The preference survives a process restart (durable, not the in-memory shim).
5. No model-, Operator-, or import-supplied path can set the preference to `enabled` on an account's behalf.
6. **Consent compliance is not inferred from extraction unit tests passing** — the proof is an end-to-end message-persistence → collection-gate assertion with a synthetic account and synthetic message, plus an explicit negative for each of `unset` / `paused` / `declined`.

### Explicitly not selected, and why

| Candidate slice | Disposition |
|---|---|
| Wire the guardrail classifier into live chat + record `source_role` (F9, F10, F11) | **Next after PFP-03B.** It is a real correctness gap — the contract's ambiguous-authorship fail-closed rule cannot be exercised — but it must follow the consent gate so that classified collection is itself consent-bound. |
| UMS `candidate_unreviewed_fact` write authority (F12, F13) | **Separate authorization required.** ADR-084 conditions it on "a separately authorized, verified migration"; a non-goal here. |
| `memory_mode` reuse as collection consent (F4, F5) | **Rejected.** `memory_mode` is an identity-modelling depth control with different semantics and a different vocabulary; reusing it would blur two distinct account authorities. |
| Import-path consent gate (F3) | **Deferred decision.** Imported history is a user-initiated account act, not automatic collection; the contract's §8.1 addresses automatic suggestions. Recorded for human disposition, not silently assumed. |
| Guardrail backfill for existing unclassified live-chat rows | **Already exists** as an operator-run tool (`scripts/personal_facts/backfill_guardrail_metadata.py`). Not a code slice; a data operation requiring its own authorization. |
| Live-chat sensitive-key persistence (F17) | **Recorded, not selected.** "Log but don't block" without a persisted flag is a defensible interim posture, but the stored candidate carries no record that it was ever flagged. Fold into the PFP-03C guardrail slice, which has a natural place to persist a reason code. |

---

## 8. Validation receipt

Run from the clean, freshly fetched `origin/main` worktree (`07069740e63107413b8e324d4b4fb99e8beb25a8`), branch `pfp/pfp03a-collection-authority`. Interpreter: `/Volumes/Dev_SSD/Codexify-main/.venv/bin/python` (Python 3.12.13); `PYTHONPATH` pinned to the worktree so `guardian` resolves to the merged tree, not the main checkout.

| # | Command | Result | Exit |
|---|---|---|---|
| 1 | `python -m pytest -o addopts="" -v tests/test_fact_candidate_pipeline.py` | **21 passed** in 0.09 s | 0 |
| 2 | `python -m pytest -o addopts="" -v tests/personal_facts/test_guardrail_policy.py` | **33 passed** in 0.08 s | 0 |
| 3 | `python -m pytest -o addopts="" -v tests/mcp/test_candidates_guardian_integration.py` | **14 passed** in 10.58 s | 0 |
| 4 | `python scripts/validate_docs.py` | "Docs validation passed: required architecture docs, README links, and source headings verified." | 0 |
| 5 | `python -m pytest -o addopts="" -q --disable-warnings tests/architecture` (additional — this file lives under `docs/Campaign/**`, which is a path trigger for the Architecture Contracts workflow) | **479 passed** in 17.15 s | 0 |
| 6 | `git diff --check` | no output (no whitespace error) | 0 |
| 7 | `git diff --name-only` | empty — no tracked file modified by this task | — |
| 8 | `git status --short` | exactly one entry, the new report: `A  docs/Campaign/pfp-03a-collection-consent-authority-proof.md`; no other file added, modified, or deleted | — |

**Totals: 68 focused tests passed, 0 failed, 0 skipped, 0 errors** (plus 479 Architecture Contracts tests). The three suites use synthetic fixtures only; no live account, no real memory content, and no production write was involved.

**These results do not evidence consent compliance.** Suite 1 exercises extraction and persistence mechanics; suite 2 exercises the guardrail classifier in isolation; suite 3 exercises the candidate-read surface end to end. None of them sets, reads, or asserts any collection-consent state, because no such state exists to exercise. The absence of the consent concept is the finding, and it is a source-level fact, not a test outcome.

### Environment note

The reusable Python 3.11 CI-shaped virtualenv from earlier campaign tasks was garbage-collected with a rotated session `TMPDIR`; the repository's own `.venv` (Python 3.12.13) was used instead. `pip check` in that environment reports one pre-existing, unrelated conflict (`mlx-vlm 0.1.27` pins `opencv-python==4.10.0.84`, installed `4.12.0.88`), which does not touch this task's suites. No PostgreSQL was required: all three suites are fixture-based.

---

## 9. Invariant and ADR checks

| Invariant | State | Basis |
|---|---|---|
| Account owns memory | upheld | both paths bind `user_id` to the account principal; live chat rejects a mismatched requested identity with 403 |
| Consent cannot be supplied by a model or Operator | upheld *today* (nothing can supply consent, because no consent surface exists) | no model/operator write path to any account preference exists |
| No automatic collection without the governing consent | **NOT UPHELD** | F1–F3: no consent concept; live chat collects unconditionally |
| No parallel mutable candidate authority | upheld | one legacy store + one read-only projection; no second writable candidate table |
| Candidate and quarantined facts cannot become ambient provider context | upheld | broker verified+active predicate; UMS `ambient_eligible = False` |
| Evidence and revision lineage remain protected | upheld | evidence written on both paths; PFP-01 fail-closed read |
| GitHub main is accepted source authority | upheld | inspected `origin/main` = `07069740e…` |
| VaultNode remains runtime/audit authority | upheld (not used as acceptance) | no runtime claim made here |
| Release HOLD remains unchanged | upheld | no deployment, no release claim, no current-state edit |

**ADR impact:** this task is a **bounded diagnostic proof**. It makes no ADR change, proposes none, and does not alter ADR-084, ADR-013, ADR-039, or ADR-041. The selected PFP-03B slice changes **consent authority**, which requires explicit architecture-impact classification before execution — it is named as a *selection*, not performed here.

---

## 10. Scope discipline

**Not done, by direction:** no classifier wiring, no consent control plane, no new automatic candidate writes, no UMS candidate migration, no schema or API change, no deduplication or retry redesign, no promotion or approval change, no frontend work, no deployment, no release qualification. No runtime file, migration, test, ADR, or canonical current-state document was modified. The historical PFP-00 baseline (`docs/Campaign/personal-fact-pipeline-baseline.md`, 997 lines) is intact. Canonical current-state and release claims are unchanged and were not updated.
