
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Switch } from "@headlessui/react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";
import { ChevronLeft, ChevronRight, Menu, MessageSquare, MoreVertical, Plus, Search, Send, Sparkles, ImagePlus, FolderOpen, FileText } from "lucide-react";

// ---------- Types ----------

type ThemeMode = "light" | "dark" | "system";

type Message = { id: string; authorId: string; authorName: string; content: string; createdAt: number; status?: "sending" | "sent" | "delivered" | "read" };
type Thread = { id: string; title: string; lastMessage: string; unread: number; participants: Array<{ id: string; name: string }>; messages: Message[] };

type ExtColors = Record<string, string>;

type GalleryItem = { src: string; prompt: string };

// ---------- Utils ----------

const fmtTime = (ts: number) => new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(ts);
const initials = (name: string) => name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();

function coerceMode(v: unknown): ThemeMode {
  return v === "light" || v === "dark" || v === "system" ? v : "system";
}

function useThemeController() {
  const getSaved = (): ThemeMode => {
    if (typeof window === "undefined") return "system";
    const raw = window.localStorage.getItem("cfy.themeMode");
    return coerceMode(raw);
  };
  const [mode, setMode] = useState<ThemeMode>(() => getSaved());
  const resolve = (m: ThemeMode) => {
    if (typeof window === "undefined") return m === "dark" ? "dark" : "light";
    const mm = window.matchMedia("(prefers-color-scheme: dark)");
    return m === "dark" || (m === "system" && mm.matches) ? "dark" : "light";
  };
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolve(getSaved()));
  useEffect(() => {
    if (typeof window === "undefined") return;
    const root = document.documentElement;
    const mm = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = (current: ThemeMode) => {
      const safe = coerceMode(current);
      const r = safe === "dark" || (safe === "system" && mm.matches) ? "dark" : "light";
      root.classList.toggle("dark", r === "dark");
      setResolved(r);
    };
    apply(mode);
    localStorage.setItem("cfy.themeMode", mode);
    const handler = () => apply("system");
    if (mode === "system") {
      if (mm.addEventListener) mm.addEventListener("change", handler);
      else mm.addListener(handler);
      return () => {
        if (mm.removeEventListener) mm.removeEventListener("change", handler);
        else mm.removeListener(handler);
      };
    }
  }, [mode]);
  const cycle = () => setMode((m) => (m === "light" ? "system" : m === "system" ? "dark" : "light"));
  return { mode, setMode, cycle, resolved } as const;
}

