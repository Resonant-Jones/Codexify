/**
 * useProjectsCache - maintains a stable project list cache and loose-thread count.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";
import { logOnce } from "@/lib/logging/logOnce";

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
function normalizeProjectName(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function isDefaultAliasName(value: unknown): boolean {
  const normalized = normalizeProjectName(value);
  return normalized === "general" || normalized === "loose threads";
}

function normalizeDefaultProjectAliases(list: Project[]): Project[] {
  const defaults = list.filter((project) => isDefaultAliasName(project?.name));
  if (defaults.length <= 1) {
    return list.map((project) =>
      isDefaultAliasName(project?.name)
        ? { ...project, name: "General" }
        : project
    );
  }

  const canonical =
    defaults.find((project) => normalizeProjectName(project.name) === "general") ||
    defaults[0];
  const canonicalId = String(canonical.id);

  return list
    .filter((project) => {
      if (!isDefaultAliasName(project?.name)) return true;
      return String(project.id) === canonicalId;
    })
    .map((project) =>
      isDefaultAliasName(project?.name)
        ? { ...project, name: "General" }
        : project
    );
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
    .map((p: any) => ({
      id: String(p.id ?? p.project_id),
      name: p.name ?? p.project_name ?? "Untitled",
      icon: p.icon ?? "📁",
      color: p.color,
    }));
  return normalizeDefaultProjectAliases(normalized);
}

function readProjectsCache(): Project[] {
  try {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.filter((p) => p && p.id && p.name) : [];
  } catch {
    return [];
  }
}

function writeProjectsCache(list: Project[]) {
  try {
    if (typeof window === "undefined") return;
    const compact = list.map((p) => ({ id: String(p.id), name: p.name, icon: p.icon, color: p.color }));
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(compact));
  } catch {
    /* ignore */
  }
}

function mergeProjects(primary: Project[], secondary: Project[]): Project[] {
  const seen = new Set<string>();
  const out: Project[] = [];
  const push = (p?: Project) => {
    if (!p) return;
    const key = String(p.id ?? "");
    const nameKey = `name:${p.name}`;
    if (key && seen.has(key)) return;
    if (!key && seen.has(nameKey)) return;
    if (key) seen.add(key);
    else seen.add(nameKey);
    out.push({ id: String(p.id), name: p.name, icon: p.icon, color: p.color });
  };
  primary.forEach(push);
  secondary.forEach(push);
  return normalizeDefaultProjectAliases(out);
}

/**
 * Compare two project records by visible fields to avoid no-op updates.
 */
function sameProject(a: Project, b: Project): boolean {
  return String(a.id) === String(b.id)
    && (a.name ?? "") === (b.name ?? "")
    && (a.icon ?? "") === (b.icon ?? "")
    && (a.color ?? "") === (b.color ?? "");
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
    const defaultProject = projectList.find((project) =>
      isDefaultAliasName(project?.name)
    );
    if (!defaultProject?.id) return;
    try {
      if (typeof window === "undefined") return;
      window.localStorage.setItem(
        "cfy.generalProjectId",
        String(defaultProject.id)
      );
      window.localStorage.setItem(
        "cfy.defaultProjectId",
        String(defaultProject.id)
      );
    } catch {
      /* ignore */
    }
  }, [projectList]);

  const refreshProjectsFromServer = useCallback(async (options: { throwOnError?: boolean } = {}) => {
    try {
      const res = await api.get("/api/projects");
      const list = normalizeProjectsResponse(res);
      if (Array.isArray(list) && list.length) {
        setProjectList((prev) => {
          const merged = mergeProjects(prev, list);
          return equalProjectLists(prev, merged) ? prev : merged;
        });
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
