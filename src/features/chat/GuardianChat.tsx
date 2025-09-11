import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { ChevronLeft, MoreVertical, Plus, Sparkles } from "lucide-react";
import { Thread, Message } from "@/types/ui";
import { Composer, ChatBubble } from "./components";

export function GuardianChat({
  guardianName,
  userName,
  prefill,
  onPrefillConsumed,
  onWorkspaceToggle,
  isSidebarVisible,
  onHideSidebar,
  activeThread,
  onSendMessage,
  onNewChat,
}: {
  guardianName: string;
  userName: string;
  prefill?: string;
  onPrefillConsumed?: () => void;
  onWorkspaceToggle?: () => void;
  isSidebarVisible: boolean;
  onHideSidebar: () => void;
  activeThread: Thread;
  onSendMessage: (text: string) => void;
  onNewChat: () => void;
}) {
  const { wallpaperUrl } = useWallpaperUrl();
  const viewportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [activeThread.messages.length]);

  return (
    // KEY FIX: Add h-full to the outermost container
    <div className="flex-1 min-h-0 min-w-0 flex flex-col h-full">
      {/* KEY FIX: Add h-full to this wrapper too */}
      <div className="flex-1 min-h-0 h-full rounded-[var(--radius)]" style={{ padding: "var(--board-edge)" }}>
        {/* KEY FIX: Add h-full here as well */}
        <div className="flex-1 min-h-0 h-full flex flex-col rounded-[var(--radius)]" style={{ background: "var(--chip-bg)", padding: "var(--frame)", border: "1px solid var(--panel-bezel)" }}>
          {/* KEY FIX: Add h-full to this wrapper */}
          <div className="flex-1 min-h-0 h-full flex flex-col rounded-[var(--radius)]" style={{ background: "linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0))", padding: "var(--rim)" }}>
            {/* KEY FIX: Add h-full here too */}
            <div className="relative rounded-[var(--radius)] h-full">
              <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--radius)] pointer-events-none">
                <RefractiveGlassCard wallpaperUrl={wallpaperUrl} className="w-full h-full rounded-[var(--radius)]" style={{ background: "transparent", border: "none" }} intensity={0.008} />
              </div>
              {/* KEY FIX: Add h-full to the main content container */}
              <div className="flex-1 min-h-0 h-full flex flex-col rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)" }}>
                
                {/* Header - fixed height */}
                <div className="w-full px-4 py-2 flex items-center shrink-0" style={{ borderBottom: "1px solid var(--panel-border)" }}>
                  <div className="flex items-center gap-2">
                    {isSidebarVisible && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                        onClick={onHideSidebar}
                        aria-label="Hide sidebar"
                        style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
                      >
                        <ChevronLeft className="h-5 w-5" />
                      </Button>
                    )}
                  </div>
                  <div className="flex-1 text-center">
                    <div className="truncate font-semibold" style={{ color: "var(--text)" }}>
                      {activeThread.title}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                      aria-label="New chat"
                      onClick={onNewChat}
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
                        <DropdownMenuItem onClick={onWorkspaceToggle}>
                          Workspace
                        </DropdownMenuItem>
                        <DropdownMenuItem>Rename</DropdownMenuItem>
                        <DropdownMenuItem>Archive</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>

                {/* Main content area - this should now fill the remaining space */}
                <div className="flex-1 min-h-0 flex flex-col">
                  {/* Messages area - scrollable */}
                  <div
                    ref={viewportRef}
                    className="flex-1 min-h-0 overflow-auto px-[var(--card-pad)] pb-[var(--card-pad)]"
                  >
                    <div>
                      <div className="space-y-3">
                        {activeThread.messages.map((m) => (
                          <ChatBubble key={m.id} message={m} isMe={m.authorId === "me"} guardianName={guardianName} />
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* Composer - fixed at bottom */}
                  <div className="border-t px-[var(--card-pad)] py-2 shrink-0" style={{ borderColor: "var(--panel-border)" }}>
                    <Composer onSend={onSendMessage} prefill={prefill} onPrefillConsumed={onPrefillConsumed} />
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