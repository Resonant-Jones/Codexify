import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const coordinator = vi.hoisted(() => {
  const idle = {
    phase: "idle" as const,
    job: null,
    error: null,
    technicalDetail: null,
    selectedFileCount: 0,
    selectedByteCount: 0,
  };
  return {
    state: { current: idle as any },
    start: vi.fn(),
    clear: vi.fn(),
    get: vi.fn(() => idle as any),
    subscribe: vi.fn(() => () => {}),
  };
});

const apiMocks = vi.hoisted(() => ({
  post: vi.fn(),
  preflight: vi.fn(),
}));

vi.mock("@/features/imports/accountImportCoordinator", () => ({
  clearAccountImportCoordinatorResult: coordinator.clear,
  getAccountImportCoordinatorSnapshot: () => coordinator.state.current,
  startOpenAIAccountImport: coordinator.start,
  subscribeAccountImportCoordinator: coordinator.subscribe,
}));

vi.mock("@/lib/api", () => ({
  default: { post: apiMocks.post },
  normalizeChatGptImportStats: (payload: unknown) => payload,
  normalizeImportRuntimeError: () => ({ message: "Import failed" }),
  preflightBackendAvailability: apiMocks.preflight,
}));

import {
  ChatGPTImportModal,
  enumerateOpenAIExportDrop,
} from "@/components/modals/ChatGPTImportModal";

const queuedJob = {
  job_id: "job-12345678",
  source_system: "openai",
  status: "queued",
  total_file_count: 2,
  total_byte_count: 5,
  uploaded_file_count: 2,
  uploaded_byte_count: 5,
  imported_thread_count: 0,
  imported_message_count: 0,
  imported_media_count: 0,
  duplicate_count: 0,
  skipped_count: 0,
  warning_count: 0,
  failure_count: 0,
  warning_details: [],
  error_details: [],
};

type TestEntry = {
  isFile: boolean;
  isDirectory: boolean;
  fullPath: string;
  file?: (success: (file: File) => void) => void;
  createReader?: () => {
    readEntries: (success: (entries: TestEntry[]) => void) => void;
  };
};

function fileEntry(path: string, file: File): TestEntry {
  return {
    isFile: true,
    isDirectory: false,
    fullPath: path,
    file: (success) => success(file),
  };
}

function directoryEntry(path: string, pages: TestEntry[][]): TestEntry {
  return {
    isFile: false,
    isDirectory: true,
    fullPath: path,
    createReader: () => {
      let index = 0;
      return {
        readEntries: (success) => success(pages[index++] || []),
      };
    },
  };
}

function idleSnapshot() {
  return {
    phase: "idle",
    job: null,
    error: null,
    technicalDetail: null,
    selectedFileCount: 0,
    selectedByteCount: 0,
  };
}

