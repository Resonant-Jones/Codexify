import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Composer } from "@/features/chat/components/Composer";

vi.mock("@/lib/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

const defaultProps = {
  onSend: vi.fn(),
  isSending: false,
  isTurnInFlight: false,
};

let textareaGeometry = { clientHeight: 96, scrollHeight: 96 };
let originalClientHeight: PropertyDescriptor | undefined;
let originalScrollHeight: PropertyDescriptor | undefined;

beforeEach(() => {
  textareaGeometry = { clientHeight: 96, scrollHeight: 96 };
  originalClientHeight = Object.getOwnPropertyDescriptor(
    HTMLTextAreaElement.prototype,
    "clientHeight",
  );
  originalScrollHeight = Object.getOwnPropertyDescriptor(
    HTMLTextAreaElement.prototype,
    "scrollHeight",
  );
  Object.defineProperty(HTMLTextAreaElement.prototype, "clientHeight", {
    configurable: true,
    get: () => textareaGeometry.clientHeight,
  });
  Object.defineProperty(HTMLTextAreaElement.prototype, "scrollHeight", {
    configurable: true,
    get: () => textareaGeometry.scrollHeight,
  });
});

afterEach(() => {
  if (originalClientHeight) {
    Object.defineProperty(
      HTMLTextAreaElement.prototype,
      "clientHeight",
      originalClientHeight,
    );
  }
  if (originalScrollHeight) {
    Object.defineProperty(
      HTMLTextAreaElement.prototype,
      "scrollHeight",
      originalScrollHeight,
    );
  }
  vi.clearAllMocks();
  window.localStorage.clear();
});

describe("Composer expansion", () => {
  it("keeps the affordance and its clearance hidden for empty and short drafts", () => {
    const { rerender } = render(<Composer {...defaultProps} />);

    const textarea = screen.getByPlaceholderText("Write a message…");
    expect(screen.queryByRole("button", { name: "Expand composer" })).toBeNull();
    expect(textarea.style.getPropertyValue("--composer-text-right-pad")).toBe(
      "var(--composer-text-pad-x, 14px)",
    );

    rerender(<Composer {...defaultProps} draftValue="Short draft" />);

    expect(screen.queryByRole("button", { name: "Expand composer" })).toBeNull();
    expect(textarea.style.getPropertyValue("--composer-text-right-pad")).toBe(
      "var(--composer-text-pad-x, 14px)",
    );
  });

  it("reveals expansion only when collapsed rendered geometry overflows", () => {
    const { rerender } = render(<Composer {...defaultProps} draftValue="Short draft" />);

    expect(screen.queryByRole("button", { name: "Expand composer" })).toBeNull();

    textareaGeometry = { clientHeight: 96, scrollHeight: 192 };
    rerender(<Composer {...defaultProps} draftValue="A longer draft" />);

    expect(screen.getByRole("button", { name: "Expand composer" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(
      screen
        .getByPlaceholderText("Write a message…")
        .style.getPropertyValue("--composer-text-right-pad"),
    ).toContain(
      "composer-control-size",
    );
  });

  it("expands the existing focused textarea without changing draft or send behavior", () => {
    textareaGeometry = { clientHeight: 96, scrollHeight: 192 };
    const onSend = vi.fn();
    const onDraftValueChange = vi.fn();
    const { container } = render(
      <Composer
        {...defaultProps}
        draftValue="Long enough to overflow"
        onSend={onSend}
        onDraftValueChange={onDraftValueChange}
        draftSyncDebounceMs={10_000}
      />,
    );

    const textarea = screen.getByPlaceholderText("Write a message…");
    textarea.focus();
    fireEvent.click(screen.getByRole("button", { name: "Expand composer" }));

    expect(screen.getByRole("button", { name: "Collapse composer" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByPlaceholderText("Write a message…")).toBe(textarea);
    expect(textarea).toHaveValue("Long enough to overflow");
    expect(textarea).toHaveFocus();
    expect(onSend).not.toHaveBeenCalled();
    expect(onDraftValueChange).not.toHaveBeenCalled();
    expect(container.querySelectorAll("textarea")).toHaveLength(1);
    expect(textarea.getAttribute("style")).toContain("--composer-expanded-max-h");
  });

  it("keeps the affordance available after a manual collapse of overflowing content", () => {
    textareaGeometry = { clientHeight: 96, scrollHeight: 192 };
    render(<Composer {...defaultProps} draftValue="Long enough to overflow" />);

    fireEvent.click(screen.getByRole("button", { name: "Expand composer" }));
    fireEvent.click(screen.getByRole("button", { name: "Collapse composer" }));

    expect(screen.getByRole("button", { name: "Expand composer" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.getByPlaceholderText("Write a message…")).toHaveValue(
      "Long enough to overflow",
    );
  });

  it("auto-collapses and hides the affordance when an expanded draft shrinks", () => {
    textareaGeometry = { clientHeight: 96, scrollHeight: 192 };
    const { rerender, container } = render(
      <Composer {...defaultProps} draftValue="Long enough to overflow" />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Expand composer" }));
    textareaGeometry = { clientHeight: 96, scrollHeight: 48 };
    rerender(<Composer {...defaultProps} draftValue="Short draft" />);

    expect(screen.queryByRole("button", { name: "Collapse composer" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Expand composer" })).toBeNull();
    expect(container.querySelector("[data-composer-expanded='true']")).toBeNull();
  });

  it("reevaluates an externally synchronized draft without replacing the textarea", () => {
    const { rerender } = render(<Composer {...defaultProps} draftValue="Short draft" />);
    const textarea = screen.getByPlaceholderText("Write a message…");

    textareaGeometry = { clientHeight: 96, scrollHeight: 192 };
    rerender(
      <Composer
        {...defaultProps}
        draftValue="Externally synchronized long draft"
      />,
    );

    expect(screen.getByPlaceholderText("Write a message…")).toBe(textarea);
    expect(textarea).toHaveValue("Externally synchronized long draft");
    expect(screen.getByRole("button", { name: "Expand composer" })).toBeInTheDocument();
    expect(defaultProps.onSend).not.toHaveBeenCalled();
  });

  it("contains expansion to the desktop surface", () => {
    textareaGeometry = { clientHeight: 96, scrollHeight: 192 };
    const { rerender } = render(
      <Composer {...defaultProps} draftValue="Long enough to overflow" />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Expand composer" }));
    rerender(
      <Composer
        {...defaultProps}
        compactMobile
        draftValue="Long enough to overflow"
      />,
    );

    expect(screen.queryByRole("button", { name: "Expand composer" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Collapse composer" })).toBeNull();
    expect(screen.queryByTestId("composer-expand-toggle")).toBeNull();
  });
});
