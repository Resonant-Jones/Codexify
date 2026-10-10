/**
 * Generative UI verification.
 *
 * Covers the four gates: artifact channel validity, sandbox containment,
 * host bridge authorization, native component registration, and restore of the
 * same artifact from canonical message content.
 */
import { render, screen, act } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ChatBubble from "@/features/chat/components/ChatBubble";
import {
  parseUiArtifacts,
  serializeUiArtifact,
  validateUiArtifact,
  MAX_SANDBOX_HTML_CHARS,
  type GenerativeUiArtifact,
} from "@/features/chat/components/generativeUi/artifactCodec";
import { NATIVE_UI_REGISTRY, resolveNativeUiComponent } from "@/features/chat/components/generativeUi/nativeRegistry";
import {
  buildSandboxDocument,
  MAX_FRAME_HEIGHT,
  MIN_FRAME_HEIGHT,
} from "@/features/chat/components/generativeUi/SandboxFrame";
import { COMPOSER_PREFILL_EVENT } from "@/features/chat/components/generativeUi/hostActions";

const CALCULATOR: GenerativeUiArtifact = {
  version: 1,
  kind: "sandbox",
  title: "Calculator",
  initialHeight: 260,
  html: [
    '<div class="wrap">',
    '<output id="display" aria-live="polite">0</output>',
    '<div class="pad">',
    ...["7", "8", "9", "/", "4", "5", "6", "*", "1", "2", "3", "-", "0", ".", "=", "+"]
      .map((key) => `<button type="button" data-key="${key}">${key}</button>`),
    "</div>",
    '<button type="button" id="clear" class="clear">C</button>',
    "</div>",
  ].join(""),
  css: ".pad{display:grid;grid-template-columns:repeat(4,1fr);gap:.35rem}",
  js: [
    'var display = document.getElementById("display");',
    'var expr = "";',
    'function flush(){ display.textContent = expr || "0"; }',
    'document.querySelectorAll("[data-key]").forEach(function (btn) {',
    '  btn.addEventListener("click", function () { expr += btn.dataset.key; flush(); });',
    '});',
    'document.getElementById("clear").addEventListener("click", function () { expr = ""; flush(); });',
    'flush();',
    'if (window.cfyUI) window.cfyUI.resizeTo(document.body);',
  ].join("\n"),
};

function bubble(content: string, isGuardian = true) {
  return <ChatBubble isGuardian={isGuardian} message={{
    id: "ui-msg", authorId: isGuardian ? "bot" : "me",
    authorName: isGuardian ? "Guardian" : "You", content, createdAt: Date.now(),
  }} />;
}

function enableGate(value = "true") {
  vi.stubEnv("VITE_GENERATIVE_UI", value);
}

function frameDocument(container: HTMLElement): string {
  const frame = container.querySelector("iframe");
  return frame?.getAttribute("srcdoc") ?? "";
}

function frameSession(container: HTMLElement): string {
  const match = /var SESSION = "([^"]+)"/.exec(frameDocument(container));
  return match?.[1] ?? "";
}

/** Blank the per-mount session nonce so two mounts can be compared. */
function normalizeSession(doc: string): string {
  return doc.replace(/var SESSION = "[^"]+"/, 'var SESSION = "<session>"');
}

