import React, { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type GuardianWindowMode = "docked" | "open" | "minimized";
type Props = React.PropsWithChildren<{
  mode: GuardianWindowMode;
  onModeChange: (mode: GuardianWindowMode) => void;
  onDock: () => void;
  opener: React.RefObject<HTMLButtonElement | null>;
}>;

const margin = 8;
const steps: Record<string, readonly [number, number]> = {
  ArrowLeft: [-16, 0], ArrowRight: [16, 0], ArrowUp: [0, -16], ArrowDown: [0, 16],
};
function clamp(value: number, extent: number, viewport: number) {
  return Math.max(margin, Math.min(value, viewport - extent - margin));
}

export default function GuardianChatWindow({ mode, onModeChange, onDock, opener, children }: Props) {
  // React keeps the portal target for the lifetime of this chat. Only its DOM parent moves.
  const [host] = useState(() => typeof document === "undefined" ? null : document.createElement("div"));
  const [attached, setAttached] = useState(false);
  const dock = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const handle = useRef<HTMLButtonElement>(null);
  const restore = useRef<HTMLButtonElement>(null);
  const drag = useRef<{ id: number; dx: number; dy: number } | null>(null);
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const floating = mode !== "docked";
  const requestedDock = useRef(false);

  useLayoutEffect(() => {
    if (!host || !dock.current) return;
    host.className = floating ? "guardian-chat-window-layer" : "h-full w-full";
    const parent = floating ? document.getElementById("cfy-portal-root") ?? document.body : dock.current;
    parent.appendChild(host);
    setAttached(true);
    return () => host.remove();
  }, [host, floating]);

  useLayoutEffect(() => {
    drag.current = null;
    if (!attached) return;
    if (mode === "docked") {
      if (!requestedDock.current) return;
      requestedDock.current = false;
      // The canvas resolver may need one more layout pass to reveal the dock.
      const frameId = requestAnimationFrame(() => dock.current?.focus());
      return () => cancelAnimationFrame(frameId);
    }
    if (mode === "open") handle.current?.focus();
    else restore.current?.focus();
    const fit = () => {
      const rect = frame.current?.getBoundingClientRect();
      if (!rect) return;
      const width = host?.clientWidth || window.innerWidth;
      const height = host?.clientHeight || window.innerHeight;
      setPosition(p => ({
        x: clamp(p?.x ?? width - rect.width - margin, rect.width, width),
        y: clamp(p?.y ?? height - rect.height - margin, rect.height, height),
      }));
    };
    fit();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(fit);
    if (host) observer?.observe(host);
    window.addEventListener("resize", fit);
    return () => { observer?.disconnect(); window.removeEventListener("resize", fit); };
  }, [attached, host, mode]);

  const close = () => {
    onModeChange("docked");
    opener.current?.focus();
  };
  const move = (x: number, y: number) => {
    const rect = frame.current?.getBoundingClientRect();
    if (!rect || !host) return;
    const layer = host.getBoundingClientRect();
    setPosition({
      x: clamp(x - layer.left, rect.width, host.clientWidth || window.innerWidth),
      y: clamp(y - layer.top, rect.height, host.clientHeight || window.innerHeight),
    });
  };

  return <div ref={dock} tabIndex={-1} className="h-full w-full min-h-0 min-w-0">
    {host && attached && createPortal(
      <div ref={frame} id={floating ? "guardian-chat-window" : undefined} tabIndex={floating ? -1 : undefined} role={floating ? "dialog" : undefined} aria-label={floating ? "Guardian Chat" : undefined}
        className={floating ? "guardian-chat-window" : "h-full w-full min-h-0"}
        data-window-mode={mode}
        style={floating ? { left: position?.x ?? margin, top: position?.y ?? margin } : undefined}
        onKeyDown={e => {
          if (floating && e.key === "Escape" && !e.defaultPrevented) { e.stopPropagation(); close(); }
        }}>
        {floating && <header className="guardian-chat-window__bar">
          {mode === "open" ? <>
            <button ref={handle} type="button" className="guardian-chat-window__handle" aria-label="Move Guardian Chat"
              title="Drag or use the arrow keys to move Guardian Chat"
              onPointerDown={e => {
                if (e.button !== 0 || drag.current) return;
                const rect = frame.current!.getBoundingClientRect();
                drag.current = { id: e.pointerId, dx: e.clientX - rect.left, dy: e.clientY - rect.top };
                e.currentTarget.setPointerCapture(e.pointerId);
              }}
              onPointerMove={e => {
                const start = drag.current;
                if (start && start.id === e.pointerId) move(e.clientX - start.dx, e.clientY - start.dy);
              }}
              onLostPointerCapture={() => { drag.current = null; }}
              onPointerUp={e => { if (drag.current?.id === e.pointerId) drag.current = null; }}
              onPointerCancel={e => { if (drag.current?.id === e.pointerId) drag.current = null; }}
              onKeyDown={e => {
                const rect = frame.current!.getBoundingClientRect();
                const delta = steps[e.key];
                if (delta) { e.preventDefault(); move(rect.left + delta[0], rect.top + delta[1]); }
              }}>Guardian Chat</button>
            <button type="button" aria-label="Minimize Guardian Chat" onClick={() => onModeChange("minimized")}>Minimize</button>
          </> : <button ref={restore} type="button" onClick={() => onModeChange("open")}>Restore Guardian Chat</button>}
          <button type="button" aria-label="Dock Guardian Chat" onClick={() => { requestedDock.current = true; onDock(); }}>Dock</button>
          <button type="button" aria-label="Close Guardian Chat" onClick={close}>Close</button>
        </header>}
        <div className="h-full min-h-0 w-full" hidden={mode === "minimized"}>{children}</div>
      </div>, host
    )}
    {!host && children}
  </div>;
}
