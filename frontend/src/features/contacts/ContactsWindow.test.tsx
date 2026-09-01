import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ContactsLauncher from "./ContactsLauncher";
import ContactsWindow from "./ContactsWindow";
import type { ContactListItem } from "./types";
import type { PeopleMessagingState } from "./usePeopleMessagingState";

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
