import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ImageGenModal } from "@/components/modals/ImageGenModal";
import api from "@/lib/api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));
const catalog = {
  default_provider: "openai",
  default_model: "test-sunburst",
  providers: [
    {
      id: "openai",
      label: "OpenAI",
      available: true,
      unavailable_reason: null,
      default_model: "test-sunburst",
      models: ["test-sunburst", "test-flare"],
      model_aliases: { sunburst: "test-sunburst", flare: "test-flare" },
    },
  ],
};
beforeEach(() => {
  vi.mocked(api.get).mockResolvedValue({ data: catalog });
  vi.mocked(api.post).mockResolvedValue({
    data: { id: "image-1", src_url: "/media/test.png", model: "test-sunburst" },
  });
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.resetAllMocks();
});

describe("ImageGenModal", () => {
  it("escapes transformed and clipped composer ancestors on mobile", async () => {
    render(
      <div data-testid="clipped-composer" style={{ transform: "translateZ(0)", overflow: "hidden" }}>
        <ImageGenModal open onOpenChange={vi.fn()} />
      </div>
    );

    await screen.findByRole("option", { name: "test-sunburst" });
    const dialog = screen.getByRole("dialog");
    expect(screen.getByTestId("clipped-composer")).not.toContainElement(dialog);
    expect(dialog.parentElement?.parentElement).toBe(document.body);
    expect(dialog).toHaveClass("max-h-[calc(100dvh-2rem)]", "overflow-y-auto");
  });

  it("loads models from the server and submits the chosen model with explicit scope", async () => {
    const user = userEvent.setup(),
      onOpenChange = vi.fn();
    render(<ImageGenModal open onOpenChange={onOpenChange} projectId={42} threadId={9} />);
    await screen.findByRole("option", { name: "test-flare" });
    await user.type(screen.getByLabelText("Prompt"), "A moon garden");
    await user.selectOptions(screen.getByLabelText("Model"), "test-flare");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(api.post).toHaveBeenCalledWith(
      "/api/media/generate/image",
      {
        prompt: "A moon garden",
        provider: "openai",
        model: "test-flare",
        project_id: 42,
        thread_id: 9,
      },
      { timeout: 210_000 }
    );
  });
  it("uses the chat callback so a new thread can be created before generation", async () => {
    const user = userEvent.setup(),
      onGenerate = vi.fn().mockResolvedValue(undefined);
    render(
      <ImageGenModal open onOpenChange={vi.fn()} initialPrompt="Moon" onGenerate={onGenerate} />
    );
    await screen.findByRole("option", { name: "test-sunburst" });
    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(onGenerate).toHaveBeenCalledWith({
      prompt: "Moon",
      provider: "openai",
      model: "test-sunburst",
    });
    expect(api.post).not.toHaveBeenCalled();
  });
  it("does not invent project or thread 1", async () => {
    const user = userEvent.setup();
    render(<ImageGenModal open onOpenChange={vi.fn()} initialPrompt="Moon" />);
    await screen.findByRole("option", { name: "test-sunburst" });
    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a project or thread");
    expect(api.post).not.toHaveBeenCalled();
  });
  it("disables a provider blocked by runtime policy", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        ...catalog,
        providers: [{ ...catalog.providers[0], available: false, unavailable_reason: "Blocked" }],
      },
    });
    render(<ImageGenModal open onOpenChange={vi.fn()} initialPrompt="Moon" />);
    await screen.findByRole("option", { name: "test-sunburst" });
    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("unavailable in this runtime");
  });
  it("preserves the prompt after failure and prevents duplicate submissions", async () => {
    let fail!: (reason: Error) => void;
    const onGenerate = vi.fn(
      () =>
        new Promise<void>((_, reject) => {
          fail = reject;
        })
    );
    const onOpenChange = vi.fn();
    render(
      <ImageGenModal
        open
        onOpenChange={onOpenChange}
        initialPrompt="Moon"
        onGenerate={onGenerate}
      />
    );
    await screen.findByRole("option", { name: "test-sunburst" });
    fireEvent.submit(screen.getByRole("dialog"));
    fireEvent.submit(screen.getByRole("dialog"));
    expect(onGenerate).toHaveBeenCalledTimes(1);
    fail(new Error("Provider unavailable"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Provider unavailable");
    expect(screen.getByLabelText("Prompt")).toHaveValue("Moon");
    expect(onOpenChange).not.toHaveBeenCalled();
  });
});
