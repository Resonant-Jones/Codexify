// Canonical chat lane width used by message stack, approval rail, and composer.
export const CHAT_LANE_MAX_WIDTH = 880;
export const CHAT_LANE_MAX_WIDTH_CLASS = "md:max-w-[880px]";

// Inline gutter applied around the lane when deriving shell widths. Mirrors
// the default `--shell-gap` token to keep layout token-driven.
export const CHAT_LANE_INLINE_GUTTER = 16;

// Shell boundary that keeps the composer frame aligned with the lane while
// leaving a consistent gutter on either side.
export const CHAT_STAGE_MAX_WIDTH =
  CHAT_LANE_MAX_WIDTH + CHAT_LANE_INLINE_GUTTER * 2;

// Token-friendly padding expression reused by chat surfaces so portrait and
// fullscreen share the same baseline inset without bespoke numbers.
export const CHAT_LANE_INLINE_PADDING =
  "max(var(--page-pad, 0px), var(--shell-gap, 16px))";
