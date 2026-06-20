import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProviderSelect } from "@/components/ProviderSelect";
import api from "@/lib/api";

const setProviderMock = vi.fn();

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
  },
  buildLlmCatalogPath: () => "/llm/catalog",
  getBackendOutageRemainingMs: () => 0,
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
            displayName: "Local",
            enabled: true,
            authorized: true,
            available: true,
            source: {
              kind: "local",
              baseUrl: "http://tailscale-server:11434/v1",
              label: "tailscale-server:11434",
            },
            models: [{ id: "llama3.1:8b", displayName: "Llama 3.1 8B" }],
          },
          {
            id: "groq",
            displayName: "Groq",
            enabled: true,
            authorized: true,
            available: true,
            models: [
              {
                id: "llama-3.1-70b-versatile",
                displayName: "Llama 3.1 70B",
                contextWindow: 128000,
              },
              {
                id: "moonshotai/kimi-k2-instruct-0905",
                displayName: "Kimi K2 Instruct",
              },
              {
                id: "qwen/qwen3-32b",
                displayName: "Qwen3 32B",
              },
            ],
          },
        ],
      },
    });

    const onChange = vi.fn();
    render(<ProviderSelect value="default" onChange={onChange} openSignal={1} />);

    await waitFor(() =>
      expect(api.get).toHaveBeenCalledTimes(1)
    );
    expect(api.get).toHaveBeenCalledWith("/llm/catalog");
    expect(screen.getByText("Select Provider")).toBeInTheDocument();
    expect(screen.getByText("tailscale-server:11434")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Groq" })).toBeInTheDocument();

    fireEvent.click(providerButton("Groq"));
    expect(await screen.findByText("Llama 3.1 70B")).toBeInTheDocument();
    expect(screen.getByText("Kimi K2 Instruct")).toBeInTheDocument();
    expect(screen.getByText("Qwen3 32B")).toBeInTheDocument();

    fireEvent.click(providerButton("Llama 3.1 70B"));
    expect(onChange).toHaveBeenCalledWith("llama-3.1-70b-versatile");
  });

  it("shows Whoosh'd profile-backed local models as selectable model entries", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        providers: [
          {
            id: "local",
            displayName: "Whoosh'd",
            enabled: true,
            authorized: true,
            available: true,
            source: {
              kind: "local",
              baseUrl: "http://host.docker.internal:8000/v1",
              label: "host.docker.internal:8000",
              vendor: "whooshd",
            },
            models: [
              {
                id: "mlx-community/gemma-4-e2b-it-4bit",
                displayName: "Gemma 4 E2B Instruct 4-bit",
                profile_id: "gemma-4-e2b-it-4bit",
                display_vendor: "Whoosh'd",
                supports_chat: true,
                supports_vision: true,
                model_kind: "vision_chat",
                release_supported: false,
              },
              {
                id: "mlx-community/gemma-4-12B-it-OptiQ-4bit",
                displayName: "Gemma 4 12B Instruct OptiQ 4-bit",
                profile_id: "gemma-4-12b-it-optiq-4bit",
                display_vendor: "Whoosh'd",
                supports_chat: true,
                supports_vision: false,
                model_kind: "chat",
                release_supported: false,
              },
              {
                id: "mlx-community/gemma-4-e4b-it-4bit",
                displayName: "Gemma 4 E4B Instruct 4-bit",
                profile_id: "gemma-4-e4b-it-4bit",
                display_vendor: "Whoosh'd",
                supports_chat: true,
                supports_vision: true,
                model_kind: "vision_chat",
                release_supported: false,
              },
              {
                id: "mlx-community/gemma-4-e4b-it-OptiQ-4bit",
                displayName: "Gemma 4 E4B Instruct OptiQ 4-bit",
                profile_id: "gemma-4-e4b-it-optiq-4bit",
                profile_source: "whooshd_model_profile",
                display_vendor: "Whoosh'd",
                supports_chat: true,
                supports_vision: false,
                model_kind: "chat",
                release_supported: false,
                release_posture: {
                  status: "candidate",
                  release_supported: false,
                  proof_required: true,
                },
              },
              {
                id: "mlx-community/gemma-4-12B-it-qat-4bit",
                displayName: "Gemma 4 12B Instruct QAT 4-bit",
                profile_id: "gemma-4-12b-it-qat-4bit",
                display_vendor: "Whoosh'd",
                supports_chat: true,
                supports_vision: true,
                model_kind: "vision_chat",
                release_supported: false,
                release_posture: {
                  status: "candidate",
                  release_supported: false,
                  proof_required: true,
                },
              },
            ],
          },
        ],
      },
    });

    const onChange = vi.fn();
    render(<ProviderSelect value="default" onChange={onChange} openSignal={1} />);

    const whooshdButton = await screen.findByRole("button", {
      name: "Whoosh'd",
    });
    expect(whooshdButton).toBeInTheDocument();
    fireEvent.click(whooshdButton);

    expect(await screen.findByText("Gemma 4 E2B Instruct 4-bit")).toBeInTheDocument();
    expect(screen.getByText("Gemma 4 12B Instruct OptiQ 4-bit")).toBeInTheDocument();
    expect(screen.getByText("Gemma 4 E4B Instruct 4-bit")).toBeInTheDocument();
    expect(screen.getByText("Gemma 4 E4B Instruct OptiQ 4-bit")).toBeInTheDocument();
    expect(screen.getByText("Gemma 4 12B Instruct QAT 4-bit")).toBeInTheDocument();

    fireEvent.click(providerButton("Gemma 4 E4B Instruct OptiQ 4-bit"));
    expect(onChange).toHaveBeenCalledWith(
      "mlx-community/gemma-4-e4b-it-OptiQ-4bit"
    );
  });

  it("refreshes catalog on a new open signal and removes unauthorized providers", async () => {
    const initialCatalog = {
      data: {
        providers: [
          {
            id: "local",
            displayName: "Local",
            enabled: true,
            authorized: true,
            available: true,
            models: [{ id: "llama3.1:8b", displayName: "Llama 3.1 8B" }],
          },
          {
            id: "groq",
            displayName: "Groq",
            enabled: true,
            authorized: true,
            available: true,
            models: [
              {
                id: "llama-3.1-70b-versatile",
                displayName: "Llama 3.1 70B",
              },
            ],
          },
        ],
      },
    };
    const updatedCatalog = {
      data: {
        providers: [
          {
            id: "local",
            displayName: "Local",
            enabled: true,
            authorized: true,
            available: true,
            models: [{ id: "llama3.1:8b", displayName: "Llama 3.1 8B" }],
          },
          {
            id: "groq",
            displayName: "Groq",
            enabled: false,
            authorized: true,
            available: false,
            models: [{ id: "llama-3.1-70b-versatile", displayName: "Llama 3.1 70B" }],
          },
        ],
      },
    };
    (api.get as any).mockResolvedValue(initialCatalog);

    const { rerender } = render(
      <ProviderSelect value="default" onChange={vi.fn()} openSignal={1} />
    );

    expect(await screen.findByRole("button", { name: "Groq" })).toBeInTheDocument();
    (api.get as any).mockResolvedValueOnce(updatedCatalog);

    rerender(<ProviderSelect value="default" onChange={vi.fn()} openSignal={2} />);

    await waitFor(() =>
      expect((api.get as any).mock.calls.length).toBe(2)
    );
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Groq" })).not.toBeInTheDocument();
    });
  });

  it("treats proof-required Whoosh'd profiles as selectable local model entries", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        providers: [
          {
            id: "local",
            displayName: "Whoosh'd",
            enabled: true,
            authorized: true,
            available: true,
            source: {
              kind: "local",
              baseUrl: "http://host.docker.internal:11434/v1",
              label: "host.docker.internal:11434",
            },
            models: [
              {
                id: "mlx-community/gemma-4-12B-it-OptiQ-4bit",
                displayName: "Gemma 4 12B Instruct OptiQ 4-bit",
                profile_id: "gemma-4-12b-it-optiq-4bit",
                profile_source: "whooshd_model_profile",
                display_vendor: "Whoosh'd",
                supports_chat: true,
                model_kind: "chat",
                release_supported: false,
                release_posture: {
                  status: "candidate",
                  release_supported: false,
                  proof_required: true,
                },
              },
            ],
          },
        ],
      },
    });

    render(<ProviderSelect value="default" onChange={vi.fn()} openSignal={1} />);

    const localProvider = await screen.findByRole("button", {
      name: "Whoosh'd",
    });
    expect(localProvider).toBeEnabled();
    fireEvent.click(localProvider);
    expect(
      await screen.findByText("Gemma 4 12B Instruct OptiQ 4-bit")
    ).toBeInTheDocument();
  });

  it("shows a visible error when the provider catalog request fails", async () => {
    (api.get as any).mockRejectedValueOnce(new Error("network down"));

    render(<ProviderSelect value="default" onChange={vi.fn()} openSignal={1} />);

    expect(
      await screen.findByText("Provider catalog unavailable")
    ).toBeInTheDocument();
  });
});
