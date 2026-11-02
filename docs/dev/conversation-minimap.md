# Conversation Minimap

Status: implemented in the `feat/auto-20261028-6442aaff` worktree.
Not released, not merged, not deployed. No release claim is made by this document.

The minimap is a narrow navigation rail that sits against the left edge of the
Guardian chat transcript. It projects the transcript that is **already loaded**
into navigable turns so a reader can inspect and revisit earlier sections
without losing their reading position.

It is a read-only projection of what the transcript already renders. It is not
a server-side thread index.

## Files

| File | Role |
| --- | --- |
| `frontend/src/features/chat/conversationNavigation.ts` | Pure projection: message order to navigable sections, plus density grouping. No React, no DOM. |
| `frontend/src/features/chat/hooks/useConversationNavigation.ts` | Geometry, active-section tracking, jump, return anchor, and density budget. |
| `frontend/src/features/chat/components/ConversationMinimap.tsx` | The rail and the preview surface, including keyboard and touch behaviour. |
| `frontend/src/features/chat/components/ConversationMinimap.module.css` | Token-driven layout for the rail and preview. |
| `frontend/src/features/chat/ChatView.tsx` | Owns the transcript, the scroll container, and the anchor attributes the navigation reads. |
| `frontend/src/features/chat/hooks/useChatAutoScroll.ts` | Auto-scroll now exposes a cancel handle and honours a follow-latest flag. |

## Implemented interaction

### Sections

A section is opened by a user-authored message and is anchored to that
message's stable identity. Assistant messages that follow are projected into
the open section and appear in the preview. The projection is deliberately
literal about what it knows:

- Consecutive user messages produce separate sections.
- A user message with no assistant reply is a complete section on its own.
- A loaded window that begins with an assistant message anchors on that
  message. No user turn is invented for it.
- Tool events, hidden context, and streaming drafts are never destinations.
- Array positions are never used as navigation identity, so prepending older
  history does not renumber the turns that were already there.

Grouping is a rendered-order observation. It does not assert request-attempt
linkage or completion status (see `docs/architecture/adr/003-message-identity-vs-request-identity.md`).

### Preview content

The preview renders plain text and attachment labels only. Message text is
passed through the shared document-context parser, so hidden document bodies
never leak into the preview. No rich-message renderer, generated UI, remote
image, audio, or executable content is mounted into the preview.

### Rail and preview

The rail is positioned at the left edge of the transcript viewport and stays
stationary while the transcript scrolls. It appears only when the transcript
overflows and more than one section exists.

- Pointer hover or keyboard focus opens a bounded, non-modal preview.
- Previewing never scrolls the transcript and never fetches messages.
- Clicking a pointer-selected destination commits the jump.
- On touch input a tap opens the preview, and the separate **Go to turn**
  action commits the navigation.
- `Escape` and any outside interaction dismiss the preview.
- The rail is one composite widget: a single mark sits in the tab order and the
  arrow keys move between them. A dense history would otherwise put dozens of
  marks in the tab order and make the preview unreachable.
- `Enter` or `Space` on a mark enters the preview for that exact range and
  moves focus onto its destinations, so a keyboard-only reader can activate an
  exact destination without tabbing through the remaining rail marks (each of
  which would replace the preview on the way). `Escape` inside the preview
  returns focus to the mark the preview was opened from.
- Focus is visible and there is no focus trap. The preview stays usable when
  the pointer leaves the rail and enters the preview.

### Dense histories

The rail is bounded by the available viewport height, and the number of
independent marks is bounded by that height. When a history has more sections
than the rail can hold, contiguous sections are coalesced into a range. A range
preview lists its exact destinations in a bounded scrollable list, so no
loaded section becomes unreachable. Chronological order is preserved, and the
active reading section is visually distinct from the destination currently
being previewed.

### Scroll ownership and return navigation

Only the existing transcript scroll container is scrolled. The document body
is never scrolled by navigation.

The active section is derived from real message geometry. The scroll handler
resolves the active section with a binary search over cached anchor positions
inside a single animation frame, so the transcript is never scanned on a raw
scroll event.

Before a committed jump the previous message anchor and its relative viewport
offset are retained. One **Back to previous position** action restores it.
Repeated jumps do not replace the original return point, and the anchor
survives older messages being prepended, because the anchor is an identity and
the content offset is re-read from the live DOM at restore time.

