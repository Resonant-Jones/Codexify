/**
 * ProviderSelect – Compact LLM provider dropdown (PCX_UI_QUIKWINS_002)
 *
 * Replaces the floating FAB with an inline dropdown suitable for chat headers/toolbars.
 * Uses the existing usePreferredProvider hook and GuardianAPI capabilities.
 */

import { ChevronDown } from "lucide-react";
import React, { useEffect, useState } from "react";

import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { usePreferredProvider } from "@/hooks/usePreferredProvider";
import { GuardianAPI } from "@/lib/guardianApi";

type ProviderSelectProps = {
  value?: string;
  onChange?: (value: string) => void;
  triggerClassName?: string;
  triggerStyle?: React.CSSProperties;
  openSignal?: number;
  cloudProvidersDisabled?: boolean;
};

const DEFAULT_OPTION = "__default__";
const KNOWN_CLOUD_PROVIDER_PREFIXES = [
  "openai",
  "anthropic",
  "groq",
  "gemini",
  "cohere",
  "mistral",
  "replicate",
  "openrouter",
  "azure",
  "vertex",
  "bedrock",
  "together",
  "fireworks",
  "perplexity",
  "xai",
  "deepseek",
];
const KNOWN_LOCAL_PROVIDER_PREFIXES = [
  "local",
  "ollama",
  "vllm",
  "llamacpp",
  "lmstudio",
  "mock",
  "dummy",
  "offline",
];

function isLikelyCloudProvider(name: string): boolean {
  const normalized = String(name || "").trim().toLowerCase();
  if (!normalized) return false;
  if (KNOWN_LOCAL_PROVIDER_PREFIXES.some((prefix) => normalized.startsWith(prefix))) {
    return false;
  }
  return KNOWN_CLOUD_PROVIDER_PREFIXES.some((prefix) => normalized.startsWith(prefix));
}

export function ProviderSelect({
  value,
  onChange,
  triggerClassName,
  triggerStyle,
  openSignal,
  cloudProvidersDisabled = false,
}: ProviderSelectProps) {
  const { provider, setProvider } = usePreferredProvider();
  const [caps, setCaps] = useState<{ chat: string[]; embeddings: string[] }>({ chat: [], embeddings: [] });
  const [open, setOpen] = useState(false);

  useEffect(() => {
    GuardianAPI.capabilities()
      .then(setCaps)
      .catch(() => setCaps({ chat: [], embeddings: [] }));
  }, []);
  useEffect(() => {
    if (typeof openSignal === "number" && openSignal > 0) {
      setOpen(true);
    }
  }, [openSignal]);

  const options = React.useMemo(() => {
    // Include explicit default option.
    const allowedChatProviders = cloudProvidersDisabled
      ? caps.chat.filter((name) => !isLikelyCloudProvider(name))
      : caps.chat;
    return [DEFAULT_OPTION, ...allowedChatProviders];
  }, [caps.chat, cloudProvidersDisabled]);

  const selectedRaw = value ?? provider ?? "default";
  const selected = options.some((option) => (option === DEFAULT_OPTION ? "default" : option) === selectedRaw)
    ? selectedRaw
    : "default";

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
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
        <span className="font-medium">{selected}</span>
        <ChevronDown className="h-3 w-3 opacity-50" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="min-w-[200px]">
        <div className="px-3 py-2 text-xs font-semibold opacity-70 border-b" style={{ borderColor: "var(--panel-border)" }}>
          Model Provider
        </div>

        {options.map((p) => (
          <DropdownMenuItem
            key={p}
            onClick={() => {
              const next = p === DEFAULT_OPTION ? "default" : p;
              if (onChange) {
                onChange(next);
                return;
              }
              setProvider(next === "default" ? null : next);
            }}
            style={{
              color: "var(--text)",
              background:
                selected === (p === DEFAULT_OPTION ? "default" : p)
                  ? "color-mix(in_oklab,var(--panel-bg),var(--accent)_15%)"
                  : "transparent",
            }}
          >
            <span className="flex items-center justify-between w-full">
              <span>{p === DEFAULT_OPTION ? "default" : p}</span>
              {selected === (p === DEFAULT_OPTION ? "default" : p) && (
                <span className="text-[var(--accent)]">✓</span>
              )}
            </span>
          </DropdownMenuItem>
        ))}

        {!onChange && options.length > 1 && (
          <>
            <div className="h-px my-1" style={{ background: "var(--panel-border)" }} />
            <DropdownMenuItem
              onClick={() => setProvider(null)}
              style={{ color: "var(--muted)" }}
            >
              Reset to default
            </DropdownMenuItem>
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
