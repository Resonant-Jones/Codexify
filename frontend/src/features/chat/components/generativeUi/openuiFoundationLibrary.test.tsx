/**
 * Rendering proof for the version-2 Codexify OpenUI foundation pack.
 *
 * These tests render through the **registered native path** (`openui.program`
 * inside the ordinary `ChatBubble` transcript), not merely through Zod parsing,
 * so they exercise the same lazy boundary and the same feature gate the host uses.
 *
 * Contract: docs/architecture/generative-ui-contract.md
 */
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createParser } from "@openuidev/react-lang";
import ChatBubble from "@/features/chat/components/ChatBubble";
import { OpenUiNative } from "./openuiNative";
import { serializeUiArtifact } from "./artifactCodec";
import { resolveNativeUiComponent } from "./nativeRegistry";
import {
  OPENUI_FOUNDATION_LIBRARY_VERSION,
  OPENUI_UNDECLARED_TOKEN_DEPENDENCIES,
  codexifyOpenUiFoundationLibrary,
} from "./openuiFoundationLibrary";
import { OPENUI_V2_MAX_LIST_ENTRIES, OPENUI_V2_MAX_NODES } from "./openuiProgramAdmission";

const prog = (body: string) => `root = ${body}`;
const STACK = "CodexifyStack";

const V2_PROPS = { libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program: "" };
function v2(program: string) {
  return { libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program };
}

function bubble(content: string) {
  return (
    <ChatBubble
      isGuardian
      message={{
        id: "openui-v2-msg",
        authorId: "bot",
        authorName: "Guardian",
        content,
        createdAt: Date.now(),
      }}
    />
  );
}

function renderArtifact(program: string, libraryVersion = OPENUI_FOUNDATION_LIBRARY_VERSION) {
  const props = { libraryVersion, program };
  const marker = serializeUiArtifact({ version: 1, kind: "native", component: "openui.program", props });
  return render(bubble("Overview.\n" + marker));
}

afterEach(() => vi.unstubAllEnvs());

describe("foundation pack: composition renders through the registered native path", () => {
  it("renders a metric dashboard from a valid version-2 program", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    expect(resolveNativeUiComponent("openui.program")).not.toBeNull();
    renderArtifact(
      prog(
        `${STACK}("vertical", [CodexifyMetric("Open tasks", "12", "Read-only foundation pack"), CodexifyMetric("Slices", "3")])`,
      ),
    );
    expect(await screen.findByTestId("openui-foundation-stack")).toBeInTheDocument();
    const metrics = await screen.findAllByTestId("openui-foundation-metric");
    expect(metrics).toHaveLength(2);
    expect(metrics[0]).toHaveTextContent("Open tasks");
    expect(metrics[0]).toHaveTextContent("12");
    expect(metrics[1]).toHaveTextContent("Slices");
    // Ordinary transcript prose survives alongside the artifact.
    expect(screen.getByText("Overview.")).toBeInTheDocument();
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("composes Stack -> Card -> leaf components", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(
      prog(`${STACK}("vertical", [CodexifyCard([CodexifyHeading("Queue", "3"), CodexifyText("Waiting on review")], "Queue panel")])`),
    );
    const stack = await screen.findByTestId("openui-foundation-stack");
    expect(stack).toHaveAttribute("data-direction", "vertical");
    const card = screen.getByTestId("openui-foundation-card");
    expect(card).toBeInTheDocument();
    expect(screen.getByTestId("openui-foundation-card-heading")).toHaveTextContent("Queue panel");
    expect(screen.getByTestId("openui-foundation-heading")).toHaveTextContent("Queue");
    expect(screen.getByTestId("openui-foundation-text")).toHaveTextContent("Waiting on review");
  });

  it("renders a mixed text, card, and list layout", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(
      prog(
        `${STACK}("vertical", [CodexifyText("Status overview"), CodexifyCard([CodexifyList(["alpha", "beta", "gamma"])], "Items")])`,
      ),
    );
    await screen.findByTestId("openui-foundation-stack");
    expect(screen.getByTestId("openui-foundation-text")).toHaveTextContent("Status overview");
    const list = screen.getByTestId("openui-foundation-list");
    expect(list.tagName).toBe("UL");
    expect(list.querySelectorAll("li")).toHaveLength(3);
  });

  it("renders every approved component at least once", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(
      prog(
        `${STACK}("vertical", [CodexifyHeading("Summary", "2"), CodexifyText("body"), CodexifyBadge("healthy", "success"), CodexifyCard([CodexifyMetric("Latency", "42ms"), CodexifyProgress("Indexing", 3, 4, "Almost done"), CodexifyList(["one"], true)])])`,
      ),
    );
    await screen.findByTestId("openui-foundation-stack");
    for (const id of [
      "openui-foundation-heading",
      "openui-foundation-text",
      "openui-foundation-badge",
      "openui-foundation-metric",
      "openui-foundation-progress",
      "openui-foundation-list",
    ]) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
    expect(screen.getByTestId("openui-foundation-card")).toBeInTheDocument();
  });

  it("renders multiple progress indicators with accessible name, range, and status", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(
      prog(
        `${STACK}("vertical", [CodexifyProgress("Indexing", 3, 4, "Almost done"), CodexifyProgress("Upload", 1, 4)])`,
      ),
    );
    await screen.findByTestId("openui-foundation-stack");
    const bars = document.querySelectorAll('[role="progressbar"]');
    expect(bars).toHaveLength(2);
    expect(bars[0]).toHaveAttribute("aria-valuenow", "3");
    expect(bars[0]).toHaveAttribute("aria-valuemin", "0");
    expect(bars[0]).toHaveAttribute("aria-valuemax", "4");
    expect(bars[0]).toHaveAttribute("aria-label", "Indexing");
    expect(screen.getByTestId("openui-foundation-progress-status")).toHaveTextContent("Almost done");
    expect(screen.getAllByTestId("openui-foundation-progress-fill")).toHaveLength(2);
  });

  it("renders ordered list semantics when requested", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(prog(`${STACK}("vertical", [CodexifyList(["first", "second"], true)])`));
    await screen.findByTestId("openui-foundation-stack");
    expect(screen.getByTestId("openui-foundation-list")).toHaveAttribute("data-ordered", "true");
  });

  it("lays the stack out horizontally when asked", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(prog(`${STACK}("horizontal", [CodexifyText("a"), CodexifyText("b")], true)`));
    const stack = await screen.findByTestId("openui-foundation-stack");
    expect(stack).toHaveAttribute("data-direction", "horizontal");
    expect(stack.style.flexDirection).toBe("row");
    expect(stack.style.flexWrap).toBe("wrap");
  });
});

