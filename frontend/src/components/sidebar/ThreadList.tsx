import * as React from "react";
import clsx from "clsx";
import {
  ChevronDown,
  Plus,
  MoreVertical,
  Pencil,
  Archive as ArchiveIcon,
  ArchiveRestore,
  Trash2,
  Loader2,
} from "lucide-react";
import type { ThreadAction } from "@/types/common";
import type { Thread } from "@/types/ui";
import TileShell from "@/components/surface/TileShell";
import type { SidebarProvenanceOption } from "./sidebarPresentation";

type ThreadListProps = {
  threads: Thread[];
  activeId: string | null;
  scopeLabel: string;
  provenanceFilter?: string | null;
  provenanceOptions?: SidebarProvenanceOption[];
  onProvenanceFilterChange?: (sourceKey: string | null) => void;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onRename: (threadId: string, title: string) => Promise<void>;
  onArchiveToggle: (threadId: string, archived: boolean) => Promise<void>;
  onDelete: (threadId: string) => Promise<void>;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  onLoadMore?: () => void | Promise<void>;
  creatingThread?: boolean;
  className?: string;
};

function getComputedStyleVar(name: string, fallback = ""): string {
  try {
    const win: any = typeof window !== "undefined" ? window : null;
    const doc: any = typeof document !== "undefined" ? document : null;
    if (!win || !doc) return fallback;
    const el = doc.documentElement as Element | null;
    if (!el || typeof win.getComputedStyle !== "function") return fallback;
    const val = win.getComputedStyle(el).getPropertyValue(name);
    return (val && typeof val === "string" ? val.trim() : "") || fallback;
  } catch {
    return fallback;
  }
}

