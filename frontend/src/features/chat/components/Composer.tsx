/**
 * Composer.tsx
 *
 * Renders the chat composer input and controls while deriving interaction
 * state from the runtime request contract instead of local loading guesses.
 */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, X, FileText } from "lucide-react";
import { UploadedAttachment, toAbsoluteMediaUrl } from "@/hooks/useUploader";
import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { useMobileShellProfile } from "@/components/persona/layout/mobileShellProfile";
import { getMobileTapTargetStyle } from "@/components/persona/layout/mobileInteractionContract";
import { ComposerActionMenu } from "@/features/chat/components/ComposerActionMenu";
import ComposerSelectMenu, {
  type ComposerSelectOption,
} from "@/features/chat/components/ComposerSelectMenu";
import DocumentContextTileView from "@/features/chat/components/DocumentContextTile";
import {
  SLASH_COMMANDS,
  type SlashCommandDefinition,
  type SlashCommandId,
  type SlashCommandIntentPayload,
  buildSlashCommandIntentPayload,
  resolveSlashCommandIntent,
} from "@/contracts/slashCommands";
import {
  CHAT_REQUEST_STATES,
  type ChatRequestState,
  type ProviderRuntimeState,
} from "@/contracts/runtimeTokens";
import {
  DEFAULT_COMPOSER_INFERENCE_MODE,
  type ComposerInferenceMode,
} from "@/types/inference";
import type { DocumentContextTile } from "@/lib/documentContext";
import {
  CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
} from "@/features/chat/chatLane";
import { usePressFeedback } from "@/hooks/usePressFeedback";
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
const SLASH_COMMAND_TOKEN_SPLIT_RE = /\s/;

function normalizeSlashCommandQuery(query: string) {
  return query.replace(/^\/+/, "").trim().toLowerCase().replace(/\s+/g, " ");
}

function fuzzySlashMatchScore(query: string, candidate: string) {
  const normalizedCandidate = candidate.toLowerCase().trim().replace(/\s+/g, " ");
  if (!query) return 1000;
  if (normalizedCandidate === query) return 2000;
  if (normalizedCandidate.startsWith(query)) return 1800 - normalizedCandidate.length;

  const containsAt = normalizedCandidate.indexOf(query);
  if (containsAt >= 0) return 1600 - containsAt * 10 - normalizedCandidate.length * 0.1;

  let queryIndex = 0;
  let lastMatchIndex = -1;
  let gapCount = 0;
  for (let candidateIndex = 0; candidateIndex < normalizedCandidate.length; candidateIndex += 1) {
    if (normalizedCandidate[candidateIndex] !== query[queryIndex]) continue;
    if (lastMatchIndex >= 0) {
      gapCount += candidateIndex - lastMatchIndex - 1;
    }
    lastMatchIndex = candidateIndex;
    queryIndex += 1;
    if (queryIndex >= query.length) break;
  }

  if (queryIndex < query.length) return null;
  return 400 - gapCount * 8 - normalizedCandidate.length * 0.1;
}

function rankSlashCommands(
  query: string | readonly string[],
  commands: readonly SlashCommandDefinition[]
) {
  const normalizedQueries = (Array.isArray(query) ? query : [query])
    .map((value) => normalizeSlashCommandQuery(value))
    .filter(Boolean);

  if (normalizedQueries.length === 0) return [...commands];

  return commands
    .map((command, index) => {
      const candidates = [command.label, ...command.aliases, ...command.keywords];
      let bestScore: number | null = null;
      for (const candidate of candidates) {
        for (const normalizedQuery of normalizedQueries) {
          const score = fuzzySlashMatchScore(normalizedQuery, candidate);
          if (score == null) continue;
          if (bestScore == null || score > bestScore) {
            bestScore = score;
          }
        }
      }
      return bestScore == null ? null : { command, index, score: bestScore };
    })
    .filter(
      (entry): entry is { command: SlashCommandDefinition; index: number; score: number } =>
        entry != null
    )
    .sort((left, right) => right.score - left.score || left.index - right.index)
    .map((entry) => entry.command);
}

