/**
 * ImageGenModal – Universal image generation modal (PCX_UI_QUIKWINS_002)
 *
 * Single source of truth for image generation across Chat, Gallery, and Dashboard.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import api from "@/lib/api";

const PROJECT_ID_STORAGE_KEYS = [
  "cfy.projectId",
  "cfy.activeProjectId",
  "cfy.lastProjectId",
  "projectId",
] as const;

const PROVIDER_STORAGE_KEY = "cfy.imagegen.provider";
const MODEL_STORAGE_KEY = "cfy.imagegen.model";

type ImageGenProvider = "nano_banana" | "dalle";

const PROVIDER_CONFIG: Record<
  ImageGenProvider,
  {
    label: string;
    models: string[];
    defaultModel: string;
    missingEnv: string;
  }
> = {
  nano_banana: {
    label: "Nano Banana",
    models: ["nano-banana"],
    defaultModel: "nano-banana",
    missingEnv: "NANO_BANANA_API_KEY",
  },
  dalle: {
    label: "DALL·E",
    models: ["dall-e-3"],
    defaultModel: "dall-e-3",
    missingEnv: "OPENAI_API_KEY",
  },
};

const DEFAULT_PROVIDER: ImageGenProvider = "dalle";

const IMAGEGEN_ENDPOINTS = {
  nano_banana: "/api/media/generate/image",
  dalle: "/api/media/generate/image",
} as const;

function parseScopeId(value: unknown): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.trunc(parsed);
}

function inferProjectIdFromPathname(): number | null {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/\/(?:projects?|p)\/(\d+)/i);
  if (!match) return null;
  return parseScopeId(match[1]);
}

function inferThreadIdFromPathname(): number | null {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/\/chat\/(\d+)/i);
  if (!match) return null;
  return parseScopeId(match[1]);
}

function inferProjectIdFromStorage(): number | null {
  if (typeof window === "undefined") return null;
  for (const key of PROJECT_ID_STORAGE_KEYS) {
    const raw = window.localStorage.getItem(key);
    const parsed = parseScopeId(raw);
    if (parsed !== null) return parsed;
  }
  return null;
}

function isValidProvider(value: unknown): value is ImageGenProvider {
  return value === "nano_banana" || value === "dalle";
}

function readStoredProvider(): ImageGenProvider {
  if (typeof window === "undefined") return DEFAULT_PROVIDER;
  const raw = window.localStorage.getItem(PROVIDER_STORAGE_KEY);
  if (isValidProvider(raw)) return raw;
  return DEFAULT_PROVIDER;
}

function readStoredModel(provider: ImageGenProvider): string {
  if (typeof window === "undefined") return PROVIDER_CONFIG[provider].defaultModel;
  const raw = (window.localStorage.getItem(MODEL_STORAGE_KEY) || "").trim();
  if (!raw) return PROVIDER_CONFIG[provider].defaultModel;
  if (!PROVIDER_CONFIG[provider].models.includes(raw)) {
    return PROVIDER_CONFIG[provider].defaultModel;
  }
  return raw;
}

function toImageSrc(data: any): string | null {
  const directCandidates = [
    data?.src_url,
    data?.image_url,
    data?.url,
    data?.output_url,
    data?.result?.src_url,
    data?.result?.image_url,
    data?.result?.url,
  ];

  for (const candidate of directCandidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }

  const base64Candidates = [
    data?.b64_json,
    data?.image_base64,
    data?.base64,
    data?.result?.b64_json,
    data?.result?.image_base64,
    Array.isArray(data?.data) ? data.data[0]?.b64_json : undefined,
  ];

  const mimeType =
    (typeof data?.mime_type === "string" && data.mime_type) ||
    (typeof data?.content_type === "string" && data.content_type) ||
    "image/png";

  for (const candidate of base64Candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      const raw = candidate.trim();
      if (raw.startsWith("data:")) return raw;
      return `data:${mimeType};base64,${raw}`;
    }
  }

  return null;
}

function isMissingKeyFailure(provider: ImageGenProvider, err: any): boolean {
  const status = Number(err?.response?.status || 0);
  const detail = String(err?.response?.data?.detail || err?.message || "").toLowerCase();

  if (status === 401 || status === 403) return true;
  if (detail.includes("api key") || detail.includes("not configured") || detail.includes("missing")) {
    return true;
  }

  if (provider === "dalle" && detail.includes("openai_api_key")) return true;
  if (provider === "nano_banana" && detail.includes("nano_banana_api_key")) return true;

  return false;
}

interface ImageGenModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Optional callback with the generated image URL/data */
  onImageGenerated?: (imageUrl: string) => void;
  projectId?: number | string | null;
  threadId?: number | string | null;
  userId?: string;
}