function postFromFrame(
  container: HTMLElement,
  data: unknown,
  { origin = "null", useSource = true }: { origin?: string; useSource?: boolean } = {}
) {
  const frame = container.querySelector("iframe") as HTMLIFrameElement | null;
  const event = new MessageEvent("message", {
    data,
    origin,
    source: useSource ? frame?.contentWindow : null,
  });
  act(() => {
    window.dispatchEvent(event);
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
});

// ---------------------------------------------------------------------------
// Gate 1 — artifact channel validity
// ---------------------------------------------------------------------------

describe("generative UI artifact codec", () => {
  it("round-trips a sandbox artifact through canonical content", () => {
    const { artifacts, text } = parseUiArtifacts(
      `Here you go.\n\n${serializeUiArtifact(CALCULATOR)}\n\nPress a key to use it.`
    );

    expect(artifacts).toHaveLength(1);
    expect(artifacts[0].kind).toBe("sandbox");
    expect(text).toBe("Here you go.\n\nPress a key to use it.");
    expect(text).not.toContain("cfy-ui");
  });

  it("round-trips a native artifact and preserves props", () => {
    const parsed = parseUiArtifacts(
      serializeUiArtifact({
        version: 1, kind: "native", component: "chart.bar",
        props: { title: "Revenue", series: [{ label: "Q1", value: 12 }] },
      })
    );

    expect(parsed.artifacts[0]).toMatchObject({
      kind: "native", component: "chart.bar",
      props: { title: "Revenue", series: [{ label: "Q1", value: 12 }] },
    });
  });

  it("rejects unknown envelope versions and kinds", () => {
    expect(validateUiArtifact({ version: 2, kind: "sandbox", html: "<p>x</p>" })).toBeNull();
    expect(validateUiArtifact({ version: 1, kind: "unknown", html: "<p>x</p>" })).toBeNull();
    expect(validateUiArtifact(null)).toBeNull();
    expect(validateUiArtifact([])).toBeNull();
  });

  it("rejects an oversized sandbox payload", () => {
    const huge = { version: 1, kind: "sandbox", html: "x".repeat(MAX_SANDBOX_HTML_CHARS + 1) };
    expect(validateUiArtifact(huge)).toBeNull();
    expect(parseUiArtifacts(`prose ${serializeUiArtifact(huge as never)}`).text).toBe("prose");
  });

  it("rejects a native artifact whose props are not an object", () => {
    expect(validateUiArtifact({ version: 1, kind: "native", component: "chart.bar", props: "nope" })).toBeNull();
    expect(validateUiArtifact({ version: 1, kind: "native", component: "" })).toBeNull();
  });

  it("strips malformed markers from display text so they never leak into the transcript", () => {
    const parsed = parseUiArtifacts("Lead in.\n<!-- cfy-ui:@@@not-valid@@@ -->\nTail end.");
    expect(parsed.artifacts).toHaveLength(0);
    expect(parsed.text).toContain("Lead in.");
    expect(parsed.text).toContain("Tail end.");
    expect(parsed.text).not.toContain("cfy-ui");
  });
});

// ---------------------------------------------------------------------------
// Gate 2 — containment
// ---------------------------------------------------------------------------

describe("generative UI sandbox containment", () => {
  it("locks the iframe to allow-scripts with no same-origin escape", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const frame = container.querySelector("iframe")!;

    expect(frame.getAttribute("sandbox")).toBe("allow-scripts");
    for (const forbidden of [
      "allow-same-origin", "allow-forms", "allow-popups",
      "allow-top-navigation", "allow-modals", "allow-downloads",
    ]) {
      expect(frame.getAttribute("sandbox")).not.toContain(forbidden);
    }
  });

  it("injects a deny-all CSP before any generated content", () => {
    const doc = buildSandboxDocument(CALCULATOR as never, "sess");

    expect(doc).toContain('http-equiv="Content-Security-Policy"');
    expect(doc).toContain("default-src &#39;none&#39;".replace(/&#39;/g, "'"));
    expect(doc).toContain("connect-src 'none'");
    expect(doc).toContain("form-action 'none'");
    expect(doc).toContain("base-uri 'none'");
    // Upstream permits four public CDNs; Codexify must ship no network egress.
    expect(doc).not.toContain("https://");
    expect(doc).not.toContain("unpkg");
    expect(doc).not.toContain("esm.sh");
    // CSP is declared in head, ahead of the generated body.
    expect(doc.indexOf("Content-Security-Policy")).toBeLessThan(doc.indexOf('<div class="wrap">'));
  });

  it("ships no CDN importmap for generated code to fetch from", () => {
    const doc = buildSandboxDocument(CALCULATOR as never, "sess");
    expect(doc).not.toContain("importmap");
    expect(doc).not.toContain("import(");
  });

  it("neutralizes a generated payload that tries to close its own script element", () => {
    const doc = buildSandboxDocument(
      { version: 1, kind: "sandbox", html: "<p>ok</p>", js: 'var x = "</script><script>alert(1)</script>";' },
      "sess",
    );
    // The injected payload may not introduce a new executable script element.
    expect(doc).not.toContain("</script><script>alert(1)</script>");
    expect(doc).toContain("<\\/script>");
  });

  it("renders a real working calculator with controls inside the frame", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const doc = frameDocument(container);

    expect(container.querySelectorAll("button[data-key]")).toHaveLength(0);
    // Controls and handlers live inside the frame document, not the host tree.
    expect(doc).toContain('data-key="7"');
    expect(doc).toContain('data-key="+"');
    expect(doc).toContain('id="clear"');
    expect(doc).toContain('addEventListener("click"');
    expect(doc).toContain("btn.dataset.key");
    expect(doc).toContain("display.textContent = expr");
  });

  it("degrades a throwing artifact to an inline notice via the error boundary", () => {
    enableGate();
    const registry = NATIVE_UI_REGISTRY as Record<string, { component: unknown }>;
    const original = registry["chart.bar"].component;
    registry["chart.bar"].component = function Exploding(): React.ReactElement {
      throw new Error("render failure");
    };

    try {
      const { container } = render(
        bubble(`Transcript must survive.\n\n${serializeUiArtifact({
          version: 1, kind: "native", component: "chart.bar",
          props: { series: [{ label: "A", value: 1 }] },
        })}`)
      );

      expect(screen.getByTestId("generative-ui-error")).toBeInTheDocument();
      // Transcript integrity: the surrounding message still renders.
      expect(screen.getByText("Transcript must survive.")).toBeInTheDocument();
      expect(container.textContent).not.toContain("render failure");
    } finally {
      registry["chart.bar"].component = original;
    }
  });
});

// ---------------------------------------------------------------------------
// Gate 2 — registered native components
// ---------------------------------------------------------------------------

describe("registered native components", () => {
  it("renders a structured visualization from a registered component", () => {
    enableGate();
    render(bubble(serializeUiArtifact({
      version: 1, kind: "native", component: "chart.bar",
      props: {
        title: "Weekly active threads",
        series: [{ label: "Mon", value: 12 }, { label: "Tue", value: 31 }, { label: "Wed", value: 8 }],
      },
    })));

    const chart = screen.getByTestId("generative-ui-native-bar-chart");
    expect(chart).toBeInTheDocument();
    expect(screen.getByText("Weekly active threads")).toBeInTheDocument();
    // Rendered as trusted host SVG, never inside a sandbox.
    expect(document.querySelector("iframe")).toBeNull();
    expect(chart.querySelectorAll("rect")).toHaveLength(3);
  });

  it("does not resolve an unregistered component id dynamically", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact({
      version: 1, kind: "native", component: "totally.not.registered", props: {},
    })));

    expect(resolveNativeUiComponent("totally.not.registered")).toBeNull();
    expect(container.querySelector('[data-testid="generative-ui-native"]')).toBeNull();
  });

  it("exposes only explicitly registered ids", () => {
    expect(Object.keys(NATIVE_UI_REGISTRY).sort()).toEqual(["chart.bar", "table.rows"]);
  });

  it("degrades a chart with unusable data instead of throwing", () => {
    enableGate();
    render(bubble(serializeUiArtifact({
      version: 1, kind: "native", component: "chart.bar", props: { series: [{ label: "x" }] },
    })));
    expect(screen.getByTestId("generative-ui-native-chart-empty")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Gate 2 — host bridge authorization
// ---------------------------------------------------------------------------

describe("generative UI host bridge", () => {
  it("routes a validated send_prompt to composer prefill, never to a direct send", () => {
    enableGate();
    const seen: string[] = [];
    const listener = (event: Event) => {
      seen.push((event as CustomEvent<{ text: string }>).detail?.text ?? "");
    };
    window.addEventListener(COMPOSER_PREFILL_EVENT, listener);

    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const session = frameSession(container);
    expect(session).not.toBe("");

    postFromFrame(container, {
      channel: "cfy-ui", session, action: "send_prompt", payload: { text: "Show me last week's numbers" },
    });

    expect(seen).toEqual(["Show me last week's numbers"]);
    window.removeEventListener(COMPOSER_PREFILL_EVENT, listener);
  });

  it("rejects a message from the wrong origin", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const session = frameSession(container);

    postFromFrame(
      container,
      { channel: "cfy-ui", session, action: "send_prompt", payload: { text: "exfiltrate" } },
      { origin: "https://evil.example" },
    );
    postFromFrame(
      container,
      { channel: "cfy-ui", session, action: "resize", payload: { height: 400 } },
      { origin: "http://localhost" },
    );

    expect(window.dispatchEvent).toBeDefined();
  });

  it("rejects a message that did not come from this frame", () => {
    enableGate();
    const seen: string[] = [];
    const listener = (event: Event) => {
      seen.push((event as CustomEvent<{ text: string }>).detail?.text ?? "");
    };
    window.addEventListener(COMPOSER_PREFILL_EVENT, listener);
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const session = frameSession(container);

    postFromFrame(
      container,
      { channel: "cfy-ui", session, action: "send_prompt", payload: { text: "spoofed" } },
      { useSource: false },
    );

    expect(seen).toEqual([]);
    window.removeEventListener(COMPOSER_PREFILL_EVENT, listener);
  });

  it("rejects a message bound to a different session", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));

    postFromFrame(container, {
      channel: "cfy-ui", session: "ui-someone-else", action: "send_prompt", payload: { text: "nope" },
    });
    postFromFrame(container, {
      channel: "cfy-ui", session: "ui-someone-else", action: "resize", payload: { height: 300 },
    });

    expect(container.querySelector("iframe")!.getAttribute("style")).not.toContain("height: 300px");
  });

  it("ignores unknown actions and malformed payloads", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const session = frameSession(container);
    const frame = container.querySelector("iframe") as HTMLIFrameElement;

    postFromFrame(container, { channel: "cfy-ui", session, action: "open_link", payload: { url: "https://evil.example" } });
    postFromFrame(container, { channel: "cfy-ui", session, action: "read_localstorage" });
    postFromFrame(container, { channel: "other-channel", session, action: "send_prompt", payload: { text: "x" } });
    postFromFrame(container, { channel: "cfy-ui", session, action: "send_prompt", payload: { text: 12345 } });
    postFromFrame(container, { channel: "cfy-ui", session, action: "send_prompt", payload: { text: "   " } });

    // Height stays at the declared initial value; nothing partially applied.
    expect(frame.getAttribute("style")).toContain("height: 260px");
  });

  it("clamps a resize request into the bounded frame range", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    const session = frameSession(container);
    const frame = container.querySelector("iframe") as HTMLIFrameElement;

    postFromFrame(container, { channel: "cfy-ui", session, action: "resize", payload: { height: 100000 } });
    expect(frame.getAttribute("style")).toContain(`height: ${MAX_FRAME_HEIGHT}px`);

    postFromFrame(container, { channel: "cfy-ui", session, action: "resize", payload: { height: 1 } });
    expect(frame.getAttribute("style")).toContain(`height: ${MIN_FRAME_HEIGHT}px`);

    postFromFrame(container, { channel: "cfy-ui", session, action: "resize", payload: { height: "abc" } });
    expect(frame.getAttribute("style")).toContain("height: 200px");
  });

  it("gives each mounted frame a distinct session nonce", () => {
    enableGate();
    const first = render(bubble(serializeUiArtifact(CALCULATOR)));
    const second = render(bubble(serializeUiArtifact(CALCULATOR)));
    expect(frameSession(first.container)).not.toBe(frameSession(second.container));
  });
});

