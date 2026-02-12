/**
 * Composer.tsx
 *
 * Renders the chat composer input and controls, including turn-based gating
 * to prevent overlapping user sends while an assistant reply is in flight.
 */
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Paperclip, ImagePlus, X, FileText } from "lucide-react";
import { UploadedAttachment, toAbsoluteMediaUrl } from "@/hooks/useUploader";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

const ACCEPTED_ATTACHMENTS =
  "image/*,application/pdf,text/plain,text/markdown,.md,.txt";

function inferProjectIdFromLocation(fallback = 1): number {
  if (typeof window === "undefined") return fallback;
  const path = window.location.pathname || "";
  // Common shapes: /projects/:id, /project/:id, /p/:id
  const match = path.match(/\/(?:projects?|p)\/(\d+)/i);
  if (!match) return fallback;
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function inferProjectIdFromStorage(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const keys = ["cfy.projectId", "cfy.activeProjectId", "projectId"];
    for (const key of keys) {
      const raw = window.localStorage.getItem(key);
      const parsed = Number(raw);
      if (Number.isFinite(parsed)) return parsed;
    }
  } catch {}
  return null;
}

export function Composer({
  onSend,
  prefill,
  onPrefillConsumed,
  threadId,
  isSending,
  isTurnInFlight,
}: {
  onSend: (t: string) => Promise<void> | void;
  prefill?: string;
  onPrefillConsumed?: () => void;
  threadId?: number;
  isSending?: boolean;
  isTurnInFlight?: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  // Initialize with saved draft if available
  const [value, setValue] = useState(() => {
    if (threadId && typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem(`composer-draft-${threadId}`);
        if (saved) return saved;
      } catch {}
    }
    return "";
  });

  const [internalSending, setInternalSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showImgGen, setShowImgGen] = useState(false);
  const effectiveSending = Boolean(isSending) || internalSending;
  const turnLocked = Boolean(isTurnInFlight);
  const actionsDisabled = turnLocked || effectiveSending || uploading;

  type DraftAttachment = {
    id: string;
    file: File;
    kind: "image" | "document";
    previewUrl?: string;
  };

  const [draftAttachments, setDraftAttachments] = useState<DraftAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const showToast = (message: string) => {
    try {
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message, kind: "error" } }));
    } catch {}
  };
  const notifyTurnLocked = () => {
    showToast("One moment—finish the current reply first.");
  };

  // Auto-save draft to sessionStorage
  useEffect(() => {
    if (threadId && typeof window !== "undefined") {
      try {
        if (value.trim()) {
          sessionStorage.setItem(`composer-draft-${threadId}`, value);
        } else {
          sessionStorage.removeItem(`composer-draft-${threadId}`);
        }
      } catch {}
    }
  }, [value, threadId]);

  // Revoke object URLs on unmount to avoid leaking blob URLs.
  useEffect(() => {
    return () => {
      for (const attachment of draftAttachments) {
        if (attachment.previewUrl) {
          try {
            URL.revokeObjectURL(attachment.previewUrl);
          } catch {}
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const buildChatAttachmentMessage = (items: UploadedAttachment[], bodyText: string) => {
    const lines: string[] = [];

    for (const item of items) {
      const kind = item.kind;
      const id = (item.id ?? "").toString().trim();
      const src = toAbsoluteMediaUrl(item.src_url);
      const name = (item.filename ?? "").toString().trim();

      // Primary marker for backend worker; keep format stable.
      lines.push(`<!-- cfy-media:${kind}:${id || "missing-id"} -->`);
      if (src) lines.push(`<!-- cfy-media-src:${src} -->`);
      if (name) lines.push(`<!-- cfy-media-name:${name} -->`);
    }

    const body = bodyText.trim();
    if (body) lines.push(body);

    return lines.join("\n\n").trim();
  };

  const resolveProjectId = () => {
    // Prefer explicit storage values to reduce reliance on URL shape.
    const fromStorage = inferProjectIdFromStorage();
    if (fromStorage !== null) return fromStorage;
    return inferProjectIdFromLocation(1);
  };

  function stageFiles(files: FileList | File[]) {
    const arr = Array.from(files || []);
    if (!arr.length) return;
    if (actionsDisabled) {
      notifyTurnLocked();
      return;
    }

    setDraftAttachments((prev) => {
      const next = [...prev];
      for (const file of arr) {
        // Prevent duplicate staging of the exact same file within the draft.
        const exists = next.some(
          (item) =>
            item.file.name === file.name &&
            item.file.size === file.size &&
            item.file.type === file.type
        );
        if (exists) continue;
        const isImage = file.type.startsWith("image/");
        next.push({
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          file,
          kind: isImage ? "image" : "document",
          previewUrl: isImage ? URL.createObjectURL(file) : undefined,
        });
      }
      return next;
    });
  }

  function removeDraftAttachment(id: string) {
    setDraftAttachments((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target?.previewUrl) {
        try {
          URL.revokeObjectURL(target.previewUrl);
        } catch {}
      }
      return prev.filter((item) => item.id !== id);
    });
  }

  async function uploadOneAttachment(att: DraftAttachment): Promise<UploadedAttachment | null> {
    const file = att.file;
    if (!file) return null;
    if (typeof threadId !== "number") {
      showToast("Attachments need an active thread before they can upload.");
      return null;
    }

    const endpoint =
      att.kind === "image" ? "/api/media/upload/image" : "/api/media/upload/document";
    const form = new FormData();
    form.append("project_id", String(resolveProjectId()));
    form.append("thread_id", String(threadId));
    form.append("file", file);
    form.append("tag", "uploaded");

    try {
      const res = await api.post(endpoint, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = (res as any)?.data ?? res;
      const src = data?.src_url;
      if (!src) {
        showToast("Upload succeeded but no media URL was returned.");
        return null;
      }
      return {
        kind: att.kind,
        id: data?.id,
        src_url: toAbsoluteMediaUrl(String(src)),
        filename: data?.filename || file.name,
      };
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to upload attachment.";
      showToast(message);
      return null;
    }
  }

  function onPaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
      stageFiles(files);
    }
  }
  useEffect(() => {
    if (prefill && prefill !== value) {
      setValue(prefill);
      setTimeout(() => ref.current?.focus(), 0);
      onPrefillConsumed && onPrefillConsumed();
    }
  }, [prefill]);
  async function send() {
    if (effectiveSending || uploading) return;
    if (turnLocked) {
      notifyTurnLocked();
      return;
    }

    const bodyText = value.trim();
    const hasAttachments = draftAttachments.length > 0;
    if (!bodyText && !hasAttachments) return;

    setInternalSending(true);
    setUploading(hasAttachments);

    try {
      let uploaded: UploadedAttachment[] = [];
      if (hasAttachments) {
        for (const att of draftAttachments) {
          const result = await uploadOneAttachment(att);
          if (result) uploaded.push(result);
        }
      }

      const message = hasAttachments
        ? buildChatAttachmentMessage(uploaded, bodyText)
        : bodyText;

      if (!message) {
        showToast("No attachments could be uploaded.");
        return;
      }

      await onSend(message);

      // Clear the draft after a successful send.
      setValue("");
      setDraftAttachments((prev) => {
        for (const attachment of prev) {
          if (attachment.previewUrl) {
            try {
              URL.revokeObjectURL(attachment.previewUrl);
            } catch {}
          }
        }
        return [];
      });
      if (threadId && typeof window !== "undefined") {
        try {
          sessionStorage.removeItem(`composer-draft-${threadId}`);
        } catch {}
      }

      if (uploaded.length) {
        const imageItems = uploaded
          .filter((item) => item.kind === "image")
          .map((item) => ({
            src: item.src_url,
            prompt: item.filename,
            id: item.id,
            tag: "uploaded",
          }));
        const docItems = uploaded
          .filter((item) => item.kind === "document")
          .map((item) => {
            const filename = item.filename || "Document";
            const extMatch = filename.match(/\.([a-z0-9]+)$/i);
            const ext = extMatch ? extMatch[1].toLowerCase() : "pdf";
            return {
              id: item.id,
              name: filename.replace(/\.[^.]+$/, ""),
              ext,
              filename,
              src_url: item.src_url,
              tag: "uploaded",
            };
          });

        try {
          if (imageItems.length) {
            window.dispatchEvent(
              new CustomEvent("cfy:gallery:add", {
                detail: { items: imageItems },
              })
            );
          }
          if (docItems.length) {
            window.dispatchEvent(
              new CustomEvent("cfy:documents:add", {
                detail: { items: docItems },
              })
            );
          }
          localStorage.setItem("cfy.hasUserUpload", "true");
        } catch {}
      }
    } catch (err: any) {
      const message = err?.message || "Failed to send message.";
      showToast(message);
    } finally {
      setUploading(false);
      setInternalSending(false);
    }
  }
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (actionsDisabled) {
      notifyTurnLocked();
      return;
    }
    if (e.dataTransfer?.files?.length) {
      stageFiles(e.dataTransfer.files);
    }
  };
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };
  return (
    <>
      <div className="flex flex-col flex-1 w-full p-[4px]" onDrop={handleDrop} onDragOver={handleDragOver}>
        <div className="flex flex-col flex-1 w-full rounded-[var(--tile-radius)] p-[4px]">
          {/* Content Rectangle - Textarea area */}
          <div className="flex-1 flex flex-col px-[12px] pt-[8px] pb-[6px]">
            <Textarea
              ref={ref}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Write a message…"
              onPaste={onPaste}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (turnLocked) {
                    notifyTurnLocked();
                    return;
                  }
                  void send();
                }
              }}
              className="w-full min-h-[96px] resize-none border-0 bg-transparent text-base leading-relaxed focus-visible:ring-0 focus-visible:outline-none shadow-none placeholder:text-white/20"
              style={{ color: "var(--text)" }}
            />
          </div>

          {draftAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2 px-[12px] pb-[6px]">
              {draftAttachments.map((att) => (
                <div
                  key={att.id}
                  className="relative overflow-hidden rounded-[var(--tile-radius)] border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5"
                  style={{ width: 88, height: 68 }}
                  title={att.file.name}
                >
                  {att.kind === "image" ? (
                    <img
                      src={att.previewUrl}
                      alt={att.file.name}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center">
                      <FileText className="h-5 w-5 opacity-70" />
                    </div>
                  )}
                  <button
                    type="button"
                    aria-label="Remove attachment"
                    onClick={() => removeDraftAttachment(att.id)}
                    className="absolute right-1 top-1 grid h-5 w-5 place-items-center rounded-full bg-black/50 text-white"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Toolbar Row - Bottom controls */}
          <div className="flex items-center justify-between px-[8px] pb-[6px]">
            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_ATTACHMENTS}
                multiple
                style={{ display: "none" }}
                onChange={(e) => {
                  const files = e.target.files;
                  e.currentTarget.value = "";
                  if (files && files.length) stageFiles(files);
                }}
              />
              <button
                type="button"
                aria-label="Attach files"
                title="Attach files"
                aria-disabled={actionsDisabled}
                onClick={() => {
                  if (actionsDisabled) {
                    notifyTurnLocked();
                    return;
                  }
                  fileInputRef.current?.click();
                }}
                tabIndex={actionsDisabled ? -1 : 0}
                className={cn(
                  "inline-flex items-center justify-center h-9 w-9 transition-opacity",
                  actionsDisabled ? "opacity-40 cursor-not-allowed" : "opacity-70 hover:opacity-100"
                )}
                style={{
                  background: "none",
                  border: "none",
                  boxShadow: "none",
                  outline: "none",
                }}
              >
                <Paperclip className="h-5 w-5" />
              </button>
              <button
                type="button"
                aria-label="Generate image"
                title="Generate image"
                aria-disabled={actionsDisabled}
                onClick={() => {
                  if (actionsDisabled) {
                    notifyTurnLocked();
                    return;
                  }
                  setShowImgGen(true);
                }}
                tabIndex={actionsDisabled ? -1 : 0}
                className={cn(
                  "inline-flex items-center justify-center h-9 w-9 transition-opacity",
                  actionsDisabled ? "opacity-40 cursor-not-allowed" : "opacity-70 hover:opacity-100"
                )}
                style={{
                  background: "none",
                  border: "none",
                  boxShadow: "none",
                  outline: "none",
                }}
              >
                <ImagePlus className="h-5 w-5" />
              </button>
            </div>

              <Button
                type="button"
                onClick={send}
                disabled={actionsDisabled || (!value.trim() && draftAttachments.length === 0)}
                aria-disabled={actionsDisabled || (!value.trim() && draftAttachments.length === 0)}
                tabIndex={actionsDisabled || (!value.trim() && draftAttachments.length === 0) ? -1 : 0}
                size="sm"
                className={cn(
                  "h-9 px-5 mr-[8px] rounded-full font-medium text-sm transition-opacity",
                  (actionsDisabled || (!value.trim() && draftAttachments.length === 0)) ? "opacity-50 cursor-not-allowed" : ""
                )}
              style={{
                background: "var(--accent-strong)",
                color: "#fff",
                boxShadow: "none",
              }}
            >
              Send
            </Button>
          </div>
          {turnLocked && (
            <div className="flex items-center gap-2 px-[8px] pb-[6px]" aria-live="polite">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs opacity-70" style={{ color: "var(--muted)" }}>
                Assistant is responding…
              </span>
            </div>
          )}
        </div>
      </div>
      <ImageGenModal
        open={showImgGen}
        onOpenChange={setShowImgGen}
        projectId={resolveProjectId()}
        threadId={threadId ?? null}
      />
    </>
  );
}

export default Composer;
