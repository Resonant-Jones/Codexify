import { ContactRound } from "lucide-react";

import { SUPPORTED_PROFILE_ROUTE_LABELS } from "@/contracts/supportedProfileRoutes";
import { useRuntimeRouteCapability } from "@/lib/runtimeRouteCapabilities";

import ContactsWindow from "./ContactsWindow";
import {
  usePeopleMessagingState,
  type PeopleMessagingState,
} from "./usePeopleMessagingState";

type ContactsLauncherProps = {
  className?: string;
  /** Canonical route-derived thread scope; only used to capture
   *  Conversation origin at creation time (never to rebind existing
   *  Conversations). */
  sourceThreadId?: number | null;
  /**
   * Optional parent-owned People state.  AppShell owns this state so the
   * portable floating Conversation survives chrome switches (dock vs
   * frame-first tools menu) that unmount this launcher.  When omitted the
   * launcher owns its own state (standalone mounts).
   */
  state?: PeopleMessagingState;
};

export default function ContactsLauncher({
  className,
  sourceThreadId = null,
  state: parentState,
}: ContactsLauncherProps) {
  const ownedState = usePeopleMessagingState();
  const state = parentState ?? ownedState;
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
        onClick={(event) => {
          // The launcher is also mounted inside the Guardian tools menu,
          // whose container closes itself when a child click reaches it.
          // Bubbling here would unmount the People state owner before the
          // window opens; keep the click local and open the window.
          event.stopPropagation();
          state.openPeople();
        }}
      >
        <ContactRound className="h-4 w-4" aria-hidden="true" />
      </button>
      <ContactsWindow
        state={state}
        contacts={[]}
        capabilityState={capability.state}
        sourceThreadId={sourceThreadId ?? null}
      />
    </>
  );
}
