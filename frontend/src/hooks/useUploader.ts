import { useCallback } from "react";

export type Accepted = ".pdf" | ".docx" | ".md" | ".txt" | ".png" | ".jpg" | ".jpeg" | ".webp";

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const DOC_EXT = new Set([".pdf", ".docx", ".md", ".txt"]);

function extOf(name: string): Accepted | null {
  const m = name.toLowerCase().match(/\.(pdf|docx|md|txt|png|jpg|jpeg|webp)$/);
  if (!m) return null;
  const e = `.${m[1]}` as Accepted;
  return e;
}

export function useUploader({
  onImages,
  onDocuments,
  onAnyUpload,
  tag,
}: {
  onImages: (items: { src: string; prompt: string; mock?: boolean }[]) => void;
  onDocuments: (items: { name: string; ext: string; mock?: boolean; source?: string }[]) => void;
  onAnyUpload?: () => void;
  tag?: string; // optional source tag (e.g., "chat", "project:<id>")
}) {
  const accept = ".pdf,.docx,.md,.txt,.png,.jpg,.jpeg,.webp";

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const arr = Array.from(files);
    const imgs: { src: string; prompt: string; mock?: boolean }[] = [];
    const docs: { name: string; ext: string; mock?: boolean; source?: string }[] = [];

    const readAsDataUrl = (file: File) => new Promise<string>((res, rej) => {
      const rd = new FileReader();
      rd.onload = () => res(String(rd.result || ""));
      rd.onerror = () => rej(new Error("read error"));
      rd.readAsDataURL(file);
    });
    const readAsText = (file: File) => new Promise<string>((res, rej) => {
      const rd = new FileReader();
      rd.onload = () => res(String(rd.result || ""));
      rd.onerror = () => rej(new Error("read error"));
      rd.readAsText(file);
    });

    // Collect ingestion payloads for optional backend POST
    type IngestItem = { filename: string; mimeType: string; fileBytes: string; source?: string; tags?: string[] };
    const ingestItems: IngestItem[] = [];

    for (const f of arr) {
      const ext = extOf(f.name);
      if (!ext) continue;
      try {
        if (IMAGE_EXT.has(ext)) {
          const data = await readAsDataUrl(f);
          imgs.push({ src: data, prompt: f.name });
          // data URL looks like data:mime;base64,XXXX
          const base64 = (data.split(",")[1] || "");
          ingestItems.push({ filename: f.name, mimeType: f.type || "image/*", fileBytes: base64, source: tag || "upload", tags: [] });
        } else if (DOC_EXT.has(ext)) {
          // For text-like files, read content and optionally request embeddings
          let preview = f.name;
          if (ext === ".txt" || ext === ".md") {
            try {
              const txt = await readAsText(f);
              preview = txt.slice(0, 2000);
            } catch {}
          }
          docs.push({ name: f.name.replace(/\.[^.]+$/, ""), ext: ext.replace(".", ""), source: tag });
          const data = await readAsDataUrl(f);
          const base64 = (data.split(",")[1] || "");
          ingestItems.push({ filename: f.name, mimeType: f.type || "application/octet-stream", fileBytes: base64, source: tag || "upload", tags: [] });
          // Best-effort embedding call; ignore failures.
          try {
            const body = { texts: [preview] } as any;
            fetch("/api/embeddings", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }).catch(() => {});
          } catch {}
        }
      } catch {}
    }

    if (imgs.length) onImages(imgs);
    if (docs.length) onDocuments(docs);
    // Emit debug hook with full payloads
    try { window.dispatchEvent(new CustomEvent("cfy:documents:upload", { detail: { items: ingestItems } })); } catch {}

    // Optional ingestion POST if enabled and endpoint configured
    try {
      const enabled = (typeof window !== "undefined") && localStorage.getItem("cfy.ingest.enabled") === "true";
      const endpoint = (import.meta as any).env?.VITE_INGESTION_ENDPOINT as string | undefined;
      if (enabled && endpoint && ingestItems.length) {
        for (const it of ingestItems) {
          try {
            const resp = await fetch(endpoint, {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ ...it }),
            });
            if (!resp.ok) throw new Error(String(resp.status));
            try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: `Ingested ${it.filename}` } })); } catch {}
          } catch (err) {
            try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: `Ingestion failed: ${it.filename}` } })); } catch {}
          }
        }
      }
    } catch {}
    try {
      localStorage.setItem("cfy.hasUserUpload", "true");
    } catch {}
    onAnyUpload?.();
  }, [onImages, onDocuments, onAnyUpload, tag]);

  return {
    accept,
    handleFiles,
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer?.files?.length) handleFiles(e.dataTransfer.files);
    },
    onDragOver: (e: React.DragEvent) => e.preventDefault(),
    pick: () => {
      const input = document.createElement("input");
      input.type = "file";
      input.multiple = true;
      input.accept = accept;
      input.onchange = () => {
        if (input.files) handleFiles(input.files);
      };
      input.click();
    },
  } as const;
}

export default useUploader;
