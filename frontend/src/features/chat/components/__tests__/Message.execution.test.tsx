import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ChatBubble from "@/features/chat/components/ChatBubble";

const baseMessage = {
  id: "msg-execution",
  authorId: "bot",
  authorName: "Guardian",
  content: "Fallback result",
  createdAt: Date.now(),
};

describe("ChatBubble execution badge", () => {
  it("renders badge when models differ", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          ...baseMessage,
          execution: {
            attempted_provider: "groq",
            attempted_model: "moonshotai/kimi-k2-instruct-0905",
            final_provider: "local",
            final_model: "qwen3.5:27b",
            fallback_triggered: true,
          },
        }}
      />
    );

    expect(screen.getByText("⚠ Executed on qwen3.5:27b")).toBeInTheDocument();
  });

  it("does not render badge when models match", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          ...baseMessage,
          execution: {
            attempted_provider: "local",
            attempted_model: "qwen3.5:27b",
            final_provider: "local",
            final_model: "qwen3.5:27b",
            fallback_triggered: false,
          },
        }}
      />
    );

    expect(screen.queryByText(/Executed on/)).not.toBeInTheDocument();
  });

  it("renders the final model label", () => {
    render(
      <ChatBubble
        isGuardian
        message={{
          ...baseMessage,
          execution: {
            attempted_provider: "groq",
            attempted_model: "moonshotai/kimi-k2-instruct-0905",
            final_provider: "openai",
            final_model: "gpt-5.4-mini",
            fallback_triggered: true,
          },
        }}
      />
    );

    expect(screen.getByText("⚠ Executed on gpt-5.4-mini")).toBeInTheDocument();
  });
});
