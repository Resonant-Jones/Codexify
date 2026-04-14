import type { CSSProperties } from "react";

import {
  getMobileTapTargetStyle,
  getMobileTopNavDockStyle,
  getMobileTopNavRailStyle,
  getMobileWorkspaceSummonCopy,
} from "./mobileInteractionContract";

export { getMobileTopNavDockStyle, getMobileTopNavRailStyle, getMobileWorkspaceSummonCopy };

export function getMobileNavigationControlStyle(
  isPhoneShell: boolean,
  options: { square?: boolean } = {}
): CSSProperties {
  return getMobileTapTargetStyle(isPhoneShell, options);
}
