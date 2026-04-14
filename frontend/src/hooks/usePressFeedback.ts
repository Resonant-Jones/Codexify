import { useCallback, useEffect, useMemo, useState } from "react";
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

  useEffect(() => {
    if (!enabled && pressed) {
      setPressed(false);
    }
  }, [enabled, pressed]);

  const clearPressed = useCallback(() => {
    setPressed(false);
  }, []);

  const handlePointerDown = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerDown"]>
  >((event) => {
    if (!enabled) return;
    if (event.button != null && event.button !== 0) return;
    setPressed(true);
  }, [enabled]);

  const handlePointerUp = useCallback<
    NonNullable<PressFeedbackButtonProps["onPointerUp"]>
  >(() => {
    if (!enabled) return;
    clearPressed();
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
          onBlur: handleBlur,
          onKeyDown: handleKeyDown,
          onKeyUp: handleKeyUp,
        }
      : {};

    return {
      pressed,
      prefersReducedMotion,
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
    handlePointerUp,
    prefersReducedMotion,
    pressed,
  ]);
}

export type PressFeedbackResult = ReturnType<typeof usePressFeedback>;
