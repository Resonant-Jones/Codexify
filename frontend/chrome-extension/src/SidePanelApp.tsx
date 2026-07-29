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
  createRemoteConnectionProfile,
  isRemoteSessionUsable,
  normalizeBackendBaseUrl,
  type ConnectionAuthMode,
  type ConnectionProfile,
  type OriginPermissionClient,
  type RemoteSessionCredential,
} from "./connectionProfile"
import {
  chromeConnectionStorage,
  type ConnectionStorage,
} from "./chromeStorage"
import {
  classifyCodexifyError,
  createCodexifyExtensionApi,
  loginRemoteSession,
  type CodexifyExtensionApi,
  type CodexifyMessage,
  type CodexifyThread,
  type CompletionReceipt,
  type RemoteLoginCredentials,
  type TaskLifecycleEvent,
} from "./codexifyExtensionApi"
import { MarkdownMessage } from "./MarkdownMessage"
import {
  DEFAULT_USER_ACCENT_TOKEN,
  USER_ACCENT_CSS_VARS,
  USER_ACCENT_LABELS,
  USER_ACCENT_TOKENS,
  type UserAccentToken,
} from "../../src/contracts/userAccentTokens"

type BootState = "loading" | "disconnected" | "connected"
type ConnectionState =
  | "checking"
  | "ready"
  | "unreachable"
  | "authentication_rejected"
type CompletionViewState =
  | ChatRequestState
  | "idle"
  | "connection_lost"
  | "cancellation_requested"
type MessageLoadState = "idle" | "loading" | "ready" | "failed"
type ProfileSyncState = "idle" | "loading" | "ready" | "failed"

