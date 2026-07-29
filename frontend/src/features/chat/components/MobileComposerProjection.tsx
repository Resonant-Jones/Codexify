/**
 * MobileComposerProjection.tsx
 *
 * Renders the mobile composer projection surface as a portal to document.body,
 * anchored above the software keyboard using the visual viewport coordinate system.
 *
 * This layer is a temporary presentation projection only. The canonical composer
 * slot remains nested at the bottom of the Guardian frame in normal flow.
 *
 * One logical composer state owns both the base and projection presentations.
 * The projection surface is the active interactive element while visible; the
 * base slot becomes inert.
 */
import { createPortal } from "react-dom";
import type { ReactNode } from "react";
import { useViewportInsets } from "@/hooks/useViewportInsets";

function getPortalTarget(): HTMLElement {
  return (
    document.getElementById("cfy-portal-root") ??
    document.getElementById("app") ??
    document.getElementById("root") ??
    document.body
  );
}

export function MobileComposerProjection({
  children,
  visible,
}: {
  children: ReactNode;
  visible: boolean;
}) {
  const { keyboardInset } = useViewportInsets(true);

  if (!visible) return null;

  const portalTarget = getPortalTarget();
  const bottomInset = Math.max(0, keyboardInset);

  return createPortal(
    <div
      data-composer-surface="projection"
      data-visible={visible ? "true" : "false"}
      className="fixed left-0 right-0 z-[9999] flex justify-center"
      style={{
        bottom: bottomInset,
        pointerEvents: "auto",
        padding: "0 var(--card-pad, 12px)",
        paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + var(--card-pad, 12px))",
      }}
      role="region"
      aria-label="Mobile composer projection"
    >
      <div
        className="w-full"
        style={{
          maxWidth: "var(--chat-lane-max-width, 720px)",
        }}
      >
        {children}
      </div>
    </div>,
    portalTarget
  );
}

export default MobileComposerProjection;
