import { afterEach, describe, expect, it, vi } from "vitest"
import {
  createConnectionProfile,
  createRemoteConnectionProfile,
  type RemoteSessionCredential,
} from "../connectionProfile"
import {
  createCodexifyExtensionApi,
  loginRemoteSession,
} from "../codexifyExtensionApi"

const fixedTimestamp = "2026-07-21T12:00:00.000Z"
const localCredential = (): string => ["unit", "local", "credential"].join("-")
const remotePassword = (): string => ["unit", "remote", "password"].join("-")
const remoteSession: RemoteSessionCredential = {
  token: ["unit", "remote", "session"].join("-"),
  userId: "remote-user",
  expiresAt: 1_900_000_000,
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("Codexify extension auth transport", () => {
  it("uses only X-API-Key for a local connection", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const headers = new Headers(init?.headers)
      expect(headers.get("X-API-Key")).toBe(localCredential())
      expect(headers.get("Authorization")).toBeNull()
      return new Response(JSON.stringify({ threads: [] }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createConnectionProfile({
      backendBaseUrl: "http://127.0.0.1:8888",
      apiKey: localCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await expect(createCodexifyExtensionApi(profile).listThreads()).resolves.toEqual([])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("uses only Authorization Bearer for a remote connection", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const headers = new Headers(init?.headers)
      expect(headers.get("Authorization")).toBe(`Bearer ${remoteSession.token}`)
      expect(headers.get("X-API-Key")).toBeNull()
      return new Response(JSON.stringify({ threads: [] }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createRemoteConnectionProfile({
      backendBaseUrl: "https://codexify.test",
      sessionUserId: remoteSession.userId,
      sessionExpiresAt: remoteSession.expiresAt,
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await expect(
      createCodexifyExtensionApi(profile, remoteSession).listThreads(),
    ).resolves.toEqual([])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("logs in with username and password and returns the opaque session", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe("https://codexify.test/api/auth/login")
      expect(new Headers(init?.headers).get("X-API-Key")).toBeNull()
      expect(JSON.parse(String(init?.body))).toEqual({
        username: remoteSession.userId,
        password: remotePassword(),
      })
      return new Response(JSON.stringify({
        token: remoteSession.token,
        user_id: remoteSession.userId,
        expires_at: remoteSession.expiresAt,
      }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)

    await expect(loginRemoteSession("https://codexify.test", {
      username: remoteSession.userId,
      password: remotePassword(),
    })).resolves.toEqual(remoteSession)
  })

  it("revokes a remote session with the same Bearer credential", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe("https://codexify.test/api/auth/logout")
      expect(init?.method).toBe("POST")
      const headers = new Headers(init?.headers)
      expect(headers.get("Authorization")).toBe(`Bearer ${remoteSession.token}`)
      expect(headers.get("X-API-Key")).toBeNull()
      return new Response(JSON.stringify({ ok: true }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createRemoteConnectionProfile({
      backendBaseUrl: "https://codexify.test",
      sessionUserId: remoteSession.userId,
      sessionExpiresAt: remoteSession.expiresAt,
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await createCodexifyExtensionApi(profile, remoteSession).logout()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
