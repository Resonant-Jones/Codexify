import * as React from "react";
import type { ComponentType } from "react";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";
import type { ConversationOriginSystem } from "@/contracts/conversationOrigin";
import SourceLogoImage from "./icons/SourceLogoImage";
import openaiOfficialSrc from "@/assets/brands/openai/openai-official.png";
import anthropicOfficialSrc from "@/assets/brands/anthropic/Rusty-Butthole.png";
import codexifyMarkSrc from "@/assets/brands/codexify/codexify-mark.png";

/* ================================
   Project Normalization (codex)
================================ */

export type SidebarProjectRecord = Project & Record<string, unknown>;

export type SidebarProjectLike = {
  id?: Project["id"];
  name?: string;
  project_id?: Project["id"];
  project_name?: string;
  icon?: string;
  color?: string;
  metadata?: unknown;
};

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

function hasImportedProvenance(project: SidebarProjectLike): boolean {
  const record = project as Record<string, unknown>;
  const directMarkers = [
    record.import_source,
    record.importSource,
    record.imported_at,
    record.importedAt,
    record.imported_from,
    record.importedFrom,
    record.restored_at,
    record.restoredAt,
    record.restored_from,
    record.restoredFrom,
    record.import_profile,
    record.importProfile,
    record.source_thread_id,
    record.sourceThreadId,
  ];

  for (const marker of directMarkers) {
    if (typeof marker === "string" && marker.trim()) return true;
    if (typeof marker === "number" && Number.isFinite(marker)) return true;
  }

  const metadata = record.metadata;
  if (metadata && typeof metadata === "object") {
    if (hasImportedProvenance(metadata as SidebarProjectLike)) return true;
  }

  return false;
}

function stripImportedProviderPrefix(name: string): string {
  const trimmed = normalizeText(name);
  for (const provider of IMPORTED_PROVIDER_PREFIXES) {
    const match = trimmed.match(new RegExp(`^${provider}\\s*[-–—:|/]\\s*`, "i"));
    if (!match) continue;
    const rest = trimmed.slice(match[0].length).trim();
    if (rest) return rest;
  }
  return trimmed;
}

export function cleanSidebarProjectTitle(
  project: SidebarProjectLike
): string {
  const rawName = normalizeText(project.name ?? project.project_name ?? "Untitled");

  if (isSidebarGeneralProjectName(rawName)) return "General";

  if (!hasImportedProvenance(project)) return rawName;

  const cleaned = stripImportedProviderPrefix(rawName);
  return cleaned || rawName;
}

export function normalizeSidebarProject<T extends SidebarProjectLike>(project: T): SidebarProjectRecord {
  return {
    ...project,
    id: String(project.id ?? project.project_id ?? ""),
    name: cleanSidebarProjectTitle(project),
  };
}

export function normalizeSidebarProjects<T extends SidebarProjectLike>(
  projects: readonly T[]
): SidebarProjectRecord[] {
  return projects.map(normalizeSidebarProject);
}

export function selectSidebarGeneralProject<T extends SidebarProjectLike>(
  projects: readonly T[]
): T | null {
  const candidates = projects.filter((project) => isSidebarGeneralProjectName(project.name));

  return candidates[0] ?? null;
}

export function resolveSidebarGeneralProjectId<T extends SidebarProjectLike>(
  projects: readonly T[],
  fallback: string | null = null
): string | null {
  const selected = selectSidebarGeneralProject(projects);
  const id = selected?.id;
  return id == null ? fallback : String(id);
}

export function collapseSidebarGeneralProjectAliases<T extends SidebarProjectLike>(
  projects: readonly T[]
): T[] {
  let generalIndex = -1;
  let generalProject: T | null = null;
  const result: T[] = [];

  for (const project of projects) {
    if (!isSidebarGeneralProjectName(project.name)) {
      result.push(project);
      continue;
    }

    if (!generalProject) {
      generalIndex = result.length;
      generalProject = project;
      result.push(project);
      continue;
    }

    if (hasImportedProvenance(generalProject) && !hasImportedProvenance(project)) {
      generalProject = project;
      result[generalIndex] = project;
    }
  }

  return result;
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

/* =======================================
   Canonical conversation-origin presentation
======================================= */

export type SidebarOriginOption = {
  value: ConversationOriginSystem;
  label: string;
  description: string;
  Icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
};

type SidebarOriginIconProps = {
  className?: string;
  "aria-hidden"?: boolean;
};

function createSidebarOriginIcon(
  name: string,
  src: string
): ComponentType<SidebarOriginIconProps> {
  const Icon = ({ className, "aria-hidden": ariaHidden }: SidebarOriginIconProps) =>
    React.createElement(SourceLogoImage, {
      src,
      alt: "",
      className,
      "aria-hidden": ariaHidden ?? true,
    });

  Icon.displayName = `${name}SidebarOriginIcon`;

  return Icon;
}

/** Fixed UI choices. These are not derived from project-local metadata. */
export const SIDEBAR_ORIGIN_OPTIONS: SidebarOriginOption[] = [
  {
    value: "codexify",
    label: "Codexify",
    description: "Show all Codexify-origin conversations",
    Icon: createSidebarOriginIcon("Codexify", codexifyMarkSrc),
  },
  {
    value: "openai",
    label: "ChatGPT",
    description: "Show all ChatGPT-origin conversations",
    Icon: createSidebarOriginIcon("ChatGPT", openaiOfficialSrc),
  },
  {
    value: "anthropic",
    label: "Claude",
    description: "Show all Claude-origin conversations",
    Icon: createSidebarOriginIcon("Claude", anthropicOfficialSrc),
  },
];
