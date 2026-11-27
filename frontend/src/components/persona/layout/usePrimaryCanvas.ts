import { useLayoutEffect, useRef, useState } from "react";
import { CHAT_MIN, DIVIDER, WORK_MIN } from "./DockedPanelDivider";
import type { WorkspaceLayoutMode } from "@/features/workspace/state/useWorkspaceLayoutMode";

type Pane = "chat" | "workspace";
type Episode = { scope: string; pane: Pane };
const splitMin = CHAT_MIN + DIVIDER + WORK_MIN;

export function usePrimaryCanvas(enabled: boolean, width: number, scope: string, choice: WorkspaceLayoutMode | null) {
  const lastUse = useRef<{ scope: string; pane: Pane } | null>(null);
  const [episode, setEpisode] = useState<Episode | null>(null);
  const current = episode?.scope === scope ? episode : null;
  const focus = choice === "chat_focus" ? "chat" : choice === "workspace_focus" ? "workspace" : null;

  useLayoutEffect(() => {
    if (!enabled || (!current && width >= splitMin)) {
      if (episode) setEpisode(null);
      return;
    }
    // A divider-width buffer avoids repeatedly entering and leaving fallback at the fit edge.
    if (current && !focus && width >= splitMin + DIVIDER) {
      setEpisode(null);
      return;
    }
    const pane = focus ?? current?.pane ?? (lastUse.current?.scope === scope ? lastUse.current.pane : "chat");
    if (current?.pane !== pane) {
      setEpisode({ scope, pane });
    }
  }, [enabled, width, current, episode, scope, focus]);

  return {
    pane: enabled ? current?.pane ?? null : null,
    recordUse(pane: Pane) { lastUse.current = { scope, pane }; },
  };
}
