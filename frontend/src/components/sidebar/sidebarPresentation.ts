import type { Thread } from "@/types/ui";

type ProjectLike = {
  id: string | number;
  name?: unknown;
};

type ThreadLike = Pick<Thread, "title" | "metadata">;

export type ProjectPresentation = {
  label: string;
  badge: string | null;
  rawName: string;
  isFallback: boolean;
};

export type ThreadPresentation = {
  label: string;
  badge: string | null;
  rawTitle: string;
};

const GENERAL_LIKE_NAMES = new Set(["general", "loose threads", "imports"]);

const CHATGPT_PREFIX_PATTERNS = [
  /^(?:imported from\s+)?chatgpt(?:[\s:–—-]+|\s+)/i,
  /^(?:chatgpt|imported from chatgpt)\s*[\-:–—()]+\s*/i,
];

function normalizeName(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

export function isGeneralLikeProjectName(value: unknown): boolean {
  return GENERAL_LIKE_NAMES.has(normalizeName(value));
}

export function pickCanonicalGeneralProject<T extends ProjectLike>(
  projects: T[]
): T | null {
  if (!Array.isArray(projects) || projects.length === 0) {
    return null;
  }

  const preferredNames = ["general", "loose threads", "imports"];
  for (const preferredName of preferredNames) {
    const match = projects.find(
      (project) => normalizeName(project?.name) === preferredName
    );
    if (match) return match;
  }

  return projects.find((project) => isGeneralLikeProjectName(project?.name)) ?? null;
}

function stripChatGptPrefix(rawTitle: string): string {
  let next = rawTitle.trim();
  for (const pattern of CHATGPT_PREFIX_PATTERNS) {
    const stripped = next.replace(pattern, "").trim();
    if (stripped !== next) {
      next = stripped;
    }
  }
  return next || rawTitle.trim();
}

function normalizeMetadata(metadata: unknown): Record<string, unknown> | null {
  return metadata && typeof metadata === "object"
    ? (metadata as Record<string, unknown>)
    : null;
}

function getImportedProvenanceLabel(
  metadata: Record<string, unknown> | null,
  rawTitle: string
): string | null {
  const importSource = normalizeName(
    metadata?.import_source ?? metadata?.source ?? metadata?.origin
  );
  const hasChatGptMetadata =
    importSource.includes("chatgpt") ||
    metadata?.source_thread_id != null ||
    metadata?.source_conversation_template_id != null ||
    metadata?.source_gizmo_id != null ||
    metadata?.source_gizmo_type != null;

  if (hasChatGptMetadata) {
    return "ChatGPT";
  }

  return CHATGPT_PREFIX_PATTERNS.some((pattern) => pattern.test(rawTitle))
    ? "ChatGPT"
    : null;
}

export function getProjectPresentation(name: unknown): ProjectPresentation {
  const rawName = String(name ?? "").trim() || "Untitled";
  const normalized = normalizeName(rawName);

  if (GENERAL_LIKE_NAMES.has(normalized)) {
    return {
      label: "General",
      badge: normalized === "imports" ? "Imported" : normalized === "loose threads" ? "Legacy" : null,
      rawName,
      isFallback: true,
    };
  }

  const stripped = stripChatGptPrefix(rawName);
  return {
    label: stripped || rawName,
    badge: stripped !== rawName ? "ChatGPT" : null,
    rawName,
    isFallback: false,
  };
}

export function getThreadPresentation(thread: ThreadLike): ThreadPresentation {
  const rawTitle = String(thread?.title ?? "").trim() || "Untitled";
  const metadata = normalizeMetadata(thread?.metadata);
  const provenanceLabel = getImportedProvenanceLabel(metadata, rawTitle);
  const label = stripChatGptPrefix(rawTitle);

  return {
    label: label || "Untitled",
    badge: provenanceLabel,
    rawTitle,
  };
}
