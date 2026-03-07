import { render, screen } from "@testing-library/react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ComposerSelectMenu } from "@/features/chat/components/ComposerSelectMenu";

type DropdownProps = {
  children?: ReactNode;
};

type TriggerProps = DropdownProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: boolean;
  };

type ItemProps = DropdownProps & ButtonHTMLAttributes<HTMLButtonElement>;

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: DropdownProps) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children, asChild, ...props }: TriggerProps) => {
    if (asChild) return children;
    return (
      <button type="button" {...props}>
        {children}
      </button>
    );
  },
  DropdownMenuContent: ({ children }: DropdownProps) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick, ...props }: ItemProps) => (
    <button type="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

describe("ComposerSelectMenu", () => {
  it("renders model options as a single-line picker entry while keeping the Active badge", () => {
    render(
      <ComposerSelectMenu
        ariaLabel="Select model"
        menuLabel="Model"
        valueLabel="Qwen 3.5 27B"
        options={[
          {
            value: "qwen3.5:27b",
            label: "Qwen 3.5 27B",
            description: "qwen3.5:27b",
          },
          {
            value: "qwen3.5:9b",
            label: "Qwen 3.5 9B",
            description: "qwen3.5:9b",
          },
        ]}
        selectedValue="qwen3.5:27b"
        onSelect={vi.fn()}
      />
    );

    expect(screen.getAllByText("Qwen 3.5 27B")).toHaveLength(2);
    expect(screen.getByText("Qwen 3.5 9B")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.queryByText("qwen3.5:27b")).not.toBeInTheDocument();
  });

  it("still shows secondary descriptions for non-model menus", () => {
    render(
      <ComposerSelectMenu
        ariaLabel="Select provider"
        menuLabel="Provider"
        valueLabel="Local"
        options={[
          {
            value: "local",
            label: "Local",
            description: "4 models · Source 127.0.0.1:11434",
          },
        ]}
        selectedValue="local"
        onSelect={vi.fn()}
      />
    );

    expect(screen.getByText("4 models · Source 127.0.0.1:11434")).toBeInTheDocument();
  });
});
