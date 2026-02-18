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
});
