import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createParser } from "@openuidev/react-lang";
import ChatBubble from "@/features/chat/components/ChatBubble";
import {
  OpenUiNative, admitOpenUiProgram, codexifyOpenUiLibrary, validateOpenUiProgram,
  OPENUI_LIBRARY_VERSION, OPENUI_MAX_PROGRAM_CHARS,
} from "./openuiNative";
import { parseUiArtifacts, serializeUiArtifact } from "./artifactCodec";
import { resolveNativeUiComponent } from "./nativeRegistry";
import { OPENUI_FOUNDATION_LIBRARY_VERSION } from "./openuiFoundationLibrary";

const program = 'root = CodexifyMetric("Tasks", "12", "Read-only")';
const props = { libraryVersion: OPENUI_LIBRARY_VERSION, program };
const marker = serializeUiArtifact({ version: 1, kind: "native", component: "openui.program", props });

function bubble(content: string) {
  return <ChatBubble isGuardian message={{
    id: "openui-msg", authorId: "bot", authorName: "Guardian", content, createdAt: Date.now(),
  }} />;
}

afterEach(() => vi.unstubAllEnvs());

describe("bounded OpenUI native renderer", () => {
  it("parses and lazily renders a registered Codexify-token-backed metric", async () => {
    const parser = createParser(codexifyOpenUiLibrary.toJSONSchema(), codexifyOpenUiLibrary.root);
    const result = parser.parse(program);
    expect(result.meta.errors).toEqual([]);
    expect(resolveNativeUiComponent("openui.program")).not.toBeNull();
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    render(bubble("Metric follows.\n" + marker));
    expect(await screen.findByTestId("openui-codexify-metric")).toHaveTextContent("Tasks");
    expect(screen.getByTestId("openui-codexify-metric")).toHaveTextContent("12");
    expect(screen.getByTestId("openui-codexify-metric")).toHaveStyle({ color: "var(--text)" });
    expect(screen.getByText("Metric follows.")).toBeInTheDocument();
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("round-trips through the unmodified canonical cfy-ui codec", () => {
    const decoded = parseUiArtifacts("Result.\n" + marker);
    expect(decoded.text).toBe("Result.");
    expect(decoded.artifacts).toHaveLength(1);
    expect(decoded.artifacts[0]).toMatchObject({ kind: "native", component: "openui.program", props });
  });

  it("respects the existing default-off renderer gate", () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "false");
    render(bubble(marker));
    expect(screen.queryByTestId("openui-codexify-metric")).toBeNull();
  });

  it("rejects unexpected versions, keys, and unbounded programs", () => {
    expect(validateOpenUiProgram({ ...props, libraryVersion: 2 })).toBeNull();
    expect(validateOpenUiProgram({ ...props, extra: "forbidden" })).toBeNull();
    expect(validateOpenUiProgram({ ...props, program: "x".repeat(OPENUI_MAX_PROGRAM_CHARS + 1) })).toBeNull();
    expect(validateOpenUiProgram({ ...props, program: 'root = CodexifyMetric("x", "y", "z".repeat(1000))' })).toBeNull();
    expect(validateOpenUiProgram({
      ...props, program: `root = CodexifyMetric(${JSON.stringify("x".repeat(101))}, "12")`,
    })).toBeNull();
    expect(validateOpenUiProgram({
      ...props, program: `root = CodexifyMetric("Tasks", ${JSON.stringify("1".repeat(41))})`,
    })).toBeNull();
    expect(validateOpenUiProgram({
      ...props, program: `root = CodexifyMetric("Tasks", "12", ${JSON.stringify("a".repeat(181))})`,
    })).toBeNull();
  });

  it.each([
    'root = Query("network", {})',
    'root = Mutation("write", {})',
    'root = CodexifyMetric(@Action("run"), "12")',
    'root = UnknownComponent("Tasks")',
    'root = CodexifyMetric("Tasks", "12")\nother = Query("x")',
    'root = CodexifyMetric("<img>", $state)',
  ])("denies executable and nonliteral OpenUI syntax: %s", (source) => {
    expect(validateOpenUiProgram({ ...props, program: source })).toBeNull();
    const { container } = render(<OpenUiNative {...props} program={source} />);
    expect(container.querySelector('[data-testid="openui-codexify-metric"]')).toBeNull();
  });

  it("renders markup-like inputs as inert text and never as host DOM", () => {
    const markup = '<img src=x onerror="window.__cfyXss=1">';
    const source = `root = CodexifyMetric(${JSON.stringify(markup)}, "12")`;
    render(<OpenUiNative libraryVersion={1} program={source} />);
    expect(screen.getByTestId("openui-codexify-metric")).toHaveTextContent(markup);
    expect(document.querySelector("img")).toBeNull();
    expect((window as unknown as Record<string, unknown>).__cfyXss).toBeUndefined();
  });

  it("offers a constrained read-only library prompt for future provider testing", () => {
    const prompt = codexifyOpenUiLibrary.prompt({ preamble: "Use read-only components." });
    expect(prompt).toContain("CodexifyMetric");
  });
});

