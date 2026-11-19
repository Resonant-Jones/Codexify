import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildSlashCommandSendPayload,
  decodeSlashCommandManifest,
  filterSlashCommands,
  resolveSlashCommand,
  type SlashCommandDefinition,
} from "@/contracts/slashCommands";
import { useSlashCommandLibrary } from "@/features/chat/useSlashCommandLibrary";
import { fetchSlashCommandManifest, getBackendOutageRemainingMs, setAuthToken } from "@/lib/api";
import type { AuthState } from "@/lib/authState";

const runtime = vi.hoisted(() => ({
  endpoint: "http://first.test",
  version: 0,
  listeners: new Set<() => void>(),
}));

vi.mock("@/lib/runtimeConfig", async (importActual) => ({
  ...await importActual<typeof import("@/lib/runtimeConfig")>(),
  getRuntimeConfigVersion: () => runtime.version,
  subscribeRuntimeConfigState: (listener: () => void) => {
    runtime.listeners.add(listener);
    return () => runtime.listeners.delete(listener);
  },
  resolveApiUrl: (path: string) => runtime.endpoint + path,
}));

function fixtureCommand(id: string, fields: Partial<SlashCommandDefinition> = {}): SlashCommandDefinition {
  return {
    id,
    token: `/${id}`,
    label: id,
    description: `Test command ${id}`,
    aliases: [],
    keywords: [],
    scaffold: `/${id}`,
    interactionModes: ["chat_intent"],
    effects: { intentKind: "help", retrievalHint: "none" },
    availability: "unknown",
    availabilityReason: "eligibility_not_evaluated",
    ...fields,
  };
}

const wireManifest = {
  schemaVersion: 1,
  manifestRevision: "revision-a",
  commands: [
    fixtureCommand("obsidian", { aliases: ["obs"], keywords: ["markdown"] }),
    fixtureCommand("project", { aliases: ["repo", "workspace"] }),
    fixtureCommand("workspace"),
  ],
};

const authA: AuthState = { ready: true, status: "authenticated", token: "token-a" };
const authB: AuthState = { ...authA, token: "token-b" };
const manifestPath = "/api/chat/slash-commands/manifest";
const reply = (id: string) => Response.json({
  schemaVersion: 1,
  manifestRevision: id,
  commands: [fixtureCommand(id)],
});

describe("Guardian slash command wire contract", () => {
  it("decodes the revision and resolves canonical tokens before aliases", () => {
    const { commands, manifestRevision } = decodeSlashCommandManifest(wireManifest);
    expect(manifestRevision).toBe("revision-a");
    expect(resolveSlashCommand(commands, "/workspace")?.id).toBe("workspace");
    expect(resolveSlashCommand(commands, " /REPO ")?.id).toBe("project");
    expect(filterSlashCommands(commands, "/obs").map(({ id }) => id)).toEqual(["obsidian"]);
    expect(filterSlashCommands(commands, "mark").map(({ id }) => id)).toEqual(["obsidian"]);
    expect(filterSlashCommands(commands, "/").map(({ id }) => id)).toEqual(["obsidian", "project", "workspace"]);
  });

  it.each([
    { ...wireManifest, schemaVersion: 2 },
    { ...wireManifest, manifestRevision: undefined },
    { ...wireManifest, commands: [{ ...wireManifest.commands[0], availability: undefined }] },
    { ...wireManifest, commands: [{ ...wireManifest.commands[0], effects: null }] },
    { ...wireManifest, commands: [wireManifest.commands[0], wireManifest.commands[0]] },
  ])("rejects an invalid or incompatible manifest", (wire) => {
    expect(() => decodeSlashCommandManifest(wire)).toThrow();
  });

  it("preserves supported modes and ignores unknown modes during send", () => {
    const { commands } = decodeSlashCommandManifest({
      ...wireManifest,
      commands: [
        fixtureCommand("new_command", { interactionModes: ["chat_intent", "future_mode"] }),
        fixtureCommand("future", { interactionModes: ["future_mode"] }),
        fixtureCommand("denied", { availability: "unavailable" }),
      ],
    });
    expect(buildSlashCommandSendPayload("/new_command", commands).slashIntent?.commandId).toBe("new_command");
    expect(buildSlashCommandSendPayload("/future", commands)).toEqual({
      messageText: "/future", slashIntent: null,
    });
    expect(buildSlashCommandSendPayload("/denied", commands).slashIntent).toBeNull();
  });
});

