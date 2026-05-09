import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AxiosResponse } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import api from "@/lib/api";
import { WORKSPACE_OPEN_EVENT } from "@/features/workspace/state/useWorkspaceState";


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
    const workspaceOpenPromise = new Promise<CustomEvent>((resolve) => {
      const handler = (event: Event) => {
        window.removeEventListener(WORKSPACE_OPEN_EVENT, handler as EventListener);
        resolve(event as CustomEvent);
      };
      window.addEventListener(WORKSPACE_OPEN_EVENT, handler as EventListener);
    });
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

    window.dispatchEvent(new CustomEvent("cfy:documents:generate"));
    expect(await screen.findByRole("dialog", { name: /generate document/i })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^title/i), "Launch Brief");
    await user.type(
      screen.getByRole("textbox", { name: /^prompt$/i }),
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

    const workspaceOpenEvent = await workspaceOpenPromise;
    expect(workspaceOpenEvent.detail).toEqual(
      expect.objectContaining({
        source: "generated-document",
        targetView: "documents",
        doc: expect.objectContaining({
          title: "Launch Brief",
          ext: "md",
        }),
      })
    );
  });
});
