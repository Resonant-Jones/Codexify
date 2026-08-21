import { describe, expect, it } from "vitest";

import {
  CONVERSATION_ORIGIN_SYSTEMS,
  parseConversationOriginSystem,
} from "../conversationOrigin";

describe("conversation origin contract", () => {
  it("exposes only the backend-owned canonical origin tokens", () => {
    expect(CONVERSATION_ORIGIN_SYSTEMS).toEqual([
      "codexify",
      "openai",
      "anthropic",
    ]);
  });

  it("accepts exact canonical DTO values and rejects aliases or metadata labels", () => {
    for (const originSystem of CONVERSATION_ORIGIN_SYSTEMS) {
      expect(parseConversationOriginSystem(originSystem)).toBe(originSystem);
    }

    for (const invalidValue of [
      "OpenAI",
      "chatgpt",
      "claude",
      "gemini",
      "perplexity",
      "codexify ",
      null,
      undefined,
      {},
    ]) {
      expect(parseConversationOriginSystem(invalidValue)).toBeNull();
    }
  });
});
