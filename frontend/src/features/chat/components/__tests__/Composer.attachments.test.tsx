import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";
import composerSource from "@/features/chat/components/Composer.tsx?raw";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

/**
 * Models the browser-owned FileList lifetime that jsdom does not reproduce.
 *
 * In a real browser the FileList handed back by `<input type="file">` is a
 * live collection: assigning `""` to the input's `value` clears the list
 * before subsequent reads. Plain arrays in tests never exhibit this, which is
 * why the regression slipped through. The object below exposes the surface
 * that `Array.from` / `FileList` consumers depend on (length, indexed access,
 * iterator) while letting us empty it on demand.
 */
function createLiveFileList(initial: File[]): {
  list: FileList;
  clear: () => void;
} {
  let items: File[] = [...initial];
  const list = {
    get length() {
      return items.length;
    },
    item(index: number) {
      return items[index] ?? null;
    },
    *[Symbol.iterator]() {
      yield* items;
    },
  } as unknown as FileList;
  return {
    list,
    clear: () => {
      items = [];
    },
  };
}

/**
 * Wires a hidden `<input type="file">` so it behaves like a browser-owned
 * picker: reading `.files` returns the live collection, and resetting
 * `.value` to `""` empties that collection in place. This is the exact
 * lifetime defect described in issue #607.
 */
function installBrowserFileInput(
  input: HTMLInputElement,
  files: File[]
): { list: FileList; clear: () => void } {
  const { list, clear } = createLiveFileList(files);
  Object.defineProperty(input, "files", {
    configurable: true,
    value: list,
  });
  let storedValue = "";
  Object.defineProperty(input, "value", {
    configurable: true,
    enumerable: true,
    get() {
      return storedValue;
    },
    set(next: string) {
      storedValue = next;
      if (next === "") clear();
    },
  });
  return { list, clear };
}

function getFileInput(container: HTMLElement): HTMLInputElement {
  return container.querySelector('input[type="file"]') as HTMLInputElement;
}

function getAttachmentTiles(): HTMLElement[] {
  return screen.getAllByLabelText("Remove attachment");
}

function getTileForButton(button: HTMLElement): HTMLElement {
  return button.closest("[title]") as HTMLElement;
}

