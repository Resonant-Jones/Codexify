/**
 * ProviderSelect – Compact LLM provider dropdown (PCX_UI_QUIKWINS_002)
 *
 * Compact provider + model selector powered by /api/llm/catalog.
 */

import { ChevronDown, ChevronLeft, Loader2 } from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { usePreferredProvider } from "@/hooks/usePreferredProvider";
import api, { buildLlmCatalogPath } from "@/lib/api";
import {
  reconcilePreferredProviderSelection,
  setPreferredProviderSelection,
} from "@/lib/providerPref";
import { usePollWithBackoff } from "@/lib/polling/usePollWithBackoff";
import { logOnce } from "@/lib/logging/logOnce";

type ProviderSelectProps = {
  value?: string;
  onChange?: (value: string) => void;
  triggerClassName?: string;
  triggerStyle?: React.CSSProperties;
  openSignal?: number;
  cloudProvidersDisabled?: boolean;
  displayMode?: "provider" | "model";
  label?: string;
  preferredProviderId?: string;
};

type CatalogModel = {
  id: string;
  displayName: string;
  contextWindow?: number;
  capabilities?: {
    vision?: boolean;
    tools?: boolean;
    streaming?: boolean;
  };
};

type CatalogProvider = {
  id: string;
  displayName: string;
  enabled: boolean;
  authorized: boolean;
  available: boolean;
  disabled_reason?: string;
  source?: {
    kind?: string;
    baseUrl?: string;
    host?: string;
    port?: number;
    label?: string;
  };
  models: CatalogModel[];
};

function describeProviderSource(source?: CatalogProvider["source"]): string | null {
  if (!source) return null;
  const label = String(source.label ?? "").trim();
  if (label) return label;
  const baseUrl = String(source.baseUrl ?? "").trim();
  if (!baseUrl) return null;
  try {
    return new URL(baseUrl).host || baseUrl;
  } catch {
    return baseUrl;
  }
}

