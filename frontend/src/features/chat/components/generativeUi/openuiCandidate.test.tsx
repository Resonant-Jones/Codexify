import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createParser } from "@openuidev/react-lang";
import { OpenUiCandidate, codexifyOpenUiCandidateLibrary } from "./openuiCandidate";
import { parseUiArtifacts, serializeUiArtifact } from "./artifactCodec";
import { resolveNativeUiComponent } from "./nativeRegistry";

const program = 'root = CodexifyMetric("Tasks", "12", "Read-only")';

describe("isolated OpenUI candidate", () => {
  it("parses and renders a token-backed metric", () => {
    const parser = createParser(codexifyOpenUiCandidateLibrary.toJSONSchema(), codexifyOpenUiCandidateLibrary.root);
    const result = parser.parse(program);
    expect(result.meta.errors).toEqual([]);
    render(<OpenUiCandidate response={program} />);
    expect(screen.getByTestId("openui-codexify-metric")).toHaveTextContent("Tasks");
    expect(screen.getByTestId("openui-codexify-metric")).toHaveTextContent("12");
    expect(screen.getByTestId("openui-codexify-metric")).toHaveStyle({ color: "var(--text)" });
  });

  it("round-trips through cfy-ui without registering new authority", () => {
    const marker = serializeUiArtifact({ version: 1, kind: "native", component: "openui.program", props: { response: program } });
    const decoded = parseUiArtifacts("Result.\n" + marker);
    expect(decoded.text).toBe("Result.");
    expect(decoded.artifacts).toHaveLength(1);
    expect(decoded.artifacts[0]).toMatchObject({ kind: "native", component: "openui.program", props: { response: program } });
    expect(resolveNativeUiComponent("openui.program")).toBeNull();
  });

  it("offers a constrained read-only model prompt", () => {
    const prompt = codexifyOpenUiCandidateLibrary.prompt({ preamble: "Use read-only components." });
    expect(prompt).toContain("CodexifyMetric");
  });
});
