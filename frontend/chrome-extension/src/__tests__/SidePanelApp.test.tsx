import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SidePanelApp } from "../SidePanelApp"
import {
  CONNECTION_PROFILE_VERSION,
  buildOriginPermissionPattern,
  type ConnectionProfile,
  type OriginPermissionClient,
  type RemoteSessionCredential,
} from "../connectionProfile"
import type { ConnectionStorage } from "../chromeStorage"
import type {
  CodexifyExtensionApi,
  CodexifyMessage,
  CodexifyThread,
  CompletionReceipt,
  TaskLifecycleCallbacks,
} from "../codexifyExtensionApi"

const fixedTimestamp = "2026-07-21T12:00:00.000Z"
const fixedNow = (): string => fixedTimestamp
const placeholderCredential = (): string => ["unit", "test", "credential"].join("-")
const placeholderPassword = (): string => ["unit", "test", "password"].join("-")
const remoteSession: RemoteSessionCredential = {
  token: ["unit", "test", "session"].join("-"),
  userId: "remote-user",
  expiresAt: 1_900_000_000,
}

function savedProfile(selectedThreadId: number | null = 7): ConnectionProfile {
  return {
    version: CONNECTION_PROFILE_VERSION,
    backendBaseUrl: "http://127.0.0.1:8888",
    authMode: "local",
    apiKey: placeholderCredential(),
    sessionUserId: null,
    sessionExpiresAt: null,
    selectedThreadId,
    connectedAt: fixedTimestamp,
    lastVerifiedAt: fixedTimestamp,
  }
}

function savedRemoteProfile(selectedThreadId: number | null = 7): ConnectionProfile {
  return {
    version: CONNECTION_PROFILE_VERSION,
    backendBaseUrl: "https://codexify.test",
    authMode: "remote",
    apiKey: null,
    sessionUserId: remoteSession.userId,
    sessionExpiresAt: remoteSession.expiresAt,
    selectedThreadId,
    connectedAt: fixedTimestamp,
    lastVerifiedAt: fixedTimestamp,
  }
}

function memoryStorage(
  initial: ConnectionProfile | null,
  initialSession: RemoteSessionCredential | null = null,
): {
  storage: ConnectionStorage
  current(): ConnectionProfile | null
  currentSession(): RemoteSessionCredential | null
} {
  let value = initial ? { ...initial } : null
  let sessionValue = initialSession ? { ...initialSession } : null
  const storage: ConnectionStorage = {
    load: vi.fn(async () => (value ? { ...value } : null)),
    save: vi.fn(async (next) => {
      value = { ...next }
    }),
    loadRemoteSession: vi.fn(async () => (sessionValue ? { ...sessionValue } : null)),
    saveRemoteSession: vi.fn(async (next) => {
      sessionValue = { ...next }
    }),
    clearRemoteSession: vi.fn(async () => {
      sessionValue = null
    }),
    updateSelectedThreadId: vi.fn(async (selectedThreadId) => {
      if (value) value = { ...value, selectedThreadId }
    }),
    clear: vi.fn(async () => {
      value = null
      sessionValue = null
    }),
  }
  return {
    storage,
    current: () => (value ? { ...value } : null),
    currentSession: () => (sessionValue ? { ...sessionValue } : null),
  }
}

function permissionMock(): OriginPermissionClient & {
  request: ReturnType<typeof vi.fn>
  contains: ReturnType<typeof vi.fn>
  remove: ReturnType<typeof vi.fn>
} {
  return {
    request: vi.fn(async () => true),
    contains: vi.fn(async () => true),
    remove: vi.fn(async () => true),
  }
}

const thread: CodexifyThread = {
  id: 7,
  title: "Existing thread",
  createdAt: fixedTimestamp,
  updatedAt: fixedTimestamp,
}

const userMessage: CodexifyMessage = {
  id: "message-user",
  threadId: 7,
  role: "user",
  content: "Persisted user message",
  createdAt: "2026-07-21T12:00:01.000Z",
  turnId: "turn-unit",
}

const assistantMessage: CodexifyMessage = {
  id: "message-assistant",
  threadId: 7,
  role: "assistant",
  content: "Persisted assistant reply",
  createdAt: "2026-07-21T12:00:02.000Z",
  turnId: "turn-unit",
}

const receipt: CompletionReceipt = {
  taskId: "task-unit-12345678",
  requestId: "request-unit",
  turnId: "turn-unit",
  threadId: 7,
  acceptanceStatus: "accepted",
  acceptanceWarnings: [],
  messagesUrl: "/api/chat/7/messages",
  traceUrl: "/api/chat/debug/rag-trace/7/latest",
}

