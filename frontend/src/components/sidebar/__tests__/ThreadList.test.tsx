import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";

import ThreadList from "../ThreadList";
import type { Thread } from "@/types/ui";

const SOURCE_OPTIONS = [
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
  provenanceOptions?: Array<{ value: string; label: string }>;
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
}: {
  initialFilter?: string | null;
  onChange?: (sourceKey: string | null) => void;
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
      provenanceOptions={SOURCE_OPTIONS}
      onProvenanceFilterChange={handleChange}
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
}: {
  initialFilter?: string | null;
  onChange?: (sourceKey: string | null) => void;
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
      provenanceOptions={SOURCE_OPTIONS}
      onProvenanceFilterChange={handleChange}
      onSelect={vi.fn()}
      onNewChat={vi.fn()}
      onRename={vi.fn().mockResolvedValue(undefined)}
      onArchiveToggle={vi.fn().mockResolvedValue(undefined)}
      onDelete={vi.fn().mockResolvedValue(undefined)}
    />
  );
}

describe("ThreadList dark mode surface contract", () => {
  afterEach(() => {
    document.documentElement.classList.remove("dark");
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
    renderThreadList({ title: "Project thread" });

    expect(screen.getByText("Project:")).toBeInTheDocument();
    expect(screen.getByText("General")).toBeInTheDocument();
    expect(screen.queryByText("Scope:")).not.toBeInTheDocument();
  });

  it("does not render provider badges in the main thread list", () => {
    const { container } = renderThreadList({
      profileMode: "cloud",
      providerOverride: "openai",
      modelOverride: "gpt-4",
    });

    expect(container.querySelector("svg[data-lucide='bolt'], svg.lucide-bolt")).toBeNull();
    expect(screen.getByText("Research notes")).toBeInTheDocument();
  });

  it("does not render inline provider badges in the thread title", () => {
    const { container } = renderThreadList(
      {
        profileMode: "cloud",
        providerOverride: "anthropic",
        modelOverride: "claude-3.5-sonnet",
      },
      "thread-1"
    );

    expect(container.querySelector(".thread-title svg")).toBeNull();
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
});

describe("ThreadList source dock", () => {
  it("keeps the source dock lane-matched, contained, and scrollable inside the card", () => {
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
    expect(toolbar.parentElement).toHaveClass("pb-2", "px-3", "min-w-0");
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
});
