/** Enough to satisfy Sidebar & friends – flesh out later */
export interface Project {
  id: number | string;
  name: string;
  icon?: string;
  color?: string;
}

/** Actions the thread list can show in its hover toolbar */
export type ThreadAction = "rename" | "archive" | "delete";
