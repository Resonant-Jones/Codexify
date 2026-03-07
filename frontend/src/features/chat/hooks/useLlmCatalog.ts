import { useCallback, useEffect, useMemo, useState } from "react";

import api, { buildLlmCatalogPath } from "@/lib/api";
import { logOnce } from "@/lib/logging/logOnce";
import { usePollWithBackoff } from "@/lib/polling/usePollWithBackoff";
import type { ComposerInferenceMode } from "@/types/inference";

type CatalogReasoningRuntime = {
  mode: ComposerInferenceMode | null;
  instruction: string | null;
  profileReason: string | null;
};

export type LlmCatalogModel = {
  id: string;
  providerId: string;
  displayName: string;
  contextWindow?: number;
  capabilities?: {
    vision?: boolean;
    tools?: boolean;
    streaming?: boolean;
  };
  runtime?: {
    reasoning?: CatalogReasoningRuntime;
  };
};

export type LlmCatalogProvider = {
  id: string;
  displayName: string;
  enabled: boolean;
  authorized: boolean;
  available: boolean;
  disabledReason?: string;
  source?: {
    kind?: string;
    baseUrl?: string;
    host?: string;
    port?: number;
    label?: string;
  };
  models: LlmCatalogModel[];
};

const CATALOG_POLL_MS = 15_000;

function normalizeString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeReasoningMode(value: unknown): ComposerInferenceMode | null {
  const normalized = normalizeString(value);
  if (normalized === "default" || normalized === "think" || normalized === "no_think") {
    return normalized;
  }
  return null;
}

function normalizeModel(
  providerId: string,
  raw: unknown
): LlmCatalogModel | null {
  if (!raw || typeof raw !== "object") return null;
  const model = raw as Record<string, unknown>;
  const id = normalizeString(model.id);
  if (!id) return null;

  const displayName =
    normalizeString(model.displayName) ??
    normalizeString(model.label) ??
    id;
  const runtime = model.runtime;
  const reasoning =
    runtime && typeof runtime === "object"
      ? (runtime as Record<string, unknown>).reasoning
      : null;

  return {
    id,
    providerId,
    displayName,
    contextWindow:
      typeof model.contextWindow === "number" && Number.isFinite(model.contextWindow)
        ? model.contextWindow
        : undefined,
    capabilities:
      model.capabilities && typeof model.capabilities === "object"
        ? {
            vision: Boolean((model.capabilities as Record<string, unknown>).vision),
            tools: Boolean((model.capabilities as Record<string, unknown>).tools),
            streaming: Boolean(
              (model.capabilities as Record<string, unknown>).streaming
            ),
          }
        : undefined,
    runtime:
      reasoning && typeof reasoning === "object"
        ? {
            reasoning: {
              mode: normalizeReasoningMode(
                (reasoning as Record<string, unknown>).mode
              ),
              instruction: normalizeString(
                (reasoning as Record<string, unknown>).instruction
              ),
              profileReason: normalizeString(
                (reasoning as Record<string, unknown>).profile_reason
              ),
            },
          }
        : undefined,
  };
}

function normalizeProvider(raw: unknown): LlmCatalogProvider | null {
  if (!raw || typeof raw !== "object") return null;
  const provider = raw as Record<string, unknown>;
  const id = normalizeString(provider.id);
  if (!id) return null;

  const models = Array.isArray(provider.models)
    ? provider.models
        .map((entry) => normalizeModel(id, entry))
        .filter(Boolean) as LlmCatalogModel[]
    : [];

  return {
    id,
    displayName: normalizeString(provider.displayName) ?? id,
    enabled: Boolean(provider.enabled),
    authorized: Boolean(provider.authorized),
    available: Boolean(provider.available),
    disabledReason: normalizeString(provider.disabled_reason) ?? undefined,
    source:
      provider.source && typeof provider.source === "object"
        ? {
            kind:
              normalizeString((provider.source as Record<string, unknown>).kind) ??
              undefined,
            baseUrl:
              normalizeString(
                (provider.source as Record<string, unknown>).baseUrl
              ) ?? undefined,
            host:
              normalizeString((provider.source as Record<string, unknown>).host) ??
              undefined,
            port:
              typeof (provider.source as Record<string, unknown>).port === "number"
                ? Number((provider.source as Record<string, unknown>).port)
                : undefined,
            label:
              normalizeString((provider.source as Record<string, unknown>).label) ??
              undefined,
          }
        : undefined,
    models,
  };
}

export function useLlmCatalog() {
  const [providers, setProviders] = useState<LlmCatalogProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCatalog = useCallback(
    async (options: { silent?: boolean; throwOnError?: boolean } = {}) => {
      if (!options.silent) {
        setLoading(true);
      }
      setError(null);

      const catalogPath = buildLlmCatalogPath();
      try {
        const response = await api.get<{ providers?: unknown[] }>(catalogPath);
        const nextProviders = Array.isArray(response?.data?.providers)
          ? response.data.providers
              .map((entry) => normalizeProvider(entry))
              .filter(Boolean) as LlmCatalogProvider[]
          : [];
        setProviders(nextProviders);
      } catch (fetchError) {
        logOnce("poll:guardian-llm-catalog", 10_000, () => {
          console.warn(
            `[guardian] failed to load catalog from ${catalogPath}`,
            fetchError
          );
        });
        setError("Model catalog unavailable");
        if (options.throwOnError) {
          throw fetchError;
        }
      } finally {
        if (!options.silent) {
          setLoading(false);
        }
      }
    },
    []
  );

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  usePollWithBackoff(
    () => loadCatalog({ silent: true, throwOnError: true }),
    {
      intervalMs: CATALOG_POLL_MS,
      maxBackoffMs: 60_000,
      enabled: true,
      onErrorKey: "poll:guardian-llm-catalog",
      logTtlMs: 10_000,
    }
  );

  const models = useMemo(
    () => providers.flatMap((provider) => provider.models),
    [providers]
  );

  const getProviderById = useCallback(
    (providerId: string | null | undefined) => {
      if (!providerId) return null;
      return providers.find((provider) => provider.id === providerId) ?? null;
    },
    [providers]
  );

  const getModelById = useCallback(
    (modelId: string | null | undefined) => {
      if (!modelId) return null;
      return models.find((model) => model.id === modelId) ?? null;
    },
    [models]
  );

  const findProviderForModel = useCallback(
    (modelId: string | null | undefined) => {
      if (!modelId) return null;
      return (
        providers.find((provider) =>
          provider.models.some((model) => model.id === modelId)
        ) ?? null
      );
    },
    [providers]
  );

  return {
    providers,
    models,
    loading,
    error,
    refresh: loadCatalog,
    getProviderById,
    getModelById,
    findProviderForModel,
  };
}
