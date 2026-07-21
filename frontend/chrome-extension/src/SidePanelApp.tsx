import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import {
  CHAT_REQUEST_STATES,
  type ChatRequestState,
} from "../../src/contracts/runtimeTokens"
import {
  buildOriginPermissionPattern,
  chromeOriginPermissionClient,
  createConnectionProfile,
  type ConnectionProfile,
  type OriginPermissionClient,
} from "./connectionProfile"
import {
  chromeConnectionStorage,
  type ConnectionStorage,
} from "./chromeStorage"
import {
  classifyCodexifyError,
  createCodexifyExtensionApi,
  type CodexifyExtensionApi,
  type CodexifyMessage,
  type CodexifyThread,
  type CompletionReceipt,
  type TaskLifecycleEvent,
} from "./codexifyExtensionApi"

type BootState = "loading" | "disconnected" | "connected"
type ConnectionState =
  | "checking"
  | "ready"
  | "unreachable"
  | "authentication_rejected"
type CompletionViewState = ChatRequestState | "idle" | "connection_lost"
type MessageLoadState = "idle" | "loading" | "ready" | "failed"

export interface SidePanelAppProps {
  storage?: ConnectionStorage
  permissionClient?: OriginPermissionClient
  apiFactory?: (profile: ConnectionProfile) => CodexifyExtensionApi
  now?: () => string
}

interface StatusPresentation {
  label: string
  detail: string
  tone: "neutral" | "active" | "attention" | "danger"
}

const COMPLETION_PRESENTATION: Record<CompletionViewState, StatusPresentation> = {
  idle: {
    label: "Ready",
    detail: "Messages are persisted before completion work is requested.",
    tone: "neutral",
  },
  [CHAT_REQUEST_STATES.DISPATCHING]: {
    label: "Sending message",
    detail: "Persisting the user message before requesting completion.",
    tone: "attention",
  },
  [CHAT_REQUEST_STATES.AWAITING_ACK]: {
    label: "Completion accepted",
    detail: "The request is accepted and still pending worker evidence.",
    tone: "attention",
  },
  [CHAT_REQUEST_STATES.AWAITING_MODEL]: {
    label: "Waiting for worker/model",
    detail: "The accepted task is running. No second request will be created.",
    tone: "attention",
  },
  [CHAT_REQUEST_STATES.STREAMING]: {
    label: "Waiting for persisted reply",
    detail: "Lifecycle events are visible; the saved assistant message remains authoritative.",
    tone: "attention",
  },
  [CHAT_REQUEST_STATES.COMPLETED]: {
    label: "Completed",
    detail: "Terminal evidence arrived and the persisted transcript was refreshed.",
    tone: "active",
  },
  [CHAT_REQUEST_STATES.FAILED_RETRYABLE]: {
    label: "Failed",
    detail: "The completion task reported failure. Your user message remains persisted.",
    tone: "danger",
  },
  [CHAT_REQUEST_STATES.FAILED_FATAL]: {
    label: "Failed",
    detail: "The completion task reported a terminal failure.",
    tone: "danger",
  },
  [CHAT_REQUEST_STATES.CANCELLED]: {
    label: "Cancelled",
    detail: "The completion task ended without a completed assistant reply.",
    tone: "danger",
  },
  [CHAT_REQUEST_STATES.ORPHANED]: {
    label: "Task state unavailable",
    detail: "The request identity is preserved; no automatic replay will occur.",
    tone: "danger",
  },
  connection_lost: {
    label: "Connection lost",
    detail: "Task observation is reconnecting. Missing events are not proof of failure.",
    tone: "danger",
  },
}

