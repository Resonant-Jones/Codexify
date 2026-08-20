import { GuardianEventSource } from "../../src/lib/guardianEventSource"
import {
  createRemoteSessionCredential,
  type ConnectionProfile,
  type RemoteSessionCredential,
} from "./connectionProfile"
import { normalizeUserAccentToken, type UserAccentToken } from "../../src/contracts/userAccentTokens"

export type CodexifyApiErrorKind =
  | "unreachable"
  | "authentication_rejected"
  | "request_failed"
  | "invalid_response"

export class CodexifyApiError extends Error {
  readonly kind: CodexifyApiErrorKind
  readonly status: number | null

  constructor(kind: CodexifyApiErrorKind, message: string, status: number | null = null) {
    super(message)
    this.name = "CodexifyApiError"
    this.kind = kind
    this.status = status
  }
}

export interface CodexifyThread {
  id: number
  title: string
  createdAt: string | null
  updatedAt: string | null
}

export interface CodexifyMessage {
  id: string
  threadId: number
  role: "user" | "assistant" | "system"
  content: string
  createdAt: string | null
  turnId: string | null
}

export interface CodexifyAgentRun {
  run_id: string | null
  runtime_target: string | null
  status: string | null
  thread_id: number | null
  worktree_id: string | null
  worktree_path: string | null
}

export interface CodexifyBrowserApproval {
  id: number | null
  operation: string | null
  request_reason: string | null
  status: string | null
  target: string | null
}

export interface CodexifyApprovalDecision {
  approvalId: number
  operation: string | null
  status: string
  target: string | null
}

export interface CompletionReceipt {
  taskId: string
  requestId: string
  turnId: string
  threadId: number
  acceptanceStatus: string
  acceptanceWarnings: string[]
  messagesUrl: string | null
  traceUrl: string | null
}

/**
 * Explicitly captured browser selection evidence attached to exactly one
 * completion attempt. The backend treats it as untrusted, turn-scoped context
 * that is never persisted, embedded, or written into memory/identity stores.
 */
export interface BrowserSelectionContext {
  content: string
  sourceUrl?: string | null
  sourceTitle?: string | null
  capturedAt?: string
  [key: string]: unknown
}

export interface TaskLifecycleEvent {
  type: string
  state: string | null
  data: Record<string, unknown>
}

export type TaskTerminalOutcome = "completed" | "failed" | "cancelled"

export interface TaskLifecycleCallbacks {
  onOpen?(): void
  onEvent?(event: TaskLifecycleEvent): void
  onTerminal?(outcome: TaskTerminalOutcome, event: TaskLifecycleEvent): void
  onConnectionLost?(): void
  onUnauthorized?(): void
}

export interface CodexifyExtensionApi {
  verifyConnection(): Promise<void>
  logout(): Promise<void>
  getUserProfile(): Promise<UserAccentToken>
  updateAccentColor(token: UserAccentToken): Promise<void>
  listThreads(): Promise<CodexifyThread[]>
  createThread(title?: string): Promise<CodexifyThread>
  listMessages(threadId: number, discoveryUrl?: string | null): Promise<CodexifyMessage[]>
  listAgentRuns(threadId: number): Promise<CodexifyAgentRun[]>
  listPendingApprovals(): Promise<CodexifyBrowserApproval[]>
  approveBrowserApproval(approvalId: number, reason: string): Promise<CodexifyApprovalDecision>
  denyBrowserApproval(approvalId: number, reason: string): Promise<CodexifyApprovalDecision>
  persistUserMessage(threadId: number, content: string): Promise<void>
  requestCompletion(
    threadId: number,
    browserContext?: BrowserSelectionContext | null,
  ): Promise<CompletionReceipt>
  cancelTask(taskId: string): Promise<void>
  subscribeToTask(receipt: CompletionReceipt, callbacks: TaskLifecycleCallbacks): () => void
}

export interface RemoteLoginCredentials {
  username: string
  password: string
}

type JsonRecord = Record<string, unknown>

const TASK_EVENT_TYPES = [
  "task.created",
  "task.running",
  "task.progress",
  "task.event",
  "task.state",
  "task.completed",
  "task.failed",
  "task.cancelled",
  "completion.error",
] as const

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === "object" ? (value as JsonRecord) : {}
}

