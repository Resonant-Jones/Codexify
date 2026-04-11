/**
 * usePressFeedback Hook
 *
 * Manages press/release state for mobile touch controls.
 * Provides a consistent interaction experience that is:
 * - reduced-motion safe
 * - centralized (avoids scattered timing literals)
 * - React-idiomatic (uses useState/useCallback)
 */

import { useCallback, useRef, useState } from "react";
import { MOBILE_INTERACTION } from "@/components/persona/layout/mobileInteractionContract";

export type PressFeedbackPhase = "idle" | "pressed" | "submitting" | "submitted";

/**
 * Configuration for the press feedback hook.
 */
export type UsePressFeedbackOptions = {
  /** Time in ms before automatically releasing (default: 800ms for submit feedback) */
  autoReleaseMs?: number;
  /** Whether this control is disabled */
  disabled?: boolean;
};

/**
 * Returns press feedback state and handlers for a touch control.
 *
 * @example
 * ```tsx
 * const { phase, pressProps, release } = usePressFeedback();
 * <button {...pressProps}>Press me</button>
 * ```
 */
export function usePressFeedback(options: UsePressFeedbackOptions = {}) {
  const { autoReleaseMs, disabled = false } = options;
  const [phase, setPhase] = useState<PressFeedbackPhase>("idle");
  const releaseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isActiveRef = useRef(false);

  /**
   * Call when touch/pointer down begins.
   */
  const onPressStart = useCallback(() => {
    if (disabled) return;
    isActiveRef.current = true;
    setPhase("pressed");
  }, [disabled]);

  /**
   * Call when touch/pointer up ends (releases naturally).
   */
  const onPressEnd = useCallback(() => {
    if (disabled || !isActiveRef.current) return;
    isActiveRef.current = false;
    setPhase("idle");
  }, [disabled]);

  /**
   * Call to initiate a submit sequence (e.g., composer send).
   * Automatically transitions through submitting -> submitted -> idle.
   */
  const onSubmit = useCallback(() => {
    if (disabled) return;
    isActiveRef.current = true;

    // Clear any existing timer
    if (releaseTimerRef.current) {
      clearTimeout(releaseTimerRef.current);
    }

    setPhase("submitting");

    // Brief confirmation state
    releaseTimerRef.current = setTimeout(() => {
      if (!isActiveRef.current) return;
      setPhase("submitted");

      // Return to idle
      releaseTimerRef.current = setTimeout(() => {
        isActiveRef.current = false;
        setPhase("idle");
      }, MOBILE_INTERACTION.settleMs);
    }, MOBILE_INTERACTION.pressScaleDownMs);
  }, [disabled]);

  /**
   * Force-release back to idle state.
   */
  const release = useCallback(() => {
    if (releaseTimerRef.current) {
      clearTimeout(releaseTimerRef.current);
      releaseTimerRef.current = null;
    }
    isActiveRef.current = false;
    setPhase("idle");
  }, []);

  /**
   * Props to spread onto the interactive element.
   * Handles pointer events for touch/click feedback.
   */
  const pressProps = {
    onPointerDown: onPressStart,
    onPointerUp: onPressEnd,
    onPointerLeave: onPressEnd,
    onPointerCancel: onPressEnd,
  };

  return {
    /** Current phase: 'idle' | 'pressed' | 'submitting' | 'submitted' */
    phase,
    /** Whether the element should appear pressed */
    isPressed: phase === "pressed" || phase === "submitting",
    /** Props to spread onto the interactive element */
    pressProps,
    /** Initiate a submit sequence */
    onSubmit,
    /** Force release to idle */
    release,
  };
}
