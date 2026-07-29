import { describe, expect, it } from "vitest";

import {
  getSupportedInlineCommands,
  markInlineCommandExecuted,
  matchInlineCommandPrefix,
  parseInlineCommandDraft,
  suggestInlineCommandValues,
  type InlineCommandOptionSets,
} from "@/features/chat/inlineCommands";

const optionSets: InlineCommandOptionSets = {
  project: [
    { value: "1", label: "General" },
    { value: "2", label: "Project Knowledge Base" },
    { value: "3", label: "Project Notes" },
  ],
  provider: [
    { value: "local", label: "Local" },
    {
      value: "cloud",
      label: "Cloud",
      disabled: true,
      disabledReason: "Cloud providers are disabled.",
    },
  ],
  model: [
    { value: "qwen3.5:9b", label: "qwen3.5:9b" },
    { value: "qwen3.5:32b", label: "qwen3.5:32b" },
  ],
  mode: [
    { value: "default", label: "Auto" },
    { value: "no_think", label: "Fast" },
  ],
  retrieval: [
    { value: "project", label: "Project" },
    { value: "personal_knowledge", label: "Personal Knowledge" },
  ],
};

describe("inline command registry", () => {
  it("lists supported canonical commands for a slash-only draft", () => {
    const result = parseInlineCommandDraft("/", optionSets);

    expect(result.state).toBe("incomplete");
    expect(result.suggestions.map((suggestion) => "name" in suggestion && suggestion.name))
      .toEqual(["project", "provider", "model", "mode", "retrieval"]);
  });

  it("filters canonical command names by prefix", () => {
    const definitions = getSupportedInlineCommands(optionSets);
    expect(matchInlineCommandPrefix("pro", definitions).map((item) => item.name))
      .toEqual(["project", "provider"]);
    expect(parseInlineCommandDraft("/mod", optionSets).state).toBe("incomplete");
  });

  it("parses exact commands and spaced project names", () => {
    const result = parseInlineCommandDraft(
      "/project Project Knowledge Base",
      optionSets
    );

    expect(result).toMatchObject({
      state: "ready",
      command: { name: "project" },
      option: { value: "2", label: "Project Knowledge Base" },
    });
  });

  it("keeps exact commands without values incomplete", () => {
    const result = parseInlineCommandDraft("/provider", optionSets);

    expect(result).toMatchObject({
      state: "incomplete",
      command: { name: "provider" },
      valueQuery: "",
    });
  });

  it.each([
    ["/unknown value", "unknown"],
    ["//model qwen3.5:9b", "unknown"],
    ["Please explain /model routing", "unknown"],
    ["The path is /project/foo", "unknown"],
    ["/model qwen3.5:9b\nordinary text", "unknown"],
  ])("treats %s as ordinary authored text", (draft, expectedState) => {
    expect(parseInlineCommandDraft(draft, optionSets).state).toBe(expectedState);
  });

  it("preserves exact canonical option tokens", () => {
    const result = parseInlineCommandDraft("/mode Auto", optionSets);

    expect(result).toMatchObject({
      state: "ready",
      option: { value: "default" },
    });
  });

  it("requires explicit selection for ambiguous values", () => {
    const result = parseInlineCommandDraft("/model qwen", optionSets);

    expect(result.state).toBe("ambiguous");
    expect(result.suggestions).toHaveLength(2);
  });

  it("reports disabled options without substituting a fallback", () => {
    const result = parseInlineCommandDraft("/provider cloud", optionSets);

    expect(result).toMatchObject({
      state: "disabled",
      option: { value: "cloud" },
      reason: "Cloud providers are disabled.",
    });
  });

  it("returns an executed result with accessible confirmation", () => {
    const parsed = parseInlineCommandDraft("/provider local", optionSets);
    expect(parsed.state).toBe("ready");
    if (parsed.state !== "ready") throw new Error("expected ready command");

    expect(markInlineCommandExecuted(parsed)).toMatchObject({
      state: "executed",
      confirmation: "Provider set to Local",
    });
  });

  it("does not mutate supplied option arrays", () => {
    const providerOptions = optionSets.provider as Array<{
      value: string;
      label: string;
      disabled?: boolean;
      disabledReason?: string;
    }>;
    const before = structuredClone(providerOptions);

    suggestInlineCommandValues("loc", providerOptions);
    parseInlineCommandDraft("/provider local", optionSets);

    expect(providerOptions).toEqual(before);
  });

  it("is a pure module with no browser or application-store dependency", () => {
    expect(() => parseInlineCommandDraft("/mode auto", optionSets)).not.toThrow();
  });
});