const CONNECTION_PRESENTATION: Record<ConnectionState, StatusPresentation> = {
  checking: {
    label: "Checking",
    detail: "Verifying runtime reachability and authenticated chat access.",
    tone: "attention",
  },
  ready: {
    label: "Connected",
    detail: "Authenticated chat access is ready.",
    tone: "active",
  },
  unreachable: {
    label: "Runtime unreachable",
    detail: "The saved runtime address is not responding.",
    tone: "danger",
  },
  authentication_rejected: {
    label: "Authentication rejected",
    detail: "The runtime rejected the saved credential.",
    tone: "danger",
  },
}

function displayError(error: unknown): string {
  const kind = classifyCodexifyError(error)
  if (kind === "unreachable") return "The Codexify runtime could not be reached."
  if (kind === "authentication_rejected") return "The backend rejected this API key."
  if (kind === "invalid_response") return "The backend returned an unexpected chat response."
  return error instanceof Error ? error.message : "The Codexify request failed."
}

function connectionStateForError(error: unknown): ConnectionState | null {
  const kind = classifyCodexifyError(error)
  if (kind === "unreachable") return "unreachable"
  if (kind === "authentication_rejected") return "authentication_rejected"
  return null
}

function threadTitleFromMessage(message: string): string {
  const firstLine = message.split("\n", 1)[0]?.trim() ?? ""
  return firstLine.slice(0, 60) || "New Chat"
}

function isWorkerProgressEvent(event: TaskLifecycleEvent): boolean {
  return ["task.running", "task.progress", "task.event", "task.state"].includes(event.type)
}

const currentIsoTimestamp = (): string => new Date().toISOString()