export interface SidePanelAppProps {
  storage?: ConnectionStorage
  permissionClient?: OriginPermissionClient
  apiFactory?: (
    profile: ConnectionProfile,
    remoteSession?: RemoteSessionCredential | null,
  ) => CodexifyExtensionApi
  remoteLogin?: (
    backendBaseUrl: string,
    credentials: RemoteLoginCredentials,
  ) => Promise<RemoteSessionCredential>
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
  cancellation_requested: {
    label: "Cancellation requested",
    detail: "Waiting for terminal cancellation evidence from the worker.",
    tone: "attention",
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
  if (kind === "authentication_rejected") return "The backend rejected the saved credential."
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
  remoteLogin = loginRemoteSession,
  now = currentIsoTimestamp,
}: SidePanelAppProps): React.JSX.Element {
  const [bootState, setBootState] = useState<BootState>("loading")
  const [profile, setProfile] = useState<ConnectionProfile | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>("checking")
  const [connectionAttempt, setConnectionAttempt] = useState<StatusPresentation | null>(null)
  const [backendInput, setBackendInput] = useState("")
  const [authModeInput, setAuthModeInput] = useState<ConnectionAuthMode>("local")
  const [apiKeyInput, setApiKeyInput] = useState("")
  const [usernameInput, setUsernameInput] = useState("")
  const [passwordInput, setPasswordInput] = useState("")
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
  const [accentToken, setAccentToken] = useState<UserAccentToken>(DEFAULT_USER_ACCENT_TOKEN)
  const [accentPickerOpen, setAccentPickerOpen] = useState(false)
  const [accentSaveError, setAccentSaveError] = useState<string | null>(null)
  const [profileSyncState, setProfileSyncState] = useState<ProfileSyncState>("idle")

  const apiRef = useRef<CodexifyExtensionApi | null>(null)
  const activeTaskStopRef = useRef<(() => void) | null>(null)
  const messageEndRef = useRef<HTMLDivElement | null>(null)
  const accentPickerRef = useRef<HTMLDivElement | null>(null)
  const lastConfirmedAccentRef = useRef<UserAccentToken>(DEFAULT_USER_ACCENT_TOKEN)

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
    "cancellation_requested",
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
      setProfile(savedProfile)

      let remoteSession: RemoteSessionCredential | null = null
      if (savedProfile.authMode === "remote") {
        remoteSession = await storage.loadRemoteSession()
        const nowEpochSeconds = Math.floor(Date.parse(now()) / 1000)
        if (!isRemoteSessionUsable(remoteSession, savedProfile, nowEpochSeconds)) {
          await storage.clearRemoteSession()
          if (cancelled) return
          setBackendInput(savedProfile.backendBaseUrl)
          setAuthModeInput("remote")
          setConnectionAttempt({
            label: "Remote sign-in required",
            detail: "The previous browser session ended or expired. Sign in again to reconnect.",
            tone: "attention",
          })
          setBootState("disconnected")
          return
        }
      }

      const api = apiFactory(savedProfile, remoteSession)
      apiRef.current = api
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
        // Hydrate the accent preference from the backend profile independently
        // of thread/message loading — a failed profile read must not break chat.
        setProfileSyncState("loading")
        api.getUserProfile().then((token) => {
          if (!cancelled) {
            setAccentToken(token)
            lastConfirmedAccentRef.current = token
            setProfileSyncState("ready")
          }
        }).catch(() => {
          if (!cancelled) setProfileSyncState("failed")
        })
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

  useEffect(() => {
    const vars = USER_ACCENT_CSS_VARS[accentToken]
    const root = document.documentElement
    // Clear previous user-accent custom properties.
    for (const key of [
      "--user-accent-border",
      "--user-accent-surface",
      "--user-accent-label",
      "--user-accent-focus",
    ]) {
      root.style.removeProperty(key)
    }
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value)
    }
  }, [accentToken])

  const handleSaveAndConnect = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault()
    setConnectionAttempt(null)

    const timestamp = now()
    let normalizedBaseUrl: string
    let permissionPattern: string
    try {
      normalizedBaseUrl = normalizeBackendBaseUrl(backendInput)
      if (authModeInput === "local") {
        createConnectionProfile({
          backendBaseUrl: normalizedBaseUrl,
          apiKey: apiKeyInput,
          connectedAt: timestamp,
          lastVerifiedAt: timestamp,
        })
      } else if (!usernameInput.trim() || !passwordInput) {
        throw new Error("Enter the Codexify username and password.")
      }
      permissionPattern = buildOriginPermissionPattern(normalizedBaseUrl)
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
    try {
      const previousProfile = profile?.backendBaseUrl === normalizedBaseUrl &&
        profile.authMode === authModeInput
        ? profile
        : null
      let remoteSession: RemoteSessionCredential | null = null
      let candidate: ConnectionProfile
      if (authModeInput === "local") {
        candidate = createConnectionProfile({
          backendBaseUrl: normalizedBaseUrl,
          apiKey: apiKeyInput,
          selectedThreadId: previousProfile?.selectedThreadId,
          connectedAt: previousProfile?.connectedAt ?? timestamp,
          lastVerifiedAt: timestamp,
        })
      } else {
        remoteSession = await remoteLogin(normalizedBaseUrl, {
          username: usernameInput.trim(),
          password: passwordInput,
        })
        candidate = createRemoteConnectionProfile({
          backendBaseUrl: normalizedBaseUrl,
          sessionUserId: remoteSession.userId,
          sessionExpiresAt: remoteSession.expiresAt,
          selectedThreadId: previousProfile?.selectedThreadId,
          connectedAt: previousProfile?.connectedAt ?? timestamp,
          lastVerifiedAt: timestamp,
        })
      }

      const api = apiFactory(candidate, remoteSession)
      await api.verifyConnection()
      const verifiedProfile = { ...candidate, lastVerifiedAt: now() }
      await storage.save(verifiedProfile)
      if (verifiedProfile.authMode === "remote" && remoteSession) {
        await storage.saveRemoteSession(remoteSession)
      } else {
        await storage.clearRemoteSession()
      }
      apiRef.current = api
      setProfile(verifiedProfile)
      setConnectionState("ready")
      setBootState("connected")
      setBackendInput("")
      setApiKeyInput("")
      setUsernameInput("")
      setPasswordInput("")
      setSurfaceError(null)
      // Hydrate the accent preference after initial connection.
      setProfileSyncState("loading")
      api.getUserProfile().then((token) => {
        setAccentToken(token)
        lastConfirmedAccentRef.current = token
        setProfileSyncState("ready")
      }).catch(() => setProfileSyncState("failed"))
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
      if (authModeInput === "remote") setPasswordInput("")
      setOperationBusy(false)
    }
  }

  const prepareRemoteSignIn = async (): Promise<void> => {
    if (!profile || profile.authMode !== "remote") return
    activeTaskStopRef.current?.()
    activeTaskStopRef.current = null
    await storage.clearRemoteSession()
    apiRef.current = null
    setBackendInput(profile.backendBaseUrl)
    setAuthModeInput("remote")
    setApiKeyInput("")
    setUsernameInput("")
    setPasswordInput("")
    setConnectionAttempt({
      label: "Remote sign-in required",
      detail: "Enter your Codexify account credentials to create a new browser session.",
      tone: "attention",
    })
    setBootState("disconnected")
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

    let remoteSession: RemoteSessionCredential | null = null
    if (profile.authMode === "remote") {
      remoteSession = await storage.loadRemoteSession()
      const nowEpochSeconds = Math.floor(Date.parse(now()) / 1000)
      if (!isRemoteSessionUsable(remoteSession, profile, nowEpochSeconds)) {
        await prepareRemoteSignIn()
        return
      }
    }

    const api = apiFactory(profile, remoteSession)
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
      await apiRef.current?.logout().catch(() => undefined)
      await storage.clear()
      await permissionClient.remove(permissionPattern).catch(() => false)
      apiRef.current = null
      setProfile(null)
      setThreads([])
      setSelectedThreadId(null)
      setMessages([])
      setComposerValue("")
      setBackendInput("")
      setAuthModeInput("local")
      setApiKeyInput("")
      setUsernameInput("")
      setPasswordInput("")
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

  const handleCancel = async (): Promise<void> => {
    const api = apiRef.current
    const receipt = completionReceipt
    if (!api || !receipt || !completionPending) return

    setSurfaceError(null)
    setCompletionState("cancellation_requested")
    try {
      await api.cancelTask(receipt.taskId)
    } catch (error) {
      recordConnectionFailure(error)
      setSurfaceError(`${displayError(error)} Task observation remains active.`)
      setCompletionState("connection_lost")
    }
  }

  // Close the accent picker when clicking outside or pressing Escape.
  useEffect(() => {
    if (!accentPickerOpen) return
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccentPickerOpen(false)
    }
    const handleClick = (event: MouseEvent) => {
      if (accentPickerRef.current && !accentPickerRef.current.contains(event.target as Node)) {
        setAccentPickerOpen(false)
      }
    }
    document.addEventListener("keydown", handleKey)
    document.addEventListener("mousedown", handleClick)
    return () => {
      document.removeEventListener("keydown", handleKey)
      document.removeEventListener("mousedown", handleClick)
    }
  }, [accentPickerOpen])

  const handleAccentPick = useCallback(async (token: UserAccentToken): Promise<void> => {
    const api = apiRef.current
    if (!api || token === accentToken) {
      setAccentPickerOpen(false)
      return
    }
    const previousToken = accentToken
    setAccentToken(token)
    setAccentPickerOpen(false)
    setAccentSaveError(null)
    try {
      await api.updateAccentColor(token)
      lastConfirmedAccentRef.current = token
    } catch {
      setAccentToken(previousToken)
      setAccentSaveError("Accent not saved — the backend could not be reached.")
    }
  }, [accentToken])

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
      activeTaskStopRef.current = api.subscribeToTask(receipt, {
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
          if (profile?.authMode === "remote") {
            void storage.clearRemoteSession()
          }
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

          <fieldset className="auth-mode-picker">
            <legend>Authentication method</legend>
            <div>
              <button
                className={authModeInput === "local" ? "auth-mode-button auth-mode-button--active" : "auth-mode-button"}
                type="button"
                aria-pressed={authModeInput === "local"}
                onClick={() => {
                  setAuthModeInput("local")
                  setUsernameInput("")
                  setPasswordInput("")
                }}
              >
                Local API key
              </button>
              <button
                className={authModeInput === "remote" ? "auth-mode-button auth-mode-button--active" : "auth-mode-button"}
                type="button"
                aria-pressed={authModeInput === "remote"}
                onClick={() => {
                  setAuthModeInput("remote")
                  setApiKeyInput("")
                }}
              >
                Remote session
              </button>
            </div>
          </fieldset>

          {authModeInput === "local" ? (
            <>
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
            </>
          ) : (
            <>
              <label htmlFor="remote-username">Codexify username</label>
              <input
                id="remote-username"
                name="remote-username"
                type="text"
                value={usernameInput}
                onChange={(event) => setUsernameInput(event.target.value)}
                autoComplete="username"
                required
              />

              <label htmlFor="remote-password">Codexify password</label>
              <input
                id="remote-password"
                name="remote-password"
                type="password"
                value={passwordInput}
                onChange={(event) => setPasswordInput(event.target.value)}
                autoComplete="current-password"
                required
              />
            </>
          )}

          <p className="credential-notice">
            {authModeInput === "local" ? (
              <>
                Private local credential: the key is stored only in this extension&apos;s
                <code> chrome.storage.local</code>, never Chrome Sync.
              </>
            ) : (
              <>
                Your password is never stored. The revocable session token stays only in
                <code> chrome.storage.session</code> and clears when Chrome restarts or the extension reloads.
              </>
            )}
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
            {operationBusy
              ? "Connecting…"
              : authModeInput === "remote"
                ? "Sign in and connect"
                : "Save and connect"}
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
          {/* Accent colour selector — compact swatch + popover */}
          <div className="accent-picker-anchor" ref={accentPickerRef}>
            <button
              className="accent-swatch"
              type="button"
              aria-label={`Accent colour: ${USER_ACCENT_LABELS[accentToken]}. Click to change.`}
              title={`User accent: ${USER_ACCENT_LABELS[accentToken]}`}
              onClick={() => setAccentPickerOpen((open) => !open)}
              aria-expanded={accentPickerOpen}
            >
              <span className="accent-swatch-dot" data-accent={accentToken} />
            </button>
            {accentPickerOpen ? (
              <div className="accent-palette-popover" role="listbox" aria-label="Accent colour">
                {USER_ACCENT_TOKENS.map((token) => (
                  <button
                    key={token}
                    className={`accent-palette-chip${token === accentToken ? " accent-palette-chip--selected" : ""}`}
                    type="button"
                    role="option"
                    aria-selected={token === accentToken}
                    aria-label={USER_ACCENT_LABELS[token]}
                    onClick={() => void handleAccentPick(token)}
                  >
                    <span className="accent-chip-swatch" data-accent={token} />
                    <span>{USER_ACCENT_LABELS[token]}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
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
            <button
              className="quiet-button"
              type="button"
              onClick={() => void (
                connectionState === "authentication_rejected" && profile?.authMode === "remote"
                  ? prepareRemoteSignIn()
                  : handleRetryConnection()
              )}
            >
              {connectionState === "authentication_rejected" && profile?.authMode === "remote"
                ? "Sign in again"
                : "Retry"}
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

        {accentSaveError ? (
          <div className="surface-error" role="alert">
            <span>{accentSaveError}</span>
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
              className={`message message--${message.role}${message.role === "user" && accentToken !== "default" ? " message--accented" : ""}`}
              data-message-id={message.id}
            >
              <span className="message-role">{message.role === "assistant" ? "Codexify" : "You"}</span>
              {message.role === "assistant" ? (
                <MarkdownMessage content={message.content} className="codexify-markdown" />
              ) : (
                <p>{message.content}</p>
              )}
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
            {completionPending && completionReceipt ? (
              <button
                className="task-cancel-button"
                type="button"
                onClick={() => void handleCancel()}
                disabled={operationBusy || completionState === "cancellation_requested"}
              >
                Cancel
              </button>
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
