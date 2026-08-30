import * as React from "react";
import clsx from "clsx";
import {
  Archive,
  FolderOpen,
  Loader2,
  MoreVertical,
  Pencil,
  PlusCircle,
  RotateCcw,
  Trash2,
} from "lucide-react";
import type { Project } from "@/types/common";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  cleanSidebarProjectTitle,
  isSidebarBuiltInProject,
  normalizeSidebarProjects,
  projectMatchesSidebarQuery,
} from "./sidebarPresentation";

type ProjectAction = "rename" | "archive" | "restore" | "delete";

type Props = {
  projects: Project[];
  search: string;
  currentId: string | null;
  onPick: (id: string | null) => void;
  onOpenNewProject?: () => void;
  onRenameProject?: (id: string, name: string) => Promise<void> | void;
  onArchiveProject?: (id: string) => Promise<void> | void;
  onRestoreProject?: (id: string) => Promise<void> | void;
  onDeleteProject?: (id: string) => Promise<void> | void;
  className?: string;
};

export default function ProjectList({
  projects,
  search,
  currentId,
  onPick,
  onOpenNewProject,
  onRenameProject,
  onArchiveProject,
  onRestoreProject,
  onDeleteProject,
  className,
}: Props) {
  const [pending, setPending] = React.useState<{
    id: string;
    action: ProjectAction;
  } | null>(null);
  const query = search.toLowerCase();
  const visibleProjects = React.useMemo(
    () => normalizeSidebarProjects(projects),
    [projects]
  );
  const filtered = query
    ? visibleProjects.filter((project) => projectMatchesSidebarQuery(project, query))
    : visibleProjects;

  const runAction = React.useCallback(
    async (project: Project, action: ProjectAction) => {
      const projectId = String(project.id);
      const projectName = cleanSidebarProjectTitle(project) || "this project";
      let operation: Promise<void> | void;

      if (action === "rename") {
        if (!onRenameProject) return;
        const nextName = window.prompt("Rename Project", projectName)?.trim();
        if (!nextName || nextName === projectName) return;
        operation = onRenameProject(projectId, nextName);
      } else if (action === "archive") {
        if (!onArchiveProject) return;
        operation = onArchiveProject(projectId);
      } else if (action === "restore") {
        if (!onRestoreProject) return;
        operation = onRestoreProject(projectId);
      } else {
        if (!onDeleteProject) return;
        const confirmed = window.confirm(
          `Permanently delete Project "${projectName}"? Its threads will be moved to General. This removes the local Project container, and backups are not guaranteed.`
        );
        if (!confirmed) return;
        operation = onDeleteProject(projectId);
      }

      setPending({ id: projectId, action });
      try {
        await operation;
      } finally {
        setPending((current) =>
          current?.id === projectId && current.action === action ? null : current
        );
      }
    },
    [onArchiveProject, onDeleteProject, onRenameProject, onRestoreProject]
  );

  return (
    <div className={clsx("flex-1 min-h-0 overflow-auto pt-[5px]", className)}>
      <div className="flex flex-col gap-2">
        {filtered.map((project) => (
          <ProjectTileCard
            key={project.id}
            project={project}
            active={currentId === String(project.id)}
            onClick={() => onPick(String(project.id))}
            onAction={(action) => void runAction(project, action)}
            pendingAction={
              pending?.id === String(project.id) ? pending.action : null
            }
            enabledActions={{
              rename: Boolean(onRenameProject),
              archive: Boolean(onArchiveProject),
              restore: Boolean(onRestoreProject),
              delete: Boolean(onDeleteProject),
            }}
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
  project,
  active,
  onClick,
  onAction,
  pendingAction,
  enabledActions,
}: {
  project: Project;
  active?: boolean;
  onClick?: () => void;
  onAction: (action: ProjectAction) => void;
  pendingAction: ProjectAction | null;
  enabledActions: Record<ProjectAction, boolean>;
}) {
  const [menuOpen, setMenuOpen] = React.useState(false);
  const label = cleanSidebarProjectTitle(project);
  const archived = Boolean(project.archivedAt);
  const builtIn = isSidebarBuiltInProject(project);
  const baseIcon = typeof project.icon === "string" && project.icon.trim().length <= 2
    ? project.icon.trim()
    : project.icon || <FolderOpen className="h-6 w-6" />;
  const iconElement = React.isValidElement(baseIcon)
    ? (baseIcon as React.ReactElement<{ className?: string }>)
    : null;
  const iconNode = iconElement
    ? React.cloneElement(iconElement, {
        className: clsx("project-tile__icon", iconElement.props.className),
      })
    : <span className="project-tile__icon">{baseIcon}</span>;
  const hasActions = enabledActions.rename
    || (!builtIn && archived && (enabledActions.restore || enabledActions.delete))
    || (!builtIn && !archived && enabledActions.archive);

  const choose = (action: ProjectAction) => {
    setMenuOpen(false);
    onAction(action);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={onClick}
        className={clsx(
          "project-tile focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]",
          "w-full min-h-[60px] pr-10",
          active && "project-tile--active",
          archived && "opacity-70"
        )}
        aria-pressed={active}
      >
        {iconNode}
        <span className="project-tile__label" title={label}>
          {label}
          {archived ? <span className="ml-2 text-[10px] uppercase">Archived</span> : null}
        </span>
      </button>
      {hasActions ? (
        <div className="absolute right-2 top-2">
          <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
            <DropdownMenuTrigger
              aria-label={`Project actions for ${label}`}
              title={`Project actions for ${label}`}
              className="icon-inline rounded-[var(--radius-micro)]"
              disabled={Boolean(pendingAction)}
              onClick={(event) => {
                event.stopPropagation();
              }}
            >
              {pendingAction ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <MoreVertical className="h-4 w-4" />
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={4} collisionPadding={8}>
              {enabledActions.rename ? (
                <DropdownMenuItem onClick={() => choose("rename")} disabled={Boolean(pendingAction)}>
                  <Pencil className="mr-2 inline h-4 w-4" /> Rename
                </DropdownMenuItem>
              ) : null}
              {!builtIn && !archived && enabledActions.archive ? (
                <DropdownMenuItem onClick={() => choose("archive")} disabled={Boolean(pendingAction)}>
                  <Archive className="mr-2 inline h-4 w-4" /> Archive
                </DropdownMenuItem>
              ) : null}
              {!builtIn && archived && enabledActions.restore ? (
                <DropdownMenuItem onClick={() => choose("restore")} disabled={Boolean(pendingAction)}>
                  <RotateCcw className="mr-2 inline h-4 w-4" /> Restore
                </DropdownMenuItem>
              ) : null}
              {!builtIn && archived && enabledActions.delete ? (
                <DropdownMenuItem
                  className="text-[var(--danger)]"
                  onClick={() => choose("delete")}
                  disabled={Boolean(pendingAction)}
                >
                  <Trash2 className="mr-2 inline h-4 w-4" /> Delete permanently
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ) : null}
    </div>
  );
}