function colorStringToRgba(input: string, alpha: number, fallback: string): string {
  const value = (input || "").trim();
  const hex = value.match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const raw = hex[1].length === 3
      ? hex[1].split("").map((c) => c + c).join("")
      : hex[1];
    const r = parseInt(raw.slice(0, 2), 16);
    const g = parseInt(raw.slice(2, 4), 16);
    const b = parseInt(raw.slice(4, 6), 16);
    if ([r, g, b].every((n) => Number.isFinite(n))) {
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
  }
  const rgb = value.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (rgb) {
    const [, r, g, b] = rgb;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return fallback;
}

export default function ThreadList({
  threads,
  activeId,
  scopeLabel,
  provenanceFilter = null,
  provenanceOptions = [],
  onProvenanceFilterChange,
  onSelect,
  onNewChat,
  onRename,
  onArchiveToggle,
  onDelete,
  hasMore = false,
  isLoadingMore = false,
  onLoadMore,
  creatingThread,
  className,
}: ThreadListProps) {
  return (
    <ThreadPreviewList
      threads={threads}
      activeId={activeId}
      onSelect={onSelect}
      className={className}
      rectH={60}
      showHeader
      scopeLabel={scopeLabel}
      provenanceFilter={provenanceFilter}
      provenanceOptions={provenanceOptions}
      onProvenanceFilterChange={onProvenanceFilterChange}
      onNewChat={onNewChat}
      onRename={onRename}
      onArchiveToggle={onArchiveToggle}
      onDelete={onDelete}
      hasMore={hasMore}
      isLoadingMore={isLoadingMore}
      onLoadMore={onLoadMore}
      creatingThread={creatingThread}
    />
  );
}

function ThreadPreviewList({
  threads,
  activeId,
  onSelect,
  className,
  rectH = 60,
  showHeader = false,
  scopeLabel,
  provenanceFilter = null,
  provenanceOptions = [],
  onProvenanceFilterChange,
  onNewChat,
  onRename,
  onArchiveToggle,
  onDelete,
  hasMore = false,
  isLoadingMore = false,
  onLoadMore,
}: {
  threads: Thread[];
  activeId: string | null;
  onSelect: (id: string) => void;
  className?: string;
  rectH?: number;
  showHeader?: boolean;
  scopeLabel?: string;
  provenanceFilter?: string | null;
  provenanceOptions?: SidebarProvenanceOption[];
  onProvenanceFilterChange?: (sourceKey: string | null) => void;
  onNewChat?: () => void;
  onRename: (threadId: string, title: string) => Promise<void>;
  onArchiveToggle: (threadId: string, archived: boolean) => Promise<void>;
  onDelete: (threadId: string) => Promise<void>;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  onLoadMore?: () => void | Promise<void>;
}) {
  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const isDarkMode =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark");

  const maybeLoadMore = React.useCallback(() => {
    if (!onLoadMore || !hasMore || isLoadingMore) return;
    const el = scrollRef.current;
    if (!el) return;
    const remaining = el.scrollHeight - (el.scrollTop + el.clientHeight);
    if (remaining <= 160) {
      void onLoadMore();
    }
  }, [hasMore, isLoadingMore, onLoadMore]);

  React.useEffect(() => {
    maybeLoadMore();
  }, [threads.length, maybeLoadMore]);

  return (
    <div
      ref={scrollRef}
      className={clsx("flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden", className)}
      onScroll={maybeLoadMore}
    >
      {showHeader && (
        <div className="flex items-center justify-between pb-2">
          <div className="inline-flex items-center gap-1 text-xs opacity-70">
            <ChevronDown className="h-3 w-3" /> <span>Project:</span>{" "}
            <span className="font-medium">{scopeLabel ?? "—"}</span>
          </div>
          {onNewChat && (
            <button type="button" className="icon-inline" onClick={onNewChat}>
              <Plus className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
      {showHeader && onProvenanceFilterChange && provenanceOptions.length > 0 && (
        <div className="pb-2 px-3 min-w-0">
          <div
            className="glass-pill flex w-full max-w-full min-w-0 overflow-hidden px-1 py-1"
            role="toolbar"
            aria-label="Imported source filter"
          >
            <span className="shrink-0 pl-2 pr-1 text-[11px] uppercase tracking-[0.16em] opacity-60">
              Source
            </span>
            <button
              type="button"
              className="pill-tab shrink-0 text-[11px]"
              data-state={!provenanceFilter ? "active" : undefined}
              aria-pressed={!provenanceFilter}
              onClick={() => onProvenanceFilterChange(null)}
            >
              All
            </button>
            <div className="min-w-0 flex-1 overflow-x-auto overflow-y-hidden">
              <div className="flex min-w-max items-center gap-1.5 pr-1">
                {provenanceOptions.map((option) => {
                  const active = provenanceFilter === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      className="pill-tab shrink-0 text-[11px]"
                      data-state={active ? "active" : undefined}
                      aria-pressed={active}
                      onClick={() => onProvenanceFilterChange(option.value)}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="space-y-2">
        {threads.map((t) => (
          <ThreadTileRow
            key={`t:${String(t.id)}`}
            thread={t}
            active={t.id === activeId}
            isDarkMode={isDarkMode}
            onSelect={onSelect}
            rectH={rectH}
            onRename={onRename}
            onArchiveToggle={onArchiveToggle}
            onDelete={onDelete}
          />
        ))}
      </div>
      {isLoadingMore && (
        <div className="flex items-center justify-center py-3 opacity-70 text-xs">
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          Loading more threads...
        </div>
      )}
    </div>
  );
}

function ThreadTileRow({
  thread,
  active,
  isDarkMode,
  onSelect,
  rectH = 60,
  className,
  onRename,
  onArchiveToggle,
  onDelete,
}: {
  thread: Thread;
  active: boolean;
  isDarkMode: boolean;
  onSelect: (id: string) => void;
  rectH?: number;
  className?: string;
  onRename: (threadId: string, title: string) => Promise<void>;
  onArchiveToggle: (threadId: string, archived: boolean) => Promise<void>;
  onDelete: (threadId: string) => Promise<void>;
}) {
  const [menuOpen, setMenuOpen] = React.useState(false);
  const [actionBusy, setActionBusy] = React.useState<ThreadAction | null>(null);
  const [hoveredAction, setHoveredAction] = React.useState<ThreadAction | null>(null);
  const menuRef = React.useRef<HTMLDivElement | null>(null);
  const kebabRef = React.useRef<HTMLButtonElement | null>(null);

  const accentColor = React.useMemo(() => getComputedStyleVar("--accent", "#6B7280"), []);
  const textColor = React.useMemo(() => getComputedStyleVar("--text", "#F9FAFB"), []);
  const highlightBg = React.useMemo(
    () => colorStringToRgba(accentColor, 0.18, "rgba(107,114,128,0.18)"),
    [accentColor]
  );
  const highlightBorder = React.useMemo(
    () => colorStringToRgba(accentColor, 0.45, "rgba(107,114,128,0.45)"),
    [accentColor]
  );
  const darkTileBackground = "var(--panel-sheet)";
  const darkActiveBackground =
    "color-mix(in oklab, var(--accent) 16%, var(--panel-sheet) 84%)";

  const makeMenuStyle = React.useCallback(
    (action: ThreadAction) => {
      const activeState = hoveredAction === action || actionBusy === action;
      return {
        color: activeState ? accentColor : textColor,
        background: activeState ? highlightBg : "transparent",
        borderColor: activeState ? highlightBorder : "transparent",
      } as React.CSSProperties;
    },
    [accentColor, actionBusy, highlightBg, highlightBorder, hoveredAction, textColor]
  );

  React.useEffect(() => {
    function handleDocMouseDown(e: MouseEvent) {
      if (!menuOpen) return;
      const t = e.target as Node;
      if (menuRef.current?.contains(t)) return;
      if (kebabRef.current?.contains(t)) return;
      setMenuOpen(false);
      setHoveredAction(null);
    }
    function handleEsc(e: KeyboardEvent) {
      if (!menuOpen) return;
      if (e.key === "Escape") {
        setMenuOpen(false);
        setHoveredAction(null);
      }
    }
    document.addEventListener("mousedown", handleDocMouseDown);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleDocMouseDown);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [menuOpen]);

  const stop = React.useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    return Boolean(actionBusy);
  }, [actionBusy]);

  const handleRename = React.useCallback(async (e: React.MouseEvent) => {
    if (stop(e)) return;
    const next = window.prompt("Rename thread", thread.title?.trim() || "");
    const title = next?.trim();
    if (!title || title === thread.title) {
      setMenuOpen(false);
      setHoveredAction(null);
      return;
    }
    setHoveredAction("rename");
    setActionBusy("rename");
    try {
      await onRename(thread.id, title);
    } catch (err) {
      console.error("rename failed", err);
    } finally {
      setActionBusy(null);
      setMenuOpen(false);
      setHoveredAction(null);
    }
  }, [onRename, stop, thread.id, thread.title]);

  const handleArchiveToggle = React.useCallback(async (e: React.MouseEvent) => {
    if (stop(e)) return;
    const isArchived = Boolean(thread.archivedAt);
    setHoveredAction("archive");
    setActionBusy("archive");
    try {
      await onArchiveToggle(thread.id, !isArchived);
    } catch (err) {
      console.error("archive toggle failed", err);
    } finally {
      setActionBusy(null);
      setMenuOpen(false);
      setHoveredAction(null);
    }
  }, [onArchiveToggle, stop, thread.archivedAt, thread.id]);

  const handleDelete = React.useCallback(async (e: React.MouseEvent) => {
    if (stop(e)) return;
    const ok = window.confirm("Delete this thread and its messages? This cannot be undone.");
    if (!ok) {
      setMenuOpen(false);
      setHoveredAction(null);
      return;
    }
    setHoveredAction("delete");
    setActionBusy("delete");
    try {
      await onDelete(thread.id);
    } catch (err) {
      console.error("delete failed", err);
    } finally {
      setActionBusy(null);
      setMenuOpen(false);
      setHoveredAction(null);
    }
  }, [onDelete, stop, thread.id]);

  const threadIsArchived = Boolean(thread.archivedAt);

  const renameIcon = actionBusy === "rename"
    ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    : <Pencil className="h-4 w-4" aria-hidden="true" />;

  const archiveIconNode = actionBusy === "archive"
    ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    : threadIsArchived
      ? <ArchiveRestore className="h-4 w-4" aria-hidden="true" />
      : <ArchiveIcon className="h-4 w-4" aria-hidden="true" />;

  const deleteIcon = actionBusy === "delete"
    ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
    : <Trash2 className="h-4 w-4" aria-hidden="true" />;

  const safeTitle = (thread.title || "").trim() || "Untitled";
  const titleNode = <span key="title" className="thread-title block truncate" title={safeTitle}>{safeTitle}</span>;
  const snippet = typeof thread.lastMessage === "string" ? thread.lastMessage.trim() : "";
  const snippetNode = (
    <span
      key="snippet"
      className="thread-snippet block truncate"
      title={snippet || undefined}
    >
      {snippet || "\u00a0"}
    </span>
  );
  const unreadBadge =
    thread.unread > 0 ? (
      <span
        key="badge"
        className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-2 text-xs font-semibold"
        style={{ background: "var(--accent-strong)", color: "#fff" }}
      >
        {thread.unread}
      </span>
    ) : null;

  const tileStyle: React.CSSProperties = { minHeight: rectH };
  if (active) {
    tileStyle.background = isDarkMode ? darkActiveBackground : highlightBg;
  } else if (isDarkMode) {
    tileStyle.background = darkTileBackground;
  }

  return (
    <div className={clsx("relative", className)}>
      <TileShell
        as="button"
        type="button"
        onClick={() => onSelect(thread.id)}
        data-testid={`thread-tile-${thread.id}`}
        className="thread-preview w-full text-left text-[var(--text)] transition-transform duration-150 ease-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] dark:text-white"
        borderColor={active ? highlightBorder : undefined}
        style={tileStyle}
      >
        <div className="flex h-full w-full items-center gap-3 px-3 py-2">
          <div className="flex min-w-0 flex-1 flex-col gap-[2px]">
            {titleNode}
            {snippetNode}
          </div>
          {unreadBadge}
        </div>
      </TileShell>

      <div className="absolute top-1 right-1">
        <button
          ref={kebabRef}
          className="icon-inline rounded-[var(--radius-micro)]"
          aria-label="Thread actions"
          onClick={(e) => { if (stop(e)) return; setMenuOpen(true); setHoveredAction(null); }}
          onMouseDown={(e) => stop(e)}
          type="button"
          aria-busy={actionBusy ? true : undefined}
        >
          <MoreVertical className="h-4 w-4" />
        </button>
      </div>

      {menuOpen && (
        <div
          ref={menuRef}
          role="menu"
          tabIndex={-1}
          className="absolute z-[9999] right-1 top-9 min-w-[180px] rounded-[var(--tile-radius)] border p-1 shadow-xl pointer-events-auto backdrop-blur-sm"
          style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm border transition-colors transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98] disabled:cursor-not-allowed"
            style={makeMenuStyle("rename")}
            onMouseDown={(e) => e.stopPropagation()}
            onMouseEnter={() => setHoveredAction("rename")}
            onMouseLeave={() => setHoveredAction((prev: ThreadAction | null) => (prev === "rename" ? null : prev))}
            onFocus={() => setHoveredAction("rename")}
            onBlur={() => setHoveredAction((prev: ThreadAction | null) => (prev === "rename" ? null : prev))}
            onClick={handleRename}
            disabled={Boolean(actionBusy)}
          >
            {renameIcon}
            Rename
          </button>
          <button
            type="button"
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm border transition-colors transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98] disabled:cursor-not-allowed"
            style={makeMenuStyle("archive")}
            onMouseDown={(e) => e.stopPropagation()}
            onMouseEnter={() => setHoveredAction("archive")}
            onMouseLeave={() => setHoveredAction((prev: ThreadAction | null) => (prev === "archive" ? null : prev))}
            onFocus={() => setHoveredAction("archive")}
            onBlur={() => setHoveredAction((prev: ThreadAction | null) => (prev === "archive" ? null : prev))}
            onClick={handleArchiveToggle}
            disabled={Boolean(actionBusy)}
          >
            {archiveIconNode}
            {threadIsArchived ? "Unarchive" : "Archive"}
          </button>
          <button
            type="button"
            className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm border transition-colors transition-transform duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98] disabled:cursor-not-allowed"
            style={makeMenuStyle("delete")}
            onMouseDown={(e) => e.stopPropagation()}
            onMouseEnter={() => setHoveredAction("delete")}
            onMouseLeave={() => setHoveredAction((prev: ThreadAction | null) => (prev === "delete" ? null : prev))}
            onFocus={() => setHoveredAction("delete")}
            onBlur={() => setHoveredAction((prev: ThreadAction | null) => (prev === "delete" ? null : prev))}
            onClick={handleDelete}
            disabled={Boolean(actionBusy)}
          >
            {deleteIcon}
            Delete…
          </button>
        </div>
      )}
    </div>
  );
}
