import {
  getPreferredProviderSelection,
  type ProviderModelSelection,
} from "@/lib/providerPref";

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
  activeModelId: string,
  preferredSelection?: ProviderModelSelection | null
): { depth_mode: string; provider?: string; model?: string } {
  const persistedSelection =
    preferredSelection !== undefined
      ? preferredSelection
      : getPreferredProviderSelection();
  return {
    depth_mode: depthMode,
    ...resolveProviderModelPayload(activeModelId, persistedSelection),
  };
}
