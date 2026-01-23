export type DocumentLike = {
  id?: string;
  name?: string;
  title: string;
  ext: string;
  type: "file" | "codex_entry";
  createdAt?: string;
  embeddingStatus?: string;
  embeddingError?: string;
  embeddingStartedAt?: string;
  embeddingCompletedAt?: string;
  mock?: boolean;
};
