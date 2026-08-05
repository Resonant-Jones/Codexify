import { afterEach, describe, expect, it, vi } from "vitest"
import {
  createConnectionProfile,
  createRemoteConnectionProfile,
  type RemoteSessionCredential,
} from "../connectionProfile"
import {
  createCodexifyExtensionApi,
  isTaskLifecycleEventCorrelated,
  loginRemoteSession,
  type CompletionReceipt,
  type TaskLifecycleEvent,
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

  it("sends the accepted completion's root request and turn correlation", async () => {
    const requestId = "req-extension-test"
    const turnId = "turn-extension-test"
    vi.stubGlobal("crypto", {
      randomUUID: vi.fn()
        .mockReturnValueOnce(requestId)
        .mockReturnValueOnce(turnId),
    })
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe("http://127.0.0.1:8888/api/chat/7/complete")
      const headers = new Headers(init?.headers)
      expect(headers.get("X-Request-ID")).toBe(requestId)
      expect(headers.get("X-API-Key")).toBe(localCredential())
      expect(headers.get("Authorization")).toBeNull()
      expect(JSON.parse(String(init?.body))).toEqual({ turn_id: turnId })
      return new Response(JSON.stringify({
        ok: true,
        request_id: requestId,
        task_id: "task-extension-test",
        turn_id: turnId,
        thread_id: 7,
      }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createConnectionProfile({
      backendBaseUrl: "http://127.0.0.1:8888",
      apiKey: localCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await expect(
      createCodexifyExtensionApi(profile).requestCompletion(7),
    ).resolves.toMatchObject({
      taskId: "task-extension-test",
      requestId,
      turnId,
      threadId: 7,
    })
  })

  it("attaches captured browser selection evidence to exactly one completion request", async () => {
    const requestId = "req-extension-browser"
    const turnId = "turn-extension-browser"
    vi.stubGlobal("crypto", {
      randomUUID: vi.fn()
        .mockReturnValueOnce(requestId)
        .mockReturnValueOnce(turnId),
    })
    const browserContext = {
      captureKind: "selected_text",
      sourceKind: "selection",
      sourceUrl: "https://example.com/articles/intro",
      sourceTitle: "An Example Article",
      capturedAt: "2026-07-21T12:00:00.000Z",
      contentType: "text/plain",
      content: "selected evidence sentence",
      contentLength: 25,
      truncated: false,
      extractorVersion: "chrome-selection-v1",
      retentionClass: "ephemeral_attachment",
      userInitiated: true,
    }
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe("http://127.0.0.1:8888/api/chat/7/complete")
      expect(JSON.parse(String(init?.body))).toEqual({
        turn_id: turnId,
        browser_context: browserContext,
      })
      return new Response(JSON.stringify({
        ok: true,
        request_id: requestId,
        task_id: "task-extension-browser",
        turn_id: turnId,
        thread_id: 7,
      }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createConnectionProfile({
      backendBaseUrl: "http://127.0.0.1:8888",
      apiKey: localCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await expect(
      createCodexifyExtensionApi(profile).requestCompletion(7, browserContext),
    ).resolves.toMatchObject({
      taskId: "task-extension-browser",
      requestId,
      turnId,
      threadId: 7,
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("never sends browser selection evidence on the durable message contract", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe("http://127.0.0.1:8888/api/chat/7/messages")
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>
      expect(body).toEqual({ role: "user", content: "ask about the page" })
      expect("browser_context" in body).toBe(false)
      expect("metadata" in body).toBe(false)
      return new Response(JSON.stringify({
        ok: true,
        message: { id: 1, thread_id: 7, role: "user", content: "ask about the page" },
      }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createConnectionProfile({
      backendBaseUrl: "http://127.0.0.1:8888",
      apiKey: localCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await expect(
      createCodexifyExtensionApi(profile).persistUserMessage(7, "ask about the page"),
    ).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("requests task cancellation through the authenticated task contract", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe("http://127.0.0.1:8888/api/tasks/task-extension-test/cancel")
      expect(init?.method).toBe("POST")
      const headers = new Headers(init?.headers)
      expect(headers.get("X-API-Key")).toBe(localCredential())
      expect(headers.get("Authorization")).toBeNull()
      return new Response(JSON.stringify({
        ok: true,
        task_id: "task-extension-test",
        cancel_requested: true,
      }), { status: 200 })
    })
    vi.stubGlobal("fetch", fetchMock)
    const profile = createConnectionProfile({
      backendBaseUrl: "http://127.0.0.1:8888",
      apiKey: localCredential(),
      connectedAt: fixedTimestamp,
      lastVerifiedAt: fixedTimestamp,
    })

    await expect(
      createCodexifyExtensionApi(profile).cancelTask("task-extension-test"),
    ).resolves.toBeUndefined()
  })

  it("accepts only lifecycle events correlated to the accepted receipt", () => {
    const receipt: CompletionReceipt = {
      taskId: "task-extension-test",
      requestId: "req-extension-test",
      turnId: "turn-extension-test",
      threadId: 7,
      acceptanceStatus: "accepted",
      acceptanceWarnings: [],
      messagesUrl: null,
      traceUrl: null,
    }
    const event = (data: Record<string, unknown>): TaskLifecycleEvent => ({
      type: "task.state",
      state: "running",
      data,
    })

    expect(isTaskLifecycleEventCorrelated(event({
      task_id: receipt.taskId,
      request_id: receipt.requestId,
      turn_id: receipt.turnId,
      thread_id: receipt.threadId,
    }), receipt)).toBe(true)
    expect(isTaskLifecycleEventCorrelated(event({
      taskId: receipt.taskId,
      requestCorrelation: { requestId: "req-other" },
      turnId: receipt.turnId,
    }), receipt)).toBe(false)
    expect(isTaskLifecycleEventCorrelated(event({
      task_id: receipt.taskId,
      turn_id: "turn-other",
    }), receipt)).toBe(false)
    expect(isTaskLifecycleEventCorrelated(event({}), receipt)).toBe(true)
  })
})
