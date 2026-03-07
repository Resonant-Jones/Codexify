import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export type ComposerSelectOption = {
  value: string;
  label: string;
  description?: string;
  meta?: string | null;
  disabled?: boolean;
};

type ComposerSelectMenuProps = {
  ariaLabel: string;
  menuLabel: string;
  valueLabel: string;
  options: ComposerSelectOption[];
  selectedValue?: string | null;
  disabled?: boolean;
  emptyLabel?: string;
  openSignal?: number;
  onSelect: (value: string) => void;
};

export function ComposerSelectMenu({
  ariaLabel,
  menuLabel,
  valueLabel,
  options,
  selectedValue,
  disabled = false,
  emptyLabel = "No options available.",
  openSignal,
  onSelect,
}: ComposerSelectMenuProps) {
  const [open, setOpen] = useState(false);
  const compactModelMenu = menuLabel.trim().toLowerCase() === "model";

  useEffect(() => {
    if (typeof openSignal !== "number" || openSignal <= 0 || disabled) return;
    setOpen(true);
  }, [disabled, openSignal]);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={ariaLabel}
          disabled={disabled}
          className={cn(
            "inline-flex min-w-0 items-center gap-1 rounded-md border px-2.5 py-1.5 text-[11px] transition-colors",
            disabled ? "cursor-not-allowed opacity-45" : "hover:opacity-95"
          )}
          style={{
            borderColor: "color-mix(in oklab, var(--panel-border) 88%, transparent)",
            background:
              "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 92%, transparent)",
            color: "var(--text)",
          }}
        >
          <span className="truncate">{valueLabel}</span>
          <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="top"
        align="start"
        sideOffset={10}
        collisionPadding={12}
        className="min-w-[14rem] overflow-hidden rounded-2xl p-2"
        style={{
          border: "none",
          background:
            "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 82%, transparent)",
          backdropFilter: "blur(18px)",
          boxShadow: "0 18px 42px rgba(0, 0, 0, 0.34)",
          color: "var(--text)",
        }}
      >
        <div
          className="px-2 pb-2 text-[10px] font-medium uppercase tracking-[0.18em]"
          style={{ color: "color-mix(in oklab, var(--muted) 82%, transparent)" }}
        >
          {menuLabel}
        </div>
        {options.length > 0 ? (
          <div className="space-y-1">
            {options.map((option) => {
              const selected = option.value === selectedValue;
              return (
                <DropdownMenuItem
                  key={option.value}
                  disabled={disabled || option.disabled}
                  onClick={() => {
                    if (option.disabled) return;
                    setOpen(false);
                    onSelect(option.value);
                  }}
                  className="cursor-pointer px-2 py-2.5 focus:outline-none disabled:cursor-not-allowed disabled:opacity-45"
                  style={{
                    borderRadius: "0.8rem",
                    background: selected
                      ? "color-mix(in oklab, var(--accent) 10%, transparent)"
                      : "transparent",
                  }}
                >
                  <span
                    className={cn(
                      "flex w-full min-w-0 justify-between gap-3",
                      compactModelMenu ? "items-center" : "items-start"
                    )}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-[12px] font-medium">
                        {option.label}
                      </span>
                      {!compactModelMenu && option.description ? (
                        <span
                          className="mt-0.5 block text-[11px]"
                          style={{ color: "var(--muted)" }}
                        >
                          {option.description}
                        </span>
                      ) : null}
                    </span>
                    {option.meta ? (
                      <span
                        className="shrink-0 rounded-full border px-1.5 py-0.5 text-[10px]"
                        style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
                      >
                        {option.meta}
                      </span>
                    ) : selected ? (
                      <span
                        className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px]"
                        style={{
                          background: "color-mix(in oklab, var(--accent) 10%, transparent)",
                          color: "color-mix(in oklab, var(--accent) 88%, white 12%)",
                        }}
                      >
                        Active
                      </span>
                    ) : null}
                  </span>
                </DropdownMenuItem>
              );
            })}
          </div>
        ) : (
          <div className="px-2 py-2 text-[11px]" style={{ color: "var(--muted)" }}>
            {emptyLabel}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default ComposerSelectMenu;
