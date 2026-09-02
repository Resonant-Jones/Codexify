import { CSSProperties, useState } from "react";

import { getMobileTapTargetStyle } from "@/components/persona/layout/mobileInteractionContract";
import ShareSheet from "@/components/share/ShareSheet";
import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import type { PeopleMessagingState } from "@/features/contacts/usePeopleMessagingState";
import { usePressFeedback } from "@/hooks/usePressFeedback";
import { useRuntimeRouteCapability } from "@/lib/runtimeRouteCapabilities";

type ShareButtonProps = {
  targetType: "thread" | "document";
  targetId: number;
  className?: string;
  style?: CSSProperties;
  dataState?: "active" | "inactive";
  isPhoneShell?: boolean;
  /** Shell-owned People state used to open the destination Conversation
   *  after a successful Send to Person.  Absent = Copy Link only. */
  peopleState?: PeopleMessagingState | null;
  /** Canonical shell thread scope used ONLY as a new-Conversation origin. */
  sourceThreadId?: number | null;
  /** Canonical project scope for project-only surfaces (optional). */
  sourceProjectId?: number | null;
};

export function ShareButton({
  targetType,
  targetId,
  className,
  style,
  dataState,
  isPhoneShell = false,
  peopleState = null,
  sourceThreadId = null,
  sourceProjectId = null,
}: ShareButtonProps) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const pressFeedback = usePressFeedback({ enabled: isPhoneShell });
  const capability = useRuntimeRouteCapability(
    SUPPORTED_PROFILE_ROUTE_LABELS.DIRECT_MESSAGES
  );

  return (
    <>
      <button
        onClick={() => setSheetOpen(true)}
        {...pressFeedback.getPressFeedbackProps({
          className,
          style: {
            ...getMobileTapTargetStyle(isPhoneShell),
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid var(--panel-border)",
            backgroundColor: "var(--panel-bg)",
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 500,
            color: "var(--text)",
            transition: "all 200ms",
            ...style,
          },
        })}
        data-state={dataState}
      >
        Share
      </button>

      <ShareSheet
        targetType={targetType}
        targetId={targetId}
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        capabilityState={capability.state}
        peopleState={peopleState}
        sourceThreadId={sourceThreadId}
        sourceProjectId={sourceProjectId}
      />
    </>
  );
}
