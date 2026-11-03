import { useOnboarding } from "@/features/onboarding/OnboardingProvider";
import { ContactRound } from "lucide-react";
import { useEffect, useRef } from "react";

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
  const onboarding = useOnboarding();
  const ownedState = usePeopleMessagingState();
  const state = parentState ?? ownedState;
  const capability = useRuntimeRouteCapability(
    SUPPORTED_PROFILE_ROUTE_LABELS.DIRECT_MESSAGES
  );

  // The launcher's unread badge reads the SAME caller-local projection the
  // Inbox badges read, from the shared People state owner.  There is no
  // second projection and no separate notification authority: the launcher
  // simply renders the derived total the surfaces already share.
  const unreadTotal = state.unreadTotal;
  const showUnreadBadge =
    capability.state === "available" && unreadTotal > 0;

  // The People window is the only place the Inbox is rendered, so the
  // projection would otherwise only exist while People is open.  The launcher
  // loads it once per state owner so the badge can display the unread count
  // on its own, and refreshes it when People closes so the count the badge
  // shows is the one the user just saw.
  useEffect(() => {
    void state.ensureUnreadProjection();
  }, [state.ensureUnreadProjection]);

  const peopleWasOpen = useRef(false);
  useEffect(() => {
    if (peopleWasOpen.current && !state.peopleOpen) {
      void state.refreshUnreadProjection();
    }
    peopleWasOpen.current = state.peopleOpen;
  }, [state.peopleOpen, state.refreshUnreadProjection]);

  return (
    <>
      <button
        type="button"
        className={className}
        data-testid="contacts-launcher"
        aria-label={
          showUnreadBadge
            ? `People (${unreadTotal} unread message${
                unreadTotal === 1 ? "" : "s"
              })`
            : "People"
        }
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
        {showUnreadBadge ? (
          <span
            data-testid="contacts-launcher-unread-badge"
            aria-hidden="true"
            className="absolute -right-1 -top-1 flex min-w-4 items-center justify-center rounded-full bg-[var(--accent)] px-1 text-[10px] font-semibold leading-none text-[var(--accent-contrast,#fff)]"
          >
            {unreadTotal > 99 ? "99+" : unreadTotal}
          </span>
        ) : null}
      </button>
      {onboarding?.incomplete && <button type="button" className="text-xs learning-muted" aria-label="Resume optional Codexify setup" onClick={event => { event.stopPropagation(); onboarding.resume(); }}>Setup</button>}
      <ContactsWindow
        state={state}
        contacts={[]}
        capabilityState={capability.state}
        sourceThreadId={sourceThreadId ?? null}
      />
    </>
  );
}