describe("ChatGPTImportModal account export intake", () => {
  beforeEach(() => {
    coordinator.state.current = idleSnapshot();
    coordinator.start.mockReset().mockResolvedValue(queuedJob);
    coordinator.clear.mockReset();
    coordinator.subscribe.mockImplementation(() => () => {});
    apiMocks.preflight.mockReset().mockResolvedValue({ ok: true });
    apiMocks.post.mockReset();
  });

  it("recursively drains directory-reader pages and preserves nested paths", async () => {
    const conversations = new File(["[]"], "conversations.json", {
      type: "application/json",
    });
    const shard = new File(["{}"], "file_1.dat", {
      type: "application/octet-stream",
    });
    const nested = directoryEntry("/export/nested", [
      [fileEntry("/export/nested/file_1.dat", shard)],
      [],
    ]);
    const root = directoryEntry("/export", [
      [fileEntry("/export/conversations.json", conversations)],
      [nested],
      [],
    ]);
    const dataTransfer = {
      items: [{ webkitGetAsEntry: () => root }],
      files: [],
    } as unknown as DataTransfer;

    const files = await enumerateOpenAIExportDrop(dataTransfer);

    expect(files.map((item) => item.relativePath)).toEqual([
      "export/conversations.json",
      "export/nested/file_1.dat",
    ]);
  });

  it("starts a recursive directory drop without a second click", async () => {
    const json = new File(["[]"], "conversations.json");
    const image = new File(["png"], "image.png", { type: "image/png" });
    const root = directoryEntry("/export", [
      [
        fileEntry("/export/conversations.json", json),
        fileEntry("/export/media/image.png", image),
      ],
      [],
    ]);
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );

    fireEvent.drop(
      screen.getByText(/Drop a conversation JSON/).closest("div.rounded-xl")!,
      {
        dataTransfer: {
          items: [{ webkitGetAsEntry: () => root }],
          files: [],
        },
      }
    );

    await waitFor(() => expect(coordinator.start).toHaveBeenCalledOnce());
    const [files, userId] = coordinator.start.mock.calls[0];
    expect(files.map((item: any) => item.relativePath)).toEqual([
      "export/conversations.json",
      "export/media/image.png",
    ]);
    expect(userId).toBe("account-a");
  });

  it("submits every folder-picker file immediately", async () => {
    const json = new File(["[]"], "conversations.json");
    const shard = new File(["{}"], "file_1.dat");
    Object.defineProperty(json, "webkitRelativePath", {
      value: "export/conversations.json",
    });
    Object.defineProperty(shard, "webkitRelativePath", {
      value: "export/nested/file_1.dat",
    });
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );
    const folderInput = document.querySelector(
      'input[type="file"][webkitdirectory]'
    ) as HTMLInputElement;

    fireEvent.change(folderInput, { target: { files: [json, shard] } });

    await waitFor(() => expect(coordinator.start).toHaveBeenCalledOnce());
    expect(
      coordinator.start.mock.calls[0][0].map((item: any) => item.relativePath)
    ).toEqual(["export/conversations.json", "export/nested/file_1.dat"]);
  });

  it("starts a complete ZIP drop immediately", async () => {
    const archive = new File(["zip"], "openai-export.zip", {
      type: "application/zip",
    });
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );

    fireEvent.drop(
      screen.getByText(/Drop a conversation JSON/).closest("div.rounded-xl")!,
      { dataTransfer: { files: [archive] } }
    );

    await waitFor(() => expect(coordinator.start).toHaveBeenCalledOnce());
    expect(coordinator.start).toHaveBeenCalledWith(
      [{ file: archive, relativePath: "openai-export.zip" }],
      "account-a"
    );
  });

  it("keeps accepted, running, and completed labels distinct and closable", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    coordinator.state.current = {
      ...idleSnapshot(),
      phase: "accepted",
      job: queuedJob,
    };
    const acceptedView = render(
      <ChatGPTImportModal
        open
        onOpenChange={onOpenChange}
        userName="account-a"
      />
    );

    expect(
      screen.getByText("Accepted — continuing in background")
    ).toBeInTheDocument();
    expect(screen.queryByText("Import running in background")).toBeNull();
    expect(screen.queryByText("Import completed")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);

    acceptedView.unmount();
    coordinator.state.current = {
      ...idleSnapshot(),
      phase: "running",
      job: { ...queuedJob, status: "running" },
    };
    const runningView = render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );
    expect(screen.getByText("Import running in background")).toBeInTheDocument();
    expect(screen.queryByText("Import completed")).toBeNull();

    runningView.unmount();
    coordinator.state.current = {
      ...idleSnapshot(),
      phase: "completed",
      job: {
        ...queuedJob,
        status: "completed",
        duplicate_count: 1,
        skipped_count: 1,
        warning_count: 1,
        warning_details: [
          {
            code: "image_provenance_unclassified",
            path: "media/orphan.png",
            message: "Image retained without provable provenance.",
          },
        ],
      },
    };
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );
    expect(screen.getByText("Import completed")).toBeInTheDocument();
    expect(screen.queryByText("Import running in background")).toBeNull();
    expect(
      screen.getByText("Duplicates: 1. Skipped: 1. Warnings: 1.")
    ).toBeInTheDocument();
    expect(screen.getByText("Review warning details")).toBeInTheDocument();
    expect(screen.getByText(/media\/orphan\.png/)).toBeInTheDocument();
  });
});
