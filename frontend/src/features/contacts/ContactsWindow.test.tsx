import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ContactsLauncher from "./ContactsLauncher";
import ContactsWindow from "./ContactsWindow";
import FloatingConversation from "./FloatingConversation";
import type { ContactListItem } from "./types";
import {
  usePeopleMessagingState,
  type PeopleMessagingState,
} from "./usePeopleMessagingState";

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  useRuntimeRouteCapability: (label: string) => ({
    mounted: ["direct_messages"],
    declared: {},
    ready: true,
    state: label === "direct_messages" ? "available" : "unavailable",
  }),
  useRuntimeRouteCapabilities: () => ({
    mounted: ["direct_messages"],
    declared: {},
    ready: true,
    states: { direct_messages: "available" },
  }),
  ensureRuntimeRouteCapabilitiesLoaded: () => Promise.resolve(),
  getRuntimeRouteCapabilityState: () => "available",
  markRuntimeRouteUnavailable: () => {},
  markRuntimeRouteUnavailableIfNotFound: () => false,
  __resetRuntimeRouteCapabilitiesForTests: () => {},
}));

vi.mock("@/lib/direct-messages", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/direct-messages")>();
  return {
    ...actual,
    normalizeDirectMessageError: (error: unknown) =>
      error instanceof Error ? error : new Error("request failed"),
    searchDirectMessageProfiles: vi.fn(() => Promise.resolve([])),
    resolveDirectMessageRelationship: vi.fn(),
    fetchDirectMessageRelationships: vi.fn(() => Promise.resolve([])),
    fetchDirectMessageConversations: vi.fn(() => Promise.resolve([])),
    fetchRelationshipConversations: vi.fn(() => Promise.resolve([])),
    createDirectMessageConversation: vi.fn(),
    fetchDirectMessageConversation: vi.fn(),
    fetchDirectMessageMessages: vi.fn(() => Promise.resolve([])),
    sendDirectMessage: vi.fn(),
    fetchThreadProjectScope: vi.fn(() => Promise.resolve(null)),
    fetchProjectLabelMap: vi.fn(() => Promise.resolve(new Map())),
  };
});

const contacts: ContactListItem[] = [
  {
    id: "ava",
    displayName: "Ava Martinez",
    localAlias: "ava-m",
    relationshipNote: "Met through the neighborhood studio.",
    preferredContactMethod: "Signal",
    externalHandles: ["@ava.studio"],
    favorite: true,
    discoveryPathLabel: "Manual entry",
    createdAt: "2026-01-10T00:00:00Z",
  },
  {
    id: "ben",
    displayName: "Ben Okafor",
    localAlias: "ben-o",
    relationshipNote: "Private planning note.",
    preferredContactMethod: "Email",
    externalHandles: ["ben@example.test"],
    archived: true,
  },
  {
    id: "cass",
    displayName: "Cass Rivera",
    relationshipNote: "Blocked after an unsolicited request.",
    preferredContactMethod: "Matrix",
    externalHandles: ["@cass:example.test"],
    blocked: true,
  },
];

function makeState(overrides: Partial<PeopleMessagingState> = {}): PeopleMessagingState {
  return {
    peopleOpen: true,
    activeTab: "inbox",
    selectedRelationshipId: null,
    selectedConversationId: null,
    floatingConversationId: null,
    floatingMode: null,
    draftsByConversationId: {},
    messagesByConversationId: {},
    loadedByConversationId: {},
    conversationMetaById: {},
    openPeople: vi.fn(),
    closePeople: vi.fn(),
    setTab: vi.fn(),
    openRelationship: vi.fn(),
    openConversation: vi.fn(),
    closeConversation: vi.fn(),
    popOutConversation: vi.fn(() => true),
    minimizeFloating: vi.fn(),
    restoreFloating: vi.fn(),
    closeFloating: vi.fn(),
    returnFloatingToPeople: vi.fn(),
    setDraft: vi.fn(),
    cacheConversationMeta: vi.fn(),
    replaceMessages: vi.fn(),
    appendServerMessage: vi.fn(),
    markTranscriptLoaded: vi.fn(),
    ...overrides,
  };
}

