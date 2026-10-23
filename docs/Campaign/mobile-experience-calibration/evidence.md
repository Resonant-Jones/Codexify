# Mobile Experience Calibration — Evidence Register

**Campaign ID:** `CAMPAIGN-MOB-2026-10-23`
**Companion:** [README.md](./README.md)
**Tracking issue:** https://github.com/Resonant-Jones/Codexify/issues/888
**Baseline commit:** `b2907f828` (branch `feat/auto-20261023-5ef3356f`)
**Gate 0 status:** complete
**Classification:** repository-local execution record. Non-normative. Cannot
authorize runtime behavior, identity claims, provider calls, or release changes.

---

## 1. How to read this register

Every entry states an **evidence class** (see README §2). Class is never
inferred from another class.

- `code-path` proves what the source says at a cited line. It does not prove a
  user saw it.
- `unit-test` proves an assertion held when the test ran. It does not prove
  runtime behavior, and it is not live-runtime proof.
- `docs-only` proves a contract or a recorded prior proof exists. Its evidence
  maturity is stated, never assumed.

The five reported symptoms originate from **reported observations**
(screenshots and operator description). Nothing in this register yet
establishes a cause for any of them on a physical device.

---

## 2. Environment and method

| Item | Value |
|---|---|
| Worktree | `/Volumes/Dev_SSD/Codexify-main/.worktrees/feat-auto-20261023-5ef3356f` |
| Branch | `feat/auto-20261023-5ef3356f` |
| Baseline | `b2907f828` (merge of PR #887) |
| Working tree at Gate 0 start | clean |
| Frontend test runner | vitest 3.2.7, config `frontend/src/vitest.config.ts` |
| Backend test runner | `pytest` (`pytest.ini` sets `addopts = -q`, which **overrides** a command-line `-v`; use `pytest -o addopts="" -v` when test identities matter) |
| Documentation validation | `scripts/validate_docs.py` validates the `docs/architecture/` corpus only. It does **not** scan `docs/Campaign/`, so no repository documentation validation applies to this gate's files. |

Gate 0 was read-only apart from the two authorized campaign documents. Two
focused read-only source sweeps were delegated (mobile composer layout;
provider/model selection truth path); every load-bearing claim below was
re-verified directly against source before being recorded.

---

## 3. Evidence register — onboarding density and copy (symptoms 1 and 2)

### E-01 — The onboarding wizard has six semantic steps, one of which renders seven cards at once

**Class:** `code-path`

`frontend/src/features/onboarding/onboardingTypes.ts:1-8` defines exactly six
step keys: `welcome`, `identity`, `username`, `navigation`, `core_surfaces`,
`help`.

`frontend/src/features/onboarding/OnboardingWizard.tsx:113-139` renders the
`core_surfaces` step as a `learning-grid` of **seven** tip cards, each showing
its full `title` + `body` from `onboardingContent.ts`.

The six-key set is a **contract**, not an implementation detail:
`docs/architecture/onboarding-and-tips-contract.md:11` requires the six
semantic step keys and forbids removing them. The contract also requires that
the six keys map to the account-owned progress record
(`onboarding-and-tips-contract.md:19-21`).

**Consequence for Gate 4:** the fix must be presentation-only. Paginating the
seven cards does not change the six step keys, the persisted `last_step_key`,
or the progress record.

### E-02 — The card grid collapses to one column on a phone, making the surfaces page the tallest step

**Class:** `code-path`

`frontend/src/features/onboarding/onboarding.css:50-54` defines `.learning-grid`
as a two-column grid (`repeat(2, minmax(0, 1fr))`); `onboarding.css:88-90`
collapses it to a single column at `max-width: 640px`.

`frontend/src/features/onboarding/onboarding.css:13-15` gives `.learning-dialog`
`max-height: calc(100dvh - 36px)` with `overflow: auto`.

**Consequence for Gate 4:** on a phone the seven two-sentence cards stack in
one column inside a scroll container. This is the structural cause of
"onboarding content exceeds comfortable phone viewport limits". No device
measurement was taken; the geometry follows from the declarations.

### E-03 — Onboarding body copy carries internal-contract language

**Class:** `code-path`

`frontend/src/features/onboarding/onboardingContent.ts` — the `body` strings
include: `"Execution capabilities depend on the current runtime and
permissions."` (Guardian), `"Availability and processing depend on the
current runtime."` (Documents), `"Generation tools depend on the runtime's
available capabilities."` (Gallery), `"according to the workspace's current
behavior"` (Projects), `"not established by this introduction"` (People), and
the full username charset rule (`"3–32 lowercase ASCII letters, digits,
underscores, or hyphens"`).

**Consequence for Gate 4:** the copy must be rewritten to user-facing language
while keeping the underlying truths. Two constraints from the governing
contract must survive the rewrite:

- `onboarding-and-tips-contract.md:15` — the account is a privacy
  boundary; onboarding must not require self-doxxing.
- `onboarding-and-tips-contract.md:13` — onboarding must not require a
  username.

The username charset rule is a *contract-level* claim about the username
field. It must be stated plainly without becoming an internal error message.

### E-04 — Onboarding account-state semantics that must not drift

**Class:** `code-path`

`frontend/src/features/onboarding/OnboardingProvider.tsx` implements the
account-owned record: skip sets `status: "skipped"` with the durable
`last_step_key` preserved; resume restores from `last_step_key`; restart
clears the record. `onboarding-and-tips-contract.md:9-21` fixes these
semantics.

`frontend/src/features/onboarding/__tests__/Onboarding.test.tsx` is the
neighboring test surface and must be extended, not replaced.

---

## 4. Evidence register — composer placement (symptom 3)

### E-05 — The landing composer unit is translated upward by half its own height, on every viewport

**Class:** `code-path`

`frontend/src/features/chat/GuardianChat.tsx:4571` — the landing stage is
`relative flex min-h-0 min-w-0 flex-1 items-center justify-center`.

`frontend/src/features/chat/GuardianChat.tsx:4592` — the landing unit carries
`transform: "translateY(-50%)"`.

The **conversation** posture has no equivalent transform.

**Reading:** `items-center` already centers the unit vertically in the stage.
The additional `translateY(-50%)` lifts it by half its own height on top of
that centering. This is the most direct code-path candidate for "the floating
composer sits too high" on the new-thread surface. The transform was
introduced by commit `93bb09a37` ("Respect Guardian sidebar in landing
layout").

**Limit of this evidence:** this is a candidate cause, not a proven cause.
It is code-path proof of *geometry*, not a measurement of what the operator saw.
Gate 3 must verify against a rendered viewport before treating it as the fix.

### E-06 — The composer has no safe-area or keyboard inset of its own; the shell root shrinks instead

**Class:** `code-path`

- `frontend/src/components/persona/layout/AppShell.tsx:3671-3676` — the phone
  shell root is `position: fixed` with `height: var(--shell-viewport-height,
  100vh)`.
- `frontend/src/components/persona/layout/AppShell.tsx:2465` publishes
  `--shell-keyboard-inset` from `viewportInsets.keyboardInset`.
- `frontend/src/hooks/useViewportInsets.ts` computes `keyboardInset` from
  `layoutViewportHeight - visualViewportHeight - visualViewportOffsetTop`,
  with `isKeyboardOpen` at a 24px threshold, and binds `resize`,
  `orientationchange`, `focusin`, `focusout`, and `visualViewport`
  `resize`/`scroll`.
- `frontend/src/components/persona/layout/mobileShellProfile.ts` declares
  `chat.composer.bottomSafeArea: "env(safe-area-inset-bottom, 0px)"`.

**Verified by direct search:** `--shell-keyboard-inset` is written at
`AppShell.tsx:2465` and read **only** by a test assertion
(`AppShell.test.tsx:2187`). No stylesheet or component consumes it. The
`bottomSafeArea` token reaches only the ChatView jump-to-latest overlay
(`frontend/src/features/chat/ChatView.tsx:903`, applied at `ChatView.tsx:1149`),
**not** the composer.

**Consequence for Gate 3:** the canonical keyboard-inset and safe-area seams
already exist and are measured correctly. They are simply not plumbed to the
composer. When the iOS keyboard opens, the fixed shell root shrinks and the
flow-positioned composer rises with it — which is consistent with "feels
detached from the bottom of the usable screen" while typing.

### E-07 — The composer is deliberately in normal document flow, and that is asserted

**Class:** `code-path` + `unit-test`

`frontend/src/features/chat/__tests__/GuardianChat.session-shortcuts.test.tsx:431`
asserts the landing unit's `position` is **not** `fixed`. The composer is in
normal flow by contract.

**Consequence for Gate 3:** Gate 3 must not "fix" the composer by making it
`position: fixed`. The correct seam is the existing shell token channel.

### E-08 — No test currently asserts the landing vertical position or the composer bottom offset

**Class:** `code-path`

`frontend/src/components/persona/layout/__tests__/GuardianMobileComposerSingleSurface.test.tsx`
(749 lines, 13 tests) covers single-surface rendering, draft preservation,
near-bottom subject lock, and shell-in-normal-flow. It asserts **no**
composer vertical position and **no** landing transform. The landing transform
at `GuardianChat.tsx:4592` is therefore unprotected by any test.

### E-09 — A second, legacy composer exists with no importers

**Class:** `code-path`

`frontend/src/components/chat/Composer.tsx` (649 lines) has **zero** importers
across `frontend/src`. The live composer is
`frontend/src/features/chat/components/Composer.tsx`.

**Disposition:** recorded, not removed. Deleting it is outside the campaign's
authorized scope and is not required by any acceptance criterion. It is listed
as deferred work in §10.

### E-10 — Declared composer shell tokens are not consumed

**Class:** `code-path`

`mobileShellProfile.ts` declares `chat.composer.padX`, `padY`, `textPadX`,
`textPadY`, `controlGap`, and `controlSize`. Direct search shows
`shellMaxHeight` is consumed (`GuardianChat.tsx:4684`) and `bottomSafeArea` is
consumed only by the ChatView overlay; the remaining declared tokens have no
consumer. The composer hardcodes its own padding rather than reading the
declared profile.

**Consequence for Gate 3:** part of the "sits too high" calibration may be
token-plumbing rather than new geometry. Gate 3 must determine which, and must
not invent a parallel token set.

---

## 5. Evidence register — provider/model truth (symptom 4)

### E-11 — The provider catalog is server-authoritative; the frontend hardcodes no provider list

**Class:** `code-path`

- `frontend/src/features/chat/hooks/useLlmCatalog.ts:405-451` fetches
  `GET /api/llm/catalog`; the path builder is `frontend/src/lib/api.ts:314-316`.
- `guardian/routes/health.py:984-987` serves it via `build_llm_catalog`.
- `guardian/core/llm_catalog.py:822-857` builds each provider entry with
  `id`, `displayName`, `enabled`, `authorized`, `available`, `models`,
  `truth`, `source`, `runtime`, `endpoint_resolution`, `model_resolution`,
  `default_model`, `configured_model`, and `disabled_reason`.
- `frontend/src/features/chat/GuardianChat.tsx:1358-1382` labels providers by
  `provider.runtime?.displayName ?? provider.displayName` — the **runtime
  identity** ("Whoosh'd"), not the provider class.

**Consequence for Gate 1:** the catalog is the correct and only source. The
Gate 1 fix is a presentation and reconciliation fix over an existing
authoritative source, not a new provider framework.

### E-12 — A locally hosted DeepSeek model presents under the label "DeepSeek"

**Class:** `code-path`

`guardian/core/llm_catalog.py:44-45` defines
`_MODEL_FAMILY_ALIASES = { "deepseek": "DeepSeek", "gemma": "Gemma", ... }`,
applied at `llm_catalog.py:258-259` when deriving a model's display label.

**Consequence for Gate 1 — decisive for the reported symptom.** A model in the
**local** provider inventory whose family is `deepseek` is displayed as
"DeepSeek", while the provider itself is displayed by runtime identity
("Whoosh'd"). A user who sees "DeepSeek" and then observes Whoosh'd executing
is seeing **two consistent facts rendered adjacently** — the physical model
family of the local runtime, and the runtime identity.

This is consistent with the governing domain fact (`00-current-state.md:37`):
physical model display metadata is observation only. It is **not** proof of
silent substitution, and it **must not** be "fixed" by inventing a separate
DeepSeek provider.

### E-13 — Requested and effective execution are distinct, recorded, and already exposed

**Class:** `code-path`

| Fact | Written | Read |
|---|---|---|
| `requested_provider` | `guardian/routes/chat.py:3065` | `guardian/workers/chat_worker.py:1584` |
| `requested_model` | `guardian/routes/chat.py:3066` | `chat_worker.py:1585, 1590` |
| `selection_source` (`"explicit"` when either requested field is set) | `guardian/routes/chat.py:3067-3069` | `chat_worker.py:1587-1589` |
| effective `provider` | `chat.py:3063` | `chat_worker.py:1599, 1718` |
| effective `model` | `chat.py:3064` | `chat_worker.py:1600, 1719` |
| `attempted_*` / `final_*` / `fallback_triggered` | `guardian/workers/chat_worker.py:2262` | `chat.py:4056-4080`; `useChat.ts:320-363`; `ChatBubble.tsx:503-507` |

The backend trace builder is `guardian/routes/chat.py:4044-4140`, exposed at
`chat.py:4690-4702`. It derives `policy_reason` values
`requested_model_not_selected` (`chat.py:4133`) and
`requested_provider_not_selected` (`chat.py:4139`).

**Consequence for Gate 1:** the requested-vs-effective truth already exists in
authoritative fields. Gate 1 surfaces it on mobile. It does not create a new
record.

### E-14 — The effective-execution badge exists but is display-gated

**Class:** `code-path`

`frontend/src/features/chat/components/ChatBubble.tsx:504-507` renders
`⚠ Executed on ${execution.final_model}` when `final_model !== attempted_model`.

`frontend/src/features/chat/hooks/useChat.ts:339-341` requires all four
provider/model strings; `useChat.ts:354` additionally requires
`fallback_triggered` to be present or coercible. A partial `execution` payload
renders **no badge** — a display-only failure mode independent of whether
execution was correct.

### E-15 — The compact mobile composer deliberately has no provider/model selector and no summary chip

**Class:** `code-path` + `unit-test`

`frontend/src/components/persona/layout/__tests__/GuardianMobileComposerSingleSurface.test.tsx:430-495`
("renders compact mobile composer without provider/model summary chip and
without projection markers") asserts, against the live `Composer`:

- `composer-mobile-context-summary` is **absent** (`:473-476`);
- the "Select provider" button is **absent** (`:487`);
- the "Select model" button is **absent** (`:488`);
- "Select inference mode" and "Select retrieval source" are **absent**
  (`:489-494`);
- only the `composer-controls-strip` and the "Open composer actions" trigger
  remain (`:456-459`).

**Consequence for Gate 1 — this is the direct code-path candidate for "the
user could not reliably find/switch the active route".** On the compact phone
composer there is no visible provider/model affordance at all in conversation
presentation. Reachability depends on the actions menu. Note that the landing
posture behaves differently: `frontend/src/features/chat/components/Composer.tsx:371-372`
forces `isLandingControlsOpen` true when `compactMobile` is set, and the
neighboring test at `:497` asserts the landing inference controls stay mounted
but quiet until lower-edge reveal.

### E-16 — A stored provider preference is silently discarded when the provider is absent from the catalog

**Class:** `code-path`

`frontend/src/lib/providerPref.ts` — `reconcilePreferredProviderSelection`
clears the stored selection when the persisted provider id is not present in
the reconciled provider list, and clears the stored model when the persisted
model id is not present in that provider's models. `frontend/src/components/ProviderSelect.tsx:271`
filters the provider list to entries with `enabled` set.

**Consequence for Gate 1 — a second, distinct mechanism.** ADR-052's 2026-09-15
amendment permits a bounded compatibility fallback when DeepSeek model
discovery is degraded. If the catalog momentarily omits a provider, the
client-side preference can be reconciled away and the interface falls back to
a default provider — with no explicit signal to the user that a stored
selection was dropped.

**Limit of this evidence:** whether this fired during the operator's session is
**unproven**. It is a proven *mechanism* in code. Gate 1 must establish whether
it is reachable and observable before treating it as the cause.

### E-17 — A stored thread configuration overrides the requested provider/model at acceptance

**Class:** `code-path`

`guardian/core/chat_completion_service.py:3070-3100` — when the thread carries
a stored `thread_config`, the requested provider and model are discarded for
the effective provider; the thread config wins. `requested_*` is still
recorded, so `selection_source` remains `"explicit"`.

**Consequence for Gate 1:** a third divergence source, independent of E-16.
Because `selection_source` stays `"explicit"`, the worker still **rejects**
rather than substitutes. The divergence is a policy decision, not a silent
replacement.

---

## 6. Evidence register — explicit-model authority (external prerequisite)

### E-18 — Explicit unavailable models already fail closed, and are test-backed

**Class:** `code-path` + `unit-test` + `docs-only`

Backend gate: `guardian/workers/chat_worker.py:1588-1595` requires
`selection_source == "explicit"`, a non-empty `requested_model`, and no image
parts for the explicit-text-model path.

- Local path: `chat_worker.py:1659-1681` resolves with
  `requested_model_is_authoritative=True`; on failure it raises
  `HTTPException(400)` carrying `requested_provider`, `requested_model`,
  `selection_source`, `model_resolution`, and a `completion_truth` block with
  `accepted: True` and every other flag false, plus `visible_output_emitted=False`.
- Non-local path: `chat_worker.py:1682-1709` calls
  `validate_provider_model_selection`; an explicit invalid selection raises
  `LLMConfigError` (**fail closed**). The degraded fallback at
  `chat_worker.py:1427-1474` is reachable **only** for a non-explicit
  selection and only when the reason contains `"no chat-capable models"`.

Automated coverage: `tests/workers/test_chat_worker_explicit_model_authority.py:62`
(`test_unavailable_explicit_model_fails_before_execution_and_releases_lock`),
`:139` (`test_explicit_unavailable_model_never_calls_degraded_fallback`),
`:122`, `:132`; and
`guardian/tests/workers/test_chat_worker_provider_resolution.py:159, 192, 136`.

Live proof at HEAD:
`docs/architecture/proofs/supported-compose/2026-10-05-chat-unavailable-explicit-model-recovered-candidate.md`
— an explicit sentinel model produced exactly one `task.failed` with failure
kind `local_model_unavailable`, no substitute executed, and no assistant
persisted.

### E-19 — The explicit-model release item is open and externally owned

**Class:** `docs-only`

`docs/architecture/00-current-state.md:74` carries an **unchecked** release
item: *"An unavailable explicit model fails before provider execution and
cannot be silently substituted."* Supporting lines: `:46` ("Do not infer exact
unavailable-model rejection; the recorded complete Compose proof accepted work
with model substitution and no assistant fallback flag."), `:56`, and `:65`.

ADR-074 (`docs/architecture/adr/074-tester-provider-model-configuration-authority.md:84-86,
:92-98, :100-112`) establishes the fail-closed doctrine: Guardian must remain
fail closed; no Qwen-to-Gemma or Gemma-to-Qwen substitution is permitted.

**Ownership is recorded, not duplicated.** The task explicitly forbids
creating a competing implementation. Gate 1 records this as an external
prerequisite owned by the release track, and Gate 1's own scope is the mobile
interface's ability to *disclose* truth — not the backend contract.

### E-20 — Two sibling proof documents referenced by the lineage are absent at HEAD

**Class:** `code-path` (verified by `git cat-file -e HEAD:<path>`)

Absent at HEAD, present in history:

- `docs/architecture/proofs/supported-compose/2026-10-03-explicit-model-test-contradiction-reassessment.md`
- `docs/architecture/proofs/supported-compose/2026-10-03-main-explicit-model-fail-closed.md`

The retained Oct 5 candidate proof **is** present at HEAD. Recorded as a
documentation gap for the owning track (see D-03).

---

## 7. Evidence register — request observation and latency (symptom 5)

### E-21 — Observation loss is correctly reported as observation loss, not execution failure

**Class:** `code-path` + `unit-test`

`frontend/src/features/chat/components/ThreadAttemptObservation.tsx:220`
renders the literal string *"Response observation is unavailable. The request
outcome has not been changed."* The trigger is the `catch` at
`ThreadAttemptObservation.tsx:208-221` wrapping the
`GET /chat/threads/{threadId}/tasks` poll (`ThreadAttemptObservation.tsx:141-145`,
5s timeout) and the history sweep (`:165-169`). Any transport, timeout, auth,
or parse error sets the observation error while prior rows are retained and
polling continues (`:222-226`).

Test proof: `frontend/src/features/chat/components/__tests__/ThreadAttemptObservation.test.tsx:144-152`
asserts the string renders, that the status does **not** match `/failed|stopped/i`,
and that `api.post` is never called. `:249` covers retaining observation
uncertainty after a canonical refresh fails.

**Disposition:** the *message* is already correct. The reported symptom is
therefore about **visibility and distinctness on a phone**, not about the
message's wording. This finding narrows Gate 2's scope usefully.

### E-22 — The lifecycle diagnostic detail is hidden below the `sm` breakpoint

**Class:** `code-path`

`frontend/src/features/chat/components/InferenceStatusBanner.tsx:81` renders
the diagnostic `detail` inside a container classed
`"hidden truncate sm:inline"`. The `sm` breakpoint is 640px, so on a phone the
detail is not rendered at all.

The detail is the carrier of the canonical lifecycle distinctions. From
`frontend/src/features/chat/hooks/useInferenceRequestState.ts`:

| State | `statusText` | `detailText` | Source |
|---|---|---|---|
| queued | `INFERENCE_STATUS_TEXT.QUEUED` | `INFERENCE_DETAIL_TEXT.QUEUED` | `:540-546` |
| model warmup | `INFERENCE_STATUS_TEXT.WARMING_MODEL` | `INFERENCE_DETAIL_TEXT.WARMING_MODEL` | `:548-554` |
| awaiting first token | `INFERENCE_STATUS_TEXT.WAITING_FOR_FIRST_TOKEN` | `INFERENCE_DETAIL_TEXT.WAITING_FOR_FIRST_TOKEN` | `:556-562` |
| streaming | `INFERENCE_STATUS_TEXT.GENERATING` | `INFERENCE_DETAIL_TEXT.STREAMING` | `:564-570` |
| provider degraded | `INFERENCE_STATUS_TEXT.PROVIDER_DEGRADED` | degraded variants | `:89-96`, `:958-960` |
| stop unconfirmed | — | `"stop request could not be confirmed"` | `InferenceStatusBanner.tsx:52` |

**Consequence for Gate 2 — the direct code-path candidate for symptom 5.** The
interface already distinguishes "queued", "warming the model", "waiting for
the first token", "generating", and "degraded". On a phone, the label alone
("Working…", "Thinking…", "Replying…") is what the user sees, and the
distinguishing detail is not rendered. A slow local model and a stalled
transport are therefore not distinguishable on the device that reported the
problem.

### E-23 — The banner's own visibility predicate hides the queued state entirely

**Class:** `code-path`

`InferenceStatusBanner.tsx:11-20` — `isVisibleState` returns true for
`sending`, `thinking`, `streaming`, `failed`, `cancelled`, and a `completed`
state carrying latency metrics. A request whose lifecycle has not yet been
classified as one of `sending`/`thinking`/`streaming` renders **nothing**,
including the queued state.

**Consequence for Gate 2:** the banner's visibility rule and the detail's
breakpoint gating are two independent reasons a phone user cannot distinguish
a warming model from a stalled request. Both are in scope.

### E-24 — The backend emits a lifecycle timing chain, but no dispatch timestamp and no durable latency record

**Class:** `code-path`

Present in the worker event payload (`guardian/workers/chat_worker.py`):

| Timestamp | Lines |
|---|---|
| `queued_at` (from `task.created_at`) | `:2799-2806`, field list `:202-209` |
| `awaiting_model_at` | `:2828-2830` |
| `awaiting_first_token_at` | `:2831-2835` |
| `first_token_at` / `first_output_at` | `:2836-2846` |
| `completed_at` | `:259-260`, `:2847-2849` |
| `worker_started_at` | `:2789`, `:3209` — **not** in the lifecycle timing field list and **not** surfaced to the UI |

**Missing:**

- **Dispatch timestamp** (queue-accepted → worker pickup). A direct search for
  `dispatched_at|dispatch_at|picked_up_at|dequeued_at` returns no chat hit.
  `worker_started_at` exists but is not exposed, so the queue-wait interval
  cannot be reconstructed in the interface.
- **Model-warmup span** as a measured interval — only the single
  `awaiting_model_at` boundary exists.
- **Durable per-request latency columns.** A search of `guardian/db/migrations/**`
  for `latency|first_token|queued_at|dispatch|warmup` returns only unrelated
  tables (notably `62127ee9a537_add_inference_provider_state_tables.py:112`,
  `avg_latency_ms`, which is provider health, not per-request).

**Consequence for Gate 2:** a genuine instrumentation gap exists for the
queue-wait interval. Gate 2 must either ground the latency picture in the
timestamps that exist, or record the gap explicitly. It must **not** present
a guessed root cause for slow first-token responses.

### E-25 — Displayed latency can be client-clock approximation

**Class:** `code-path`

`frontend/src/features/chat/hooks/useInferenceRequestState.ts:836-853` —
when a lifecycle event lacks a timestamp, the client substitutes
`new Date().toISOString()`.

**Consequence for Gate 2:** any latency figure the phone shows may be
client-synthesized rather than server-derived. The interface must not present
a client approximation as a server measurement.

---

## 8. Discrepancies requiring reconciliation

These are recorded, not resolved. Each names its owner.

### D-01 — Branch-local proof shows fail-closed rejection; current-state says the complete Compose proof accepted substitution

**Owner:** release track (not this campaign)

`docs/architecture/proofs/supported-compose/2026-10-03-chat-unavailable-model-ui-truth.md`
and the retained Oct 5 candidate proof record an explicit unavailable model
rejected before execution. But `00-current-state.md:46` states the recorded
**complete** Compose proof accepted work with model substitution and no
assistant fallback flag, and `:74` carries the item as unchecked.

**Resolution path:** these may describe different profiles or request shapes —
the Oct 5 proof is explicitly "not a native model-picker or active browser
Send/Stop failure test". The campaign must not resolve this by assertion. It
is recorded as the external prerequisite in §9 and must be reconciled by the
owning track before release qualification.

### D-02 — The onboarding contract states a baseline limitation that no longer holds

**Owner:** Gate 4 (documentation correction, within the campaign's scope)

`docs/architecture/onboarding-and-tips-contract.md:43` states that
`config/supported_profiles/v1-whooshd-deepseek-web.yaml` contains an orphan
`=======` line and therefore cannot be loaded. **Verified false at the
baseline:** the file parses cleanly as YAML, and no `=======` line exists.
The repair landed in commit `3f4ba0034` ("Repair inherited backend profile and
auth fixtures").

The contract text is now stale. Gate 4 owns the correction because the
onboarding contract is in the same subject area and the correction is
one-line. No functional behavior depends on it.

### D-03 — Two explicit-model proof documents are referenced by lineage but absent at HEAD

**Owner:** release track

See E-20. The Oct 5 candidate proof is present and sufficient for the
fail-closed behavior; the two absent documents concern an earlier
reassessment and a main-branch fail-closed run. Recorded so the owning track
can decide whether they must be restored. Not this campaign's scope to
restore them.

### D-04 — The ADR index references ADR-052 by wikilink title, while the file carries an `ADR-` filename prefix

**Owner:** documentation hygiene (recorded, not fixed)

`docs/architecture/adr/adr-index.md` links
`[[ADR-052-Whoosh'd Gemma and Approved DeepSeek Startup Profile|...]]`, and
the file is `docs/architecture/adr/ADR-052-whooshd-deepseek-dual-provider-startup-profile.md`.
The link resolves by title, not by filename.

A second naming collision exists in the same directory:
`docs/architecture/adr/ADR-051-whooshd-deepseek-dual-provider-startup-profile.md`
carries the *same* slug as ADR-052, while `051-chrome-side-panel-dual-auth-client-contract.md`
holds the ADR-051 number.

**Disposition:** recorded. Renumbering or renaming ADRs is a governance change
with wide blast radius and is outside this campaign's authorized files. It is
deferred work, listed in §10.

---

## 9. External prerequisites and ownership

| Prerequisite | Owner | Evidence | Status |
|---|---|---|---|
| Explicit unavailable model must fail before provider execution, with no silent substitution | Release track | `00-current-state.md:74` (unchecked), ADR-074, Oct 5 proof (E-18, E-19) | Open, externally owned |
| Complete-Compose explicit-model contradiction (D-01) | Release track | `00-current-state.md:46` | Open, externally owned |
| Queue-wait (dispatch) timestamp not instrumented (E-24) | Runtime track | `chat_worker.py` timing field list | Open — Gate 2 may record, not invent |
| Missing explicit-model proof documents (D-03) | Release track | `git cat-file -e HEAD:<path>` | Open, externally owned |

**Rule:** where an existing campaign or track owns a prerequisite, this
campaign records the dependency and does not create a competing implementation.

---

## 10. Deferred work (not admitted into this campaign)

| Item | Reason | Suggested owner |
|---|---|---|
| Remove the dead legacy `frontend/src/components/chat/Composer.tsx` | Unrelated cleanup; no acceptance criterion depends on it | Runtime hygiene |
| Consume the declared-but-unused `mobileShellProfile.chat.composer.*` tokens | May be subsumed by Gate 3; decide there | Gate 3, if it falls out of scope |
| Resolve the ADR-051/ADR-052 filename collision (D-04) | Governance change with wide blast radius | Architecture |
| Restore or supersede the two absent explicit-model proofs (D-03) | Release track owns the explicit-model contract | Release track |
| Instrument a dispatch timestamp and durable per-request latency columns (E-24) | Schema/backend change; requires an independent decision | Runtime track |

---

## 11. Gate 0 validation performed

| Check | Result |
|---|---|
| Campaign documents inspected after authoring | Both files re-read for internal consistency |
| `git diff --check` (whitespace/conflict markers) | Clean — see §12 |
| `scripts/validate_docs.py` | Not applicable: it validates the `docs/architecture/` corpus and does not scan `docs/Campaign/` |
| `scripts/check_diagram_freshness.py` | Not applicable: no diagram sources changed |
| Repository documentation validation | None applies to `docs/Campaign/` additions |
| Automated runtime tests | None apply — Gate 0 is docs-only and changed no functional source |
| Frontend test runner availability | vitest 3.2.7 confirmed executable in the worktree (`frontend/node_modules` symlinked to the main checkout; `frontend/package.json` and `frontend/pnpm-lock.yaml` verified byte-identical to the main checkout) |
| Frontend test smoke | `ComposerSelectMenu.test.tsx` — 1 file passed, 2 tests passed. **Smoke only** — not a campaign acceptance proof |
| Issue #888 correspondence | Confirmed: title, campaign ID, and gate sequence match this register |
| Frozen execution sequence vs issue | Gate 0–5 sequence in the issue matches README §4 |

**Deliberately not claimed:** no device measurement, no browser emulation, no
live-runtime execution, and no full-suite run was performed in Gate 0. The
frontend smoke run above is a toolchain check and is labeled as such.

---

## 12. Gate 0 checkpoint

**Outcome:** complete.

**Files changed:** `docs/Campaign/mobile-experience-calibration/README.md`
(created), `docs/Campaign/mobile-experience-calibration/evidence.md` (created).

**ADR impact:** none. No ADR is added, amended, or retired. ADR-052 and
ADR-074 are read and cited, not modified.

**Preserved invariants:** unchanged — no functional source was touched.

**Commit:** the Gate 0 documentation commit —
`docs(campaign): define mobile experience calibration gates` — on branch
`feat/auto-20261023-5ef3356f`, baseline `b2907f828`, 2 files added, 1006
insertions, no functional source touched.

The commit hash is recorded in the Gate 0 checkpoint comment on Issue #888.
It is not written here because amending this register to embed its own hash
would change that hash.

**Tracking issue checkpoint:** posted to Issue #888.

**Outstanding blockers:** none for Gate 0. Four external prerequisites are
recorded in §9.

**Next atomic Task:** Gate 1 — provider/model selection and execution-truth
reconciliation on mobile. It is scoped against the allowlist in README §4 and
must narrow that list before implementation.
