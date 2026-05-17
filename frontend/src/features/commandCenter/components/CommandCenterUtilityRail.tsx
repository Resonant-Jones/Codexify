import * as React from "react";

export type CommandCenterLensId =
  | "agent-command"
  | "observability"
  | "runtime-health"
  | "event-console"
  | "deep-settings"
  | "extensions";

interface LensEntry {
  id: CommandCenterLensId;
  label: string;
  icon: string;
  ariaLabel: string;
}

const LENSES: LensEntry[] = [
  { id: "agent-command", label: "Agent Command", icon: "⚡", ariaLabel: "Agent Command lens" },
  { id: "observability", label: "Observability", icon: "◉", ariaLabel: "Observability lens" },
  { id: "runtime-health", label: "Runtime Health", icon: "♥", ariaLabel: "Runtime Health lens" },
  { id: "heartbeat", label: "Heartbeat", icon: "⊛", ariaLabel: "Heartbeat pipeline lens" },
  { id: "event-console", label: "Event Console", icon: "☰", ariaLabel: "Event Console lens" },
  { id: "deep-settings", label: "Deep Settings", icon: "⚙", ariaLabel: "Deep Settings lens" },
  { id: "extensions", label: "Extensions", icon: "⬡", ariaLabel: "Extensions lens" },
];

const STORAGE_KEY_RAIL_SIDE = "codexify-command-center-rail-side";
const STORAGE_KEY_RAIL_PINNED = "codexify-command-center-rail-pinned";

type RailSide = "left" | "right";

function readStoredRailSide(): RailSide {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_RAIL_SIDE);
    if (stored === "left" || stored === "right") return stored;
  } catch {
    // localStorage unavailable
  }
  return "left";
}

function writeStoredRailSide(side: RailSide): void {
  try {
    localStorage.setItem(STORAGE_KEY_RAIL_SIDE, side);
  } catch {
    // localStorage unavailable
  }
}

function readStoredRailPinned(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_RAIL_PINNED);
    if (stored === "true") return true;
    if (stored === "false") return false;
  } catch {
    // localStorage unavailable
  }
  return false;
}

function writeStoredRailPinned(pinned: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY_RAIL_PINNED, String(pinned));
  } catch {
    // localStorage unavailable
  }
}

export interface CommandCenterUtilityRailProps {
  activeLens: CommandCenterLensId;
  onLensChange: (lensId: CommandCenterLensId) => void;
  onToggleDrawer: () => void;
}

