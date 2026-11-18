import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mock = vi.hoisted(() => ({
  api: { get: vi.fn(), patch: vi.fn(), put: vi.fn(), defaults: { baseURL: "/api" } },
  auth: { ready: true, status: "authenticated", token: "account-a" },
}));
vi.mock("@/lib/api", () => ({ default: mock.api }));
vi.mock("@/lib/authState", () => ({ useAuthState: () => mock.auth }));

import { AccountPresentationController, accountPresentation, DEFAULT_APPEARANCE } from "./accountPresentation";
import AccountAppearancePanel from "./components/AccountAppearancePanel";

const WORKSPACE = "11111111-1111-4111-8111-111111111111";
const ROOT = "/api/auth/scout/profile";
let serverName: string | null;
let settings: typeof DEFAULT_APPEARANCE;
let unique: boolean;
let wallpaper: string | null;

function response() { return { settings: { ...settings }, workspace_unique: unique, wallpaper_url: wallpaper }; }
function controller() { return new AccountPresentationController(mock.api as never, () => WORKSPACE); }
function defer<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  cleanup(); accountPresentation.connect(null); vi.clearAllMocks(); localStorage.clear();
  mock.auth.token = "account-a"; mock.auth.status = "authenticated";
  serverName = null; settings = { ...DEFAULT_APPEARANCE }; unique = false; wallpaper = null;
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:account-wallpaper") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  mock.api.get.mockImplementation(async (path: string) => ({ data: path === ROOT ? { greeting_name: serverName } : path.includes("wallpaper") ? new Blob(["image"], { type: "image/png" }) : response() }));
  mock.api.patch.mockImplementation(async (path: string, body: Record<string, any>) => {
    if (path === ROOT) { serverName = body.greeting_name; return { data: { greeting_name: serverName } }; }
    if (body.settings) settings = { ...settings, ...body.settings };
    if (body.workspace_unique !== undefined) unique = body.workspace_unique;
    if (body.clear_wallpaper) wallpaper = null;
    return { data: response() };
  });
  mock.api.put.mockImplementation(async () => { wallpaper = "/api/auth/scout/profile/presentation/wallpaper?v=new"; return { data: response() }; });
});
afterEach(() => { cleanup(); accountPresentation.connect(null); });

describe("account appearance transport and lifecycle", () => {
  it("rejects delayed draft/image events captured before an account switch", async () => {
    const state = controller(); state.connect("owner-a");
    await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    const epoch = state.getSnapshot().epoch;
    state.connect("owner-b");
    await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    state.update({ theme_mode: "dark" }, epoch);
    await state.saveGreeting("Former owner draft", epoch);
    await state.uploadWallpaper(new Blob(["old image"]), epoch);
    await state.setWorkspaceUnique(true, epoch);
    expect(mock.api.patch).not.toHaveBeenCalled();
    expect(mock.api.put).not.toHaveBeenCalled();
  });
  it("retries a failed wallpaper upload without resetting the chosen source", async () => {
    const state = controller(); state.connect("owner-a");
    await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    mock.api.put.mockRejectedValueOnce(new Error("offline"));
    const source = new Blob(["chosen image"], { type: "image/png" });
    await state.uploadWallpaper(source);
    expect(state.getSnapshot().error).toContain("wallpaper");
    state.retry();
    await waitFor(() => expect(state.getSnapshot().wallpaperSrc).toBe("blob:account-wallpaper"));
    expect(mock.api.put).toHaveBeenCalledTimes(2);
    expect(mock.api.put.mock.calls[1][1]).toBe(source);
  });
  it("reads account defaults without importing or deleting browser nickname/appearance", async () => {
    localStorage.setItem("cfy.userName", "Browser nickname"); localStorage.setItem("cfy.themeMode", "dark"); localStorage.setItem("cfy.wallpaper", "data:old-image");
    const state = controller(); state.connect("owner-a");
    await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    expect(state.getSnapshot().greetingName).toBeNull();
    expect(state.getSnapshot().settings.theme_mode).toBe("system");
    expect(state.getSnapshot().wallpaperSrc).toBeNull();
    expect(mock.api.patch).not.toHaveBeenCalled();
    expect(localStorage.getItem("cfy.userName")).toBe("Browser nickname");
    expect(localStorage.getItem("cfy.wallpaper")).toBe("data:old-image");
  });

  it("merges rapid writes and does not let a read overwrite pending intent", async () => {
    const state = controller(); state.connect("owner-a"); await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    const first = defer<{ data: ReturnType<typeof response> }>();
    mock.api.patch.mockImplementationOnce(() => first.promise);
    state.update({ theme_mode: "dark" }); state.update({ base_color: "#123456" });
    await state.refresh();
    expect(state.getSnapshot().settings).toMatchObject({ theme_mode: "dark", base_color: "#123456" });
    settings.theme_mode = "dark"; first.resolve({ data: response() });
    await waitFor(() => expect(state.getSnapshot().saving).toBe(false));
    expect(mock.api.patch).toHaveBeenCalledTimes(2);
    expect(state.getSnapshot().settings).toMatchObject({ theme_mode: "dark", base_color: "#123456" });
  });

  it("rolls failed writes back to the last server state and retries explicitly", async () => {
    const state = controller(); state.connect("owner-a"); await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    mock.api.patch.mockRejectedValueOnce(new Error("offline"));
    state.update({ theme_mode: "dark" });
    await waitFor(() => expect(state.getSnapshot().error).toMatch(/save appearance/));
    expect(state.getSnapshot().settings.theme_mode).toBe("system");
    state.retry(); await waitFor(() => expect(state.getSnapshot().error).toBeNull());
    expect(state.getSnapshot().settings.theme_mode).toBe("dark");
  });

  it("ignores late reads from a former account and clears data immediately", async () => {
    const state = controller(); const pending = defer<{ data: { greeting_name: string } }>();
    mock.api.get.mockImplementationOnce(() => pending.promise);
    state.connect("owner-a"); state.connect("owner-b");
    expect(state.getSnapshot().greetingName).toBeNull();
    await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    pending.resolve({ data: { greeting_name: "Former account" } }); await Promise.resolve();
    expect(state.getSnapshot().greetingName).toBeNull();
  });

  it("revokes authenticated wallpaper objects on logout and reloads per account", async () => {
    wallpaper = "/api/auth/scout/profile/presentation/wallpaper?v=one";
    const state = controller(); state.connect("owner-a"); await waitFor(() => expect(state.getSnapshot().wallpaperSrc).toBeTruthy());
    state.connect(null);
    expect(state.getSnapshot().wallpaperSrc).toBeNull(); expect(state.getSnapshot().ready).toBe(false);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:account-wallpaper");
    state.connect("owner-b"); await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2);
  });

  it("does not apply a late successful save after account switch", async () => {
    const state = controller(); state.connect("owner-a"); await waitFor(() => expect(state.getSnapshot().ready).toBe(true));
    const pending = defer<{ data: { greeting_name: string } }>(); mock.api.patch.mockImplementationOnce(() => pending.promise);
    const saving = state.saveGreeting("Chosen A"); state.connect("owner-b");
    pending.resolve({ data: { greeting_name: "Chosen A" } });
    expect(await saving).toBe(false); expect(state.getSnapshot().greetingName).toBeNull();
  });
});

