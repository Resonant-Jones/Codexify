import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";

export type SidebarProjectRecord = Project & Record<string, unknown>;

const GENERAL_PROJECT_ALIASES = new Set(["general", "loose threads"]);
const IMPORTED_PROVIDER_PREFIXES = [
  "chatgpt",
  "openai",
  "claude",
  "anthropic",
  "gemini",
  "perplexity",
];

function normalizeText(value: unknown): string {
  return String(value ?? "")
    .trim()
    .replace(/\s+/g, " ");
}

export function isSidebarGeneralProjectName(value: unknown): boolean {
  return GENERAL_PROJECT_ALIASES.has(normalizeText(value).toLowerCase());
}

function hasImportedProvenance(project: Record<string, unknown>): boolean {
  const directMarkers = [
    project.import_source,
    project.importSource,
    project.imported_at,
    project.importedAt,
    project.imported_from,
    project.importedFrom,
    project.restored_at,
    project.restoredAt,
    project.restored_from,
    project.restoredFrom,
    project.import_profile,
    project.importProfile,
    project.source_thread_id,
    project.sourceThreadId,
    project.source_conversation_template_id,
    project.sourceConversationTemplateId,
    project.source_gizmo_id,
    project.sourceGizmoId,
    project.source_gizmo_type,
    project.sourceGizmoType,
  ];

  for (const marker of directMarkers) {
    if (typeof marker === "string" && marker.trim()) {
      return true;
    }
    if (typeof marker === "number" && Number.isFinite(marker)) {
      return true;
    }
  }

  const metadata = project.metadata;
  if (metadata && typeof metadata === "object") {
    const meta = metadata as Record<string, unknown>;
    if (hasImportedProvenance(meta)) {
      return true;
    }
    const provenance = meta.provenance;
    if (typeof provenance === "string" && /import|restore/i.test(provenance)) {
      return true;
    }
    const origin = meta.origin;
    if (typeof origin === "string" && /import/i.test(origin)) {
      return true;
    }
  }

  const provenance = project.provenance;
  if (typeof provenance === "string" && /import|restore/i.test(provenance)) {
    return true;
  }

  return false;
}

function isSidebarGeneralProjectCandidate(
  project: Partial<SidebarProjectRecord> & Record<string, unknown>
): boolean {
  const rawName = normalizeText(project.name ?? project.project_name ?? "");
  const cleanedName = cleanSidebarProjectTitle(project);
  return isSidebarGeneralProjectName(rawName) || isSidebarGeneralProjectName(cleanedName);
}

function stripImportedProviderPrefix(name: string): string {
  const trimmed = normalizeText(name);
  for (const provider of IMPORTED_PROVIDER_PREFIXES) {
    const match = trimmed.match(
      new RegExp(`^${provider}\\s*[-–—:|/]\\s*`, "i")
    );
    if (!match) continue;
    const rest = trimmed.slice(match[0].length).trim();
    if (rest) return rest;
  }
  return trimmed;
}

export function cleanSidebarProjectTitle(
  project: Partial<SidebarProjectRecord> & Record<string, unknown>
): string {
  const rawName = normalizeText(project.name ?? project.project_name ?? "Untitled");
  if (isSidebarGeneralProjectName(rawName)) {
    return "General";
  }
  if (!hasImportedProvenance(project)) {
    return rawName;
  }
  const cleaned = stripImportedProviderPrefix(rawName);
  return cleaned || rawName;
}

export function normalizeSidebarProject<T extends SidebarProjectRecord>(project: T): T {
  return {
    ...project,
    id: String(project.id ?? project.project_id ?? ""),
    name: cleanSidebarProjectTitle(project),
  } as T;
}

export function normalizeSidebarProjects<T extends SidebarProjectRecord>(projects: readonly T[]): T[] {
  return projects.map((project) => normalizeSidebarProject(project));
}

export function selectSidebarGeneralProject<T extends SidebarProjectRecord>(
  projects: readonly T[]
): T | null {
  const candidates = projects.filter((project) => isSidebarGeneralProjectCandidate(project));
  if (!candidates.length) return null;

  const isExactGeneral = (project: T) =>
    normalizeText(project.name ?? project.project_name ?? "").toLowerCase() === "general";

  // Prefer the exact General row first, then the best remaining non-imported alias.
  return (
    candidates.find((project) => isExactGeneral(project))
    || candidates.find((project) => !hasImportedProvenance(project))
    || candidates[0]
  );
}

export function resolveSidebarGeneralProjectId<T extends SidebarProjectRecord>(
  projects: readonly T[],
  fallback: string | null = null
): string | null {
  const project = selectSidebarGeneralProject(projects);
  return project?.id != null ? String(project.id) : fallback;
}

export function collapseSidebarGeneralProjectAliases<T extends SidebarProjectRecord>(
  projects: readonly T[]
): T[] {
  const normalized = projects.map((project) => normalizeSidebarProject(project));
  const canonical = selectSidebarGeneralProject(projects);
  if (!canonical) return normalized;

  const canonicalId = String(canonical.id);
  let keptCanonical = false;

  return normalized.reduce<T[]>((acc, project) => {
    if (!isSidebarGeneralProjectName(project?.name)) {
      acc.push(project);
      return acc;
    }

    if (String(project.id) !== canonicalId || keptCanonical) {
      return acc;
    }

    acc.push(project);
    keptCanonical = true;
    return acc;
  }, []);
}

export function normalizeSidebarProjectId(value: unknown): string | null {
  const id = normalizeText(value);
  return id || null;
}

export function resolveSidebarThreadBucketId(
  thread: Pick<Thread, "projectId">,
  projects: ReadonlyArray<Pick<Project, "id">>,
  generalProjectId: string | null
): string | null {
  const threadProjectId = normalizeSidebarProjectId(thread.projectId);
  if (!threadProjectId) {
    return generalProjectId;
  }
  if (generalProjectId && threadProjectId === generalProjectId) {
    return generalProjectId;
  }
  const knownProjectIds = new Set(projects.map((project) => String(project.id)));
  if (knownProjectIds.has(threadProjectId)) {
    return threadProjectId;
  }
  return generalProjectId;
}

export function threadBelongsToGeneral(
  thread: Pick<Thread, "projectId">,
  projects: ReadonlyArray<Pick<Project, "id">>,
  generalProjectId: string | null
): boolean {
  const bucketId = resolveSidebarThreadBucketId(thread, projects, generalProjectId);
  return bucketId === generalProjectId || bucketId === null;
}

export function projectMatchesSidebarQuery(project: SidebarProjectRecord, query: string): boolean {
  if (!query.trim()) return true;
  return cleanSidebarProjectTitle(project).toLowerCase().includes(query.trim().toLowerCase());
}