describe("foundation pack: boundary states", () => {
  it("renders an admitted but empty root", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(prog(`${STACK}("vertical", [])`));
    const stack = await screen.findByTestId("openui-foundation-stack");
    expect(stack).toBeInTheDocument();
    expect(stack.children).toHaveLength(0);
  });

  it("renders at the maximum node and list boundaries", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    const items = Array.from({ length: OPENUI_V2_MAX_LIST_ENTRIES }, (_, i) => `"item ${i}"`).join(", ");
    const leaves = Array.from({ length: OPENUI_V2_MAX_NODES - 2 }, (_, i) => `CodexifyBadge("b${i}")`).join(", ");
    renderArtifact(prog(`${STACK}("vertical", [CodexifyList([${items}]), ${leaves}])`));
    await screen.findByTestId("openui-foundation-stack");
    // root + list + 10 badges == the declared node bound
    expect(OPENUI_V2_MAX_NODES).toBe(12);
    expect(screen.getByTestId("openui-foundation-list").querySelectorAll("li")).toHaveLength(12);
    expect(screen.getAllByTestId("openui-foundation-badge")).toHaveLength(10);
  });

  it("renders an omitted card heading without an empty heading element", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(prog(`${STACK}("vertical", [CodexifyCard([CodexifyText("body")])])`));
    await screen.findByTestId("openui-foundation-stack");
    expect(screen.getByTestId("openui-foundation-card")).toBeInTheDocument();
    expect(screen.queryByTestId("openui-foundation-card-heading")).toBeNull();
  });
});

describe("foundation pack: appearance inherits Codexify tokens", () => {
  it("expresses colour and surface through tokens rather than literals", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    renderArtifact(
      prog(`${STACK}("vertical", [CodexifyCard([CodexifyText("body"), CodexifyBadge("ok", "info")], "Panel")])`),
    );
    const card = await screen.findByTestId("openui-foundation-card");
    expect(card.style.background).toContain("var(--panel-bg)");
    expect(card.style.border).toContain("var(--panel-border)");
    expect(card.style.color).toBe("var(--text)");
    expect(card.style.padding).toContain("var(--card-pad");

    const badge = screen.getByTestId("openui-foundation-badge");
    expect(badge.style.background).toContain("var(--info-surface)");
    expect(badge.style.color).toBe("var(--info-text)");
    expect(badge.style.borderRadius).toContain("--radius-micro");
  });

  it("contains no hard-coded colour or width in rendered foundation output", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    const { container } = renderArtifact(
      prog(`${STACK}("vertical", [CodexifyCard([CodexifyText("body"), CodexifyBadge("ok", "danger")], "Panel")])`),
    );
    const styles = Array.from(container.querySelectorAll<HTMLElement>("[style]"))
      .map((node) => node.getAttribute("style") ?? "")
      .join(";");
    expect(styles).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(styles).not.toMatch(/rgba?\(/);
    // No fixed pixel width that could overflow a narrow conversation lane.
    expect(styles).not.toMatch(/width:\s*\d+px/);
  });

  it("reports the contract tokens that have no declaration in the current tree", () => {
    // These four are consumed with a documented fallback rather than created,
    // because this task may not introduce new runtime theme tokens.
    expect([...OPENUI_UNDECLARED_TOKEN_DEPENDENCIES].sort()).toEqual([
      "--card-pad",
      "--card-radius",
      "--radius-micro",
      "--shell-gap",
    ]);
  });
});

