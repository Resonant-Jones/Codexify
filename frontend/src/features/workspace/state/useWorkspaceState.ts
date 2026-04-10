import { useCallback, useEffect, useState } from "react";

import type { DocumentLike } from "@/types/documents";
import {
  isPhoneShellViewportClass,
  useShellViewportClass,
} from "@/components/persona/layout/shellBreakpointContract";

export const WORKSPACE_OPEN_EVENT = "cfy:workspace:open";
export const LEGACY_DOCUMENT_OPEN_EVENT = "cfy:documents:open";

export type WorkspaceOpenSource =
  | "documents"
  | "guardian-chat"
  | "generated-document";

export type WorkspaceTargetView = "documents" | "guardian";

export type WorkspaceOpenRequest = {
  doc: DocumentLike;
  source: WorkspaceOpenSource;
  targetView: WorkspaceTargetView;
};

type WorkspaceOpenRequestDefaults = Partial<
  Pick<WorkspaceOpenRequest, "source" | "targetView">
>;

type UseWorkspaceStateOptions = {
  normalizeDocument?: (doc: DocumentLike) => DocumentLike;
  onOpenRequest?: (request: WorkspaceOpenRequest) => void;
};

function normalizeString(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function normalizeNumericId(value: unknown): number | undefined {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function normalizeWorkspaceTargetView(
  value: unknown,
  fallback: WorkspaceTargetView
): WorkspaceTargetView {
  if (value === "guardian") {
    return "guardian";
  }
  if (value === "documents") {
    return "documents";
  }
  return fallback;
}

function inferExtension(candidate: Record<string, unknown>): string {
  const direct = normalizeString(
    candidate.ext ?? candidate.extension ?? candidate.format
  );
  if (direct) {
    return direct.replace(/^\./, "").toLowerCase();
  }

  const sources = [
    normalizeString(candidate.filename),
    normalizeString(candidate.name),
    normalizeString(candidate.title),
    normalizeString(candidate.src_url),
    normalizeString(candidate.srcUrl),
    normalizeString(candidate.src),
    normalizeString(candidate.url),
  ];

  for (const source of sources) {
    if (!source) continue;

    try {
      const pathname = new URL(source, "http://workspace.local").pathname;
      const match = pathname.match(/\.([a-z0-9]+)$/i);
      if (match?.[1]) {
        return match[1].toLowerCase();
      }
    } catch {
      const match = source.split(/[?#]/, 1)[0]?.match(/\.([a-z0-9]+)$/i);
      if (match?.[1]) {
        return match[1].toLowerCase();
      }
    }
  }

  return "md";
}

export function toWorkspaceDocument(raw: unknown): DocumentLike | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return null;
  }

  const candidate = raw as Record<string, unknown>;
  const filename = normalizeString(candidate.filename);
  const name = normalizeString(candidate.name) ?? filename;
  const title =
    normalizeString(candidate.title) ??
    name?.replace(/\.[^.]+$/, "") ??
    "Untitled";
  const ext = inferExtension(candidate);
  const srcUrl =
    normalizeString(candidate.src_url) ??
    normalizeString(candidate.srcUrl) ??
    normalizeString(candidate.src) ??
    normalizeString(candidate.url);

  return {
    id:
      normalizeString(candidate.id) ??
      normalizeString(candidate.document_id) ??
      undefined,
    name: name ?? title,
    title,
    ext,
    type: candidate.type === "codex_entry" ? "codex_entry" : "file",
    content:
      normalizeString(candidate.content) ??
      normalizeString(candidate.parsed_text) ??
      normalizeString(candidate.parsedText),
    parsed_text:
      normalizeString(candidate.parsed_text) ??
      normalizeString(candidate.parsedText) ??
      normalizeString(candidate.content),
    parsedText:
      normalizeString(candidate.parsedText) ??
      normalizeString(candidate.parsed_text) ??
      normalizeString(candidate.content),
    src_url: srcUrl,
    srcUrl: normalizeString(candidate.srcUrl),
    src: normalizeString(candidate.src),
    url: normalizeString(candidate.url),
    mime_type:
      normalizeString(candidate.mime_type) ??
      normalizeString(candidate.mimeType) ??
      normalizeString(candidate.content_type),
    mimeType:
      normalizeString(candidate.mimeType) ??
      normalizeString(candidate.mime_type) ??
      normalizeString(candidate.content_type),
    projectId:
      normalizeNumericId(candidate.projectId) ??
      normalizeNumericId(candidate.project_id),
    project_id:
      normalizeNumericId(candidate.project_id) ??
      normalizeNumericId(candidate.projectId),
    threadId:
      normalizeNumericId(candidate.threadId) ??
      normalizeNumericId(candidate.thread_id),
    thread_id:
      normalizeNumericId(candidate.thread_id) ??
      normalizeNumericId(candidate.threadId),
    createdAt:
      normalizeString(candidate.createdAt) ??
      normalizeString(candidate.created_at),
    embeddingStatus:
      normalizeString(candidate.embeddingStatus) ??
      normalizeString(candidate.embedding_status),
    embeddingError:
      normalizeString(candidate.embeddingError) ??
      normalizeString(candidate.embedding_error),
    embeddingStartedAt:
      normalizeString(candidate.embeddingStartedAt) ??
      normalizeString(candidate.embedding_started_at),
    embeddingCompletedAt:
      normalizeString(candidate.embeddingCompletedAt) ??
      normalizeString(candidate.embedding_completed_at),
    mock: Boolean(candidate.mock),
  };
}

export function normalizeWorkspaceOpenRequest(
  raw: unknown,
  defaults: WorkspaceOpenRequestDefaults = {}
): WorkspaceOpenRequest | null {
  const candidate =
    raw && typeof raw === "object" && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : null;
  const doc = toWorkspaceDocument(candidate?.doc ?? raw);
  if (!doc) return null;

  const sourceCandidate = normalizeString(candidate?.source);
  const targetViewCandidate = normalizeString(candidate?.targetView);

  const source: WorkspaceOpenSource =
    sourceCandidate === "guardian-chat" ||
    sourceCandidate === "generated-document"
      ? sourceCandidate
      : "documents";

  const targetView = normalizeWorkspaceTargetView(
    targetViewCandidate,
    defaults.targetView ?? "documents"
  );

  return {
    doc,
    source: defaults.source ?? source,
    targetView,
  };
}

export function shouldBlockNestedWorkspaceShell(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.self !== window.top;
  } catch {
    return true;
  }
}

export function requestWorkspaceOpen(
  raw: unknown,
  defaults: WorkspaceOpenRequestDefaults = {}
): boolean {
  if (typeof window === "undefined" || shouldBlockNestedWorkspaceShell()) {
    return false;
  }

  const request = normalizeWorkspaceOpenRequest(raw, defaults);
  if (!request) return false;

  try {
    window.dispatchEvent(
      new CustomEvent(WORKSPACE_OPEN_EVENT, {
        detail: request,
      })
    );
    return true;
  } catch {
    return false;
  }
}

export function forwardLegacyDocumentOpenToWorkspace(
  raw: unknown,
  defaults: WorkspaceOpenRequestDefaults = {
    source: "guardian-chat",
    targetView: "guardian",
  }
): boolean {
  const candidate =
    raw && typeof raw === "object" && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : null;
  return requestWorkspaceOpen(candidate?.doc ?? raw, defaults);
}

export function useWorkspaceState({
  normalizeDocument,
  onOpenRequest,
}: UseWorkspaceStateOptions = {}) {
  const shellViewportClass = useShellViewportClass();
  const isPhoneShell = isPhoneShellViewportClass(shellViewportClass);
  const [activeDoc, setActiveDoc] = useState<DocumentLike | null>(null);
  const [workspaceOpen, setWorkspaceOpen] = useState(false);

  useEffect(() => {
    if (!isPhoneShell) return;
    setWorkspaceOpen(false);
  }, [isPhoneShell]);

  const openWorkspaceDocument = useCallback(
    (raw: unknown, defaults: WorkspaceOpenRequestDefaults = {}) => {
      if (shouldBlockNestedWorkspaceShell()) {
        setWorkspaceOpen(false);
        setActiveDoc(null);
        return false;
      }

      const request = normalizeWorkspaceOpenRequest(raw, defaults);
      if (!request) return false;

      const nextDoc = normalizeDocument
        ? normalizeDocument(request.doc)
        : request.doc;
      const nextRequest = { ...request, doc: nextDoc };

      setActiveDoc(nextDoc);
      // Phone shells keep Workspace collapsed until the user explicitly summons it.
      setWorkspaceOpen((previous) => {
        if (isPhoneShell) {
          return previous;
        }
        return true;
      });
      onOpenRequest?.(nextRequest);
      return true;
    },
    [isPhoneShell, normalizeDocument, onOpenRequest]
  );

  const closeWorkspace = useCallback(() => {
    setWorkspaceOpen(false);
  }, []);

  const toggleWorkspace = useCallback(() => {
    if (shouldBlockNestedWorkspaceShell()) {
      setWorkspaceOpen(false);
      return;
    }

    setWorkspaceOpen((previous) => !previous);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const onOpen = (event: Event) => {
      const request = normalizeWorkspaceOpenRequest(
        (event as CustomEvent).detail
      );
      if (!request) return;
      openWorkspaceDocument(request.doc, {
        source: request.source,
        targetView: request.targetView,
      });
    };

    window.addEventListener(WORKSPACE_OPEN_EVENT, onOpen as EventListener);
    return () => {
      window.removeEventListener(WORKSPACE_OPEN_EVENT, onOpen as EventListener);
    };
  }, [openWorkspaceDocument]);

  return {
    activeDoc,
    workspaceOpen,
    openWorkspaceDocument,
    closeWorkspace,
    toggleWorkspace,
  };
}