function firstString(record: JsonRecord, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === "string" && value.trim()) return value.trim()
  }
  return null
}

function parseThreadId(value: unknown): number | null {
  const parsed = typeof value === "number" ? value : Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function normalizeThread(value: unknown): CodexifyThread | null {
  const record = asRecord(value)
  const id = parseThreadId(record.id ?? record.thread_id)
  if (id === null) return null
  return {
    id,
    title: firstString(record, "title", "name") ?? `Thread ${id}`,
    createdAt: firstString(record, "created_at", "createdAt"),
    updatedAt: firstString(record, "updated_at", "updatedAt"),
  }
}

function normalizeMessage(value: unknown, fallbackThreadId: number): CodexifyMessage | null {
  const record = asRecord(value)
  const roleValue = firstString(record, "role")?.toLowerCase()
  if (roleValue !== "user" && roleValue !== "assistant" && roleValue !== "system") {
    return null
  }
  const content = firstString(record, "content", "text")
  if (content === null) return null

  const idValue = record.id ?? record.message_id
  const id = typeof idValue === "string" || typeof idValue === "number"
    ? String(idValue)
    : `${fallbackThreadId}:${roleValue}:${firstString(record, "created_at") ?? content}`

  return {
    id,
    threadId: parseThreadId(record.thread_id) ?? fallbackThreadId,
    role: roleValue,
    content,
    createdAt: firstString(record, "created_at", "createdAt"),
    turnId: firstString(record, "turn_id", "turnId"),
  }
}

function normalizeAgentRun(value: unknown): CodexifyAgentRun | null {
  const record = asRecord(value)
  const status = firstString(record, "status")
  if (!status) return null
  return {
    run_id: firstString(record, "run_id", "runId"),
    runtime_target: firstString(record, "runtime_target", "runtimeTarget"),
    status,
    thread_id: parseThreadId(record.thread_id ?? record.threadId),
    worktree_id: firstString(record, "worktree_id", "worktreeId"),
    worktree_path: firstString(record, "worktree_path", "worktreePath"),
  }
}

function normalizeBrowserApproval(value: unknown): CodexifyBrowserApproval | null {
  const record = asRecord(value)
  const idValue = typeof record.id === "number" ? record.id : Number(record.id)
  const id = Number.isInteger(idValue) && idValue > 0 ? idValue : null
  if (id === null) return null
  return {
    id,
    operation: firstString(record, "operation"),
    request_reason: firstString(record, "request_reason", "requestReason"),
    status: firstString(record, "status"),
    target: firstString(record, "target"),
  }
}

function sortMessages(messages: CodexifyMessage[]): CodexifyMessage[] {
  return [...messages].sort((left, right) => {
    const dateCompare = (left.createdAt ?? "").localeCompare(right.createdAt ?? "")
    return dateCompare || left.id.localeCompare(right.id)
  })
}

function safeJson(text: string): unknown {
  if (!text.trim()) return {}
  try {
    return JSON.parse(text) as unknown
  } catch {
    return {}
  }
}

function taskState(data: JsonRecord): string | null {
  return firstString(data, "state", "status", "lifecycle_state")?.toLowerCase() ?? null
}

function terminalOutcome(type: string, state: string | null): TaskTerminalOutcome | null {
  if (type === "task.completed" || state === "completed" || state === "success") {
    return "completed"
  }
  if (type === "task.cancelled" || state === "cancelled" || state === "canceled") {
    return "cancelled"
  }
  if (
    type === "task.failed" ||
    type === "completion.error" ||
    state === "failed" ||
    state === "error"
  ) {
    return "failed"
  }
  return null
}

function correlationValue(data: JsonRecord, key: string): string | null {
  const camelKey = key.replace(/_([a-z])/g, (_match, character: string) => character.toUpperCase())
  const direct = firstString(data, key, camelKey)
  if (direct) return direct

  const nested = asRecord(data.request_correlation ?? data.requestCorrelation)
  return firstString(nested, key, camelKey)
}

/**
 * Task streams are addressed by task ID, but lifecycle payloads can be
 * observed through more than one producer. Ignore payloads whose explicit
 * correlation disagrees with the accepted completion receipt. Missing fields
 * remain compatible with older task.created/task.completed payloads.
 */
export function isTaskLifecycleEventCorrelated(
  event: TaskLifecycleEvent,
  receipt: CompletionReceipt,
): boolean {
  const taskId = correlationValue(event.data, "task_id")
  const requestId = correlationValue(event.data, "request_id")
  const turnId = correlationValue(event.data, "turn_id")
  const threadId = parseThreadId(event.data.thread_id ?? event.data.threadId)

  return (
    (!taskId || taskId === receipt.taskId) &&
    (!requestId || requestId === receipt.requestId) &&
    (!turnId || turnId === receipt.turnId) &&
    (threadId === null || threadId === receipt.threadId)
  )
}

async function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 15_000)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    window.clearTimeout(timeout)
  }
}

