import * as React from "react";

type DrawerTab = "terminal" | "logs" | "receipts" | "problems";

const DRAWER_TABS: Array<{ id: DrawerTab; label: string }> = [
  { id: "terminal", label: "Terminal" },
  { id: "logs", label: "Logs" },
  { id: "receipts", label: "Receipts" },
  { id: "problems", label: "Problems" },
];

const STORAGE_KEY_DRAWER_HEIGHT = "codexify-command-center-drawer-height";

function readStoredDrawerHeight(): number {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_DRAWER_HEIGHT);
    const parsed = Number(stored);
    if (Number.isFinite(parsed) && parsed >= 160 && parsed <= 600) return parsed;
  } catch {
    // localStorage unavailable
  }
  return 280;
}

function writeStoredDrawerHeight(height: number): void {
  try {
    localStorage.setItem(STORAGE_KEY_DRAWER_HEIGHT, String(height));
  } catch {
    // localStorage unavailable
  }
}

export interface CommandCenterBottomDrawerProps {
  open: boolean;
  onToggle: () => void;
}

export default function CommandCenterBottomDrawer({
  open,
  onToggle,
}: CommandCenterBottomDrawerProps) {
  const [activeTab, setActiveTab] = React.useState<DrawerTab>("terminal");
  const [drawerHeight, setDrawerHeight] = React.useState<number>(readStoredDrawerHeight);
  const resizeRef = React.useRef<HTMLDivElement>(null);
  const resizeStartY = React.useRef<number>(0);
  const resizeStartHeight = React.useRef<number>(0);

  const handleResizeMouseDown = React.useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault();
      resizeStartY.current = event.clientY;
      resizeStartHeight.current = drawerHeight;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const delta = resizeStartY.current - moveEvent.clientY;
        const nextHeight = Math.max(160, Math.min(600, resizeStartHeight.current + delta));
        setDrawerHeight(nextHeight);
      };

      const handleMouseUp = () => {
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("mouseup", handleMouseUp);
        writeStoredDrawerHeight(drawerHeight);
      };

      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    },
    [drawerHeight]
  );

  const drawerBody = React.useMemo((): React.ReactNode => {
    switch (activeTab) {
      case "terminal":
        return (
          <div
            data-testid="command-center-drawer-terminal"
            style={{
              display: "flex",
              flexDirection: "column",
              height: "100%",
              padding: "12px",
              gap: "8px",
            }}
          >
            <div
              style={{
                flex: 1,
                borderRadius: "var(--tile-radius)",
                border: "1px solid var(--panel-border)",
                background: "color-mix(in oklab, var(--panel-bg) 90%, transparent)",
                padding: "12px",
                fontFamily: "monospace",
                fontSize: "13px",
                lineHeight: 1.5,
                color: "var(--muted)",
                overflowY: "auto",
              }}
            >
              <p style={{ color: "var(--muted)" }}>
                Terminal execution is not enabled in this Command Center build.
              </p>
              <p style={{ color: "var(--muted)", marginTop: "8px" }}>
                This drawer tab is a scaffold for future terminal access. No shell
                commands can be executed from this panel.
              </p>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "4px 12px",
                borderRadius: "var(--tile-radius)",
                border: "1px solid var(--panel-border)",
                background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
              }}
            >
              <span
                style={{
                  fontFamily: "monospace",
                  fontSize: "13px",
                  color: "var(--muted)",
                }}
              >
                $ _
              </span>
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--muted)",
                }}
              >
                (input disabled — terminal is non-executable)
              </span>
            </div>
          </div>
        );

      case "logs":
        return (
          <div
            data-testid="command-center-drawer-logs"
            style={{
              padding: "var(--card-pad)",
              height: "100%",
              overflowY: "auto",
            }}
          >
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Log stream will appear here once available. This panel is a placeholder
              for future runtime log inspection.
            </p>
          </div>
        );

      case "receipts":
        return (
          <div
            data-testid="command-center-drawer-receipts"
            style={{
              padding: "var(--card-pad)",
              height: "100%",
              overflowY: "auto",
            }}
          >
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Run receipts and lineage records will appear here once available. This panel
              is a placeholder for future receipt inspection.
            </p>
          </div>
        );

      case "problems":
        return (
          <div
            data-testid="command-center-drawer-problems"
            style={{
              padding: "var(--card-pad)",
              height: "100%",
              overflowY: "auto",
            }}
          >
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Detected problems and diagnostics will appear here once available. This panel
              is a placeholder for future problem surfaces.
            </p>
          </div>
        );

      default:
        return null;
    }
  }, [activeTab]);

  return (
    <div
      data-testid="command-center-bottom-drawer"
      style={{
        flexShrink: 0,
        borderTop: "1px solid var(--panel-border)",
        display: "flex",
        flexDirection: "column",
        height: open ? `${drawerHeight}px` : "0px",
        overflow: "hidden",
        transition: "height 200ms ease-out",
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
      }}
    >
      {/* Resize handle */}
      {open && (
        <div
          ref={resizeRef}
          data-testid="command-center-drawer-resize-handle"
          role="separator"
          aria-label="Resize drawer height"
          tabIndex={0}
          onMouseDown={handleResizeMouseDown}
          style={{
            height: "6px",
            cursor: "ns-resize",
            background: "transparent",
            borderTop: "1px solid var(--panel-border)",
            flexShrink: 0,
          }}
        />
      )}

      {/* Header with tabs */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "2px",
          padding: "0 var(--card-pad)",
          borderBottom: "1px solid var(--panel-border)",
          flexShrink: 0,
          minHeight: "36px",
        }}
      >
        {DRAWER_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            data-testid={`command-center-drawer-tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "6px 12px",
              border: "none",
              borderBottom:
                activeTab === tab.id
                  ? "2px solid var(--accent-strong)"
                  : "2px solid transparent",
              background: "transparent",
              color:
                activeTab === tab.id ? "var(--text)" : "var(--muted)",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: activeTab === tab.id ? 600 : 400,
              lineHeight: 1,
              transition: "color 120ms ease-out, border-color 120ms ease-out",
            }}
          >
            {tab.label}
          </button>
        ))}

        <div style={{ flex: 1 }} />

        <button
          type="button"
          aria-label="Close drawer"
          data-testid="command-center-drawer-close"
          onClick={onToggle}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "28px",
            height: "28px",
            border: "none",
            borderRadius: "var(--tile-radius)",
            background: "transparent",
            color: "var(--muted)",
            cursor: "pointer",
            fontSize: "14px",
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        {drawerBody}
      </div>
    </div>
  );
}