// ---------------------------------------------------------------------------
// Gate — feature gating and transcript integrity
// ---------------------------------------------------------------------------

describe("generative UI feature gate", () => {
  it("renders nothing and executes nothing when the gate is off", () => {
    enableGate("false");
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));

    expect(container.querySelector("iframe")).toBeNull();
    expect(container.querySelector('[data-testid="generative-ui-stack"]')).toBeNull();
    // The marker is still stripped from displayed text.
    expect(container.textContent).not.toContain("cfy-ui");
  });

  it("defaults to off with no env var set", () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "");
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR)));
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("keeps ordinary assistant text untouched", () => {
    enableGate();
    render(bubble("Just a normal sentence with `code` and **bold**."));
    expect(screen.getByText(/Just a normal sentence/)).toBeInTheDocument();
    expect(screen.getByText("code")).toBeInTheDocument();
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  it("does not render artifacts on user bubbles", () => {
    enableGate();
    const { container } = render(bubble(serializeUiArtifact(CALCULATOR), false));
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("preserves surrounding markdown, code blocks, and document markers", () => {
    enableGate();
    const content = [
      "## Findings",
      "",
      "```py",
      "print('kept')",
      "```",
      "",
      serializeUiArtifact(CALCULATOR),
      "",
      "Closing note.",
    ].join("\n");

    render(bubble(content));
    expect(screen.getByText("Findings")).toBeInTheDocument();
    expect(screen.getByText("Closing note.")).toBeInTheDocument();
    expect(screen.getByText("print('kept')")).toBeInTheDocument();
    expect(document.querySelector("iframe")).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Gate 3 — durable restore from canonical content
// ---------------------------------------------------------------------------

describe("generative UI durability", () => {
  it("restores the same interactive artifact after unmount and remount", () => {
    enableGate();
    const persisted = [
      "Here is the calculator you asked for.",
      serializeUiArtifact(CALCULATOR),
    ].join("\n\n");

    const first = render(bubble(persisted));
    const firstDoc = frameDocument(first.container);
    expect(first.container.querySelectorAll("iframe")).toHaveLength(1);
    first.unmount();

    // Reload: the artifact is replayed from canonical message content.
    const reloaded = render(bubble(persisted));
    expect(reloaded.container.querySelectorAll("iframe")).toHaveLength(1);
    // Identical artifact, including its generated controls and script. The only
    // difference is the per-mount session nonce, which is bound to the frame.
    expect(normalizeSession(frameDocument(reloaded.container))).toBe(normalizeSession(firstDoc));
    expect(screen.getByText("Here is the calculator you asked for.")).toBeInTheDocument();
  });

  it("restores a native visualization after reload without regenerating it", () => {
    enableGate();
    const persisted = serializeUiArtifact({
      version: 1, kind: "native", component: "chart.bar",
      props: { title: "Persisted chart", series: [{ label: "A", value: 3 }, { label: "B", value: 9 }] },
    });

    const first = render(bubble(persisted));
    expect(screen.getByTestId("generative-ui-native-bar-chart")).toBeInTheDocument();
    first.unmount();

    render(bubble(persisted));
    expect(screen.getByTestId("generative-ui-native-bar-chart")).toBeInTheDocument();
    expect(screen.getByText("Persisted chart")).toBeInTheDocument();
  });

  it("does not duplicate artifacts when a message re-renders with the same content", () => {
    enableGate();
    const content = `Intro.\n\n${serializeUiArtifact(CALCULATOR)}\n\nOutro.`;
    const { container, rerender } = render(bubble(content));
    rerender(bubble(content));

    expect(container.querySelectorAll("iframe")).toHaveLength(1);
    expect(screen.getAllByText("Intro.")).toHaveLength(1);
    expect(screen.getAllByText("Outro.")).toHaveLength(1);
  });

  it("renders multiple artifacts in one message in order", () => {
    enableGate();
    const content = [
      serializeUiArtifact({ version: 1, kind: "native", component: "chart.bar", props: { series: [{ label: "A", value: 1 }] } }),
      serializeUiArtifact(CALCULATOR),
      "Tail.",
    ].join("\n");

    render(bubble(content));
    expect(document.querySelectorAll("iframe")).toHaveLength(1);
    expect(screen.getByTestId("generative-ui-native-bar-chart")).toBeInTheDocument();
    expect(screen.getByText("Tail.")).toBeInTheDocument();
  });
});