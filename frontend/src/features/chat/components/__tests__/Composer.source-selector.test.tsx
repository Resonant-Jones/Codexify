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

    fireEvent.change(screen.getByPlaceholderText("Write a message…"), {
      target: { value: "Test retrieval source" },
    });
    fireEvent.keyDown(screen.getByPlaceholderText("Write a message…"), {
      key: "Enter",
    });

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledTimes(1);
    });
    expect(
      screen.getByRole("button", { name: "Select retrieval source" })
    ).toHaveTextContent("Personal Knowledge");
  });
});
