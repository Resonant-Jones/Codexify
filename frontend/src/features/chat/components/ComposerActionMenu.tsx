import { ImagePlus, Layers3, Paperclip, Volume2 } from "lucide-react";
import { useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  getComposerControlSurfaceStyle,
  getMobileTapTargetStyle,
} from "@/components/persona/layout/mobileInteractionContract";
import { usePressFeedback } from "@/hooks/usePressFeedback";
import { cn } from "@/lib/utils";

type DepthMode = "shallow" | "normal" | "deep" | "diagnostic";

type DepthOption = {
  value: DepthMode;
  label: string;
  description: string;
};

type ComposerActionMenuProps = {
  disabled?: boolean;
  isPhoneShell?: boolean;
  depthMode: DepthMode;
  depthOptions: DepthOption[];
  onAttach: () => void;
  onGenerateImage: () => void;
  onDepthChange: (mode: DepthMode) => void;
  onVoiceTurn?: () => void;
  voiceTurnDisabled?: boolean;
  voiceTurnLabel?: string;
};

export function ComposerActionMenu({
  disabled = false,
  isPhoneShell = false,
  depthMode,
  depthOptions,
  onAttach,
  onGenerateImage,
  onDepthChange,
  onVoiceTurn,
  voiceTurnDisabled = false,
  voiceTurnLabel = "Upload voice turn",
}: ComposerActionMenuProps) {
  const [open, setOpen] = useState(false);
  const pressFeedback = usePressFeedback({
    enabled: !disabled,
    visualMode: isPhoneShell ? "mobile" : "none",
  });

  const closeAndRun = (action: () => void) => {
    setOpen(false);
    action();
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          {...pressFeedback.getPressFeedbackProps({
            className: cn(
              "inline-flex h-8 w-8 items-center justify-center rounded-lg border border-transparent bg-transparent text-[11px] leading-none transition-colors",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color-mix(in_oklab,var(--panel-border)_72%,var(--text)_28%)]",
              disabled
                ? "cursor-not-allowed opacity-35"
                : isPhoneShell
                  ? "opacity-82 hover:bg-[color-mix(in_oklab,var(--panel-bg)_78%,var(--text)_22%)] hover:opacity-100"
                  : "opacity-100 hover:bg-[color-mix(in_oklab,var(--panel-bg)_78%,var(--text)_22%)]",
              !isPhoneShell &&
                "bg-[color-mix(in_oklab,var(--panel-bg)_92%,transparent)]"
            ),
            style: {
              ...getMobileTapTargetStyle(isPhoneShell, { square: true }),
              ...getComposerControlSurfaceStyle(isPhoneShell, {
                variant: "trigger",
              }),
              transform:
                !isPhoneShell && pressFeedback.pressed
                  ? "translateY(1px)"
                  : undefined,
              color: "var(--text)",
              width: "var(--composer-control-size, 2rem)",
              height: "var(--composer-control-size, 2rem)",
            },
          })}
          aria-label="Open composer actions"
          disabled={disabled}
        >
          <span className="text-[22px] leading-none">+</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="top"
        align="start"
        sideOffset={10}
        collisionPadding={12}
        className="min-w-[15rem] rounded-2xl p-2"
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
          Composer actions
        </div>
        {/* Beta-disabled: document upload is broken in this build */}
        <DropdownMenuItem
          onClick={() => {
            setOpen(false);
            // Show toast for beta limitation
            try {
              window.dispatchEvent(new CustomEvent("cfy:toast", {
                detail: { message: "Document upload is not available in this beta build", duration: 4000 }
              }));
            } catch {}
          }}
          className="cursor-not-allowed px-2 py-2 opacity-50"
          style={{ borderRadius: "0.8rem" }}
        >
          <span className="flex items-center gap-2">
            <Paperclip className="h-3.5 w-3.5" />
            <span>Attach file</span>
            <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--accent)] text-[var(--text-on-accent)] opacity-80">
              Beta
            </span>
          </span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => closeAndRun(onGenerateImage)}
          className="cursor-pointer px-2 py-2"
          style={{ borderRadius: "0.8rem" }}
        >
          <span className="flex items-center gap-2">
            <ImagePlus className="h-3.5 w-3.5" />
            <span>Generate image</span>
          </span>
        </DropdownMenuItem>
        {onVoiceTurn ? (
          <DropdownMenuItem
            onClick={() => {
              if (voiceTurnDisabled) return;
              closeAndRun(onVoiceTurn);
            }}
            disabled={voiceTurnDisabled}
            className="cursor-pointer px-2 py-2 disabled:cursor-not-allowed disabled:opacity-45"
            style={{ borderRadius: "0.8rem" }}
          >
            <span className="flex items-center gap-2">
              <Volume2 className="h-3.5 w-3.5" />
              <span>{voiceTurnLabel}</span>
            </span>
          </DropdownMenuItem>
        ) : null}
        <div
          className="px-2 pb-2 pt-3 text-[10px] font-medium uppercase tracking-[0.18em]"
          style={{ color: "color-mix(in oklab, var(--muted) 82%, transparent)" }}
        >
          RAG depth
        </div>
        {depthOptions.map((option) => {
          const selected = option.value === depthMode;
          return (
            <DropdownMenuItem
              key={option.value}
              onClick={() => closeAndRun(() => onDepthChange(option.value))}
              className="cursor-pointer px-2 py-2"
              style={{
                borderRadius: "0.8rem",
                background:
                  selected
                    ? "color-mix(in oklab, var(--accent) 8%, transparent)"
                    : "transparent",
              }}
            >
              <span className="flex w-full items-start gap-2">
                <Layers3
                  className="mt-0.5 h-3.5 w-3.5 shrink-0"
                  style={{ color: selected ? "var(--accent)" : "currentColor" }}
                />
                <span className="min-w-0">
                  <span
                    className="block text-[12px] font-medium"
                    style={{ color: selected ? "var(--accent)" : "var(--text)" }}
                  >
                    {option.label}
                  </span>
                  <span
                    className="mt-0.5 block text-[11px]"
                    style={{ color: "var(--muted)" }}
                  >
                    {option.description}
                  </span>
                </span>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default ComposerActionMenu;
