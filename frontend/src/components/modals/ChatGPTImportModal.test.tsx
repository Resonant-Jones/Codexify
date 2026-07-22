import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ChatGPTImportModal } from "@/components/modals/ChatGPTImportModal";

const apiMocks = vi.hoisted(() => ({
  post: vi.fn(),
  preflightBackendAvailability: vi.fn(),
}));

const idleAccountImport = vi.hoisted(() => ({
  phase: "idle",
  job: null,
  error: null,
  technicalDetail: null,
  selectedFileCount: 0,
  selectedByteCount: 0,
}));

vi.mock("@/features/imports/accountImportCoordinator", () => ({
  clearAccountImportCoordinatorResult: vi.fn(),
  getAccountImportCoordinatorSnapshot: () => idleAccountImport,
  startOpenAIAccountImport: vi.fn(),
  subscribeAccountImportCoordinator: () => () => {},
}));

vi.mock("@/lib/api", () => ({
  default: { post: apiMocks.post },
  normalizeChatGptImportStats: (payload: unknown) => payload,
  normalizeImportRuntimeError: () => ({
    isRuntimeUnavailable: false,
    message: "Import failed",
  }),
  preflightBackendAvailability: apiMocks.preflightBackendAvailability,
}));

const importStats = {
  threads_imported: 1,
  messages_imported: 2,
  projects_created: 1,
  projects_reused: 0,
  messages_filtered: 0,
  embedding_candidates: 0,
  embeddings_persisted: 0,
  embeddings_failed: 0,
  embedding_coverage_degraded: false,
};

function renderModal() {
  render(
    <ChatGPTImportModal
      open
      onOpenChange={vi.fn()}
      userName="local_user"
    />
  );
}

function expectUploadedFile(expectedFile: File) {
  expect(apiMocks.post).toHaveBeenCalledOnce();
  const [path, body, options] = apiMocks.post.mock.calls[0];
  expect(path).toBe("/api/upload-chatgpt-export");
  expect(body).toBeInstanceOf(FormData);
  expect((body as FormData).get("file")).toBe(expectedFile);
  expect(options).toMatchObject({
    headers: { "X-User-Id": "local_user" },
    timeout: 0,
  });
}

describe("ChatGPTImportModal", () => {
  beforeEach(() => {
    apiMocks.preflightBackendAvailability.mockResolvedValue({ ok: true });
    apiMocks.post.mockResolvedValue({ data: importStats });
  });

  test("accepts conversation.json through the file picker", async () => {
    const user = userEvent.setup();
    const exportFile = new File(["[]"], "conversation.json", {
      type: "application/json",
    });

    renderModal();

    const input = document.querySelector('input[type="file"]');
    expect(input).toHaveAttribute(
      "accept",
      ".json,.dat,application/json,application/octet-stream"
    );
    await user.upload(input as HTMLInputElement, exportFile);

    expect(
      screen.getByText("conversation.json (1 KB)")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Upload & Migrate" }));

    await waitFor(() => expectUploadedFile(exportFile));
  });

  test("accepts an OpenAI .dat shard through drag and drop", async () => {
    const user = userEvent.setup();
    const exportFile = new File(
      ['{"conversation_id":"thread-1","messages":[]}'],
      "file_0000000000000001.dat",
      { type: "application/octet-stream" }
    );

    renderModal();

    fireEvent.drop(
      screen.getByText(/Drop a conversation JSON/).closest("div.rounded-xl")!,
      {
        dataTransfer: { files: [exportFile] },
      }
    );

    expect(
      screen.getByText(/file_0000000000000001\.dat/)
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Upload & Migrate" }));

    await waitFor(() => expectUploadedFile(exportFile));
  });
});
