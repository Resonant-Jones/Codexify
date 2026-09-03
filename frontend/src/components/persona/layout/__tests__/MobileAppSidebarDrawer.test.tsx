import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MobileAppSidebarDrawer from "../MobileAppSidebarDrawer";
import type {
  MobileApplicationDestination,
  MobileApplicationView,
} from "../mobileNavigationContract";

const DESTINATIONS = [
  { view: "guardian", label: "Guardian", priority: "primary" },
  { view: "documents", label: "Documents", priority: "primary" },
  { view: "gallery", label: "Gallery", priority: "primary" },
  { view: "dashboard", label: "Dashboard", priority: "secondary" },
  { view: "settings", label: "Settings", priority: "secondary" },
] as const satisfies readonly MobileApplicationDestination[];

vi.mock("@/components/ui/RefractiveGlassCard", () => ({
  default: () => null,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

const workspaceMountSpy = vi.fn();

function StatefulWorkspace() {
  const [tab, setTab] = React.useState<"threads" | "projects">("threads");
  const [search, setSearch] = React.useState("");

  React.useEffect(() => {
    workspaceMountSpy();
  }, []);

  return (
    <section data-testid="workspace-stateful">
      <button type="button" onClick={() => setTab("projects")}>
        Projects
      </button>
      <output aria-label="Selected workspace tab">{tab}</output>
      <input
        aria-label="Workspace search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
    </section>
  );
}

function DrawerHarness({
  initialExpanded = false,
  activeApplicationView = "guardian",
  onNavigateApplicationView = vi.fn(),
}: {
  initialExpanded?: boolean;
  activeApplicationView?: MobileApplicationView;
  onNavigateApplicationView?: (view: MobileApplicationView) => void;
}) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isExpanded, setIsExpanded] = React.useState(initialExpanded);
  const openerRef = React.useRef<HTMLButtonElement | null>(null);

  return (
    <>
      <div id="cfy-portal-root" />
      <button
        ref={openerRef}
        type="button"
        onClick={() => setIsOpen(true)}
      >
        Show sidebar
      </button>
      <MobileAppSidebarDrawer
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        isApplicationNavigationExpanded={isExpanded}
        onApplicationNavigationExpandedChange={setIsExpanded}
        activeApplicationView={activeApplicationView}
        applicationDestinations={DESTINATIONS}
        onNavigateApplicationView={onNavigateApplicationView}
        returnFocusRef={openerRef}
      >
        <StatefulWorkspace />
      </MobileAppSidebarDrawer>
    </>
  );
}

async function openDrawer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Show sidebar" }));
  return screen.findByRole("dialog", {
    name: "Application navigation and workspace",
  });
}

describe("MobileAppSidebarDrawer", () => {
  beforeEach(() => {
    workspaceMountSpy.mockClear();
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 430,
    });
    document.body.style.overflow = "";
  });

  it("pushes application destinations above a stable workspace child", async () => {
    const user = userEvent.setup();
    render(<DrawerHarness />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const drawer = await openDrawer(user);
    const workspace = within(drawer).getByTestId("workspace-stateful");
    const disclosure = within(drawer).getByRole("button", {
      name: "Expand application navigation",
    });

    expect(disclosure).toHaveAttribute("aria-expanded", "false");
    expect(workspaceMountSpy).toHaveBeenCalledTimes(1);
    await user.click(within(drawer).getByRole("button", { name: "Projects" }));
    await user.type(
      within(drawer).getByRole("textbox", { name: "Workspace search" }),
      "retained"
    );
    await user.click(disclosure);

    const navigation = within(drawer).getByRole("navigation", {
      name: "Application destinations",
    });
    expect(
      within(navigation)
        .getAllByRole("button")
        .map((button) => button.textContent)
    ).toEqual(["Guardian", "Documents", "Gallery", "Dashboard", "Settings"]);
    expect(
      navigation.compareDocumentPosition(workspace) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(within(drawer).getByTestId("workspace-stateful")).toBe(workspace);
    expect(
      within(drawer).getByRole("textbox", { name: "Workspace search" })
    ).toHaveValue("retained");
    expect(
      within(drawer).getByRole("status", { name: "Selected workspace tab" })
    ).toHaveTextContent("projects");
    expect(workspaceMountSpy).toHaveBeenCalledTimes(1);
  });

  it("contains focus, layers Escape, locks scroll, and restores the opener", async () => {
    const user = userEvent.setup();
    render(<DrawerHarness initialExpanded />);
    const opener = screen.getByRole("button", { name: "Show sidebar" });
    const drawer = await openDrawer(user);

    expect(document.body.style.overflow).toBe("hidden");
    expect(
      within(drawer).getByRole("button", {
        name: "Close application navigation and workspace sidebar",
      })
    ).toHaveFocus();

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(drawer).toContainElement(document.activeElement as HTMLElement);

    await user.keyboard("{Escape}");
    expect(drawer).toBeInTheDocument();
    expect(
      within(drawer).getByRole("button", {
        name: "Expand application navigation",
      })
    ).toHaveFocus();
    expect(
      within(drawer).queryByRole("navigation", {
        name: "Application destinations",
      })
    ).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(document.body.style.overflow).toBe("");
    expect(opener).toHaveFocus();
  });

  it("closes after navigation without collapsing controlled disclosure memory", async () => {
    const user = userEvent.setup();
    const navigate = vi.fn();
    render(
      <DrawerHarness
        initialExpanded
        activeApplicationView="documents"
        onNavigateApplicationView={navigate}
      />
    );

    const drawer = await openDrawer(user);
    expect(
      within(drawer).getByTestId("mobile-app-sidebar-destination-documents")
    ).toHaveAttribute("aria-current", "page");
    await user.click(
      within(drawer).getByTestId("mobile-app-sidebar-destination-gallery")
    );

    expect(navigate).toHaveBeenCalledWith("gallery");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const reopened = await openDrawer(user);
    expect(
      within(reopened).getByRole("button", {
        name: "Collapse application navigation",
      })
    ).toHaveAttribute("aria-expanded", "true");
  });

  it("dismisses from the view-neutral scrim affordance", async () => {
    const user = userEvent.setup();
    render(<DrawerHarness />);
    await openDrawer(user);

    await user.click(
      screen.getByRole("button", {
        name: "Dismiss application navigation and workspace sidebar",
      })
    );

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