/**
 * Version coexistence proof.
 *
 * The artifact envelope stays `version: 1` and the component id stays
 * `openui.program`; only `libraryVersion` discriminates. Version 1 keeps its
 * original validator verbatim, so artifacts persisted before this change restore
 * exactly as they did.
 */
describe("OpenUI version coexistence", () => {
  const v1Program = 'root = CodexifyMetric("Tasks", "12", "Read-only")';
  const v2Program =
    'root = CodexifyStack("vertical", [CodexifyMetric("Tasks", "12"), CodexifyCard([CodexifyText("Read-only")], "Panel")])';

  it("dispatches admission by libraryVersion", () => {
    expect(admitOpenUiProgram({ libraryVersion: OPENUI_LIBRARY_VERSION, program: v1Program })).toEqual({
      version: 1,
      program: v1Program,
    });
    expect(admitOpenUiProgram({ libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program: v2Program })).toEqual({
      version: 2,
      program: v2Program,
    });
  });

  it("refuses unknown, missing, and mismatched library versions", () => {
    expect(admitOpenUiProgram({ libraryVersion: 3, program: v2Program })).toBeNull();
    expect(admitOpenUiProgram({ program: v1Program })).toBeNull();
    // A version-1 validator must never admit a version-2 program, and vice versa.
    expect(validateOpenUiProgram({ libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program: v2Program })).toBeNull();
    expect(admitOpenUiProgram({ libraryVersion: OPENUI_LIBRARY_VERSION, program: v2Program })).toBeNull();
  });

  it("keeps the version-1 validator byte-for-byte compatible with its original behaviour", () => {
    expect(validateOpenUiProgram({ libraryVersion: 1, program: v1Program })).toBe(v1Program);
    expect(validateOpenUiProgram({ libraryVersion: 1, program: v1Program, extra: true })).toBeNull();
  });

  it("round-trips a version-2 program through the unmodified cfy-ui codec", () => {
    const props = { libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program: v2Program };
    const v2Marker = serializeUiArtifact({ version: 1, kind: "native", component: "openui.program", props });
    const decoded = parseUiArtifacts("Result.\n" + v2Marker);
    expect(decoded.text).toBe("Result.");
    expect(decoded.artifacts).toHaveLength(1);
    expect(decoded.artifacts[0]).toMatchObject({ version: 1, kind: "native", component: "openui.program", props });
    // The envelope is still version 1; only the inner library version differs.
    expect((decoded.artifacts[0] as { version: number }).version).toBe(1);
  });

  it("renders both library versions through the one registered component id", async () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    expect(resolveNativeUiComponent("openui.program")).not.toBeNull();

    const v1Marker = serializeUiArtifact({
      version: 1,
      kind: "native",
      component: "openui.program",
      props: { libraryVersion: OPENUI_LIBRARY_VERSION, program: v1Program },
    });
    const { unmount } = render(bubble(v1Marker));
    expect(await screen.findByTestId("openui-codexify-metric")).toHaveTextContent("Tasks");
    unmount();

    const v2Marker = serializeUiArtifact({
      version: 1,
      kind: "native",
      component: "openui.program",
      props: { libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program: v2Program },
    });
    render(bubble(v2Marker));
    expect(await screen.findByTestId("openui-foundation-stack")).toBeInTheDocument();
    expect(screen.getByTestId("openui-foundation-metric")).toHaveTextContent("Tasks");
  });

  it("renders nothing for an admitted-shape but refused program", () => {
    vi.stubEnv("VITE_GENERATIVE_UI", "true");
    const hostile =
      'root = CodexifyStack("vertical", [CodexifyCard([CodexifyCard([CodexifyText("x")], "inner")], "outer")])';
    const { container } = render(
      bubble(serializeUiArtifact({
        version: 1,
        kind: "native",
        component: "openui.program",
        props: { libraryVersion: OPENUI_FOUNDATION_LIBRARY_VERSION, program: hostile },
      })),
    );
    expect(container.querySelector('[data-testid^="openui-foundation-"]')).toBeNull();
  });
});
