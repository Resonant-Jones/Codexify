import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const session = vi.hoisted(() => ({ auth: { status: "authenticated", ready: true, token: "session-a" }, owner: "account-a", get: vi.fn() }));
vi.mock("@/lib/authState", () => ({ useAuthState: () => session.auth }));
vi.mock("@/lib/api", () => ({ default: { get: session.get } }));
import FeedLayout from "./FeedLayout";
import { feedStorageKey } from "./feedPreferences";

const cards = { threads: <p>Chats content</p>, documents: <p>Documents content</p>, gallery: <p>Gallery content</p> };
const order = () => screen.queryAllByRole("article").map((card) => card.getAttribute("aria-label"));
async function customize() {
  fireEvent.click(screen.getByRole("button", { name: "Customize Feed" }));
  await screen.findByText("Saved for your account on this device.");
}

beforeEach(() => {
  localStorage.clear();
  session.auth = { status: "authenticated", ready: true, token: "session-a" };
  session.owner = "account-a";
  session.get.mockReset().mockImplementation(async () => ({ data: [{ user_id: session.owner }] }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Feed customization", () => {
  it("persists visibility and order across remounts, restores hidden cards in place, and resets", async () => {
    const first = render(<FeedLayout cards={cards} />);
    await customize();
    expect(screen.getByRole("button", { name: "Move Recent Threads up" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move Gallery down" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Move Gallery up" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Recent Documents" }));
    expect(order()).toEqual(["Recent Threads", "Gallery"]);
    first.unmount();
    render(<FeedLayout cards={cards} />);
    await customize();
    expect(order()).toEqual(["Recent Threads", "Gallery"]);
    expect(screen.getByRole("checkbox", { name: "Recent Documents" })).not.toBeChecked();
    fireEvent.click(screen.getByRole("checkbox", { name: "Recent Documents" }));
    expect(order()).toEqual(["Recent Threads", "Gallery", "Recent Documents"]);
    fireEvent.click(screen.getByRole("button", { name: "Reset layout" }));
    expect(order()).toEqual(["Recent Threads", "Recent Documents", "Gallery"]);
  });

  it("preserves edits made before account ownership finishes loading", async () => {
    let resolveOwner!: (value: unknown) => void;
    session.get.mockImplementationOnce(() => new Promise((resolve) => { resolveOwner = resolve; }));
    render(<FeedLayout cards={cards} />);
    fireEvent.click(screen.getByRole("button", { name: "Customize Feed" }));
    fireEvent.click(screen.getByRole("button", { name: "Move Gallery up" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Recent Documents" }));
    expect(order()).toEqual(["Recent Threads", "Gallery"]);

    await act(async () => resolveOwner({ data: [{ user_id: "account-a" }] }));

    expect(order()).toEqual(["Recent Threads", "Gallery"]);
    expect(screen.getByRole("checkbox", { name: "Recent Documents" })).not.toBeChecked();
    expect(JSON.parse(localStorage.getItem(feedStorageKey("account-a"))!)).toMatchObject({
      order: ["threads", "gallery", "documents"],
      hidden: ["documents"],
    });
  });

  it("keeps recovery controls reachable when every card is hidden and supports Escape", async () => {
    render(<FeedLayout cards={cards} />);
    await customize();
    for (const checkbox of screen.getAllByRole("checkbox")) fireEvent.click(checkbox);
    expect(order()).toEqual([]);
    expect(screen.getByText("Your Feed is clear")).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("checkbox", { name: "Gallery" }), { key: "Escape" });
    expect(screen.getByRole("button", { name: "Customize Feed" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Customize Feed" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Gallery" }));
    expect(order()).toEqual(["Gallery"]);
  });

  it("isolates accounts and ignores ownership responses from a previous session", async () => {
    let resolveOld!: (value: unknown) => void;
    session.get.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }));
    localStorage.setItem(feedStorageKey("account-a"), JSON.stringify({ version: 1, order: ["gallery"], hidden: ["threads"] }));
    const view = render(<FeedLayout cards={cards} />);
    fireEvent.click(screen.getByRole("button", { name: "Customize Feed" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Gallery" }));
    session.auth = { ...session.auth, token: "session-b" };
    session.owner = "account-b";
    view.rerender(<FeedLayout cards={cards} />);
    await screen.findByText("Saved for your account on this device.");
    await act(async () => resolveOld({ data: [{ user_id: "account-a" }] }));
    expect(order()).toEqual(["Recent Threads", "Recent Documents", "Gallery"]);
    fireEvent.click(screen.getByRole("checkbox", { name: "Gallery" }));
    expect(JSON.parse(localStorage.getItem(feedStorageKey("account-b"))!).hidden).toEqual(["gallery"]);
    expect(JSON.parse(localStorage.getItem(feedStorageKey("account-a"))!).hidden).toEqual(["threads"]);
    session.auth = { ...session.auth, token: "session-c" };
    session.owner = "account-a";
    view.rerender(<FeedLayout cards={cards} />);
    await waitFor(() => expect(order()).toEqual(["Gallery", "Recent Documents"]));
  });

  it.each(["invalid JSON", JSON.stringify({ version: 2, order: [], hidden: ["gallery"] })])("recovers from invalid or unsupported saved preferences (%s)", async (saved) => {
    localStorage.setItem(feedStorageKey("account-a"), saved);
    render(<FeedLayout cards={cards} />);
    await customize();
    expect(order()).toEqual(["Recent Threads", "Recent Documents", "Gallery"]);
  });

  it("drops retired and duplicate cards and appends new cards", async () => {
    localStorage.setItem(feedStorageKey("account-a"), JSON.stringify({ version: 1, order: ["gallery", "retired", "gallery"], hidden: ["retired", "documents"] }));
    render(<FeedLayout cards={cards} />);
    await customize();
    expect(order()).toEqual(["Gallery", "Recent Threads"]);
    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
  });

  it("keeps controls working when storage writes fail and explains the limitation", async () => {
    render(<FeedLayout cards={cards} />);
    await customize();
    // JSDOM Storage methods live on the prototype; the Node fallback owns them.
    const storageMethods = typeof Object.getPrototypeOf(localStorage).setItem === "function"
      ? Object.getPrototypeOf(localStorage)
      : localStorage;
    vi.spyOn(storageMethods, "setItem").mockImplementation(() => { throw new Error("unavailable"); });
    fireEvent.click(screen.getByRole("checkbox", { name: "Gallery" }));
    expect(order()).toEqual(["Recent Threads", "Recent Documents"]);
    expect(screen.getByText(/Changes apply for this visit/)).toBeInTheDocument();
  });
});