describe("foundation pack: fail-closed rendering and inertness", () => {
  it("renders no native artifact for an invalid program while prose survives", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    const { container } = renderArtifact(
      prog(`${STACK}("vertical", [CodexifyCard([CodexifyCard([CodexifyText("x")], "inner")], "outer")])`),
    );
    expect(container.querySelector('[data-testid="openui-foundation-stack"]')).toBeNull();
    expect(screen.getByText("Overview.")).toBeInTheDocument();
  });

  it("renders nothing at all for a refused program handed straight to the component", () => {
    const { container } = render(<OpenUiNative {...V2_PROPS} program={prog(`${STACK}("vertical", [CodexifyWidget("x")])`)} />);
    expect(container.querySelector("[data-testid^='openui-foundation-']")).toBeNull();
  });

  it("renders hostile markup as inert text and never as host DOM", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    const hostile = '<img src=x onerror="window.__cfyXss=1"><script>window.__cfyXss=1</script>';
    renderArtifact(prog(`${STACK}("vertical", [CodexifyText(${JSON.stringify(hostile)})])`));
    const text = await screen.findByTestId("openui-foundation-text");
    expect(text).toHaveTextContent("onerror");
    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
    expect((window as unknown as Record<string, unknown>).__cfyXss).toBeUndefined();
  });

  it("renders nothing when the existing feature gate is off", () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "false");
    const { container } = renderArtifact(prog(`${STACK}("vertical", [CodexifyText("body")])`));
    expect(container.querySelector('[data-testid="openui-foundation-stack"]')).toBeNull();
  });
});

describe("foundation pack: version coexistence", () => {
  it("renders a version-1 metric and a version-2 program through the same component id", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    const { container } = render(<OpenUiNative libraryVersion={1} program='root = CodexifyMetric("Tasks", "12", "Read-only")' />);
    expect(container.querySelector('[data-testid="openui-codexify-metric"]')).not.toBeNull();

    renderArtifact(prog(`${STACK}("vertical", [CodexifyMetric("Tasks", "12")])`));
    await screen.findByTestId("openui-foundation-stack");
    // The version-2 metric is a distinct element from the version-1 one.
    expect(screen.getByTestId("openui-foundation-metric")).toBeInTheDocument();
  });
});

/**
 * Regression guard for a real @openuidev/react-lang 1.0.1 behaviour.
 *
 * The parser maps positional arguments onto declared schema keys **in order**,
 * and it does not skip an optional key. An optional prop declared ahead of a
 * required one therefore swallows the next argument and makes that required prop
 * unreachable. Every foundation schema keeps required props first; this test
 * fails loudly if that ordering is ever undone.
 */
describe("foundation pack: positional argument ordering", () => {
  it("keeps required props ahead of optional props on every component", () => {
    const parser = createParser(codexifyOpenUiFoundationLibrary.toJSONSchema(), codexifyOpenUiFoundationLibrary.root);

    // Stack: direction + children are required; wrap is optional and trailing.
    const stack = parser.parse(prog(`${STACK}("vertical", [CodexifyText("a")])`));
    expect(stack.meta.errors).toEqual([]);
    expect(stack.root?.props.direction).toBe("vertical");

    // Card: children is required and first; heading is optional and trailing.
    const card = parser.parse(prog(`${STACK}("vertical", [CodexifyCard([CodexifyText("a")])])`));
    expect(card.meta.errors).toEqual([]);
    expect(Array.isArray(card.root?.props.children)).toBe(true);

    // Text: text is required; size and emphasis are optional and trailing.
    const text = parser.parse(prog(`${STACK}("vertical", [CodexifyText("a")])`));
    expect(text.meta.errors).toEqual([]);

    // Progress: label, value, max are required; statusText is optional/trailing.
    const progress = parser.parse(prog(`${STACK}("vertical", [CodexifyProgress("L", 1, 2)])`));
    expect(progress.meta.errors).toEqual([]);
  });
});