export async function loginRemoteSession(
  backendBaseUrl: string,
  credentials: RemoteLoginCredentials,
): Promise<RemoteSessionCredential> {
  const username = credentials.username.trim()
  if (!username || !credentials.password) {
    throw new CodexifyApiError(
      "authentication_rejected",
      "Enter the Codexify username and password.",
    )
  }

  let response: Response
  try {
    response = await fetchWithTimeout(`${backendBaseUrl}/api/auth/login`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password: credentials.password }),
      cache: "no-store",
      credentials: "omit",
    })
  } catch {
    throw new CodexifyApiError(
      "unreachable",
      "The Codexify runtime could not be reached at this address.",
    )
  }

  if (response.status === 401 || response.status === 403) {
    throw new CodexifyApiError(
      "authentication_rejected",
      "The runtime rejected the Codexify username or password.",
      response.status,
    )
  }
  if (!response.ok) {
    throw new CodexifyApiError(
      "request_failed",
      `The Codexify login request failed with status ${response.status}.`,
      response.status,
    )
  }

  const body = asRecord(safeJson(await response.text()))
  const token = firstString(body, "token")
  const userId = firstString(body, "user_id", "userId")
  const expiresAt = Number(body.expires_at ?? body.expiresAt)
  try {
    return createRemoteSessionCredential({
      token: token ?? "",
      userId: userId ?? "",
      expiresAt,
    })
  } catch {
    throw new CodexifyApiError(
      "invalid_response",
      "The runtime returned an invalid remote session.",
    )
  }
}

export class FetchCodexifyExtensionApi implements CodexifyExtensionApi {
  private readonly backendBaseUrl: string
  private readonly authHeaders: Record<string, string>

  constructor(
    profile: ConnectionProfile,
    remoteSession: RemoteSessionCredential | null = null,
  ) {
    this.backendBaseUrl = profile.backendBaseUrl
    if (profile.authMode === "local") {
      this.authHeaders = { "X-API-Key": profile.apiKey }
      return
    }
    if (
      !remoteSession ||
      remoteSession.userId !== profile.sessionUserId ||
      remoteSession.expiresAt !== profile.sessionExpiresAt
    ) {
      throw new CodexifyApiError(
        "authentication_rejected",
        "The remote session is missing or no longer matches this connection.",
      )
    }
    this.authHeaders = { Authorization: `Bearer ${remoteSession.token}` }
  }

  async verifyConnection(): Promise<void> {
    await this.fetchReachabilityProbe()
    await this.listThreadsWithLimit(1)
  }

  async logout(): Promise<void> {
    if (!("Authorization" in this.authHeaders)) return
    await this.requestJson("/api/auth/logout", { method: "POST" })
  }

  async listThreads(): Promise<CodexifyThread[]> {
    return this.listThreadsWithLimit(100)
  }

  async createThread(title = "New Chat"): Promise<CodexifyThread> {
    const body = asRecord(await this.requestJson("/api/chat/threads", {
      method: "POST",
      body: JSON.stringify({ title }),
    }))
    const thread = normalizeThread(body.thread ?? body)
    if (!thread) {
      const fallback = normalizeThread({ ...body, title })
      if (fallback) return fallback
      throw new CodexifyApiError("invalid_response", "The backend returned an invalid thread.")
    }
    return thread
  }

  async listMessages(
    threadId: number,
    discoveryUrl: string | null = null,
  ): Promise<CodexifyMessage[]> {
    const path = discoveryUrl ?? `/api/chat/${threadId}/messages?limit=500`
    const body = asRecord(await this.requestJson(path))
    const rawMessages = Array.isArray(body.messages) ? body.messages : []
    return sortMessages(
      rawMessages
        .map((message) => normalizeMessage(message, threadId))
        .filter((message): message is CodexifyMessage => message !== null),
    )
  }

