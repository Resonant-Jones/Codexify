import { useMemo, useState, useEffect } from "react";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { MoreVertical, Plus, Sparkles } from "lucide-react";
import { Thread, Message } from "@/types/ui";
import { Composer } from "./components";
import ChatView from "@/features/chat/ChatView";
import api from "@/lib/api";
import { getSSEClient } from "@/lib/sseClient";

export function GuardianChat({
  guardianName,
  userName,
  prefill,
  onPrefillConsumed,
  onWorkspaceToggle,
  activeThread,
  onSendMessage,
  onNewChat,
}: {
  guardianName: string;
  userName: string;
  prefill?: string;
  onPrefillConsumed?: () => void;
  onWorkspaceToggle?: () => void;
  activeThread: Thread;
  onSendMessage: (text: string) => void;
  onNewChat: () => void;
}) {
  const { wallpaperUrl } = useWallpaperUrl();
  const [currentThreadId, setCurrentThreadId] = useState<number | null>(null);
  
  const numericThreadId = useMemo(() => {
    let urlId: number | null = null;
    if (typeof window !== "undefined") {
      const m = window.location.pathname.match(/\/chat\/(\d+)/);
      if (m && m[1]) {
        const v = Number(m[1]);
        if (Number.isFinite(v)) urlId = v;
      }
    }
    if (urlId != null) return urlId;
    const n = Number((activeThread as any)?.id);
    return Number.isFinite(n) ? (n as number) : null;
  }, [activeThread?.id]);

  // Update currentThreadId when numericThreadId changes
  useEffect(() => {
    if (numericThreadId !== currentThreadId) {
      setCurrentThreadId(numericThreadId);
    }
  }, [numericThreadId, currentThreadId]);

  // SSE integration for real-time updates
  useEffect(() => {
    if (numericThreadId) {
      const sseClient = getSSEClient();
      sseClient.connect();

      // Handle message.created events for the current thread
      const unsubscribeMessage = sseClient.on('message.created', (event) => {
        if (event.data.thread_id === numericThreadId) {
          console.log('[SSE] New message in current thread:', event.data);
          // You can add logic here to update the UI or trigger a refetch
        }
      });

      // Handle thread.updated events
      const unsubscribeThread = sseClient.on('thread.updated', (event) => {
        if (event.data.thread_id === numericThreadId) {
          console.log('[SSE] Thread updated:', event.data);
          // You can add logic here to update thread metadata
        }
      });

      return () => {
        unsubscribeMessage();
        unsubscribeThread();
      };
    }
  }, [numericThreadId]);

  // Auto-thread creation handler
  const handleThreadCreated = async (threadId: number) => {
    setCurrentThreadId(threadId);
    // Update URL to reflect the new thread
    if (typeof window !== "undefined") {
      window.history.replaceState({}, "", `/chat/${threadId}`);
    }
  };

  // Enhanced send handler with auto-thread creation
  const handleSendMessage = (text: string) => {
    if (!currentThreadId) {
      // Create a new thread if none exists
      api.post('/api/chat/threads', {
        title: text.substring(0, 50), // Use first 50 chars as title
        user_id: userName || 'default'
      }).then(response => {
        if (response.data?.ok && response.data?.id) {
          const newThreadId = response.data.id;
          handleThreadCreated(newThreadId);
          
          // Now send the message to the new thread
          return api.post(`/api/chat/${newThreadId}/messages`, {
            role: 'user',
            content: text,
            user_id: userName || 'default'
          });
        }
      }).then(() => {
        // Call the original onSendMessage
        onSendMessage(text);
      }).catch(error => {
        console.error('Failed to create thread or send message:', error);
        // Fallback to original behavior
        onSendMessage(text);
      });
    } else {
      // Thread exists, just send the message
      onSendMessage(text);
    }
  };

  return (
    // KEY FIX: Add h-full to the outermost container
    <div className="flex-1 min-h-0 min-w-0 flex flex-col h-full overflow-hidden">
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
              <div className="flex-1 min-h-0 min-w-0 h-full flex flex-col rounded-[var(--radius)] overflow-hidden" style={{ background: "var(--panel-bg)", border: "1px solid var(--panel-border)" }}>
                
                {/* Header - fixed height */}
                <div className="w-full px-4 py-2 flex items-center shrink-0" style={{ borderBottom: "1px solid var(--panel-border)" }}>
                  <div className="w-10" aria-hidden />
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
                        <DropdownMenuItem
                          onClick={async () => {
                            if (numericThreadId == null) return alert("Thread is not persisted yet");
                            const title = window.prompt("Rename thread", activeThread.title || "");
                            if (!title) return;
                            try { await api.patch(`/api/chat/threads/${numericThreadId}`, { title }); } catch (e) { console.warn(e); }
                          }}
                        >
                          Rename Thread
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={async () => {
                            if (numericThreadId == null) return alert("Thread is not persisted yet");
                            const pidRaw = window.prompt("Assign to project id (blank to cancel)", "");
                            if (pidRaw == null || pidRaw === "") return;
                            const pid = Number(pidRaw);
                            if (!Number.isFinite(pid)) return alert("Invalid project id");
                            try { await api.patch(`/api/chat/threads/${numericThreadId}`, { project_id: pid }); } catch (e) { console.warn(e); }
                          }}
                        >
                          Assign to Project…
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={async () => {
                            if (numericThreadId == null) return alert("Thread is not persisted yet");
                            try { await api.patch(`/api/chat/threads/${numericThreadId}`, { project_id: null }); } catch (e) { console.warn(e); }
                          }}
                        >
                          Eject from Project
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={async () => {
                            if (numericThreadId == null) return alert("Thread is not persisted yet");
                            if (!window.confirm("Delete this thread? This cannot be undone.")) return;
                            try { await api.delete(`/api/chat/threads/${numericThreadId}`); } catch (e) { console.warn(e); }
                          }}
                        >
                          Delete Thread
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>

                {/* Main content area - this should now fill the remaining space */}
                <div className="flex-1 min-h-0 min-w-0 flex flex-col">
                  {/* Messages area - scrollable */}
                  <div className="flex-1 min-h-0 overflow-hidden px-[var(--card-pad)] pb-[var(--card-pad)]">
                    {numericThreadId != null ? (
                      <ChatView threadId={numericThreadId} guardianName={guardianName} />
                    ) : (
                      <div className="flex items-center justify-center h-full text-muted-foreground">
                        No thread selected.
                      </div>
                    )}
                  </div>
                  
                  {/* Composer - fixed at bottom */}
                  <div className="border-t px-[var(--card-pad)] py-2 shrink-0" style={{ borderColor: "var(--panel-border)" }}>
                    <Composer
                      onSend={handleSendMessage}
                      prefill={prefill}
                      onPrefillConsumed={onPrefillConsumed}
                      threadId={currentThreadId ?? undefined}
                    />
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
