import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import ThreadList from "../ThreadList";
import {
  SIDEBAR_ORIGIN_OPTIONS,
  type SidebarOriginOption,
} from "../sidebarPresentation";
import type { ConversationOriginSystem } from "@/contracts/conversationOrigin";
import type { Thread } from "@/types/ui";

const SOURCE_OPTIONS: SidebarOriginOption[] = SIDEBAR_ORIGIN_OPTIONS;

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
  originSystem = null,
  originOptions = [],
  onOriginSystemChange,
}: {
  threadOverrides?: Partial<Thread>;
  activeId?: string | null;
  originSystem?: ConversationOriginSystem | null;
  originOptions?: SidebarOriginOption[];
  onOriginSystemChange?: (originSystem: ConversationOriginSystem | null) => void;
} = {}) {
  const handleOriginSystemChange = onOriginSystemChange ?? vi.fn();

  return render(
    <ThreadList
      threads={[createThread(threadOverrides)]}
      activeId={activeId}
      scopeLabel="General"
      originSystem={originSystem}
      originOptions={originOptions}
      onOriginSystemChange={handleOriginSystemChange}
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
  originOptions = SOURCE_OPTIONS,
}: {
  initialFilter?: ConversationOriginSystem | null;
  onChange?: (originSystem: ConversationOriginSystem | null) => void;
  originOptions?: SidebarOriginOption[];
}) {
  const [originSystem, setOriginSystem] = useState<ConversationOriginSystem | null>(initialFilter);

  const handleChange = (nextOriginSystem: ConversationOriginSystem | null) => {
    onChange?.(nextOriginSystem);
    setOriginSystem(nextOriginSystem);
  };

  return (
    <ThreadList
      threads={[createThread()]}
      activeId={null}
      scopeLabel="General"
      originSystem={originSystem}
      originOptions={originOptions}
      onOriginSystemChange={handleChange}
      onSelect={vi.fn()}
      onNewChat={vi.fn()}
      onRename={vi.fn().mockResolvedValue(undefined)}
      onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
      onDelete={vi.fn().mockResolvedValue(undefined)}
    />
  );
}

const ICON_SOURCE_OPTIONS = SIDEBAR_ORIGIN_OPTIONS;

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

  it("keeps the action affordance limited to the selected row", async () => {
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

    expect(screen.queryByRole("button", { name: "Thread actions" })).toBeNull();
  });
});

describe("ThreadList source dock", () => {
  it("keeps the source dock contained and scrollable inside the card", () => {
    render(
      <ThreadList
        threads={[createThread()]}
        activeId={null}
        scopeLabel="General"
        originSystem={null}
        originOptions={SOURCE_OPTIONS}
        onOriginSystemChange={vi.fn()}
        onSelect={vi.fn()}
        onNewChat={vi.fn()}
        onRename={vi.fn().mockResolvedValue(undefined)}
        onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
        onDelete={vi.fn().mockResolvedValue(undefined)}
      />
    );

    const toolbar = screen.getByRole("toolbar", { name: "Canonical conversation origin filter" });
    expect(toolbar).toHaveClass(
      "glass-pill",
      "sidebar-source-navigation",
      "flex",
      "w-full",
      "min-w-0",
      "overflow-hidden"
    );

    const scrollRail = toolbar.querySelector(".overflow-x-auto");
    expect(scrollRail).not.toBeNull();
    expect(scrollRail).toHaveClass("min-w-0", "flex-1", "overflow-x-auto");

    expect(within(toolbar).getByRole("button", { name: "All" })).toHaveClass(
      "sidebar-source-navigation__all"
    );
    for (const label of ["Codexify", "ChatGPT", "Claude"]) {
      expect(within(toolbar).getByRole("button", { name: label })).toHaveClass(
        "sidebar-source-navigation__control"
      );
    }
  });

  it("keeps All mutually exclusive with the canonical source pills", () => {
    const onChange = vi.fn();
    render(<SourceDockHarness onChange={onChange} />);

    const toolbar = screen.getByRole("toolbar", { name: "Canonical conversation origin filter" });
    const allButton = within(toolbar).getByRole("button", { name: "All" });
    const codexifyButton = within(toolbar).getByRole("button", { name: "Codexify" });
    const openaiButton = within(toolbar).getByRole("button", { name: "ChatGPT" });
    const claudeButton = within(toolbar).getByRole("button", { name: "Claude" });

    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(codexifyButton).toHaveAttribute("aria-pressed", "false");
    expect(openaiButton).toHaveAttribute("aria-pressed", "false");
    expect(claudeButton).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(claudeButton);

    expect(onChange).toHaveBeenCalledWith("anthropic");
    expect(allButton).toHaveAttribute("aria-pressed", "false");
    expect(codexifyButton).toHaveAttribute("aria-pressed", "false");
    expect(openaiButton).toHaveAttribute("aria-pressed", "false");
    expect(claudeButton).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(allButton);

    expect(onChange).toHaveBeenLastCalledWith(null);
    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(codexifyButton).toHaveAttribute("aria-pressed", "false");
    expect(openaiButton).toHaveAttribute("aria-pressed", "false");
    expect(claudeButton).toHaveAttribute("aria-pressed", "false");
  });

  it("renders source marks inside the canonical navigation controls", () => {
    const onChange = vi.fn();
    render(<SourceDockHarness onChange={onChange} originOptions={ICON_SOURCE_OPTIONS} />);

    const toolbar = screen.getByRole("toolbar", { name: "Canonical conversation origin filter" });
    const labels = ["Codexify", "ChatGPT", "Claude"] as const;

    for (const label of labels) {
      const button = within(toolbar).getByRole("button", { name: label });
      expect(button).toHaveAttribute("aria-pressed", "false");

      const icon = button.querySelector("img");
      expect(icon).not.toBeNull();
      expect(icon).toHaveAttribute("aria-hidden", "true");
      expect(icon).toHaveClass(
        "block",
        "aspect-square",
        "shrink-0",
        "select-none",
        "object-contain",
        "sidebar-source-navigation__mark"
      );
      expect(button).toHaveClass("sidebar-source-navigation__control");
    }

    const claudeButton = within(toolbar).getByRole("button", { name: "Claude" });
    fireEvent.click(claudeButton);

    expect(onChange).toHaveBeenCalledWith("anthropic");
    expect(claudeButton).toHaveAttribute("aria-pressed", "true");
  });
});
