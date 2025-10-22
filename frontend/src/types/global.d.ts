/// <reference types="@testing-library/jest-dom" />
// global.d.ts  (inside src/)
export interface Project {
  id: string | number;
  name: string;
  icon?: string;
  color?: string;
  // add any other fields you actually use
}

export type ThreadAction = 'rename' | 'archive' | 'delete';

// Props reused in several places
export interface PreviewTileExtraProps {
  rectH?: number;
  active?: boolean;
  layer?: string;
  tone?: string;
}
