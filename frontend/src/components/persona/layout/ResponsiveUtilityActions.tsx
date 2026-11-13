import { Ellipsis } from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

type UtilityAction = { label: string; control: ReactNode };

/** Collapse against the actual shell width, including embedded desktop panes. */
export default function ResponsiveUtilityActions({
  containerRef,
  actions,
}: {
  containerRef: RefObject<HTMLDivElement | null>;
  actions: UtilityAction[];
}) {
  const [compact, setCompact] = useState(false);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const actionsRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const measure = () => {
      const width = container.getBoundingClientRect().width;
      // A zero measurement is possible before layout (and in jsdom).
      if (width > 0) setCompact(width < 1280);
    };
    measure();
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    observer?.observe(container);
    window.addEventListener("resize", measure);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [containerRef]);

  useEffect(() => {
    setOpen(false);
  }, [compact]);

  useEffect(() => {
    if (!open) return;
    actionsRef.current
      ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
      ?.focus();
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    // Portaled dialogs may stop bubbling to protect their own drag/resize UI.
    document.addEventListener("pointerdown", dismiss, true);
    return () => document.removeEventListener("pointerdown", dismiss, true);
  }, [open]);

  return (
    <div
      ref={rootRef}
      className="codexify-utilities"
      data-compact={compact ? "true" : "false"}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          event.preventDefault();
          setOpen(false);
          triggerRef.current?.focus();
        }
      }}
      onBlur={(event) => {
        if (
          event.relatedTarget instanceof Node &&
          !event.currentTarget.contains(event.relatedTarget)
        ) {
          setOpen(false);
        }
      }}
    >
      {compact && (
        <button
          ref={triggerRef}
          type="button"
          className="pill-tab codexify-utilities__toggle"
          aria-label="Utilities"
          title="Utilities"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);
            }
          }}
        >
          <Ellipsis className="h-5 w-5" aria-hidden="true" />
        </button>
      )}
      {/* Keep launchers mounted: their portaled windows must survive dismissal
          and resizing of the utility disclosure. */}
      <div
        id={panelId}
        ref={actionsRef}
        className="codexify-utilities__actions"
        role="group"
        aria-label="Utilities"
        hidden={compact && !open}
      >
        {actions.filter(({ control }) => control != null).map(({ label, control }) => (
          <div className="codexify-utilities__action" key={label}>
            {control}
            {compact && (
              <span className="codexify-utilities__label" aria-hidden="true">
                {label}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
