import { ContactRound } from "lucide-react";

import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import { useRuntimeRouteCapability } from "@/lib/runtimeRouteCapabilities";

import ContactsWindow from "./ContactsWindow";
import FloatingConversation from "./FloatingConversation";
import { usePeopleMessagingState } from "./usePeopleMessagingState";

type ContactsLauncherProps = {
  className?: string;
  /** Canonical route-derived thread scope; only used to capture
   *  Conversation origin at creation time (never to rebind existing
   *  Conversations). */
  sourceThreadId?: number | null;
};

export default function ContactsLauncher({
  className,
  sourceThreadId = null,
}: ContactsLauncherProps) {
  const state = usePeopleMessagingState();
  const capability = useRuntimeRouteCapability(
    SUPPORTED_PROFILE_ROUTE_LABELS.DIRECT_MESSAGES
  );

  return (
    <>
      <button
        type="button"
        className={className}
        data-testid="contacts-launcher"
        aria-label="People"
        title="People"
        onClick={state.openPeople}
      >
        <ContactRound className="h-4 w-4" aria-hidden="true" />
      </button>
      <ContactsWindow
        state={state}
        contacts={[]}
        capabilityState={capability.state}
        sourceThreadId={sourceThreadId ?? null}
      />
      <FloatingConversation state={state} />
    </>
  );
}
