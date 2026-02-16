/**
 * ProviderSelect – Compact LLM provider dropdown (PCX_UI_QUIKWINS_002)
 *
 * Compact provider + model selector powered by /api/llm/catalog.
 */

import { ChevronDown, ChevronLeft, Loader2 } from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { usePreferredProvider } from "@/hooks/usePreferredProvider";
import api from "@/lib/api";

type ProviderSelectProps = {
  value?: string;
  onChange?: (value: string) => void;
  triggerClassName?: string;
  triggerStyle?: React.CSSProperties;
  openSignal?: number;
  cloudProvidersDisabled?: boolean;
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
  models: CatalogModel[];
};

export function ProviderSelect({
  value,
  onChange,
  triggerClassName,
  triggerStyle,
  openSignal,
  cloudProvidersDisabled = false,
}: ProviderSelectProps) {
  const { provider, setProvider } = usePreferredProvider();
  const [providers, setProviders] = useState<CatalogProvider[]>([]);
  const [open, setOpen] = useState(false);
  const [activeProviderId, setActiveProviderId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await api.get<{ providers?: CatalogProvider[] }>("/llm/catalog");
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
      setActiveProviderId((previous) =>
        previous && normalizedProviders.some((entry) => entry.id === previous)
          ? previous
          : null
      );
    } catch {
      setProviders([]);
      setLoadError("Provider catalog unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    if (typeof openSignal !== "number" || openSignal <= 0) return;
    setOpen(true);
    setActiveProviderId(null);
    void loadCatalog();
  }, [openSignal, loadCatalog]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      setOpen(nextOpen);
      if (!nextOpen) {
        setActiveProviderId(null);
        return;
      }
      setActiveProviderId(null);
      void loadCatalog();
    },
    [loadCatalog]
  );

  const selectedRaw = String(value ?? provider ?? "default").trim() || "default";

  const selectedProvider = useMemo(() => {
    if (selectedRaw === "default") return null;
    const byModel = providers.find((entry) =>
      entry.models.some((model) => model.id === selectedRaw)
    );
    if (byModel) return byModel;
    return providers.find((entry) => entry.id === selectedRaw) ?? null;
  }, [providers, selectedRaw]);

  const triggerProviderLabel =
    selectedProvider?.displayName
    || providers[0]?.displayName
    || "Provider";

  const activeProvider = useMemo(
    () =>
      activeProviderId
        ? providers.find((entry) => entry.id === activeProviderId) || null
        : null,
    [providers, activeProviderId]
  );

  const applySelection = useCallback(
    (modelId: string, providerId?: string | null) => {
      if (onChange) {
        if (providerId) {
          setProvider(providerId);
        } else if (modelId === "default") {
          setProvider(null);
        }
        onChange(modelId);
        return;
      }

      if (modelId === "default") {
        setProvider(null);
        return;
      }

      if (providerId) {
        setProvider(providerId);
        return;
      }

      const providerFromModel = providers.find((entry) =>
        entry.models.some((model) => model.id === modelId)
      );
      setProvider(providerFromModel?.id || modelId);
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
        <span className="font-medium">{triggerProviderLabel}</span>
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
          <span>{activeProvider ? `${activeProvider.displayName} Models` : "Select Provider"}</span>
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
                onSelect={(event) => {
                  event.preventDefault();
                  setActiveProviderId(entry.id);
                }}
                style={{ color: "var(--text)" }}
              >
                <span className="flex items-center justify-between w-full gap-2">
                  <span className="truncate">{entry.displayName}</span>
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
