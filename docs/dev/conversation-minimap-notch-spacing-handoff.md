# Tighten conversation minimap notch spacing

Workflow lane: standard

## Context

The conversation minimap ships in `main` (PR #956, then #964 for the
latest-follow and keyboard fixes). The rail is visible and usable, but the
**notches are spread too far apart** in the common case of a short or
medium-length thread. The owner supplied a MiniMax reference capture showing
the intended look: notches grouped into a tight cluster rather than distributed
across the full viewport height.

Why this is requested now: the minimap is already merged and in use, and the
spacing is the remaining visible gap between the shipped Codexify rail and the
reference interaction. The owner wants it corrected deliberately rather than
merged blind.

### Measured current behaviour (proven in live runtime)

Measured against the deployed Codexify chat at `air.codexify.space/chat/7507`
and reproduced locally in Chromium against `main` at a 1440x900 viewport with a
900px-tall transcript container.

The rail currently distributes notches across the **entire** container height:

| Turns | Notch pitch (CSS px) | Dash size (CSS px) |
| --- | --- | --- |
| 2 | 900 | 6 x 2 |
| 3 | 450 | 6 x 2 |
| 6 | 180 | 6 x 2 |
| 12 | 81.8 | 6 x 2 |

The first and last notches sit at the extreme edges of the container
(`-1px` and `899px` relative to the transcript container top), so the first
notch is partially clipped above the rail.

Live DOM confirms the shipped markup for a 3-turn thread: three
`[data-testid="conversation-minimap-mark"]` buttons, one marked
`data-active="true"` (`Turn 3, currently reading`), with the roving tabindex
from #964 (`tabindex="0"` on the first mark, `-1` on the rest).

### Measured reference geometry (from the supplied MiniMax capture)

Measured from `Screenshot 2026-11-25 at 10.41.04 AM.png` (284x340 capture).
The reference shows 5 notches with the active one highlighted in blue at the
top of the cluster:

| Notch | Row band | Pitch to next |
| --- | --- | --- |
| 1 (active, blue) | 94-98 | 29 |
| 2 | 123-127 | 28 |
| 3 | 151-156 | 29 |
| 4 | 180-185 | 29 |
| 5 | 209-214 | - |

Reference notch pitch is therefore ~28-29 px in capture pixels, and the
notches occupy a **compact cluster** spanning roughly 120px, not the full
capture height.

Note on scale: the reference capture is a zoomed crop at an unknown device
pixel ratio, so the ~29px pitch is a **relative** target, not an absolute CSS
value to copy. The capture proves the *shape* (tight, evenly pitched cluster)
and the *ratio* of pitch to notch height (roughly 6:1). It does not prove
MiniMax's internal layout algorithm.

### Root cause (code-path)

`frontend/src/features/chat/components/ConversationMinimap.tsx` positions each
notch as a percentage of the rail height:

```tsx
const position = markCount === 1 ? 50 : (index / (markCount - 1)) * 100;
// ...
style={{
  top: `${position}%`,
  height: `${100 / markCount}%`,
}}
```

With `markCount` notches the pitch is therefore `containerHeight / (markCount - 1)`,
which grows without bound as the thread gets shorter. This is the direct cause
of the 900px and 450px pitches above.

`frontend/src/features/chat/hooks/useConversationNavigation.ts` already
computes a density budget (`CONVERSATION_RAIL_MIN_MARK_SPACING = 12`,
`CONVERSATION_RAIL_MIN_MARKS = 4`, `CONVERSATION_RAIL_MAX_MARKS = 64`) and uses
it to decide how many **entries** to coalesce. That budget controls the count
of marks, not the distance between them, so it does not affect this symptom.

### Known constraints and non-goals

- The rail must stay stationary while the transcript scrolls, must not cover
  the composer, the latest-turn control, message actions, or the workspace, and
  must remain absent on phone viewports. Do not regress any of these.
- The preview, the committed jump, the single **Back to previous position**
  anchor, and the active-position tracking are all existing, merged, and
  covered by tests. This task changes **visual density only**.
- Not in scope: changing what a notch represents, adding a scrollbar-like
  proportional mapping if the bounded option is chosen, changing the density
  coalescing thresholds, or touching the preview contents.
- The backend pagination discrepancy noted in the post-merge review of #956 is
  unrelated and remains out of scope.

### Evidence posture

- Notch pitch, dash size, edge clipping, and the shipped DOM: **proven in live
  runtime** on the deployed Codexify chat, and reproduced locally in Chromium
  against `main`.
- Reference notch pitch and cluster shape: **measured from the supplied
  capture**, with the caveat above about capture scale.
- The specific layout algorithm to adopt: **open design decision** — see
  Goal.

## Goal

Make the notches sit close together, matching the reference's tight clustered
look, while keeping every loaded destination reachable and every existing
interaction intact.

Two viable approaches. The implementer should pick one and state the choice:

- **Option A — bounded proportional.** Keep the current percentage positioning
  but clamp the maximum pitch, so a short thread produces a tight cluster while
  a long thread still spans the rail. Position still encodes scroll position,
  but no longer linearly.
- **Option B — compact turn list.** Lay notches out at a fixed pitch
  (independent of thread length), matching the reference most literally.
  Position no longer encodes scroll position; the rail becomes a list of turns
  with one highlighted.

Either option must:

- keep the active notch visually distinct;
- keep notches in chronological order;
- keep every loaded destination reachable (a range preview must still expose
  its exact destinations);
