// Canonical chat lane width used by message stack, approval rail, and composer.
export const CHAT_LANE_MAX_WIDTH = 888;
export const CHAT_LANE_MAX_WIDTH_CLASS = "md:max-w-[888px]";
// Inline gutter applied around the lane when deriving shell widths. Mirrors
// the default `--shell-gap` token to keep layout token-driven.
export const CHAT_LANE_INLINE_GUTTER = 16;
export const CHAT_LANE_GUTTER_CLASS =
  "px-[max(var(--page-pad,0px),var(--shell-gap,16px))]";
export const CHAT_LANE_STAGE_GUTTER_CLASS =
  "mx-[max(var(--page-pad,0px),var(--shell-gap,16px))]";

// Shell boundary for the composer frame. Keep identical to lane width so the
// composer edge aligns to the shared chat column contract.
export const CHAT_STAGE_MAX_WIDTH = CHAT_LANE_MAX_WIDTH;
export const CHAT_COMPOSER_SHELL_MARGIN_CLASS =
  "mx-[max(var(--page-pad,0px),var(--shell-gap,16px))]";
export const CHAT_COMPOSER_SHELL_PAD_CLASS =
  "px-[max(var(--page-pad,0px),var(--shell-gap,16px))]";

// Shared class contract for control-row bottom seating in the composer.
export const CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS = "pb-[2px]";
export const CHAT_COMPOSER_CONTROLS_PAD_CLASS = "px-3 pb-3 pt-2";
export const CHAT_COMPOSER_INNER_PAD_CLASS = "px-3 pb-3 pt-3";
export const CHAT_COMPOSER_TEXTAREA_PAD_CLASS = "px-3 pt-3";
export const CHAT_COMPOSER_ATTACHMENTS_PAD_CLASS = "px-3 pt-2";
export const CHAT_COMPOSER_SEND_PAD_CLASS = "pr-2";

// Outer Guardian surface ceiling for fullscreen layouts. Keeps the shell large
// enough for future workspace activation without letting the empty side bands
// dominate the scene on very wide displays.
export const GUARDIAN_SHELL_MAX_WIDTH = 1200;

// Static class companion for shell consumers that need the canonical Tailwind
// contract alongside the numeric token.
export const GUARDIAN_SHELL_MAX_WIDTH_CLASS = "max-w-[1200px]";

// Token-friendly padding expression reused by chat surfaces so portrait and
// fullscreen share the same baseline inset without bespoke numbers.
export const CHAT_LANE_INLINE_PADDING =
  "max(var(--page-pad, 0px), var(--shell-gap, 16px))";
