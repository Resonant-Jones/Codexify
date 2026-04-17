import { ChevronDown } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getMobileTapTargetStyle } from "@/components/persona/layout/mobileInteractionContract";
import { usePressFeedback } from "@/hooks/usePressFeedback";
import { cn } from "@/lib/utils";

export type ComposerSelectOption = {
  value: string;
  label: string;
  description?: string;
  meta?: string | null;
  disabled?: boolean;
  supportsChat?: boolean;
  supportsVision?: boolean;
  supportsTextInput?: boolean;
  modelKind?: "chat" | "vision_chat" | "utility";
};

type ComposerSelectMenuProps = {
  ariaLabel: string;
  menuLabel: string;
  valueLabel: string;
  options: ComposerSelectOption[];
  isPhoneShell?: boolean;
  selectedValue?: string | null;
  disabled?: boolean;
  emptyLabel?: string;
  openSignal?: number;
  onSelect: (value: string) => void;
};

const COMPOSER_SELECT_MENU_COLLISION_PADDING = 12;
const COMPOSER_SELECT_MENU_SIDE_OFFSET = 10;
const COMPOSER_SELECT_MENU_MAX_HEIGHT = "24rem";
const COMPOSER_SELECT_MENU_VIEWPORT_MAX_HEIGHT = `min(${COMPOSER_SELECT_MENU_MAX_HEIGHT}, var(--dropdown-menu-available-height, calc(100vh - ${COMPOSER_SELECT_MENU_COLLISION_PADDING * 2}px)))`;

