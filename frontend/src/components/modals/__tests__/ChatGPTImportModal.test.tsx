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

// Use `importOriginal` so the real module exports are preserved. The modal
// imports `isAccountImportSourceSystem` (and other helpers) from
// `@/lib/api`; a partial mock that omits them prevents the component from
// resolving the canonical source validator at submit time.
vi.mock(import("@/lib/api"), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    default: { post: apiMocks.post },
    normalizeChatGptImportStats: (payload: unknown) => payload,
    normalizeImportRuntimeError: () => ({ message: "Import failed" }),
    preflightBackendAvailability: apiMocks.preflight,
  };
});

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

  it("renders both canonical source choices and defaults to OpenAI", () => {
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );
    expect(
      screen.getByTestId("account-import-source-openai")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("account-import-source-anthropic")
    ).toBeInTheDocument();
    expect(screen.getByText("OpenAI (ChatGPT)")).toBeInTheDocument();
    expect(screen.getByText("Anthropic (Claude)")).toBeInTheDocument();
    expect(
      (screen.getByTestId("account-import-source-openai") as HTMLInputElement)
        .checked
    ).toBe(true);
    expect(
      (screen.getByTestId("account-import-source-anthropic") as HTMLInputElement)
        .checked
    ).toBe(false);
  });

  it("sends source_system=anthropic when Anthropic is selected and a folder is dropped", async () => {
    const user = userEvent.setup();
    const json = new File(["[]"], "conversations.json");
    const root = directoryEntry("/export", [
      [fileEntry("/export/conversations.json", json)],
    ]);
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );

    const openaiRadio = screen.getByTestId(
      "account-import-source-openai"
    ) as HTMLInputElement;
    const anthropicRadio = screen.getByTestId(
      "account-import-source-anthropic"
    ) as HTMLInputElement;
    expect(openaiRadio.checked).toBe(true);
    expect(anthropicRadio.checked).toBe(false);

    await user.click(anthropicRadio);

    // Observable rendered selection: the Anthropic radio is now checked and
    // the OpenAI radio is no longer checked. The styled label reinforces the
    // selection but the `checked` attribute is the canonical, library-agnostic
    // proof of active selection.
    expect(anthropicRadio.checked).toBe(true);
    expect(openaiRadio.checked).toBe(false);
    expect(
      screen.getByText("Anthropic (Claude)").closest("label")
    ).toHaveAttribute("style", expect.stringContaining("rgba(34, 197, 94"));

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
    // The submission crossed the existing import-submission seam with the
    // canonical Anthropic source. No `origin_system` field is ever sent.
    expect(coordinator.start).toHaveBeenCalledWith(
      expect.any(Array),
      "account-a",
      "anthropic"
    );
    const [
      startFiles,
      startUserId,
      startSource,
      startOptions,
    ] = coordinator.start.mock.calls[0];
    expect(startFiles).toEqual(expect.any(Array));
    expect(startUserId).toBe("account-a");
    expect(startSource).toBe("anthropic");
    // Only the three documented arguments flow through the seam; any
    // surfaced origin_system would appear here as a fourth argument.
    expect(startOptions).toBeUndefined();
  });

  it("sends source_system=openai when OpenAI is selected and a folder is dropped", async () => {
    const user = userEvent.setup();
    const json = new File(["[]"], "conversations.json");
    const root = directoryEntry("/export", [
      [fileEntry("/export/conversations.json", json)],
    ]);
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );

    const openaiRadio = screen.getByTestId(
      "account-import-source-openai"
    ) as HTMLInputElement;
    const anthropicRadio = screen.getByTestId(
      "account-import-source-anthropic"
    ) as HTMLInputElement;
    expect(openaiRadio.checked).toBe(true);

    // Selecting Anthropic then re-selecting OpenAI must round-trip through
    // the rendered UI without leaking the previous selection.
    await user.click(anthropicRadio);
    expect(anthropicRadio.checked).toBe(true);
    await user.click(openaiRadio);
    expect(openaiRadio.checked).toBe(true);
    expect(anthropicRadio.checked).toBe(false);

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
    expect(coordinator.start).toHaveBeenCalledWith(
      expect.any(Array),
      "account-a",
      "openai"
    );
  });

  it("routes both Anthropic and OpenAI through the same existing submission seam", async () => {
    const user = userEvent.setup();
    const json = new File(["[]"], "conversations.json");
    const root = directoryEntry("/export", [
      [fileEntry("/export/conversations.json", json)],
    ]);
    render(
      <ChatGPTImportModal open onOpenChange={vi.fn()} userName="account-a" />
    );

    // Drive the Anthropic branch through the same modal, then the OpenAI
    // branch. Both must call the same `startOpenAIAccountImport` from
    // `@/features/imports/accountImportCoordinator` — the existing import
    // submission seam — not a separate endpoint or component.
    await user.click(screen.getByTestId("account-import-source-anthropic"));
    fireEvent.drop(
      screen.getByText(/Drop a conversation JSON/).closest("div.rounded-xl")!,
      {
        dataTransfer: {
          items: [{ webkitGetAsEntry: () => root }],
          files: [],
        },
      }
    );
    await waitFor(() => expect(coordinator.start).toHaveBeenCalledTimes(1));
    expect(coordinator.start.mock.calls[0][2]).toBe("anthropic");

    // Reset and drive the OpenAI branch through the same modal.
    coordinator.start.mockClear();
    await user.click(screen.getByTestId("account-import-source-openai"));
    fireEvent.drop(
      screen.getByText(/Drop a conversation JSON/).closest("div.rounded-xl")!,
      {
        dataTransfer: {
          items: [{ webkitGetAsEntry: () => root }],
          files: [],
        },
      }
    );
    await waitFor(() => expect(coordinator.start).toHaveBeenCalledTimes(1));
    expect(coordinator.start.mock.calls[0][2]).toBe("openai");

    // The legacy single-file ChatGPT endpoint must not be involved in
    // either path through the rendered modal.
    expect(apiMocks.post).not.toHaveBeenCalled();
  });

  it("only ever serializes canonical source values when a folder is dropped", async () => {
    const json = new File(["[]"], "conversations.json");
    const root = directoryEntry("/export", [
      [fileEntry("/export/conversations.json", json)],
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
    const sourceSystem = coordinator.start.mock.calls[0][2];
    expect(["openai", "anthropic"]).toContain(sourceSystem);
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
    // The default source is "openai" because the explicit selector defaults
    // to OpenAI; the third argument must always be the canonical source.
    expect(coordinator.start).toHaveBeenCalledWith(
      [{ file: archive, relativePath: "openai-export.zip" }],
      "account-a",
      "openai"
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