- not push the first or last notch outside the visible rail.

This change belongs in
frontend/src/features/chat/components/ConversationMinimap.tsx

## Target files

```
Files:
- frontend/src/features/chat/components/ConversationMinimap.tsx
- frontend/src/features/chat/components/ConversationMinimap.module.css
- frontend/src/features/chat/hooks/useConversationNavigation.ts
- frontend/src/features/chat/__tests__/ConversationMinimap.test.tsx
- frontend/src/tests/playwright/conversation-minimap.spec.ts
- docs/dev/conversation-minimap.md
```

Discovery scope is limited to these files plus the existing minimap helpers in
`frontend/src/features/chat/conversationNavigation.ts`. If the implementation
requires changing the projection semantics in `conversationNavigation.ts`, say
so explicitly in the closeout before making that change — it is not authorised
by default.

## Acceptance criteria

- At a 900px-tall transcript container, the notch pitch is at most 32 CSS px
  for a 2-turn thread and at most 32 CSS px for a 3-turn thread. The current
  900px and 450px pitches are the failing baseline.
- The dash size stays at least 6 x 2 CSS px so a notch remains visible and
  hoverable.
- The first notch is fully visible: its top edge is not above the rail's
  visible top, and the last notch is not below the visible bottom. The current
  `-1px` top offset is the failing baseline.
- The active notch remains visually distinct from inactive notches.
- Notches remain in chronological order.
- Every loaded destination remains reachable: the dense-history range preview
  still exposes its exact destinations, and the range preview stays a bounded
  scrollable list.
- Hover and focus still open the preview without scrolling or fetching.
- A committed jump still reaches the correct stable message, and **Back to
  previous position** still restores the prior reading position, including
  after older messages are prepended.
- Keyboard operation is unchanged: the rail keeps its single tab stop,
  `Enter`/`Space` enters the preview for the focused mark's range, and
  `Escape` returns focus to the originating mark.
- Phone viewports still show no minimap and no hidden focusable controls.
- The existing phone, tablet-touch, reduced-motion, thread-switch, and
  prepending browser scenarios still pass unchanged.
- No new API calls and no new persistent state.
- The change is confined to presentation. It does not alter the projection
  semantics, message identity, canonical runtime tokens, or the UI token law.

## Validation

```
Validation:
- pnpm --dir frontend/src exec vitest run features/chat/__tests__/conversationNavigation.test.ts features/chat/__tests__/ConversationMinimap.test.tsx features/chat/__tests__/ChatView.navigation.test.tsx features/chat/__tests__/ChatView.loop-guards.test.tsx features/chat/__tests__/GuardianChat.message-pagination.test.tsx
- pnpm --dir frontend/src exec playwright test --config playwright.config.ts tests/playwright/conversation-minimap.spec.ts
- pnpm --dir frontend/src exec eslint features/chat/components/ConversationMinimap.tsx features/chat/components/ConversationMinimap.module.css features/chat/hooks/useConversationNavigation.ts
- pnpm --dir frontend/src exec tsc -p tsconfig.app.json --noEmit
- git diff --check
```

The Vitest command must report 75 or more passing tests with no failures. The
Playwright command must report 10 passing scenarios. The typecheck command must
not introduce any new errors beyond the repository's pre-existing baseline of
120 errors on `main` at `784bbc368` (verify by running the command on a clean
checkout and comparing counts; the number is a moving baseline, so the
comparison matters more than the figure).

A regression test must assert the bounded pitch directly, by reading the
rendered notch geometry rather than by asserting on a CSS string, so that a
future change cannot silently re-open the gap. The browser suite must gain a
scenario that measures the rendered pitch in a real browser.

Report environment limitations separately from failures. In a restricted local
runtime, Chromium may only launch with `--single-process`, and that build
cannot be reused across browser contexts, so each Playwright scenario may need
its own invocation to obtain a fresh browser. If that is needed, report it as
an environment limitation and report each scenario's individual result.

## Git add

```
git add frontend/src/features/chat/components/ConversationMinimap.tsx frontend/src/features/chat/components/ConversationMinimap.module.css frontend/src/features/chat/hooks/useConversationNavigation.ts frontend/src/features/chat/__tests__/ConversationMinimap.test.tsx frontend/src/tests/playwright/conversation-minimap.spec.ts docs/dev/conversation-minimap.md
```

## Git commit

```
git commit -m "fix(chat): tighten conversation minimap notch spacing"
```

## Expected closeout fields

- Summary of changes
- Files changed
- Validation results, or explicit `No automated runtime tests apply`
- Which option (A or B) was chosen, and why
- The measured notch pitch before and after, in CSS px, and the viewport used
- Git commit hash
- What Axis should add to his KB

Warnings must be reported separately from failures. Environment limitations must
not be presented as successful validation.

## Board metadata

- Lane: standard
- Priority: normal
- Owner: Codex
- Target status after completion: Ready for review
- Dependencies/blockers: none
- Review expectation: standard PR review

## Source evidence links

- docs/dev/conversation-minimap.md
- https://github.com/Resonant-Jones/Codexify/pull/956
- https://github.com/Resonant-Jones/Codexify/pull/964
- https://github.com/Resonant-Jones/Codexify/pull/956#issuecomment-6531717934
- frontend/src/features/chat/components/ConversationMinimap.tsx
- frontend/src/features/chat/hooks/useConversationNavigation.ts