function hexToRgb(hex: string) {
  const n = hex.replace("#", "");
  const v = n.length === 3 ? n.split("").map((c) => c + c).join("") : n;
  const num = parseInt(v, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}
function rgbToHsl(r: number, g: number, b: number) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b);
  let h = 0,
    s = 0,
    l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h /= 6;
  }
  return { h: h * 360, s: s * 100, l: l * 100 };
}
function hslToHex(h: number, s: number, l: number) {
  s /= 100;
  l /= 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0,
    g = 0,
    b = 0;
  if (0 <= h && h < 60) {
    r = c;
    g = x;
  } else if (60 <= h && h < 120) {
    r = x;
    g = c;
  } else if (120 <= h && h < 180) {
    g = c;
    b = x;
  } else if (180 <= h && h < 240) {
    g = x;
    b = c;
  } else if (240 <= h && h < 300) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }
  const to255 = (v: number) => Math.round((v + m) * 255);
  const out = (n: number) => n.toString(16).padStart(2, "0");
  return `#${out(to255(r))}${out(to255(g))}${out(to255(b))}`;
}
function rotateHue(hex: string, deg: number) {
  const { r, g, b } = hexToRgb(hex);
  const { h, s, l } = rgbToHsl(r, g, b);
  const nh = (h + deg + 360) % 360;
  return hslToHex(nh, s, l);
}
function darken(hex: string, amount: number) {
  const { r, g, b } = hexToRgb(hex);
  const { h, s, l } = rgbToHsl(r, g, b);
  const nl = Math.max(0, l - amount * 100);
  return hslToHex(h, s, nl);
}
function lighten(hex: string, amount: number) {
  const { r, g, b } = hexToRgb(hex);
  const { h, s, l } = rgbToHsl(r, g, b);
  const nl = Math.min(100, l + amount * 100);
  return hslToHex(h, s, nl);
}
function relativeLuminance(hex: string) {
  const { r, g, b } = hexToRgb(hex);
  const srgb = (c: number) => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const R = srgb(r),
    G = srgb(g),
    B = srgb(b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}
function contrastRatioHex(a: string, b: string) {
  const L1 = relativeLuminance(a);
  const L2 = relativeLuminance(b);
  const [hi, lo] = L1 >= L2 ? [L1, L2] : [L2, L1];
  return (hi + 0.05) / (lo + 0.05);
}

// ---------- UI bits ----------

function SegmentedThemeControl({ mode, onChange }: { mode: ThemeMode; onChange: (m: ThemeMode) => void }) {
  const items = ["light", "system", "dark"] as ThemeMode[];
  return (
    <div className="inline-flex rounded-xl border bg-white dark:bg-neutral-700 border-neutral-200 dark:border-neutral-600 overflow-hidden">
      {items.map((m) => (
        <Button
          key={m}
          type="button"
          variant={mode === m ? "default" : "ghost"}
          size="sm"
          className="rounded-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{ outlineColor: "var(--accent-weak)" }}
          onClick={() => onChange(m)}
        >
          {m[0].toUpperCase() + m.slice(1)}
        </Button>
      ))}
    </div>
  );
}

function ContrastChip({ label, ratio }: { label: string; ratio: number }) {
  const status = ratio >= 7 ? "AAA" : ratio >= 4.5 ? "AA" : "Fail";
  const color = ratio >= 7 ? "#16a34a" : ratio >= 4.5 ? "#f59e0b" : "#ef4444";
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full align-middle"
      style={{ border: "1px solid var(--panel-border)", padding: "1px 4px", lineHeight: 1 }}
      title={`${label}: ${ratio.toFixed(2)}:1 • ${status}`}
      aria-label={`${label} contrast ${ratio.toFixed(2)} to 1, ${status}`}
    >
      <span style={{ width: 5, height: 5, background: color, borderRadius: 9999, display: "inline-block" }} />
      <span className="text-[9px]" style={{ color: "var(--text)" }}>
        {ratio.toFixed(1)}:1
      </span>
    </span>
  );
}

function Composer({ onSend, prefill, onPrefillConsumed }: { onSend: (t: string) => void; prefill?: string; onPrefillConsumed?: () => void }) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  useEffect(() => {
    if (prefill && prefill !== value) {
      setValue(prefill);
      setTimeout(() => ref.current?.focus(), 0);
      onPrefillConsumed && onPrefillConsumed();
    }
  }, [prefill]);
  function send() {
    const v = value.trim();
    if (!v) return;
    setSending(true);
    onSend(v);
    setValue("");
    setTimeout(() => setSending(false), 200);
  }
  return (
    <div className="flex items-center gap-2 rounded-2xl border p-2 shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
      <Textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Write a message…"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
        className="min-h-[44px] max-h-44 resize-none border-0 bg-transparent px-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{ color: "var(--text)", outlineColor: "var(--accent-weak)" }}
      />
      <Button
        type="button"
        onClick={send}
        disabled={sending || !value.trim()}
        size="icon"
        className="h-11 w-11 grid place-items-center"
        style={{ background: "#2f2f2f", color: "#fff", borderRadius: "22px", outlineColor: "var(--accent-weak)" }}
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );
}

function Sidebar({ threads, activeId, onSelect, onNewChat }: { threads: Thread[]; activeId: string; onSelect: (id: string) => void; onNewChat: () => void }) {
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

function ChatBubble({ message, isMe, guardianName }: { message: Message; isMe: boolean; guardianName: string }) {
  if (!isMe) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 500, damping: 30 }} className="w-full">
        <div className="mb-1 text-xs font-semibold" style={{ color: "var(--text)" }}>
          {guardianName}
        </div>
        <div className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "var(--text)" }}>
          {message.content}
        </div>
        <div className="mt-1.5 flex items-center gap-2 text-[10px]" style={{ color: "var(--muted)" }}>
          {fmtTime(message.createdAt)}
        </div>
      </motion.div>
    );
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className="max-w-[78%] rounded-2xl p-3 shadow-sm ml-auto"
      style={{ background: "#2f2f2f", color: "#fff" }}
    >
      <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
      <div className="mt-1.5 flex items-center justify-end gap-2">
        <span className="text-[10px] opacity-90">{fmtTime(message.createdAt)}</span>
      </div>
    </motion.div>
  );
}

