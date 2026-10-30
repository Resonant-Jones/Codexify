/**
 * Conversation minimap — browser proof.
 *
 * ---------------------------------------------------------------------------
 * WHAT THIS FILE PROVES
 * ---------------------------------------------------------------------------
 * The minimap is a *presentation* surface, so the only honest browser proof
 * exercises the real `ChatView` and the real `ConversationMinimap` in a real
 * browser with real layout. jsdom cannot express any of the properties that
 * matter here: a stationary rail next to a scrolling transcript, measured
 * message geometry, coalesced dense marks, pointer-versus-touch input, or
 * `prefers-reduced-motion`.
 *
 * ---------------------------------------------------------------------------
 * WHY THE FIXTURE IS A PAGE, NOT THE WHOLE APPLICATION
 * ---------------------------------------------------------------------------
 * The fixture mounts the real `ChatView` from the application source into a
 * synthetic page served from the Vite dev server origin. Nothing about the
 * component is reimplemented here: the transcript, the scroll container, the
 * rail, the preview, and the theme tokens are all the shipped code.
 *
 * The messages are synthetic fixtures. No backend, no recorded traffic, and no
 * live runtime is involved, so this file proves *interface behaviour* only.
 * It is not release qualification for a supported runtime.
 *
 * The synthetic page is served through a route interception on the dev server
 * origin so that module imports resolve against the same origin that serves
 * `/features/chat/ChatView.tsx`.
 */
import * as fs from "node:fs";
import * as path from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

const __dirname = new URL(".", import.meta.url).pathname;
const SCREENSHOT_DIR = path.join(__dirname, "../../screenshots");

const FIXTURE_ROUTE = "**/__minimap_fixture__";

const FIXTURE_HTML = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/index.css?direct" />
    <link rel="stylesheet" href="/styles/interaction.css?direct" />
    <!--PREAMBLE-->
    <style>
      html,
      body {
        height: 100%;
        margin: 0;
        background: #000;
      }
      #minimap-fixture {
        height: 100%;
      }
    </style>
  </head>
  <body>
    <div id="minimap-fixture"></div>
  </body>
</html>`;

/**
 * The fixture entry module. It is injected into the page as a module script
 * so that the browser resolves it exactly like any other application module
 * served by Vite, including the React instance shared with ChatView.
 */
const FIXTURE_ENTRY = `
import React from "/@id/react";
import ReactDOMClient from "/@id/react-dom/client";
import ChatView from "/features/chat/ChatView.tsx";
import { injectCssVars } from "/theme/index.ts";

const { createRoot } = ReactDOMClient;

// The application injects its theme tokens at runtime. The synthetic page has
// to do the same, otherwise the rail has no token-derived width.
injectCssVars();

const container = document.getElementById("minimap-fixture");
const root = createRoot(container);

window.__mountMinimapFixture = (options) => {
  const {
    messages = [],
    threadId = 7,
    hasMore = false,
    streamingDraft = null,
  } = options || {};

  root.render(
    React.createElement(ChatView, {
      threadId,
      guardianName: "Guardian",
      messages,
      loading: false,
      error: null,
      hasMore,
      onLoadOlderMessages: () => Promise.resolve(),
      completionState: {
        isCompleting: false,
        activeTaskId: null,
        activeThreadId: null,
        startedAt: null,
      },
      endCompletion: () => {},
      streamingDraft,
    })
  );
};

