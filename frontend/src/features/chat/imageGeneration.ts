import { resolveSlashCommand } from "@/contracts/slashCommands";
import type { SlashCommandLibrary } from "@/features/chat/useSlashCommandLibrary";
import api from "@/lib/api";
import { toAbsoluteMediaUrl } from "@/hooks/useUploader";

export type ImageGenerationIntent = {
  prompt: string;
  provider?: string;
  model?: string;
  modelAlias?: string;
};
export type ImageProvider = {
  id: string;
  label: string;
  models: string[];
  default_model: string;
  model_aliases: Record<string, string>;
  available: boolean;
  unavailable_reason: string | null;
};
export type ImageCatalog = {
  providers: ImageProvider[];
  default_provider: string;
  default_model: string;
};
export type GeneratedImage = {
  id: string;
  src_url: string;
  prompt: string;
  model: string;
  provider?: string;
};

// Inspect only the authored draft, before attachments or document context are added.
// Only explicit slash commands opt into paid generation. Ordinary prose stays chat.
export function resolveImageGenerationIntent(input: string): ImageGenerationIntent | null {
  const command = input.trim().match(/^\/(sunburst|flare|image|imagine)\b\s*([\s\S]*)$/i);
  if (command) {
    let prompt = command[2].trim();
    const intent: ImageGenerationIntent = { prompt };
    if (/^(sunburst|flare)$/i.test(command[1])) intent.modelAlias = command[1].toLowerCase();
    prompt = prompt
      .replace(/--(provider|model)\s+([\w./:-]+)/gi, (_, key: string, value: string) => {
        if (key.toLowerCase() === "provider") intent.provider = value;
        else intent.model = value;
        return "";
      })
      .trim();
    return { ...intent, prompt };
  }
  return null;
}

export function requireImageCommandDiscovery(
  library: SlashCommandLibrary | undefined, intent: ImageGenerationIntent
): void {
  const id = intent.modelAlias || "image";
  const command = library?.status === "ready"
    ? resolveSlashCommand(library.manifest.commands, `/${id}`) : undefined;
  if (!command || command.id !== id || !command.effects ||
      !command.interactionModes.includes("chat_intent") || command.availability === "unavailable") {
    throw new Error("Image commands are unavailable. Reconnect to Guardian and try again.");
  }
  // Unknown discovery availability is not an execution grant. The current image
  // catalog and server policy still decide provider/model eligibility at send.
}

export async function loadImageCatalog(): Promise<ImageCatalog> {
  const { data } = await api.get<ImageCatalog>("/api/media/generate/image/models");
  return data;
}

export function imageSelection(catalog: ImageCatalog, intent: ImageGenerationIntent) {
  let savedProvider: string | null = null,
    savedModel: string | null = null;
  try {
    savedProvider = localStorage.getItem("cfy.imagegen.provider");
    savedModel = localStorage.getItem("cfy.imagegen.model");
  } catch {
    /* Storage is optional. */
  }
  if (!catalog.providers.some((item) => item.id === savedProvider)) savedProvider = null;
  const provider = intent.modelAlias
    ? catalog.providers.find((item) => item.model_aliases[intent.modelAlias!])
    : catalog.providers.find(
        (item) => item.id === (intent.provider || savedProvider || catalog.default_provider)
      );
  if (!provider) throw new Error("The requested image provider or model is unavailable.");
  if (intent.provider && intent.provider !== provider.id)
    throw new Error("The requested model is not available from the selected image provider.");
  if (!provider.available)
    throw new Error(provider.unavailable_reason || "Image generation is unavailable.");
  const usingSavedProvider = !savedProvider || provider.id === savedProvider;
  if (!intent.model && !intent.modelAlias && savedModel && usingSavedProvider &&
      !provider.models.includes(savedModel)) {
    throw new Error("Your saved image model is no longer offered. Choose a model in Generate image or use /sunburst or /flare.");
  }
  const model =
    intent.model ||
    (intent.modelAlias && provider.model_aliases[intent.modelAlias]) ||
    (usingSavedProvider && savedModel && provider.models.includes(savedModel) ? savedModel : null) ||
    (provider.id === catalog.default_provider && provider.models.includes(catalog.default_model)
      ? catalog.default_model
      : provider.default_model);
  if (!provider.models.includes(model))
    throw new Error("The selected image model is not supported by this provider.");
  return { provider: provider.id, model };
}

export async function generateImage(
  intent: ImageGenerationIntent,
  scope: { projectId?: number | null; threadId?: number | null }
): Promise<GeneratedImage> {
  if (!intent.prompt.trim()) throw new Error("Describe the image you want to generate.");
  if (!scope.projectId && !scope.threadId)
    throw new Error("Choose a project or thread for this image.");
  const selection = imageSelection(await loadImageCatalog(), intent);
  const { data } = await api.post<GeneratedImage>(
    "/api/media/generate/image",
    {
      prompt: intent.prompt.trim(),
      ...selection,
      project_id: scope.projectId ?? undefined,
      thread_id: scope.threadId ?? undefined,
    },
    { timeout: 210_000 }
  );
  if (!data.id || !data.src_url) throw new Error("No saved image was returned.");
  const image = {
    ...data,
    provider: selection.provider,
    src_url: toAbsoluteMediaUrl(data.src_url),
  };
  window.dispatchEvent(
    new CustomEvent("cfy:gallery:add", {
      detail: {
        items: [
          {
            ...image,
            src: image.src_url,
            project_id: scope.projectId,
            thread_id: scope.threadId,
            tag: "generated",
            mock: false,
          },
        ],
      },
    })
  );
  return image;
}

export function imageGenerationError(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return error instanceof Error ? error.message : "Image generation failed.";
}
