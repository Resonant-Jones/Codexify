import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { buildChatCompletionPayload } from "@/lib/chatClient";
import {
  setPreferredProviderSelection,
  setPreferredProvider,
} from "@/lib/providerPref";

describe("buildChatCompletionPayload", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("includes provider and model from persisted preference", () => {
    setPreferredProviderSelection({
      provider: "openai",
      model: "gpt-4.1-mini",
    });

    expect(buildChatCompletionPayload("deep", "default")).toEqual({
      depth_mode: "deep",
      provider: "openai",
      model: "gpt-4.1-mini",
    });
  });

  it("falls back to active model id when no persisted provider-model preference exists", () => {
    setPreferredProvider(null);

    expect(buildChatCompletionPayload("normal", "llama3.1:8b")).toEqual({
      depth_mode: "normal",
      model: "llama3.1:8b",
    });
  });

  it("prefers explicit provider/model/mode selection when provided", () => {
    expect(
      buildChatCompletionPayload("normal", {
        providerId: "local",
        modelId: "qwen3.5:4b",
        reasoningMode: "think",
      })
    ).toEqual({
      depth_mode: "normal",
      provider: "local",
      model: "qwen3.5:4b",
      reasoning_mode: "think",
    });
  });

  it("includes identity fields when provided", () => {
    expect(
      buildChatCompletionPayload("normal", {
        preferredName: "Harbor",
        profession: "Engineer",
        guardianName: "Aurelia",
      })
    ).toEqual({
      depth_mode: "normal",
      preferred_name: "Harbor",
      profession: "Engineer",
      guardian_name: "Aurelia",
    });
  });

  it("omits blank identity fields cleanly", () => {
    expect(
      buildChatCompletionPayload("normal", {
        preferredName: " ",
        profession: "",
        guardianName: null,
      })
    ).toEqual({
      depth_mode: "normal",
    });
  });
});
