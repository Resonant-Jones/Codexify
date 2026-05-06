import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import ThreadList from "../ThreadList";
import {
  collectSidebarProvenanceOptions,
  type SidebarProvenanceOption,
} from "../sidebarPresentation";
import type { Thread } from "@/types/ui";

const SOURCE_OPTIONS: SidebarProvenanceOption[] = [
  { value: "chatgpt", label: "ChatGPT" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
];

function createThread(overrides: Partial<Thread> = {}): Thread {
  return {
    id: "thread-1",
    title: "Research notes",
    lastMessage: "Valid content should read as content.",
    unread: 0,
    participants: [],
    messages: [],
    ...overrides,
  };
}

function renderThreadList({
  threadOverrides = {},
  activeId = null,
  provenanceFilter = null,
  provenanceOptions = [],
  onProvenanceFilterChange,
}: {
  threadOverrides?: Partial<Thread>;
  activeId?: string | null;
  provenanceFilter?: string | null;
  provenanceOptions?: SidebarProvenanceOption[];
  onProvenanceFilterChange?: (sourceKey: string | null) => void;
} = {}) {
  const handleProvenanceFilterChange = onProvenanceFilterChange ?? vi.fn();

  return render(
    <ThreadList
      threads={[createThread(threadOverrides)]}
      activeId={activeId}
      scopeLabel="General"
      provenanceFilter={provenanceFilter}
      provenanceOptions={provenanceOptions}
      onProvenanceFilterChange={handleProvenanceFilterChange}
      onSelect={vi.fn()}
      onNewChat={vi.fn()}
      onRename={vi.fn().mockResolvedValue(undefined)}
      onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
      onDelete={vi.fn().mockResolvedValue(undefined)}
    />
  );
}

function SourceDockHarness({
  initialFilter = null,
  onChange,
  provenanceOptions = SOURCE_OPTIONS,
}: {
  initialFilter?: string | null;
  onChange?: (sourceKey: string | null) => void;
  provenanceOptions?: SidebarProvenanceOption[];
}) {
  const [provenanceFilter, setProvenanceFilter] = useState<string | null>(initialFilter);

  const handleChange = (sourceKey: string | null) => {
    onChange?.(sourceKey);
    setProvenanceFilter(sourceKey);
  };

  return (
    <ThreadList
      threads={[createThread()]}
      activeId={null}
      scopeLabel="General"
      provenanceFilter={provenanceFilter}
      provenanceOptions={provenanceOptions}
      onProvenanceFilterChange={handleChange}
      onSelect={vi.fn()}
      onNewChat={vi.fn()}
      onRename={vi.fn().mockResolvedValue(undefined)}
      onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
      onDelete={vi.fn().mockResolvedValue(undefined)}
    />
  );
}

const ICON_SOURCE_OPTIONS = collectSidebarProvenanceOptions([
  createThread({ id: "thread-chatgpt", metadata: { import_source: "chatgpt" } }),
  createThread({ id: "thread-openai", metadata: { source: "openai" } }),
  createThread({ id: "thread-gemini", metadata: { provider: "gemini" } }),
  createThread({ id: "thread-codexify", metadata: { source: "codexify" } }),
]);

describe("ThreadList dark mode surface contract", () => {
  afterEach(() => {
    document.documentElement.classList.remove("dark");
  });

  it("keeps thread rows compact and title-first", () => {
    renderThreadList();

    const guide = screen.getByTestId("thread-rail-guide");
    const tile = screen.getByTestId("thread-tile-thread-1");

    expect(guide).toHaveClass("bg-transparent", "shadow-none", "border-0", "rounded-none");
    expect(guide.getAttribute("style")).toContain("background: transparent");
    expect(guide.getAttribute("style")).toContain("box-shadow: none");
    expect(tile).toHaveStyle({
      minHeight: "44px",
      background: "var(--panel-bg)",
    });
    expect(within(tile).getByText("Research notes")).toBeInTheDocument();
    expect(within(tile).queryByText("Valid content should read as content.")).toBeNull();
  });

  it("keeps the light-mode thread tile on the default panel background", () => {
    renderThreadList();

    expect(screen.getByTestId("thread-tile-thread-1")).toHaveStyle({
      background: "var(--panel-bg)",
    });
  });

  it("uses the darker sheet surface and white text in dark mode", () => {
    document.documentElement.classList.add("dark");

    renderThreadList();

    const tile = screen.getByTestId("thread-tile-thread-1");
    expect(tile).toHaveStyle({ background: "var(--panel-sheet)" });
    expect(tile).toHaveClass("dark:text-white");
  });

  it("keeps the active dark-mode tile anchored to the darker sheet token", () => {
    document.documentElement.classList.add("dark");

    renderThreadList({ activeId: "thread-1" });

    expect(screen.getByTestId("thread-tile-thread-1")).toHaveStyle({
      background: "color-mix(in oklab, var(--accent) 16%, var(--panel-sheet) 84%)",
    });
  });

  it("labels the active project context as project instead of scope", () => {
    renderThreadList({ threadOverrides: { title: "Project thread" } });

    expect(screen.getByText("Project:")).toBeInTheDocument();
    expect(screen.getByText("General")).toBeInTheDocument();
    expect(screen.queryByText("Scope:")).not.toBeInTheDocument();
  });

  it("does not render provider badges in the main thread list", () => {
    const { container } = renderThreadList({
      threadOverrides: {
        profileMode: "cloud",
        providerOverride: "openai",
        modelOverride: "gpt-4",
      },
    });

    expect(container.querySelector("svg[data-lucide='bolt'], svg.lucide-bolt")).toBeNull();
    expect(screen.getByText("Research notes")).toBeInTheDocument();
  });

  it("does not render inline provider badges in the thread title", () => {
    const { container } = renderThreadList({
      threadOverrides: {
        profileMode: "cloud",
        providerOverride: "anthropic",
        modelOverride: "claude-3.5-sonnet",
      },
      activeId: "thread-1",
    });

    expect(container.querySelector(".thread-title svg")).toBeNull();
  });
});

describe("ThreadList thread actions menu", () => {
  it("shows the kebab only on the selected thread and keeps the action menu usable", async () => {
    const onSelect = vi.fn();
    const onRename = vi.fn().mockResolvedValue(undefined);
    const onArchiveToggle = vi.fn().mockResolvedValue(undefined);
    const onDelete = vi.fn().mockResolvedValue(undefined);
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("Updated research notes");
    const user = userEvent.setup();

    render(
      <ThreadList
        threads={[
          createThread({ id: "thread-1", title: "First thread" }),
          createThread({ id: "thread-2", title: "Second thread" }),
        ]}
        activeId={"thread-1"}
        scopeLabel="General"
        onSelect={onSelect}
        onNewChat={vi.fn()}
        onRename={onRename}
        onArchiveToggle={onArchiveToggle}
        onDelete={onDelete}
      />
    );

    expect(screen.getAllByRole("button", { name: "Thread actions" })).toHaveLength(1);

    const selectedRow = screen.getByTestId("thread-row-thread-1");
    const selectedTile = within(selectedRow).getByTestId("thread-tile-thread-1");
    const selectedTitle = within(selectedTile).getByText("First thread");
    const selectedActions = within(selectedRow).getByRole("button", { name: "Thread actions" });

    expect(selectedTile).toHaveStyle({ minHeight: "44px" });
    expect(selectedActions).toHaveStyle({
      background: "color-mix(in oklab, var(--panel-bg) 84%, var(--text) 16%)",
    });
    expect(selectedRow).toContainElement(selectedActions);
    expect(
      selectedTitle.compareDocumentPosition(selectedActions) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(screen.queryByTestId("thread-row-thread-2")?.contains(selectedActions)).toBe(false);

    await user.click(screen.getByRole("button", { name: "Thread actions" }));

    const menu = await screen.findByRole("menu");
    expect(menu).toBeVisible();

    await user.click(within(menu).getByRole("button", { name: "Rename" }));

    expect(promptSpy).toHaveBeenCalledWith("Rename thread", "First thread");
    expect(onRename).toHaveBeenCalledWith("thread-1", "Updated research notes");
    expect(onSelect).not.toHaveBeenCalled();
    expect(onArchiveToggle).not.toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();

    promptSpy.mockRestore();
  });

  it("reveals the action affordance while an unselected row has keyboard focus", async () => {
    const user = userEvent.setup();

    render(
      <ThreadList
        threads={[
          createThread({ id: "thread-1", title: "First thread" }),
          createThread({ id: "thread-2", title: "Second thread" }),
        ]}
        activeId={null}
        scopeLabel="General"
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
        onRename={vi.fn().mockResolvedValue(undefined)}
        onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />
    );

    expect(screen.queryByRole("button", { name: "Thread actions" })).toBeNull();

    await user.tab();
    await user.tab();

    expect(await screen.findByRole("button", { name: "Thread actions" })).toBeVisible();
    expect(screen.getByTestId("thread-row-thread-1")).toContainElement(
      screen.getByRole("button", { name: "Thread actions" })
    );
  });
});

describe("ThreadList source dock", () => {
  it("keeps the source dock contained and scrollable inside the card", () => {
    render(
      <ThreadList
        threads={[createThread()]}
        activeId={null}
        scopeLabel="General"
        provenanceFilter={null}
        provenanceOptions={SOURCE_OPTIONS}
        onProvenanceFilterChange={vi.fn()}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
        onRename={vi.fn().mockResolvedValue(undefined)}
        onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />
    );

    const toolbar = screen.getByRole("toolbar", { name: "Imported source filter" });
    expect(toolbar).toHaveClass("glass-pill", "flex", "w-full", "min-w-0", "overflow-hidden");

    const scrollRail = toolbar.querySelector(".overflow-x-auto");
    expect(scrollRail).not.toBeNull();
    expect(scrollRail).toHaveClass("min-w-0", "flex-1", "overflow-x-auto");
  });

  it("keeps All mutually exclusive with the canonical source pills", () => {
    const onChange = vi.fn();
    render(<SourceDockHarness onChange={onChange} />);

    const toolbar = screen.getByRole("toolbar", { name: "Imported source filter" });
    const allButton = within(toolbar).getByRole("button", { name: "All" });
    const chatgptButton = within(toolbar).getByRole("button", { name: "ChatGPT" });
    const openaiButton = within(toolbar).getByRole("button", { name: "OpenAI" });

    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(chatgptButton).toHaveAttribute("aria-pressed", "false");
    expect(openaiButton).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(chatgptButton);

    expect(onChange).toHaveBeenCalledWith("chatgpt");
    expect(allButton).toHaveAttribute("aria-pressed", "false");
    expect(chatgptButton).toHaveAttribute("aria-pressed", "true");
    expect(openaiButton).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(allButton);

    expect(onChange).toHaveBeenLastCalledWith(null);
    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(chatgptButton).toHaveAttribute("aria-pressed", "false");
    expect(openaiButton).toHaveAttribute("aria-pressed", "false");
  });

  it("renders compact source logos inside the provenance buttons", () => {
    const onChange = vi.fn();
    render(<SourceDockHarness onChange={onChange} provenanceOptions={ICON_SOURCE_OPTIONS} />);

    const toolbar = screen.getByRole("toolbar", { name: "Imported source filter" });
    const labels = ["ChatGPT", "OpenAI", "Gemini", "Codexify"] as const;

    for (const label of labels) {
      const button = within(toolbar).getByRole("button", { name: label });
      expect(button).toHaveAttribute("aria-pressed", "false");

      const icon = button.querySelector("img");
      expect(icon).not.toBeNull();
      expect(icon).toHaveAttribute("aria-hidden", "true");
      expect(icon).toHaveClass(
        "block",
        "h-4",
        "w-4",
        "aspect-square",
        "max-h-4",
        "max-w-4",
        "shrink-0",
        "select-none",
        "object-contain"
      );
    }

    const geminiButton = within(toolbar).getByRole("button", { name: "Gemini" });
    fireEvent.click(geminiButton);

    expect(onChange).toHaveBeenCalledWith("gemini");
    expect(geminiButton).toHaveAttribute("aria-pressed", "true");
  });
});
