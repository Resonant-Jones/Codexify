import { useCallback, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";

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
  return list
    .filter(Boolean)
    .map((p: any) => ({
      id: String(p.id ?? p.project_id),
      name: p.name ?? p.project_name ?? "Untitled",
      icon: p.icon ?? "📁",
      color: p.color,
    }));
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
  return out;
}

export function useProjectsCache({
  initialProjects = [],
  threadsForLooseCount = [],
}: UseProjectsCacheOptions = {}): UseProjectsCacheResult {
  const [projectList, setProjectList] = useState<Project[]>(() => {
    const cache = readProjectsCache();
    return cache.length ? cache : initialProjects;
  });

  useEffect(() => {
    setProjectList((prev) => mergeProjects(prev, initialProjects));
  }, [initialProjects]);

  useEffect(() => {
    writeProjectsCache(projectList);
  }, [projectList]);

  const refreshProjectsFromServer = useCallback(async () => {
    try {
      const res = await api.get("/projects");
      const list = normalizeProjectsResponse(res);
      if (Array.isArray(list) && list.length) {
        setProjectList((prev) => mergeProjects(prev, list));
      }
    } catch {
      /* parent may retry; swallow errors here */
    }
  }, []);

  // Hydrate on mount
  useEffect(() => {
    void refreshProjectsFromServer();
  }, [refreshProjectsFromServer]);

  // Refresh when focus or visibility regained
  useEffect(() => {
    const onFocus = () => { void refreshProjectsFromServer(); };
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        void refreshProjectsFromServer();
      }
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refreshProjectsFromServer]);

  const looseCount = useMemo(
    () => (threadsForLooseCount || []).filter((t) => !t.projectId).length,
    [threadsForLooseCount]
  );

  return { projectList, setProjectList, refreshProjectsFromServer, looseCount };
}

export default useProjectsCache;
