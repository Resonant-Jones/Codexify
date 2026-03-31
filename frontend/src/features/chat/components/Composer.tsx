/**
 * Composer.tsx
 *
 * Renders the chat composer input and controls, including turn-based gating
 * to prevent overlapping user sends while an assistant reply is in flight.
 */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, X, FileText } from "lucide-react";
import { UploadedAttachment, toAbsoluteMediaUrl } from "@/hooks/useUploader";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { ComposerActionMenu } from "@/features/chat/components/ComposerActionMenu";
import ComposerSelectMenu, {
  type ComposerSelectOption,
} from "@/features/chat/components/ComposerSelectMenu";
import {
  DEFAULT_COMPOSER_INFERENCE_MODE,
  type ComposerInferenceMode,
} from "@/types/inference";
import {
  CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
  CHAT_COMPOSER_SEND_EDGE_INSET_CLASS,
} from "@/features/chat/chatLane";
const ACCEPTED_ATTACHMENTS =
  [
    "image/*",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    ".docx",
    ".md",
    ".txt",
  ].join(",");
const DEFAULT_DRAFT_SYNC_DEBOUNCE_MS = 350;
const MIN_COMPOSER_ROWS = 2;
const MAX_COMPOSER_ROWS = 6;
const FALLBACK_LINE_HEIGHT_PX = 24;
const GENERIC_UPLOAD_ERROR_MESSAGE = "Upload failed. Please try again.";
const COMPOSER_TEXTAREA_PAD_X = "var(--composer-text-pad-x, 14px)";
const COMPOSER_TEXTAREA_PAD_Y = "var(--composer-text-pad-y, 10px)";

const parsePx = (value?: string | null) => {
  const parsed = Number.parseFloat(value ?? "");
  return Number.isFinite(parsed) ? parsed : 0;
};

const measureComposerHeights = (el: HTMLTextAreaElement) => {
  const style = window.getComputedStyle(el);
  const lineHeight = (() => {
    const fromStyle = parsePx(style.lineHeight);
    if (fromStyle) return fromStyle;
    const fontSize = parsePx(style.fontSize);
    return fontSize ? fontSize * 1.5 : FALLBACK_LINE_HEIGHT_PX;
  })();

  const paddingBlock = parsePx(style.paddingTop) + parsePx(style.paddingBottom);
  const borderBlock = parsePx(style.borderTopWidth) + parsePx(style.borderBottomWidth);

  return {
    minHeight: lineHeight * MIN_COMPOSER_ROWS + paddingBlock + borderBlock,
    maxHeight: lineHeight * MAX_COMPOSER_ROWS + paddingBlock + borderBlock,
  } as const;
};

const autosizeComposerTextarea = (el: HTMLTextAreaElement) => {
  const { minHeight, maxHeight } = measureComposerHeights(el);
  el.style.minHeight = `${minHeight}px`;
  el.style.maxHeight = `${maxHeight}px`;
  el.style.height = "auto";
  const nextHeight = Math.min(el.scrollHeight, maxHeight);
  el.style.height = `${nextHeight}px`;
  el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
};

export type ComposerSendOptions = {
  threadIdOverride?: number;
};

type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";
type SourceMode = "project" | "personal_knowledge";

type DraftAttachment = {
  id: string;
  file: File;
  kind: "image" | "document";
  previewUrl?: string;
};

function normalizeOptionalPositiveProjectId(value: unknown): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return parsed > 0 ? parsed : null;
}

function inferProjectIdFromLocation(fallback: number | null = null): number | null {
  if (typeof window === "undefined") return fallback;
  const path = window.location.pathname || "";
  // Common shapes: /projects/:id, /project/:id, /p/:id
  const match = path.match(/\/(?:projects?|p)\/(\d+)/i);
  if (!match) return fallback;
  return normalizeOptionalPositiveProjectId(match[1]) ?? fallback;
}

