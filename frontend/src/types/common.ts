/** Enough to satisfy Sidebar & friends – flesh out later */
export interface Project {
  id: number | string;
  name: string;
  description?: string | null;
  icon?: string;
  color?: string;
  systemRole?: "general" | "imports" | null;
  archivedAt?: string | null;
}

/** Actions the thread list can show in its hover toolbar */
export type ThreadAction = "rename" | "archive" | "delete";
