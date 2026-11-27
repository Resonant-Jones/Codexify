import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import {
  generateImage,
  imageGenerationError,
  loadImageCatalog,
  type ImageCatalog,
  type ImageGenerationIntent,
} from "@/features/chat/imageGeneration";

interface ImageGenModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImageGenerated?: (imageUrl: string) => void;
  onGenerate?: (intent: ImageGenerationIntent) => Promise<void>;
  initialPrompt?: string;
  initialModelAlias?: string;
  projectId?: number | string | null;
  threadId?: number | string | null;
  userId?: string;
}

export function ImageGenModal({
  open,
  onOpenChange,
  onImageGenerated,
  onGenerate,
  initialPrompt = "",
  initialModelAlias,
  projectId,
  threadId,
}: ImageGenModalProps) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [catalog, setCatalog] = useState<ImageCatalog | null>(null);
  const [providerId, setProviderId] = useState("");
  const [model, setModel] = useState("");
  const [generating, setGenerating] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const provider = catalog?.providers.find((item) => item.id === providerId);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setPrompt(initialPrompt);
    setError(null);
    setCatalog(null);
    void loadImageCatalog()
      .then((next) => {
        if (!active) return;
        let savedProvider: string | null = null,
          savedModel: string | null = null;
        try {
          savedProvider = localStorage.getItem("cfy.imagegen.provider");
          savedModel = localStorage.getItem("cfy.imagegen.model");
        } catch {
          /* Optional preferences. */
        }
        const selected =
          (initialModelAlias &&
            next.providers.find((item) => item.model_aliases[initialModelAlias])) ||
          next.providers.find((item) => item.id === savedProvider) ||
          next.providers.find((item) => item.id === next.default_provider) ||
          next.providers[0];
        setCatalog(next);
        setProviderId(selected?.id || "");
        const useSavedModel = !savedProvider || selected?.id === savedProvider;
        const aliasModel = initialModelAlias && selected?.model_aliases[initialModelAlias];
        if (!aliasModel && useSavedModel && savedModel && !selected?.models.includes(savedModel)) {
          setModel("");
          setError("Your saved image model is no longer offered. Choose a replacement.");
          return;
        }
        setModel(
          aliasModel ||
            (useSavedModel && savedModel
              ? savedModel
              : selected?.models.includes(next.default_model)
                ? next.default_model
                : selected?.default_model || "")
        );
      })
      .catch((err: unknown) => {
        if (active) setError(imageGenerationError(err));
      });
    return () => {
      active = false;
    };
  }, [open, initialPrompt, initialModelAlias]);

  useEffect(() => {
    const onOpen = () => onOpenChange(true);
    window.addEventListener("cfy:imagegen:open", onOpen);
    return () => window.removeEventListener("cfy:imagegen:open", onOpen);
  }, [onOpenChange]);

  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div className="fixed inset-0 z-[1200] flex items-center justify-center px-4 py-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => !generating && onOpenChange(false)}
      />
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="imagegen-title"
        className="relative z-[1201] max-h-[calc(100dvh-2rem)] w-[min(560px,92vw)] overflow-y-auto rounded-2xl border p-6 flex flex-col gap-4 shadow-xl"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
        onSubmit={async (event) => {
          event.preventDefault();
          if (submitting.current || !provider?.available || !prompt.trim() || !model) return;
          submitting.current = true;
          setGenerating(true);
          setError(null);
          try {
            try {
              localStorage.setItem("cfy.imagegen.provider", providerId);
              localStorage.setItem("cfy.imagegen.model", model);
            } catch {
              /* Optional preferences. */
            }
            const intent = { prompt: prompt.trim(), provider: providerId, model };
            if (onGenerate) await onGenerate(intent);
            else {
              const image = await generateImage(intent, {
                projectId: Number(projectId) > 0 ? Number(projectId) : null,
                threadId: Number(threadId) > 0 ? Number(threadId) : null,
              });
              onImageGenerated?.(image.src_url);
            }
            onOpenChange(false);
          } catch (err) {
            setError(imageGenerationError(err));
          } finally {
            submitting.current = false;
            setGenerating(false);
          }
        }}
      >
        <h2 id="imagegen-title" className="text-lg font-semibold">
          Generate image
        </h2>
        <label className="flex flex-col gap-2">
          Prompt
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={generating}
            className="rounded-xl border bg-transparent p-3"
            rows={4}
            placeholder="Describe what you’d like to see…"
          />
        </label>
        <label className="flex flex-col gap-2">
          Provider
          <select
            className="rounded-lg border bg-[var(--panel-bg)] p-2"
            value={providerId}
            disabled={generating || !catalog}
            onChange={(e) => {
              setProviderId(e.target.value);
              setError(null);
              setModel(
                catalog?.providers.find((item) => item.id === e.target.value)?.default_model || ""
              );
            }}
          >
            {!catalog && <option value="">Loading image models…</option>}
            {catalog?.providers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2">
          Model
          <select
            className="rounded-lg border bg-[var(--panel-bg)] p-2"
            value={model}
            disabled={generating || !provider}
            onChange={(e) => {
              setModel(e.target.value);
              setError(null);
            }}
          >
            {!model && <option value="" disabled>Choose an image model</option>}
            {provider?.models.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs opacity-70">
          One image per request. You can also use /sunburst, /flare, or /image in chat.
        </p>
        {!provider?.available && provider?.unavailable_reason && (
          <p role="status">Image generation is unavailable in this runtime.</p>
        )}
        {error && (
          <p role="alert" className="text-sm text-red-400">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="ghost"
            disabled={generating}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={generating || !prompt.trim() || !model || !provider?.available}
          >
            {generating ? "Generating image…" : "Generate"}
          </Button>
        </div>
      </form>
    </div>,
    document.body
  );
}
export default ImageGenModal;