function extractSlashCommandContext(value: string, caretIndex: number | null) {
  const caret = Math.max(0, Math.min(caretIndex ?? value.length, value.length));
  let start = -1;
  for (let index = caret - 1; index >= 0; index -= 1) {
    if (value[index] !== "/") continue;
    if (index > 0 && !SLASH_COMMAND_TOKEN_SPLIT_RE.test(value[index - 1])) continue;
    start = index;
    break;
  }

  if (start < 0) return null;

  const token = value.slice(start, caret);
  if (!token.startsWith("/")) return null;

  const query = token.slice(1);
  return {
    start,
    end: caret,
    text: token,
    query,
    key: `${start}:${caret}:${token}`,
  } as const;
}

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

export type ComposerInteractionState =
  | "idle"
  | "typing"
  | "submitting"
  | "awaiting_model"
  | "streaming"
  | "disabled";

export function deriveComposerState(
  requestState?: ChatRequestState,
  providerState?: ProviderRuntimeState,
  inputValue?: string
): ComposerInteractionState {
  void providerState;

  if (requestState === CHAT_REQUEST_STATES.STREAMING) return "streaming";
  if (requestState === CHAT_REQUEST_STATES.AWAITING_MODEL) return "awaiting_model";
  if (
    requestState === CHAT_REQUEST_STATES.DISPATCHING ||
    requestState === CHAT_REQUEST_STATES.AWAITING_ACK
  ) {
    return "submitting";
  }

  if (!inputValue || inputValue.trim() === "") return "idle";

  return "typing";
}

export type ComposerSendOptions = {
  threadIdOverride?: number;
  slashIntent?: SlashCommandIntentPayload | null;
};

type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";
type SourceMode = "project" | "personal_knowledge";

