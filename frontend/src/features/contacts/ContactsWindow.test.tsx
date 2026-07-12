import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ContactsLauncher from "./ContactsLauncher";
import ContactsWindow from "./ContactsWindow";
import type { ContactListItem } from "./types";

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
});

describe("ContactsWindow", () => {
  it("renders nothing while closed", () => {
    renderWithPortal(<ContactsWindow open={false} onClose={vi.fn()} contacts={[]} />);
    expect(screen.queryByTestId("contacts-window")).not.toBeInTheDocument();
  });

  it("renders into cfy-portal-root and stops window events", () => {
    const { portal, onShellClick } = renderWithPortal(
      <ContactsWindow open onClose={vi.fn()} contacts={contacts} />
    );
    const window = screen.getByTestId("contacts-window");
    expect(portal).toContainElement(window);
    fireEvent.pointerDown(window);
    fireEvent.click(window);
    expect(onShellClick).not.toHaveBeenCalled();
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithPortal(<ContactsWindow open onClose={onClose} contacts={[]} />);
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows an honest empty state without demo records or an implicit create action", () => {
    renderWithPortal(<ContactsWindow open onClose={vi.fn()} contacts={[]} />);
    expect(screen.getByRole("heading", { name: "No contacts yet" })).toBeInTheDocument();
    expect(screen.getByText(/do not grant access or expose presence/i)).toBeInTheDocument();
    expect(screen.queryByText("Ava Martinez")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new contact/i })).not.toBeInTheDocument();
  });

  it("renders and invokes an optional New Contact action", async () => {
    const user = userEvent.setup();
    const onRequestCreate = vi.fn();
    renderWithPortal(
      <ContactsWindow open onClose={vi.fn()} contacts={[]} onRequestCreate={onRequestCreate} />
    );
    await user.click(screen.getByRole("button", { name: "New Contact" }));
    expect(onRequestCreate).toHaveBeenCalledTimes(1);
  });

  it("selects the first visible contact and updates the card", async () => {
    const user = userEvent.setup();
    renderWithPortal(<ContactsWindow open onClose={vi.fn()} contacts={contacts} />);
    expect(await screen.findByRole("heading", { name: "Ava Martinez" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Ben Okafor/ }));
    expect(screen.getByRole("heading", { name: "Ben Okafor" })).toBeInTheDocument();
  });

  it("searches display names, aliases, methods, and handles but not private notes", async () => {
    const user = userEvent.setup();
    renderWithPortal(<ContactsWindow open onClose={vi.fn()} contacts={contacts} />);
    const search = screen.getByLabelText("Search contacts");
    const list = screen.getByRole("region", { name: "Contact list" });

    await user.type(search, "ava-m");
    expect(within(list).getByRole("button", { name: /Ava Martinez/ })).toBeInTheDocument();
    expect(within(list).queryByRole("button", { name: /Ben Okafor/ })).not.toBeInTheDocument();

    await user.clear(search);
    await user.type(search, "Signal");
    expect(within(list).getByRole("button", { name: /Ava Martinez/ })).toBeInTheDocument();

    await user.clear(search);
    await user.type(search, "@cass:example.test");
    expect(within(list).getByRole("button", { name: /Cass Rivera/ })).toBeInTheDocument();

    await user.clear(search);
    await user.type(search, "neighborhood studio");
    expect(screen.getByText("No contacts match this view.")).toBeInTheDocument();
  });

  it("filters favorites, archived, and blocked contacts", async () => {
    const user = userEvent.setup();
    renderWithPortal(<ContactsWindow open onClose={vi.fn()} contacts={contacts} />);
    const list = screen.getByRole("region", { name: "Contact list" });

    await user.click(screen.getByRole("button", { name: "Favorites" }));
    expect(within(list).getByRole("button", { name: /Ava Martinez/ })).toBeInTheDocument();
    expect(within(list).queryByRole("button", { name: /Ben Okafor/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Archived" }));
    expect(within(list).getByRole("button", { name: /Ben Okafor/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Blocked" }));
    expect(within(list).getByRole("button", { name: /Cass Rivera/ })).toBeInTheDocument();
  });

  it("keeps private notes out of rows and shows them on the selected card with the boundary", () => {
    renderWithPortal(<ContactsWindow open onClose={vi.fn()} contacts={contacts} />);
    const list = screen.getByRole("region", { name: "Contact list" });
    expect(within(list).queryByText("Met through the neighborhood studio.")).not.toBeInTheDocument();
    expect(screen.getByText("Met through the neighborhood studio.")).toBeInTheDocument();
    expect(screen.getByText("Private relationship record")).toBeInTheDocument();
    expect(screen.getByText(/does not prove account ownership/i)).toBeInTheDocument();
    expect(within(list).queryByText(/online|verified|invite|space|permission/i)).not.toBeInTheDocument();
  });

  it("exposes rows as keyboard-accessible buttons", () => {
    renderWithPortal(<ContactsWindow open onClose={vi.fn()} contacts={contacts} />);
    expect(screen.getByRole("button", { name: /Ava Martinez/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("button", { name: /Ben Okafor/ })).toHaveAttribute("aria-selected", "false");
  });
});

describe("ContactsLauncher", () => {
  beforeEach(() => {
    const portal = document.createElement("div");
    portal.id = "cfy-portal-root";
    document.body.appendChild(portal);
  });

  it("opens with the Contacts accessible name and closes through the window", async () => {
    const user = userEvent.setup();
    render(<ContactsLauncher className="pill-tab" />);
    const launcher = screen.getByRole("button", { name: "Contacts" });
    expect(launcher).toHaveAttribute("title", "Contacts");
    await user.click(launcher);
    expect(screen.getByTestId("contacts-window")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close Contacts" }));
    expect(screen.queryByTestId("contacts-window")).not.toBeInTheDocument();
  });
});