describe("explicit profile controls", () => {
  async function mount() {
    accountPresentation.connect("account-a");
    await waitFor(() => expect(accountPresentation.getSnapshot().ready).toBe(true));
    return render(<AccountAppearancePanel />);
  }
  it("saves only an explicit greeting and clears back to neutral", async () => {
    await mount();
    fireEvent.change(screen.getByLabelText("Greeting name"), { target: { value: "User" } });
    expect(mock.api.patch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Save greeting" }));
    await waitFor(() => expect(accountPresentation.getSnapshot().greetingName).toBe("User"));
    expect(mock.api.patch).toHaveBeenCalledWith(ROOT, { greeting_name: "User" }, expect.anything());
    fireEvent.click(screen.getByRole("button", { name: "Use neutral greeting" }));
    await waitFor(() => expect(screen.getByLabelText("Greeting name")).toHaveValue(""));
    expect(accountPresentation.getSnapshot().greetingName).toBeNull();
  });
  it("keeps a failed name save out of the greeting and preserves the draft", async () => {
    await mount(); mock.api.patch.mockRejectedValueOnce(new Error("unavailable"));
    fireEvent.change(screen.getByLabelText("Greeting name"), { target: { value: "Chosen" } });
    fireEvent.click(screen.getByRole("button", { name: "Save greeting" }));
    await screen.findByRole("alert");
    expect(accountPresentation.getSnapshot().greetingName).toBeNull();
    expect(screen.getByLabelText("Greeting name")).toHaveValue("Chosen");
  });
  it("changes only the explicit workspace mode and preserves the account greeting", async () => {
    serverName = "Chosen"; await mount();
    fireEvent.click(screen.getByRole("checkbox", { name: /Keep this workspace/ }));
    await waitFor(() => expect(screen.getByRole("checkbox")).toBeChecked());
    expect(mock.api.patch.mock.calls[0][1]).toEqual({ workspace_id: expect.any(String), workspace_unique: true });
    expect(accountPresentation.getSnapshot().greetingName).toBe("Chosen");
  });
  it("clears unsaved former-account drafts on account change", async () => {
    const view = await mount(); fireEvent.change(screen.getByLabelText("Greeting name"), { target: { value: "Unsent private draft" } });
    act(() => { mock.auth.token = "account-b"; accountPresentation.connect("account-b"); });
    view.rerender(<AccountAppearancePanel />);
    expect(screen.getByLabelText("Greeting name")).toHaveValue("");
  });
});
