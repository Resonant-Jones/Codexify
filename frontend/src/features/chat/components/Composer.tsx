/**
 * Composer.tsx
 *
 * Renders the chat composer input and controls, including turn-based gating
 * to prevent overlapping user sends while an assistant reply is in flight.
 */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { BookOpen, Send, X, FileText } from "lucide-react";
import { UploadedAttachment, toAbsoluteMediaUrl } from "@/hooks/useUploader";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { ComposerActionMenu } from "@/features/chat/components/ComposerActionMenu";
import { MobileComposerProjection } from "@/features/chat/components/MobileComposerProjection";
import ComposerSelectMenu, {
  type ComposerSelectOption,
} from "@/features/chat/components/ComposerSelectMenu";
import {
  DEFAULT_COMPOSER_INFERENCE_MODE,
  type ComposerInferenceMode,
} from "@/types/inference";
import {
  buildSlashCommandSendPayload,
  resolveSlashCommandIntent,
  type SlashCommandIntentPayload,
} from "@/contracts/slashCommands";
import {
  CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
  CHAT_COMPOSER_SEND_EDGE_INSET_CLASS,
  CHAT_COMPOSER_SEND_SLOT_BALANCE_CLASS,
} from "@/features/chat/chatLane";
import {
  markInlineCommandExecuted,
  parseInlineCommandDraft,
  type InlineCommandDefinition,
  type InlineCommandName,
  type InlineCommandOption,
  type InlineCommandOptionSets,
} from "@/features/chat/inlineCommands";
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
const MIN_COMPOSER_ROWS_MOBILE = 1;
const MAX_COMPOSER_ROWS_MOBILE = 4;
const FALLBACK_LINE_HEIGHT_PX = 24;
const GENERIC_UPLOAD_ERROR_MESSAGE = "Upload failed. Please try again.";
const COMPOSER_TEXTAREA_PAD_X = "var(--composer-text-pad-x, 14px)";
const COMPOSER_TEXTAREA_PAD_Y = "var(--composer-text-pad-y, 10px)";

const parsePx = (value?: string | null) => {
  const parsed = Number.parseFloat(value ?? "");
  return Number.isFinite(parsed) ? parsed : 0;
};

const measureComposerHeights = (
  el: HTMLTextAreaElement,
  minimumRows = MIN_COMPOSER_ROWS,
  maximumRows = MAX_COMPOSER_ROWS
) => {
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
    minHeight: lineHeight * minimumRows + paddingBlock + borderBlock,
    maxHeight: lineHeight * maximumRows + paddingBlock + borderBlock,
  } as const;
};

const autosizeComposerTextarea = (
  el: HTMLTextAreaElement,
  minimumRows = MIN_COMPOSER_ROWS,
  maximumRows = MAX_COMPOSER_ROWS
) => {
  const { minHeight, maxHeight } = measureComposerHeights(el, minimumRows, maximumRows);
  el.style.minHeight = `${minHeight}px`;
  el.style.maxHeight = `${maxHeight}px`;
  el.style.height = "auto";
  const nextHeight = Math.min(el.scrollHeight, maxHeight);
  el.style.height = `${nextHeight}px`;
  el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
};

export type ComposerSendOptions = {
  threadIdOverride?: number;
  slashIntent?: SlashCommandIntentPayload;
};

