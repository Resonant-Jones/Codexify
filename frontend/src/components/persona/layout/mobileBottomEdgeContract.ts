/**
 * Mobile Bottom Edge Contract
 *
 * Shared rules for keyboard-adjacent UI on phone-class widths.
 * Prevents two-footer fighting between the composer and any ambient chrome.
 */

/** Controls whether the mobile composer shows its full control strip */
export type ComposerBottomEdgeMode = "full" | "collapsed";

/** Safe-area-aware bottom inset for the composer when keyboard is open */
export const MOBILE_COMPOSER_KEYBOARD_BOTTOM_PAD_PX = 0;

/**
 * Returns true when ambient bottom chrome (FAB, control pills, extra spacers)
 * should be suppressed on phone-class widths to keep the keyboard flush
 * against the active input surface.
 */
export function shouldSuppressMobileAmbientBottom(
  isPhoneClass: boolean,
  isKeyboardOpen: boolean
): boolean {
  return isPhoneClass && isKeyboardOpen;
}

/**
 * Returns the effective composer bottom edge mode.
 * When keyboard is open on mobile, collapse nonessential controls to keep
 * the input surface tight against the keyboard.
 */
export function resolveComposerBottomEdgeMode(
  isPhoneClass: boolean,
  isKeyboardOpen: boolean
): ComposerBottomEdgeMode {
  return isPhoneClass && isKeyboardOpen ? "collapsed" : "full";
}

/**
 * Returns the effective bottom padding for the message lane.
 * On mobile with keyboard open, the composer itself provides the bottom anchor —
 * the message lane should not add extra padding that would push content up.
 */
export function resolveMessageLaneBottomPad(
  isPhoneClass: boolean,
  isKeyboardOpen: boolean,
  baseComposerReserve: number
): number {
  if (isPhoneClass && isKeyboardOpen) {
    return 0;
  }
  return baseComposerReserve;
}
