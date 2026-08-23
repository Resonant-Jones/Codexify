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
  projectId: null,
  projectName: null,
  originSystem: null,
  providerOverride: null,
  modelOverride: null,
  threadConfig: null,
}

function threadPage(
  threads: CodexifyThread[],
  nextOffset = threads.length,
  hasMore = false,
) {
  return { threads, nextOffset, hasMore }
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
  content: "Persisted assistant reply with **bold** and `code`.",
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
    getUserProfile: vi.fn(async () => "default"),
    updateAccentColor: vi.fn(async () => undefined),
    listProjects: vi.fn(async () => []),
    listThreads: vi.fn(async () => threadPage([thread], 1)),
    getThread: vi.fn(async () => thread),
    createThread: vi.fn(async () => thread),
    listMessages: vi.fn(async () => [userMessage, assistantMessage]),
    listAgentRuns: vi.fn(async () => []),
    listPendingApprovals: vi.fn(async () => []),
    approveBrowserApproval: vi.fn(async (approvalId) => ({
      approvalId,
      operation: "evaluate",
      status: "APPROVED",
      target: null,
    })),
    denyBrowserApproval: vi.fn(async (approvalId) => ({
      approvalId,
      operation: "evaluate",
      status: "DENIED",
      target: null,
    })),
    persistUserMessage: vi.fn(async () => undefined),
    requestCompletion: vi.fn(async () => receipt),
    cancelTask: vi.fn(async () => undefined),
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

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()
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

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()
    expect(screen.getByText("Connected")).toBeVisible()
    expect(screen.getByRole("button", { name: /Existing thread/ })).toBeVisible()
    expect(screen.queryByDisplayValue(placeholderCredential())).not.toBeInTheDocument()
    expect(api.verifyConnection).toHaveBeenCalledTimes(1)

    // Assistant messages render through MarkdownMessage.
    expect(document.querySelector(".codexify-markdown")).toBeTruthy()
    // Bold markdown is rendered as <strong>.
    expect(document.querySelector(".codexify-markdown strong")).toBeTruthy()
    // Inline code is rendered as <code>.
    expect(document.querySelector(".codexify-markdown code")).toBeTruthy()

    // User messages remain literal — no codexify-markdown wrapper.
    const userArticle = document.querySelector('[data-message-id="message-user"]')
    expect(userArticle).toBeTruthy()
    expect(userArticle!.querySelector(".codexify-markdown")).toBeNull()
    expect(userArticle!.querySelector("p")).toBeTruthy()
    expect(userArticle!.textContent).toContain("Persisted user message")
  })

  it("observes project-scoped thread context and creates a New Chat in the explicit project lens", async () => {
    const { storage } = memoryStorage(savedProfile())
    const scopedThread: CodexifyThread = {
      ...thread,
      projectId: 12,
      projectName: "Project Atlas",
      originSystem: "openai",
      providerOverride: "override-provider",
      modelOverride: "override-model",
      threadConfig: {
        providerId: "canonical-provider",
        modelId: "canonical-model",
        inferenceMode: "deep",
        retrievalSource: "personal_knowledge",
        personaId: "persona-atlas",
      },
    }
    const projectThread: CodexifyThread = {
      ...scopedThread,
      id: 12,
      title: "Project-scoped conversation",
    }
    const api = apiMock({
      listProjects: vi.fn(async () => [{ id: 12, name: "Project Atlas", icon: "atlas" }]),
      listThreads: vi.fn(async (query) => query?.projectId === 12
        ? threadPage([projectThread], 1)
        : threadPage([scopedThread], 1)),
      createThread: vi.fn(async () => projectThread),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText("Project Atlas")).toBeVisible()
    expect(screen.getByText("Openai")).toBeVisible()
    expect(screen.getByText("canonical-provider")).toBeVisible()
    expect(screen.getByText("canonical-model")).toBeVisible()
    expect(screen.queryByText("override-provider")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Existing thread/ }))
    const projectScope = screen.getByLabelText("Project scope")
    expect(screen.getByRole("option", { name: "Project Atlas" })).toBeVisible()
    fireEvent.change(projectScope, { target: { value: "12" } })

    await waitFor(() => {
      expect(api.listThreads).toHaveBeenLastCalledWith({
        limit: 50,
        offset: 0,
        projectId: 12,
      })
    })

    fireEvent.click(screen.getByRole("button", { name: "New Chat" }))
    await waitFor(() => {
      expect(api.createThread).toHaveBeenCalledWith("New Chat", 12)
    })
  })

  it("uses only the canonical provenance lens when the origin scope changes", async () => {
    const { storage } = memoryStorage(savedProfile())
    const importedThread: CodexifyThread = {
      ...thread,
      id: 22,
      title: "Imported conversation",
      originSystem: "anthropic",
    }
    const api = apiMock({
      listThreads: vi.fn(async (query) => query?.originSystem === "anthropic"
        ? threadPage([importedThread], 1)
        : threadPage([thread], 1)),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    fireEvent.click(await screen.findByRole("button", { name: /Existing thread/ }))
    fireEvent.change(screen.getByLabelText("Conversation origin"), {
      target: { value: "anthropic" },
    })

    await waitFor(() => {
      expect(api.listThreads).toHaveBeenLastCalledWith({
        limit: 50,
        offset: 0,
        originSystem: "anthropic",
      })
    })
    expect(await screen.findByRole("button", { name: "Imported conversation" })).toBeVisible()
  })

  it("loads later pages without duplicates and retains selected-thread truth across a scope reset", async () => {
    const { storage } = memoryStorage(savedProfile())
    const secondThread: CodexifyThread = { ...thread, id: 8, title: "Second page seed" }
    const laterThread: CodexifyThread = { ...thread, id: 9, title: "Later conversation" }
    const projectThread: CodexifyThread = { ...thread, id: 12, title: "Project result", projectId: 12 }
    const api = apiMock({
      listProjects: vi.fn(async () => [{ id: 12, name: "Project Atlas", icon: null }]),
      listThreads: vi.fn(async (query) => {
        if (query?.projectId === 12) return threadPage([projectThread], 1)
        if (query?.offset === 50) return threadPage([thread, laterThread], 52)
        return threadPage([thread, secondThread], 50, true)
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

    fireEvent.click(await screen.findByRole("button", { name: /Existing thread/ }))
    fireEvent.click(screen.getByRole("button", { name: "Load more" }))
    expect(await screen.findByRole("button", { name: "Later conversation" })).toBeVisible()
    expect(screen.getAllByRole("button", { name: "Existing thread" })).toHaveLength(2)
    expect(api.listThreads).toHaveBeenLastCalledWith({ limit: 50, offset: 50 })
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText("Project scope"), { target: { value: "12" } })
    await waitFor(() => {
      expect(api.listThreads).toHaveBeenLastCalledWith({
        limit: 50,
        offset: 0,
        projectId: 12,
      })
    })
    expect(screen.getByRole("button", { name: /Existing thread/ })).toBeVisible()
    expect(screen.getByLabelText("Selected thread context")).toBeVisible()
  })

  it("renders an honest unspecified provider and model when selected configuration is absent", async () => {
    const { storage } = memoryStorage(savedProfile())
    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => apiMock()}
        now={fixedNow}
      />,
    )

    expect(await screen.findByLabelText("Selected thread context")).toBeVisible()
    expect(screen.getAllByText("Unspecified")).toHaveLength(2)
  })

  it("projects the selected thread's Guardian approval above the composer", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock({
      listAgentRuns: vi.fn(async () => [{
        run_id: "run_7",
        runtime_target: "guardian",
        status: "awaiting_approval",
        thread_id: 7,
        worktree_id: "worktree_7",
        worktree_path: "/private/worktree-7",
      }]),
      listPendingApprovals: vi.fn(async () => [{
        id: 17,
        operation: "evaluate",
        request_reason: "Guarded action for thread_id:7 run_7",
        status: "PENDING",
        target: "browser action",
      }]),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    const card = await screen.findByTestId("side-panel-intervention")
    const composer = screen.getByLabelText("Message Codexify")
    expect(screen.getByText("Guardian needs your approval")).toBeVisible()
    expect(screen.queryByText("Run: run_7")).not.toBeInTheDocument()
    expect(
      card.compareDocumentPosition(composer) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()

    fireEvent.click(screen.getByRole("button", { name: "Inspect context" }))
    expect(screen.getByText("Run: run_7")).toBeVisible()
  })

  it("submits one exact approval decision and refreshes Guardian truth", async () => {
    const { storage } = memoryStorage(savedProfile())
    const listPendingApprovals = vi
      .fn<CodexifyExtensionApi["listPendingApprovals"]>()
      .mockResolvedValueOnce([{
        id: 17,
        operation: "evaluate",
        request_reason: "thread_id:7 run_7",
        status: "PENDING",
        target: "browser action",
      }])
      .mockResolvedValue([])
    const api = apiMock({
      listAgentRuns: vi.fn(async () => [{
        run_id: "run_7",
        runtime_target: null,
        status: "awaiting_approval",
        thread_id: 7,
        worktree_id: null,
        worktree_path: null,
      }]),
      listPendingApprovals,
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    const approve = await screen.findByRole("button", {
      name: "Approve Guardian request",
    })
    fireEvent.click(approve)
    fireEvent.click(approve)

    expect(await screen.findByText("Approved.")).toBeVisible()
    expect(api.approveBrowserApproval).toHaveBeenCalledTimes(1)
    expect(api.approveBrowserApproval).toHaveBeenCalledWith(
      17,
      "Approved from thread 7 side panel.",
    )
    expect(listPendingApprovals).toHaveBeenCalledTimes(2)
    expect(
      screen.queryByRole("button", { name: "Approve Guardian request" }),
    ).not.toBeInTheDocument()
  })

  it("submits one exact denial and never treats composer Enter as approval", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock({
      listAgentRuns: vi.fn(async () => [{
        run_id: "run_7",
        runtime_target: null,
        status: "awaiting_approval",
        thread_id: 7,
        worktree_id: null,
        worktree_path: null,
      }]),
      listPendingApprovals: vi.fn(async () => [{
        id: 23,
        operation: "evaluate",
        request_reason: "thread_id:7 run_7",
        status: "PENDING",
        target: null,
      }]),
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
    fireEvent.change(composer, { target: { value: "Do something else" } })
    fireEvent.keyDown(composer, { key: "Enter" })
    expect(api.approveBrowserApproval).not.toHaveBeenCalled()

    fireEvent.click(
      await screen.findByRole("button", { name: "Deny Guardian request" }),
    )
    await waitFor(() => {
      expect(api.denyBrowserApproval).toHaveBeenCalledTimes(1)
    })
    expect(api.denyBrowserApproval).toHaveBeenCalledWith(
      23,
      "Denied from thread 7 side panel.",
    )
  })

  it("removes stale intervention state when the selected thread changes", async () => {
    const { storage } = memoryStorage(savedProfile())
    const secondThread: CodexifyThread = {
      ...thread,
      id: 8,
      title: "Second thread",
    }
    const api = apiMock({
      listThreads: vi.fn(async () => ({
        threads: [thread, secondThread],
        nextOffset: 2,
        hasMore: false,
      })),
      listAgentRuns: vi.fn(async (threadId) => threadId === 7 ? [{
        run_id: "run_7",
        runtime_target: null,
        status: "awaiting_approval",
        thread_id: 7,
        worktree_id: null,
        worktree_path: null,
      }] : []),
      listPendingApprovals: vi.fn(async () => [{
        id: 17,
        operation: "evaluate",
        request_reason: "thread_id:7 run_7",
        status: "PENDING",
        target: null,
      }]),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByTestId("side-panel-intervention")).toBeVisible()
    fireEvent.click(screen.getByRole("button", { name: /Existing thread/ }))
    fireEvent.click(screen.getByRole("button", { name: "Second thread" }))

    await waitFor(() => {
      expect(screen.queryByTestId("side-panel-intervention")).not.toBeInTheDocument()
    })
    expect(api.listAgentRuns).toHaveBeenCalledWith(8)
  })

  it("renders assistant messages as Markdown and keeps user messages literal", async () => {
    const { storage } = memoryStorage(savedProfile())
    const mdAssistant: CodexifyMessage = {
      ...assistantMessage,
      content: "**Bold** and *italic* assistant reply.",
    }
    const api = apiMock({
      listMessages: vi.fn(async () => [userMessage, mdAssistant]),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText(/Bold/)).toBeVisible()

    // Assistant article has the codexify-markdown container.
    const assistantArticle = document.querySelector('[data-message-id="message-assistant"]')
    expect(assistantArticle!.querySelector(".codexify-markdown")).toBeTruthy()
    expect(assistantArticle!.querySelector("strong")).toHaveTextContent("Bold")
    expect(assistantArticle!.querySelector("em")).toHaveTextContent("italic")

    // User article has a plain <p>, not the Markdown renderer.
    const userArticle = document.querySelector('[data-message-id="message-user"]')
    expect(userArticle!.querySelector(".codexify-markdown")).toBeNull()
    expect(userArticle!.querySelector("p")).toBeTruthy()
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

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()
    expect(screen.getByText("Completed")).toBeVisible()

    // After terminal completion, the assistant message still uses the Markdown renderer.
    expect(document.querySelector(".codexify-markdown")).toBeTruthy()
  })

  it("refreshes intervention visibility from active task lifecycle evidence", async () => {
    const { storage } = memoryStorage(savedProfile())
    let callbacks: TaskLifecycleCallbacks | null = null
    const listAgentRuns = vi
      .fn<CodexifyExtensionApi["listAgentRuns"]>()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValue([{
        run_id: "run_lifecycle",
        runtime_target: null,
        status: "awaiting_approval",
        thread_id: 7,
        worktree_id: null,
        worktree_path: null,
      }])
    const api = apiMock({
      listAgentRuns,
      listPendingApprovals: vi.fn(async () => [{
        id: 41,
        operation: "evaluate",
        request_reason: "thread_id:7 run_lifecycle",
        status: "PENDING",
        target: null,
      }]),
      subscribeToTask: vi.fn((_receipt, nextCallbacks) => {
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
    fireEvent.change(composer, { target: { value: "Run guarded work" } })
    fireEvent.submit(composer.closest("form") as HTMLFormElement)
    expect(await screen.findByText("Completion accepted")).toBeVisible()
    expect(screen.queryByTestId("side-panel-intervention")).not.toBeInTheDocument()

    await act(async () => {
      callbacks?.onEvent?.({
        type: "task.running",
        state: "running",
        data: { task_id: receipt.taskId },
      })
    })

    expect(await screen.findByTestId("side-panel-intervention")).toBeVisible()
    expect(listAgentRuns).toHaveBeenCalledTimes(3)
    expect(api.requestCompletion).toHaveBeenCalledTimes(1)
  })

  it("requests cancellation and waits for terminal cancelled evidence", async () => {
    const { storage } = memoryStorage(savedProfile())
    let callbacks: TaskLifecycleCallbacks | null = null
    const api = apiMock({
      subscribeToTask: vi.fn((_receipt, nextCallbacks) => {
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
    fireEvent.change(composer, { target: { value: "Cancel this private completion" } })
    fireEvent.submit(composer.closest("form") as HTMLFormElement)

    expect(await screen.findByText("Completion accepted")).toBeVisible()
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))

    expect(await screen.findByText("Cancellation requested")).toBeVisible()
    expect(api.cancelTask).toHaveBeenCalledWith(receipt.taskId)
    expect(screen.queryByText("Cancelled")).not.toBeInTheDocument()

    await act(async () => {
      callbacks?.onTerminal?.("cancelled", {
        type: "task.cancelled",
        state: "cancelled",
        data: {
          task_id: receipt.taskId,
          request_id: receipt.requestId,
          turn_id: receipt.turnId,
        },
      })
    })

    expect(await screen.findByText("Cancelled")).toBeVisible()
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

  // ── accent colour tests ────────────────────────────────────────────

  it("hydrates the default accent from the backend profile after connection", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock({ getUserProfile: vi.fn(async () => "default") })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()
    expect(api.getUserProfile).toHaveBeenCalledTimes(1)

    // The default accent means no accented class on user messages.
    const userArticle = document.querySelector('[data-message-id="message-user"]')
    expect(userArticle?.classList.contains("message--accented")).toBe(false)
  })

  it("applies a non-default accent to user messages", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock({ getUserProfile: vi.fn(async () => "violet") })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()

    // User message should have the accented class.
    const userArticle = document.querySelector('[data-message-id="message-user"]')
    expect(userArticle?.classList.contains("message--accented")).toBe(true)

    // Assistant message should remain neutral.
    const assistantArticle = document.querySelector('[data-message-id="message-assistant"]')
    expect(assistantArticle?.classList.contains("message--accented")).toBe(false)
  })

  it("falls back to default accent when profile read fails", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock({
      getUserProfile: vi.fn(async () => { throw new Error("unreachable") }),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    // Chat still works — profile failure is non-fatal.
    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()
    expect(api.getUserProfile).toHaveBeenCalledTimes(1)

    // Default accent means no accented class.
    const userArticle = document.querySelector('[data-message-id="message-user"]')
    expect(userArticle?.classList.contains("message--accented")).toBe(false)
  })

  it("shows the accent selector and can change the accent", async () => {
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

    // Wait for the connected shell.
    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()

    // Open the accent picker.
    const swatchButton = screen.getByRole("button", { name: /Accent colour:/i })
    expect(swatchButton).toBeVisible()
    fireEvent.click(swatchButton)

    // All accent choices should be visible.
    expect(screen.getByRole("option", { name: "Default" })).toBeVisible()
    expect(screen.getByRole("option", { name: "Violet" })).toBeVisible()
    expect(screen.getByRole("option", { name: "Amber" })).toBeVisible()

    // Select violet.
    fireEvent.click(screen.getByRole("option", { name: "Violet" }))

    // The API should have been called to persist the choice.
    await waitFor(() => {
      expect(api.updateAccentColor).toHaveBeenCalledWith("violet")
    })
  })

  it("rolls back accent on save failure", async () => {
    const { storage } = memoryStorage(savedProfile())
    const api = apiMock({
      getUserProfile: vi.fn(async () => "default"),
      updateAccentColor: vi.fn(async () => { throw new Error("unreachable") }),
    })

    render(
      <SidePanelApp
        storage={storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()

    // Open picker, select rose.
    fireEvent.click(screen.getByRole("button", { name: /Accent colour:/i }))
    fireEvent.click(screen.getByRole("option", { name: "Rose" }))

    // Save error should appear.
    expect(await screen.findByText(/Accent not saved/)).toBeVisible()

    // The accent should remain on default (rolled back).
    const userArticle = document.querySelector('[data-message-id="message-user"]')
    expect(userArticle?.classList.contains("message--accented")).toBe(false)
  })

  it("does not persist the accent to Chrome storage", async () => {
    const memory = memoryStorage(savedProfile())
    const api = apiMock({
      getUserProfile: vi.fn(async () => "violet"),
    })

    render(
      <SidePanelApp
        storage={memory.storage}
        permissionClient={permissionMock()}
        apiFactory={() => api}
        now={fixedNow}
      />,
    )

    expect(await screen.findByText(/Persisted assistant reply/)).toBeVisible()

    // After hydration, the saved profile should still contain the same fields.
    const saved = memory.current()
    expect(saved).toBeTruthy()
    // The stored profile never gains an accent_color or accent field.
    const savedJson = JSON.stringify(saved)
    expect(savedJson).not.toContain("accent")

    // The connection-storage save was called but only with the connection profile.
    expect(memory.storage.save).toHaveBeenCalled()
    const lastSaveCall = (memory.storage.save as ReturnType<typeof vi.fn>).mock.calls.slice(-1)[0]?.[0]
    if (lastSaveCall) {
      expect(lastSaveCall).not.toHaveProperty("accent_color")
      expect(lastSaveCall).not.toHaveProperty("accentColor")
      expect(lastSaveCall).not.toHaveProperty("accent")
    }
  })
})
