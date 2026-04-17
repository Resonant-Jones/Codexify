import { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";

type SourceMode = "project" | "personal_knowledge";

const SOURCE_OPTIONS = [
  {
    value: "project",
    label: "Project",
    description:
      "Current thread first, then this project if more context is needed.",
  },
  {
    value: "personal_knowledge",
    label: "Personal Knowledge",
    description:
      "Current thread first, then your broader knowledge across projects.",
  },
];

const originalScrollTo = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  "scrollTo"
);
const originalInnerWidth = Object.getOwnPropertyDescriptor(window, "innerWidth");

function restoreScrollTo() {
  if (originalScrollTo) {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", originalScrollTo);
    return;
  }
  delete (HTMLElement.prototype as Record<string, unknown>).scrollTo;
}

describe("Composer source selector", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    restoreScrollTo();
    if (originalInnerWidth) {
      Object.defineProperty(window, "innerWidth", originalInnerWidth);
    }
    vi.restoreAllMocks();
  });

  it("renders the bottom-row Source selector", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        sourceMode="project"
        sourceOptions={SOURCE_OPTIONS}
        onSourceModeChange={vi.fn()}
      />
    );

    expect(
      screen.getByRole("button", { name: "Select retrieval source" })
    ).toHaveTextContent("Project");
  });

  it("shows only Project and Personal Knowledge with the exact descriptions", async () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        sourceMode="project"
        sourceOptions={SOURCE_OPTIONS}
        onSourceModeChange={vi.fn()}
      />
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Select retrieval source" })
    );

    const options = await screen.findAllByRole("menuitem");
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("Project");
    expect(options[1]).toHaveTextContent("Personal Knowledge");
    expect(
      screen.getByText(
        "Current thread first, then this project if more context is needed."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Current thread first, then your broader knowledge across projects."
      )
    ).toBeInTheDocument();
  });

  it("renders the desktop source selector as minimal floating text", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1280,
    });

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        sourceMode="project"
        sourceOptions={SOURCE_OPTIONS}
        onSourceModeChange={vi.fn()}
      />
    );

    const controlsStrip = screen.getByTestId("composer-controls-strip");
    const sourceButton = screen.getByRole("button", {
      name: "Select retrieval source",
    });

    expect(controlsStrip).toHaveClass("flex-none", "w-fit");
    expect(controlsStrip.className).not.toContain("bg-[");
    expect(controlsStrip.style.borderRadius).toBe("");
    expect(controlsStrip.style.borderColor).toBe("");
    expect(sourceButton).toHaveClass(
      "bg-transparent",
      "border-0",
      "rounded-none"
    );
    expect(sourceButton.style.borderRadius).toBe("");
    expect(sourceButton.style.borderColor).toBe("");
    expect(sourceButton.style.color).toBe("var(--text)");
  });

  it("keeps the mobile command bar content-sized and minimal", () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        sourceMode="project"
        sourceOptions={SOURCE_OPTIONS}
        onSourceModeChange={vi.fn()}
      />
    );

    const controlsStrip = screen.getByTestId("composer-controls-strip");
    const actionButton = screen.getByRole("button", {
      name: "Open composer actions",
    });
    const sourceButton = screen.getByRole("button", {
      name: "Select retrieval source",
    });

    expect(controlsStrip).toHaveClass("flex-none", "w-fit");
    expect(controlsStrip.className).not.toContain("bg-[");
    expect(controlsStrip.style.borderRadius).toBe("");
    expect(controlsStrip.style.borderColor).toBe("");

    expect(actionButton).toHaveClass("bg-transparent", "border-0", "rounded-none");
    expect(actionButton.style.borderRadius).toBe("");

    expect(sourceButton).toHaveClass("bg-transparent", "border-0", "rounded-none");
    expect(sourceButton.style.borderRadius).toBe("");
    expect(sourceButton.style.borderColor).toBe("");
  });

  it("keeps the selected source across sends in the same thread-scoped harness", async () => {
    const onSend = vi.fn().mockResolvedValue(undefined);

    function Harness() {
      const [sourceMode, setSourceMode] = useState<SourceMode>("project");
      return (
        <Composer
          onSend={onSend}
          draftScopeKey="thread-42"
          draftValue=""
          threadId={42}
          sourceMode={sourceMode}
          sourceOptions={SOURCE_OPTIONS}
          onSourceModeChange={setSourceMode}
        />
      );
    }

    render(<Harness />);

    fireEvent.click(
      screen.getByRole("button", { name: "Select retrieval source" })
    );
    fireEvent.click(
      await screen.findByRole("menuitem", { name: /Personal Knowledge/i })
    );

    expect(
      screen.getByRole("button", { name: "Select retrieval source" })
    ).toHaveTextContent("Personal Knowledge");

    fireEvent.change(screen.getByTestId("composer-textarea"), {
      target: { value: "Test retrieval source" },
    });
    fireEvent.keyDown(screen.getByTestId("composer-textarea"), {
      key: "Enter",
    });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });
    expect(
      screen.getByRole("button", { name: "Select retrieval source" })
    ).toHaveTextContent("Personal Knowledge");
  });

  it("shows lineage copy and no project/thread toggle in the composer", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        threadId={1}
        projectId={7}
        projectName="Imports"
      />
    );

    expect(screen.getByTestId("composer-lineage-copy")).toHaveTextContent(
      "Send a message to Imports"
    );
    expect(
      screen.queryByRole("button", { name: /Toggle source context/i })
    ).not.toBeInTheDocument();
  });

  it("hides the prompt copy once the user starts typing", () => {
    render(
      <Composer
        onSend={vi.fn()}
        draftScopeKey="thread-1"
        draftValue=""
        projectName="Home Renovation"
      />
    );

    expect(screen.getByTestId("composer-lineage-copy")).toHaveTextContent(
      "Send a message to Home Renovation"
    );

    fireEvent.change(screen.getByTestId("composer-textarea"), {
      target: { value: "Hello" },
    });

    expect(
      screen.queryByTestId("composer-lineage-copy")
    ).not.toBeInTheDocument();
  });
});
