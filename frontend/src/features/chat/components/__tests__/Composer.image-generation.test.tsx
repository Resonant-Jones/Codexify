import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Composer } from "../Composer";
import api from "@/lib/api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => {
  vi.mocked(api.get).mockResolvedValue({
    data: {
      default_provider: "openai",
      default_model: "sunburst-model",
      providers: [
        {
          id: "openai",
          label: "OpenAI",
          available: true,
          unavailable_reason: null,
          models: ["sunburst-model", "flare-model"],
          default_model: "sunburst-model",
          model_aliases: { sunburst: "sunburst-model", flare: "flare-model" },
        },
      ],
    },
  });
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
  vi.resetAllMocks();
});

it.each(["/sunburst A fox", "/imagine A fox"])(
  "passes image intent for %s",
  async (draft) => {
    const user = userEvent.setup(),
      onSend = vi.fn().mockResolvedValue(undefined);
    render(<Composer onSend={onSend} slashCommandLibrary={library} />);
    fireEvent.change(screen.getByTestId("composer-textarea"), { target: { value: draft } });
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() =>
      expect(onSend).toHaveBeenCalledWith(
        draft,
        expect.objectContaining({
          imageGeneration: expect.objectContaining({
            prompt: draft.startsWith("/") ? "A fox" : draft,
          }),
        })
      )
    );
  }
);

it("opens the model-specific prompt form for a bare slash command", async () => {
  const user = userEvent.setup(),
    onSend = vi.fn().mockResolvedValue(undefined);
  render(<Composer onSend={onSend} slashCommandLibrary={library} />);
  fireEvent.change(screen.getByTestId("composer-textarea"), { target: { value: "/flare" } });
  await user.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByRole("option", { name: "flare-model" });
  expect(screen.getByLabelText("Model")).toHaveValue("flare-model");
  expect(onSend).not.toHaveBeenCalled();
  await user.type(screen.getByLabelText("Prompt"), "A fox");
  await user.click(screen.getByRole("button", { name: "Generate" }));
  expect(onSend).toHaveBeenCalledWith("A fox", {
    imageGeneration: { prompt: "A fox", provider: "openai", model: "flare-model" },
  });
});

it("uses the existing Generate image action", async () => {
  const user = userEvent.setup(),
    onSend = vi.fn().mockResolvedValue(undefined);
  render(<Composer onSend={onSend} slashCommandLibrary={library} />);
  await user.click(screen.getByRole("button", { name: "Open composer actions" }));
  await user.click(screen.getByRole("menuitem", { name: "Generate image" }));
  await screen.findByRole("option", { name: "sunburst-model" });
  await user.type(screen.getByLabelText("Prompt"), "A fox");
  await user.click(screen.getByRole("button", { name: "Generate" }));
  expect(onSend).toHaveBeenCalledWith("A fox", {
    imageGeneration: { prompt: "A fox", provider: "openai", model: "sunburst-model" },
  });
});

it("keeps quoted examples on the normal chat path", async () => {
  const user = userEvent.setup(),
    onSend = vi.fn().mockResolvedValue(undefined);
  render(<Composer onSend={onSend} slashCommandLibrary={library} />);
  fireEvent.change(screen.getByTestId("composer-textarea"), {
    target: { value: "> generate an image of a cat" },
  });
  await user.click(screen.getByRole("button", { name: "Send" }));
  expect(onSend.mock.calls[0][1].imageGeneration).toBeUndefined();
});

const imageCommands = ["image", "sunburst", "flare"].map((id) => ({
  id, token: `/${id}`, scaffold: `/${id}`, label: id,
  description: "Image command", aliases: id === "image" ? ["imagine"] : [],
  keywords: ["image"], interactionModes: ["chat_intent"],
  effects: { intentKind: "conversation" as const, retrievalHint: "none" as const },
  availability: "unknown" as const, availabilityReason: "eligibility_not_evaluated",
}));
const library = { status: "ready" as const, manifest: {
  schemaVersion: 1 as const, manifestRevision: "image-fixture", commands: imageCommands,
}};

it.each(["image", "sunburst", "flare"])("discovers /%s without dispatching on selection", async (id) => {
  const user = userEvent.setup(), onSend = vi.fn();
  render(<Composer onSend={onSend} slashCommandLibrary={library} />);
  await user.click(screen.getByTestId("composer-textarea"));
  fireEvent.change(screen.getByTestId("composer-textarea"), { target: { value: `/${id}` } });
  const option = await screen.findByRole("option", { name: new RegExp(id) });
  await user.click(option);
  expect(screen.getByTestId("composer-textarea")).toHaveValue(`/${id}`);
  expect(onSend).not.toHaveBeenCalled();
  expect(api.post).not.toHaveBeenCalled();
});

it("preserves a manifest denial on explicit image submission", async () => {
  const user = userEvent.setup(), onSend = vi.fn();
  render(<Composer onSend={onSend} slashCommandLibrary={{ ...library, manifest: {
    ...library.manifest, commands: imageCommands.map(command => ({ ...command, availability: "unavailable" })),
  }}} />);
  fireEvent.change(screen.getByTestId("composer-textarea"), { target: { value: "/imagine A fox" } });
  await user.click(screen.getByRole("button", { name: "Send" }));
  expect(onSend).not.toHaveBeenCalled();
  expect(api.post).not.toHaveBeenCalled();
});

it.each([undefined, { status: "loading" as const }, { status: "unavailable" as const },
  { ...library, manifest: { ...library.manifest, commands: [] } },
])("blocks explicit image dispatch without known current discovery: %j", async discovery => {
  const user = userEvent.setup(), onSend = vi.fn();
  render(<Composer onSend={onSend} slashCommandLibrary={discovery} />);
  fireEvent.change(screen.getByTestId("composer-textarea"), { target: { value: "/image A fox" } });
  await user.click(screen.getByRole("button", { name: "Send" }));
  expect(onSend).not.toHaveBeenCalled();
  expect(api.post).not.toHaveBeenCalled();
});