type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";

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
  depthMode = "normal",
  depthOptions = [],
  onDepthModeChange,
  onVoiceTurn,
  voiceTurnLabel = "Upload voice turn",
  sourceMode = "project",
  sourceOptions = [],
  onSourceModeChange,
  projectName,
  projectOptions = [],
  onProjectChange,
  mobileProjectionEnabled = false,
  projectionSuspended = false,
  onMobileProjectionChange,
  mobileModelId,
  mobileModelLabel,
  mobileModelOptions = [],
  onMobileModelChange,
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
  /** Mobile model selection props for the action menu */
  mobileModelId?: string;
  mobileModelLabel?: string;
  mobileModelOptions?: ComposerSelectOption[];
  onMobileModelChange?: (modelId: string) => void;
  activeInferenceMode?: ComposerInferenceMode;
  inferenceModeOptions?: ComposerSelectOption[];
  onInferenceModeChange?: (mode: ComposerInferenceMode) => void;
  depthMode?: DepthMode;
  depthOptions?: Array<{
    value: DepthMode;
    label: string;
    description: string;
  }>;
  onDepthModeChange?: (mode: DepthMode) => void;
  onVoiceTurn?: () => void;
  voiceTurnLabel?: string;
  sourceMode?: string;
  sourceOptions?: ComposerSelectOption[];
  onSourceModeChange?: (mode: string) => void;
  projectId?: number | string | null;
  projectName?: string | null;
  projectOptions?: ComposerSelectOption[];
  onProjectChange?: (projectId: string) => void;
  documentTiles?: unknown[];
  onDocumentTileRemove?: (tile: unknown) => void;
  currentRequestState?: unknown;
  providerRuntimeState?: unknown;
  onCatalogRefresh?: () => void;
  mobileProjectionEnabled?: boolean;
  projectionSuspended?: boolean;
  onMobileProjectionChange?: (projected: boolean) => void;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const [isComposerFocused, setIsComposerFocused] = useState(false);
  const [dismissedCommandDraft, setDismissedCommandDraft] = useState<
    string | null
  >(null);
  const [activeCommandOptionIndex, setActiveCommandOptionIndex] = useState(0);
  const [commandAnnouncement, setCommandAnnouncement] = useState("");
  const isMobileComposerProjected =
    mobileProjectionEnabled && isComposerFocused && !projectionSuspended;
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
  const [obsidianSlashActive, setObsidianSlashActive] = useState(false);
  const hasDraftContent = Boolean(value.trim()) || draftAttachments.length > 0;
  const sendTransportDisabled = transportBusy || !hasDraftContent;

  useEffect(() => {
    onMobileProjectionChange?.(isMobileComposerProjected);
  }, [isMobileComposerProjected, onMobileProjectionChange]);

  useEffect(() => {
    if (!mobileProjectionEnabled || !projectionSuspended) return;
    if (ref.current === document.activeElement) {
      ref.current.blur();
    }
    setIsComposerFocused(false);
  }, [mobileProjectionEnabled, projectionSuspended]);
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
    autosizeComposerTextarea(
      ref.current,
      mobileProjectionEnabled ? MIN_COMPOSER_ROWS_MOBILE : MIN_COMPOSER_ROWS,
      mobileProjectionEnabled ? MAX_COMPOSER_ROWS_MOBILE : MAX_COMPOSER_ROWS
    );
  }, [mobileProjectionEnabled, value]);

  // Re-focus the textarea when projection activates (it moves to a portal)
  useEffect(() => {
    if (isMobileComposerProjected && ref.current) {
      ref.current.focus({ preventScroll: true });
    }
  }, [isMobileComposerProjected]);

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

  const isObsidianSlashCommand = (rawValue: string) =>
    resolveSlashCommandIntent(rawValue)?.command.id === "obsidian";

  const resolveProjectId = () => {
    // Prefer explicit storage values to reduce reliance on URL shape.
    const fromStorage = inferProjectIdFromStorage();
    if (fromStorage !== null) return fromStorage;
    return inferProjectIdFromLocation(null);
  };

  function stageFiles(files: readonly File[]) {
    if (!files.length) return;
    if (draftControlsDisabled) {
      notifyTransportBusy();
      return;
    }

    setDraftAttachments((prev) => {
      const next = [...prev];
      for (const file of files) {
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
      const res = await api.post(endpoint, form);
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
    const files = Array.from(e.clipboardData?.files ?? []);
    if (files.length > 0) {
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

    const { messageText, slashIntent } = buildSlashCommandSendPayload(value);
    const bodyText = messageText.trim();
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
        ...(slashIntent ? { slashIntent } : {}),
      });

      // Clear the draft after a successful send.
      setValue("");
      valueRef.current = "";
      commitDraftNow("");
      ref.current?.blur();
      setIsComposerFocused(false);
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
    const files = Array.from(e.dataTransfer?.files ?? []);
    if (files.length) {
      stageFiles(files);
    }
  };
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const selectedProviderLabel =
    providerOptions.find((option) => option.value === activeProviderId)?.label ??
    null;
  const selectedModelLabel =
    modelOptions.find((option) => option.value === activeModelId)?.label ?? null;
  const providerLabel =
    selectedProviderLabel ?? providerOptions[0]?.label ?? "Provider";
  const modelLabel = selectedModelLabel ?? modelOptions[0]?.label ?? "Model";
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
  const handleAttemptSend = () => {
    if (turnLocked) {
      notifyTurnLocked();
      return;
    }
    void send();
  };
  const sourceLabel =
    sourceOptions.find((option) => option.value === sourceMode)?.label ??
    (sourceMode === "personal_knowledge" ? "Personal Knowledge" : "Project");
  const toInlineOptions = (
    options: readonly ComposerSelectOption[]
  ): readonly InlineCommandOption[] =>
    options.map((option) => ({
      value: option.value,
      label: option.label,
      description: option.description,
      disabled: option.disabled,
      disabledReason: option.disabled ? option.description : undefined,
    }));
  const inlineCommandOptionSets = useMemo<InlineCommandOptionSets>(
    () => ({
      ...(onProjectChange && projectOptions.length > 0
        ? { project: toInlineOptions(projectOptions) }
        : {}),
      ...(onProviderChange && providerOptions.length > 0
        ? { provider: toInlineOptions(providerOptions) }
        : {}),
      ...(onModelChange && modelOptions.length > 0
        ? { model: toInlineOptions(modelOptions) }
        : {}),
      ...(onInferenceModeChange && inferenceModeOptions.length > 0
        ? { mode: toInlineOptions(inferenceModeOptions) }
        : {}),
      ...(onSourceModeChange && sourceOptions.length > 0
        ? { retrieval: toInlineOptions(sourceOptions) }
        : {}),
    }),
    [
      inferenceModeOptions,
      modelOptions,
      onInferenceModeChange,
      onModelChange,
      onProjectChange,
      onProviderChange,
      onSourceModeChange,
      projectOptions,
      providerOptions,
      sourceOptions,
    ]
  );
  const inlineCommandResult = useMemo(
    () => parseInlineCommandDraft(value, inlineCommandOptionSets),
    [inlineCommandOptionSets, value]
  );
  const commandPaletteOpen =
    mobileProjectionEnabled &&
    isComposerFocused &&
    !projectionSuspended &&
    dismissedCommandDraft !== value &&
    inlineCommandResult.state !== "unknown" &&
    inlineCommandResult.state !== "executed";
  const commandSuggestions = commandPaletteOpen
    ? inlineCommandResult.suggestions
    : [];
  const commandPaletteMode =
    inlineCommandResult.command == null ? "command" : "value";
  const lineageLabel = projectName?.trim()
    ? `Send a message to ${projectName.trim()}`
    : "Send a message";

  useEffect(() => {
    setActiveCommandOptionIndex(0);
  }, [value, commandSuggestions.length]);

  const updateDraftValue = (next: string) => {
    setValue(next);
    valueRef.current = next;
    setDismissedCommandDraft(null);
    setObsidianSlashActive(isObsidianSlashCommand(next.trimStart()));
    scheduleDraftCommit(next);
  };

  const executeInlineCommandOption = (
    command: InlineCommandDefinition,
    option: InlineCommandOption
  ) => {
    if (option.disabled) return;
    const handlers: Partial<Record<InlineCommandName, (next: string) => void>> = {
      project: onProjectChange,
      provider: onProviderChange,
      model: onModelChange,
      mode: (next) =>
        onInferenceModeChange?.(next as ComposerInferenceMode),
      retrieval: onSourceModeChange,
    };
    const handler = handlers[command.name];
    if (!handler) return;

    handler(option.value);
    const readyResult = parseInlineCommandDraft(
      `/${command.name} ${option.value}`,
      inlineCommandOptionSets
    );
    const confirmation =
      readyResult.state === "ready"
        ? markInlineCommandExecuted(readyResult).confirmation
        : `${command.label} set to ${option.label}`;
    setCommandAnnouncement(confirmation);
    updateDraftValue("");
    ref.current?.focus({ preventScroll: true });
  };

  const activateCommandSuggestion = (index: number) => {
    const suggestion = commandSuggestions[index];
    if (!suggestion) return;
    if ("name" in suggestion) {
      updateDraftValue(`/${suggestion.name} `);
      ref.current?.focus({ preventScroll: true });
      return;
    }
    if (inlineCommandResult.command) {
      executeInlineCommandOption(inlineCommandResult.command, suggestion);
    }
  };

  const handleComposerKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (commandPaletteOpen) {
      if (event.key === "Escape") {
        event.preventDefault();
        setDismissedCommandDraft(value);
        return;
      }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const direction = event.key === "ArrowDown" ? 1 : -1;
        const next =
          (activeCommandOptionIndex + direction + commandSuggestions.length) %
          commandSuggestions.length;
        setActiveCommandOptionIndex(next);
        return;
      }
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        if (inlineCommandResult.state === "ambiguous") return;
        activateCommandSuggestion(activeCommandOptionIndex);
        return;
      }
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAttemptSend();
    }
  };

  const renderComposerTextarea = () => (
    <Textarea
      data-testid="composer-textarea"
      ref={ref}
      rows={mobileProjectionEnabled ? MIN_COMPOSER_ROWS_MOBILE : MIN_COMPOSER_ROWS}
      value={value}
      onChange={(event) => {
        updateDraftValue(event.target.value);
      }}
      onFocus={() => setIsComposerFocused(true)}
      onBlur={() => {
        setIsComposerFocused(false);
        commitDraftNow(valueRef.current);
      }}
      placeholder="Write a message…"
      onPaste={onPaste}
      onKeyDown={handleComposerKeyDown}
      aria-controls={
        commandPaletteOpen ? "composer-inline-command-listbox" : undefined
      }
      aria-expanded={commandPaletteOpen}
      aria-activedescendant={
        commandPaletteOpen && commandSuggestions.length > 0
          ? `composer-inline-option-${activeCommandOptionIndex}`
          : undefined
      }
      className="min-w-0 flex-1 resize-none border-0 bg-transparent text-base leading-relaxed focus-visible:ring-0 focus-visible:outline-none shadow-none placeholder:text-white/20"
      style={{
        color: "var(--text)",
        overflow: "hidden",
        padding: `${COMPOSER_TEXTAREA_PAD_Y} ${COMPOSER_TEXTAREA_PAD_X}`,
        ...(mobileProjectionEnabled
          ? { fontSize: "var(--guardian-composer-mobile-input-size)" }
          : {}),
      }}
    />
  );

  const renderComposerActionMenu = () => (
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
      showModelMenu={mobileProjectionEnabled}
      modelId={mobileModelId}
      modelLabel={mobileModelLabel}
      modelOptions={mobileModelOptions}
      onModelChange={(nextId) => onMobileModelChange?.(nextId)}
    />
  );

  const renderSendButton = () => (
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
        color: "var(--text-on-accent, var(--panel-bg))",
        boxShadow: "none",
      }}
    >
      <Send className="h-3.5 w-3.5 shrink-0" />
    </Button>
  );

  return (
    <>
      {/* Status announcement — rendered outside inert/portal regions for accessibility */}
      <div className="sr-only" aria-live="polite" role="status">
        {commandAnnouncement}
      </div>

      {/* Base composer surface — always in DOM for layout, inert when projected */}
      <div
        data-composer-root
        data-composer-surface="base"
        data-mobile-projected={isMobileComposerProjected ? "true" : "false"}
        data-mobile-compact={mobileProjectionEnabled ? "true" : "false"}
        className={cn(
          "flex w-full flex-col",
          mobileProjectionEnabled
            ? "flex-none py-[var(--guardian-composer-compact-gap)]"
            : "flex-1 py-[var(--composer-pad-y,12px)]"
        )}
        {...(isMobileComposerProjected ? { inert: true as any, "aria-hidden": true as any } : {})}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <div
          data-testid="composer-content-plane"
          className={cn(
            "flex min-h-0 flex-1 flex-col justify-end px-[var(--composer-pad-x,12px)]",
            mobileProjectionEnabled
              ? "gap-[var(--guardian-composer-compact-gap)]"
              : "gap-2"
          )}
        >
          {commandPaletteOpen && !isMobileComposerProjected ? (
            <div
              data-testid="composer-command-palette"
              data-command-mode={commandPaletteMode}
              className="min-w-0 overflow-hidden rounded-[var(--radius-micro)] border bg-[var(--panel-bg)]"
              style={{ borderColor: "var(--panel-border)" }}
            >
              <div
                className="border-b px-[var(--card-pad)] py-[var(--guardian-composer-compact-gap)] text-xs font-medium"
                style={{
                  borderColor: "var(--panel-border)",
                  color: "var(--muted)",
                }}
              >
                {commandPaletteMode === "command"
                  ? "Composer commands"
                  : `/${inlineCommandResult.command?.name} values`}
              </div>
              <div
                id="composer-inline-command-listbox"
                role="listbox"
                aria-label={
                  commandPaletteMode === "command"
                    ? "Composer commands"
                    : `${inlineCommandResult.command?.label} values`
                }
                className="overflow-y-auto p-[var(--guardian-composer-compact-gap)]"
                style={{
                  maxHeight:
                    "var(--guardian-composer-command-palette-max-height)",
                }}
              >
                {commandSuggestions.map((suggestion, index) => {
                  const isCommand = "name" in suggestion;
                  const disabled = !isCommand && suggestion.disabled;
                  const optionId = `composer-inline-option-${index}`;
                  return (
                    <button
                      key={
                        isCommand
                          ? suggestion.name
                          : `${inlineCommandResult.command?.name}-${suggestion.value}`
                      }
                      id={optionId}
                      type="button"
                      role="option"
                      aria-selected={index === activeCommandOptionIndex}
                      aria-disabled={disabled || undefined}
                      disabled={disabled}
                      className="flex w-full min-w-0 items-start gap-[var(--guardian-composer-compact-gap)] rounded-[var(--radius-micro)] px-[var(--card-pad)] py-[var(--guardian-composer-compact-gap)] text-left disabled:opacity-50"
                      style={{
                        color: "var(--text)",
                        background:
                          index === activeCommandOptionIndex
                            ? "var(--chip-bg)"
                            : "transparent",
                      }}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setActiveCommandOptionIndex(index)}
                      onClick={() => activateCommandSuggestion(index)}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">
                          {isCommand
                            ? `/${suggestion.name}`
                            : suggestion.label}
                        </span>
                        {suggestion.description ? (
                          <span
                            className="block truncate text-xs"
                            style={{ color: "var(--muted)" }}
                          >
                            {suggestion.description}
                          </span>
                        ) : null}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
          {!mobileProjectionEnabled ? renderComposerTextarea() : null}

          {!mobileProjectionEnabled &&
          !value.trim() &&
          !draftAttachments.length ? (
            <div
              data-testid="composer-lineage-copy"
              className="px-[var(--composer-text-pad-x,14px)] text-[11px] leading-snug"
              style={{ color: "var(--muted)" }}
            >
              {lineageLabel}
            </div>
          ) : null}

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
            style={{ position: "fixed", left: "-9999px", width: "1px", height: "1px", opacity: 0 }}
            onChange={(e) => {
              const files = Array.from(e.currentTarget.files ?? []);
              e.currentTarget.value = "";
              stageFiles(files);
            }}
          />

          {mobileProjectionEnabled ? (
            <div
              data-testid="composer-control-row"
              className={cn(
                CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
                "flex w-full min-w-0 items-center gap-[var(--guardian-composer-compact-gap)] px-[var(--composer-text-pad-x,14px)]"
              )}
            >
              <div
                data-testid="composer-controls-strip"
                className="flex shrink-0 items-center"
              >
                {renderComposerActionMenu()}
              </div>
              {/* In projected mode, render a layout placeholder instead of the textarea */}
              {isMobileComposerProjected ? (
                <div
                  className="min-w-0 flex-1"
                  style={{
                    minHeight: "2.5rem",
                    color: "var(--muted)",
                    fontSize: "var(--guardian-composer-mobile-input-size, 16px)",
                    lineHeight: "1.5",
                    padding: `${COMPOSER_TEXTAREA_PAD_Y} ${COMPOSER_TEXTAREA_PAD_X}`,
                  }}
                  aria-hidden
                >
                  <span className="block truncate">
                    {value.trim() || "Write a message…"}
                  </span>
                </div>
              ) : (
                renderComposerTextarea()
              )}
              <div
                data-testid="composer-send-slot"
                className={cn(
                  "flex shrink-0 items-center justify-center justify-self-end",
                  "mr-[var(--composer-text-pad-x,14px)]",
                  CHAT_COMPOSER_SEND_SLOT_BALANCE_CLASS
                )}
              >
                {renderSendButton()}
              </div>
            </div>
          ) : (
            <div
              data-testid="composer-control-row"
              className={cn(
                CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
                CHAT_COMPOSER_SEND_EDGE_INSET_CLASS,
                "grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-[var(--composer-text-pad-x,14px)]"
              )}
            >
              <div
                data-testid="composer-controls-strip"
                className="flex min-w-0 flex-1 flex-nowrap items-center gap-3 overflow-x-auto"
              >
                {renderComposerActionMenu()}
                {obsidianSlashActive ? (
                  <div
                    data-testid="composer-obsidian-action"
                    className="inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-none border-0 bg-transparent px-1 text-[11px]"
                    style={{ color: "var(--text)" }}
                    title="Obsidian context will be queried for this turn"
                  >
                    <BookOpen className="h-3.5 w-3.5" />
                    <span>Obsidian</span>
                  </div>
                ) : null}
                {sourceOptions.length > 0 ? (
                  <ComposerSelectMenu
                    ariaLabel="Select retrieval source"
                    menuLabel="Source"
                    valueLabel={sourceLabel}
                    options={sourceOptions}
                    selectedValue={sourceMode}
                    disabled={draftControlsDisabled}
                    onSelect={(value) => onSourceModeChange?.(value)}
                  />
                ) : null}
                <ComposerSelectMenu
                  ariaLabel="Select provider"
                  menuLabel="Provider"
                  valueLabel={providerLabel}
                  options={providerOptions}
                  selectedValue={activeProviderId}
                  openSignal={providerOpenSignal}
                  disabled={
                    draftControlsDisabled || providerOptions.length === 0
                  }
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
                  disabled={
                    draftControlsDisabled ||
                    inferenceModeOptions.length === 0
                  }
                  onSelect={(nextMode) =>
                    onInferenceModeChange?.(
                      nextMode as ComposerInferenceMode
                    )
                  }
                />
              </div>

              <div
                data-testid="composer-send-slot"
                className={cn(
                  "flex shrink-0 items-center justify-center",
                  "justify-self-end",
                  CHAT_COMPOSER_SEND_SLOT_BALANCE_CLASS
                )}
              >
                {renderSendButton()}
              </div>
            </div>
          )}
          {imageCapabilityMessage ? (
            <div className="pb-[6px] text-[11px] leading-snug" style={{ color: "var(--muted)" }}>
              {imageCapabilityMessage}
            </div>
          ) : null}
        </div>
      </div>

      {/* Projection surface — portal'd to document.body when active */}
      {isMobileComposerProjected && (
        <MobileComposerProjection visible>
          <div className="flex flex-col gap-[var(--guardian-composer-compact-gap)]">
            {/* Command palette is rendered inside the portal when projected */}
            {commandPaletteOpen ? (
              <div
                data-testid="composer-command-palette"
                data-command-mode={commandPaletteMode}
                className="min-w-0 overflow-hidden rounded-[var(--radius-micro)] border bg-[var(--panel-bg)]"
                style={{ borderColor: "var(--panel-border)" }}
              >
                <div
                  className="border-b px-[var(--card-pad)] py-[var(--guardian-composer-compact-gap)] text-xs font-medium"
                  style={{
                    borderColor: "var(--panel-border)",
                    color: "var(--muted)",
                  }}
                >
                  {commandPaletteMode === "command"
                    ? "Composer commands"
                    : `/${inlineCommandResult.command?.name} values`}
                </div>
                <div
                  id="composer-inline-command-listbox"
                  role="listbox"
                  aria-label={
                    commandPaletteMode === "command"
                      ? "Composer commands"
                      : `${inlineCommandResult.command?.label} values`
                  }
                  className="overflow-y-auto p-[var(--guardian-composer-compact-gap)]"
                  style={{
                    maxHeight:
                      "var(--guardian-composer-command-palette-max-height)",
                  }}
                >
                  {commandSuggestions.map((suggestion, index) => {
                    const isCommand = "name" in suggestion;
                    const disabled = !isCommand && suggestion.disabled;
                    const optionId = `composer-inline-option-${index}`;
                    return (
                      <button
                        key={
                          isCommand
                            ? suggestion.name
                            : `${inlineCommandResult.command?.name}-${suggestion.value}`
                        }
                        id={optionId}
                        type="button"
                        role="option"
                        aria-selected={index === activeCommandOptionIndex}
                        aria-disabled={disabled || undefined}
                        disabled={disabled}
                        className="flex w-full min-w-0 items-start gap-[var(--guardian-composer-compact-gap)] rounded-[var(--radius-micro)] px-[var(--card-pad)] py-[var(--guardian-composer-compact-gap)] text-left disabled:opacity-50"
                        style={{
                          color: "var(--text)",
                          background:
                            index === activeCommandOptionIndex
                              ? "var(--chip-bg)"
                              : "transparent",
                        }}
                        onMouseDown={(event) => event.preventDefault()}
                        onMouseEnter={() => setActiveCommandOptionIndex(index)}
                        onClick={() => activateCommandSuggestion(index)}
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">
                            {isCommand
                              ? `/${suggestion.name}`
                              : suggestion.label}
                          </span>
                          {suggestion.description ? (
                            <span
                              className="block truncate text-xs"
                              style={{ color: "var(--muted)" }}
                            >
                              {suggestion.description}
                            </span>
                          ) : null}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : null}
            <div
              data-testid="composer-control-row"
              className={cn(
                CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
                "flex w-full min-w-0 items-center gap-[var(--guardian-composer-compact-gap)]"
              )}
              style={{
                background: "color-mix(in oklab, var(--panel-bg) 95%, black)",
                borderRadius: "24px",
                border: "1px solid var(--panel-border)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
                backdropFilter: "blur(18px)",
                padding: "0 calc(var(--guardian-composer-compact-gap, 6px) * 1)",
                WebkitBackdropFilter: "blur(18px)",
              }}
            >
              <div
                data-testid="composer-controls-strip"
                className="flex shrink-0 items-center"
              >
                {renderComposerActionMenu()}
              </div>
              {renderComposerTextarea()}
              <div
                data-testid="composer-send-slot"
                className={cn(
                  "flex shrink-0 items-center justify-center justify-self-end",
                  "mr-[var(--composer-text-pad-x,14px)]",
                  CHAT_COMPOSER_SEND_SLOT_BALANCE_CLASS
                )}
              >
                {renderSendButton()}
              </div>
            </div>
          </div>
        </MobileComposerProjection>
      )}

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
