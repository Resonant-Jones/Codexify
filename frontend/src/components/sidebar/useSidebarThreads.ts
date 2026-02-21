/**
 * useSidebarThreads - thread list state with semantic update guards.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";

type UseSidebarThreadsOptions = {
  initialThreads: Thread[];
  projectId?: string | null;
  onProjectChange?: (id: string | null) => void;
  projects?: Project[];
};

type UseSidebarThreadsResult = {
  threads: Thread[];
  displayThreads: Thread[];
  scopeLabel: string;
  currentProjectId: string | null;
  setScope: (id: string | null) => void;
  handleDeleteThread: (threadId: string) => void;
  renameThread: (threadId: string, title: string) => Promise<void>;
  toggleArchiveThread: (threadId: string, archived: boolean) => Promise<void>;
  deleteThread: (threadId: string) => Promise<void>;
  looseCount: number;
};

const LOCAL_SCOPE_KEY = "cfy.lastProjectId";

function emitThreadsRefresh(kind: string, detail: Record<string, any>) {
  try {
    window.dispatchEvent(new CustomEvent("cfy:threads:refresh", { detail: { kind, ...detail } }));
  } catch {
    /* no-op for non-DOM envs */
  }
}

function emitToast(kind: "success" | "error", message: string) {
  try {
    window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { kind, message } }));
  } catch {
    /* ignore */
  }
}

async function threadApi(method: "patch" | "delete", id: string | number, body?: any) {
  const paths = [`/chat/${id}`, `/chat/threads/${id}`];
  let lastErr: any = null;
  for (const p of paths) {
    try {
      if (method === "patch") return await api.patch(p, body);
      if (method === "delete") return await api.delete(p);
    } catch (err: any) {
      if (err?.response?.status === 404) {
        lastErr = err;
        continue;
      }
      throw err;
    }
  }
  throw lastErr || new Error("Thread API routes not available");
}

function sameThread(a: Thread, b: Thread): boolean {
  return String(a.id) === String(b.id)
    && a.title === b.title
    && (a.lastMessage ?? "") === (b.lastMessage ?? "")
    && (a.projectId ?? null) === (b.projectId ?? null)
    && (a.archivedAt ?? null) === (b.archivedAt ?? null)
    && (a.unread ?? 0) === (b.unread ?? 0);
}

function equalThreadLists(a: Thread[], b: Thread[]): boolean {
  if (a === b) return true;
  if (!Array.isArray(a) || !Array.isArray(b)) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (!sameThread(a[i], b[i])) return false;
  }
  return true;
}

function sanitizeThread(raw: Thread): Thread {
  return {
    ...raw,
    messages: [], // avoid storing message arrays in sidebar state
    lastMessage: (raw.lastMessage ?? "").toString(),
    title: (raw.title ?? "").toString(),
  };
}

