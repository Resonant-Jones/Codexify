import {
  getPreferredProviderSelection,
  type ProviderModelSelection,
} from "@/lib/providerPref";
import type { SlashCommandContextDirective } from "@/contracts/slashCommands";
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

function normalizeIdentityValue(
  value: unknown,
  placeholder?: string
): string | undefined {
  const trimmed = normalizeValue(value);
  if (!trimmed) return undefined;
  if (placeholder && trimmed.toLowerCase() === placeholder.toLowerCase()) {
    return undefined;
  }
  return trimmed;
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
  preferredName?: string | null;
  profession?: string | null;
  guardianName?: string | null;
  contextDirectives?: SlashCommandContextDirective[] | null;
};

type ChatCompletionContextDirectivePayload = {
  kind: "connector_context";
  connector_id: "obsidian";
  invocation: "turn_scoped";
  query_text: string;
};

function normalizeContextDirectiveQueryText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function toContextDirectivePayload(
  directives: SlashCommandContextDirective[] | null | undefined
): ChatCompletionContextDirectivePayload[] | undefined {
  if (!Array.isArray(directives) || directives.length === 0) {
    return undefined;
  }

  const normalized = directives.flatMap((directive) => {
    if (!directive || directive.kind !== "connector_context") {
      return [];
    }
    const queryText = normalizeContextDirectiveQueryText(directive.queryText);
    if (!queryText) {
      return [];
    }
    return [
      {
        kind: "connector_context" as const,
        connector_id: "obsidian" as const,
        invocation: "turn_scoped" as const,
        query_text: queryText,
      },
    ];
  });

  return normalized.length > 0 ? normalized : undefined;
}

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
  preferred_name?: string;
  profession?: string;
  guardian_name?: string;
  context_directives?: ChatCompletionContextDirectivePayload[];
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
  const preferredName = normalizeIdentityValue(
    selection?.preferredName,
    "You"
  );
  const profession = normalizeValue(selection?.profession);
  const guardianName = normalizeIdentityValue(
    selection?.guardianName,
    "Guardian"
  );
  const contextDirectives = toContextDirectivePayload(
    selection?.contextDirectives
  );
  return {
    depth_mode: depthMode,
    ...providerModelPayload,
    ...(reasoningMode && reasoningMode !== "default"
      ? { reasoning_mode: reasoningMode }
      : {}),
    ...(preferredName ? { preferred_name: preferredName } : {}),
    ...(profession ? { profession } : {}),
    ...(guardianName ? { guardian_name: guardianName } : {}),
    ...(contextDirectives
      ? { context_directives: contextDirectives }
      : {}),
  };
}