function apiMock(overrides: Partial<CodexifyExtensionApi> = {}): CodexifyExtensionApi {
  return {
    verifyConnection: vi.fn(async () => undefined),
    logout: vi.fn(async () => undefined),
    listThreads: vi.fn(async () => [thread]),
    createThread: vi.fn(async () => thread),
    listMessages: vi.fn(async () => [userMessage, assistantMessage]),
    persistUserMessage: vi.fn(async () => undefined),
    requestCompletion: vi.fn(async () => receipt),
    subscribeToTask: vi.fn(() => () => undefined),
    ...overrides,
  }
}

describe("Codexify Chrome side panel", () => {
  it("shows the disconnected connection form on first run", async () => {
    const { storage } = memoryStorage(null)

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => apiMock()}
        now={fixedNow}
      />,
    )

    expect(await screen.findByRole("heading", { name: "Connect your private runtime" })).toBeVisible()
    expect(screen.getByLabelText("Authentication API key")).toHaveAttribute("type", "password")
    expect(screen.getByRole("button", { name: "Remote session" })).toBeVisible()
    expect(screen.getByText(/never Chrome Sync/i)).toBeVisible()
  })

  it("requests the configured origin before verification and local profile storage", async () => {
    const memory = memoryStorage(null)
    const order: string[] = []
    const originalSave = memory.storage.save
    memory.storage.save = vi.fn(async (profile) => {
      order.push("save")
      await originalSave(profile)
    })
    const permissions = permissionMock()
    permissions.request.mockImplementation(async () => {
      order.push("permission")
      return true
    })
    const api = apiMock({
      verifyConnection: vi.fn(async () => {
        order.push("verify")
      }),
    })

    render(
      <SidePanelApp
        storage={memory.storage}
        permissionClient={permissions}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    fireEvent.change(await screen.findByLabelText("Backend URL"), {
      target: { value: "https://codexify.test:9443/" },
    })
    fireEvent.change(screen.getByLabelText("Authentication API key"), {
      target: { value: placeholderCredential() },
    })
    fireEvent.click(screen.getByRole("button", { name: "Save and connect" }))

    expect(await screen.findByText("Connected")).toBeVisible()
    expect(permissions.request).toHaveBeenCalledWith("https://codexify.test:9443/*")
    expect(order.slice(0, 3)).toEqual(["permission", "verify", "save"])
    expect(memory.current()?.apiKey).toBe(placeholderCredential())
    expect(screen.queryByDisplayValue(placeholderCredential())).not.toBeInTheDocument()
  })

  it("creates a remote session without storing the password or sending an API key profile", async () => {
    const memory = memoryStorage(null)
    const permissions = permissionMock()
    const remoteLogin = vi.fn(async () => remoteSession)
    const api = apiMock()
    const apiFactory = vi.fn(() => api)

    render(
      <SidePanelApp
        storage={memory.storage}
        permissionClient={permissions}
        apiFactory={apiFactory}
        remoteLogin={remoteLogin}
        now={fixedNow}
      />,
    )

    fireEvent.change(await screen.findByLabelText("Backend URL"), {
      target: { value: "https://codexify.test/" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Remote session" }))
    fireEvent.change(screen.getByLabelText("Codexify username"), {
      target: { value: remoteSession.userId },
    })
    fireEvent.change(screen.getByLabelText("Codexify password"), {
      target: { value: placeholderPassword() },
    })
    fireEvent.click(screen.getByRole("button", { name: "Sign in and connect" }))

    expect(await screen.findByText("Connected")).toBeVisible()
    expect(remoteLogin).toHaveBeenCalledWith("https://codexify.test", {
      username: remoteSession.userId,
      password: placeholderPassword(),
    })
    expect(memory.current()).toMatchObject({
      authMode: "remote",
      apiKey: null,
      sessionUserId: remoteSession.userId,
    })
    expect(memory.currentSession()).toEqual(remoteSession)
    expect(apiFactory).toHaveBeenCalledWith(
      expect.objectContaining({ authMode: "remote", apiKey: null }),
      remoteSession,
    )
    expect(JSON.stringify(memory.current())).not.toContain(remoteSession.token)
    expect(JSON.stringify(memory.current())).not.toContain(placeholderPassword())
  })

  it("restores a remote chat shell from session-scoped storage", async () => {
    const { storage } = memoryStorage(savedRemoteProfile(), remoteSession)
    const api = apiMock()
    const apiFactory = vi.fn(() => api)

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={apiFactory}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText("Persisted assistant reply")).toBeVisible()
    expect(apiFactory).toHaveBeenCalledWith(
      expect.objectContaining({ authMode: "remote" }),
      remoteSession,
    )
  })

  it("returns a remote profile without a live token to the sign-in form", async () => {
    const memory = memoryStorage(savedRemoteProfile(), null)

    render(
      <SidePanelApp
        storage={memory.storage}
        permissionClient={permissionMock()}
        apiFactory={() => apiMock()}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText("Remote sign-in required")).toBeVisible()
    expect(screen.getByLabelText("Backend URL")).toHaveValue("https://codexify.test")
    expect(screen.getByRole("button", { name: "Remote session" })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
    expect(memory.storage.clearRemoteSession).toHaveBeenCalledTimes(1)
  })

  it("restores a connected chat shell and persisted messages", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock()

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText("Persisted assistant reply")).toBeVisible()
    expect(screen.getByText("Connected")).toBeVisible()
    expect(screen.getByRole("button", { name: /Existing thread/ })).toBeVisible()
    expect(screen.queryByDisplayValue(placeholderCredential())).not.toBeInTheDocument()
    expect(api.verifyConnection).toHaveBeenCalledTimes(1)
  })

  it("rejects an empty composer submission without calling the backend", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock()

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    const composer = await screen.findByLabelText("Message Codexify")
    fireEvent.change(composer, { target: { value: "   " } })
    fireEvent.submit(composer.closest("form") as HTMLFormElement)

    expect(api.persistUserMessage).not.toHaveBeenCalled()
    expect(api.requestCompletion).not.toHaveBeenCalled()
  })

  it("keeps completion acceptance distinct from terminal completion", async () => {
    const { storage } = memoryStorage(savedProfile())
    let callbacks: TaskLifecycleCallbacks | null = null
    const listMessages = vi
      .fn<CodexifyExtensionApi["listMessages"]>()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([userMessage])
      .mockResolvedValueOnce([userMessage, assistantMessage])
    const api = apiMock({
      listMessages,
      subscribeToTask: vi.fn((_taskId, nextCallbacks) => {
        callbacks = nextCallbacks
        return () => undefined
      }),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    const composer = await screen.findByLabelText("Message Codexify")
    fireEvent.change(composer, { target: { value: "Run one private completion" } })
    fireEvent.submit(composer.closest("form") as HTMLFormElement)

    expect(await screen.findByText("Completion accepted")).toBeVisible()
    expect(screen.queryByText("Completed")).not.toBeInTheDocument()
    expect(api.persistUserMessage).toHaveBeenCalledWith(7, "Run one private completion")
    expect(api.requestCompletion).toHaveBeenCalledWith(7)

    await act(async () => {
      callbacks?.onTerminal?.("completed", {
        type: "task.completed",
        state: "completed",
        data: { task_id: receipt.taskId },
      })
    })

    expect(await screen.findByText("Persisted assistant reply")).toBeVisible()
    expect(screen.getByText("Completed")).toBeVisible()
  })

  it("disconnects by clearing the stored credential and granted origin", async () => {
    const memory = memoryStorage(savedProfile())
    const permissions = permissionMock()

    render(
      <SidePanelApp
        storage={memory.storage}
        permissionClient={permissions}
        apiFactory={() => apiMock()}
        now={fixedNow}
      />,
    )

    const switcher = await screen.findByRole("button", { name: /Existing thread/ })
    fireEvent.click(switcher)
    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }))

    expect(await screen.findByRole("heading", { name: "Connect your private runtime" })).toBeVisible()
    expect(memory.storage.clear).toHaveBeenCalledTimes(1)
    expect(memory.current()).toBeNull()
    expect(permissions.remove).toHaveBeenCalledWith(
      buildOriginPermissionPattern("http://127.0.0.1:8888"),
    )
  })

  it("revokes and clears a remote session on disconnect", async () => {
    const memory = memoryStorage(savedRemoteProfile(), remoteSession)
    const permissions = permissionMock()
    const api = apiMock()

    render(
      <SidePanelApp
        storage={memory.storage}
        permissionClient={permissions}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    fireEvent.click(await screen.findByRole("button", { name: /Existing thread/ }))
    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }))

    expect(await screen.findByRole("heading", { name: "Connect your private runtime" })).toBeVisible()
    expect(api.logout).toHaveBeenCalledTimes(1)
    expect(memory.current()).toBeNull()
    expect(memory.currentSession()).toBeNull()
  })
})