export function ImageGenModal({
  open,
  onOpenChange,
  onImageGenerated,
  projectId,
  threadId,
  userId,
}: ImageGenModalProps) {
  const [prompt, setPrompt] = useState("");
  const [provider, setProvider] = useState<ImageGenProvider>(() => readStoredProvider());
  const [model, setModel] = useState(() => {
    const initialProvider = readStoredProvider();
    return readStoredModel(initialProvider);
  });
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modelOptions = useMemo(() => PROVIDER_CONFIG[provider].models, [provider]);

  useEffect(() => {
    try {
      window.localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
    } catch {
      // ignore storage errors
    }
  }, [provider]);

  useEffect(() => {
    try {
      window.localStorage.setItem(MODEL_STORAGE_KEY, model);
    } catch {
      // ignore storage errors
    }
  }, [model]);

  useEffect(() => {
    const onOpen = () => onOpenChange(true);
    window.addEventListener("cfy:imagegen:open", onOpen as EventListener);
    return () => {
      window.removeEventListener("cfy:imagegen:open", onOpen as EventListener);
    };
  }, [onOpenChange]);

  const resolveScope = useCallback(() => {
    const resolvedProjectId =
      parseScopeId(projectId) ?? inferProjectIdFromStorage() ?? inferProjectIdFromPathname() ?? 1;
    const resolvedThreadId = parseScopeId(threadId) ?? inferThreadIdFromPathname() ?? 1;
    return { resolvedProjectId, resolvedThreadId };
  }, [projectId, threadId]);

  const handleProviderChange = (nextProvider: ImageGenProvider) => {
    setProvider(nextProvider);
    setModel(PROVIDER_CONFIG[nextProvider].defaultModel);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmed = prompt.trim();
    if (!trimmed) {
      setError("Please enter a prompt");
      return;
    }

    const trimmedModel = model.trim();
    if (!trimmedModel) {
      setError("Please select a model");
      return;
    }

    setGenerating(true);
    setError(null);

    try {
      const { resolvedProjectId, resolvedThreadId } = resolveScope();
      const endpoint = IMAGEGEN_ENDPOINTS[provider];
      const response = await api.post(endpoint, {
        prompt: trimmed,
        model: trimmedModel,
        project_id: resolvedProjectId,
        thread_id: resolvedThreadId,
        user_id: userId ?? "default",
      });

      const imageSrc = toImageSrc(response.data);
      if (!imageSrc) {
        setError("No image payload returned from server");
        return;
      }

      // Notify parent if callback provided.
      onImageGenerated?.(imageSrc);

      // Broadcast success for gallery refresh.
      try {
        window.dispatchEvent(
          new CustomEvent("cfy:gallery:add", {
            detail: {
              items: [
                {
                  src: imageSrc,
                  prompt: trimmed,
                  project_id: resolvedProjectId,
                  thread_id: resolvedThreadId,
                  mock: false,
                  tag: "generated",
                },
              ],
            },
          })
        );
      } catch {
        // no-op
      }

      // Show success toast.
      try {
        window.dispatchEvent(
          new CustomEvent("cfy:toast", {
            detail: { message: "Image generated successfully!", duration: 3000 },
          })
        );
      } catch {
        // no-op
      }

      // Reset and close.
      setPrompt("");
      onOpenChange(false);
    } catch (err: any) {
      if (isMissingKeyFailure(provider, err)) {
        setError(
          `API key missing for ${PROVIDER_CONFIG[provider].label}. Add ${PROVIDER_CONFIG[provider].missingEnv} to .env and restart backend.`
        );
      } else {
        const message = err?.response?.data?.detail || err?.message || "Failed to generate image";
        setError(message);
      }
    } finally {
      setGenerating(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => !generating && onOpenChange(false)}
      />

      {/* Modal */}
      <form
        onSubmit={handleSubmit}
        className="relative z-[1201] w-[min(560px,92vw)] rounded-2xl border p-6 flex flex-col gap-4 shadow-xl"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        <div>
          <h2 className="text-lg font-semibold">Generate Image</h2>
          <p className="text-sm mt-1 opacity-70" style={{ color: "var(--muted)" }}>
            Choose a provider and model, then describe the image you want.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="imageProvider">
              Provider
            </label>
            <select
              id="imageProvider"
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value as ImageGenProvider)}
              className="w-full rounded-[var(--tile-radius)] border px-3 py-2 text-sm"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
              disabled={generating}
            >
              <option value="nano_banana">Nano Banana</option>
              <option value="dalle">DALL·E</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="imageModel">
              Model
            </label>
            <select
              id="imageModel"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded-[var(--tile-radius)] border px-3 py-2 text-sm"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
              disabled={generating}
            >
              {modelOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium" htmlFor="imagePrompt">
            Prompt
          </label>
          <Textarea
            id="imagePrompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., A cinematic sunset over neon-lit mountains"
            rows={4}
            className="w-full rounded-xl"
            style={{
              background: "transparent",
              borderColor: "var(--panel-border)",
              color: "var(--text)",
            }}
            disabled={generating}
            autoFocus
          />
          <div className="text-xs opacity-60">
            Using endpoint: <code>{IMAGEGEN_ENDPOINTS[provider]}</code>
          </div>
        </div>

        {error && (
          <div className="text-sm font-medium text-red-400 bg-red-400/10 rounded-lg px-3 py-2">{error}</div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={generating}
            className="rounded-full px-4"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            className="rounded-full px-4"
            disabled={generating || !prompt.trim() || !model.trim()}
          >
            {generating ? (
              <>
                <span className="inline-block h-3 w-3 mr-2 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Generating...
              </>
            ) : (
              "Generate"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default ImageGenModal;
