/**
 * DocumentLike
 *
 * Shared document metadata used across the workspace and document views,
 * including optional media URLs for previewing uploaded files.
 */
export type DocumentLike = {
  id?: string;
  name?: string;
  title: string;
  ext: string;
  type: "file" | "codex_entry";
  src_url?: string;
  srcUrl?: string;
  src?: string;
  url?: string;
  projectId?: number;
  project_id?: number;
  threadId?: number | null;
  thread_id?: number | null;
  createdAt?: string;
  embeddingStatus?: string;
  embeddingError?: string;
  embeddingStartedAt?: string;
  embeddingCompletedAt?: string;
  mock?: boolean;
};
