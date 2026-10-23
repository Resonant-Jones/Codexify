# Mobile Experience Calibration

**Campaign ID:** `CAMPAIGN-MOB-2026-10-23`
**Status:** Gate 0–2 complete — campaign frozen, execution order fixed
**Lane:** Architecture-impact (campaign governance and provider/runtime truth)
**Executor:** MiniMax, supervised and dependency-ordered
**Campaign owner:** Resonant Jones
**Tracking issue:** https://github.com/Resonant-Jones/Codexify/issues/888
**Evidence register:** [evidence.md](./evidence.md)
**Release effect:** None. The release gate remains `HOLD` per
[`00-current-state.md`](../../architecture/00-current-state.md). This campaign
does not change, narrow, or widen that status.

> **Campaign thesis:** Codexify already has a visually coherent mobile baseline.
> The remaining defect is that the mobile interface cannot tell the user the
> truth about *what is running*, *why it is slow*, and *what the app is asking
> of them*. Calibrate those three truths without touching the visual language.

---

## 1. Authority hierarchy

When sources disagree, resolve in this order and record the disagreement rather
than silently reconciling it.

1. [`docs/architecture/00-current-state.md`](../../architecture/00-current-state.md) — release truth.
2. Accepted ADRs in the [ADR index](../../architecture/adr/adr-index.md).
3. Domain contracts: [`onboarding-and-tips-contract.md`](../../architecture/onboarding-and-tips-contract.md),
   [`guardian-chat-portal.md`](../../architecture/guardian-chat-portal.md),
   [`chat-runtime-contract.md`](../../architecture/chat-runtime-contract.md),
   [`request-state-machine.md`](../../architecture/request-state-machine.md),
   [`providers.md`](../../architecture/providers.md),
   [`provider-capability-contract.md`](../../architecture/provider-capability-contract.md).
4. Repository Campaign registers and `docs/architecture/proofs/`.
5. This campaign register. It is an execution record, not an authority source.
6. GitHub Issue #888 — navigable progress index, never a substitute for the above.

### Governing domain facts (do not violate)

- `local` is the **provider/policy class**; `whooshd` is the **runtime identity**;
  `local-chat` is the **logical route**; physical model display metadata is
  **observation only** (`00-current-state.md:37`).
- `Whoosh'd` is **not** a provider to be invented. It is a runtime identity.
- Requested target and effective execution are **distinct facts** and must stay
  distinguishable.
- Observation loss is **not** execution failure.
- Guardian ownership, account scoping, provider policy, canonical tokens,
  message/attempt identity, and transcript integrity are preserved unchanged.

---

## 2. Evidence posture vocabulary

Every claim in this campaign carries one classification. A classification is
never upgraded by repetition.

| Class | Meaning |
|---|---|
| `code-path` | Read directly from source at a cited line. Proves what the code says, not what a user saw. |
| `unit-test` | Asserted by an executed automated test. Proves the assertion, not the runtime. |
| `browser-emulated` | Observed under viewport emulation. Not a real device. |
| `real-device` | Observed on physical hardware. |
| `live-runtime` | Observed against a running supported-Compose stack. |
| `docs-only` | Documented contract or recorded prior proof. Evidence maturity is stated, never assumed. |

Screenshots and user reports are **reported observations**, not proven causes.

---

## 3. The five reported problems, mapped to owning code

Each reported symptom is listed with the code that owns it and the evidence
class that currently applies. Full citations are in [evidence.md](./evidence.md).

| # | Reported symptom | Owning code | Current evidence |
|---|---|---|---|
| 1 | Onboarding content exceeds comfortable phone viewport | `frontend/src/features/onboarding/OnboardingWizard.tsx`, `onboarding.css` | `code-path` |
| 2 | Onboarding wording contains unnecessary technical language | `frontend/src/features/onboarding/onboardingContent.ts` | `code-path` |
| 3 | Floating composer sits too high, especially while typing | `frontend/src/features/chat/GuardianChat.tsx`, `AppShell.tsx`, `mobileShellProfile.ts` | `code-path` |
| 4 | Provider/model selection hard to discover or reconcile with execution | `frontend/src/features/chat/components/Composer.tsx`, `frontend/src/lib/providerPref.ts`, `guardian/core/llm_catalog.py` | `code-path` |
| 5 | Delayed local inference and degraded observation insufficiently distinguishable | `frontend/src/features/chat/components/InferenceStatusBanner.tsx`, `ThreadAttemptObservation.tsx` | `code-path` |

No symptom in this table has yet been reproduced on a device. Every Gate below
must state which of these three evidence classes its result carries.

---

## 4. Frozen gate sequence

Gates are sequential and dependency-ordered. Each gate produces exactly one
atomic Task Spec with an exact file allowlist, one narrow commit, and one
Issue #888 checkpoint. Gates do not run together.

