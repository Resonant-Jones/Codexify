// lodash-es doesn’t ship its own .d.ts
declare module "lodash-es";

// quick domain shims – refine later
export interface Project {
  id: number;
  name: string;
  icon?: string;
  color?: string;
}

export type ThreadAction = "rename" | "archive" | "delete";
