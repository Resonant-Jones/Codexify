import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ChatBubble from "@/features/chat/components/ChatBubble";

describe("ChatBubble", () => {
  it("hides malformed timestamps instead of rendering Invalid Date", () => {
    render(
      <ChatBubble
        isGuardian={false}
        message={{
          id: "msg-1",
          authorId: "me",
          authorName: "You",
          content: "Hello world",
          createdAt: Number.NaN,
        }}
      />
    );

    expect(screen.getByText("Hello world")).toBeInTheDocument();
    expect(screen.queryByText("Invalid Date")).not.toBeInTheDocument();
  });
});
