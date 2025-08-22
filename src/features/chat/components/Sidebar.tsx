import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Search, Plus } from "lucide-react";
import { Thread } from "@/types/ui";

const initials = (name: string) => name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();

export function Sidebar({ threads, activeId, onSelect, onNewChat }: { threads: Thread[]; activeId: string; onSelect: (id: string) => void; onNewChat: () => void }) {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => threads.filter((t) => (t.title + " " + t.lastMessage).toLowerCase().includes(q.toLowerCase())), [threads, q]);
  return (
    <div className="flex h-full flex-col" style={{ backgroundColor: "var(--panel-bg)" }}>
      <div className="flex items-center gap-2 border-b p-2" style={{ backgroundColor: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: "var(--muted)" }} />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search threads…"
            className="pl-8 bg-transparent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
          />
        </div>
        <Button onClick={onNewChat} size="icon" className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {filtered.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelect(t.id)}
            className="flex w-full items-center gap-3 rounded-xl border p-2 text-left transition-colors"
            style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
          >
            <Avatar className="h-8 w-8">
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
          </button>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;

