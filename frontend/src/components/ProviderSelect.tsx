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

type CatalogModel = { id: string; label: string };
type CatalogProvider = {
  id: string;
  label: string;
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
          label: String(entry.label || entry.id || "").trim(),
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
                  label: String(model.label || model.id || "").trim(),
                }))
                .filter((model) => model.id.length > 0)
            : [],
        }))
        .filter((entry) => entry.id.length > 0);

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

  const selectedModel = useMemo(() => {
    if (selectedRaw === "default") return null;
    for (const providerEntry of providers) {
      const match = providerEntry.models.find((model) => model.id === selectedRaw);
      if (match) return match;
    }
    return null;
  }, [providers, selectedRaw]);

  const selectedProvider = useMemo(() => {
    if (selectedRaw === "default") return null;
    const byModel = providers.find((entry) =>
      entry.models.some((model) => model.id === selectedRaw)
    );
    if (byModel) return byModel;
    return providers.find((entry) => entry.id === selectedRaw) ?? null;
  }, [providers, selectedRaw]);

  const triggerLabel =
    selectedRaw === "default"
      ? "default"
      : selectedModel?.label || selectedProvider?.label || selectedRaw;

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
        aria-label="Choose model provider"
      >
        <span className="opacity-70">⚙︎</span>
        <span className="font-medium">{triggerLabel}</span>
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
          <span>{activeProvider ? `${activeProvider.label} models` : "Model Provider"}</span>
        </div>

        {loading ? (
          <div className="px-3 py-3 text-xs opacity-80 inline-flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Loading providers…</span>
          </div>
        ) : loadError ? (
          <div className="px-3 py-2 text-xs opacity-80">{loadError}</div>
        ) : activeProvider ? (
          <>
            <DropdownMenuItem
              onClick={() => {
                applySelection("default", null);
                setOpen(false);
              }}
              style={{
                color: "var(--text)",
                background:
                  selectedRaw === "default"
                    ? "color-mix(in_oklab,var(--panel-bg),var(--accent)_15%)"
                    : "transparent",
              }}
            >
              <span className="flex items-center justify-between w-full">
                <span>default</span>
                {selectedRaw === "default" ? (
                  <span className="text-[var(--accent)]">✓</span>
                ) : null}
              </span>
            </DropdownMenuItem>
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
                  <span className="truncate">{model.label}</span>
                  {selectedRaw === model.id ? (
                    <span className="text-[var(--accent)]">✓</span>
                  ) : null}
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
          </>
        ) : (
          <>
            <DropdownMenuItem
              onClick={() => {
                applySelection("default", null);
                setOpen(false);
              }}
              style={{
                color: "var(--text)",
                background:
                  selectedRaw === "default"
                    ? "color-mix(in_oklab,var(--panel-bg),var(--accent)_15%)"
                    : "transparent",
              }}
            >
              <span className="flex items-center justify-between w-full">
                <span>default</span>
                {selectedRaw === "default" ? (
                  <span className="text-[var(--accent)]">✓</span>
                ) : null}
              </span>
            </DropdownMenuItem>
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
                  <span className="truncate">{entry.label}</span>
                  {!entry.available ? (
                    <span className="text-[10px] opacity-70">Unavailable</span>
                  ) : null}
                </span>
              </DropdownMenuItem>
            ))}
            {providers.length === 0 ? (
              <div className="px-3 py-2 text-xs opacity-75">No providers available.</div>
            ) : null}
          </>
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