| Gate | Objective | Class | Depends on |
|---|---|---|---|
| **0** | Source inspection, evidence register, campaign freeze | docs-only | — |
| **1** | Provider/model selection and execution-truth reconciliation | architecture-impact | Gate 0 | ✅ complete |
| **2** | Request-observation correctness and first-token latency diagnosis | architecture-impact | Gate 1 | ✅ complete |
| **3** | Mobile composer placement and keyboard-safe layout | standard | Gate 2 | next |
| **4** | Bounded onboarding pages, pagination, copy revision | standard | Gate 3 | |
| **5** | Mobile regression proof and campaign closeout | docs-only | Gate 4 | |

### Gate 0 — Source inspection, evidence register, campaign freeze

**Status:** complete. See [evidence.md §12.1](./evidence.md#121-gate-0--evidence-inventory-and-campaign-freeze).

**Objective.** Separate observed symptoms, code-proven behavior, documented
contracts, and unknowns. Identify task owners and overlapping campaigns.

**Authorized files (this gate, complete list).**

- `docs/Campaign/mobile-experience-calibration/README.md`
- `docs/Campaign/mobile-experience-calibration/evidence.md`

No functional source edits. No schema edits. No new dependencies.

**Acceptance.** Campaign register committed; Issue #888 carries the baseline
checkpoint; execution sequence frozen and identical in both places; existing
owners of prerequisites identified and recorded.

### Gate 1 — Provider/model selection and execution-truth reconciliation

**Status:** complete (`MOB-G1-TASK-1`). See [evidence.md §12.2](./evidence.md#122-gate-1--provider-model-selection-and-execution-truth-reconciliation).

**Objective.** Make the active provider/model route visible and truthful on a
phone, and reconcile *requested* against *effective* execution without creating
a parallel authority.

**Authorized files (as executed).**

- `frontend/src/features/chat/components/Composer.tsx`
- `frontend/src/features/chat/components/__tests__/Composer.mobile-route.test.tsx` (new)
- `frontend/src/components/persona/layout/__tests__/GuardianMobileComposerSingleSurface.test.tsx`
- `frontend/src/components/persona/layout/__tests__/GuardianMobileComposerCommands.test.tsx`

Backend files are **out of scope by default**. The explicit-model
fail-closed contract is already implemented, test-backed, and owned elsewhere
(`00-current-state.md:74`, ADR-074, and the 2026-10-05 proof). Gate 1 records
that ownership as an external prerequisite rather than duplicating it.

**Acceptance.** On a phone the active provider/model route is visible and
switchable; a selection that the runtime cannot serve is never silently
replaced; requested-vs-effective truth is displayed from authoritative fields;
no new provider, route, or authority is introduced.

### Gate 2 — Request-observation correctness and first-token latency diagnosis

**Status:** complete (`MOB-G2-TASK-1`). See [evidence.md §12.3](./evidence.md#123-gate-2--request-observation-correctness-and-first-token-latency-diagnosis).

**Objective.** Distinguish queueing, model warmup, generation, transport, and
durable terminal outcome in the interface — using only evidence that exists.

**Authorized files (as executed).**

- `frontend/src/features/chat/components/InferenceStatusBanner.tsx`
- `frontend/src/features/chat/ChatView.tsx`
- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/features/chat/components/__tests__/InferenceStatusBanner.phone-lifecycle.test.tsx` (new)

**Acceptance.** Observation loss is never presented as execution failure or
completion; request/attempt identity and transcript behavior are unchanged; the
latency picture either has an evidence-backed stage breakdown or is recorded as
an explicit instrumentation gap — never a guessed root cause.

### Gate 3 — Mobile composer placement and keyboard-safe layout

**Objective.** Calibrate the landing and active-thread composer postures so the
active composer sits near the bottom of the usable viewport and stays
keyboard-accessible.

**Authorized files (proposed).**

- `frontend/src/features/chat/GuardianChat.tsx`
- `frontend/src/components/persona/layout/mobileShellProfile.ts`
- `frontend/src/components/persona/layout/AppShell.tsx`
- `frontend/src/components/persona/layout/mobileBottomEdgeContract.ts`
- `frontend/src/components/persona/layout/__tests__/GuardianMobileComposerSingleSurface.test.tsx`
- `frontend/src/features/chat/__tests__/GuardianChat.session-shortcuts.test.tsx`

**Acceptance.** The active composer remains reachable with the iOS keyboard
open, across viewport changes and multiline drafts; drafts, focus, send/stop,
and attachments survive the posture change; desktop behavior does not regress;
`env(safe-area-inset-bottom)` and the measured keyboard inset reach the
composer through the canonical shell tokens rather than ad-hoc offsets.

### Gate 4 — Bounded onboarding pages, pagination, copy revision

**Objective.** Make ordinary onboarding pages fit a bounded phone viewport
without nested scrolling, and replace internal-contract language with
user-facing copy that keeps privacy and capability truth.

**Authorized files (proposed).**

- `frontend/src/features/onboarding/onboardingContent.ts`
- `frontend/src/features/onboarding/OnboardingWizard.tsx`
- `frontend/src/features/onboarding/onboarding.css`
- `frontend/src/features/onboarding/__tests__/Onboarding.test.tsx`

**Explicitly excluded.** `onboardingTypes.ts`, `onboardingApi.ts`,
`OnboardingProvider.tsx`, the backend onboarding route, and any persistence
schema. Pagination is **presentation-only**. The six semantic step keys, the
account-owned progress record, and the skip/resume/restart invariants are
preserved exactly.

**Acceptance.** Ordinary pages fit a bounded phone viewport without nested
scrolling; Back/Continue/Skip/Resume and screen-reader usability are intact;
username remains optional and its claim semantics are unchanged; deeper
explanatory copy moves to Tips rather than being deleted; no username-edit
route is invented.

### Gate 5 — Mobile regression proof and campaign closeout

**Objective.** Revalidate every campaign acceptance criterion and separate
proven outcomes from unresolved limitations.

**Authorized files (proposed).**

- `docs/Campaign/mobile-experience-calibration/README.md`
- `docs/Campaign/mobile-experience-calibration/evidence.md`

Tests are executed against the committed implementation; no product source is
edited in this gate.

---

## 5. Preserved invariants

Every Task in this campaign must leave all of the following unchanged, or stop
and escalate:

- Guardian ownership of chat execution and provider policy.
- Account scoping: API input never supplies authority.
- Canonical UI tokens; no ad-hoc color, radius, or spacing values where a token
  exists.
- Message identity vs request identity vs attempt identity (ADR-003).
- Transcript integrity across observation loss, refresh, and reload.
- Provider/runtime truth: class, runtime identity, logical route, and physical
  display metadata stay distinguishable.
- The removed mobile Session rail and current FrameCard styling.
- Existing desktop shell behavior.
- The six-step onboarding progress semantics and optional username semantics.
- The release gate status (`HOLD`) and the authority of `00-current-state.md`.

---

## 6. Non-goals

- No broad UI redesign and no FrameCard replacement.
- No new provider framework and no new provider identity.
- No unrelated runtime refactoring.
- No automatic deployment, push, merge, or release promotion.
- No new onboarding persistence schema without an independent architecture
  decision.
- No unrelated feature development.
- No parallel campaign management system and no autonomous architectural
  decision-making.
- No release-readiness claim derived from issue checklists or documentation.

---

## 7. Execution discipline

For each gate:

1. Inspect the current implementation and identify the owning component and
   its tests.
2. Choose the smallest independently provable change.
3. Write exactly one atomic Task Spec with exact file boundaries.
4. Classify it `standard` or `architecture-impact`.
5. Implement only the authorized scope.
6. Run the relevant tests and collect evidence with a stated class.
7. Review the diff and stage only owned files — never `git add .`.
8. Commit the completed task.
9. Record results and deferred work in [evidence.md](./evidence.md).
10. Post one progress checkpoint to Issue #888.
11. Link commits, PRs, proof results, and blockers.

Never invent proof. Never mark an unrun test as passed. Never silently mark a
blocked gate complete.

### Stop conditions

Stop the affected scope and escalate when any of these is required:

- an unapproved ADR change;
- an unsafe authority change or a second parallel authority;
- an unresolved contract contradiction between repository sources;
- missing authorization;
- an incompatible concurrent change.

---

## 8. Stop rule and closeout

The campaign ends when every in-scope gate is proven, or when the remaining
scope is blocked by an external owner whose prerequisite is recorded and
linked. It does not reopen for additional feature ideas.

At closeout: revalidate every acceptance criterion; separate proven outcomes
from unresolved limitations; confirm the register carries complete evidence
links; reconcile every gate's status with Issue #888; publish a final closeout
comment; list deferred work without admitting it into the completed campaign;
and leave release qualification unchanged unless separately proven and
authorized through the governing release process.

---

## 9. Related reading

- [Evidence register](./evidence.md)
- [Guardian Chat Portal](../../architecture/guardian-chat-portal.md)
- [Account onboarding and Tips contract](../../architecture/onboarding-and-tips-contract.md)
- [Chat runtime contract](../../architecture/chat-runtime-contract.md)
- [Request state machine](../../architecture/request-state-machine.md)
- [Inference providers](../../architecture/providers.md)
- [ADR-074 — Tester Provider / Model Configuration Authority](../../architecture/adr/074-tester-provider-model-configuration-authority.md)
- [ADR-052 — Whoosh'd Gemma and Approved DeepSeek Startup Profile](../../architecture/adr/ADR-052-whooshd-deepseek-dual-provider-startup-profile.md)