export function ComposerSelectMenu({
  ariaLabel,
  menuLabel,
  valueLabel,
  options,
  isPhoneShell = false,
  selectedValue,
  disabled = false,
  emptyLabel = "No options available.",
  openSignal,
  onSelect,
}: ComposerSelectMenuProps) {
  const [open, setOpen] = useState(false);
  const pressFeedback = usePressFeedback({
    enabled: !disabled,
    visualMode: isPhoneShell ? "mobile" : "none",
  });
  const scrollRegionRef = useRef<HTMLDivElement | null>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const menuSurface =
    "color-mix(in oklab, var(--panel-bg) 88%, var(--text) 12%)";
  const menuHoverSurface =
    "color-mix(in oklab, var(--panel-bg) 78%, var(--text) 22%)";
  const menuSelectedSurface =
    "color-mix(in oklab, var(--accent) 14%, var(--panel-bg) 86%)";

  const enabledOptionIndexes = useMemo(
    () =>
      options.reduce<number[]>((indexes, option, index) => {
        if (!disabled && !option.disabled) {
          indexes.push(index);
        }
        return indexes;
      }, []),
    [disabled, options]
  );

  const selectedIndex = useMemo(
    () => options.findIndex((option) => option.value === selectedValue),
    [options, selectedValue]
  );

  const getDefaultActiveIndex = useCallback(() => {
    if (
      selectedIndex >= 0 &&
      !disabled &&
      !options[selectedIndex]?.disabled
    ) {
      return selectedIndex;
    }
    return enabledOptionIndexes[0] ?? -1;
  }, [disabled, enabledOptionIndexes, options, selectedIndex]);

  const [activeIndex, setActiveIndex] = useState(() => getDefaultActiveIndex());

  useEffect(() => {
    if (typeof openSignal !== "number" || openSignal <= 0 || disabled) return;
    setOpen(true);
  }, [disabled, openSignal]);

  useEffect(() => {
    if (!open) return;
    setActiveIndex(getDefaultActiveIndex());
  }, [getDefaultActiveIndex, open]);

  const scrollIndexIntoView = useCallback(
    (index: number, behavior: ScrollBehavior = "auto") => {
      const scrollRegion = scrollRegionRef.current;
      const optionNode = optionRefs.current[index];
      if (!scrollRegion || !optionNode) return;

      const centeredTop =
        optionNode.offsetTop - (scrollRegion.clientHeight - optionNode.offsetHeight) / 2;
      const maxScrollTop = Math.max(
        0,
        scrollRegion.scrollHeight - scrollRegion.clientHeight
      );
      const nextScrollTop = Math.min(Math.max(0, centeredTop), maxScrollTop);

      scrollRegion.scrollTo({
        top: nextScrollTop,
        behavior,
      });
    },
    []
  );

  useLayoutEffect(() => {
    if (!open || activeIndex < 0) return;
    const frame = window.requestAnimationFrame(() => {
      optionRefs.current[activeIndex]?.focus({ preventScroll: true });
      scrollIndexIntoView(activeIndex);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [activeIndex, open, scrollIndexIntoView]);

  const moveActiveIndex = useCallback(
    (direction: 1 | -1) => {
      if (enabledOptionIndexes.length === 0) return;
      const currentPosition = enabledOptionIndexes.indexOf(activeIndex);
      const fallbackPosition = direction > 0 ? -1 : enabledOptionIndexes.length;
      const nextPosition = Math.min(
        enabledOptionIndexes.length - 1,
        Math.max(0, (currentPosition >= 0 ? currentPosition : fallbackPosition) + direction)
      );
      setActiveIndex(enabledOptionIndexes[nextPosition] ?? activeIndex);
    },
    [activeIndex, enabledOptionIndexes]
  );

  const activateOption = useCallback(
    (index: number) => {
      const option = options[index];
      if (!option || disabled || option.disabled) return;
      setOpen(false);
      onSelect(option.value);
    },
    [disabled, onSelect, options]
  );

  const handleMenuKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (enabledOptionIndexes.length === 0) return;

      if (event.key === "ArrowDown") {
        event.preventDefault();
        moveActiveIndex(1);
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        moveActiveIndex(-1);
        return;
      }

      if (event.key === "Home") {
        event.preventDefault();
        setActiveIndex(enabledOptionIndexes[0] ?? -1);
        return;
      }

      if (event.key === "End") {
        event.preventDefault();
        setActiveIndex(enabledOptionIndexes[enabledOptionIndexes.length - 1] ?? -1);
        return;
      }

      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (activeIndex >= 0) {
          activateOption(activeIndex);
        }
      }
    },
    [activateOption, activeIndex, enabledOptionIndexes, moveActiveIndex]
  );

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          {...pressFeedback.getPressFeedbackProps({
            className: cn(
              "inline-flex h-8 min-w-0 items-center gap-1.5 rounded-none border-0 bg-transparent px-0 py-0 text-[12px] transition-colors",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color-mix(in_oklab,var(--panel-border)_72%,var(--text)_28%)]",
              disabled ? "cursor-not-allowed opacity-45" : "opacity-100 hover:opacity-80",
            ),
            style: {
              ...getMobileTapTargetStyle(isPhoneShell),
              transform:
                !isPhoneShell && pressFeedback.pressed
                  ? "translateY(1px)"
                  : undefined,
              color: isPhoneShell
                ? "color-mix(in oklab, var(--text) 86%, var(--muted) 14%)"
                : "var(--text)",
              height: "var(--composer-control-size, 2rem)",
            },
          })}
          aria-label={ariaLabel}
          disabled={disabled}
        >
          <span className="truncate">{valueLabel}</span>
          <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="top"
        align="start"
        sideOffset={COMPOSER_SELECT_MENU_SIDE_OFFSET}
        collisionPadding={COMPOSER_SELECT_MENU_COLLISION_PADDING}
        aria-label={menuLabel}
        className="flex min-h-0 flex-col overflow-hidden rounded-[var(--card-radius,19px)] border p-0 shadow-xl"
        onKeyDown={handleMenuKeyDown}
        style={{
          minWidth: "max(var(--dropdown-menu-trigger-width, 0px), 11.5rem)",
          maxWidth: "min(20rem, calc(100vw - 24px))",
          maxHeight: COMPOSER_SELECT_MENU_VIEWPORT_MAX_HEIGHT,
          borderColor: "color-mix(in oklab, var(--panel-border) 84%, var(--text) 16%)",
          background: menuSurface,
          boxShadow:
            "0 14px 32px color-mix(in srgb, rgba(0, 0, 0, 0.24) 78%, var(--panel-border) 22%)",
          color: "var(--text)",
        }}
      >
        <div
          className="w-full shrink-0 px-3 py-2 text-center text-[10px] font-medium uppercase tracking-[0.12em] leading-none"
          style={{ color: "var(--muted)" }}
        >
          {menuLabel}
        </div>
        {options.length > 0 ? (
          <div
            ref={scrollRegionRef}
            data-composer-select-scroll-region="true"
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain pb-1"
          >
            {options.map((option, index) => {
              const selected = option.value === selectedValue;
              const focused = index === activeIndex;
              return (
                <DropdownMenuItem
                  key={option.value}
                  ref={(node) => {
                    optionRefs.current[index] = node;
                  }}
                  data-option-index={index}
                  data-selected={selected ? "true" : "false"}
                  aria-disabled={disabled || option.disabled ? "true" : undefined}
                  disabled={disabled || option.disabled}
                  tabIndex={focused ? 0 : -1}
                  title={
                    option.description
                      ? `${option.label} — ${option.description}`
                      : option.label
                  }
                  onFocus={() => setActiveIndex(index)}
                  onMouseEnter={() => {
                    if (!disabled && !option.disabled) {
                      setActiveIndex(index);
                    }
                  }}
                  onClick={() => activateOption(index)}
                  className={cn(
                    "cursor-pointer rounded-none border-0 px-2.5 py-1.5 focus:outline-none hover:bg-[color-mix(in_oklab,var(--panel-bg)_78%,var(--text)_22%)] disabled:cursor-not-allowed disabled:opacity-45"
                  )}
                  style={{
                    background: selected
                      ? menuSelectedSurface
                      : focused
                        ? menuHoverSurface
                        : undefined,
                  }}
                >
                  <span className="flex w-full min-w-0 items-center justify-between gap-3">
                    <span className="min-w-0">
                      <span className="block truncate text-[12px] font-medium">
                        {option.label}
                      </span>
                      {option.description ? (
                        <span
                          className="block truncate text-[10px]"
                          style={{ color: "var(--muted)" }}
                        >
                          {option.description}
                        </span>
                      ) : null}
                    </span>
                    {option.meta ? (
                      <span className="shrink-0 text-[10px]" style={{ color: "var(--muted)" }}>
                        {option.meta}
                      </span>
                    ) : null}
                  </span>
                </DropdownMenuItem>
              );
            })}
          </div>
        ) : (
          <div className="px-2.5 py-2 text-[11px]" style={{ color: "var(--muted)" }}>
            {emptyLabel}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default ComposerSelectMenu;
