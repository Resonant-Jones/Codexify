import * as React from "react";
import { Check, ChevronDown } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Project } from "@/types/common";
import { cleanSidebarProjectTitle } from "./sidebarPresentation";

export type ProjectScope = {
  projects: Project[];
  currentId: string | null;
  onPick: (id: string) => void;
};

export default function ProjectSwitcher({ label, scope }: { label: string; scope?: ProjectScope }) {
  const [open, setOpen] = React.useState(false);
  const menuId = React.useId();
  const trigger = React.useRef<HTMLButtonElement>(null);
  const projects = scope?.projects.filter((project) => !project.archivedAt) ?? [];
  const hasProjects = projects.length > 0;

  React.useEffect(() => {
    if (!open) return;
    if (!hasProjects) {
      setOpen(false);
      return;
    }
    // Wait for the portaled menu to be positioned and made visible before focusing it.
    const frame = window.requestAnimationFrame(() => {
      const menu = document.getElementById(menuId);
      const item = menu?.querySelector<HTMLElement>('[aria-checked="true"]')
        ?? menu?.querySelector<HTMLElement>('[role="menuitemradio"]');
      item?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [open, hasProjects, menuId]);

  const projectLabel = (
    <>
      <span className="shrink-0">Project:</span>
      <span className="truncate font-medium">{label}</span>
    </>
  );

  if (!scope || !hasProjects) {
    return <div className="inline-flex min-w-0 items-center gap-1 text-xs opacity-70">{projectLabel}</div>;
  }

  const closeAndRestoreFocus = () => {
    setOpen(false);
    trigger.current?.focus();
  };

  const handleMenuKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" || event.key === "Tab") {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
      }
      closeAndRestoreFocus();
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitemradio"]'));
    if (!items.length) return;
    event.preventDefault();
    const current = items.indexOf(document.activeElement as HTMLButtonElement);
    const last = items.length - 1;
    const next = event.key === "Home" ? 0
      : event.key === "End" ? last
      : event.key === "ArrowDown" ? (current + 1) % items.length
      : current <= 0 ? last : current - 1;
    items[next]?.focus();
  };

  return (
    <div className="min-w-0 [&>[data-ddm-root]]:max-w-full">
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild aria-controls={open ? menuId : undefined}>
          <button
            ref={trigger}
            type="button"
            className="inline-flex min-h-8 max-w-full cursor-pointer items-center gap-1 rounded-md px-1 text-xs opacity-70 hover:bg-[var(--surface-hover)] hover:opacity-100 aria-expanded:opacity-100"
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setOpen(true);
              } else if (open && event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                closeAndRestoreFocus();
              }
            }}
          >
            <ChevronDown className="h-3 w-3 shrink-0" aria-hidden="true" />
            {projectLabel}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          id={menuId}
          aria-label="Switch project"
          align="start"
          sideOffset={4}
          collisionPadding={8}
          portalContainer={open ? trigger.current?.closest<HTMLElement>('[data-testid="mobile-sidebar-drawer"]') : null}
          className="overflow-y-auto overscroll-contain border-[var(--panel-border)] text-[var(--text)]"
          style={{
            maxWidth: "min(16rem, calc(100vw - 16px))",
            maxHeight: "min(16rem, var(--dropdown-menu-available-height))",
            background: "var(--panel-sheet, var(--panel-bg))",
          }}
          onKeyDown={handleMenuKeyDown}
        >
          {projects.map((project) => {
            const id = String(project.id);
            const selected = scope.currentId === id;
            return (
              <DropdownMenuItem
                key={id}
                type="button"
                role="menuitemradio"
                aria-checked={selected}
                tabIndex={-1}
                className="flex cursor-pointer items-center justify-between gap-3 focus:bg-[var(--surface-hover)]"
                onClick={() => {
                  closeAndRestoreFocus();
                  if (!selected) scope.onPick(id);
                }}
              >
                <span className="min-w-0 break-words">{cleanSidebarProjectTitle(project)}</span>
                {selected && <Check className="h-4 w-4 shrink-0" aria-hidden="true" />}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
