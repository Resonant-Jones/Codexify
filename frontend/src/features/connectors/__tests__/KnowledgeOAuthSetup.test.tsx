import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import api from "@/lib/api";

import type { ConnectionEntry } from "../connectionCatalog";
import { KnowledgeOAuthSetup } from "../KnowledgeOAuthSetup";
vi.mock("@/lib/api", () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
const entry = { id: "notion", display_name: "Notion" } as ConnectionEntry;
const flush = async () => { await act(async () => { await Promise.resolve(); }); };
describe("Knowledge OAuth", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.resetAllMocks(); });
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });
  it("does not launch without operator setup", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { available: false, configured: false } });
    render(<KnowledgeOAuthSetup connection={entry} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    expect(screen.getByText(/not configured by this server/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Connect Notion" })).toBeDisabled();
  });
  it("reports blocked popups without starting server state", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { available: true, configured: false } });
    vi.spyOn(window, "open").mockReturnValue(null);
    render(<KnowledgeOAuthSetup connection={entry} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    fireEvent.click(screen.getByRole("button", { name: "Connect Notion" })); await flush();
    expect(api.post).not.toHaveBeenCalled(); expect(screen.getByText(/Allow pop-ups/)).toBeTruthy();
  });
  it("ignores old generations and stops polling on close", async () => {
    const close = vi.fn(); const changed = vi.fn();
    const popup = { close: vi.fn(), closed: false, location: { href: "" }, opener: null };
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    vi.mocked(api.get).mockResolvedValue({ data: { available: true, configured: true, state: "connected", generation: "old" } });
    vi.mocked(api.post).mockResolvedValue({ data: { authorization_url: "https://api.notion.com/v1/oauth/authorize?state=opaque", generation: "new" } });
    render(<KnowledgeOAuthSetup connection={entry} onClose={close} onChanged={changed} />); await flush();
    fireEvent.click(screen.getByRole("button", { name: "Reconnect Notion" })); await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(changed).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    const count = vi.mocked(api.get).mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(api.get).toHaveBeenCalledTimes(count); expect(popup.close).toHaveBeenCalled(); expect(close).toHaveBeenCalledOnce();
  });
  it("accepts GitHub needs_scope without granting repositories", async () => {
    const github = { ...entry, id: "github_knowledge", display_name: "GitHub Knowledge" };
    const popup = { close: vi.fn(), closed: false, location: { href: "" }, opener: null };
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    vi.mocked(api.get).mockResolvedValueOnce({ data: { available: true, configured: false } }).mockResolvedValueOnce({ data: { available: true, configured: false, state: "needs_scope", generation: "new" } }).mockResolvedValueOnce({ data: { installations: [] } });
    vi.mocked(api.post).mockResolvedValue({ data: { authorization_url: "https://github.com/login/oauth/authorize", generation: "new" } });
    render(<KnowledgeOAuthSetup connection={github} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    fireEvent.click(screen.getByRole("button", { name: "Connect GitHub" })); await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(screen.getByText(/Authorized. Select/)).toBeTruthy(); expect(api.put).not.toHaveBeenCalled();
  });
  it("rejects an untrusted authorization URL", async () => {
    const popup = { close: vi.fn(), closed: false, location: { href: "" }, opener: null };
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    vi.mocked(api.get).mockResolvedValue({ data: { available: true, configured: false } });
    vi.mocked(api.post).mockResolvedValue({ data: { authorization_url: "https://evil.example/", generation: "new" } });
    render(<KnowledgeOAuthSetup connection={entry} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    fireEvent.click(screen.getByRole("button", { name: "Connect Notion" })); await flush();
    expect(popup.location.href).toBe(""); expect(popup.close).toHaveBeenCalled();
    expect(screen.getByText(/Could not start authorization/)).toBeTruthy();
  });
  it("ignores a pending start after unmount and prevents duplicate starts", async () => {
    let resolve!: (value: unknown) => void;
    const popup = { close: vi.fn(), closed: false, location: { href: "" }, opener: null };
    vi.spyOn(window, "open").mockReturnValue(popup as unknown as Window);
    vi.mocked(api.get).mockResolvedValue({ data: { available: true, configured: false } });
    vi.mocked(api.post).mockReturnValue(new Promise((done) => { resolve = done; }));
    const view = render(<KnowledgeOAuthSetup connection={entry} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    const button = screen.getByRole("button", { name: "Connect Notion" });
    fireEvent.click(button); fireEvent.click(button);
    expect(api.post).toHaveBeenCalledTimes(1); view.unmount();
    resolve({ data: { authorization_url: "https://api.notion.com/v1/oauth/authorize", generation: "new" } }); await flush();
    expect(popup.location.href).toBe(""); expect(popup.close).toHaveBeenCalled();
  });

  it.each(["pending", "reconnect_required"])("can disconnect a reopened %s connection", async (state) => {
    const changed = vi.fn();
    vi.mocked(api.get).mockResolvedValue({ data: { available: true, configured: false, state, generation: "persisted" } });
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    render(<KnowledgeOAuthSetup connection={entry} onClose={vi.fn()} onChanged={changed} />); await flush();
    const button = screen.getByRole("button", { name: "Disconnect" });
    expect(button).toBeEnabled(); fireEvent.click(button); await flush();
    expect(api.post).toHaveBeenCalledWith("/api/connect/notion/oauth/disconnect", {});
    expect(changed).toHaveBeenCalledOnce();
    expect(screen.getByText(/Disconnected from Codexify/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Disconnect" })).toBeNull();
  });

  it("offers a safe installation link and explains an empty installation list", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { available: true, configured: false, state: "needs_scope", generation: "saved", installation_url: "https://github.com/apps/codexify-read/installations/new" } }).mockResolvedValueOnce({ data: { installations: [] } });
    render(<KnowledgeOAuthSetup connection={{ ...entry, id: "github_knowledge" }} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    expect(screen.getByRole("link", { name: "Install GitHub App" })).toHaveAttribute("href", "https://github.com/apps/codexify-read/installations/new");
    fireEvent.click(screen.getByRole("button", { name: "Choose repositories" })); await flush();
    expect(screen.getByText(/No available installations/)).toBeTruthy();
    expect(screen.getByText(/does not grant Codexify/)).toBeTruthy();
  });
  it("does not render an untrusted installation link", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { available: true, state: "needs_scope", installation_url: "https://evil.example/installations/new" } });
    render(<KnowledgeOAuthSetup connection={{ ...entry, id: "github_knowledge" }} onClose={vi.fn()} onChanged={vi.fn()} />); await flush();
    expect(screen.queryByRole("link", { name: "Install GitHub App" })).toBeNull();
  });

});