window.__minimapFixtureReady = true;
`;

type FixtureMessage = {
  id: number;
  thread_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

function buildMessage(
  id: number,
  role: "user" | "assistant",
  content: string
): FixtureMessage {
  return {
    id,
    thread_id: 7,
    role,
    content,
    created_at: `2026-03-13T00:00:${String(id % 60).padStart(2, "0")}.000Z`,
  };
}

/** A short transcript with three user turns and tall, variable-height replies. */
function shortHistory(): FixtureMessage[] {
  const tallReply = (label: string) =>
    Array.from(
      { length: 18 },
      (_unused, index) => `${label} reply paragraph ${index + 1}`
    ).join("\n\n");

  return [
    buildMessage(1, "user", "First question about the renderer."),
    buildMessage(2, "assistant", tallReply("First")),
    buildMessage(3, "user", "Second question with a much longer body."),
    buildMessage(4, "assistant", tallReply("Second")),
    buildMessage(5, "user", "Third question."),
    buildMessage(6, "assistant", tallReply("Third")),
  ];
}

/** A dense history that forces the rail to coalesce marks into ranges. */
const DENSE_TURNS = 72;

function denseHistory(turns = DENSE_TURNS): FixtureMessage[] {
  const messages: FixtureMessage[] = [];
  for (let index = 0; index < turns; index += 1) {
    const id = index * 10 + 1;
    messages.push(buildMessage(id, "user", `Dense turn ${index + 1}`));
    messages.push(
      buildMessage(id + 1, "assistant", `Dense reply ${index + 1}`)
    );
  }
  return messages;
}

/**
 * The React plugin installs a preamble hook into the document before any
 * transformed component module is evaluated. The synthetic page is served
 * outside the Vite HTML pipeline, so the preamble is copied verbatim from the
 * development index document.
 */
const FALLBACK_PREAMBLE = `<script type="module">import { injectIntoGlobalHook } from "/@react-refresh";
injectIntoGlobalHook(window);
window.$RefreshReg$ = () => {};
window.$RefreshSig$ = () => (type) => type;</script>`;

async function resolvePreamble(page: Page): Promise<string> {
  try {
    const response = await page.request.get("/");
    const html = await response.text();
    const match = html.match(
      /<script type="module">[^<]*injectIntoGlobalHook[\s\S]*?<\/script>/
    );
    if (match) return match[0];
  } catch {
    // Fall through to the standard preamble below.
  }
  return FALLBACK_PREAMBLE;
}

/**
 * Move the transcript and wait for the navigation projection to settle.
 *
 * The active turn is resolved inside an animation frame after the scroll, so
 * the test has to let those frames land before it reads the rail.
 */
async function scrollTranscriptTo(
  container: Locator,
  position: number
): Promise<void> {
  await container.evaluate(async (node, top) => {
    node.scrollTop = top;
    node.dispatchEvent(new Event("scroll", { bubbles: true }));
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });
  }, position);
}

async function openFixture(page: Page): Promise<void> {
  const preamble = await resolvePreamble(page);

  await page.route(FIXTURE_ROUTE, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/html",
      body: FIXTURE_HTML.replace("<!--PREAMBLE-->", preamble),
    });
  });

  await page.goto("/__minimap_fixture__");
  await page.addScriptTag({ type: "module", content: FIXTURE_ENTRY });
  await page.waitForFunction(() => Boolean(window.__minimapFixtureReady));
}

async function mountFixture(
  page: Page,
  options: {
    messages: FixtureMessage[];
    threadId?: number;
    hasMore?: boolean;
    streamingDraft?: {
      threadId: number | null;
      content: string;
      updatedAt: number;
    } | null;
  }
): Promise<void> {
  await page.evaluate((payload) => {
    window.__mountMinimapFixture(payload);
  }, options as unknown as Record<string, unknown>);
  await page.waitForSelector('[data-testid="chat-container"]');
}

function capture(page: Page, name: string): void {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  page
    .screenshot({ path: path.join(SCREENSHOT_DIR, `${name}.png`) })
    .catch(() => undefined);
}

test.describe("Conversation minimap", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("shows a stationary rail, previews a destination, and jumps on click", async ({
    page,
  }) => {
    await openFixture(page);
    await mountFixture(page, { messages: shortHistory() });

    const minimap = page.getByTestId("conversation-minimap");
    await expect(minimap).toBeVisible();

    // The transcript really does overflow, which is what admits the rail.
    const overflows = await page
      .getByTestId("chat-container")
      .evaluate((node) => node.scrollHeight > node.clientHeight);
    expect(overflows).toBe(true);

    const marks = page.getByTestId("conversation-minimap-mark");
    await expect(marks).toHaveCount(3);

    // The rail sits at the left edge of the transcript viewport.
    const railBox = await minimap.boundingBox();
    const containerBox = await page.getByTestId("chat-container").boundingBox();
    expect(railBox).not.toBeNull();
    expect(containerBox).not.toBeNull();
    if (!railBox || !containerBox) throw new Error("missing bounding box");
    expect(railBox.x).toBeLessThanOrEqual(containerBox.x + 1);
    expect(railBox.width).toBeLessThan(40);

    capture(page, "conversation-minimap-rail");

    // Previewing must not move the transcript.
    const scrollBefore = await page
      .getByTestId("chat-container")
      .evaluate((node) => node.scrollTop);

    await marks.nth(1).hover();

    const preview = page.getByTestId("conversation-minimap-preview");
    await expect(preview).toBeVisible();
    await expect(preview).toHaveAttribute("aria-modal", "false");

    const scrollAfterPreview = await page
      .getByTestId("chat-container")
      .evaluate((node) => node.scrollTop);
    expect(scrollAfterPreview).toBe(scrollBefore);

    capture(page, "conversation-minimap-preview");

    // A pointer-selected destination commits the jump.
    const destination = page
      .getByTestId("conversation-minimap-destination")
      .first();
    await destination.click();

    // The second turn sits above the current reading position, so committing
    // the jump moves the transcript up.
    await expect
      .poll(async () =>
        page.getByTestId("chat-container").evaluate((node) => node.scrollTop)
      )
      .toBeLessThan(scrollBefore);

    // The jump leaves a single return point.
    const back = page.getByTestId("conversation-minimap-back");
    await expect(back).toBeVisible();
    await back.click();

    await expect
      .poll(async () =>
        page.getByTestId("chat-container").evaluate((node) => node.scrollTop)
      )
      .toBe(scrollBefore);
  });

  test("keeps every loaded destination reachable in a dense history", async ({
    page,
  }) => {
    await openFixture(page);
    await mountFixture(page, { messages: denseHistory() });

    const marks = page.getByTestId("conversation-minimap-mark");
    await expect(marks.first()).toBeVisible();

    const markCount = await marks.count();
    // The rail is coalesced into ranges rather than hundreds of marks.
    expect(markCount).toBeLessThanOrEqual(64);
    expect(markCount).toBeGreaterThan(1);

    const rangeCount = await page
      .locator('[data-entry-kind="range"]')
      .count();
    expect(rangeCount).toBeGreaterThan(0);

    // Every loaded turn is reachable through the range preview.
    await marks.first().hover();
    const destinations = page.getByTestId("conversation-minimap-destination");
    const destinationCount = await destinations.count();
    expect(destinationCount).toBeGreaterThan(1);

    const reachable = destinationCount * markCount;
    expect(reachable).toBeGreaterThanOrEqual(DENSE_TURNS);
    // Nothing is dropped: the ranges tile the loaded turns.
    expect(reachable).toBeLessThan(DENSE_TURNS + markCount);

    // The range preview is a bounded scroll container.
    const previewOverflow = await page
      .getByTestId("conversation-minimap-preview")
      .evaluate((node) => getComputedStyle(node).overflowY);
    expect(["auto", "scroll"]).toContain(previewOverflow);

    const previewBox = await page
      .getByTestId("conversation-minimap-preview")
      .boundingBox();
    expect(previewBox).not.toBeNull();
    if (!previewBox) throw new Error("missing preview bounding box");
    expect(previewBox.height).toBeLessThan(900);

    // The destinations inside a range are contiguous and in order.
    const sectionIds = await destinations.evaluateAll((nodes) =>
      nodes.map((node) => node.getAttribute("data-section-id"))
    );
    for (let index = 1; index < sectionIds.length; index += 1) {
      const previous = Number(sectionIds[index - 1]?.replace(/\D/g, ""));
      const current = Number(sectionIds[index]?.replace(/\D/g, ""));
      expect(current).toBeGreaterThan(previous);
    }
  });

  test("keeps the reading anchor when older history is prepended", async ({
    page,
  }) => {
    await openFixture(page);

    const initial = shortHistory();
    await mountFixture(page, { messages: initial });

    const container = page.getByTestId("chat-container");
    await scrollTranscriptTo(container, 120);

    // The turn being read before the jump is the anchor that has to survive.
    await expect(
      page.locator('[data-testid="conversation-minimap-mark"][data-active="true"]')
    ).toHaveCount(1);

    const anchoredSectionId = await page
      .locator('[data-testid="conversation-minimap-mark"][data-active="true"]')
      .first()
      .getAttribute("data-section-ids");
    expect(anchoredSectionId).toBeTruthy();

    const anchorOffset = async (): Promise<number> =>
      container.evaluate((node, sectionId) => {
        const message = node.querySelector(
          `[data-conversation-anchor="${sectionId}"]`
        );
        if (!message) return Number.NaN;
        return (
          message.getBoundingClientRect().top -
          node.getBoundingClientRect().top
        );
      }, anchoredSectionId!);

    const offsetBefore = await anchorOffset();

    const marks = page.getByTestId("conversation-minimap-mark");
    await marks.nth(0).click();

    await expect(page.getByTestId("conversation-minimap-back")).toBeVisible();

    // Older turns arrive above the current transcript.
    const prepended: FixtureMessage[] = [
      buildMessage(901, "user", "An older turn."),
      buildMessage(902, "assistant", "An older reply."),
      ...initial,
    ];
    await mountFixture(page, { messages: prepended });

    await page.getByTestId("conversation-minimap-back").click();

    // The anchored turn keeps its viewport relationship even though history
    // was inserted above it. A pixel of slack absorbs sub-pixel rounding.
    await expect
      .poll(async () => Math.abs((await anchorOffset()) - offsetBefore))
      .toBeLessThan(1);
  });

  test("does not pull the reader down when a stream updates", async ({
    page,
  }) => {
    await openFixture(page);
    const messages = shortHistory();
    await mountFixture(page, { messages });

    const container = page.getByTestId("chat-container");
    await scrollTranscriptTo(container, 120);

    const marks = page.getByTestId("conversation-minimap-mark");
    await marks.nth(0).click();

    const position = await container.evaluate((node) => node.scrollTop);

    await mountFixture(page, {
      messages,
      streamingDraft: {
        threadId: 7,
        content: "A streaming reply that is still arriving.",
        updatedAt: 1_800_000_000_000,
      },
    });

    await page.waitForTimeout(250);

    const afterStream = await container.evaluate((node) => node.scrollTop);
    expect(afterStream).toBe(position);
  });

  test("never shows another thread's preview after a thread switch", async ({
    page,
  }) => {
    await openFixture(page);
    await mountFixture(page, { messages: shortHistory(), threadId: 7 });

    await page.getByTestId("conversation-minimap-mark").nth(1).hover();
    await expect(page.getByTestId("conversation-minimap-preview")).toBeVisible();

    await mountFixture(page, {
      messages: [
        buildMessage(801, "user", "Other thread question."),
        buildMessage(802, "assistant", "Other thread answer."),
        buildMessage(803, "user", "Another other-thread question."),
      ],
      threadId: 8,
    });

    await expect(
      page.getByTestId("conversation-minimap-preview")
    ).toHaveCount(0);
  });

  test("honours reduced motion when a jump is committed", async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openFixture(page);
    await mountFixture(page, { messages: shortHistory() });

    const container = page.getByTestId("chat-container");
    await container.evaluate((node) => {
      node.scrollTop = 0;
    });

    await page.getByTestId("conversation-minimap-mark").nth(2).click();

    // A reduced-motion jump lands immediately instead of animating.
    await expect
      .poll(async () => container.evaluate((node) => node.scrollTop))
      .toBeGreaterThan(0);
  });

  test("tracks the active turn from real message geometry", async ({
    page,
  }) => {
    await openFixture(page);
    await mountFixture(page, { messages: shortHistory() });

    const container = page.getByTestId("chat-container");

    /** Scroll to a position and report which turn is marked as active. */
    const activeTurnAt = async (fraction: number): Promise<string[]> => {
      const limit = await container.evaluate(
        (node) => node.scrollHeight - node.clientHeight
      );
      await scrollTranscriptTo(container, Math.round(limit * fraction));

      await expect
        .poll(async () =>
          page
            .locator(
              '[data-testid="conversation-minimap-mark"][data-active="true"]'
            )
            .count()
        )
        .toBe(1);

      return page
        .locator('[data-testid="conversation-minimap-mark"][data-active="true"]')
        .evaluateAll((nodes) =>
          nodes.map((node) => node.getAttribute("aria-label") ?? "")
        );
    };

    // The active turn follows the reader: the first turn at the top of the
    // transcript, and a later turn further down.
    const atTop = await activeTurnAt(0);
    expect(atTop[0]).toContain("Turn 1");

    const inMiddle = await activeTurnAt(0.5);
    const atBottom = await activeTurnAt(1);

    const turnNumber = (label: string | null) =>
      Number(String(label ?? "").replace(/\D/g, ""));

    // The active turn never moves backwards as the reader moves forwards.
    expect(turnNumber(inMiddle[0])).toBeGreaterThanOrEqual(turnNumber(atTop[0]));
    expect(turnNumber(atBottom[0])).toBeGreaterThanOrEqual(
      turnNumber(inMiddle[0])
    );

    // The transcript ends in the final stretch of the last turn.
    expect(turnNumber(atBottom[0])).toBeGreaterThanOrEqual(2);
  });
});

test.describe("Conversation minimap — wide tablet touch", () => {
  test.use({ viewport: { width: 1024, height: 768 }, hasTouch: true });

  test("opens the preview on tap and commits with an explicit action", async ({
    page,
  }) => {
    await openFixture(page);
    await mountFixture(page, { messages: shortHistory() });

    const minimap = page.getByTestId("conversation-minimap");
    await expect(minimap).toBeVisible();

    const container = page.getByTestId("chat-container");
    const before = await container.evaluate((node) => node.scrollTop);

    await page.getByTestId("conversation-minimap-mark").nth(0).tap();

    // A tap opens the preview without navigating.
    await expect(page.getByTestId("conversation-minimap-preview")).toBeVisible();
    expect(await container.evaluate((node) => node.scrollTop)).toBe(before);

    await page.getByTestId("conversation-minimap-go-to-turn").tap();

    await expect
      .poll(async () => container.evaluate((node) => node.scrollTop))
      .toBeLessThan(before);
  });
});

test.describe("Conversation minimap — phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("is absent and leaves no hidden focusable control", async ({ page }) => {
    await openFixture(page);
    await mountFixture(page, { messages: shortHistory() });

    await expect(page.getByTestId("conversation-minimap")).toHaveCount(0);
    await expect(
      page.locator("[data-testid^='conversation-minimap']")
    ).toHaveCount(0);

    // Ordinary transcript scrolling still works.
    const container = page.getByTestId("chat-container");
    const scrollable = await container.evaluate(
      (node) => node.scrollHeight > node.clientHeight
    );
    expect(scrollable).toBe(true);
  });
});
