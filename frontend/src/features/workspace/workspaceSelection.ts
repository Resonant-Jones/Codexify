export type WorkspaceMediaRecord = {
  id: string;
  src_url: string;
  filename?: string | null;
  title?: string | null;
  format?: string | null;
  artifact_type?: string | null;
  caption?: string | null;
  mime_type?: string | null;
  filesize?: number | null;
  created_at?: string | null;
  project_id?: string | number | null;
  thread_id?: string | number | null;
  source_tag?: string | null;
};

export type WorkspaceDocumentRecord = WorkspaceMediaRecord & {
  content?: string | null;
  parsed_text?: string | null;
};

export type WorkspaceImageRecord = WorkspaceMediaRecord;

export type WorkspaceSelection =
  | { kind: "document"; item: WorkspaceDocumentRecord }
  | { kind: "image"; item: WorkspaceImageRecord };

/** Normalize a backend-provided media URL and reject executable URL schemes. */
export function normalizeWorkspaceMediaUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const candidate = value.trim();
  if (!candidate) return null;

  try {
    const base = typeof window === "undefined" ? "http://workspace.local" : window.location.origin;
    const url = new URL(candidate, base);
    if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}
