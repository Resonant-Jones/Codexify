import * as React from "react";
import clsx from "clsx";
import { FolderOpen, PlusCircle } from "lucide-react";
import type { Project } from "@/types/common";
import TileShell from "@/components/surface/TileShell";

type Props = {
  projects: Project[];
  search: string;
  currentId: string | null;
  onPick: (id: string | null) => void;
  onOpenNewProject?: () => void;
  className?: string;
};

export default function ProjectList({
  projects,
  search,
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
    <TileShell
      as="button"
      type="button"
      onClick={onClick}
      className={clsx(
        "project-tile focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)]",
        active && "project-tile--active"
      )}
      style={{
        background: "color-mix(in oklab,var(--panel-sheet,rgba(12,19,32,0.78)) 60%,transparent)",
        border: `1.5px solid ${
          active ? "color-mix(in oklab,var(--accent-strong) 55%, var(--panel-border))" : "var(--panel-border)"
        }`,
      }}
      aria-pressed={active}
    >
      {iconNode}
      <span className="project-tile__label">{label}</span>
    </TileShell>
  );
}
