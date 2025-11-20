import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Search, Plus, MoreVertical } from "lucide-react";
import { Thread } from "@/types/ui";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

const initials = (name: string) => name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();

export function Sidebar({ threads, activeId, onSelect, onNewChat }: { threads: Thread[]; activeId: string; onSelect: (id: string) => void; onNewChat: () => void }) {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => threads.filter((t) => (t.title + " " + t.lastMessage).toLowerCase().includes(q.toLowerCase())), [threads, q]);
  return (
    <div className="flex h-full flex-col" style={{ backgroundColor: "var(--panel-bg)" }}>
      <div className="flex items-center gap-2 border-b px-3 py-2" style={{ backgroundColor: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
        <div className="relative flex-1 min-w-0">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 shrink-0" style={{ color: "var(--muted)" }} />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search threads…"
            className="pl-9 pr-3 h-8 bg-transparent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
          />
        </div>
        <Button onClick={onNewChat} size="icon" className="h-8 w-8 shrink-0 rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {filtered.map((t) => (
          <div key={t.id} className="group mb-2">
            <div
              onClick={() => onSelect(t.id)}
              className="flex w-full items-center gap-3 rounded-xl border p-2 text-left transition-colors cursor-pointer hover:bg-white/5"
              style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
            >
              <Avatar className="h-8 w-8 shrink-0">
                <AvatarImage src={""} alt={t.title} />
                <AvatarFallback>{initials(t.title)}</AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-sm font-medium">{t.title}</div>
                  {t.unread > 0 && <Badge style={{ background: "var(--accent-weak)", color: "#000" }}>{t.unread}</Badge>}
                </div>
                <div className="truncate text-xs opacity-80">{t.lastMessage}</div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0 h-8 w-8 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ background: "rgba(255,255,255,0.08)", color: "var(--text)" }}
                    aria-label="Thread options"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem>Rename</DropdownMenuItem>
                  <DropdownMenuItem>Archive</DropdownMenuItem>
                  <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;

