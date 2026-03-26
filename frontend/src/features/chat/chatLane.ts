// Canonical chat lane width used by message stack, approval rail, and composer.
export const CHAT_LANE_MAX_WIDTH = 880;

// Shared Tailwind class for lane-bound surfaces that match the canonical width.
export const CHAT_LANE_MAX_WIDTH_CLASS = "md:max-w-[880px]";

// Token-friendly padding expression reused by chat surfaces so portrait and
// fullscreen share the same baseline inset without bespoke numbers.
export const CHAT_LANE_INLINE_PADDING =
  "max(var(--page-pad, 0px), var(--shell-gap, 16px))";