  async listAgentRuns(threadId: number): Promise<CodexifyAgentRun[]> {
    const body = asRecord(
      await this.requestJson(`/api/chat/${threadId}/agent-runs`),
    )
    const rawRuns = Array.isArray(body.runs) ? body.runs : []
    return rawRuns
      .map(normalizeAgentRun)
      .filter((run): run is CodexifyAgentRun => run !== null)
  }

  async listPendingApprovals(): Promise<CodexifyBrowserApproval[]> {
    const body = asRecord(
      await this.requestJson("/api/browser/approvals?status_value=PENDING"),
    )
    const rawApprovals = Array.isArray(body.items) ? body.items : []
    return rawApprovals
      .map(normalizeBrowserApproval)
      .filter((approval): approval is CodexifyBrowserApproval => approval !== null)
  }

  async approveBrowserApproval(
    approvalId: number,
    reason: string,
  ): Promise<CodexifyApprovalDecision> {
    return this.decideBrowserApproval(approvalId, "approve", reason)
  }

  async denyBrowserApproval(
    approvalId: number,
    reason: string,
  ): Promise<CodexifyApprovalDecision> {
    return this.decideBrowserApproval(approvalId, "deny", reason)
  }

  async persistUserMessage(threadId: number, content: string): Promise<void> {
    await this.requestJson(`/api/chat/${threadId}/messages`, {
      method: "POST",
      body: JSON.stringify({ role: "user", content }),
    })
  }

  async requestCompletion(
    threadId: number,
    browserContext: BrowserSelectionContext | null = null,
  ): Promise<CompletionReceipt> {
    const requestId = crypto.randomUUID()
    const turnId = crypto.randomUUID()
    const body = asRecord(await this.requestJson(`/api/chat/${threadId}/complete`, {
      method: "POST",
      headers: { "X-Request-ID": requestId },
      body: JSON.stringify({
        turn_id: turnId,
        ...(browserContext ? { browser_context: browserContext } : {}),
      }),
    }))

    const taskId = firstString(body, "task_id", "taskId")
    if (!taskId) {
      throw new CodexifyApiError(
        "invalid_response",
        "The backend accepted no observable completion task.",
      )
    }

    const warnings = Array.isArray(body.acceptance_warnings)
      ? body.acceptance_warnings.filter((value): value is string => typeof value === "string")
      : []

    return {
      taskId,
      requestId: firstString(body, "request_id", "requestId") ?? requestId,
      turnId: firstString(body, "turn_id", "turnId") ?? turnId,
      threadId: parseThreadId(body.thread_id ?? body.threadId) ?? threadId,
      acceptanceStatus: firstString(body, "acceptance_status", "status") ?? "accepted",
      acceptanceWarnings: warnings,
      messagesUrl: firstString(body, "messages_url", "messagesUrl"),
      traceUrl: firstString(body, "trace_url", "traceUrl"),
    }
  }

  async cancelTask(taskId: string): Promise<void> {
    await this.requestJson(`/api/tasks/${encodeURIComponent(taskId)}/cancel`, {
      method: "POST",
    })
  }

  async getUserProfile(): Promise<UserAccentToken> {
    const body = asRecord(await this.requestJson("/api/user/profile"))
    const profile = asRecord(body.profile ?? body)
    return normalizeUserAccentToken(profile.accent_color ?? profile.accentColor)
  }

  async updateAccentColor(token: UserAccentToken): Promise<void> {
    await this.requestJson("/api/user/profile", {
      method: "PATCH",
      body: JSON.stringify({ accent_color: token }),
    })
  }