export function ProviderSelect({
  value,
  onChange,
  triggerClassName,
  triggerStyle,
  openSignal,
  cloudProvidersDisabled = false,
  displayMode = "provider",
  label,
  preferredProviderId,
}: ProviderSelectProps) {
  const { provider, setProvider } = usePreferredProvider();
  const [providers, setProviders] = useState<CatalogProvider[]>([]);
  const [open, setOpen] = useState(false);
  const [activeProviderId, setActiveProviderId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const CATALOG_POLL_MS = 15_000;

  const loadCatalog = useCallback(async (options: { throwOnError?: boolean; silent?: boolean } = {}) => {
    if (!options.silent) {
      setLoading(true);
      setLoadError(null);
    }
    const catalogPath = buildLlmCatalogPath();
    try {
      const response = await api.get<{ providers?: CatalogProvider[] }>(catalogPath);
      const rawProviders = Array.isArray(response?.data?.providers)
        ? response.data.providers
        : [];
      const normalizedProviders: CatalogProvider[] = rawProviders
        .filter((entry): entry is CatalogProvider => Boolean(entry) && typeof entry === "object")
        .map((entry) => ({
          id: String(entry.id || "").trim(),
          displayName: String((entry as any).displayName || (entry as any).label || entry.id || "").trim(),
          enabled: Boolean((entry as any).enabled),
          authorized: Boolean(entry.authorized),
          available: Boolean(entry.available),
          disabled_reason:
            typeof entry.disabled_reason === "string"
              ? entry.disabled_reason
              : undefined,
          source:
            entry.source && typeof entry.source === "object"
              ? {
                  kind:
                    typeof entry.source.kind === "string"
                      ? entry.source.kind
                      : undefined,
                  baseUrl:
                    typeof entry.source.baseUrl === "string"
                      ? entry.source.baseUrl
                      : undefined,
                  host:
                    typeof entry.source.host === "string"
                      ? entry.source.host
                      : undefined,
                  port:
                    typeof entry.source.port === "number"
                      ? entry.source.port
                      : undefined,
                  label:
                    typeof entry.source.label === "string"
                      ? entry.source.label
                      : undefined,
                }
              : undefined,
          models: Array.isArray(entry.models)
            ? entry.models
                .filter((model): model is CatalogModel => Boolean(model) && typeof model === "object")
                .map((model) => ({
                  id: String(model.id || "").trim(),
                  displayName: String((model as any).displayName || (model as any).label || model.id || "").trim(),
                  contextWindow:
                    typeof (model as any).contextWindow === "number"
                      ? (model as any).contextWindow
                      : undefined,
                  capabilities:
                    typeof (model as any).capabilities === "object"
                    && (model as any).capabilities
                      ? {
                          vision: Boolean((model as any).capabilities.vision),
                          tools: Boolean((model as any).capabilities.tools),
                          streaming: Boolean((model as any).capabilities.streaming),
                        }
                      : undefined,
                }))
                .filter((model) => model.id.length > 0)
            : [],
        }))
        .filter((entry) => entry.id.length > 0 && entry.enabled);

      setProviders(normalizedProviders);
      reconcilePreferredProviderSelection(normalizedProviders);
      setActiveProviderId((previous) =>
        previous && normalizedProviders.some((entry) => entry.id === previous)
          ? previous
          : null
      );
    } catch (error: any) {
      setProviders([]);
      setLoadError("Provider catalog unavailable");
      logOnce("poll:llm-catalog", 10_000, () => {
        console.warn(
          `[providers] failed to load catalog from ${catalogPath}`,
          error
        );
      });
      if (options.throwOnError) {
        throw error;
      }
    } finally {
      if (!options.silent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  const selectedRaw = String(value ?? provider ?? "default").trim() || "default";

  const selectedProvider = useMemo(() => {
    if (selectedRaw === "default") return null;
    const byModel = providers.find((entry) =>
      entry.models.some((model) => model.id === selectedRaw)
    );
    if (byModel) return byModel;
    return providers.find((entry) => entry.id === selectedRaw) ?? null;
  }, [providers, selectedRaw]);

  const selectedModel = useMemo(() => {
    if (!selectedProvider) return null;
    return selectedProvider.models.find((m) => m.id === selectedRaw) ?? null;
  }, [selectedProvider, selectedRaw]);

  const owningProviderId = useMemo(() => {
    if (displayMode === "model" && selectedProvider?.id) return selectedProvider.id;
    return null;
  }, [displayMode, selectedProvider?.id]);

  const triggerProviderLabel = (() => {
    if (displayMode === "model" && selectedModel?.displayName) {
      return selectedModel.displayName;
    }
    if (selectedProvider?.displayName) return selectedProvider.displayName;
    if (providers[0]?.displayName) return providers[0].displayName;
    return displayMode === "model" ? "Model" : "Provider";
  })();

  const activeProvider = useMemo(
    () =>
      activeProviderId
        ? providers.find((entry) => entry.id === activeProviderId) || null
        : null,
    [providers, activeProviderId]
  );

  useEffect(() => {
    if (typeof openSignal !== "number" || openSignal <= 0) return;
    setOpen(true);
    const initialProvider =
      displayMode === "model"
        ? preferredProviderId || owningProviderId || null
        : null;
    setActiveProviderId(initialProvider);
    void loadCatalog();
  }, [openSignal, loadCatalog, displayMode, preferredProviderId, owningProviderId]);

  usePollWithBackoff(
    () => loadCatalog({ throwOnError: true, silent: true }),
    {
      intervalMs: CATALOG_POLL_MS,
      maxBackoffMs: 60_000,
      enabled: open,
      onErrorKey: "poll:llm-catalog",
      logTtlMs: 10_000,
    }
  );

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      setOpen(nextOpen);
      if (!nextOpen) {
        setActiveProviderId(null);
        return;
      }
      const initialProvider =
        displayMode === "model"
          ? preferredProviderId || owningProviderId || null
          : null;
      setActiveProviderId(initialProvider);
      void loadCatalog();
    },
    [loadCatalog, displayMode, preferredProviderId, owningProviderId]
  );

  const applySelection = useCallback(
    (modelId: string, providerId?: string | null) => {
      const normalizedModel = String(modelId || "").trim() || "default";
      const normalizedProvider = providerId ? String(providerId).trim() : null;
      if (onChange) {
        if (normalizedProvider) {
          setProvider(normalizedProvider);
          setPreferredProviderSelection({
            provider: normalizedProvider,
            model: normalizedModel === "default" ? null : normalizedModel,
          });
        } else if (normalizedModel === "default") {
          setProvider(null);
          setPreferredProviderSelection(null);
        } else {
          const providerFromModel = providers.find((entry) =>
            entry.models.some((model) => model.id === normalizedModel)
          );
          const providerValue = providerFromModel?.id || null;
          if (providerValue) setProvider(providerValue);
          setPreferredProviderSelection({
            provider: providerValue,
            model: normalizedModel,
          });
        }
        onChange(normalizedModel);
        return;
      }

      if (normalizedModel === "default") {
        setProvider(null);
        setPreferredProviderSelection(null);
        return;
      }

      if (normalizedProvider) {
        setProvider(normalizedProvider);
        setPreferredProviderSelection({
          provider: normalizedProvider,
          model: normalizedModel,
        });
        return;
      }

      const providerFromModel = providers.find((entry) =>
        entry.models.some((model) => model.id === normalizedModel)
      );
      const providerValue = providerFromModel?.id || null;
      if (providerValue) {
        setProvider(providerValue);
      }
      setPreferredProviderSelection({
        provider: providerValue,
        model: normalizedModel,
      });
    },
    [onChange, providers, setProvider]
  );

  return (
    <DropdownMenu open={open} onOpenChange={handleOpenChange}>
      <DropdownMenuTrigger
        className={`inline-flex items-center gap-1.5 h-8 px-3 text-xs rounded-full border transition-colors hover:bg-[color-mix(in_oklab,var(--panel-bg),var(--panel-border)_15%)] ${triggerClassName ?? ""}`.trim()}
        style={{
          borderColor: "var(--panel-border)",
          background: "var(--panel-bg)",
          color: "var(--text)",
          ...triggerStyle,
        }}
        aria-label="Open provider selector"
      >
        <span className="opacity-90">⚡</span>
        {label ? (
          <span className="uppercase tracking-wide text-[10px] opacity-70">{label}</span>
        ) : null}
        <span className="font-medium truncate max-w-[160px]">{triggerProviderLabel}</span>
        <ChevronDown className="h-3 w-3 opacity-50" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="min-w-[200px]">
        <div
          className="px-3 py-2 text-xs font-semibold opacity-70 border-b flex items-center gap-2"
          style={{ borderColor: "var(--panel-border)" }}
        >
          {activeProvider ? (
            <button
              type="button"
              aria-label="Back to providers"
              className="inline-flex h-5 w-5 items-center justify-center rounded-full"
              onClick={() => setActiveProviderId(null)}
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
          ) : null}
          <span>
            {activeProvider
              ? `${activeProvider.displayName} Models`
              : displayMode === "model"
                ? "Select Model"
                : "Select Provider"}
          </span>
        </div>

        {loading ? (
          <div className="px-3 py-3 text-xs opacity-80 inline-flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Loading providers…</span>
          </div>
        ) : loadError ? (
          <div className="px-3 py-2 text-xs opacity-80">{loadError}</div>
        ) : activeProvider ? (
          <div className="transition-all duration-150 ease-out">
            {describeProviderSource(activeProvider.source) ? (
              <div
                className="px-3 py-2 text-[10px] opacity-70 border-b"
                style={{ borderColor: "var(--panel-border)" }}
              >
                Source: {describeProviderSource(activeProvider.source)}
              </div>
            ) : null}
            {activeProvider.models.map((model) => (
              <DropdownMenuItem
                key={model.id}
                disabled={!activeProvider.available}
                onClick={() => {
                  applySelection(model.id, activeProvider.id);
                  setOpen(false);
                }}
                style={{
                  color: "var(--text)",
                  background:
                    selectedRaw === model.id
                      ? "color-mix(in_oklab,var(--panel-bg),var(--accent)_15%)"
                      : "transparent",
                }}
              >
                <span className="flex items-center justify-between w-full gap-2">
                  <span className="truncate">{model.displayName}</span>
                  <span className="inline-flex items-center gap-1">
                    {typeof model.contextWindow === "number" ? (
                      <span
                        className="rounded-full border px-1.5 py-0.5 text-[9px] opacity-70"
                        style={{ borderColor: "var(--panel-border)" }}
                      >
                        {Math.round(model.contextWindow / 1000)}k
                      </span>
                    ) : null}
                    {selectedRaw === model.id ? (
                      <span className="text-[var(--accent)]">✓</span>
                    ) : null}
                  </span>
                </span>
              </DropdownMenuItem>
            ))}
            {activeProvider.models.length === 0 ? (
              <div className="px-3 py-2 text-xs opacity-75">No models available.</div>
            ) : null}
            {!activeProvider.available && activeProvider.disabled_reason ? (
              <div
                className="px-3 py-2 mt-1 text-[10px] opacity-80 border-t"
                style={{ borderColor: "var(--panel-border)" }}
              >
                {activeProvider.disabled_reason}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="transition-all duration-150 ease-out">
            {providers.map((entry) => (
              <DropdownMenuItem
                key={entry.id}
                onClick={(event) => {
                  event.preventDefault();
                  setActiveProviderId(entry.id);
                }}
                style={{ color: "var(--text)" }}
              >
                <span className="flex items-center justify-between w-full gap-2">
                  <span className="min-w-0">
                    <span className="block truncate">{entry.displayName}</span>
                    {describeProviderSource(entry.source) ? (
                      <span className="block truncate text-[10px] opacity-65">
                        {describeProviderSource(entry.source)}
                      </span>
                    ) : null}
                  </span>
                  {!entry.available ? (
                    <span className="text-[10px] opacity-70">Unavailable</span>
                  ) : null}
                </span>
              </DropdownMenuItem>
            ))}
            {providers.length === 0 ? (
              <div className="px-3 py-2 text-xs opacity-75">No providers available.</div>
            ) : null}
          </div>
        )}

        {cloudProvidersDisabled ? (
          <div
            className="px-3 py-2 mt-1 text-[10px] opacity-80 border-t"
            style={{ borderColor: "var(--panel-border)" }}
          >
            Cloud providers disabled by config.
          </div>
        ) : null}

        <div className="px-3 py-2 mt-1 text-[10px] opacity-60 border-t" style={{ borderColor: "var(--panel-border)" }}>
          Default uses <code className="px-1 rounded" style={{ background: "var(--chip-bg)" }}>GUARDIAN_PROVIDER</code>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default ProviderSelect;
