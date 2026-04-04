import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";

/* ================================
   Project Normalization (codex)
================================ */

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
  return String(value ?? "").trim().replace(/\s+/g, " ");
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
  ];

  for (const marker of directMarkers) {
    if (typeof marker === "string" && marker.trim()) return true;
    if (typeof marker === "number" && Number.isFinite(marker)) return true;
  }

  const metadata = project.metadata;
  if (metadata && typeof metadata === "object") {
    const meta = metadata as Record<string, unknown>;
    if (hasImportedProvenance(meta)) return true;
  }

  return false;
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

  if (isSidebarGeneralProjectName(rawName)) return "General";

  if (!hasImportedProvenance(project)) return rawName;

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

export function normalizeSidebarProjects<T extends SidebarProjectRecord>(
  projects: readonly T[]
): T[] {
  return projects.map(normalizeSidebarProject);
}

export function selectSidebarGeneralProject<T extends SidebarProjectRecord>(
  projects: readonly T[]
): T | null {
  const candidates = projects.filter((project) =>
    isSidebarGeneralProjectName(project.name)
  );

  return candidates[0] ?? null;
}

export function resolveSidebarGeneralProjectId<T extends SidebarProjectRecord>(
  projects: readonly T[],
  fallback: string | null = null
): string | null {
  return selectSidebarGeneralProject(projects)?.id ?? fallback;
}

export function collapseSidebarGeneralProjectAliases<T extends SidebarProjectRecord>(
  projects: readonly T[]
): T[] {
  const seen = new Set<string>();

  return projects.filter((project) => {
    if (!isSidebarGeneralProjectName(project.name)) return true;
    if (seen.has("general")) return false;
    seen.add("general");
    return true;
  });
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

  if (!threadProjectId) return generalProjectId;

  const known = new Set(projects.map((p) => String(p.id)));

  return known.has(threadProjectId) ? threadProjectId : generalProjectId;
}

export function threadBelongsToGeneral(
  thread: Pick<Thread, "projectId">,
  projects: ReadonlyArray<Pick<Project, "id">>,
  generalProjectId: string | null
): boolean {
  return resolveSidebarThreadBucketId(thread, projects, generalProjectId) === generalProjectId;
}

export function projectMatchesSidebarQuery(
  project: SidebarProjectRecord,
  query: string
): boolean {
  if (!query.trim()) return true;
  return cleanSidebarProjectTitle(project)
    .toLowerCase()
    .includes(query.trim().toLowerCase());
}

/* ================================
   Provenance System (main)
================================ */

export type SidebarProvenanceOption = {
  value: string;
  label: string;
};

const CANONICAL_PROVENANCE_LABELS = new Map<string, string>([
  ["chatgpt", "ChatGPT"],
  ["openai", "OpenAI"],
  ["claude", "Claude"],
  ["anthropic", "Anthropic"],
  ["gemini", "Gemini"],
]);

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function normalizeLookupKey(value: string): string {
  return value.trim().toLowerCase();
}

export function normalizeSidebarProvenanceLabel(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const key = normalizeLookupKey(value);
  return CANONICAL_PROVENANCE_LABELS.get(key) ?? value;
}

function readThreadProvenanceCandidates(thread: Thread): unknown[] {
  const metadata = asRecord(thread.metadata);
  if (!metadata) return [];

  const provenance = asRecord(metadata.provenance);

  return [
    metadata.import_source,
    metadata.provider,
    metadata.source,
    provenance?.provider,
    provenance?.source,
  ];
}

export function getSidebarThreadProvenanceLabel(thread: Thread): string | null {
  for (const candidate of readThreadProvenanceCandidates(thread)) {
    const label = normalizeSidebarProvenanceLabel(candidate);
    if (label) return label;
  }
  return null;
}

export function collectSidebarProvenanceOptions(
  threads: Thread[]
): SidebarProvenanceOption[] {
  const seen = new Set<string>();

  return threads
    .map((t) => getSidebarThreadProvenanceLabel(t))
    .filter((label): label is string => !!label && !seen.has(label))
    .map((label) => {
      seen.add(label);
      return { value: label, label };
    });
}

export function threadMatchesSidebarProvenance(
  thread: Thread,
  selectedProvenance: string | null
): boolean {
  if (!selectedProvenance) return true;
  return getSidebarThreadProvenanceLabel(thread) === selectedProvenance;
}