import React from "react";

interface SidebarProps {
  threads: any[];
  activeId: string | null;
  scopeLabel: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  creatingThread?: boolean;
  onDeleteThread?: (threadId: string) => void;
}

const NavItem: React.FC<{ label: string }> = ({ label }) => (
  <button className="w-full text-left px-3 py-2 rounded-md hover:bg-white/5">
    {label}
  </button>
);

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeId,
  scopeLabel,
  onSelect,
  onNewChat,
  creatingThread,
  onDeleteThread,
}) => {
  return (
    <aside className="hidden md:flex md:flex-col w-56 shrink-0 border-r border-white/10 bg-[var(--color-surface)] h-full p-3 gap-2">
      <div className="text-xs uppercase tracking-wide text-[var(--color-muted)] px-2">Navigation</div>
      <NavItem label="Dashboard" />
      <NavItem label="Threads" />
      <NavItem label="Memory" />
      <NavItem label="Research" />
      <NavItem label="Settings" />
      <div className="mt-auto text-[var(--color-muted)] text-xs px-2">v0.1.0</div>
    </aside>
  );
};