function renderWithPortal(ui: ReactNode, onShellClick = vi.fn()) {
  const shell = document.createElement("div");
  shell.addEventListener("click", onShellClick);
  const portal = document.createElement("div");
  portal.id = "cfy-portal-root";
  shell.appendChild(portal);
  document.body.appendChild(shell);
  const result = render(ui);
  return { ...result, shell, portal, onShellClick };
}

describe("ContactsLauncher (global People affordance)", () => {
  it("opens the People window without leaking the click to an enclosing menu", async () => {
    const user = userEvent.setup();
    // Simulates the Guardian tools-menu mount: the launcher is rendered
    // inside a React container that closes itself when any child click
    // reaches it (as the tools DropdownMenuContent's synthetic onClick
    // does).  If the launcher's click bubbles, the container unmounts the
    // state owner before the window can open — the exact live defect on
    // the frame-first Guardian shell.
    const onContainerClick = vi.fn();
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);
    render(
      <div onClick={onContainerClick}>
        <ContactsLauncher />
      </div>
    );

    await user.click(screen.getByRole("button", { name: "People" }));

    expect(await screen.findByTestId("contacts-window")).toBeInTheDocument();
    expect(onContainerClick).not.toHaveBeenCalled();
  });

  it("keeps the floating conversation alive across launcher remounts with parent-owned state", async () => {
    // The AppShell renders the launcher inside chrome that changes between
    // views (dock vs frame-first tools menu).  The People state owner must
    // therefore live ABOVE the launcher: when the launcher unmounts and
    // remounts, the floating Conversation_ID, draft, and mode must survive.
    let capturedState: PeopleMessagingState | null = null;
    const Harness = () => {
      const state = usePeopleMessagingState();
      capturedState = state;
      const [chromeVariant, setChromeVariant] = useState("dock");
      return (
        <div>
          <button type="button" onClick={() => setChromeVariant("menu")}>
            switch-chrome
          </button>
          {chromeVariant === "dock" ? (
            <div data-testid="chrome-dock">
              <ContactsLauncher state={state} />
            </div>
          ) : null}
          <FloatingConversation state={state} />
        </div>
      );
    };
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);
    const user = userEvent.setup();
    render(<Harness />);

    // Pop a conversation out (as DirectConversation does) and park a draft.
    await act(async () => {
      capturedState?.popOutConversation("conv-1", {
        conversation_id: "conv-1",
        relationship_id: "rel-1",
        kind: "direct",
        created_at: "2026-09-01T00:00:00Z",
        latest_activity_at: "2026-09-01T00:00:00Z",
        participants: [],
        peer: {
          node_id: "node-local",
          profile_id: "profile-bob",
          username: "bob",
          username_state: "active",
          display_name: "Bob Tester",
          avatar_url: null,
        },
        origin: {
          created_by_profile_id: null,
          origin_project_id: null,
          origin_thread_id: null,
          created_at: "2026-09-01T00:00:00Z",
        },
        placement: { project_id: null, created_at: null, updated_at: null },
        latest_message: null,
      });
      capturedState?.setDraft("conv-1", "parked draft");
    });
    expect(await screen.findByTestId("floating-conversation")).toBeInTheDocument();

    // Simulate the frame-first chrome switch: the launcher unmounts.
    await user.click(screen.getByRole("button", { name: "switch-chrome" }));
    expect(screen.queryByTestId("contacts-launcher")).not.toBeInTheDocument();

    // The floating projection and its draft must survive the remount.
    expect(screen.getByTestId("floating-conversation")).toBeInTheDocument();
    expect(
      (
        screen
          .getByTestId("floating-conversation")
          .querySelector('textarea[aria-label="Message"]') as HTMLTextAreaElement
      ).value
    ).toBe("parked draft");
  });
});

