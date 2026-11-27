import { afterEach, describe, expect, it, vi } from "vitest";
import {
  generateImage,
  imageSelection,
  resolveImageGenerationIntent,
  type ImageCatalog,
} from "../imageGeneration";
import api from "@/lib/api";

vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));
const catalog: ImageCatalog = {
  default_provider: "openai",
  default_model: "sunburst-id",
  providers: [
    {
      id: "openai",
      label: "OpenAI",
      available: true,
      unavailable_reason: null,
      models: ["sunburst-id", "flare-id", "small-id"],
      default_model: "sunburst-id",
      model_aliases: { sunburst: "sunburst-id", flare: "flare-id" },
    },
  ],
};
afterEach(() => {
  localStorage.clear();
  vi.resetAllMocks();
});

describe("image intent", () => {
  it.each([
    "make a picture of a fox",
    "generate me a cat",
    "I'd like to see an image of a forest",
    "id like to see an image",
    "I would love a portrait of a wolf",
    "A mountain would look great as a poster",
    "It would be nice to see a picture of Saturn",
    "Draw a cat",
    "Imagine a floating city",
    "I'd like an image of a fox that's sleeping",
    "Can you generate an illustration of home?",
   ])("leaves natural language on the ordinary chat path: %s", (text) => {
    expect(resolveImageGenerationIntent(text)).toBeNull();
  });
  it.each([
    "Don't generate an image",
    "I do not want an image",
    "How are you?",
    "generate me a report",
    "> generate an image of a cat",
    'The document says "generate an image of a cat".',
    "```\ngenerate an image of a cat\n```",
    "Use `generate an image` as a label",
    "/doc generate an image",
  ])("keeps negation, evidence and other commands out: %s", (text) => {
    expect(resolveImageGenerationIntent(text)).toBeNull();
  });
  it("supports named model commands and explicit provider/model selection", () => {
    expect(resolveImageGenerationIntent("/sunburst A fox")).toEqual({
      prompt: "A fox",
      modelAlias: "sunburst",
    });
    expect(resolveImageGenerationIntent("/flare A fox")).toEqual({
      prompt: "A fox",
      modelAlias: "flare",
    });
    expect(resolveImageGenerationIntent("/image --provider openai --model small-id A fox")).toEqual(
      { prompt: "A fox", provider: "openai", model: "small-id" }
    );
    expect(resolveImageGenerationIntent("/image")).toEqual({ prompt: "" });
  });
  it("takes model aliases from the server independently of saved chat/image choices", () => {
    localStorage.setItem("cfy.imagegen.model", "small-id");
    expect(imageSelection(catalog, { prompt: "cat", modelAlias: "flare" })).toEqual({
      provider: "openai",
      model: "flare-id",
    });
    expect(imageSelection(catalog, { prompt: "cat" }).model).toBe("small-id");
  });
  it("requires a new choice for a retired saved model without sending a paid request", async () => {
    localStorage.setItem("cfy.imagegen.provider", "openai");
    localStorage.setItem("cfy.imagegen.model", "gpt-image-1-mini");
    vi.mocked(api.get).mockResolvedValue({ data: catalog });
    await expect(generateImage({ prompt: "cat" }, { threadId: 17 })).rejects.toThrow(
      "Your saved image model is no longer offered"
    );
    expect(api.post).not.toHaveBeenCalled();
    expect(imageSelection(catalog, { prompt: "cat", modelAlias: "flare" }).model).toBe("flare-id");
    expect(imageSelection(catalog, { prompt: "cat", model: "sunburst-id" }).model).toBe("sunburst-id");
  });
  it("makes one bounded paid request and emits its saved image", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: catalog });
    vi.mocked(api.post).mockResolvedValue({
      data: { id: "image-1", src_url: "/media/cat.png", model: "flare-id" },
    });
    const event = vi.fn();
    window.addEventListener("cfy:gallery:add", event);
    await generateImage({ prompt: "cat", modelAlias: "flare" }, { threadId: 17 });
    expect(api.post).toHaveBeenCalledExactlyOnceWith(
      "/api/media/generate/image",
      {
        prompt: "cat",
        provider: "openai",
        model: "flare-id",
        project_id: undefined,
        thread_id: 17,
      },
      { timeout: 210_000 }
    );
    expect(event).toHaveBeenCalledOnce();
    window.removeEventListener("cfy:gallery:add", event);
  });
  it("does not fall back to a paid model when a provider is blocked", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        ...catalog,
        providers: [{ ...catalog.providers[0], available: false, unavailable_reason: "Blocked" }],
      },
    });
    await expect(generateImage({ prompt: "cat" }, { threadId: 17 })).rejects.toThrow("Blocked");
    expect(api.post).not.toHaveBeenCalled();
  });
});

it.each([
  { prompt: "cat", provider: "unknown" },
  { prompt: "cat", model: "unsupported-model" },
  { prompt: "cat", modelAlias: "flare", provider: "local" },
])("rejects incompatible image selections before paid dispatch: %j", async intent => {
  vi.mocked(api.get).mockResolvedValue({ data: catalog });
  await expect(generateImage(intent, { threadId: 17 })).rejects.toThrow();
  expect(api.post).not.toHaveBeenCalled();
});
