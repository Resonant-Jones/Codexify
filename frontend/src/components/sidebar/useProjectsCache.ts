/**
 * useProjectsCache - maintains a stable project list cache and loose-thread count.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";
import { logOnce } from "@/lib/logging/logOnce";
import {
  collapseSidebarGeneralProjectAliases,
  resolveSidebarGeneralProjectId,
  normalizeSidebarProject,
} from "./sidebarPresentation";

type UseProjectsCacheOptions = {
  initialProjects?: Project[];
  threadsForLooseCount?: Thread[];
};

type UseProjectsCacheResult = {
  projectList: Project[];
  setProjectList: React.Dispatch<React.SetStateAction<Project[]>>;
  refreshProjectsFromServer: () => Promise<void>;
  looseCount: number;
};

const STORAGE_KEY = "cfy.projectsCache";

function normalizeProjectsResponse(res: any): Project[] {
  const payload = res?.data ?? res;
  const list = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.projects)
    ? payload.projects
    : [];
  const normalized = list
    .filter(Boolean)
    .map((p: any) => ({
      ...p,
      id: String(p.id ?? p.project_id ?? ""),
      name: p.name ?? p.project_name ?? "Untitled",
      icon: p.icon ?? "📁",
      color: p.color,
    }))
    .filter((project: any) => String(project.id).trim().length > 0);
  return collapseSidebarGeneralProjectAliases(normalized);
}

function readProjectsCache(): Project[] {
  try {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr)
      ? collapseSidebarGeneralProjectAliases(arr.filter((p) => p && p.id && p.name))
      : [];
  } catch {
    return [];
  }
}

function writeProjectsCache(list: Project[]) {
  try {
    if (typeof window === "undefined") return;
    const compact = collapseSidebarGeneralProjectAliases(list as Project[]);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(compact));
  } catch {
    /* ignore */
  }
}

function mergeProjects(primary: Project[], secondary: Project[]): Project[] {
  const seen = new Map<string, Project>();
  const push = (p?: Project) => {
    if (!p) return;
    const normalized = normalizeSidebarProject(p as any);
    const key = String(normalized.id ?? "");
    const nameKey = `name:${normalized.name}`;
    const existingKey = key || nameKey;
    const previous = seen.get(existingKey);
    const merged = previous ? normalizeSidebarProject({ ...previous, ...normalized } as any) : normalized;
    seen.set(existingKey, merged);
  };
  primary.forEach(push);
  secondary.forEach(push);
  return collapseSidebarGeneralProjectAliases(Array.from(seen.values()));
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
  initialProjects = [],
  threadsForLooseCount = [],
}: UseProjectsCacheOptions = {}): UseProjectsCacheResult {
  const [projectList, setProjectList] = useState<Project[]>(() => {
    const cache = readProjectsCache();
    return cache.length ? cache : initialProjects;
  });
  const hasFetchedRef = useRef(false);

  useEffect(() => {
    if (!initialProjects.length) return;
    setProjectList((prev) => {
      const merged = mergeProjects(prev, initialProjects);
      // Avoid churn when the merged list is identical but newly allocated.
      return equalProjectLists(prev, merged) ? prev : merged;
    });
  }, [initialProjects]);

  useEffect(() => {
    writeProjectsCache(projectList);
  }, [projectList]);

  useEffect(() => {
    const defaultProjectId = resolveSidebarGeneralProjectId(projectList);
    if (!defaultProjectId) return;
    try {
      if (typeof window === "undefined") return;
      window.localStorage.setItem("cfy.generalProjectId", defaultProjectId);
      window.localStorage.setItem("cfy.defaultProjectId", defaultProjectId);
    } catch {
      /* ignore */
    }
  }, [projectList]);

  const refreshProjectsFromServer = useCallback(async (options: { throwOnError?: boolean } = {}) => {
    try {
      const res = await api.get("/api/projects");
      const list = normalizeProjectsResponse(res);
      if (Array.isArray(list)) {
        setProjectList((prev) => (equalProjectLists(prev, list) ? prev : list));
      }
    } catch (err) {
      logOnce("poll:projects", 10_000, () => {
        console.warn("[projects] failed to refresh project cache", err);
      });
      if (options.throwOnError) {
        throw err;
      }
      /* parent may retry; swallow errors here */
    }
  }, []);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    void refreshProjectsFromServer({ throwOnError: true });
  }, [refreshProjectsFromServer]);

  const looseCount = useMemo(
    () => (threadsForLooseCount || []).filter((t) => !t.projectId).length,
    [threadsForLooseCount]
  );

  return { projectList, setProjectList, refreshProjectsFromServer, looseCount };
}

export default useProjectsCache;