export function SidePanelApp({
  storage = chromeConnectionStorage,
  permissionClient = chromeOriginPermissionClient,
  apiFactory = createCodexifyExtensionApi,
  now = currentIsoTimestamp,
}: SidePanelAppProps): React.JSX.Element {
  const [bootState, setBootState] = useState<BootState>("loading")
  const [profile, setProfile] = useState<ConnectionProfile | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>("checking")
  const [connectionAttempt, setConnectionAttempt] = useState<StatusPresentation | null>(null)
  const [backendInput, setBackendInput] = useState("")
  const [apiKeyInput, setApiKeyInput] = useState("")
  const [threads, setThreads] = useState<CodexifyThread[]>([])
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null)
  const [threadsLoading, setThreadsLoading] = useState(false)
  const [threadDrawerOpen, setThreadDrawerOpen] = useState(false)
  const [messages, setMessages] = useState<CodexifyMessage[]>([])
  const [messageLoadState, setMessageLoadState] = useState<MessageLoadState>("idle")
  const [composerValue, setComposerValue] = useState("")
  const [completionState, setCompletionState] = useState<CompletionViewState>("idle")
  const [completionReceipt, setCompletionReceipt] = useState<CompletionReceipt | null>(null)
  const [surfaceError, setSurfaceError] = useState<string | null>(null)
  const [operationBusy, setOperationBusy] = useState(false)

  const apiRef = useRef<CodexifyExtensionApi | null>(null)
  const activeTaskStopRef = useRef<(() => void) | null>(null)
  const messageEndRef = useRef<HTMLDivElement | null>(null)

  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) ?? null,
    [selectedThreadId, threads],
  )
  const visibleMessages = useMemo(
    () => messages.filter((message) => message.role === "user" || message.role === "assistant"),
    [messages],
  )
  const completionPresentation = COMPLETION_PRESENTATION[completionState]
  const connectionPresentation = CONNECTION_PRESENTATION[connectionState]
  const completionPending = [
    CHAT_REQUEST_STATES.DISPATCHING,
    CHAT_REQUEST_STATES.AWAITING_ACK,
    CHAT_REQUEST_STATES.AWAITING_MODEL,
    CHAT_REQUEST_STATES.STREAMING,
    "connection_lost",
  ].includes(completionState)

  const recordConnectionFailure = useCallback((error: unknown): void => {
    const nextState = connectionStateForError(error)
    if (nextState) setConnectionState(nextState)
    setSurfaceError(displayError(error))
  }, [])

  const loadMessages = useCallback(async (
    api: CodexifyExtensionApi,
    threadId: number,
    discoveryUrl?: string | null,
  ): Promise<boolean> => {
    setMessageLoadState("loading")
    try {
      const nextMessages = await api.listMessages(threadId, discoveryUrl)
      setMessages(nextMessages)
      setMessageLoadState("ready")
      return true
    } catch (error) {
      setMessageLoadState("failed")
      recordConnectionFailure(error)
      return false
    }
  }, [recordConnectionFailure])

  const rememberSelectedThread = useCallback(async (threadId: number | null): Promise<void> => {
    setProfile((current) => current ? { ...current, selectedThreadId: threadId } : current)
    await storage.updateSelectedThreadId(threadId)
  }, [storage])

  const hydrateChat = useCallback(async (
    api: CodexifyExtensionApi,
    preferredThreadId: number | null,
  ): Promise<void> => {
    setThreadsLoading(true)
    try {
      const nextThreads = await api.listThreads()
      setThreads(nextThreads)
      const preferredExists = nextThreads.some((thread) => thread.id === preferredThreadId)
      const nextSelectedThreadId = preferredExists
        ? preferredThreadId
        : nextThreads[0]?.id ?? null
      setSelectedThreadId(nextSelectedThreadId)
      await rememberSelectedThread(nextSelectedThreadId)
      if (nextSelectedThreadId === null) {
        setMessages([])
        setMessageLoadState("ready")
      } else {
        await loadMessages(api, nextSelectedThreadId)
      }
    } catch (error) {
      recordConnectionFailure(error)
    } finally {
      setThreadsLoading(false)
    }
  }, [loadMessages, recordConnectionFailure, rememberSelectedThread])

  useEffect(() => {
    let cancelled = false

    const restore = async (): Promise<void> => {
      const savedProfile = await storage.load()
      if (cancelled) return
      if (!savedProfile) {
        setBootState("disconnected")
        return
      }

      const api = apiFactory(savedProfile)
      apiRef.current = api
      setProfile(savedProfile)
      setSelectedThreadId(savedProfile.selectedThreadId)
      setConnectionState("checking")
      setBootState("connected")

      try {
        await api.verifyConnection()
        if (cancelled) return
        const verifiedProfile = { ...savedProfile, lastVerifiedAt: now() }
        await storage.save(verifiedProfile)
        if (cancelled) return
        setProfile(verifiedProfile)
        setConnectionState("ready")
        await hydrateChat(api, verifiedProfile.selectedThreadId)
      } catch (error) {
        if (!cancelled) recordConnectionFailure(error)
      }
    }

    void restore().catch((error) => {
      if (!cancelled) {
        setBootState("disconnected")
        setConnectionAttempt({
          label: "Local profile unavailable",
          detail: displayError(error),
          tone: "danger",
        })
      }
    })

    return () => {
      cancelled = true
      activeTaskStopRef.current?.()
      activeTaskStopRef.current = null
    }
  }, [apiFactory, hydrateChat, now, recordConnectionFailure, storage])

  useEffect(() => {
    messageEndRef.current?.scrollIntoView?.({ block: "end" })
  }, [completionState, visibleMessages])

  const handleSaveAndConnect = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault()
    setConnectionAttempt(null)

    let candidate: ConnectionProfile
    let permissionPattern: string
    try {
      const timestamp = now()
      candidate = createConnectionProfile({
        backendBaseUrl: backendInput,
        apiKey: apiKeyInput,
        connectedAt: timestamp,
        lastVerifiedAt: timestamp,
      })
      permissionPattern = buildOriginPermissionPattern(candidate.backendBaseUrl)
    } catch (error) {
      setConnectionAttempt({
        label: "Connection details rejected",
        detail: error instanceof Error ? error.message : "Check the connection details.",
        tone: "danger",
      })
      return
    }

    setConnectionAttempt({
      label: "Permission requested",
      detail: "Chrome is requesting access only to the configured backend origin.",
      tone: "attention",
    })

    setOperationBusy(true)
    let granted: boolean
    try {
      granted = await permissionClient.request(permissionPattern)
    } catch {
      setConnectionAttempt({
        label: "Host access request failed",
        detail: "Chrome could not request access to this backend origin.",
        tone: "danger",
      })
      setOperationBusy(false)
      return
    }
    if (!granted) {
      setConnectionAttempt({
        label: "Host access not granted",
        detail: "Codexify cannot connect without access to that backend origin.",
        tone: "danger",
      })
      setOperationBusy(false)
      return
    }

    setConnectionAttempt(CONNECTION_PRESENTATION.checking)
    const api = apiFactory(candidate)
    try {
      await api.verifyConnection()
      const verifiedProfile = { ...candidate, lastVerifiedAt: now() }
      await storage.save(verifiedProfile)
      apiRef.current = api
      setProfile(verifiedProfile)
      setConnectionState("ready")
      setBootState("connected")
      setBackendInput("")
      setApiKeyInput("")
      setSurfaceError(null)
      await hydrateChat(api, verifiedProfile.selectedThreadId)
    } catch (error) {
      await permissionClient.remove(permissionPattern).catch(() => false)
      const state = connectionStateForError(error)
      setConnectionAttempt(state
        ? CONNECTION_PRESENTATION[state]
        : {
            label: "Chat verification failed",
            detail: displayError(error),
            tone: "danger",
          })
    } finally {
      setOperationBusy(false)
    }
  }

  const handleRetryConnection = async (): Promise<void> => {
    if (!profile) return
    const pattern = buildOriginPermissionPattern(profile.backendBaseUrl)
    setConnectionState("checking")
    setSurfaceError(null)

    let granted: boolean
    try {
      granted = await permissionClient.request(pattern)
    } catch {
      setConnectionState("unreachable")
      setSurfaceError("Chrome could not request access to this backend origin.")
      return
    }
    if (!granted) {
      setConnectionState("unreachable")
      setSurfaceError("Chrome host access was not granted for this backend.")
      return
    }

    const api = apiFactory(profile)
    apiRef.current = api
    try {
      await api.verifyConnection()
      const verifiedProfile = { ...profile, lastVerifiedAt: now() }
      await storage.save(verifiedProfile)
      setProfile(verifiedProfile)
      setConnectionState("ready")
      await hydrateChat(api, verifiedProfile.selectedThreadId)
    } catch (error) {
      recordConnectionFailure(error)
    }
  }

  const handleDisconnect = async (): Promise<void> => {
    if (!profile) return
    setOperationBusy(true)
    const permissionPattern = buildOriginPermissionPattern(profile.backendBaseUrl)
    try {
      activeTaskStopRef.current?.()
      activeTaskStopRef.current = null
      await storage.clear()
      await permissionClient.remove(permissionPattern).catch(() => false)
      apiRef.current = null
      setProfile(null)
      setThreads([])
      setSelectedThreadId(null)
      setMessages([])
      setComposerValue("")
      setCompletionState("idle")
      setCompletionReceipt(null)
      setThreadDrawerOpen(false)
      setSurfaceError(null)
      setConnectionAttempt(null)
      setBootState("disconnected")
    } catch (error) {
      setSurfaceError(error instanceof Error ? error.message : "The saved profile could not be cleared.")
    } finally {
      setOperationBusy(false)
    }
  }

  const selectThread = async (threadId: number): Promise<void> => {
    const api = apiRef.current
    if (!api || threadId === selectedThreadId) {
      setThreadDrawerOpen(false)
      return
    }
    activeTaskStopRef.current?.()
    activeTaskStopRef.current = null
    setCompletionState("idle")
    setCompletionReceipt(null)
    setSelectedThreadId(threadId)
    setMessages([])
    setSurfaceError(null)
    setThreadDrawerOpen(false)
    await rememberSelectedThread(threadId)
    await loadMessages(api, threadId)
  }

  const createNewThread = async (title = "New Chat"): Promise<CodexifyThread | null> => {
    const api = apiRef.current
    if (!api) return null
    setOperationBusy(true)
    setSurfaceError(null)
    try {
      const thread = await api.createThread(title)
      setThreads((current) => [thread, ...current.filter((item) => item.id !== thread.id)])
      setSelectedThreadId(thread.id)
      setMessages([])
      setMessageLoadState("ready")
      setCompletionState("idle")
      setCompletionReceipt(null)
      setThreadDrawerOpen(false)
      await rememberSelectedThread(thread.id)
      return thread
    } catch (error) {
      recordConnectionFailure(error)
      return null
    } finally {
      setOperationBusy(false)
    }
  }

  const handleTerminalTask = async (
    api: CodexifyExtensionApi,
    receipt: CompletionReceipt,
    outcome: "completed" | "failed" | "cancelled",
  ): Promise<void> => {
    activeTaskStopRef.current = null
    if (outcome === "completed") {
      const refreshed = await loadMessages(api, receipt.threadId, receipt.messagesUrl)
      setCompletionState(refreshed ? CHAT_REQUEST_STATES.COMPLETED : "connection_lost")
      return
    }

    await loadMessages(api, receipt.threadId)
    setCompletionState(
      outcome === "cancelled"
        ? CHAT_REQUEST_STATES.CANCELLED
        : CHAT_REQUEST_STATES.FAILED_RETRYABLE,
    )
  }

  const handleSend = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault()
    const content = composerValue.trim()
    const api = apiRef.current
    if (!content || !api || connectionState !== "ready" || completionPending) return

    setSurfaceError(null)
    setCompletionReceipt(null)
    setCompletionState(CHAT_REQUEST_STATES.DISPATCHING)

    let threadId = selectedThreadId
    if (threadId === null) {
      const created = await createNewThread(threadTitleFromMessage(content))
      if (!created) {
        setCompletionState(CHAT_REQUEST_STATES.FAILED_RETRYABLE)
        return
      }
      threadId = created.id
      setCompletionState(CHAT_REQUEST_STATES.DISPATCHING)
    }

    let receipt: CompletionReceipt
    try {
      await api.persistUserMessage(threadId, content)
      setComposerValue("")
      await loadMessages(api, threadId)
      receipt = await api.requestCompletion(threadId)
      setCompletionReceipt(receipt)
      setCompletionState(CHAT_REQUEST_STATES.AWAITING_ACK)
    } catch (error) {
      recordConnectionFailure(error)
      setCompletionState(CHAT_REQUEST_STATES.FAILED_RETRYABLE)
      return
    }

    try {
      activeTaskStopRef.current?.()
      activeTaskStopRef.current = api.subscribeToTask(receipt.taskId, {
        onOpen: () => {
          setCompletionState((current) =>
            current === "connection_lost" ? CHAT_REQUEST_STATES.AWAITING_MODEL : current,
          )
        },
        onEvent: (taskEvent) => {
          if (isWorkerProgressEvent(taskEvent)) {
            setCompletionState(CHAT_REQUEST_STATES.AWAITING_MODEL)
          }
        },
        onConnectionLost: () => setCompletionState("connection_lost"),
        onUnauthorized: () => {
          setConnectionState("authentication_rejected")
          setCompletionState("connection_lost")
        },
        onTerminal: (outcome) => {
          void handleTerminalTask(api, receipt, outcome)
        },
      })
    } catch (error) {
      setSurfaceError(`${displayError(error)} The accepted completion was not replayed.`)
      setCompletionState("connection_lost")
    }
  }

  if (bootState === "loading") {
    return (
      <main className="connection-screen" aria-busy="true">
        <div className="brand-mark" aria-hidden="true">C</div>
        <p className="eyebrow">Codexify</p>
        <h1>Opening private chat</h1>
        <p className="muted-copy">Restoring the extension-local connection profile.</p>
      </main>
    )
  }

  if (bootState === "disconnected") {
    return (
      <main className="connection-screen">
        <div className="brand-mark" aria-hidden="true">C</div>
        <p className="eyebrow">Codexify Side Panel</p>
        <h1>Connect your private runtime</h1>
        <p className="muted-copy">
          This client requests access only to the Codexify origin you enter.
        </p>

        <form className="connection-form" onSubmit={handleSaveAndConnect}>
          <label htmlFor="backend-url">Backend URL</label>
          <input
            id="backend-url"
            name="backend-url"
            type="url"
            inputMode="url"
            placeholder="Enter backend origin"
            value={backendInput}
            onChange={(event) => setBackendInput(event.target.value)}
            autoComplete="url"
            required
          />

          <label htmlFor="api-key">Authentication API key</label>
          <input
            id="api-key"
            name="api-key"
            type="password"
            value={apiKeyInput}
            onChange={(event) => setApiKeyInput(event.target.value)}
            autoComplete="off"
            required
          />

          <p className="credential-notice">
            Private local credential: the key is stored only in this extension&apos;s
            <code> chrome.storage.local</code>, never Chrome Sync.
          </p>

          {connectionAttempt ? (
            <div
              className={`status-card status-card--${connectionAttempt.tone}`}
              role="status"
              data-testid="connection-attempt"
            >
              <strong>{connectionAttempt.label}</strong>
              <span>{connectionAttempt.detail}</span>
            </div>
          ) : null}

          <button className="primary-button" type="submit" disabled={operationBusy}>
            {operationBusy ? "Connecting…" : "Save and connect"}
          </button>
        </form>
      </main>
    )
  }

  return (
    <div
      className="side-panel-shell"
      onKeyDown={(event) => {
        if (event.key === "Escape") setThreadDrawerOpen(false)
      }}
    >
      <header className="panel-header">
        <div className="header-brand">
          <span className="brand-mark brand-mark--compact" aria-hidden="true">C</span>
          <div>
            <strong>Codexify</strong>
            <span className={`connection-pill connection-pill--${connectionPresentation.tone}`}>
              {connectionPresentation.label}
            </span>
          </div>
        </div>
        <div className="header-actions">
          <button
            className="quiet-button thread-switcher"
            type="button"
            aria-expanded={threadDrawerOpen}
            aria-controls="thread-drawer"
            onClick={() => setThreadDrawerOpen((open) => !open)}
            disabled={completionPending}
          >
            <span>{selectedThread?.title ?? "Threads"}</span>
            <span aria-hidden="true">⌄</span>
          </button>
          <button
            className="quiet-button quiet-button--emphasis"
            type="button"
            onClick={() => void createNewThread()}
            disabled={operationBusy || completionPending || connectionState !== "ready"}
          >
            New Chat
          </button>
        </div>
      </header>

      {threadDrawerOpen ? (
        <>
          <button
            className="drawer-scrim"
            type="button"
            aria-label="Close thread list"
            onClick={() => setThreadDrawerOpen(false)}
          />
          <aside id="thread-drawer" className="thread-drawer" aria-label="Chat threads">
            <div className="drawer-heading">
              <div>
                <p className="eyebrow">Persisted chats</p>
                <h2>Threads</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                aria-label="Close thread list"
                onClick={() => setThreadDrawerOpen(false)}
              >
                ×
              </button>
            </div>

            <div className="thread-list">
              {threadsLoading ? <p className="list-state">Loading threads…</p> : null}
              {!threadsLoading && threads.length === 0 ? (
                <p className="list-state">No persisted threads yet.</p>
              ) : null}
              {threads.map((thread) => (
                <button
                  key={thread.id}
                  className={`thread-row${thread.id === selectedThreadId ? " thread-row--active" : ""}`}
                  type="button"
                  onClick={() => void selectThread(thread.id)}
                >
                  <span>{thread.title}</span>
                  {thread.id === selectedThreadId ? <span aria-hidden="true">•</span> : null}
                </button>
              ))}
            </div>

            <div className="drawer-footer">
              <span>{profile ? new URL(profile.backendBaseUrl).host : ""}</span>
              <button
                className="danger-button"
                type="button"
                onClick={() => void handleDisconnect()}
                disabled={operationBusy}
              >
                Disconnect
              </button>
            </div>
          </aside>
        </>
      ) : null}

      <main className="message-lane">
        {connectionState !== "ready" ? (
          <div className={`connection-banner status-card--${connectionPresentation.tone}`} role="status">
            <div>
              <strong>{connectionPresentation.label}</strong>
              <span>{connectionPresentation.detail}</span>
            </div>
            <button className="quiet-button" type="button" onClick={() => void handleRetryConnection()}>
              Retry
            </button>
          </div>
        ) : null}

        {surfaceError ? (
          <div className="surface-error" role="alert">
            <span>{surfaceError}</span>
            {selectedThreadId !== null ? (
              <button
                className="text-button"
                type="button"
                onClick={() => {
                  const api = apiRef.current
                  if (api) void loadMessages(api, selectedThreadId)
                }}
              >
                Refresh
              </button>
            ) : null}
          </div>
        ) : null}

        <section className="messages" aria-label="Chat messages" aria-busy={messageLoadState === "loading"}>
          {messageLoadState === "loading" ? (
            <div className="empty-state"><p>Loading persisted messages…</p></div>
          ) : null}
          {messageLoadState === "failed" ? (
            <div className="empty-state"><p>Persisted messages could not be loaded.</p></div>
          ) : null}
          {messageLoadState !== "loading" && messageLoadState !== "failed" && visibleMessages.length === 0 ? (
            <div className="empty-state">
              <div className="brand-mark" aria-hidden="true">C</div>
              <h1>{selectedThreadId === null ? "Start a private chat" : "This thread is empty"}</h1>
              <p>Your user message and the final assistant reply will be read from Codexify.</p>
            </div>
          ) : null}
          {visibleMessages.map((message) => (
            <article
              key={message.id}
              className={`message message--${message.role}`}
              data-message-id={message.id}
            >
              <span className="message-role">{message.role === "assistant" ? "Codexify" : "You"}</span>
              <p>{message.content}</p>
            </article>
          ))}
          <div ref={messageEndRef} />
        </section>
      </main>

      <footer className="composer-dock">
        {completionState !== "idle" ? (
          <div
            className={`task-indicator task-indicator--${completionPresentation.tone}`}
            role="status"
            aria-live="polite"
            data-testid="task-state"
            data-task-state={completionState}
          >
            <span className="task-dot" aria-hidden="true" />
            <div>
              <strong>{completionPresentation.label}</strong>
              <span>{completionPresentation.detail}</span>
            </div>
            {completionReceipt ? (
              <span className="task-id" title="Completion task identity">
                {completionReceipt.taskId.slice(0, 8)}
              </span>
            ) : null}
          </div>
        ) : null}

        <form className="composer" onSubmit={handleSend}>
          <label className="sr-only" htmlFor="composer-input">Message Codexify</label>
          <textarea
            id="composer-input"
            value={composerValue}
            onChange={(event) => setComposerValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                event.currentTarget.form?.requestSubmit()
              }
            }}
            placeholder="Message Codexify"
            rows={1}
            disabled={connectionState !== "ready"}
          />
          <button
            className="send-button"
            type="submit"
            aria-label="Send message"
            disabled={!composerValue.trim() || completionPending || connectionState !== "ready"}
          >
            ↑
          </button>
        </form>
      </footer>
    </div>
  )
}