function inferProjectIdFromStorage(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const keys = [
      "cfy.projectId",
      "cfy.activeProjectId",
      "cfy.generalProjectId",
      "cfy.defaultProjectId",
      "projectId",
    ];
    for (const key of keys) {
      const raw = window.localStorage.getItem(key);
      const parsed = normalizeOptionalPositiveProjectId(raw);
      if (parsed !== null) return parsed;
    }
  } catch {}
  return null;
}

function sanitizeUploadError(err: unknown): string {
  const detail = (err as any)?.response?.data?.detail;
  const rawMessage =
    typeof detail === "string"
      ? detail
      : typeof detail?.message === "string"
        ? detail.message
        : typeof (err as any)?.message === "string"
          ? (err as any).message
          : "";

  if (!rawMessage.trim()) {
    return GENERIC_UPLOAD_ERROR_MESSAGE;
  }

  if (
    /(foreignkey|psycopg|sqlalchemy|traceback|stack trace|insert into|constraint)/i.test(
      rawMessage
    )
  ) {
    return GENERIC_UPLOAD_ERROR_MESSAGE;
  }

  return rawMessage;
}

export function Composer({
  onSend,
  ensureThreadIdForAttachments,
  prefill,
  onPrefillConsumed,
  threadId,
  isSending,
  isTurnInFlight,
  draftValue,
  draftScopeKey,
  draftSyncDebounceMs,
  onDraftValueChange,
  activeProviderId,
  providerOptions = [],
  providerOpenSignal,
  onProviderChange,
  activeModelId = "default",
  modelOptions = [],
  onModelChange,
  activeInferenceMode = DEFAULT_COMPOSER_INFERENCE_MODE,
  inferenceModeOptions = [],
  onInferenceModeChange,
  sourceMode = "project",
  sourceOptions = [],
  onSourceModeChange,
  depthMode = "normal",
  depthOptions = [],
  onDepthModeChange,
  onVoiceTurn,
  voiceTurnLabel = "Upload voice turn",
}: {
  onSend: (t: string, options?: ComposerSendOptions) => Promise<void> | void;
  ensureThreadIdForAttachments?: (
    bodyText: string
  ) => Promise<number | null>;
  prefill?: string;
  onPrefillConsumed?: () => void;
  threadId?: number;
  isSending?: boolean;
  isTurnInFlight?: boolean;
  draftValue?: string;
  draftScopeKey?: string;
  draftSyncDebounceMs?: number;
  onDraftValueChange?: (value: string) => void;
  activeProviderId?: string | null;
  providerOptions?: ComposerSelectOption[];
  providerOpenSignal?: number;
  onProviderChange?: (providerId: string) => void;
  activeModelId?: string;
  modelOptions?: ComposerSelectOption[];
  onModelChange?: (modelId: string) => void;
  activeInferenceMode?: ComposerInferenceMode;
  inferenceModeOptions?: ComposerSelectOption[];
  onInferenceModeChange?: (mode: ComposerInferenceMode) => void;
  sourceMode?: SourceMode;
  sourceOptions?: ComposerSelectOption[];
  onSourceModeChange?: (mode: SourceMode) => void;
  depthMode?: DepthMode;
  depthOptions?: Array<{
    value: DepthMode;
    label: string;
    description: string;
  }>;
  onDepthModeChange?: (mode: DepthMode) => void;
  onVoiceTurn?: () => void;
  voiceTurnLabel?: string;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const syncDebounceMs = Math.max(
    0,
    draftSyncDebounceMs ?? DEFAULT_DRAFT_SYNC_DEBOUNCE_MS
  );
  const resolveInitialDraft = (): string => {
    if (typeof draftValue === "string") {
      return draftValue;
    }
    if (threadId && typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem(`composer-draft-${threadId}`);
        if (saved) return saved;
      } catch {}
    }
    return "";
  };

  // Initialize with saved draft if available
  const [value, setValue] = useState(() => resolveInitialDraft());
  const valueRef = useRef(value);
  const lastCommittedDraftRef = useRef(value);
  const draftCommitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [internalSending, setInternalSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showImgGen, setShowImgGen] = useState(false);
  const effectiveSending = Boolean(isSending) || internalSending;
  const turnLocked = Boolean(isTurnInFlight);
  const transportBusy = effectiveSending || uploading;
  const draftControlsDisabled = transportBusy;
  const voiceTurnDisabled = turnLocked || transportBusy;

  const [draftAttachments, setDraftAttachments] = useState<DraftAttachment[]>([]);
  const hasDraftContent = Boolean(value.trim()) || draftAttachments.length > 0;
  const sendTransportDisabled = transportBusy || !hasDraftContent;
  const sendBlockedByTurnLock = turnLocked && hasDraftContent && !transportBusy;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const showToast = (message: string) => {
    try {
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message, kind: "error" } }));
    } catch {}
  };
  const notifyTurnLocked = () => {
    showToast("Keep typing. Send unlocks when the current reply finishes.");
  };
  const notifyTransportBusy = () => {
    showToast("Finishing the current send…");
  };

  const clearDraftCommitTimer = () => {
    if (!draftCommitTimerRef.current) return;
    clearTimeout(draftCommitTimerRef.current);
    draftCommitTimerRef.current = null;
  };

  useLayoutEffect(() => {
    if (!ref.current) return;
    autosizeComposerTextarea(ref.current);
  }, [value]);

  const commitDraftNow = (nextValue = valueRef.current) => {
    if (!onDraftValueChange) return;
    clearDraftCommitTimer();
    if (lastCommittedDraftRef.current === nextValue) return;
    lastCommittedDraftRef.current = nextValue;
    onDraftValueChange(nextValue);
  };

  const scheduleDraftCommit = (nextValue = valueRef.current) => {
    if (!onDraftValueChange) return;
    clearDraftCommitTimer();
    if (lastCommittedDraftRef.current === nextValue) return;
    draftCommitTimerRef.current = setTimeout(() => {
      draftCommitTimerRef.current = null;
      if (lastCommittedDraftRef.current === nextValue) return;
      lastCommittedDraftRef.current = nextValue;
      onDraftValueChange(nextValue);
    }, syncDebounceMs);
  };

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  // Flush pending draft for previous scope before switching tabs/unmounting.
  useEffect(() => {
    return () => {
      commitDraftNow(valueRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftScopeKey, onDraftValueChange]);

  // Re-initialize local draft when the active tab scope changes.
  useEffect(() => {
    const initial = resolveInitialDraft();
    clearDraftCommitTimer();
    valueRef.current = initial;
    lastCommittedDraftRef.current = initial;
    setValue(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftScopeKey, draftValue, threadId]);

  // Auto-save draft to sessionStorage
  useEffect(() => {
    if (onDraftValueChange) return;
    if (threadId && typeof window !== "undefined") {
      try {
        if (value.trim()) {
          sessionStorage.setItem(`composer-draft-${threadId}`, value);
        } else {
          sessionStorage.removeItem(`composer-draft-${threadId}`);
        }
      } catch {}
    }
  }, [onDraftValueChange, value, threadId]);

  // Revoke object URLs on unmount to avoid leaking blob URLs.
  useEffect(() => {
    return () => {
      clearDraftCommitTimer();
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

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const onBeforeUnload = () => {
      commitDraftNow(valueRef.current);
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onDraftValueChange]);

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
    return inferProjectIdFromLocation(null);
  };

  function stageFiles(files: FileList | File[]) {
    const arr = Array.from(files || []);
    if (!arr.length) return;
    if (draftControlsDisabled) {
      notifyTransportBusy();
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

  async function uploadOneAttachment(
    att: DraftAttachment,
    uploadThreadId: number
  ): Promise<UploadedAttachment | null> {
    const file = att.file;
    if (!file) return null;

    const endpoint =
      att.kind === "image" ? "/api/media/upload/image" : "/api/media/upload/document";
    const form = new FormData();
    const resolvedProjectId = resolveProjectId();
    if (resolvedProjectId !== null) {
      form.append("project_id", String(resolvedProjectId));
    }
    form.append("thread_id", String(uploadThreadId));
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
      showToast(sanitizeUploadError(err));
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
      valueRef.current = prefill;
      commitDraftNow(prefill);
      setTimeout(() => ref.current?.focus(), 0);
      onPrefillConsumed && onPrefillConsumed();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onPrefillConsumed, prefill, value]);
  async function send() {
    if (transportBusy) return;
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
      let uploadThreadId = typeof threadId === "number" ? threadId : null;

      if (hasAttachments && uploadThreadId == null) {
        uploadThreadId = ensureThreadIdForAttachments
          ? await ensureThreadIdForAttachments(bodyText)
          : null;
        if (uploadThreadId == null) {
          showToast("Attachments need an active thread before they can send.");
          return;
        }
      }

      if (hasAttachments) {
        for (const att of draftAttachments) {
          const result = await uploadOneAttachment(att, uploadThreadId as number);
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

      commitDraftNow(valueRef.current);
      await onSend(message, {
        threadIdOverride:
          uploadThreadId != null && uploadThreadId !== threadId
            ? uploadThreadId
            : undefined,
      });

      // Clear the draft after a successful send.
      setValue("");
      valueRef.current = "";
      commitDraftNow("");
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
    if (draftControlsDisabled) {
      notifyTransportBusy();
      return;
    }
    if (e.dataTransfer?.files?.length) {
      stageFiles(e.dataTransfer.files);
    }
  };
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const providerLabel =
    providerOptions.find((option) => option.value === activeProviderId)?.label ??
    providerOptions[0]?.label ??
    "Provider";
  const modelLabel =
    modelOptions.find((option) => option.value === activeModelId)?.label ??
    modelOptions[0]?.label ??
    "Model";
  const hasImageAttachments = draftAttachments.some((att) => att.kind === "image");
  const hasVisionCapableModel = modelOptions.some((option) => {
    if (option.supportsChat === false || option.modelKind === "utility") {
      return false;
    }
    return option.supportsVision === true;
  });
  const imageCapabilityMessage = hasImageAttachments
    ? hasVisionCapableModel
      ? "Image attached. Vision-capable chat models can inspect it; text-only chat models will not see it natively."
      : "Image attached, but no vision-capable chat models are available for this provider."
    : null;
  const inferenceModeLabel =
    inferenceModeOptions.find((option) => option.value === activeInferenceMode)
      ?.label ??
    "Auto";
  const sourceLabel =
    sourceOptions.find((option) => option.value === sourceMode)?.label ??
    sourceOptions[0]?.label ??
    "Project";
  const handleAttemptSend = () => {
    if (turnLocked) {
      notifyTurnLocked();
      return;
    }
    void send();
  };

  return (
    <>
      <div
        data-composer-root
        className="flex flex-col flex-1 w-full py-[var(--composer-pad-y,12px)]"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <div
          data-testid="composer-content-plane"
          className="flex min-h-0 flex-1 flex-col gap-3 px-[var(--composer-pad-x,12px)]"
        >
          <Textarea
            ref={ref}
            rows={MIN_COMPOSER_ROWS}
            value={value}
            onChange={(e) => {
              const next = e.target.value;
              setValue(next);
              valueRef.current = next;
              scheduleDraftCommit(next);
            }}
            onBlur={() => commitDraftNow(valueRef.current)}
            placeholder="Write a message…"
            onPaste={onPaste}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAttemptSend();
              }
            }}
            className="w-full resize-none border-0 bg-transparent text-base leading-relaxed focus-visible:ring-0 focus-visible:outline-none shadow-none placeholder:text-white/20"
            style={{
              color: "var(--text)",
              overflow: "hidden",
              padding: `${COMPOSER_TEXTAREA_PAD_Y} ${COMPOSER_TEXTAREA_PAD_X}`,
            }}
          />

          {draftAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2">
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

          <div
            data-testid="composer-control-row"
            className={cn(
              CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
              CHAT_COMPOSER_SEND_EDGE_INSET_CLASS,
              "mt-auto flex w-full items-center gap-3 px-[var(--composer-text-pad-x,14px)] pb-[6px]"
            )}
          >
            <div
              data-testid="composer-controls-strip"
              className="flex min-w-0 flex-1 flex-nowrap items-center gap-3 overflow-x-auto"
            >
              <ComposerActionMenu
                disabled={draftControlsDisabled}
                depthMode={depthMode}
                depthOptions={depthOptions}
                onAttach={() => {
                  if (draftControlsDisabled) {
                    notifyTransportBusy();
                    return;
                  }
                  fileInputRef.current?.click();
                }}
                onGenerateImage={() => {
                  if (draftControlsDisabled) {
                    notifyTransportBusy();
                    return;
                  }
                  setShowImgGen(true);
                }}
                onDepthChange={(nextDepth) => {
                  onDepthModeChange?.(nextDepth);
                }}
                onVoiceTurn={onVoiceTurn}
                voiceTurnDisabled={voiceTurnDisabled}
                voiceTurnLabel={voiceTurnLabel}
              />
              <ComposerSelectMenu
                ariaLabel="Select provider"
                menuLabel="Provider"
                valueLabel={providerLabel}
                options={providerOptions}
                selectedValue={activeProviderId}
                openSignal={providerOpenSignal}
                disabled={draftControlsDisabled || providerOptions.length === 0}
                onSelect={onProviderChange ?? (() => {})}
              />
              <ComposerSelectMenu
                ariaLabel="Select model"
                menuLabel="Model"
                valueLabel={modelLabel}
                options={modelOptions}
                selectedValue={activeModelId}
                disabled={draftControlsDisabled || modelOptions.length === 0}
                onSelect={onModelChange ?? (() => {})}
              />
              <ComposerSelectMenu
                ariaLabel="Select inference mode"
                menuLabel="Mode"
                valueLabel={inferenceModeLabel}
                options={inferenceModeOptions}
                selectedValue={activeInferenceMode}
                disabled={draftControlsDisabled || inferenceModeOptions.length === 0}
                onSelect={(value) =>
                  onInferenceModeChange?.(value as ComposerInferenceMode)
                }
              />
              <ComposerSelectMenu
                ariaLabel="Select retrieval source"
                menuLabel="Source"
                valueLabel={`Source: ${sourceLabel}`}
                options={sourceOptions}
                selectedValue={sourceMode}
                disabled={draftControlsDisabled || sourceOptions.length === 0}
                onSelect={(value) => onSourceModeChange?.(value as SourceMode)}
              />
            </div>

            <div
              data-testid="composer-send-slot"
              className="flex shrink-0 items-center justify-center"
            >
              <Button
                type="button"
                onClick={handleAttemptSend}
                disabled={sendTransportDisabled}
                aria-label="Send"
                aria-disabled={sendTransportDisabled || sendBlockedByTurnLock}
                tabIndex={sendTransportDisabled ? -1 : 0}
                title={
                  sendBlockedByTurnLock
                    ? "Finish the current reply before sending."
                    : undefined
                }
                size="icon"
                className={cn(
                  "h-8 w-8 min-w-0 rounded-full p-0 transition-opacity",
                  sendTransportDisabled
                    ? "cursor-not-allowed opacity-50"
                    : sendBlockedByTurnLock
                      ? "opacity-75"
                    : ""
                )}
                style={{
                  background: "color-mix(in oklab, var(--accent-strong) 82%, white 18%)",
                  color: "var(--text-on-accent, #111827)",
                  boxShadow: "none",
                }}
              >
                <Send className="h-3.5 w-3.5 shrink-0" />
              </Button>
            </div>
          </div>
          {imageCapabilityMessage ? (
            <div className="pb-[6px] text-[11px] leading-snug" style={{ color: "var(--muted)" }}>
              {imageCapabilityMessage}
            </div>
          ) : null}
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