describe("Composer attachment staging", () => {
  const originalCreateObjectURL = Object.getOwnPropertyDescriptor(
    window.URL,
    "createObjectURL"
  );

  beforeEach(() => {
    // jsdom does not implement blob URL creation; give the image preview a
    // stable, revocable-looking string so the `<img>` renders a real src.
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn((file: File) => `blob:${file.name}`),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    if (originalCreateObjectURL) {
      Object.defineProperty(
        window.URL,
        "createObjectURL",
        originalCreateObjectURL
      );
    }
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("copies picker files before the input reset so the live FileList cannot drop them", () => {
    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const fileInput = getFileInput(container);
    const image = new File(["pixel"], "photo.png", { type: "image/png" });
    installBrowserFileInput(fileInput, [image]);

    fireEvent.change(fileInput);

    // Buggy implementation retained the live FileList across the reset, so
    // the staged attachment would vanish. The normalized copy survives.
    expect(fileInput.value).toBe("");
    const removeButton = screen.getByLabelText("Remove attachment");
    const tile = getTileForButton(removeButton);
    expect(tile.getAttribute("title")).toBe("photo.png");
    expect(tile.querySelector("img")).toHaveAttribute("src", "blob:photo.png");
  });

  it("stages a document through the file picker and renders a document tile", () => {
    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const fileInput = getFileInput(container);
    const document = new File(["hello world"], "notes.txt", {
      type: "text/plain",
    });
    installBrowserFileInput(fileInput, [document]);

    fireEvent.change(fileInput);

    const tile = getTileForButton(screen.getByLabelText("Remove attachment"));
    expect(tile.getAttribute("title")).toBe("notes.txt");
    expect(tile.querySelector("img")).toBeNull();
  });

  it("stages every unique file when multiple are picked at once", () => {
    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const fileInput = getFileInput(container);
    const first = new File(["a"], "alpha.txt", { type: "text/plain" });
    const second = new File(["b"], "bravo.png", { type: "image/png" });
    installBrowserFileInput(fileInput, [first, second]);

    fireEvent.change(fileInput);

    expect(getAttachmentTiles()).toHaveLength(2);
  });

  it("allows re-selecting the same file after its staged attachment is removed", () => {
    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const fileInput = getFileInput(container);
    const file = new File(["payload"], "report.pdf", {
      type: "application/pdf",
    });

    installBrowserFileInput(fileInput, [file]);
    fireEvent.change(fileInput);
    expect(getAttachmentTiles()).toHaveLength(1);

    fireEvent.click(screen.getByLabelText("Remove attachment"));
    expect(screen.queryByLabelText("Remove attachment")).not.toBeInTheDocument();

    // A fresh picker interaction yields a brand-new live FileList that must
    // stage cleanly even though the underlying File object matches the prior
    // selection by name/size/type.
    installBrowserFileInput(fileInput, [file]);
    fireEvent.change(fileInput);
    expect(getAttachmentTiles()).toHaveLength(1);
  });

  it("keeps duplicate detection based on filename, size, and MIME type", () => {
    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const fileInput = getFileInput(container);
    const file = new File(["dup"], "twin.txt", { type: "text/plain" });

    installBrowserFileInput(fileInput, [file]);
    fireEvent.change(fileInput);
    expect(getAttachmentTiles()).toHaveLength(1);

    // Selecting the same file again (without removing the first) must be a
    // no-op because the duplicate signature matches.
    installBrowserFileInput(fileInput, [file]);
    fireEvent.change(fileInput);
    expect(getAttachmentTiles()).toHaveLength(1);

    // A genuinely different file still stages alongside the first.
    const other = new File(["other"], "other.txt", { type: "text/plain" });
    installBrowserFileInput(fileInput, [other]);
    fireEvent.change(fileInput);
    expect(getAttachmentTiles()).toHaveLength(2);
  });

  it("routes drag/drop through the same immutable staging path as the picker", () => {
    const { container } = render(
      <Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />
    );

    const composerRoot = container.querySelector(
      "[data-composer-root]"
    ) as HTMLElement;
    const dropped = createLiveFileList([
      new File(["px"], "drop.png", { type: "image/png" }),
      new File(["doc"], "drop.txt", { type: "text/plain" }),
    ]).list;

    fireEvent.drop(composerRoot, {
      dataTransfer: { files: dropped },
    });

    expect(getAttachmentTiles()).toHaveLength(2);
    const imageTile = getTileForButton(getAttachmentTiles()[0]);
    const documentTile = getTileForButton(getAttachmentTiles()[1]);
    expect(imageTile.querySelector("img")).toHaveAttribute(
      "src",
      "blob:drop.png"
    );
    expect(documentTile.querySelector("img")).toBeNull();
  });

  it("keeps paste staging attachments through the shared immutable path", () => {
    render(<Composer onSend={vi.fn()} draftScopeKey="tab-1" draftValue="" />);

    const textarea = screen.getByTestId("composer-textarea");
    const pasted = createLiveFileList([
      new File(["clip"], "clipboard.png", { type: "image/png" }),
    ]).list;

    fireEvent.paste(textarea, {
      clipboardData: { files: pasted },
    });

    const tile = getTileForButton(screen.getByLabelText("Remove attachment"));
    expect(tile.getAttribute("title")).toBe("clipboard.png");
    expect(tile.querySelector("img")).toHaveAttribute(
      "src",
      "blob:clipboard.png"
    );
  });

  it("does not depend on FileList or live browser collections inside stageFiles", () => {
    // Guard against regressing the staging contract: stageFiles must accept an
    // immutable normalized File[] so the input reset can never reach it.
    expect(composerSource).toContain(
      "function stageFiles(files: readonly File[])"
    );
    expect(composerSource).not.toContain("stageFiles(e.dataTransfer.files)");
    expect(composerSource).not.toContain("stageFiles(e.clipboardData");
    expect(composerSource).toContain("Array.from(e.currentTarget.files ?? [])");
    expect(composerSource).toContain("Array.from(e.dataTransfer?.files ?? [])");
    expect(composerSource).toContain(
      "Array.from(e.clipboardData?.files ?? [])"
    );
  });
});