function WorkspacePane() {
  return (
    <aside className="hidden lg:flex w-[360px] shrink-0 flex-col ml-3">
      <Card className="flex-1 rounded-2xl border shadow-sm overflow-hidden" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)", backdropFilter: "blur(12px) saturate(120%)", WebkitBackdropFilter: "blur(12px) saturate(120%)", borderColor: "var(--panel-bezel)", boxShadow: "inset 0 1px rgba(255,255,255,0.18), inset 0 -1px rgba(0,0,0,0.25), 0 10px 22px rgba(0,0,0,0.25)" }}>
        <div className="p-3 border-b" style={{ borderColor: "var(--panel-border)" }}>
          <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            Workspace
          </div>
        </div>
        <div className="p-3 space-y-4" style={{ color: "var(--text)" }}>
          <div>
            <div className="text-xs font-semibold opacity-70">PROJECTS</div>
            <div className="mt-2 space-y-2">
              {["Sovereign AI Principles", "Health & Wellness"].map((p) => (
                <div key={p} className="rounded-md px-3 py-2" style={{ background: "var(--chip-bg)", border: "1px solid var(--panel-border)" }}>
                  {p}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold opacity-70">DOCS</div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {["Covenant.pdf", "Roadmap.md", "Vision.txt", "Design.sketch"].map((d) => (
                <div key={d} className="rounded-md px-3 py-2 text-sm text-center" style={{ background: "var(--chip-bg)", border: "1px solid var(--panel-border)" }}>
                  {d}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </aside>
  );
}

function ext(name: string) {
  const m = name.match(/\.([^.]+)$/);
  return m ? m[1].toLowerCase() : "";
}

function DocumentTile({ name, color }: { name: string; color: string }) {
  return (
    <div className="relative aspect-square rounded-2xl overflow-hidden border shadow-sm" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)" }}>
      <div className="grid h-full place-items-center">
        <FileText className="h-8 w-8" style={{ color }} />
      </div>
      <div className="absolute inset-x-0 bottom-0">
        <div className="px-2 py-1 text-xs text-center" style={{ background: "rgba(0,0,0,0.35)", color: "#fff" }}>
          {name}
        </div>
      </div>
    </div>
  );
}

export function GuardianChat({ guardianName, userName, prefill, onPrefillConsumed }: { guardianName: string; userName: string; prefill?: string; onPrefillConsumed?: () => void }) {
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
    setThreads((prev) => prev.map((t) => (t.id !== activeId ? t : { ...t, messages: [...t.messages, newMsg], lastMessage: text })));
    setTimeout(() => {
      setThreads((prev) => prev.map((t) => (t.id !== activeId ? t : { ...t, messages: t.messages.map((m) => (m.id === newMsg.id ? { ...m, status: "sent" } : m)) })));
    }, 300);
  }
  const [threadsOpen, setThreadsOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="flex h-full w-full gap-3">
      {threadsOpen && (
        <Card className="hidden lg:flex w-80 shrink-0 overflow-hidden rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-bezel)" }}>
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
        </Card>
      )}
      <Card className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border shadow-lg" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-bezel)" }}>
        <div className="flex items-center justify-between border-b p-2 lg:hidden" style={{ borderColor: "var(--panel-border)" }}>
          <div className="flex items-center gap-2">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2" style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }} aria-label="Open threads">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-80 p-0">
                <SheetHeader>
                  <SheetTitle>
                    <VisuallyHidden>Thread list</VisuallyHidden>
                  </SheetTitle>
                </SheetHeader>
                <Sidebar
                  threads={threads}
                  activeId={activeId}
                  onSelect={(id) => {
                    setActiveId(id);
                    setMobileOpen(false);
                  }}
                  onNewChat={() => {
                    const id = `t_${Date.now()}`;
                    setThreads((prev) => [
                      { id, title: "New Chat", lastMessage: "", unread: 0, participants: [{ id: "me", name: userName }, { id: "bot", name: guardianName }], messages: [] },
                      ...prev,
                    ]);
                    setMobileOpen(false);
                    setActiveId(id);
                  }}
                />
              </SheetContent>
            </Sheet>
            <div className="font-semibold" style={{ color: "var(--text)" }}>
              Chats
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between gap-2 p-3" style={{ borderBottom: `1px solid var(--panel-border)`, color: "var(--text)" }}>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-2xl hidden lg:inline-flex focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              aria-label="Toggle threads"
              onClick={() => setThreadsOpen((v) => !v)}
              style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
            >
              {threadsOpen ? <ChevronLeft className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
            </Button>
            <MessageSquare className="h-5 w-5" style={{ color: "var(--text)" }} />
            <div className="truncate font-semibold" style={{ color: "var(--text)" }}>
              {active.title}
            </div>
          </div>
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
        <Separator />
        <div className="flex min-h-0 flex-1 flex-col p-3">
          <CardContent className="flex min-h-0 flex-1 flex-col gap-3 p-0">
            <div ref={viewportRef} className="flex-1 overflow-y-auto p-2">
              <div className="space-y-3">
                <AnimatePresence initial={false}>
                  {active.messages.map((m) => (
                    <ChatBubble key={m.id} message={m} isMe={m.authorId === "me"} guardianName={guardianName} />
                  ))}
                </AnimatePresence>
              </div>
            </div>
            <div className="pt-1">
              <Composer onSend={send} prefill={prefill} onPrefillConsumed={onPrefillConsumed} />
            </div>
          </CardContent>
        </div>
      </Card>
      <WorkspacePane />
    </div>
  );
}

