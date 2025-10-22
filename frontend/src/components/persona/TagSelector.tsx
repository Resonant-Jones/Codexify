import React, { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { usePersona } from "./PersonaProvider";

export const TagSelector: React.FC<{ onSelect?: (tag: string) => void }> = ({ onSelect }) => {
  const {
    memoryTags,
    setMemoryTags,
    recentTags,
    setRecentTags,
    addMemoryTag,
    removeMemoryTag,
    clearMemoryTags,
    pushRecentTag,
  } = usePersona();

  const [q, setQ] = useState("");

  const norm = (s: string) => s.trim().replace(/\s+/g, " ").toLowerCase().slice(0, 64);

  const add = (raw: string) => {
    const t = norm(raw);
    if (!t) return;
    // Prevent duplicate tags (case‑insensitive)
    if (memoryTags.includes(t) || recentTags.includes(t)) {
      setQ("");
      return;
    }
    if (addMemoryTag) addMemoryTag(t);
    else setMemoryTags((prev) => Array.from(new Set([...prev, t])));
    if (pushRecentTag) pushRecentTag(t);
    setQ("");
    onSelect?.(t);
  };

  const remove = (t: string) => {
    if (removeMemoryTag) removeMemoryTag(t);
    else setMemoryTags((prev) => prev.filter((x) => x !== t));
    // Also purge from recent tags to avoid lingering button after removal
    if (setRecentTags) {
      const newRecent = recentTags.filter((x) => x !== t);
      setRecentTags(newRecent);
    }
  };

  const filteredMemory = useMemo(
    () => memoryTags.filter((t) => t.toLowerCase().includes(q.toLowerCase())),
    [memoryTags, q]
  );

  const filteredRecent = useMemo(
    () => recentTags.filter((t) => t.toLowerCase().includes(q.toLowerCase()) && !memoryTags.includes(t)),
    [recentTags, memoryTags, q]
  );

  return (
    <div className="space-y-3" style={{ color: "var(--text)" }}>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Add or search tags…"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                add(q);
              }
            }}
            className="bg-transparent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ outlineColor: "var(--accent-weak)", color: "var(--text)" }}
            aria-label="Add or search tags"
          />
        </div>
        <Button type="button" size="sm" onClick={() => add(q)} disabled={!norm(q)} className="rounded-xl">
          Add
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => clearMemoryTags && clearMemoryTags()}
          disabled={!memoryTags.length}
          className="rounded-xl"
        >
          Clear
        </Button>
      </div>

      <div className="space-y-1">
        <div className="text-xs font-semibold opacity-70">Selected</div>
        <div className="flex flex-wrap gap-2">
          {filteredMemory.length === 0 && (
            <span className="text-xs opacity-70">No tags</span>
          )}
          {filteredMemory.map((t) => (
            <Badge key={t} className="cursor-default select-none" style={{ background: "var(--chip-bg)", border: "1px solid var(--panel-border)", color: "var(--text)" }}>
              <span>{t}</span>
              <button
                type="button"
                className="ml-2 rounded-sm px-1 text-[10px] opacity-80 hover:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1"
                style={{ outlineColor: "var(--accent-weak)" }}
                aria-label={`Remove ${t}`}
                onClick={() => remove(t)}
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <div className="text-xs font-semibold opacity-70">Recent</div>
        <div className="flex flex-wrap gap-2">
          {filteredRecent.length === 0 && (
            <span className="text-xs opacity-70">No recent</span>
          )}
          {filteredRecent.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => add(t)}
              className="rounded-full border px-2 py-1 text-xs transition-colors hover:opacity-100"
              style={{ background: "var(--chip-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
              aria-label={`Add ${t}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
