/**
 * Focused UI tests for the @luna identity contract in webui-basic.
 *
 * webui-basic/index.html is a single-file static page with inline JS
 * wrapped in an IIFE. To keep the production HTML untouched, these tests
 * read the HTML, extract the `renderMessages` and `esc` function source
 * with regex, and exercise them in a controlled scope with jsdom.
 *
 * The contract under test:
 *   - assistant message with metadata.source === 'luna_n8n' OR
 *     metadata.display_name === 'Luna' renders as Luna (purple bg, "Luna" name)
 *   - any other assistant message renders as Guardian (default assistant
 *     styling, "Guardian" name)
 *   - the previous text-prefix heuristic ([luna] ... in content) is no
 *     longer authoritative; messages without the metadata are NOT styled
 *     as Luna even if the text starts with "[luna]"
 *   - user messages are unaffected
 */

import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const HTML_PATH = resolve(
  __dirname,
  "..",
  "..",
  "webui-basic",
  "index.html",
);

interface RenderMessagesArgs {
  msgs: Array<{
    role: string;
    content: string;
    metadata?: Record<string, unknown> | null;
  }>;
  userName: string;
}

interface RenderHandle {
  (args: RenderMessagesArgs): string;
}

/** Extracts the body of a `function NAME(...) { ... }` declaration from the
 *  webui-basic HTML. Tolerates arbitrary leading whitespace.
 */
function extractFunctionSource(html: string, name: string): string {
  const pattern = new RegExp(
    `function\\s+${name}\\s*\\([^)]*\\)\\s*\\{[\\s\\S]*?\\n  \\}`,
    "m",
  );
  const match = html.match(pattern);
  if (!match) {
    throw new Error(
      `Could not extract function '${name}' from webui-basic/index.html`,
    );
  }
  return match[0];
}

/** Loads the HTML, extracts the relevant functions, and returns a renderer
 *  that accepts a list of messages plus a userName and returns the
 *  resulting innerHTML of the messages container element.
 */
function loadRenderer(): RenderHandle {
  const html = readFileSync(HTML_PATH, "utf-8");
  const renderMessagesSrc = extractFunctionSource(html, "renderMessages");
  const escSrc = extractFunctionSource(html, "esc");

  // The original `renderMessages` references `userName` and `esc` from the
  // IIFE closure. We re-declare them as parameters/inner bindings so the
  // extracted source runs standalone in a test scope.
  const renderMessages = new Function(
    "msgs",
    "userName",
    "esc",
    renderMessagesSrc,
  );
  // `esc` is a one-liner: `var d = document.createElement('div'); d.textContent = s; return d.innerHTML;`
  // Re-declare as a normal function so the renderer can use it.
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  const esc = new Function("s", escSrc.replace(/^function\s+esc\s*\(\s*s\s*\)\s*\{/, ""));

  return ({ msgs, userName }) => {
    const container = document.createElement("div");
    container.id = "messages";
    document.body.appendChild(container);
    const oldGetById = document.getElementById.bind(document);
    document.getElementById = ((id: string) => {
      if (id === "messages") return container;
      return oldGetById(id);
    }) as typeof document.getElementById;
    try {
      renderMessages(msgs, userName, esc);
    } finally {
      document.getElementById = oldGetById;
      container.remove();
    }
    return container.innerHTML;
  };
}

describe("webui-basic renderMessages — @luna identity contract", () => {
  let render: RenderHandle;

  beforeAll(() => {
    render = loadRenderer();
  });

  it("renders an assistant message with metadata.source='luna_n8n' as Luna", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        {
          role: "assistant",
          content: "Hello from Luna",
          metadata: { source: "luna_n8n", display_name: "Luna" },
        },
      ],
    });
    expect(out).toContain('class="message assistant luna"');
    expect(out).toContain(">Luna<");
    expect(out).not.toContain(">Guardian<");
  });

  it("identifies Luna via display_name when source is missing", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        {
          role: "assistant",
          content: "Hi",
          metadata: { display_name: "Luna" },
        },
      ],
    });
    expect(out).toContain('class="message assistant luna"');
    expect(out).toContain(">Luna<");
  });

  it("renders an ordinary assistant message as Guardian", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        {
          role: "assistant",
          content: "Hello from Codexify",
        },
      ],
    });
    expect(out).toContain('class="message assistant"');
    expect(out).not.toContain('class="message assistant luna"');
    expect(out).toContain(">Guardian<");
  });

  it("renders an assistant with display_name='Codexify' as Guardian", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        {
          role: "assistant",
          content: "Hi",
          metadata: { source: "codexify", display_name: "Codexify" },
        },
      ],
    });
    expect(out).toContain('class="message assistant"');
    expect(out).toContain(">Guardian<");
  });

  it("does NOT apply Luna styling based on the legacy [luna] text prefix", () => {
    // The previous heuristic used /^[luna]/i.test(content). After the
    // metadata contract, a leading "[luna] " in the content alone MUST
    // NOT trigger Luna styling — only the metadata does.
    const out = render({
      userName: "Zac",
      msgs: [
        {
          role: "assistant",
          content:
            "[luna] this used to be Luna before the metadata contract",
        },
      ],
    });
    expect(out).toContain(">Guardian<");
    expect(out).not.toContain('class="message assistant luna"');
  });

  it("escapes Luna reply content (no HTML injection)", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        {
          role: "assistant",
          content: "<script>alert(1)</script>",
          metadata: { source: "luna_n8n", display_name: "Luna" },
        },
      ],
    });
    expect(out).toContain("&lt;script&gt;");
    expect(out).not.toContain("<script>");
  });

  it("renders user messages independently of Luna identity", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        // webui-basic prefixes user messages with "[Name]: " so the bubble
        // is classified as user-self when the name matches userName.
        { role: "user", content: "[Zac]: hi" },
        {
          role: "assistant",
          content: "Luna reply",
          metadata: { source: "luna_n8n", display_name: "Luna" },
        },
      ],
    });
    // User bubble (self, name matches)
    expect(out).toMatch(/class="message user-self"/);
    // Luna bubble
    expect(out).toMatch(/class="message assistant luna"/);
    // No accidental Guardian styling
    expect(out).not.toContain(">Guardian<");
  });

  it("renders mixed Guardian + Luna threads correctly", () => {
    const out = render({
      userName: "Zac",
      msgs: [
        { role: "user", content: "[Zac]: earlier" },
        { role: "assistant", content: "earlier reply" },
        { role: "user", content: "[Zac]: @luna latest" },
        {
          role: "assistant",
          content: "Luna reply",
          metadata: { source: "luna_n8n", display_name: "Luna" },
        },
      ],
    });
    // Both classes must appear
    expect(out).toContain('class="message assistant luna"');
    expect(out).toContain('class="message assistant"');
    // Exactly one Luna bubble and at least one Guardian bubble
    const lunaMatches = out.match(/class="message assistant luna"/g) ?? [];
    const guardianMatches = out.match(/class="message assistant"/g) ?? [];
    expect(lunaMatches.length).toBe(1);
    expect(guardianMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders an empty message list with the no-thread marker", () => {
    const out = render({ userName: "Zac", msgs: [] });
    expect(out).toContain("no-thread");
    expect(out).not.toContain("class=\"message");
  });
});