describe("authenticated slash command discovery", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    runtime.endpoint = "http://first.test";
    runtime.version = 0;
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    setAuthToken("token-a");
  });

  afterEach(() => {
    setAuthToken(null);
    vi.unstubAllGlobals();
  });

  it("fetches the canonical route with shared credentials and no browser caching", async () => {
    fetchMock.mockResolvedValueOnce(reply("revision-a"));
    const signal = new AbortController().signal;
    const manifest = await fetchSlashCommandManifest(signal);
    expect(manifest.manifestRevision).toBe("revision-a");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://first.test" + manifestPath,
      expect.objectContaining({
        signal,
        credentials: "include",
        cache: "no-store",
        headers: expect.objectContaining({ Authorization: "Bearer token-a" }),
      }),
    );
  });

  it("drops a visible catalog on account change and aborts requests on endpoint change", async () => {
    let staleResolve: (response: Response) => void = () => {};
    fetchMock.mockResolvedValueOnce(reply("account-a"))
      .mockImplementationOnce(() => new Promise((resolve) => { staleResolve = resolve; }))
      .mockResolvedValueOnce(reply("second-endpoint"));
    const { result, rerender } = renderHook(({ auth }) => useSlashCommandLibrary(auth), {
      initialProps: { auth: authA },
    });
    await waitFor(() => expect(result.current.manifest?.manifestRevision).toBe("account-a"));

    setAuthToken("token-b");
    rerender({ auth: authB });
    expect(result.current).toEqual({ status: "loading" });
    const staleSignal = fetchMock.mock.calls[1][1]?.signal;
    act(() => {
      runtime.endpoint = "http://second.test";
      runtime.version += 1;
      runtime.listeners.forEach((listener) => listener());
    });
    expect(staleSignal?.aborted).toBe(true);
    expect(fetchMock.mock.calls[2][0]).toBe("http://second.test" + manifestPath);
    await waitFor(() => expect(result.current.manifest?.manifestRevision).toBe("second-endpoint"));
    await act(async () => staleResolve(reply("stale-response")));
    expect(result.current.manifest?.manifestRevision).toBe("second-endpoint");
  });

  it("waits for authentication and reloads after reconnect", async () => {
    fetchMock.mockResolvedValueOnce(reply("before-reconnect")).mockResolvedValueOnce(reply("after-reconnect"));
    const { result, rerender } = renderHook(({ auth, connected }: { auth: AuthState; connected: boolean }) =>
      useSlashCommandLibrary(auth, connected), {
      initialProps: { auth: { ready: false, status: "unknown" }, connected: true },
    });
    expect(fetchMock).not.toHaveBeenCalled();
    rerender({ auth: authA, connected: true });
    await waitFor(() => expect(result.current.manifest?.manifestRevision).toBe("before-reconnect"));
    rerender({ auth: authA, connected: false });
    expect(result.current).toEqual({ status: "unavailable" });
    rerender({ auth: authA, connected: true });
    await waitFor(() => expect(result.current.manifest?.manifestRevision).toBe("after-reconnect"));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([404, 503, 200])("keeps discovery failure isolated for HTTP %s", async (status) => {
    fetchMock.mockResolvedValueOnce(Response.json({ invalid: true }, { status }));
    const { result } = renderHook(() => useSlashCommandLibrary(authA));
    await waitFor(() => expect(result.current).toEqual({ status: "unavailable" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getBackendOutageRemainingMs()).toBe(0);
  });
});
