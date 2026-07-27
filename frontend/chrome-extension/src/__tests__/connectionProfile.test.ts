import { afterEach, describe, expect, it, vi } from "vitest"
import {
  buildOriginPermissionPattern,
  chromeOriginPermissionClient,
  CONNECTION_PROFILE_VERSION,
  deserializeConnectionProfile,
  createConnectionProfile,
  createRemoteConnectionProfile,
  normalizeBackendBaseUrl,
  serializeConnectionProfile,
  summarizeConnectionProfile,
} from "../connectionProfile"
import {
  CONNECTION_PROFILE_STORAGE_KEY,
  CONNECTION_SESSION_STORAGE_KEY,
  createChromeConnectionStorage,
  type ChromeStorageAreaLike,
} from "../chromeStorage"

const fixedTimestamp = "2026-07-21T12:00:00.000Z"
const placeholderCredential = (): string => ["unit", "test", "credential"].join("-")

function createChromeStorageAreaMock(): {
  area: ChromeStorageAreaLike
  read(): Record<string, unknown>
} {
  let values: Record<string, unknown> = {}
  const area: ChromeStorageAreaLike = {
    get: vi.fn(async () => ({ ...values })),
    set: vi.fn(async (items) => {
      values = { ...values, ...items }
    }),
    remove: vi.fn(async (keys) => {
      for (const key of Array.isArray(keys) ? keys : [keys]) {
        delete values[key]
      }
    }),
    setAccessLevel: vi.fn(async () => undefined),
  }
  return { area, read: () => ({ ...values }) }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("connection profile", () => {
  it("normalizes trailing slashes while preserving an intentional base path", () => {
    expect(normalizeBackendBaseUrl(" http://127.0.0.1:8888/// ")).toBe(
      "http://127.0.0.1:8888",
    )
    expect(normalizeBackendBaseUrl("https://vault.tailnet.ts.net/codexify///")).toBe(
      "https://vault.tailnet.ts.net/codexify",
    )
  })

  it.each([
    "ftp://127.0.0.1/runtime",
    "file:///tmp/codexify",
    "chrome-extension://example/runtime",
    "javascript:alert(1)",
  ])("rejects unsupported protocol %s", (url) => {
    expect(() => normalizeBackendBaseUrl(url)).toThrow(
      "Only HTTP and HTTPS backend URLs are supported.",
    )
  })

  it("constructs the permission match pattern from the exact configured origin", () => {
    expect(
      buildOriginPermissionPattern("https://vault.tailnet.ts.net:9443/codexify/"),
    ).toBe("https://vault.tailnet.ts.net:9443/*")
    expect(buildOriginPermissionPattern("http://localhost:8888/")).toBe(
      "http://localhost:8888/*",
    )
  })

  it("serializes into local storage without logging or exposing the credential in summaries", async () => {
    const consoleSpies = [
      vi.spyOn(console, "log"),
      vi.spyOn(console, "info"),
      vi.spyOn(console, "warn"),
      vi.spyOn(console, "error"),
    ]
    const profile = createConnectionProfile({
      backendBaseUrl: "http://127.0.0.1:8888/",
      apiKey: placeholderCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })
    const serialized = serializeConnectionProfile(profile)
    const summary = summarizeConnectionProfile(profile)

    expect(serialized).toEqual(profile)
    expect(summary).toEqual({
      backendBaseUrl: "http://127.0.0.1:8888",
      authMode: "local",
      selectedThreadId: null,
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
      hasStoredCredential: true,
    })
    expect(summary).not.toHaveProperty("apiKey")
    expect(JSON.stringify(summary)).not.toContain(placeholderCredential())
    for (const spy of consoleSpies) expect(spy).not.toHaveBeenCalled()
  })

  it("migrates a version-one API-key profile into explicit local auth mode", () => {
    expect(deserializeConnectionProfile({
      version: 1,
      backendBaseUrl: "http://127.0.0.1:8888/",
      apiKey: placeholderCredential(),
      selectedThreadId: 7,
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })).toEqual({
      version: CONNECTION_PROFILE_VERSION,
      backendBaseUrl: "http://127.0.0.1:8888",
      authMode: "local",
      apiKey: placeholderCredential(),
      sessionUserId: null,
      sessionExpiresAt: null,
      selectedThreadId: 7,
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })
  })

  it("uses chrome.storage.local in trusted extension contexts", async () => {
    const { area, read } = createChromeStorageAreaMock()
    const { area: sessionArea } = createChromeStorageAreaMock()
    const permissions = {
      request: vi.fn(async () => true),
      contains: vi.fn(async () => true),
      remove: vi.fn(async () => true),
    }
    vi.stubGlobal("chrome", { storage: { local: area, session: sessionArea }, permissions })
    const storage = createChromeConnectionStorage()
    const profile = createConnectionProfile({
      backendBaseUrl: "https://vault.tailnet.ts.net",
      apiKey: placeholderCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await storage.save(profile)
    expect(area.setAccessLevel).toHaveBeenCalledWith({ accessLevel: "TRUSTED_CONTEXTS" })
    expect(read()[CONNECTION_PROFILE_STORAGE_KEY]).toEqual(profile)
    await expect(storage.load()).resolves.toEqual(profile)

    const pattern = buildOriginPermissionPattern(profile.backendBaseUrl)
    await expect(chromeOriginPermissionClient.request(pattern)).resolves.toBe(true)
    expect(permissions.request).toHaveBeenCalledWith({ origins: [pattern] })
  })

  it("keeps remote session tokens out of the persistent connection profile", async () => {
    const local = createChromeStorageAreaMock()
    const session = createChromeStorageAreaMock()
    const storage = createChromeConnectionStorage(local.area, session.area)
    const sessionCredential = {
      token: ["unit", "session", "token"].join("-"),
      userId: "remote-user",
      expiresAt: 1_900_000_000,
    }
    const profile = createRemoteConnectionProfile({
      backendBaseUrl: "https://vault.tailnet.ts.net",
      sessionUserId: sessionCredential.userId,
      sessionExpiresAt: sessionCredential.expiresAt,
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await storage.save(profile)
    await storage.saveRemoteSession(sessionCredential)

    expect(local.read()[CONNECTION_PROFILE_STORAGE_KEY]).toEqual(profile)
    expect(JSON.stringify(local.read())).not.toContain(sessionCredential.token)
    expect(session.read()[CONNECTION_SESSION_STORAGE_KEY]).toEqual(sessionCredential)
    await expect(storage.loadRemoteSession()).resolves.toEqual(sessionCredential)
    expect(session.area.setAccessLevel).toHaveBeenCalledWith({
      accessLevel: "TRUSTED_CONTEXTS",
    })
  })

  it("removes a malformed stored profile instead of retaining an unusable credential", async () => {
    const { area, read } = createChromeStorageAreaMock()
    await area.set({
      [CONNECTION_PROFILE_STORAGE_KEY]: {
        version: CONNECTION_PROFILE_VERSION + 1,
        backendBaseUrl: "https://codexify.test",
        apiKey: placeholderCredential(),
      },
    })
    const storage = createChromeConnectionStorage(area)

    await expect(storage.load()).resolves.toBeNull()
    expect(read()).not.toHaveProperty(CONNECTION_PROFILE_STORAGE_KEY)
  })
})
