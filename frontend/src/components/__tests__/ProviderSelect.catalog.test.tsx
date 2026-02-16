import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProviderSelect } from "@/components/ProviderSelect";
import api from "@/lib/api";

const setProviderMock = vi.fn();

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock("@/hooks/usePreferredProvider", () => ({
  usePreferredProvider: () => ({
    provider: null,
    setProvider: setProviderMock,
  }),
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children, ...props }: any) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
  DropdownMenuContent: ({ children }: any) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick, onSelect, disabled, ...props }: any) => (
    <button
      type="button"
      disabled={disabled}
      onClick={(event) => {
        onSelect?.(event);
        onClick?.(event);
      }}
      {...props}
    >
      {children}
    </button>
  ),
}));

function providerButton(label: string): HTMLButtonElement {
  const textNode = screen.getByText(label);
  const button = textNode.closest("button");
  if (!button) {
    throw new Error(`Unable to find button for label: ${label}`);
  }
  return button as HTMLButtonElement;
}

describe("ProviderSelect catalog routing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads /api/llm/catalog on open and drills into provider models", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        providers: [
          {
            id: "local",
            label: "Local",
            authorized: true,
            available: true,
            models: [{ id: "llama3.1:8b", label: "Llama 3.1 8B" }],
          },
          {
            id: "groq",
            label: "Groq",
            authorized: true,
            available: true,
            models: [
              {
                id: "llama-3.1-70b-versatile",
                label: "Llama 3.1 70B",
              },
            ],
          },
        ],
      },
    });

    const onChange = vi.fn();
    render(<ProviderSelect value="default" onChange={onChange} openSignal={1} />);

    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith("/llm/catalog")
    );
    expect(screen.getByText("Local")).toBeInTheDocument();
    expect(screen.getByText("Groq")).toBeInTheDocument();

    fireEvent.click(providerButton("Groq"));
    expect(await screen.findByText("Llama 3.1 70B")).toBeInTheDocument();

    fireEvent.click(providerButton("Llama 3.1 70B"));
    expect(onChange).toHaveBeenCalledWith("llama-3.1-70b-versatile");
  });

  it("refreshes catalog on a new open signal and removes unauthorized providers", async () => {
    (api.get as any)
      .mockResolvedValueOnce({
        data: {
          providers: [
            {
              id: "local",
              label: "Local",
              authorized: true,
              available: true,
              models: [{ id: "llama3.1:8b", label: "Llama 3.1 8B" }],
            },
            {
              id: "groq",
              label: "Groq",
              authorized: true,
              available: true,
              models: [
                {
                  id: "llama-3.1-70b-versatile",
                  label: "Llama 3.1 70B",
                },
              ],
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          providers: [
            {
              id: "local",
              label: "Local",
              authorized: true,
              available: true,
              models: [{ id: "llama3.1:8b", label: "Llama 3.1 8B" }],
            },
          ],
        },
      });

    const { rerender } = render(
      <ProviderSelect value="default" onChange={vi.fn()} openSignal={1} />
    );

    expect(await screen.findByText("Groq")).toBeInTheDocument();

    rerender(<ProviderSelect value="default" onChange={vi.fn()} openSignal={2} />);

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
    await waitFor(() => {
      expect(screen.queryByText("Groq")).not.toBeInTheDocument();
    });
  });
});
