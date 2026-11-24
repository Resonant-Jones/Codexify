import React, { useRef } from "react";

export const DIVIDER = 12;
export const SIDE_MIN = 300;
export const CHAT_MIN = 384;
export const WORK_MIN = 320;

export function allocatePanels(width: number, desktop: boolean, sidebarOpen: boolean, workspace: boolean,
  preferredSide: number, preferredWork: number) {
  const fitsSidebar = desktop && width >= SIDE_MIN + DIVIDER + CHAT_MIN + (workspace ? DIVIDER + WORK_MIN : 0);
  const sideMax = width - CHAT_MIN - DIVIDER - (workspace ? DIVIDER + WORK_MIN : 0);
  const side = fitsSidebar && sidebarOpen ? Math.min(sideMax, Math.max(SIDE_MIN, preferredSide)) : 0;
  const primary = width - (side ? side + DIVIDER : 0);
  const workMax = Math.max(0, primary - CHAT_MIN - DIVIDER);
  const work = workspace ? Math.min(workMax, Math.max(WORK_MIN, preferredWork)) : 0;
  return { fitsSidebar, side, work, workMax, sideMax: width - CHAT_MIN - DIVIDER - (workspace ? work + DIVIDER : 0) };
}

type Props = { label: string; value: number; min: number; max: number; reverse?: boolean; onChange: (width: number) => void };
export function DockedPanelDivider({ label, value, min, max, reverse, onChange }: Props) {
  const drag = useRef<{ id: number; x: number; value: number } | null>(null);
  const move = (start: number, delta: number) => onChange(Math.max(min, Math.min(max, start + delta * (reverse ? -1 : 1))));
  return <div role="separator" aria-label={label} aria-orientation="vertical" aria-valuenow={Math.round(value)}
    aria-valuemin={min} aria-valuemax={Math.round(max)} tabIndex={0} className="docked-panel-divider"
    onKeyDown={e => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      move(value, e.key === "ArrowRight" ? 16 : -16);
    }}
    onPointerDown={e => {
      if (e.button !== 0 || drag.current) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      drag.current = { id: e.pointerId, x: e.clientX, value };
    }}
    onPointerMove={e => {
      const start = drag.current;
      if (start?.id === e.pointerId && start) move(start.value, e.clientX - start.x);
    }}
    onPointerUp={e => { if (drag.current?.id === e.pointerId) drag.current = null; }}
    onPointerCancel={e => { if (drag.current?.id === e.pointerId) drag.current = null; }}
    onLostPointerCapture={() => { drag.current = null; }}
  />;
}