afterEach(() => {
  document.body.innerHTML = "";
  vi.clearAllMocks();
});

describe("ContactsWindow (People)", () => {
  it("renders nothing while closed", () => {
    const state = makeState({ peopleOpen: false });
    renderWithPortal(
      <ContactsWindow
        state={state}
        contacts={[]}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    expect(screen.queryByTestId("contacts-window")).not.toBeInTheDocument();
  });

  it("renders into cfy-portal-root, uses People terminology, and stops window events", () => {
    const { portal, onShellClick } = renderWithPortal(
      <ContactsWindow
        state={makeState()}
        contacts={contacts}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    const window = screen.getByTestId("contacts-window");
    expect(window).toHaveAttribute("aria-label", "People");
    expect(portal).toContainElement(window);
    expect(screen.getByRole("heading", { name: "People" })).toBeInTheDocument();
    expect(screen.getByText("Private communication space")).toBeInTheDocument();
    fireEvent.pointerDown(window);
    fireEvent.click(window);
    expect(onShellClick).not.toHaveBeenCalled();
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    const closePeople = vi.fn();
    renderWithPortal(
      <ContactsWindow
        state={makeState({ closePeople })}
        contacts={[]}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    await user.keyboard("{Escape}");
    expect(closePeople).toHaveBeenCalledTimes(1);
  });

  it("exposes exactly Inbox and Contacts tabs", async () => {
    const user = userEvent.setup();
    const setTab = vi.fn();
    renderWithPortal(
      <ContactsWindow
        state={makeState({ setTab })}
        contacts={[]}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    const tablist = screen.getByRole("tablist", { name: "People sections" });
    const tabs = within(tablist).getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Inbox", "Contacts"]);
    await user.click(tabs[1]);
    expect(setTab).toHaveBeenCalledWith("contacts");
  });

  it("shows the fail-closed Inbox state when direct_messages is unavailable", async () => {
    renderWithPortal(
      <ContactsWindow
        state={makeState({ activeTab: "inbox" })}
        contacts={[]}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    expect(
      screen.getByRole("heading", { name: "Direct messages unavailable" })
    ).toBeInTheDocument();
    // No DM list request may fire in this posture.
    const { fetchDirectMessageConversations } = await import(
      "@/lib/direct-messages"
    );
    expect(fetchDirectMessageConversations).not.toHaveBeenCalled();
  });

  it("preserves the honest Contacts empty state behind the Contacts tab", () => {
    renderWithPortal(
      <ContactsWindow
        state={makeState({ activeTab: "contacts" })}
        contacts={[]}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    expect(screen.getByRole("heading", { name: "No contacts yet" })).toBeInTheDocument();
    expect(screen.getByText(/do not grant access or expose presence/i)).toBeInTheDocument();
    expect(screen.queryByText("Ava Martinez")).not.toBeInTheDocument();
  });

  it("renders the existing contact list/card surface unchanged behind Contacts", async () => {
    const user = userEvent.setup();
    renderWithPortal(
      <ContactsWindow
        state={makeState({ activeTab: "contacts" })}
        contacts={contacts}
        capabilityState="unavailable"
        sourceThreadId={null}
      />
    );
    expect(await screen.findByRole("heading", { name: "Ava Martinez" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Ben Okafor/ }));
    expect(screen.getByRole("heading", { name: "Ben Okafor" })).toBeInTheDocument();
    expect(screen.getByText("Private relationship record")).toBeInTheDocument();
  });
});

describe("ContactsLauncher (People doorway)", () => {
  beforeEach(() => {
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);
  });

  it("uses People terminology and opens/closes through the window", async () => {
    const user = userEvent.setup();
    render(<ContactsLauncher className="pill-tab" />);
    const launcher = screen.getByRole("button", { name: "People" });
    expect(launcher).toHaveAttribute("title", "People");
    await user.click(launcher);
    expect(screen.getByTestId("contacts-window")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "People" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close People" }));
    expect(screen.queryByTestId("contacts-window")).not.toBeInTheDocument();
  });
});
