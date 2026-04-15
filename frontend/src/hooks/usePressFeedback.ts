import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  CSSProperties,
  FocusEventHandler,
  KeyboardEventHandler,
  PointerEventHandler,
} from "react";

import { cn } from "@/lib/utils";

import {
  MOBILE_INTERACTION_CLASS,
  getMobilePressFeedbackStyle,
} from "@/components/persona/layout/mobileInteractionContract";

type PressFeedbackBindOptions = {
  className?: string;
  style?: CSSProperties;
};

type PressFeedbackButtonProps = {
  className?: string;
  style?: CSSProperties;
  "data-press-feedback"?: "idle" | "pressed";
  "data-press-feedback-motion"?: "normal" | "reduced";
  onPointerDown?: PointerEventHandler<HTMLButtonElement>;
  onPointerUp?: PointerEventHandler<HTMLButtonElement>;
  onPointerCancel?: PointerEventHandler<HTMLButtonElement>;
  onPointerLeave?: PointerEventHandler<HTMLButtonElement>;
  onPointerMove?: PointerEventHandler<HTMLButtonElement>;
  onBlur?: FocusEventHandler<HTMLButtonElement>;
  onKeyDown?: KeyboardEventHandler<HTMLButtonElement>;
  onKeyUp?: KeyboardEventHandler<HTMLButtonElement>;
};

type UsePressFeedbackOptions = {
  enabled: boolean;
};

function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return undefined;
    }

    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => {
      setPrefersReducedMotion(media.matches);
    };

    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", updatePreference);
      return () => media.removeEventListener("change", updatePreference);
    }

    media.addListener(updatePreference);
    return () => media.removeListener(updatePreference);
  }, []);

  return prefersReducedMotion;
}

export function usePressFeedback({ enabled }: UsePressFeedbackOptions) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const [pressed, setPressed] = useState(false);
  const pressedPointerIdRef = useRef<number | null>(null);
  const pointerStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!enabled && pressed) {
      setPressed(false);
    }
    if (!enabled) {
      pressedPointerIdRef.current = null;
      pointerStartRef.current = null;
    }
  }, [enabled, pressed]);

  const clearPressed = useCallback(() => {
    setPressed(false);
    pressedPointerIdRef.current = null;
    pointerStartRef.current = null;
  }, []);

  const handlePointerDown = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerDown"]>
  >((event) => {
    if (!enabled) return;
    if (event.button != null && event.button !== 0) return;
    pressedPointerIdRef.current = event.pointerId;
    pointerStartRef.current = { x: event.clientX, y: event.clientY };
    setPressed(true);
  }, [enabled]);

  const handlePointerUp = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerUp"]>
  >(() => {
    if (!enabled) return;
    clearPressed();
  }, [clearPressed, enabled]);

  const handlePointerMove = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerMove"]>
  >((event) => {
    if (!enabled || pressedPointerIdRef.current == null) return;
    if (event.pointerId !== pressedPointerIdRef.current) return;

    const start = pointerStartRef.current;
    if (!start) return;

    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    const movedDistance = Math.hypot(dx, dy);

    if (movedDistance >= MOBILE_INTERACTION.pressDragCancelDistancePx) {
      clearPressed();
    }
  }, [clearPressed, enabled]);

  const handlePointerCancel = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerCancel"]>
  >(() => {
    if (!enabled) return;
    clearPressed();
  }, [clearPressed, enabled]);

  const handlePointerLeave = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerLeave"]>
  >(() => {
    if (!enabled) return;
    clearPressed();
  }, [clearPressed, enabled]);

  const handleBlur = useCallback<NonNullable<PressFeedbackButtonProps["onBlur"]>>(() => {
    if (!enabled) return;
    clearPressed();
  }, [clearPressed, enabled]);

  const handleKeyDown = useCallback<
    NonNullable<PressFeedbackButtonProps["onKeyDown"]>
  >((event) => {
    if (!enabled || event.repeat) return;
    if (event.key !== " " && event.key !== "Enter") return;
    setPressed(true);
  }, [enabled]);

  const handleKeyUp = useCallback<NonNullable<PressFeedbackButtonProps["onKeyUp"]>>(
    (event) => {
      if (!enabled) return;
      if (event.key !== " " && event.key !== "Enter") return;
      clearPressed();
    },
    [clearPressed, enabled]
  );

  return useMemo(() => {
    const baseProps: PressFeedbackButtonProps = enabled
      ? {
          className: MOBILE_INTERACTION_CLASS.pressFeedback,
          style: getMobilePressFeedbackStyle(prefersReducedMotion),
          "data-press-feedback": pressed ? "pressed" : "idle",
          "data-press-feedback-motion": prefersReducedMotion ? "reduced" : "normal",
          onPointerDown: handlePointerDown,
          onPointerUp: handlePointerUp,
          onPointerCancel: handlePointerCancel,
          onPointerLeave: handlePointerLeave,
          onPointerMove: handlePointerMove,
          onBlur: handleBlur,
          onKeyDown: handleKeyDown,
          onKeyUp: handleKeyUp,
        }
      : {};

    return {
      pressed,
      prefersReducedMotion,
      releasePressed: clearPressed,
      getPressFeedbackProps: ({
        className,
        style,
      }: PressFeedbackBindOptions = {}) => ({
        ...baseProps,
        className: cn(baseProps.className, className) || undefined,
        style: {
          ...baseProps.style,
          ...style,
        },
      }),
    };
  }, [
    enabled,
    handleBlur,
    handleKeyDown,
    handleKeyUp,
    handlePointerCancel,
    handlePointerDown,
    handlePointerLeave,
    handlePointerMove,
    handlePointerUp,
    prefersReducedMotion,
    pressed,
  ]);
}

export type PressFeedbackResult = ReturnType<typeof usePressFeedback>;
