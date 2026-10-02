import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import FrameCard from "@/components/surface/FrameCard";
import { Button } from "@/components/ui/button";
import "./onboarding.css";

export default function LearningModal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    return () => {
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return createPortal(
    <div
      className="learning-scrim"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className="learning-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            onClose();
          }
          if (e.key !== "Tab") return;
          const nodes = Array.from(
            ref.current?.querySelectorAll<HTMLElement>(
              "button:not(:disabled), input:not(:disabled), select, a[href]"
            ) ?? []
          );
          const first = nodes[0],
            last = nodes[nodes.length - 1];
          if (!first) {
            e.preventDefault();
            return;
          }
          if (
            e.shiftKey &&
            (document.activeElement === first || document.activeElement === ref.current)
          ) {
            e.preventDefault();
            last.focus();
          } else if (
            !e.shiftKey &&
            (document.activeElement === last || document.activeElement === ref.current)
          ) {
            e.preventDefault();
            first.focus();
          }
        }}
      >
        <FrameCard hoverPop={false}>
          <header className="learning-header">
            <strong>{title}</strong>
            <Button variant="ghost" size="sm" aria-label={`Close ${title}`} onClick={onClose}>
              Close
            </Button>
          </header>
          {children}
        </FrameCard>
      </div>
    </div>,
    document.body
  );
}
