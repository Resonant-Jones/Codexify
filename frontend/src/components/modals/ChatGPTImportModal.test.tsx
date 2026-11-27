import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ChatGPTImportModal } from "@/components/modals/ChatGPTImportModal";

const coordinator = vi.hoisted(() => ({
  start: vi.fn(),
  snapshot: {
    phase: "idle",
    job: null,
    error: null,
    technicalDetail: null,
    selectedFileCount: 0,
    selectedByteCount: 0,
  },
}));

vi.mock("@/features/imports/accountImportCoordinator", () => ({
  clearAccountImportCoordinatorResult: vi.fn(),
  getAccountImportCoordinatorSnapshot: () => coordinator.snapshot,
  startOpenAIAccountImport: coordinator.start,
  subscribeAccountImportCoordinator: () => () => {},
  hasArchivedAccountImport: () => false,
  restoreArchivedAccountImport: vi.fn().mockResolvedValue(false),
}));

vi.mock(import("@/lib/api"), async (importOriginal) => ({
  ...await importOriginal(),
  listOpenAIImportSources: vi.fn().mockResolvedValue([{ id: "saved-pro-id", label: "Pro" }]),
}));

describe("conversation history modal", () => {
  beforeEach(() => coordinator.start.mockReset().mockResolvedValue({ status: "queued" }));

  test("submits a selected ChatGPT JSON file through the canonical coordinator", async () => {
    const user = userEvent.setup();
    const exportFile = new File(["[]"], "conversation.json", {
      type: "application/json",
    });
    render(<ChatGPTImportModal open onOpenChange={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Import Conversation History" })).toBeInTheDocument();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await screen.findByRole("option", { name: "Pro" });
    await user.selectOptions(screen.getByLabelText("Saved OpenAI import source"), "saved-pro-id");
    await user.upload(input, exportFile);
    await user.click(screen.getByRole("button", { name: "Upload & Migrate" }));

    await waitFor(() => expect(coordinator.start).toHaveBeenCalledWith(
      [{ file: exportFile, relativePath: "conversation.json" }], "openai", "saved-pro-id"
    ));
  });

  test("submits a selected Claude JSON file through the same coordinator", async () => {
    const user = userEvent.setup();
    const exportFile = new File(["[]"], "conversations.json", {
      type: "application/json",
    });
    render(<ChatGPTImportModal open onOpenChange={vi.fn()} />);

    await user.click(screen.getByTestId("account-import-source-anthropic"));
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, exportFile);
    await user.click(screen.getByRole("button", { name: "Upload & Migrate" }));

    await waitFor(() => expect(coordinator.start).toHaveBeenCalledWith(
      [{ file: exportFile, relativePath: "conversations.json" }], "anthropic"
    ));
  });
});
