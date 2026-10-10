/**
 * useProjectsCache - maintains a stable project list cache and loose-thread count.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import { checkAuthGate, getAuthState, useAuthState } from "@/lib/authState";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";
import { logOnce } from "@/lib/logging/logOnce";
import {
  collapseSidebarGeneralProjectAliases,
  resolveSidebarGeneralProjectId,
  normalizeSidebarProject,
} from "./sidebarPresentation";

type UseProjectsCacheOptions = {
  threadsForLooseCount?: Thread[];
  enabled?: boolean;
};

export type UseProjectsCacheResult = {
  projectList: Project[];
  setProjectList: React.Dispatch<React.SetStateAction<Project[]>>;
  refreshProjectsFromServer: () => Promise<void>;
  looseCount: number;
  accountId: string | null;
  loadedForCurrentAuth: boolean;
};

const STORAGE_KEY = "cfy.projectsCache";
const EMPTY_PROJECT_LIST: Project[] = [];

type ProjectSnapshot = {
  sessionScope: string;
  projectList: Project[];
  accountId: string | null;
  loaded: boolean;
};

function authSessionScope(auth: ReturnType<typeof getAuthState>): string {
  return auth.status === "authenticated"
    ? `authenticated:${auth.token ?? "local"}`
    : auth.status;
}

function normalizeProjectsResponse(res: any): Project[] {
  const payload = res?.data ?? res;
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.projects)
    ? payload.projects
    : [];
  const normalized = list
    .filter(Boolean)
    .map((p: any) => normalizeSidebarProject({
      ...p,
      id: String(p.id ?? p.project_id ?? ""),
      name: p.name ?? p.project_name ?? "Untitled",
      icon: p.icon ?? "📁",
      color: p.color,
      ...("systemRole" in p || "system_role" in p
        ? { systemRole: p.systemRole ?? p.system_role ?? null }
        : {}),
      ...("archivedAt" in p || "archived_at" in p
        ? { archivedAt: p.archivedAt ?? p.archived_at ?? null }
        : {}),
    }))
    .filter((project: any) => String(project.id).trim().length > 0);
  return collapseSidebarGeneralProjectAliases(normalized);
}

function resolveProjectAccountId(res: any): string | null {
  const payload = res?.data ?? res;
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.projects)
      ? payload.projects
      : [];
  if (list.length === 0) return null;
  const owners = list.map((project: any) =>
    typeof project?.user_id === "string" ? project.user_id.trim() : ""
  );
  if (owners.some((owner: string) => !owner)) return null;
  const uniqueOwners = new Set(owners);
  return uniqueOwners.size === 1 ? owners[0] : null;
}

/**
 * Compare two project records by visible fields to avoid no-op updates.
 */
function sameProject(a: Project, b: Project): boolean {
  const aRest = { ...a } as Record<string, unknown>;
  const bRest = { ...b } as Record<string, unknown>;
  delete aRest.id;
  delete aRest.name;
  delete aRest.icon;
  delete aRest.color;
  delete bRest.id;
  delete bRest.name;
  delete bRest.icon;
  delete bRest.color;
  return String(a.id) === String(b.id)
    && (a.name ?? "") === (b.name ?? "")
    && (a.icon ?? "") === (b.icon ?? "")
    && (a.color ?? "") === (b.color ?? "")
    && JSON.stringify(aRest) === JSON.stringify(bRest);
}

/**
 * Check if two project lists are effectively identical for UI rendering.
 */
function equalProjectLists(a: Project[], b: Project[]): boolean {
  if (a === b) return true;
  if (!Array.isArray(a) || !Array.isArray(b)) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (!sameProject(a[i], b[i])) return false;
  }
  return true;
}

export function useProjectsCache({
  threadsForLooseCount = [],
  enabled = true,
}: UseProjectsCacheOptions = {}): UseProjectsCacheResult {
  const auth = useAuthState();
  const sessionScope = authSessionScope(auth);
  const requestGenerationRef = useRef(0);
  const [snapshot, setSnapshot] = useState<ProjectSnapshot>({
    sessionScope,
    projectList: [],
    accountId: null,
    loaded: false,
  });
  const snapshotIsCurrent = snapshot.sessionScope === sessionScope;
  const projectList = snapshotIsCurrent ? snapshot.projectList : EMPTY_PROJECT_LIST;
  const accountId = snapshotIsCurrent ? snapshot.accountId : null;
  const loadedForCurrentAuth = snapshotIsCurrent && snapshot.loaded;

  useEffect(() => {
    try {
      if (typeof window !== "undefined") window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore unavailable storage */
    }
  }, []);

  useEffect(() => {
    if (!enabled || !loadedForCurrentAuth) return;
    const defaultProjectId = resolveSidebarGeneralProjectId(projectList);
    if (!defaultProjectId) return;
    try {
      if (typeof window === "undefined") return;
      window.localStorage.setItem("cfy.generalProjectId", defaultProjectId);
      window.localStorage.setItem("cfy.defaultProjectId", defaultProjectId);
    } catch {
      /* ignore */
    }
  }, [enabled, loadedForCurrentAuth, projectList]);

  const setProjectList = useCallback<React.Dispatch<React.SetStateAction<Project[]>>>(
    (nextValue) => {
      setSnapshot((previous) => {
        const current = previous.sessionScope === sessionScope
          ? previous
          : { sessionScope, projectList: [], accountId: null, loaded: false };
        const nextList = typeof nextValue === "function"
          ? nextValue(current.projectList)
          : nextValue;
        return equalProjectLists(current.projectList, nextList)
          ? current
          : { ...current, projectList: nextList };
      });
    },
    [sessionScope]
  );

  const refreshProjectsFromServer = useCallback(async (options: { throwOnError?: boolean } = {}) => {
    const requestSessionScope = sessionScope;
    if (!checkAuthGate(getAuthState(), "projects list load")) return;
    const requestGeneration = ++requestGenerationRef.current;
    try {
      const res = await api.get("/api/projects");
      if (
        requestGeneration !== requestGenerationRef.current ||
        authSessionScope(getAuthState()) !== requestSessionScope
      ) return;
      const list = normalizeProjectsResponse(res);
      setSnapshot({
        sessionScope: requestSessionScope,
        projectList: list,
        accountId: resolveProjectAccountId(res),
        loaded: true,
      });
    } catch (err) {
      logOnce("poll:projects", 10_000, () => {
        console.warn("[projects] failed to refresh project cache", err);
      });
      if (options.throwOnError) {
        throw err;
      }
      /* parent may retry; swallow errors here */
    }
  }, [sessionScope]);

  const canLoadProjects = checkAuthGate(auth, "projects list load");
  useEffect(() => {
    if (!enabled) return;
    if (!canLoadProjects) {
      requestGenerationRef.current += 1;
      setSnapshot({ sessionScope, projectList: [], accountId: null, loaded: false });
      return;
    }
    void refreshProjectsFromServer({ throwOnError: true });
    return () => {
      requestGenerationRef.current += 1;
    };
  }, [auth.ready, auth.status, auth.token, canLoadProjects, enabled, refreshProjectsFromServer, sessionScope]);

  const looseCount = useMemo(
    () => (threadsForLooseCount || []).filter((t) => !t.projectId).length,
    [threadsForLooseCount]
  );

  return {
    projectList,
    setProjectList,
    refreshProjectsFromServer,
    looseCount,
    accountId,
    loadedForCurrentAuth,
  };
}

export default useProjectsCache;
