import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AxiosResponse } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import api from "@/lib/api";


describe("Document generation editor open", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, "", "/chat/123");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("opens the generated document in the workspace", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "get").mockResolvedValue({
      data: [],
    } as AxiosResponse);
    const postSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: {
        document_id: "doc-123",
        content: "Drafted content",
        format: "markdown",
        title: "Launch Brief",
      },
    } as AxiosResponse);

    render(<App />);

    await user.click(screen.getByRole("button", { name: /generate doc/i }));
    await user.type(screen.getByLabelText(/title/i), "Launch Brief");
    await user.type(
      screen.getByLabelText(/prompt/i),
      "Draft a launch overview."
    );
    await user.click(screen.getByRole("button", { name: /save draft/i }));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith(
        "/documents/generate",
        expect.objectContaining({
          thread_id: 123,
          title: "Launch Brief",
          prompt: "Draft a launch overview.",
          format: "markdown",
        })
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText(/Workspace .*Launch Brief\.md/i)
      ).toBeInTheDocument();
    });
  });
});
