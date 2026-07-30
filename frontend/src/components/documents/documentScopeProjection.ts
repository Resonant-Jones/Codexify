import type { Thread } from "@/types/ui";

/**
 * The deliberately small Guardian-owned context that may be projected into
 * Documents. It is observational: Documents never writes it back.
 */
export type DocumentSidebarThread = Omit<Thread, "messages">;

export type GuardianSidebarSnapshot = {
  threads: DocumentSidebarThread[];
  activeThreadId: number | null;
  selectedProjectId: number | null;
  selectedProjectName: string | null;
  activeThreadProjectId: number | null;
};

export type DocumentsScope =
  | {
      kind: "project";
      projectId: number | null;
      threadId: null;
    }
  | {
      kind: "thread";
      projectId: number | null;
      threadId: number;
    };

export type DocumentScopeQuery = {
  limit: 100;
  project_id?: number;
  thread_id?: number;
};

export type DocumentUploadScope = {
  projectId: number | null;
  threadId: number | null;
};

function toPositiveId(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function projectIdForThread(
  threadId: number,
  threads: readonly DocumentSidebarThread[]
): number | null {
  const matched = threads.find((thread) => toPositiveId(thread.id) === threadId);
  return toPositiveId(matched?.projectId);
}

/** Seed once when entering Documents; it is not a synchronization mechanism. */
export function seedDocumentsScope(
  snapshot: GuardianSidebarSnapshot | null,
  fallbackProjectId: number | null = null
): DocumentsScope {
  const activeThreadId = toPositiveId(snapshot?.activeThreadId);
  if (activeThreadId != null) {
    return {
      kind: "thread",
      threadId: activeThreadId,
      projectId:
        toPositiveId(snapshot?.activeThreadProjectId) ??
        projectIdForThread(activeThreadId, snapshot?.threads ?? []),
    };
  }

  return selectDocumentsProject(
    toPositiveId(snapshot?.selectedProjectId) ?? toPositiveId(fallbackProjectId)
  );
}

export function selectDocumentsProject(projectId: number | string | null): DocumentsScope {
  return {
    kind: "project",
    projectId: toPositiveId(projectId),
    threadId: null,
  };
}

export function selectDocumentsThread(
  threadId: number | string,
  threads: readonly DocumentSidebarThread[],
  fallbackProjectId: number | null = null
): DocumentsScope {
  const resolvedThreadId = toPositiveId(threadId);
  if (resolvedThreadId == null) {
    return selectDocumentsProject(fallbackProjectId);
  }

  return {
    kind: "thread",
    threadId: resolvedThreadId,
    projectId: projectIdForThread(resolvedThreadId, threads) ?? toPositiveId(fallbackProjectId),
  };
}

export function getDocumentScopeQuery(scope: DocumentsScope): DocumentScopeQuery {
  if (scope.kind === "thread") {
    return { limit: 100, thread_id: scope.threadId };
  }

  return scope.projectId == null
    ? { limit: 100 }
    : { limit: 100, project_id: scope.projectId };
}

export function getDocumentUploadScope(scope: DocumentsScope): DocumentUploadScope {
  return {
    projectId: scope.projectId,
    threadId: scope.threadId,
  };
}