type DraftAttachment = {
  id: string;
  kind: "image" | "document";
  file?: File;
  asset?: {
    id?: string;
    src_url: string;
    filename: string;
    project_id?: string | number | null;
    thread_id?: string | number | null;
  };
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
  documentTiles = [],
  onDocumentTileRemove,
  threadId,
  currentRequestState,
  providerRuntimeState,
  isSending = false,
  isTurnInFlight = false,
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
  projectId = null,
  projectName,
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
  documentTiles?: DocumentContextTile[];
  onDocumentTileRemove?: (tileId: string) => void;
  threadId?: number;
  currentRequestState?: ChatRequestState | null;
  providerRuntimeState?: ProviderRuntimeState | null;
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
  projectId?: number | null;
  projectName?: string | null;
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
  const [caretIndex, setCaretIndex] = useState(() => resolveInitialDraft().length);
  const [slashPaletteOpen, setSlashPaletteOpen] = useState(false);
  const [activeSlashCommandId, setActiveSlashCommandId] = useState<SlashCommandId | null>(null);
  const dismissedSlashTokenKeyRef = useRef<string | null>(null);
  const activeSlashToken = useMemo(
    () => extractSlashCommandContext(value, caretIndex),
    [caretIndex, value]
  );
  const activeSlashIntent = useMemo(
    () => (activeSlashToken ? resolveSlashCommandIntent(activeSlashToken.text) : null),
    [activeSlashToken?.text]
  );
  const activeSlashQueries = useMemo(() => {
    if (!activeSlashToken) return [] as string[];

    const queries = [activeSlashToken.query];
    const normalizedQuery = normalizeSlashCommandQuery(activeSlashToken.query);
    if (normalizedQuery) {
      const commandToken = normalizedQuery.split(/\s+/)[0] ?? "";
      if (commandToken && commandToken !== normalizedQuery) {
        queries.push(commandToken);
      }
    }

    if (activeSlashIntent?.queryText) {
      queries.push(activeSlashIntent.queryText);
    }

    return queries;
  }, [activeSlashIntent?.queryText, activeSlashToken?.query]);
  const visibleSlashCommands = useMemo(
    () => rankSlashCommands(activeSlashQueries, SLASH_COMMANDS),
    [activeSlashQueries]
  );

  const [internalSending, setInternalSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const sendInFlightRef = useRef(false);
  const [showImgGen, setShowImgGen] = useState(false);
  const mobileShellProfile = useMobileShellProfile();
  const isPhoneShell = mobileShellProfile.active;

  const [draftAttachments, setDraftAttachments] = useState<DraftAttachment[]>([]);
  const hasDraftContent =
    Boolean(value.trim()) || draftAttachments.length > 0 || documentTiles.length > 0;
  const localSendInProgress = internalSending || uploading;
  const runtimeInteractionState = deriveComposerState(
    currentRequestState ?? undefined,
    providerRuntimeState ?? undefined,
    value
  );
  const interactionState =
    localSendInProgress && runtimeInteractionState === "typing"
      ? "submitting"
      : runtimeInteractionState;
  const inputLocked =
    interactionState === "submitting" || interactionState === "awaiting_model";
  const draftControlsDisabled = localSendInProgress;
  const sendTransportDisabled = !hasDraftContent || inputLocked || localSendInProgress;
  const turnLocked = Boolean(isTurnInFlight);
  const transportBusy = localSendInProgress;
  const sendBlockedByTurnLock = turnLocked && hasDraftContent && !transportBusy;
  const voiceTurnDisabled = inputLocked || localSendInProgress || turnLocked;
  const composerSendButtonLabel =
    interactionState === "awaiting_model"
      ? "Warming…"
      : interactionState === "streaming"
        ? "Streaming…"
        : interactionState === "submitting"
          ? "Sending…"
          : "Send";
  const composerPressFeedback = usePressFeedback({
    enabled: !sendTransportDisabled,
    visualMode: isPhoneShell ? "mobile" : "none",
  });
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

  useEffect(() => {
    if (!activeSlashToken) {
      dismissedSlashTokenKeyRef.current = null;
      setSlashPaletteOpen(false);
      setActiveSlashCommandId(null);
      return;
    }

    if (dismissedSlashTokenKeyRef.current === activeSlashToken.key) {
      setSlashPaletteOpen(false);
      return;
    }

    setSlashPaletteOpen(true);
  }, [activeSlashToken]);

  useEffect(() => {
    if (!slashPaletteOpen || visibleSlashCommands.length === 0) {
      setActiveSlashCommandId(null);
      return;
    }

    setActiveSlashCommandId((current) => {
      if (current && visibleSlashCommands.some((command) => command.id === current)) {
        return current;
      }
      return visibleSlashCommands[0]?.id ?? null;
    });
  }, [slashPaletteOpen, visibleSlashCommands]);

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
    setCaretIndex(initial.length);
    setSlashPaletteOpen(false);
    setActiveSlashCommandId(null);
    dismissedSlashTokenKeyRef.current = null;
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

  const closeSlashPalette = (tokenKey: string | null = activeSlashToken?.key ?? null) => {
    dismissedSlashTokenKeyRef.current = tokenKey;
    setSlashPaletteOpen(false);
    setActiveSlashCommandId(null);
  };

  const applySlashCommand = (command: SlashCommandDefinition) => {
    if (!activeSlashToken) return;

    const nextValue =
      `${value.slice(0, activeSlashToken.start)}` +
      `${command.scaffold}` +
      `${value.slice(activeSlashToken.end)}`;
    const nextCaretIndex = activeSlashToken.start + command.scaffold.length;
    const normalizedNextToken = extractSlashCommandContext(nextValue, nextCaretIndex);

    setValue(nextValue);
    valueRef.current = nextValue;
    setCaretIndex(nextCaretIndex);
    scheduleDraftCommit(nextValue);
    closeSlashPalette(normalizedNextToken?.key ?? null);
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
            item.file != null &&
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

  function stageRemoteAsset(asset: DraftAttachment["asset"]) {
    if (!asset) return;
    setDraftAttachments((prev) => {
      const next = [...prev];
      const duplicate = next.some((item) => {
        if (!item.asset) return false;
        return (
          item.asset.id === asset.id &&
          item.asset.src_url === asset.src_url &&
          item.asset.filename === asset.filename
        );
      });
      if (duplicate) return prev;
      next.push({
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        kind: asset.filename.match(/\.(png|jpe?g|gif|webp|avif)$/i)
          ? "image"
          : "document",
        asset,
        previewUrl: toAbsoluteMediaUrl(asset.src_url),
      });
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
    if (att.asset) {
      return {
        kind: att.kind,
        id: att.asset.id,
        src_url: toAbsoluteMediaUrl(att.asset.src_url),
        filename: att.asset.filename,
      };
    }
    const file = att.file;
    if (!file) return null;

    const endpoint =
      att.kind === "image" ? "/api/media/upload/image" : "/api/media/upload/document";
    const form = new FormData();
    const resolvedProjectId = projectId ?? resolveProjectId();
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
      setCaretIndex(prefill.length);
      commitDraftNow(prefill);
      setTimeout(() => ref.current?.focus(), 0);
      onPrefillConsumed && onPrefillConsumed();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onPrefillConsumed, prefill, value]);
  async function send() {
    if (sendInFlightRef.current) return;
    if (sendTransportDisabled) return;

    const bodyText = value.trim();
    const hasAttachments = draftAttachments.length > 0;
    const hasDocumentTiles = documentTiles.length > 0;
    if (!bodyText && !hasAttachments && !hasDocumentTiles) return;

    const slashIntent = buildSlashCommandIntentPayload(value);

    sendInFlightRef.current = true;
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
      const slashIntent = buildSlashCommandIntentPayload(value);

      if (hasAttachments && !message) {
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
      setCaretIndex(0);
      commitDraftNow("");
      closeSlashPalette(null);
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
      sendInFlightRef.current = false;
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
    const rawAsset = e.dataTransfer?.getData("application/x-cfy-asset");
    if (rawAsset) {
      try {
        const parsed = JSON.parse(rawAsset) as {
          kind?: "image" | "document";
          item?: Record<string, unknown>;
        };
        const item = parsed?.item ?? {};
        const droppedProjectId = Number(item.project_id ?? item.projectId ?? null);
        const droppedThreadId = Number(item.thread_id ?? item.threadId ?? null);
        const assetProjectId = Number.isFinite(droppedProjectId) ? droppedProjectId : null;
        const assetThreadId = Number.isFinite(droppedThreadId) ? droppedThreadId : null;
        const allowed =
          (projectId != null &&
            assetProjectId != null &&
            assetProjectId === projectId) ||
          (threadId != null &&
            assetThreadId != null &&
            assetThreadId === threadId);
        if (!allowed) {
          window.dispatchEvent(
            new CustomEvent("cfy:toast", {
              detail: {
                kind: "error",
                message:
                  "Cross-context file not allowed. Drag the file into composer to include it manually.",
              },
            })
          );
          return;
        }
        const filename = String(item.filename ?? item.name ?? "Untitled").trim();
        const srcUrl = String(item.src_url ?? item.srcUrl ?? item.src ?? item.url ?? "");
        stageRemoteAsset({
          id: item.id != null ? String(item.id) : undefined,
          src_url: srcUrl,
          filename,
          project_id: item.project_id ?? item.projectId ?? null,
          thread_id: item.thread_id ?? item.threadId ?? null,
        });
        return;
      } catch {
        // Fall through to file staging below.
      }
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
  const lineageTargetLabel = projectName?.trim() || "General";
  const activeSlashCommand =
    visibleSlashCommands.find((command) => command.id === activeSlashCommandId) ??
    visibleSlashCommands[0] ??
    null;
  const activeSlashSemanticHint = activeSlashIntent
    ? `intent kind: ${activeSlashIntent.command.effects.intentKind} · retrieval hint: ${activeSlashIntent.command.effects.retrievalHint}`
    : null;
  const showLineageCopy =
    !value.trim() && draftAttachments.length === 0 && documentTiles.length === 0;
  const lineageCopy = `Send a message to ${lineageTargetLabel}`;
  const sendButtonLabel =
    interactionState === "submitting"
      ? "Sending…"
      : interactionState === "streaming"
        ? "Streaming…"
        : interactionState === "awaiting_model"
          ? "Warming…"
          : "Send";
  const handleAttemptSend = () => {
    if (turnLocked) {
      notifyTurnLocked();
      return;
    }
    if (sendTransportDisabled) return;
    void send();
  };
  const composerSendButtonProps = composerPressFeedback.getPressFeedbackProps({
    className: cn(
      "inline-flex items-center justify-center rounded-full border-0 p-0 transition-opacity focus:outline-none disabled:pointer-events-none",
      sendTransportDisabled
        ? "cursor-not-allowed opacity-50"
        : sendBlockedByTurnLock
          ? "opacity-75"
          : "",
      sendTransportDisabled && "opacity-50 cursor-not-allowed",
      interactionState === "typing"
        ? "bg-[var(--accent)] text-[var(--pill-active-text)]"
        : "bg-[var(--panel-bg)] text-[var(--muted)]"
    ),
    style: {
      ...getMobileTapTargetStyle(isPhoneShell, { square: true }),
      width: "var(--composer-control-size, 2rem)",
      height: "var(--composer-control-size, 2rem)",
      background: "color-mix(in oklab, var(--accent-strong) 82%, white 18%)",
      color: "var(--text-on-accent, #111827)",
      boxShadow: "none",
      borderRadius: "9999px",
    },
  });
  const composerSurfaceStyle = useMemo<React.CSSProperties>(
    () =>
      ({
        "--composer-pad-x": mobileShellProfile.chat.composer.padX,
        "--composer-pad-y": mobileShellProfile.chat.composer.padY,
        "--composer-text-pad-x": mobileShellProfile.chat.composer.textPadX,
        "--composer-text-pad-y": mobileShellProfile.chat.composer.textPadY,
        "--composer-control-gap": mobileShellProfile.chat.composer.controlGap,
        "--composer-control-size": mobileShellProfile.chat.composer.controlSize,
        "--composer-safe-area-bottom": mobileShellProfile.chat.composer.bottomSafeArea,
        paddingBottom: "calc(var(--composer-pad-y, 12px) + var(--composer-safe-area-bottom, 0px))",
      }) as React.CSSProperties,
    [mobileShellProfile]
  );

  return (
    <>
      <div
        data-composer-root
        className="flex min-w-0 flex-col flex-1 w-full py-[var(--composer-pad-y,12px)] overflow-x-hidden"
        style={composerSurfaceStyle}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <div
          data-testid="composer-content-plane"
          className="relative flex min-h-0 min-w-0 flex-1 flex-col justify-end gap-2 px-[var(--composer-pad-x,12px)]"
        >
          {showLineageCopy ? (
            <div
              data-testid="composer-lineage-copy"
              className="pointer-events-none absolute left-[var(--composer-text-pad-x,14px)] top-[var(--composer-text-pad-y,10px)] text-base leading-relaxed font-normal tracking-normal text-[var(--text)] opacity-[0.85]"
            >
              {lineageCopy}
            </div>
          ) : null}
          {documentTiles.length > 0 ? (
            <div className="flex flex-wrap gap-2 px-[var(--composer-text-pad-x,14px)]">
              {documentTiles.map((tile) => (
                <DocumentContextTileView
                  key={tile.id}
                  tile={tile}
                  onRemove={
                    onDocumentTileRemove
                      ? () => onDocumentTileRemove(tile.id)
                      : undefined
                  }
                  className="max-w-full"
                />
              ))}
            </div>
          ) : null}
          <textarea
            ref={ref}
            data-testid="composer-textarea"
            rows={MIN_COMPOSER_ROWS}
            wrap="soft"
            value={value}
            disabled={inputLocked}
            onChange={(e) => {
              const next = e.target.value;
              setValue(next);
              valueRef.current = next;
              setCaretIndex(e.currentTarget.selectionStart ?? next.length);
              scheduleDraftCommit(next);
            }}
            onSelect={(e) => {
              setCaretIndex(e.currentTarget.selectionStart ?? e.currentTarget.value.length);
            }}
            onBlur={() => {
              commitDraftNow(valueRef.current);
              if (slashPaletteOpen) {
                closeSlashPalette(activeSlashToken?.key ?? null);
              }
            }}
            onPaste={onPaste}
            onKeyDown={(e) => {
              if (slashPaletteOpen) {
                if (e.key === "Escape") {
                  e.preventDefault();
                  closeSlashPalette(activeSlashToken?.key ?? null);
                  return;
                }

                if (e.key === "ArrowDown" && visibleSlashCommands.length > 0) {
                  e.preventDefault();
                  const currentIndex = visibleSlashCommands.findIndex(
                    (command) => command.id === activeSlashCommandId
                  );
                  const nextIndex =
                    currentIndex < 0
                      ? 0
                      : (currentIndex + 1) % visibleSlashCommands.length;
                  setActiveSlashCommandId(visibleSlashCommands[nextIndex]?.id ?? null);
                  return;
                }

                if (e.key === "ArrowUp" && visibleSlashCommands.length > 0) {
                  e.preventDefault();
                  const currentIndex = visibleSlashCommands.findIndex(
                    (command) => command.id === activeSlashCommandId
                  );
                  const nextIndex =
                    currentIndex < 0
                      ? visibleSlashCommands.length - 1
                      : (currentIndex - 1 + visibleSlashCommands.length) %
                        visibleSlashCommands.length;
                  setActiveSlashCommandId(visibleSlashCommands[nextIndex]?.id ?? null);
                  return;
                }

                if (e.key === "Enter" && !e.shiftKey && visibleSlashCommands.length > 0) {
                  e.preventDefault();
                  const nextCommand = activeSlashCommand ?? visibleSlashCommands[0];
                  if (nextCommand) {
                    applySlashCommand(nextCommand);
                  }
                  return;
                }
              }

              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAttemptSend();
              }
            }}
            aria-label={lineageCopy}
            placeholder=""
            className={cn(
              "w-full bg-transparent border-none outline-none text-[var(--text)] placeholder:text-[var(--muted)] resize-none text-base leading-relaxed",
              interactionState === "awaiting_model" &&
                "opacity-60 cursor-not-allowed"
            )}
            style={{
              overflow: "hidden",
              overflowWrap: "anywhere",
              wordBreak: "break-word",
              padding: `${COMPOSER_TEXTAREA_PAD_Y} ${COMPOSER_TEXTAREA_PAD_X}`,
            }}
          />

          {slashPaletteOpen ? (
            <div
              role="menu"
              aria-label="Slash commands"
              className="overflow-hidden rounded-2xl border px-1 py-1.5"
              style={{
                marginTop: "2px",
                borderColor: "color-mix(in oklab, var(--panel-border) 70%, transparent)",
                background:
                  "color-mix(in oklab, var(--panel-bg) 90%, var(--text) 10%)",
                boxShadow: "0 18px 42px rgba(0, 0, 0, 0.22)",
                backdropFilter: "blur(18px)",
              }}
            >
              <div className="flex items-center justify-between px-2 pb-1 text-[10px] font-medium uppercase tracking-[0.18em]">
                <span style={{ color: "color-mix(in oklab, var(--muted) 82%, transparent)" }}>
                  Slash commands
                </span>
                <span style={{ color: "color-mix(in oklab, var(--muted) 72%, transparent)" }}>
                  {activeSlashToken?.query ? `/${activeSlashToken.query}` : "/"}
                </span>
              </div>
              {activeSlashSemanticHint ? (
                <div
                  className="px-2 pb-2 text-[10px] leading-snug"
                  style={{ color: "color-mix(in oklab, var(--muted) 76%, transparent)" }}
                >
                  {activeSlashSemanticHint}
                </div>
              ) : null}
              <div className="max-h-60 overflow-y-auto">
                {visibleSlashCommands.length > 0 ? (
                  visibleSlashCommands.map((command) => {
                    const isActive = command.id === activeSlashCommand?.id;
                    return (
                      <button
                        key={command.id}
                        type="button"
                        role="menuitem"
                        aria-label={`${command.label} ${command.description}`}
                        aria-current={isActive ? "true" : undefined}
                        onMouseDown={(event) => event.preventDefault()}
                        onMouseEnter={() => setActiveSlashCommandId(command.id)}
                        onClick={() => applySlashCommand(command)}
                        className={cn(
                          "flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left transition-colors",
                          isActive
                            ? "bg-[color-mix(in_oklab,var(--accent)_14%,var(--panel-bg)_86%)]"
                            : "hover:bg-[color-mix(in_oklab,var(--panel-bg)_78%,var(--text)_22%)]"
                        )}
                        style={{
                          color: "var(--text)",
                        }}
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block text-[12px] font-medium leading-snug">
                            {command.label}
                          </span>
                          <span
                            className="mt-0.5 block text-[11px] leading-snug"
                            style={{ color: "var(--muted)" }}
                          >
                            {command.description}
                          </span>
                        </span>
                        <span
                          className="mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em]"
                          style={{
                            color: isActive ? "var(--accent)" : "var(--muted)",
                            background: isActive
                              ? "color-mix(in oklab, var(--accent) 10%, transparent)"
                              : "transparent",
                          }}
                        >
                          /{command.id}
                        </span>
                      </button>
                    );
                  })
                ) : (
                  <div className="px-3 py-3 text-sm" style={{ color: "var(--muted)" }}>
                    No slash commands match this query.
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {draftAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {draftAttachments.map((att) => (
                <div
                  key={att.id}
                  className="relative overflow-hidden rounded-[var(--tile-radius)] border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5"
                  style={{ width: 88, height: 68 }}
                  title={att.file?.name ?? att.asset?.filename ?? "Attachment"}
                >
                  {att.kind === "image" ? (
                    <img
                      src={att.previewUrl}
                      alt={att.file?.name ?? att.asset?.filename ?? "Attachment"}
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
              "flex w-full items-center gap-3 px-[var(--composer-text-pad-x,14px)]"
            )}
            style={{ gap: "var(--composer-control-gap, 12px)" }}
          >
          <div
            data-testid="composer-controls-strip"
            className="flex w-fit max-w-full min-w-0 flex-none flex-nowrap items-center gap-3 overflow-x-auto"
            style={{ gap: "var(--composer-control-gap, 12px)" }}
          >
              <ComposerActionMenu
                disabled={draftControlsDisabled}
                isPhoneShell={isPhoneShell}
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
                isPhoneShell={isPhoneShell}
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
                isPhoneShell={isPhoneShell}
                selectedValue={activeModelId}
                disabled={draftControlsDisabled || modelOptions.length === 0}
                onSelect={onModelChange ?? (() => {})}
              />
              <ComposerSelectMenu
                ariaLabel="Select inference mode"
                menuLabel="Mode"
                valueLabel={inferenceModeLabel}
                options={inferenceModeOptions}
                isPhoneShell={isPhoneShell}
                selectedValue={activeInferenceMode}
                disabled={draftControlsDisabled || inferenceModeOptions.length === 0}
                onSelect={(value) =>
                  onInferenceModeChange?.(value as ComposerInferenceMode)
                }
              />
              <ComposerSelectMenu
                ariaLabel="Select retrieval source"
                menuLabel="Source"
                valueLabel={`${sourceLabel}`}
                options={sourceOptions}
                isPhoneShell={isPhoneShell}
                selectedValue={sourceMode}
                disabled={draftControlsDisabled || sourceOptions.length === 0}
                onSelect={(value) => onSourceModeChange?.(value as SourceMode)}
              />
            </div>

            <div
              data-testid="composer-send-slot"
              className="flex shrink-0 items-center justify-center"
              style={{ marginRight: "6px" }}
            >
              <button
                type="button"
                aria-label={composerSendButtonLabel}
                {...composerPressFeedback.getPressFeedbackProps({
                  className:
                    cn(
                      "rounded-[var(--radius-micro)] px-3 py-2 transition-all",
                      sendTransportDisabled
                        ? "cursor-not-allowed opacity-50"
                        : sendBlockedByTurnLock
                          ? "opacity-75"
                          : "",
                      interactionState === "typing"
                        ? "bg-[var(--accent)] text-[var(--pill-active-text)]"
                        : "bg-[var(--panel-bg)] text-[var(--muted)]"
                    ),
                  style: {
                    ...getMobileTapTargetStyle(isPhoneShell, { square: true }),
                    transform:
                      !isPhoneShell && composerPressFeedback.pressed
                        ? "translateY(1px)"
                        : undefined,
                  },
                })}
                onClick={handleAttemptSend}
                disabled={sendTransportDisabled}
              >
                <span className="sr-only">{sendButtonLabel}</span>
                <ArrowUp size={16} />
              </button>
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
        projectId={projectId ?? resolveProjectId()}
        threadId={threadId ?? null}
      />
    </>
  );
}

export default Composer;
