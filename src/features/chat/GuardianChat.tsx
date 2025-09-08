import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { ChevronLeft, ChevronRight, Menu, MessageSquare, MoreVertical, Plus, Sparkles } from "lucide-react";
import { Thread, Message } from "@/types/ui";
import { Composer, ChatBubble } from "./components";
import Sidebar from "@/components/chat/Sidebar";

export function GuardianChat({ guardianName, userName, prefill, onPrefillConsumed }: { guardianName: string; userName: string; prefill?: string; onPrefillConsumed?: () => void }) {
  const { wallpaperUrl } = useWallpaperUrl();
  const [threads, setThreads] = useState<Thread[]>([
    {
      id: "t1",
      title: "Design Sync",
      lastMessage: "Let's ship the new message bubbles today.",
      unread: 2,
      participants: [
        { id: "me", name: userName },
        { id: "bot", name: guardianName },
      ],
      messages: [
        { id: "m1", authorId: "bot", authorName: guardianName, content: "Morning! Did you see the updated chat bubble spec?", createdAt: Date.now() - 1000 * 60 * 60, status: "read" },
        { id: "m2", authorId: "me", authorName: userName, content: "Yep—looks great. The drop shadows feel a bit heavy though.", createdAt: Date.now() - 1000 * 60 * 58, status: "read" },
        { id: "m3", authorId: "bot", authorName: guardianName, content: "Agreed. I lightened them and added a subtle border.", createdAt: Date.now() - 1000 * 60 * 42, status: "read" },
      ],
    },
  ]);
  const [activeId, setActiveId] = useState<string>("t1");
  const active = useMemo(() => threads.find((t) => t.id === activeId)!, [threads, activeId]);
  useEffect(() => {
    setThreads((prev) =>
      prev.map((t) => ({
        ...t,
        participants: t.participants.map((p) => (p.id === "bot" ? { ...p, name: guardianName } : p)),
        messages: t.messages.map((m) => (m.authorId === "bot" ? { ...m, authorName: guardianName } : m)),
      }))
    );
  }, [guardianName]);
  useEffect(() => {
    setThreads((prev) =>
      prev.map((t) => ({
        ...t,
        participants: t.participants.map((p) => (p.id === "me" ? { ...p, name: userName } : p)),
        messages: t.messages.map((m) => (m.authorId === "me" ? { ...m, authorName: userName } : m)),
      }))
    );
  }, [userName]);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [active.messages.length, activeId]);
  function send(text: string) {
    const newMsg: Message = { id: String(Math.random()), authorId: "me", authorName: userName, content: text, createdAt: Date.now(), status: "sending" };
    setThreads((prev) => prev.map((t) => (t.id === activeId ? { ...t, messages: [...t.messages, newMsg], lastMessage: text } : t)));
    setTimeout(() => {
      setThreads((prev) => prev.map((t) => (t.id === activeId ? { ...t, messages: t.messages.map((m) => (m.id === newMsg.id ? { ...m, status: "sent" } : m)) } : t)));
    }, 300);
  }
  const [threadsOpen, setThreadsOpen] = useState(true);
  return (
    <div
      className="flex-1 h-full min-h-0 w-full grid gap-[var(--gutter)] px-[var(--board-edge)] pb-[var(--board-edge)]"
      style={{ gridTemplateColumns: "minmax(280px, 360px) 1fr" }}
    >
      {/* Sidebar (collapsible on small screens) */}
      <div className={`hidden md:flex h-full min-h-0 ${threadsOpen ? "" : "md:hidden"}`}>
        <div className="h-full rounded-[var(--radius)] flex-1" style={{ padding: "var(--board-edge)" }}>
          <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}>
            <div className="rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0))", padding: "var(--rim)" }}>
              <div className="relative rounded-[var(--radius)] h-full">
                <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                  <RefractiveGlassCard wallpaperUrl={wallpaperUrl} className="w-full h-full rounded-[var(--radius)]" style={{ background: "transparent", border: "none" }} intensity={0.008} intensity={0} />
                </div>
                <div className="min-h-0 h-full rounded-[var(--radius)] overflow-hidden flex flex-col" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)" }}>
                  <div className="min-h-0 flex-1 overflow-auto">
                    <Sidebar
                      threads={threads}
                      activeId={activeId}
                      onSelect={setActiveId}
                      onNewChat={() => {
                        const id = `t_${Date.now()}`;
                        setThreads((prev) => [
                          { id, title: "New Chat", lastMessage: "", unread: 0, participants: [{ id: "me", name: userName }, { id: "bot", name: guardianName }], messages: [] },
                          ...prev,
                        ]);
                        setActiveId(id);
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chat area (opaque) */}
      <div className="h-full min-h-0 min-w-0">
        <div className="h-full rounded-[var(--radius)]" style={{ padding: "var(--board-edge)" }}>
          <div className="rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}>
            <div className="rounded-[var(--radius)] h-full" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0))", padding: "var(--rim)" }}>
              <div className="relative rounded-[var(--radius)] h-full">
                <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                  <RefractiveGlassCard wallpaperUrl={wallpaperUrl} className="w-full h-full rounded-[var(--radius)]" style={{ background: "transparent", border: "none" }} intensity={0.008} intensity={0} />
                </div>
                <div className="min-h-0 h-full rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)" }}>
        <div className="w-full px-4 py-2 flex items-center justify-between gap-2" style={{ borderBottom: "1px solid var(--panel-border)" }}>
          {/* LEFT CONTROLS (inline) */}
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-2xl md:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              onClick={() => setThreadsOpen((v) => !v)}
              aria-label="Toggle threads"
              style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
            >
              {threadsOpen ? <ChevronLeft className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
            </Button>

            <MessageSquare className="h-5 w-5" style={{ color: "var(--text)" }} />
          </div>

          {/* CENTERED TITLE */}
          <div className="absolute left-1/2 -translate-x-1/2 text-center pointer-events-none">
            <div className="truncate font-semibold" style={{ color: "var(--text)" }}>
              {active.title}
            </div>
          </div>

          {/* RIGHT CONTROLS */}
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              aria-label="New chat"
              onClick={() => {
                const id = `t_${Date.now()}`;
                setThreads((prev) => [
                  { id, title: "New Chat", lastMessage: "", unread: 0, participants: [{ id: "me", name: userName }, { id: "bot", name: guardianName }], messages: [] },
                  ...prev,
                ]);
                setActiveId(id);
              }}
              style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
            >
              <Plus className="h-5 w-5" />
            </Button>

            <Button variant="ghost" size="icon" className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}>
              <Sparkles className="h-5 w-5" />
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}>
                  <MoreVertical className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>Rename</DropdownMenuItem>
                <DropdownMenuItem>Archive</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <div className="h-full min-h-0 flex flex-col">
          <div className="min-h-0 flex-1 overflow-auto px-[var(--card-pad)] pb-[var(--card-pad)]">
            <div ref={viewportRef} className="min-h-0">
              <div className="space-y-3">
                {active.messages.map((m) => (
                  <ChatBubble key={m.id} message={m} isMe={m.authorId === "me"} guardianName={guardianName} />
                ))}
              </div>
            </div>
          </div>
          <div className="border-t px-[var(--card-pad)] py-2" style={{ borderColor: "var(--panel-border)" }}>
            <Composer onSend={send} prefill={prefill} onPrefillConsumed={onPrefillConsumed} />
          </div>
        </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GuardianChat;