export default function CommandCenterUtilityRail({
  activeLens,
  onLensChange,
  onToggleDrawer,
}: CommandCenterUtilityRailProps) {
  const [railSide, setRailSide] = React.useState<RailSide>(readStoredRailSide);
  const [pinned, setPinned] = React.useState<boolean>(readStoredRailPinned);
  const [hovered, setHovered] = React.useState(false);
  const railRef = React.useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // collapse on blur if not pinned
  const expanded = pinned || hovered;

  const sideClass = railSide === "left" ? "" : "flex-row-reverse";

  const handleMouseEnter = React.useCallback(() => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setHovered(true);
  }, []);

  const handleMouseLeave = React.useCallback(() => {
    // brief delay before collapsing to avoid flicker
    hoverTimeoutRef.current = setTimeout(() => {
      setHovered(false);
    }, 150);
  }, []);

  const handleTogglePin = React.useCallback(() => {
    setPinned((current) => {
      const next = !current;
      writeStoredRailPinned(next);
      return next;
    });
  }, []);

  const handleToggleSide = React.useCallback(() => {
    setRailSide((current) => {
      const next: RailSide = current === "left" ? "right" : "left";
      writeStoredRailSide(next);
      return next;
    });
  }, []);

  // keyboard navigation for the rail
  const handleRailKeyDown = React.useCallback(
    (event: React.KeyboardEvent) => {
      const currentIndex = LENSES.findIndex((l) => l.id === activeLens);
      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        event.preventDefault();
        const nextIndex = (currentIndex + 1) % LENSES.length;
        onLensChange(LENSES[nextIndex].id);
      } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        event.preventDefault();
        const prevIndex = (currentIndex - 1 + LENSES.length) % LENSES.length;
        onLensChange(LENSES[prevIndex].id);
      }
    },
    [activeLens, onLensChange]
  );

  // force focus edge affordance on mount so keyboard users can Tab into rail
  React.useEffect(() => {
    if (!pinned && railRef.current) {
      // ensure rail has tabIndex so keyboard users can discover it
    }
  }, [pinned]);

  React.useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      ref={railRef}
      className={`flex ${sideClass}`}
      data-testid="command-center-utility-rail-container"
      style={{
        flexShrink: 0,
        position: "relative",
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onKeyDown={handleRailKeyDown}
      role="navigation"
      aria-label="Command Center lens navigation"
    >
      {/* Edge affordance / handle — always visible for discoverability */}
      <div
        data-testid="command-center-utility-rail-edge"
        style={{
          width: "4px",
          cursor: "pointer",
          background: "transparent",
          flexShrink: 0,
          borderLeft: railSide === "left" ? undefined : "1px solid var(--panel-border)",
          borderRight: railSide === "left" ? "1px solid var(--panel-border)" : undefined,
        }}
        tabIndex={0}
        aria-label={`Command Center rail — ${railSide} side, ${pinned ? "pinned" : "unpinned"}. Press Enter to toggle pin.`}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setHovered((current) => !current);
          }
        }}
      />

      {/* Rail content */}
      <div
        data-testid="command-center-utility-rail"
        className="flex flex-col gap-1"
        style={{
          width: expanded ? "48px" : "0px",
          overflow: "hidden",
          transition: "width 180ms ease-out",
          flexShrink: 0,
          padding: expanded ? "var(--card-pad) 6px" : "0",
          borderLeft: railSide === "left" ? "1px solid var(--panel-border)" : undefined,
          borderRight: railSide === "right" ? "1px solid var(--panel-border)" : undefined,
          background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        }}
      >
        {LENSES.map((lens) => (
          <button
            key={lens.id}
            type="button"
            aria-label={lens.ariaLabel}
            aria-current={activeLens === lens.id ? "true" : undefined}
            data-testid={`command-center-rail-item-${lens.id}`}
            onClick={() => onLensChange(lens.id)}
            title={lens.label}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "36px",
              height: "36px",
              margin: "0 auto",
              border: "none",
              borderRadius: "var(--tile-radius)",
              background:
                activeLens === lens.id
                  ? "color-mix(in oklab, var(--accent-weak) 70%, transparent)"
                  : "transparent",
              color:
                activeLens === lens.id
                  ? "var(--text-on-accent)"
                  : "var(--muted)",
              cursor: "pointer",
              fontSize: "16px",
              lineHeight: 1,
              transition: "background 120ms ease-out, color 120ms ease-out",
              position: "relative",
            }}
          >
            {/* Active pill indicator */}
            {activeLens === lens.id && (
              <span
                style={{
                  position: "absolute",
                  [railSide === "left" ? "left" : "right"]: "-2px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: "3px",
                  height: "18px",
                  borderRadius: "3px",
                  background: "var(--accent-strong)",
                }}
                aria-hidden="true"
              />
            )}
            {lens.icon}
          </button>
        ))}

        {/* Separator */}
        <div
          style={{
            height: "1px",
            margin: "4px 6px",
            background: "var(--panel-border)",
            flexShrink: 0,
          }}
          aria-hidden="true"
        />

        {/* Pin toggle */}
        <button
          type="button"
          aria-label={pinned ? "Unpin rail" : "Pin rail"}
          data-testid="command-center-rail-pin-toggle"
          onClick={handleTogglePin}
          title={pinned ? "Unpin rail" : "Pin rail"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "36px",
            height: "36px",
            margin: "0 auto",
            border: "none",
            borderRadius: "var(--tile-radius)",
            background: pinned
              ? "color-mix(in oklab, var(--accent-weak) 40%, transparent)"
              : "transparent",
            color: pinned ? "var(--text-on-accent)" : "var(--muted)",
            cursor: "pointer",
            fontSize: "14px",
            lineHeight: 1,
            transition: "background 120ms ease-out, color 120ms ease-out",
          }}
        >
          {pinned ? "📌" : "📍"}
        </button>

        {/* Side toggle */}
        <button
          type="button"
          aria-label={`Move rail to ${railSide === "left" ? "right" : "left"} side`}
          data-testid="command-center-rail-side-toggle"
          onClick={handleToggleSide}
          title={`Move rail to ${railSide === "left" ? "right" : "left"}`}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "36px",
            height: "36px",
            margin: "0 auto",
            border: "none",
            borderRadius: "var(--tile-radius)",
            background: "transparent",
            color: "var(--muted)",
            cursor: "pointer",
            fontSize: "14px",
            lineHeight: 1,
            transition: "background 120ms ease-out",
          }}
        >
          {railSide === "left" ? "→" : "←"}
        </button>

        {/* Drawer toggle */}
        <button
          type="button"
          aria-label="Toggle bottom drawer"
          data-testid="command-center-rail-drawer-toggle"
          onClick={onToggleDrawer}
          title="Toggle bottom drawer"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "36px",
            height: "36px",
            margin: "0 auto",
            border: "none",
            borderRadius: "var(--tile-radius)",
            background: "transparent",
            color: "var(--muted)",
            cursor: "pointer",
            fontSize: "14px",
            lineHeight: 1,
            transition: "background 120ms ease-out",
          }}
        >
          ▤
        </button>
      </div>
    </div>
  );
}
