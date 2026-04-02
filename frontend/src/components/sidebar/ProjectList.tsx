import * as React from "react";
import clsx from "clsx";
import { FolderOpen, Loader2, PlusCircle, Trash2 } from "lucide-react";
import type { Project } from "@/types/common";

type Props = {
  projects: Project[];
  search: string;
  currentId: string | null;
  onPick: (id: string | null) => void;
  onOpenNewProject?: () => void;
  onDeleteProject?: (id: string) => Promise<void> | void;
  className?: string;
};

export default function ProjectList({
  projects,
  search,
  currentId,
  onPick,
  onOpenNewProject,
  onDeleteProject,
  className,
}: Props) {
  const [deletingProjectId, setDeletingProjectId] = React.useState<string | null>(null);
  const query = search.toLowerCase();
  const filtered = query ? projects.filter((p) => p.name.toLowerCase().includes(query)) : projects;
  const handleDeleteProject = React.useCallback(
    async (project: Project) => {
      if (!onDeleteProject) return;
      const projectId = String(project.id);
      const projectName = String(project.name || "").trim() || "this project";
      const confirmed = window.confirm(
        `Delete project "${projectName}"? This will remove the project and unassign its threads.`
      );
      if (!confirmed) return;
      setDeletingProjectId(projectId);
      try {
        await onDeleteProject(projectId);
      } finally {
        setDeletingProjectId((current) => (current === projectId ? null : current));
      }
    },
    [onDeleteProject]
  );

  return (
    <div className={clsx("flex-1 min-h-0 overflow-auto pt-[5px]", className)}>
      <div className="flex flex-col gap-2">
        {filtered.map((p) => (
          <ProjectTileCard
            key={p.id}
            label={p.name}
            icon={p.icon}
            active={currentId === String(p.id)}
            onClick={() => onPick(String(p.id))}
            onDelete={onDeleteProject ? () => void handleDeleteProject(p) : undefined}
            deleting={deletingProjectId === String(p.id)}
          />
        ))}
      </div>
      {onOpenNewProject && (
        <button
          type="button"
          className="embedded-btn mt-4 w-full justify-center gap-2"
          onClick={onOpenNewProject}
        >
          <PlusCircle className="h-4 w-4" /> New Project
        </button>
      )}
    </div>
  );
}

function ProjectTileCard({
  label,
  icon,
  active,
  onClick,
  onDelete,
  deleting = false,
}: {
  label: string;
  icon?: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  onDelete?: () => void;
  deleting?: boolean;
}) {
  const baseIcon = typeof icon === "string" && icon.trim().length <= 2
    ? icon.trim()
    : icon || <FolderOpen className="h-6 w-6" />;
  const iconNode = React.isValidElement(baseIcon)
    ? React.cloneElement(baseIcon as React.ReactElement, {
        className: clsx("project-tile__icon", ((baseIcon as React.ReactElement).props as any)?.className),
      })
    : <span className="project-tile__icon">{baseIcon}</span>;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={onClick}
        className={clsx(
          "project-tile focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]",
          "w-full min-h-[60px]",
          active && "project-tile--active"
        )}
        aria-pressed={active}
      >
        {iconNode}
        <span className="project-tile__label" title={label}>{label}</span>
      </button>
      {onDelete && (
        <button
          type="button"
          aria-label={`Delete project ${label}`}
          title={`Delete project ${label}`}
          className="icon-inline absolute right-2 top-2 rounded-[var(--radius-micro)]"
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            if (deleting) return;
            onDelete();
          }}
          disabled={deleting}
        >
          {deleting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Trash2 className="h-3.5 w-3.5" />
          )}
        </button>
      )}
    </div>
  );
}
