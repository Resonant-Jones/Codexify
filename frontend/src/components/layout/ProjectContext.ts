import React from "react";

export type Project = { id: string; name: string; color?: string; icon?: string };

export const ProjectContext = React.createContext<{
  projectId: string | null;
  setProjectId: (id: string | null) => void;
}>({ projectId: null, setProjectId: () => {} });
