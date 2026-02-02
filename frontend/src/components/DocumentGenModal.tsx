import React, { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export type DocumentGenInput = {
  title: string;
  prompt: string;
  format: "markdown" | "plain";
  doc_type: "code" | "literature" | "diagram";
};

interface DocumentGenModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit?: (input: DocumentGenInput) => void;
  initialValues?: Partial<DocumentGenInput>;
}

export function DocumentGenModal({
  open,
  onOpenChange,
  onSubmit,
  initialValues,
}: DocumentGenModalProps) {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [format, setFormat] = useState<DocumentGenInput["format"]>("markdown");
  const [docType, setDocType] = useState<DocumentGenInput["doc_type"]>("literature");
  const [error, setError] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement | null>(null);

  const hintId = useMemo(
    () => `doc-gen-hint-${Math.random().toString(36).slice(2, 9)}`,
    []
  );
  const titleId = useMemo(
    () => `doc-gen-title-${Math.random().toString(36).slice(2, 9)}`,
    []
  );

  useEffect(() => {
    if (!open) return;
    setTitle(initialValues?.title ?? "");
    setPrompt(initialValues?.prompt ?? "");
    setFormat(initialValues?.format ?? "markdown");
    setDocType(initialValues?.doc_type ?? "literature");
    setError(null);
    const raf = window.requestAnimationFrame(() => {
      titleRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(raf);
  }, [open, initialValues]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      setError("Prompt is required.");
      return;
    }
    const payload: DocumentGenInput = {
      title: title.trim(),
      prompt: trimmedPrompt,
      format,
      doc_type: docType,
    };
    onSubmit?.(payload);
    onOpenChange(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center px-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      <form
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={hintId}
        className="relative z-[1201] w-[min(560px,90vw)] rounded-2xl border p-6 flex flex-col gap-4 shadow-xl"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        <div>
          <h2 id={titleId} className="text-lg font-semibold">
            Generate Document
          </h2>
          <p
            id={hintId}
            className="text-sm mt-1 opacity-70"
            style={{ color: "var(--muted)" }}
          >
            Draft the details for your document. Generation runs in the next step.
          </p>
        </div>

        <div className="space-y-3">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="docGenTitle">
              Title (optional)
            </label>
            <Input
              id="docGenTitle"
              ref={titleRef}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g., Launch Brief"
              className="rounded-[var(--tile-radius)]"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="docGenPrompt">
              Prompt
            </label>
            <Textarea
              id="docGenPrompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Describe the document you want to generate."
              rows={5}
              className="w-full rounded-xl"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="docGenFormat">
              Output format
            </label>
            <select
              id="docGenFormat"
              value={format}
              onChange={(event) =>
                setFormat(event.target.value as DocumentGenInput["format"])
              }
              className="h-10 w-full rounded-[var(--tile-radius)] border px-3 text-sm"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
            >
              <option value="markdown">Markdown</option>
              <option value="plain">Plain text</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="docGenType">
              Document type
            </label>
            <select
              id="docGenType"
              value={docType}
              onChange={(event) =>
                setDocType(event.target.value as DocumentGenInput["doc_type"])
              }
              className="h-10 w-full rounded-[var(--tile-radius)] border px-3 text-sm"
              style={{
                background: "transparent",
                borderColor: "var(--panel-border)",
                color: "var(--text)",
              }}
            >
              <option value="code">Code</option>
              <option value="literature">Literature</option>
              <option value="diagram">Diagram</option>
            </select>
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
            className="rounded-full px-4"
          >
            Cancel
          </Button>
          <Button type="submit" className="rounded-full px-4">
            Save Draft
          </Button>
        </div>
      </form>
    </div>
  );
}

export default DocumentGenModal;
