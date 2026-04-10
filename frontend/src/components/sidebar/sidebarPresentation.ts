import * as React from "react";
import type { ComponentType } from "react";
import type { Project } from "@/types/common";
import type { Thread } from "@/types/ui";
import SourceLogoImage from "./icons/SourceLogoImage";
import openaiOfficialSrc from "@/assets/brands/openai/openai-official.png";
import googleOfficialSrc from "@/assets/brands/google/google-official.png";
import codexifyMarkSrc from "@/assets/brands/codexify/codexify-mark.png";

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
    const match = trimmed.match(new RegExp(`^${provider}\\s*[-–—:|/]\\s*`, "i"));
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
  const candidates = projects.filter((project) => isSidebarGeneralProjectName(project.name));

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
  description?: string;
  Icon?: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
};

const CANONICAL_PROVENANCE_LABELS = new Map<string, string>([
  ["chatgpt", "ChatGPT"],
  ["openai", "OpenAI"],
  ["claude", "Claude"],
  ["anthropic", "Anthropic"],
  ["gemini", "Gemini"],
  ["perplexity", "Perplexity"],
]);

const CANONICAL_PROVENANCE_KEY_ALIASES = new Map<string, string>([
  ["chatgpt-import", "chatgpt"],
  ["chat-gpt", "chatgpt"],
  ["imported-from-chatgpt", "chatgpt"],
  ["chatgpt-imported", "chatgpt"],
  ["open-ai", "openai"],
]);

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function normalizeLookupKey(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function formatSidebarProvenanceLabel(key: string): string {
  const canonical = CANONICAL_PROVENANCE_LABELS.get(key);
  if (canonical) return canonical;

  return key
    .split("-")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

type SidebarProvenanceDescriptor = {
  key: string;
  label: string;
};

type SidebarProvenanceIconProps = {
  className?: string;
  "aria-hidden"?: boolean;
};

function createSidebarProvenanceIcon(
  name: string,
  src: string
): ComponentType<SidebarProvenanceIconProps> {
  const Icon = ({ className, "aria-hidden": ariaHidden }: SidebarProvenanceIconProps) =>
    React.createElement(SourceLogoImage, {
      src,
      alt: "",
      className,
      "aria-hidden": ariaHidden ?? true,
    });

  Icon.displayName = `${name}SidebarProvenanceIcon`;

  return Icon;
}

const SIDEBAR_PROVENANCE_ICONS: Record<string, ComponentType<SidebarProvenanceIconProps>> = {
  chatgpt: createSidebarProvenanceIcon("ChatGPT", openaiOfficialSrc),
  openai: createSidebarProvenanceIcon("OpenAI", openaiOfficialSrc),
  gemini: createSidebarProvenanceIcon("Gemini", googleOfficialSrc),
  codexify: createSidebarProvenanceIcon("Codexify", codexifyMarkSrc),
};

function resolveSidebarProvenanceIcon(key: string): ComponentType<SidebarProvenanceIconProps> | null {
  return SIDEBAR_PROVENANCE_ICONS[key] ?? null;
}

export function normalizeSidebarProvenanceKey(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = normalizeLookupKey(value);
  if (!normalized) return null;
  const alias = CANONICAL_PROVENANCE_KEY_ALIASES.get(normalized);
  if (alias) return alias;
  if (normalized.includes("chatgpt")) return "chatgpt";
  if (normalized.includes("openai")) return "openai";
  return normalized;
}

function resolveSidebarProvenanceDescriptor(
  value: unknown
): SidebarProvenanceDescriptor | null {
  const key = normalizeSidebarProvenanceKey(value);
  if (!key) return null;
  return {
    key,
    label: formatSidebarProvenanceLabel(key),
  };
}

export function normalizeSidebarProvenanceLabel(value: unknown): string | null {
  return resolveSidebarProvenanceDescriptor(value)?.label ?? null;
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

function resolveThreadProvenanceDescriptor(
  thread: Thread
): SidebarProvenanceDescriptor | null {
  for (const candidate of readThreadProvenanceCandidates(thread)) {
    const descriptor = resolveSidebarProvenanceDescriptor(candidate);
    if (descriptor) return descriptor;
  }
  return null;
}

export function getSidebarThreadProvenanceKey(thread: Thread): string | null {
  return resolveThreadProvenanceDescriptor(thread)?.key ?? null;
}

export function getSidebarThreadProvenanceLabel(thread: Thread): string | null {
  return resolveThreadProvenanceDescriptor(thread)?.label ?? null;
}

export function collectSidebarProvenanceOptions(
  threads: Thread[]
): SidebarProvenanceOption[] {
  const seen = new Set<string>();
  const options: SidebarProvenanceOption[] = [];

  for (const thread of threads) {
    const descriptor = resolveThreadProvenanceDescriptor(thread);
    if (!descriptor || seen.has(descriptor.key)) continue;
    seen.add(descriptor.key);
    const Icon = resolveSidebarProvenanceIcon(descriptor.key);
    options.push(
      Icon
        ? { value: descriptor.key, label: descriptor.label, Icon }
        : { value: descriptor.key, label: descriptor.label }
    );
  }

  return options;
}

export function threadMatchesSidebarProvenance(
  thread: Thread,
  selectedProvenance: string | null
): boolean {
  if (!selectedProvenance) return true;
  return getSidebarThreadProvenanceKey(thread) === selectedProvenance;
}