export function useSidebarThreads({
  initialThreads,
  projectId,
  onProjectChange,
  projects = [],
}: UseSidebarThreadsOptions): UseSidebarThreadsResult {
  const [threadList, setThreadList] = useState<Thread[]>(() => (initialThreads || []).map(sanitizeThread));
  const previewRef = useRef<Map<string, string>>(new Map());
  const stableTitleRef = useRef<Map<string, string>>(new Map());
  const lastEventSigRef = useRef<string | null>(null);
  const lastEventTsRef = useRef<number>(0);

  // Local project scope fallback if parent does not control it
  const [localProjectId, setLocalProjectId] = useState<string | null>(() => {
    if (projectId !== undefined && projectId !== null) return projectId;
    if (typeof window === "undefined") return null;
    const stored = window.localStorage.getItem(LOCAL_SCOPE_KEY);
    if (stored === "null") return null;
    return stored || null;
  });

  // Mirror incoming threads (sanitized) while avoiding no-op state churn
  useEffect(() => {
    const sanitized = (initialThreads || []).map(sanitizeThread);
    setThreadList((prev) => (equalThreadLists(prev, sanitized) ? prev : sanitized));
  }, [initialThreads]);

  // Seed preview cache and titles when threads change
  useEffect(() => {
    const map = previewRef.current;
    const incomingIds = new Set<string>();
    const freq = new Map<string, number>();

    threadList.forEach((t) => {
      const snippet = (t.lastMessage ?? "").toString().trim();
      if (snippet) freq.set(snippet, (freq.get(snippet) || 0) + 1);
    });

    threadList.forEach((t) => {
      const id = String(t.id ?? "");
      if (!id) return;
      incomingIds.add(id);
      if (!map.has(id)) {
        const candidate = (t.lastMessage ?? "").toString();
        const trimmed = candidate.trim();
        const looksDuplicated = trimmed && (freq.get(trimmed) || 0) > 1;
        if (!looksDuplicated && trimmed) {
          map.set(id, candidate);
        }
      }
      const title = (t.title ?? "").toString().trim();
      if (title && !stableTitleRef.current.has(id)) {
        stableTitleRef.current.set(id, title);
      }
    });

    // prune stale previews
    Array.from(map.keys()).forEach((k) => {
      if (!incomingIds.has(k)) map.delete(k);
    });
  }, [threadList]);

  // keep local scope in sync with controlled prop
  useEffect(() => {
    if (projectId === undefined) return;
    setLocalProjectId((prev) => (prev === projectId ? prev : projectId ?? null));
    try {
      window.localStorage.setItem(LOCAL_SCOPE_KEY, projectId ?? "null");
    } catch {}
  }, [projectId]);

  const handleDeleteThread = useCallback(
    (threadId: string) => {
      setThreadList((prev) => {
        const next = prev.filter((t) => String(t.id) !== String(threadId));
        return next.length === prev.length ? prev : next;
      });
      try {
        previewRef.current.delete(String(threadId));
      } catch {}
    },
    []
  );

  const setScope = useCallback(
    (id: string | null) => {
      if (onProjectChange) {
        onProjectChange(id);
      } else {
        setLocalProjectId((prev) => (prev === id ? prev : id));
      }
      try {
        window.localStorage.setItem(LOCAL_SCOPE_KEY, id ?? "null");
      } catch {}
    },
    [onProjectChange]
  );

  // SSE / cross-view updates
  useEffect(() => {
    function onThreadsRefresh(raw: Event) {
      const ce = raw as CustomEvent;
      const d: any = ce.detail || {};
      const kind = d?.kind ?? d?.type;
      if (!d || kind === "ping") return;

      const idGuess =
        d?.id != null ? String(d.id) :
        d?.thread_id != null ? String(d.thread_id) :
        d?.threadId != null ? String(d.threadId) :
        "";

      const sig = JSON.stringify({
        k: kind,
        id: idGuess,
        title: d.title ?? "",
        content: d.content ?? d.message?.content ?? "",
        proj: d.project_id ?? d.projectId ?? null,
        arch: d.archived ?? null,
      });

      const now = Date.now();
      if (lastEventSigRef.current === sig && now - (lastEventTsRef.current || 0) < 5000) return;
      lastEventSigRef.current = sig;
      lastEventTsRef.current = now;

      setThreadList((prev) => {
        const id =
          d?.id != null ? String(d.id)
          : d?.thread_id != null ? String(d.thread_id)
          : d?.threadId != null ? String(d.threadId)
          : "";
        if (!id) return prev;

        const idx = prev.findIndex((t) => String(t.id) === id);
        if (idx === -1) return prev;

        switch (kind) {
          case "rename": {
            const title = (d.title ?? "").toString().trim();
            if (!title) return prev;
            stableTitleRef.current.set(id, title);
            const next = [...prev];
            next[idx] = { ...next[idx], title };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "archive": {
            if (prev[idx].archivedAt) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], archivedAt: new Date().toISOString() };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "unarchive": {
            if (!prev[idx].archivedAt) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], archivedAt: null };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "message":
          case "message.created": {
            const content = (d.content ?? d.message?.content ?? "").toString();
            if (!content) return prev;
            try {
              previewRef.current.set(id, content);
            } catch {}
            const next = [...prev];
            next[idx] = { ...next[idx], lastMessage: content };
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "delete": {
            const next = prev.filter((t) => String(t.id) !== id);
            return equalThreadLists(next, prev) ? prev : next;
          }
          case "move": {
            const proj = d.project_id ?? d.projectId ?? null;
            if ((prev[idx].projectId ?? null) === (proj ?? null)) return prev;
            const next = [...prev];
            next[idx] = { ...next[idx], projectId: proj };
            return equalThreadLists(next, prev) ? prev : next;
          }
          default:
            return prev;
        }
      });
    }
    window.addEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
    return () => window.removeEventListener("cfy:threads:refresh", onThreadsRefresh as EventListener);
  }, []);

  const renameThread = useCallback(
    async (threadId: string, title: string) => {
      const nextTitle = title.trim();
      if (!nextTitle) return;
      try {
        await threadApi("patch", threadId, { title: nextTitle });
        emitThreadsRefresh("rename", { id: threadId, title: nextTitle });
        emitToast("success", "Thread renamed");
        setThreadList((prev) => {
          const idx = prev.findIndex((t) => String(t.id) === String(threadId));
          if (idx === -1) return prev;
          const next = [...prev];
          next[idx] = { ...next[idx], title: nextTitle };
          stableTitleRef.current.set(String(threadId), nextTitle);
          return equalThreadLists(next, prev) ? prev : next;
        });
      } catch (err) {
        emitToast("error", "Rename failed. Please try again.");
        throw err;
      }
    },
    []
  );

  const toggleArchiveThread = useCallback(
    async (threadId: string, archived: boolean) => {
      try {
        await threadApi("patch", threadId, { archived });
        emitThreadsRefresh(archived ? "archive" : "unarchive", { id: threadId, archived });
        emitToast("success", archived ? "Thread archived" : "Thread restored");
        setThreadList((prev) => {
          const idx = prev.findIndex((t) => String(t.id) === String(threadId));
          if (idx === -1) return prev;
          const next = [...prev];
          next[idx] = { ...next[idx], archivedAt: archived ? new Date().toISOString() : null };
          return equalThreadLists(next, prev) ? prev : next;
        });
        if (archived) {
          handleDeleteThread(threadId);
        }
      } catch (err) {
        emitToast("error", `${archived ? "Archive" : "Restore"} failed. Please try again.`);
        throw err;
      }
    },
    [handleDeleteThread]
  );

  const deleteThread = useCallback(
    async (threadId: string) => {
      try {
        await threadApi("delete", threadId);
        emitThreadsRefresh("delete", { id: threadId });
        emitToast("success", "Thread deleted");
        handleDeleteThread(threadId);
      } catch (err: any) {
        const status = err?.response?.status;
        emitToast("error", `Delete failed${status ? ` (${status})` : ""}. Please try again.`);
        throw err;
      }
    },
    [handleDeleteThread]
  );

  const currentProjectId = onProjectChange ? (projectId ?? null) : localProjectId;

  const scopedThreads = useMemo(() => {
    const base =
      currentProjectId === null
        ? threadList.filter((t) => !t.projectId)
        : currentProjectId
        ? threadList.filter((t) => String(t.projectId ?? "") === String(currentProjectId))
        : threadList;
    return base.filter((t) => !t.archivedAt);
  }, [currentProjectId, threadList]);

  const displayThreads = useMemo(() => {
    const titleMap = stableTitleRef.current;
    const previewMap = previewRef.current;
    const seen = new Set<string>();
    const out: Thread[] = [];
    for (const t of scopedThreads) {
      const id = String(t.id ?? "");
      if (!id || seen.has(id)) continue;
      seen.add(id);
      out.push({
        ...t,
        messages: [],
        lastMessage: (previewMap.get(id) ?? t.lastMessage ?? "").toString(),
        title: (titleMap.get(id) ?? t.title ?? "Untitled").toString(),
      });
    }
    return out;
  }, [scopedThreads]);

  const scopeLabel = useMemo(() => {
    if (currentProjectId === null) return "General";
    if (currentProjectId) {
      const proj = projects.find((p) => String(p.id) === String(currentProjectId));
      return proj?.name ?? "Project";
    }
    return "All";
  }, [currentProjectId, projects]);

  const looseCount = useMemo(() => threadList.filter((t) => !t.projectId).length, [threadList]);

  return {
    threads: threadList,
    displayThreads,
    scopeLabel,
    currentProjectId,
    setScope,
    handleDeleteThread,
    renameThread,
    toggleArchiveThread,
    deleteThread,
    looseCount,
  };
}

export default useSidebarThreads;
