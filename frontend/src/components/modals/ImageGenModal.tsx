/**
 * ImageGenModal – Universal image generation modal (PCX_UI_QUIKWINS_002)
 *
 * Single source of truth for image generation across Chat, Gallery, and Dashboard.
 * Uses the backend's configurable provider system (Ollama, DALL-E, Stability, Replicate).
 */

import React, { useCallback, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import api from "@/lib/api";

const DEFAULT_MODELS = ["dall-e-3", "dall-e-2", "sdxl"];
const PROJECT_ID_STORAGE_KEYS = [
  "cfy.projectId",
  "cfy.activeProjectId",
  "cfy.lastProjectId",
  "projectId",
] as const;

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
  const [model, setModel] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_MODELS[0];
    const configured = (window as any).__imageGenModel;
    if (typeof configured === "string" && configured.trim()) {
      return configured.trim();
    }
    return DEFAULT_MODELS[0];
  });
  const modelOptions = useMemo(() => {
    if (typeof window === "undefined") return DEFAULT_MODELS;
    const provided = (window as any).__imageGenModels;
    if (!Array.isArray(provided)) return DEFAULT_MODELS;
    const cleaned = provided
      .map((item) => (typeof item === "string" ? item.trim() : ""))
      .filter((item) => item);
    return cleaned.length ? Array.from(new Set(cleaned)) : DEFAULT_MODELS;
  }, []);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resolveScope = useCallback(() => {
    const resolvedProjectId =
      parseScopeId(projectId)
      ?? inferProjectIdFromStorage()
      ?? inferProjectIdFromPathname()
      ?? 1;
    const resolvedThreadId =
      parseScopeId(threadId)
      ?? inferThreadIdFromPathname()
      ?? 1;
    return { resolvedProjectId, resolvedThreadId };
  }, [projectId, threadId]);

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
      const response = await api.post("/api/media/generate/image", {
        prompt: trimmed,
        model: trimmedModel,
        project_id: resolvedProjectId,
        thread_id: resolvedThreadId,
        user_id: userId ?? "default",
      });

      const imageUrl = response.data?.src_url;
      if (imageUrl) {
        // Notify parent if callback provided
        onImageGenerated?.(imageUrl);

        // Broadcast success for gallery refresh
        try {
          window.dispatchEvent(new CustomEvent("cfy:gallery:add", {
            detail: {
              items: [{
                src: imageUrl,
                prompt: trimmed,
                project_id: resolvedProjectId,
                thread_id: resolvedThreadId,
                mock: false,
                tag: "generated",
              }],
            },
          }));
        } catch {}

        // Show success toast
        try {
          window.dispatchEvent(new CustomEvent("cfy:toast", {
            detail: { message: "Image generated successfully!", duration: 3000 }
          }));
        } catch {}

        // Reset and close
        setPrompt("");
        onOpenChange(false);
      } else {
        setError("No image URL returned from server");
      }
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Failed to generate image";
      setError(message);
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
        className="relative z-[1201] w-[min(540px,90vw)] rounded-2xl border p-6 flex flex-col gap-4 shadow-xl"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
          color: "var(--text)"
        }}
      >
        <div>
          <h2 className="text-lg font-semibold">Generate Image</h2>
          <p className="text-sm mt-1 opacity-70" style={{ color: "var(--muted)" }}>
            Describe the image you want to create. Your configured provider will be used.
          </p>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium" htmlFor="imagePrompt">
            Prompt
          </label>
          <Textarea
            id="imagePrompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., A sunset over mountains, digital art style, vibrant colors"
            rows={4}
            className="w-full rounded-xl"
            style={{
              background: "transparent",
              borderColor: "var(--panel-border)",
              color: "var(--text)"
            }}
            disabled={generating}
            autoFocus
          />
          <div className="text-xs opacity-60">
            Provider: {(window as any).__imageGenProvider || "Auto (from config)"}
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="imageModel">
            Model
          </label>
          <Input
            id="imageModel"
            list="imageModelOptions"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={DEFAULT_MODELS[0]}
            className="rounded-[var(--tile-radius)]"
            style={{
              background: "transparent",
              borderColor: "var(--panel-border)",
              color: "var(--text)",
            }}
            disabled={generating}
          />
          <datalist id="imageModelOptions">
            {modelOptions.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
          <div className="text-xs opacity-60">
            Defaults to {DEFAULT_MODELS[0]} unless configured.
          </div>
        </div>

        {error && (
          <div className="text-sm font-medium text-red-400 bg-red-400/10 rounded-lg px-3 py-2">
            {error}
          </div>
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
