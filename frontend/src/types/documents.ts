export type DocumentLike = {
  id?: string;
  name?: string;
  title: string;
  ext: string;
  type: "file" | "codex_entry";
  createdAt?: string;
  mock?: boolean;
};
