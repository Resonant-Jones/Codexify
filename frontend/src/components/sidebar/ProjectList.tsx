import * as React from "react";
import clsx from "clsx";
import { FolderOpen, PlusCircle } from "lucide-react";
import type { Project } from "@/types/common";

type Props = {
  projects: Project[];
  search: string;
  looseCount: number;
  currentId: string | null;
  onPick: (id: string | null) => void;
  onOpenNewProject?: () => void;
  className?: string;
};

export default function ProjectList({
  projects,
  search,
  looseCount,
  currentId,
  onPick,
  onOpenNewProject,
  className,
}: Props) {
  const query = search.toLowerCase();
  const filtered = query ? projects.filter((p) => p.name.toLowerCase().includes(query)) : projects;

  return (
    <div className={clsx("flex-1 min-h-0 overflow-auto pt-[5px]", className)}>
      <div className="grid auto-rows-[minmax(140px,auto)] grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        <ProjectTileCard
          key="__loose"
          label={`Loose threads${looseCount ? ` (${looseCount})` : ""}`}
          icon={<FolderOpen className="h-6 w-6" />}
          active={currentId === null}
          onClick={() => onPick(null)}
        />
        {filtered.map((p) => (
          <ProjectTileCard
            key={p.id}
            label={p.name}
            icon={p.icon}
            active={currentId === String(p.id)}
            onClick={() => onPick(String(p.id))}
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
}: {
  label: string;
  icon?: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
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
    <button
      type="button"
      onClick={onClick}
      className={clsx("project-tile", active && "project-tile--active")}
      aria-pressed={active}
    >
      {iconNode}
      <span className="project-tile__label">{label}</span>
    </button>
  );
}