A committed jump intentionally leaves the latest turn: pending auto-scroll
work is cancelled and the follow-latest intent is cleared, so streaming updates
and incoming messages do not pull the reader back down. The existing **Jump to
latest** action restores normal latest-follow behaviour.

Latest-follow is driven by *intent*, not by the measured distance from the
bottom. Appending a reply grows the transcript, which makes that distance look
large even though the reader never moved, so the two are tracked separately:
only an explicit navigation may clear the follow-latest intent, and returning
to the bottom restores it.

If a destination has been removed, the jump fails safely and does not land on
an unrelated message. Preview state, the return position, observers, and
scheduled callbacks are cleared on a thread change and on unmount. Reduced
motion is respected.

### Responsive behaviour

| Viewport | Behaviour |
| --- | --- |
| Desktop | Full pointer and keyboard interaction. |
| Wide tablet | Enabled only when the chat container itself has sufficient room. Touch input opens the preview and commits through **Go to turn**. |
| Phone | No minimap, no replacement scrubber, and no hidden focusable controls. |

The rail does not cover the composer, the latest-turn control, message
actions, or the workspace. If the navigator is hidden after a resize, its
preview is dismissed and focus is released.

### Loaded-history limitation

When the supplied history state still has older messages to load, the preview
is labelled **Loaded history**. The existing pagination control is retained and
still works.

The minimap never promises a jump to a turn that has not been loaded. It does
not auto-fetch all history and it does not add a second fetching path.
Prepending newly loaded messages updates the projection without losing the
reading anchor.

## Test commands

Run from the repository root.

```bash
pnpm --dir frontend/src exec vitest run \
  features/chat/__tests__/conversationNavigation.test.ts \
  features/chat/__tests__/ConversationMinimap.test.tsx \
  features/chat/__tests__/ChatView.navigation.test.tsx \
  features/chat/__tests__/ChatView.loop-guards.test.tsx \
  features/chat/__tests__/GuardianChat.message-pagination.test.tsx
```

```bash
pnpm --dir frontend/src exec playwright test \
  --config playwright.config.ts \
  tests/playwright/conversation-minimap.spec.ts
```

```bash
git diff --check
```

The browser suite needs the Playwright Chromium build:

```bash
pnpm --dir frontend/src exec playwright install chromium
```

### Browser execution note

In a restricted local runtime, Chromium can only be launched with
`--single-process`, and that build cannot be reused across browser contexts:
the browser process is torn down when a context closes, so a single
`playwright test` invocation reports spurious
`browserContext.newPage: Target page, context or browser has been closed`
failures for the tests that follow the first one. Running each test in its
own invocation gives a fresh browser and every test passes.

That is a property of the constrained browser build, not of this change. The
suite is written for the repository's normal `playwright.config.ts`, which
launches Chromium with its default arguments.

## Proof limits

- The unit suites are jsdom. They prove projection rules, preview behaviour,
  jump and return semantics, and the absence of a second fetching path. They
  cannot prove layout.
- The Playwright suite mounts the real `ChatView` and the real
  `ConversationMinimap` in Chromium against synthetic messages, served from the
  Vite dev server origin. It proves the stationary rail, real message
  geometry, coalesced dense marks, pointer-versus-touch input, reduced
  motion, prepending, streaming updates, and phone absence. Screenshots of the
  rail and of an open preview are written to `frontend/src/screenshots/`.
- The synthetic page calls the application's own `injectCssVars()` and copies
  the React plugin preamble out of the development index document. Without
  both, the rail has no token-derived width and the React plugin refuses to
  evaluate a component module.
- Every browser observation uses synthetic fixtures. There is no recorded
  traffic, no live backend, and no live runtime in this proof. This is
  interface evidence, not release qualification for a supported runtime.
- The pagination discrepancy observed previously in the backend is unchanged.
  It stays a separately revalidated dependency for future whole-thread
  navigation and was not touched here.
- No ADR was added. The change stays inside the existing contracts: the
  canonical runtime tokens, the UI token law, and the message/attempt identity
  boundary are unchanged.

## Not covered

- Direct navigation to unloaded turns.
- Server-side turn indexing or backend pagination repair.
- Summaries, embeddings, semantic search, bookmarks, or conversation branches.
- Any new identity, memory, persistence, authority, or execution semantics.