  subscribeToTask(receipt: CompletionReceipt, callbacks: TaskLifecycleCallbacks): () => void {
    const source = new GuardianEventSource(
      this.resolveUrl(`/api/tasks/${encodeURIComponent(receipt.taskId)}/events`),
      {
        headers: { ...this.authHeaders },
        withCredentials: false,
        heartbeatTimeout: 45_000,
        retryInterval: 500,
        autoReconnect: true,
        onUnauthorized: () => callbacks.onUnauthorized?.(),
      },
    )
    let terminal = false

    source.onopen = () => callbacks.onOpen?.()
    source.onerror = () => {
      if (!terminal) callbacks.onConnectionLost?.()
    }

    const receive = (event: Event): void => {
      if (terminal) return
      const messageEvent = event as MessageEvent<string>
      const data = asRecord(safeJson(messageEvent.data ?? ""))
      const embeddedType = firstString(data, "event_type", "type")
      const type = event.type === "message" && embeddedType ? embeddedType : event.type
      const lifecycleEvent: TaskLifecycleEvent = {
        type,
        state: taskState(data),
        data,
      }
      if (!isTaskLifecycleEventCorrelated(lifecycleEvent, receipt)) return
      callbacks.onEvent?.(lifecycleEvent)
      const outcome = terminalOutcome(type, lifecycleEvent.state)
      if (!outcome) return

      terminal = true
      source.close()
      callbacks.onTerminal?.(outcome, lifecycleEvent)
    }

    for (const eventType of [...TASK_EVENT_TYPES, "message"]) {
      source.addEventListener(eventType, receive)
    }

    return () => {
      terminal = true
      source.close()
    }
  }

  private async listThreadsWithLimit(limit: number): Promise<CodexifyThread[]> {
    const body = asRecord(await this.requestJson(`/api/chat/threads?limit=${limit}`))
    const rawThreads = Array.isArray(body.threads) ? body.threads : []
    return rawThreads
      .map(normalizeThread)
      .filter((thread): thread is CodexifyThread => thread !== null)
  }

  private async decideBrowserApproval(
    approvalId: number,
    decision: "approve" | "deny",
    reason: string,
  ): Promise<CodexifyApprovalDecision> {
    const body = asRecord(
      await this.requestJson(
        `/api/browser/approvals/${approvalId}/${decision}`,
        {
          method: "POST",
          body: JSON.stringify({ reason }),
        },
      ),
    )
    return {
      approvalId:
        typeof body.id === "number" ? body.id : approvalId,
      operation: firstString(body, "operation"),
      status: firstString(body, "status") ?? "UNKNOWN",
      target: firstString(body, "target"),
    }
  }

  private async fetchReachabilityProbe(): Promise<void> {
    try {
      await this.fetchWithTimeout(this.resolveUrl("/ping"), {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      })
    } catch {
      throw new CodexifyApiError(
        "unreachable",
        "The Codexify runtime could not be reached at this address.",
      )
    }
  }

  private async requestJson(pathOrUrl: string, init: RequestInit = {}): Promise<unknown> {
    const headers = new Headers(init.headers)
    headers.set("Accept", "application/json")
    for (const [name, value] of Object.entries(this.authHeaders)) {
      headers.set(name, value)
    }
    if (init.body !== undefined) headers.set("Content-Type", "application/json")

    let response: Response
    try {
      response = await this.fetchWithTimeout(this.resolveUrl(pathOrUrl), {
        ...init,
        headers,
        cache: "no-store",
      })
    } catch {
      throw new CodexifyApiError(
        "unreachable",
        "The Codexify runtime connection was lost.",
      )
    }

    if (response.status === 401 || response.status === 403) {
      throw new CodexifyApiError(
        "authentication_rejected",
        "The backend rejected the saved credential.",
        response.status,
      )
    }
    if (!response.ok) {
      throw new CodexifyApiError(
        "request_failed",
        `The Codexify request failed with status ${response.status}.`,
        response.status,
      )
    }

    return safeJson(await response.text())
  }

  private resolveUrl(pathOrUrl: string): string {
    if (/^https?:\/\//iu.test(pathOrUrl)) {
      const candidate = new URL(pathOrUrl)
      if (candidate.origin !== new URL(this.backendBaseUrl).origin) {
        throw new CodexifyApiError(
          "invalid_response",
          "The backend returned a discovery URL for an unconfigured origin.",
        )
      }
      return candidate.toString()
    }
    const suffix = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`
    return `${this.backendBaseUrl}${suffix}`
  }

  private async fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
    return fetchWithTimeout(url, init)
  }
}

export function createCodexifyExtensionApi(
  profile: ConnectionProfile,
  remoteSession: RemoteSessionCredential | null = null,
): CodexifyExtensionApi {
  return new FetchCodexifyExtensionApi(profile, remoteSession)
}

export function classifyCodexifyError(error: unknown): CodexifyApiErrorKind {
  return error instanceof CodexifyApiError ? error.kind : "request_failed"
}
