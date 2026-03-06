import {
  getPreferredProviderSelection,
  type ProviderModelSelection,
} from "@/lib/providerPref";
import type { ComposerInferenceMode } from "@/types/inference";

const KNOWN_PROVIDER_IDS = new Set([
  "local",
  "openai",
  "anthropic",
  "gemini",
  "groq",
]);

function normalizeValue(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

type ProviderModelPayload = {
  provider?: string;
  model?: string;
};

type ChatCompletionSelection = {
  providerId?: string | null;
  modelId?: string | null;
  reasoningMode?: ComposerInferenceMode;
  preferredSelection?: ProviderModelSelection | null;
};

function resolveProviderModelPayload(
  activeModelId: string,
  persistedSelection: ProviderModelSelection | null
): ProviderModelPayload {
  const persistedProvider = normalizeValue(persistedSelection?.provider);
  const persistedModel = normalizeValue(persistedSelection?.model);
  if (persistedProvider || persistedModel) {
    return {
      ...(persistedProvider ? { provider: persistedProvider } : {}),
      ...(persistedModel ? { model: persistedModel } : {}),
    };
  }

  const selected = normalizeValue(activeModelId);
  if (!selected || selected === "default") return {};
  if (KNOWN_PROVIDER_IDS.has(selected)) {
    return { provider: selected };
  }
  return { model: selected };
}

export function buildChatCompletionPayload(
  depthMode: string,
  selectionOrModelId: string | ChatCompletionSelection,
  preferredSelection?: ProviderModelSelection | null
): {
  depth_mode: string;
  provider?: string;
  model?: string;
  reasoning_mode?: ComposerInferenceMode;
} {
  const selection =
    typeof selectionOrModelId === "string"
      ? null
      : selectionOrModelId;
  const persistedSelection =
    selection?.preferredSelection !== undefined
      ? selection.preferredSelection
      : preferredSelection !== undefined
        ? preferredSelection
        : getPreferredProviderSelection();
  const explicitProvider = normalizeValue(selection?.providerId);
  const explicitModel = normalizeValue(selection?.modelId);
  const providerModelPayload =
    explicitProvider || explicitModel
      ? {
          ...(explicitProvider ? { provider: explicitProvider } : {}),
          ...(explicitModel && explicitModel !== "default"
            ? { model: explicitModel }
            : {}),
        }
      : resolveProviderModelPayload(
          typeof selectionOrModelId === "string"
            ? selectionOrModelId
            : selection?.modelId || "default",
          persistedSelection
        );

  const reasoningMode = selection?.reasoningMode;
  return {
    depth_mode: depthMode,
    ...providerModelPayload,
    ...(reasoningMode && reasoningMode !== "default"
      ? { reasoning_mode: reasoningMode }
      : {}),
  };
}
