import { ChevronUp } from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
} from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getMobileTapTargetStyle } from "@/components/persona/layout/mobileInteractionContract";

import styles from "./SolarEffortControl.module.css";

const PROVIDER_DEFAULT = "default";
const PROVIDER_DEFAULT_LABEL = "Provider default";

function effortTone(level: string) {
  return /^(xhigh|extra[-_ ]high)$/i.test(level) ? "extra-high" : level;
}

function effortLabel(level: string) {
  const label = effortTone(level).replace(/[-_]/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function scalePosition(index: number, lastIndex: number) {
  return lastIndex === 0 ? 0.5 : index / lastIndex;
}

type SolarEffortControlProps = {
  levels: readonly string[];
  value: string;
  onChange?: (level: string) => void;
  disabled?: boolean;
  compact?: boolean;
  variant?: "bare" | "chip";
};

export function SolarEffortControl({
  levels,
  value,
  onChange,
  disabled = false,
  compact = false,
  variant = "bare",
}: SolarEffortControlProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const rangeRef = useRef<HTMLInputElement>(null);
  const defaultRef = useRef<HTMLButtonElement>(null);
  const selectedIndex = levels.indexOf(value);
  const hasSelection = selectedIndex >= 0;
  const index = Math.max(0, selectedIndex);
  const lastIndex = levels.length - 1;
  const label = hasSelection ? effortLabel(value) : PROVIDER_DEFAULT_LABEL;

  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => rangeRef.current?.focus({ preventScroll: true }));
    return () => cancelAnimationFrame(frame);
  }, [open]);

  if (levels.length === 0) return null;

  const selectIndex = (nextIndex: number) => {
    const next = levels[nextIndex];
    if (!disabled && next !== undefined && next !== value) onChange?.(next);
  };

  const selectFromDefault = (event: KeyboardEvent<HTMLInputElement>) => {
    if (hasSelection || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === "End") {
      event.preventDefault();
      selectIndex(lastIndex);
    } else if (["Home", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      event.preventDefault();
      selectIndex(0);
    }
  };

  const handlePanelKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const leaveByTab = event.key === "Tab" && (
      event.shiftKey ? event.target === rangeRef.current : event.target === defaultRef.current
    );
    if (event.key !== "Escape" && !leaveByTab) return;
    event.preventDefault();
    event.stopPropagation();
    setOpen(false);
    triggerRef.current?.focus({ preventScroll: true });
  };

  return (
    <div className={styles.control} data-compact={compact}>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          {...{ ref: triggerRef }}
          aria-label={`Thinking effort: ${label}`}
          aria-haspopup="dialog"
          aria-controls={open ? panelId : undefined}
          className={styles.trigger}
          data-variant={variant}
          style={getMobileTapTargetStyle(compact, { square: true })}
          disabled={disabled}
        >
          <span className={styles.triggerLabel}>{compact && !hasSelection ? "Default" : label}</span>
          <ChevronUp aria-hidden="true" className={styles.chevron} />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          id={panelId}
          role="dialog"
          aria-label="Thinking effort"
          side="top"
          align="start"
          collisionPadding={12}
          className={styles.panel}
          onKeyDown={handlePanelKeyDown}
          onBlur={(event) => {
            const next = event.relatedTarget;
            if (next && next !== triggerRef.current && !event.currentTarget.contains(next)) {
              setOpen(false);
            }
          }}
        >
          <div className={styles.heading}>
            <span>Thinking effort</span>
            <span className={styles.selectedLabel}>{label}</span>
          </div>
          <div
            className={styles.housing}
            data-tone={hasSelection ? effortTone(value) : undefined}
            dir="ltr"
          >
            <div
              className={styles.scale}
              style={{ "--solar-position": scalePosition(index, lastIndex) } as CSSProperties}
            >
              <div className={styles.rail} aria-hidden="true">
                <div className={styles.fill} />
                {levels.map((level, step) => (
                  <span
                    key={level}
                    className={styles.stop}
                    style={{ "--solar-position": scalePosition(step, lastIndex) } as CSSProperties}
                  />
                ))}
              </div>
              <span className={styles.thumb} aria-hidden="true" />
              <input
                ref={rangeRef}
                className={styles.range}
                type="range"
                min={0}
                max={lastIndex}
                step={1}
                value={index}
                aria-label="Thinking effort"
                aria-valuetext={label}
                disabled={disabled}
                onChange={(event) => selectIndex(event.currentTarget.valueAsNumber)}
                onKeyDown={selectFromDefault}
                onPointerUp={(event) => {
                  // A tap at the native minimum may leave its value unchanged.
                  if (!hasSelection && event.button === 0) {
                    selectIndex(event.currentTarget.valueAsNumber);
                  }
                }}
              />
            </div>
          </div>
          <div className={styles.labels} aria-hidden="true" data-single={lastIndex === 0}>
            {levels.map((level) => <span key={level}>{effortLabel(level)}</span>)}
          </div>
          <button
            ref={defaultRef}
            type="button"
            className={styles.reset}
            aria-pressed={!hasSelection}
            disabled={disabled}
            onClick={() => {
              if (hasSelection) onChange?.(PROVIDER_DEFAULT);
            }}
          >
            {PROVIDER_DEFAULT_LABEL}
          </button>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