function DashboardView({ extColors, gallery, onImagePrompt }: { extColors: ExtColors; gallery: GalleryItem[]; onImagePrompt: (p: string) => void }) {
  const recentDocs = ["Covenant.pdf", "Roadmap.md", "Vision.txt"];
  const colorFor = (name: string) => extColors[ext(name)] || "#6366f1";
  return (
    <div className="grid h-full grid-cols-1 gap-4 p-4 lg:grid-cols-2">
      <Card className="rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-bezel)" }}>
        <CardContent className="p-4 space-y-4">
          <div>
            <div className="mb-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
              Pinned
            </div>
            <div className="grid grid-cols-2 gap-3">
              {"Sovereign AI Principles,Health & Wellness,Novel Outline,Meeting Prep".split(",").map((t) => (
                <div key={t} className="rounded-xl border p-3 text-sm" style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}>
                  {t}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="mb-3 text-lg font-semibold" style={{ color: "var(--text)" }}>
              Recent Documents
            </div>
            <div className="grid grid-cols-3 gap-3">
              {recentDocs.map((d) => (
                <DocumentTile key={d} name={d} color={colorFor(d)} />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-bezel)" }}>
        <CardContent className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-lg font-semibold" style={{ color: "var(--text)" }}>
              Generated Images
            </div>
            <Button size="sm" variant="ghost" className="rounded-xl" style={{ color: "var(--text)" }}>
              See all
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {gallery.map((item, i) => (
              <button
                key={i}
                className="aspect-square overflow-hidden rounded-2xl border"
                style={{ borderColor: "var(--panel-border)" }}
                onClick={() => onImagePrompt(item.prompt)}
                title="Open chat with prompt"
              >
                <img src={item.src} alt="Gallery" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SettingsView({
  mode,
  setMode,
  guardianName,
  setGuardianName,
  userName,
  setUserName,
  role,
  setRole,
  notes,
  setNotes,
  baseColor,
  setBaseColor,
  depth,
  setDepth,
  fade,
  setFade,
  resolved,
  systemPrompt,
  setSystemPrompt,
  wallpaper,
  setWallpaper,
  extColors,
  setExtColors,
  openDashboardOnLaunch,
  setOpenDashboardOnLaunch,
}: {
  mode: ThemeMode;
  setMode: (m: ThemeMode) => void;
  guardianName: string;
  setGuardianName: (s: string) => void;
  userName: string;
  setUserName: (s: string) => void;
  role: string;
  setRole: (s: string) => void;
  notes: string;
  setNotes: (s: string) => void;
  baseColor: string;
  setBaseColor: (s: string) => void;
  depth: number;
  setDepth: (n: number) => void;
  fade: number;
  setFade: (n: number) => void;
  resolved: "light" | "dark";
  systemPrompt: string;
  setSystemPrompt: (s: string) => void;
  wallpaper: string | null;
  setWallpaper: (s: string | null) => void;
  extColors: ExtColors;
  setExtColors: (m: ExtColors) => void;
  openDashboardOnLaunch: boolean;
  setOpenDashboardOnLaunch: (b: boolean) => void;
}) {
  const [tab, setTab] = useState<"appearance" | "system">("appearance");
  const [name, setName] = useState(guardianName);
  const [uName, setUName] = useState(userName);
  const [uRole, setURole] = useState(role);
  const [prompt, setPrompt] = useState(systemPrompt);
  const [memo, setMemo] = useState(notes);
  useEffect(() => setName(guardianName), [guardianName]);
  useEffect(() => setUName(userName), [userName]);
  useEffect(() => setURole(role), [role]);
  useEffect(() => setPrompt(systemPrompt), [systemPrompt]);
  useEffect(() => setMemo(notes), [notes]);

  function handleSave() {
    setGuardianName(name);
    setUserName(uName);
    setRole(uRole);
    setSystemPrompt(prompt);
    setNotes(memo);
  }

  const [fileLabel, setFileLabel] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);
  function triggerFile() {
    fileRef.current?.click();
  }
  function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setUploading(true);
    setFileLabel(f.name);
    const rd = new FileReader();
    rd.onload = () => {
      const url = String(rd.result || "");
      setWallpaper(url);
      if (typeof window !== "undefined") localStorage.setItem("cfy.wallpaper", url);
      setUploading(false);
    };
    rd.onerror = () => setUploading(false);
    rd.readAsDataURL(f);
  }
  function clearWallpaper() {
    setWallpaper(null);
    setFileLabel("");
    if (typeof window !== "undefined") localStorage.removeItem("cfy.wallpaper");
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div className="h-full p-4" style={{ color: "var(--text)" }}>
      <Card className="mx-auto w-full max-w-4xl rounded-2xl border shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-bezel)", color: "var(--text)" }}>
        <CardContent className="space-y-6 p-4">
          <div className="flex items-center gap-2">
            <Button type="button" variant={tab === "appearance" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setTab("appearance")}>
              Appearance
            </Button>
            <Button type="button" variant={tab === "system" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setTab("system")}>
              System Prompt
            </Button>
          </div>

          {tab === "system" && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <div className="text-sm font-medium">Guardian Nickname</div>
                  <Input value={name} onChange={(e) => setName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-medium">User Nickname</div>
                  <Input value={uName} onChange={(e) => setUName(e.target.value)} className="w-48 h-8 text-xs" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
                <div className="space-y-1 sm:col-span-2">
                  <div className="text-sm font-medium">Occupation / Role</div>
                  <Input value={uRole} onChange={(e) => setURole(e.target.value)} className="h-9" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-sm font-medium">System Prompt</div>
                <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} className="min-h[140px] text-sm" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-medium">Extra Things to Remember</div>
                <Textarea value={memo} onChange={(e) => setMemo(e.target.value)} className="min-h-[100px] text-sm" style={{ color: "var(--text)", background: "transparent", borderColor: "var(--panel-border)" }} />
              </div>
              <div>
                <Button type="button" size="sm" onClick={handleSave}>
                  Save
                </Button>
              </div>
            </div>
          )}

          {tab === "appearance" && (
            <div className="space-y-6">
              {/* Codexify Badge or brand header is above */}
              <div>
                <div className="mb-2 text-lg font-semibold">Theme</div>
                <SegmentedThemeControl mode={mode} onChange={setMode} />
              </div>
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-300 dark:text-gray-100 mb-1">
                  Launch to Dashboard on Startup
                </label>
                <p className="text-xs text-gray-400 mb-2">
                  When enabled, the app opens to the Dashboard instead of Guardian on fresh launch.
                </p>
                <Switch
                  checked={openDashboardOnLaunch}
                  onChange={(checked) => setOpenDashboardOnLaunch(checked)}
                  className={`${openDashboardOnLaunch ? "bg-green-500" : "bg-gray-600"} 
                    relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200`}
                >
                  <span
                    className={`${
                      openDashboardOnLaunch ? "translate-x-6" : "translate-x-1"
                    } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
                  />
                </Switch>
              </div>
              <div>
                <div className="mb-2 text-lg font-semibold">Wallpaper</div>
                <div className="flex items-center gap-2">
                  <input id="wallpaper-file" ref={fileRef} type="file" accept="image/*" onChange={onUpload} className="sr-only" />
                  <Button type="button" size="sm" onClick={triggerFile} className="rounded-xl flex items-center gap-2">
                    <ImagePlus className="h-4 w-4" /> {uploading ? "Uploading…" : "Upload Image"}
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={clearWallpaper}>
                    Clear
                  </Button>
                  <Button type="button" variant="ghost" size="sm" className="flex items-center gap-2">
                    <FolderOpen className="h-4 w-4" /> Gallery
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={() => {
                    const url = "https://images.unsplash.com/photo-1596709031408-b0b2c9659c8a?q=80&w=1440&auto=format&fit=crop";
                    setWallpaper(url);
                    if (typeof window !== "undefined") localStorage.setItem("cfy.wallpaper", url);
                  }}>
                    Use Demo
                  </Button>
                </div>
                <div className="sr-only" aria-live="polite">{fileLabel ? `Selected ${fileLabel}` : ""}</div>
                {fileLabel && <div className="text-xs opacity-80 mt-1">Selected: {fileLabel}</div>}
                {wallpaper && (
                  <div className="mt-3 overflow-hidden rounded-xl border" style={{ borderColor: "var(--panel-border)" }}>
                    <img src={wallpaper} alt="Wallpaper preview" className="h-32 w-full object-cover" />
                  </div>
                )}
              </div>
              <div>
                <div className="mb-2 text-lg font-semibold">Background Accents</div>
                <div className="flex items-center gap-3">
                  <input type="color" value={baseColor} onChange={(e) => setBaseColor(e.target.value)} className="h-9 w-9 rounded-md border" />
                  <div className="text-sm">Base color (used when no wallpaper)</div>
                </div>
                <div className="mt-4 grid grid-cols-1 gap-4">
                  <div>
                    <div className="mb-1 text-sm">Depth</div>
                    <input type="range" min={0} max={100} value={Math.round(depth * 100)} onChange={(e) => setDepth(Number(e.target.value) / 100)} className="w-full" />
                  </div>
                  <div>
                    <div className="mb-1 text-sm">Fade</div>
                    <input type="range" min={0} max={100} value={Math.round(fade * 100)} onChange={(e) => setFade(Number(e.target.value) / 100)} className="w-full" />
                  </div>
                </div>
              </div>
              <div>
                <div className="mb-2 text-lg font-semibold">File Type Colors</div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {["pdf", "md", "txt", "sketch", "docx", "png", "jpg"].map((k) => (
                    <div key={k} className="flex items-center gap-2">
                      <span className="w-10 text-xs uppercase opacity-70">{k}</span>
                      <input type="color" value={extColors[k] || "#6B7280"} onChange={(e) => setExtColors({ ...extColors, [k]: e.target.value })} className="h-7 w-7 rounded-md border" />
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="mb-2 text-lg font-semibold">Live Contrast</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <ContrastChip label="Text vs Panel" ratio={contrastRatioHex(resolved === "dark" ? "#ffffff" : "#111827", resolved === "dark" ? "#202020" : "#f3f4f6")} />
                  <ContrastChip label="User Text vs Bubble" ratio={contrastRatioHex("#ffffff", "#2f2f2f")} />
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------- App Shell ----------

export default function AppShell() {
  const { mode, setMode, cycle, resolved } = useThemeController();
  const [guardianName, setGuardianName] = useState<string>(() => (typeof window === "undefined" ? "Guardian" : localStorage.getItem("cfy.assistantName") || "Guardian"));
  const [userName, setUserName] = useState<string>(() => (typeof window === "undefined" ? "You" : localStorage.getItem("cfy.userName") || "You"));
  const [role, setRole] = useState<string>(() => (typeof window === "undefined" ? "" : localStorage.getItem("cfy.role") || ""));
  const [notes, setNotes] = useState<string>(() => (typeof window === "undefined" ? "" : localStorage.getItem("cfy.notes") || ""));
  // --- Persist openDashboardOnLaunch toggle ---
  const [openDashboardOnLaunch, setOpenDashboardOnLaunch] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("cfy.openDashboardOnLaunch") === "true";
  });
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.openDashboardOnLaunch", String(openDashboardOnLaunch));
    }
  }, [openDashboardOnLaunch]);
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.assistantName", guardianName);
    }
  }, [guardianName]);
  const [systemPrompt, setSystemPrompt] = useState<string>(() => (typeof window === "undefined" ? "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity." : localStorage.getItem("cfy.systemPrompt") || "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity."));
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.userName", userName);
      localStorage.setItem("cfy.role", role);
      localStorage.setItem("cfy.notes", notes);
      localStorage.setItem("cfy.systemPrompt", systemPrompt);
    }
  }, [userName, role, notes, systemPrompt]);
  const [view, setView] = useState<"dashboard" | "guardian" | "settings">(() => {
    if (typeof window === "undefined") return "guardian";
    const last = localStorage.getItem("cfy.lastView") as any;
    if (last) return last;
    return localStorage.getItem("cfy.openDashboardOnLaunch") === "true" ? "dashboard" : "guardian";
  });
  useEffect(() => {
    if (typeof window !== "undefined") localStorage.setItem("cfy.lastView", view);
  }, [view]);
  const [wallpaper, setWallpaper] = useState<string | null>(() => (typeof window === "undefined" ? null : localStorage.getItem("cfy.wallpaper")));
  const [baseColor, setBaseColor] = useState<string>(() => (typeof window === "undefined" ? "#6B7280" : localStorage.getItem("cfy.baseColor") || "#6B7280"));
  const [depth, setDepth] = useState<number>(() => (typeof window === "undefined" ? 0.6 : Number(localStorage.getItem("cfy.depth") || "0.6")));
  const [fade, setFade] = useState<number>(() => (typeof window === "undefined" ? 0.4 : Number(localStorage.getItem("cfy.fade") || "0.4")));
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("cfy.baseColor", baseColor);
      localStorage.setItem("cfy.depth", String(depth));
      localStorage.setItem("cfy.fade", String(fade));
    }
  }, [baseColor, depth, fade]);

  // Default gradient orientation for light/dark when *no wallpaper* is set
  useEffect(() => {
    if (wallpaper) return;
    if (resolved === "dark") {
      setDepth(0.9);
      setFade(0.1);
    } else {
      setDepth(0.1);
      setFade(0.9);
    }
  }, [resolved]);

  const accent = baseColor;
  const accentWeak = rotateHue(baseColor, 12);
  const accentStrong = rotateHue(baseColor, -12);
  const bgStyleNoWallpaper = (() => {
    const start = lighten(baseColor, fade * 0.5);
    const end = darken(baseColor, depth * 0.8);
    return { background: `linear-gradient(to bottom, ${start}, ${end})` } as React.CSSProperties;
  })();
  const backgroundStyle: React.CSSProperties = wallpaper
    ? { backgroundImage: `url(${wallpaper})`, backgroundSize: "cover", backgroundPosition: "center" }
    : bgStyleNoWallpaper;
  const panelBg = resolved === "dark" ? "#202020" : "#f3f4f6";
  const chipBg = resolved === "dark" ? "#2f2f2f" : "#e5e7eb";
  const panelBorder = resolved === "dark" ? "#3f3f3f" : "#e5e7eb";
  const textColor = resolved === "dark" ? "#ffffff" : "#111827";
  const mutedColor = resolved === "dark" ? "rgba(255,255,255,0.88)" : "#374151";
  const panelBezel = resolved === "dark" ? "rgba(255,255,255,0.08)" : "rgba(17,24,39,0.06)";
  const styleVars = {
    "--accent": accent,
    "--accent-weak": accentWeak,
    "--accent-strong": accentStrong,
    "--panel-bg": panelBg,
    "--chip-bg": chipBg,
    "--panel-border": panelBorder,
    "--panel-bezel": panelBezel,
    "--text": textColor,
    "--muted": mutedColor,
  } as React.CSSProperties as any;

  // Lightweight self checks ("tests")
  useEffect(() => {
    try {
      console.assert(coerceMode("nope") === "system");
      console.assert(Math.abs(contrastRatioHex("#000000", "#ffffff") - 21) < 0.1);
      console.assert(rotateHue("#336699", 180).startsWith("#"));
      console.assert(hslToHex(0, 0, 50).toLowerCase() === "#808080");
    } catch (e) {
      console.error("Self-tests failed", e);
    }
  }, []);

  const [extColors, setExtColors] = useState<ExtColors>(() => {
    if (typeof window === "undefined") return { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
    try {
      const raw = localStorage.getItem("cfy.extColors");
      return raw ? JSON.parse(raw) : { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
    } catch {
      return { pdf: "#ef4444", md: "#6366f1", txt: "#06b6d4", sketch: "#f59e0b" };
    }
  });
  useEffect(() => {
    if (typeof window !== "undefined") localStorage.setItem("cfy.extColors", JSON.stringify(extColors));
  }, [extColors]);

  const [gallery] = useState<GalleryItem[]>(() => {
    const def: GalleryItem[] = [
      { src: "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?q=80&w=600&auto=format&fit=crop", prompt: "vibrant color gradient, smooth texture, abstract art, minimalist, 4k" },
      { src: "https://images.unsplash.com/photo-1557682250-33bd709cbe85?q=80&w=600&auto=format&fit=crop", prompt: "dramatic light, deep shadows, cinematic, moody, purple and blue tones" },
      { src: "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?q=80&w=600&auto=format&fit=crop", prompt: "ethereal smoke, liquid metal, iridescent, holographic, studio lighting, 8k" },
      { src: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=600&auto=format&fit=crop", prompt: "soft gradient, warm horizon fade, subtle grain, minimal" },
    ];
    if (typeof window === "undefined") return def;
    try {
      const raw = localStorage.getItem("cfy.gallery");
      return raw ? JSON.parse(raw) : def;
    } catch {
      return def;
    }
  });

  const [prefill, setPrefill] = useState<string | undefined>(undefined);
  function openChatWithPrompt(p: string) {
    setPrefill(p);
    setView("guardian");
  }

  return (
    <div className={`h-dvh w-full p-[3px] ${resolved === "dark" ? "dark" : ""}`} style={{ ...backgroundStyle, ...styleVars }}>
      <div className="flex h-full w-full flex-col rounded-2xl">
        {/* Top Nav */}
        <div className="flex items-center justify-between gap-2 p-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full px-2 py-1 text-xs font-semibold" style={{ background: "#000", color: "#fff" }}>
              Codexify
            </span>
            <Button variant={view === "dashboard" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setView("dashboard")}>Dashboard</Button>
            <Button variant={view === "guardian" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setView("guardian")}>Guardian</Button>
            <Button variant={view === "settings" ? "default" : "ghost"} size="sm" className="rounded-xl" onClick={() => setView("settings")}>Settings</Button>
          </div>
          <div className="text-xs opacity-80" style={{ color: "var(--text)" }}>Mode: {resolved}</div>
        </div>
        <Separator />

        {/* Main Content */}
        <div className="flex min-h-0 flex-1 p-3">
          {view === "guardian" && (
            <GuardianChat guardianName={guardianName} userName={userName} prefill={prefill} onPrefillConsumed={() => setPrefill(undefined)} />
          )}
          {view === "dashboard" && (
            <div className="flex min-h-0 w-full gap-3">
              <Card className="flex min-w-0 flex-1 rounded-2xl border shadow-sm overflow-hidden" style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)), rgba(255,255,255,0.06)", backdropFilter: "blur(12px) saturate(120%)", WebkitBackdropFilter: "blur(12px) saturate(120%)", borderColor: "var(--panel-bezel)", boxShadow: "inset 0 1px rgba(255,255,255,0.18), inset 0 -1px rgba(0,0,0,0.25), 0 10px 22px rgba(0,0,0,0.25)" }}>
                <DashboardView extColors={extColors} gallery={gallery} onImagePrompt={openChatWithPrompt} />
              </Card>
              <WorkspacePane />
            </div>
          )}
          {view === "settings" && (
            <div className="flex min-h-0 w-full gap-3">
              <Card className="flex min-w-0 flex-1 rounded-2xl border shadow-sm overflow-hidden" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-bezel)" }}>
                <SettingsView
                  mode={mode}
                  setMode={setMode}
                  guardianName={guardianName}
                  setGuardianName={setGuardianName}
                  userName={userName}
                  setUserName={setUserName}
                  role={role}
                  setRole={setRole}
                  notes={notes}
                  setNotes={setNotes}
                  baseColor={baseColor}
                  setBaseColor={setBaseColor}
                  depth={depth}
                  setDepth={setDepth}
                  fade={fade}
                  setFade={setFade}
                  resolved={resolved}
                  systemPrompt={systemPrompt}
                  setSystemPrompt={setSystemPrompt}
                  wallpaper={wallpaper}
                  setWallpaper={setWallpaper}
                  extColors={extColors}
                  setExtColors={setExtColors}
                  openDashboardOnLaunch={openDashboardOnLaunch}
                  setOpenDashboardOnLaunch={setOpenDashboardOnLaunch}
                />
              </Card>
              <WorkspacePane />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
