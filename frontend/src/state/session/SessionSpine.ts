import type { SessionStateStore } from "@/state/session/SessionStateStore";
import {
  DEFAULT_INFERENCE_MODE,
  DEFAULT_PROVIDER_ID,
  DEFAULT_MODEL_ID,
  SESSION_DRAFTS_TTL_SECONDS,
  SESSION_SCHEMA_VERSION,
  SESSION_TTL_SECONDS,
  type SessionState,
  type SessionTab,
  type TabId,
} from "@/state/session/types";
import {
  type ComposerInferenceMode,
  isReasoningMode,
} from "@/types/inference";

type SessionListener = (state: SessionState) => void;

export type CompletionLifecycleStatus =
  | "idle"
  | "submitting"
  | "streaming"
  | "canceling"
  | "canceled"
  | "failed"
  | "completed";

export type SessionCompletionSnapshot = {
  completionId: string;
  tabId: TabId;
  threadId: string | null;
  status: CompletionLifecycleStatus;
  taskId: string | null;
  taskIdAliases: string[];
  turnId: string | null;
  turnIdAliases: string[];
  submittedDraft: string;
  errorText: string | null;
  startedAt: string;
  updatedAt: string;
};

type SessionSpineState = SessionState & {
  selectedInferenceMode?: ComposerInferenceMode;
  activeCompletion?: SessionCompletionSnapshot | null;
  completionHistory?: SessionCompletionSnapshot[];
  pendingSubmittedDrafts?: Record<TabId, string>;
};

type HydrateOptions = {
  threadId?: string;
  title?: string;
  providerId?: string | null;
  modelId?: string;
  inferenceMode?: ComposerInferenceMode;
};

type MutationOptions = {
  debounceMs?: number;
};

type SessionSpineConfig = {
  userId: string;
  deviceId: string;
  store: SessionStateStore;
  defaultProviderId?: string | null;
  defaultModelId?: string;
  defaultInferenceMode?: ComposerInferenceMode;
  ttlSeconds?: number;
  draftsTtlSeconds?: number;
  canHydrate?: () => boolean;
  canPersist?: () => boolean;
};

type CompletionSelector = {
  tabId?: TabId | null;
  threadId?: string | null;
  taskId?: string | null;
  turnId?: string | null;
};

type AcceptedLiveEvent = {
  id?: string | null;
  type: string;
  data: unknown;
};

type RuntimeSessionCache = {
  snapshot: SessionSpineState | null;
  processedLiveEventKeys: string[];
};

type ActiveSpineListener = (
  spine: SessionSpine | null,
  snapshot: SessionState | null
) => void;

type CompletionEventIdentity = {
  relevant: boolean;
  threadId: string | null;
  taskId: string | null;
  turnId: string | null;
  role: string | null;
  messageId: string | null;
};

const INFERENCE_MODE_STORAGE_KEY = "cfy.chat.inferenceMode";
const FALLBACK_INFERENCE_MODE: ComposerInferenceMode = "no_think";
const COMPLETION_HISTORY_LIMIT = 12;
const RECENT_COMPLETION_EVENT_LIMIT = 48;
const GUARDED_COMPLETION_EVENT_TYPES = new Set([
  "task.progress",
  "task.completed",
  "task.failed",
  "task.cancelled",
  "completion.error",
]);
const runtimeSessionCacheByKey = new Map<string, RuntimeSessionCache>();

function nowIso(): string {
  return new Date().toISOString();
}

function normalizeToken(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeCompletionStatus(
  value: unknown
): CompletionLifecycleStatus {
  switch (value) {
    case "submitting":
    case "streaming":
    case "canceling":
    case "canceled":
    case "failed":
    case "completed":
    case "idle":
      return value;
    default:
      return "idle";
  }
}

function isComposerBlockedStatus(status: CompletionLifecycleStatus): boolean {
  return status === "submitting" || status === "streaming";
}

function uniqueTokens(values: Array<unknown>): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const value of values) {
    const token = normalizeToken(value);
    if (!token || seen.has(token)) continue;
    seen.add(token);
    normalized.push(token);
  }
  return normalized;
}

function generateTabId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `tab-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function generateCompletionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `completion-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function copyCompletion(
  completion: SessionCompletionSnapshot | null | undefined
): SessionCompletionSnapshot | null {
  if (!completion) return null;
  return {
    ...completion,
    taskIdAliases: [...completion.taskIdAliases],
    turnIdAliases: [...completion.turnIdAliases],
  };
}

function copyCompletionHistory(
  completions: SessionCompletionSnapshot[] | null | undefined
): SessionCompletionSnapshot[] | undefined {
  if (!completions?.length) return undefined;
  return completions.map((completion) => copyCompletion(completion)!);
}

function copyState(state: SessionSpineState): SessionSpineState {
  return {
    ...state,
    tabs: state.tabs.map((tab) => ({ ...tab })),
    drafts: state.drafts ? { ...state.drafts } : undefined,
    pendingSubmittedDrafts: state.pendingSubmittedDrafts
      ? { ...state.pendingSubmittedDrafts }
      : undefined,
    activeCompletion: copyCompletion(state.activeCompletion),
    completionHistory: copyCompletionHistory(state.completionHistory),
  };
}

function readStoredInferenceMode(): ComposerInferenceMode | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(INFERENCE_MODE_STORAGE_KEY);
    if (isReasoningMode(raw)) return raw;
    if (raw != null) {
      window.localStorage.removeItem(INFERENCE_MODE_STORAGE_KEY);
    }
  } catch {
    // Ignore locked/private storage contexts.
  }
  return null;
}

function writeStoredInferenceMode(mode: ComposerInferenceMode | null): void {
  if (typeof window === "undefined") return;
  try {
    if (mode && isReasoningMode(mode)) {
      window.localStorage.setItem(INFERENCE_MODE_STORAGE_KEY, mode);
      return;
    }
    window.localStorage.removeItem(INFERENCE_MODE_STORAGE_KEY);
  } catch {
    // Ignore locked/private storage contexts.
  }
}

function resolveDefaultInferenceMode(
  value: ComposerInferenceMode | undefined
): ComposerInferenceMode {
  if (value && isReasoningMode(value) && value !== "default") {
    return value;
  }
  return FALLBACK_INFERENCE_MODE;
}

function isSessionTabEqual(a: SessionTab, b: SessionTab): boolean {
  return (
    a.tabId === b.tabId &&
    a.threadId === b.threadId &&
    a.pendingThread === b.pendingThread &&
    a.title === b.title &&
    (a.providerId ?? null) === (b.providerId ?? null) &&
    a.modelId === b.modelId &&
    a.inferenceMode === b.inferenceMode &&
    a.createdAt === b.createdAt &&
    a.updatedAt === b.updatedAt
  );
}

function areDraftsEqual(
  a: Record<string, string> | undefined,
  b: Record<string, string> | undefined
): boolean {
  if (a === b) return true;
  if (!a || !b) return !a && !b;
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) return false;
  for (const key of aKeys) {
    if ((a[key] ?? "") !== (b[key] ?? "")) {
      return false;
    }
  }
  return true;
}

function isCompletionEqual(
  a: SessionCompletionSnapshot | null | undefined,
  b: SessionCompletionSnapshot | null | undefined
): boolean {
  if (a === b) return true;
  if (!a || !b) return !a && !b;
  return (
    a.completionId === b.completionId &&
    a.tabId === b.tabId &&
    a.threadId === b.threadId &&
    a.status === b.status &&
    a.taskId === b.taskId &&
    a.turnId === b.turnId &&
    a.submittedDraft === b.submittedDraft &&
    a.errorText === b.errorText &&
    a.startedAt === b.startedAt &&
    a.updatedAt === b.updatedAt &&
    areDraftsEqual(
      Object.fromEntries(a.taskIdAliases.map((alias) => [alias, alias])),
      Object.fromEntries(b.taskIdAliases.map((alias) => [alias, alias]))
    ) &&
    areDraftsEqual(
      Object.fromEntries(a.turnIdAliases.map((alias) => [alias, alias])),
      Object.fromEntries(b.turnIdAliases.map((alias) => [alias, alias]))
    )
  );
}

function areCompletionHistoryEqual(
  a: SessionCompletionSnapshot[] | undefined,
  b: SessionCompletionSnapshot[] | undefined
): boolean {
  if (a === b) return true;
  if (!a || !b) return !a && !b;
  if (a.length !== b.length) return false;
  for (let index = 0; index < a.length; index += 1) {
    if (!isCompletionEqual(a[index], b[index])) {
      return false;
    }
  }
  return true;
}

function isStateSemanticallyEqual(a: SessionSpineState, b: SessionSpineState): boolean {
  if (
    (isReasoningMode(a.selectedInferenceMode) ? a.selectedInferenceMode : undefined) !==
    (isReasoningMode(b.selectedInferenceMode) ? b.selectedInferenceMode : undefined)
  ) {
    return false;
  }
  if (a.userId !== b.userId || a.deviceId !== b.deviceId) {
    return false;
  }
  if (a.activeTabId !== b.activeTabId) {
    return false;
  }
  if (a.tabs.length !== b.tabs.length) {
    return false;
  }
  for (let index = 0; index < a.tabs.length; index += 1) {
    if (!isSessionTabEqual(a.tabs[index], b.tabs[index])) {
      return false;
    }
  }
  if (!areDraftsEqual(a.drafts, b.drafts)) {
    return false;
  }
  if (!areDraftsEqual(a.pendingSubmittedDrafts, b.pendingSubmittedDrafts)) {
    return false;
  }
  if (!isCompletionEqual(a.activeCompletion, b.activeCompletion)) {
    return false;
  }
  return areCompletionHistoryEqual(a.completionHistory, b.completionHistory);
}

function unwrapEventPayload(data: unknown): Record<string, unknown> {
  if (!data || typeof data !== "object") return {};
  const candidate = data as Record<string, unknown>;
  const nested = candidate.data;
  if (nested && typeof nested === "object") {
    return nested as Record<string, unknown>;
  }
  return candidate;
}

function readCompletionEventIdentity(
  type: string,
  data: unknown
): CompletionEventIdentity {
  const payload = unwrapEventPayload(data);
  const message =
    payload.message && typeof payload.message === "object"
      ? (payload.message as Record<string, unknown>)
      : null;
  const role = normalizeToken(payload.role ?? message?.role)?.toLowerCase() ?? null;
  const identity: CompletionEventIdentity = {
    relevant:
      GUARDED_COMPLETION_EVENT_TYPES.has(type) ||
      (type === "message.created" && role === "assistant"),
    threadId:
      normalizeToken(
        payload.thread_id ??
          payload.threadId ??
          message?.thread_id ??
          message?.threadId ??
          (payload.thread && typeof payload.thread === "object"
            ? (payload.thread as Record<string, unknown>).id
            : null)
      ) ?? null,
    taskId:
      normalizeToken(
        payload.task_id ?? payload.taskId ?? message?.task_id ?? message?.taskId
      ) ?? null,
    turnId:
      normalizeToken(
        payload.turn_id ?? payload.turnId ?? message?.turn_id ?? message?.turnId
      ) ?? null,
    role,
    messageId:
      normalizeToken(
        payload.message_id ?? payload.messageId ?? payload.id ?? message?.id
      ) ?? null,
  };
  return identity;
}

function buildLiveEventKey(event: AcceptedLiveEvent): string {
  const eventId = normalizeToken(event.id);
  if (eventId) return eventId;
  const identity = readCompletionEventIdentity(event.type, event.data);
  return [
    event.type,
    identity.threadId ?? "",
    identity.taskId ?? "",
    identity.turnId ?? "",
    identity.messageId ?? "",
  ].join("|");
}

function hasVolatileRuntimeState(state: SessionSpineState | null | undefined): boolean {
  if (!state) return false;
  if (state.activeCompletion) return true;
  if (state.completionHistory?.length) return true;
  return Boolean(
    state.pendingSubmittedDrafts && Object.keys(state.pendingSubmittedDrafts).length
  );
}

export class SessionSpine {
  private static activeInstance: SessionSpine | null = null;
  private static readonly activeListeners = new Set<ActiveSpineListener>();

  static getRegisteredSpine(): SessionSpine | null {
    return SessionSpine.activeInstance;
  }

  static subscribeActiveSpine(listener: ActiveSpineListener): () => void {
    SessionSpine.activeListeners.add(listener);
    listener(
      SessionSpine.activeInstance,
      SessionSpine.activeInstance?.getSnapshot() ?? null
    );
    return () => {
      SessionSpine.activeListeners.delete(listener);
    };
  }

  private static emitActiveSnapshot(): void {
    const active = SessionSpine.activeInstance;
    const snapshot = active?.getSnapshot() ?? null;
    for (const listener of SessionSpine.activeListeners) {
      listener(active, snapshot);
    }
  }

  private readonly userId: string;
  private readonly deviceId: string;
  private readonly store: SessionStateStore;
  private readonly defaultProviderId: string | null;
  private readonly defaultModelId: string;
  private readonly defaultInferenceMode: ComposerInferenceMode;
  private readonly ttlSeconds: number;
  private readonly draftsTtlSeconds: number;
  private readonly canHydrate: () => boolean;
  private readonly canPersist: () => boolean;
  private readonly listeners = new Set<SessionListener>();
  private readonly runtimeKey: string;

  private state: SessionSpineState | null = null;
  private persistTimer: ReturnType<typeof setTimeout> | null = null;
  private hydrated = false;
  private activationHistory: TabId[] = [];

  constructor(config: SessionSpineConfig) {
    this.userId = config.userId;
    this.deviceId = config.deviceId;
    this.store = config.store;
    this.defaultProviderId = config.defaultProviderId ?? DEFAULT_PROVIDER_ID;
    this.defaultModelId = (config.defaultModelId || DEFAULT_MODEL_ID).trim() || DEFAULT_MODEL_ID;
    this.defaultInferenceMode = resolveDefaultInferenceMode(
      config.defaultInferenceMode ?? DEFAULT_INFERENCE_MODE
    );
    this.ttlSeconds = config.ttlSeconds ?? SESSION_TTL_SECONDS;
    this.draftsTtlSeconds = config.draftsTtlSeconds ?? SESSION_DRAFTS_TTL_SECONDS;
    this.canHydrate = config.canHydrate ?? (() => true);
    this.canPersist = config.canPersist ?? (() => true);
    this.runtimeKey = `${this.userId}:${this.deviceId}`;
    if (!runtimeSessionCacheByKey.has(this.runtimeKey)) {
      runtimeSessionCacheByKey.set(this.runtimeKey, {
        snapshot: null,
        processedLiveEventKeys: [],
      });
    }
    SessionSpine.activeInstance = this;
    SessionSpine.emitActiveSnapshot();
  }

  async hydrate(options: HydrateOptions = {}): Promise<SessionState> {
    const cached = this.readRuntimeSnapshot();
    if (cached) {
      this.state = cached;
      this.syncActivationHistory(cached);
      writeStoredInferenceMode(this.getSelectedInferenceMode(cached));
      this.hydrated = true;
      this.emit();
      return copyState(cached);
    }

    if (!this.canHydrate()) {
      const next = this.createDefaultState(options);
      this.state = next;
      this.writeRuntimeSnapshot(next);
      writeStoredInferenceMode(this.getSelectedInferenceMode(next));
      this.hydrated = true;
      this.emit();
      return copyState(next);
    }

    let loaded: SessionState | null = null;
    try {
      loaded = await this.store.getSessionState(this.userId, this.deviceId);
    } catch (error) {
      console.warn("[session] failed to hydrate state; using defaults", error);
    }
    const next = loaded
      ? this.normalizeState(loaded)
      : this.createDefaultState(options);
    this.state = next;
    this.writeRuntimeSnapshot(next);
    this.syncActivationHistory(next);
    writeStoredInferenceMode(this.getSelectedInferenceMode(next));
    this.hydrated = true;
    this.emit();
    if (!loaded) {
      await this.persistNow();
    }
    return copyState(next);
  }

  isHydrated(): boolean {
    return this.hydrated;
  }

  getSnapshot(): SessionState | null {
    return this.state ? copyState(this.state) : null;
  }

  getTabs(): SessionTab[] {
    return this.state ? this.state.tabs.map((tab) => ({ ...tab })) : [];
  }

  getActiveTab(): SessionTab | null {
    if (!this.state) return null;
    const tab = this.state.tabs.find((candidate) => candidate.tabId === this.state?.activeTabId);
    return tab ? { ...tab } : null;
  }

  getActiveTabId(): TabId | null {
    return this.state?.activeTabId ?? null;
  }

  getDraft(tabId: TabId): string {
    if (!this.state?.drafts) return "";
    return this.state.drafts[tabId] ?? "";
  }

  getActiveCompletion(): SessionCompletionSnapshot | null {
    return copyCompletion(this.state?.activeCompletion);
  }

  getCompletionStatus(): CompletionLifecycleStatus {
    return this.state?.activeCompletion?.status ?? "idle";
  }

  isComposerBlocked(): boolean {
    return isComposerBlockedStatus(this.getCompletionStatus());
  }

  findTabIdForThread(threadId: string | null | undefined): TabId | null {
    const normalizedThreadId = normalizeToken(threadId);
    if (!normalizedThreadId || !this.state) return null;
    const match = this.state.tabs.find((tab) => tab.threadId === normalizedThreadId);
    return match?.tabId ?? null;
  }

  rememberSubmittedDraft(
    text: string,
    options: { tabId?: TabId | null; threadId?: string | null } = {}
  ): void {
    this.mutate((current) => {
      const tabId = this.resolveCompletionTabId(current, options);
      if (!tabId) return;
      const nextValue = text ?? "";
      const currentValue = current.pendingSubmittedDrafts?.[tabId] ?? "";
      if (nextValue === currentValue) return;
      const pending = { ...(current.pendingSubmittedDrafts || {}) };
      if (nextValue) {
        pending[tabId] = nextValue;
      } else {
        delete pending[tabId];
      }
      current.pendingSubmittedDrafts = Object.keys(pending).length ? pending : undefined;
    });
  }

  startCompletion(
    options: {
      tabId?: TabId | null;
      threadId?: string | null;
      taskId?: string | null;
      turnId?: string | null;
      submittedDraft?: string | null;
      status?: CompletionLifecycleStatus;
    } = {}
  ): SessionCompletionSnapshot | null {
    let nextCompletion: SessionCompletionSnapshot | null = null;
    this.mutate((current) => {
      const tabId = this.resolveCompletionTabId(current, options);
      if (!tabId) return;
      const activeThreadId =
        current.tabs.find((tab) => tab.tabId === tabId)?.threadId ?? null;
      const threadId = normalizeToken(options.threadId) ?? activeThreadId;
      const taskIdAliases = uniqueTokens([options.taskId]);
      const turnIdAliases = uniqueTokens([options.turnId]);
      const submittedDraft =
        options.submittedDraft ??
        current.pendingSubmittedDrafts?.[tabId] ??
        current.drafts?.[tabId] ??
        "";
      const completionId = generateCompletionId();
      if (current.activeCompletion) {
        current.completionHistory = this.pushCompletionHistory(
          current.completionHistory,
          current.activeCompletion
        );
      }
      current.activeCompletion = {
        completionId,
        tabId,
        threadId,
        status:
          normalizeCompletionStatus(options.status) === "idle"
            ? "submitting"
            : normalizeCompletionStatus(options.status),
        taskId: taskIdAliases[0] ?? null,
        taskIdAliases,
        turnId: turnIdAliases[0] ?? null,
        turnIdAliases,
        submittedDraft,
        errorText: null,
        startedAt: nowIso(),
        updatedAt: nowIso(),
      };
      if (submittedDraft) {
        const pending = { ...(current.pendingSubmittedDrafts || {}) };
        pending[tabId] = submittedDraft;
        current.pendingSubmittedDrafts = pending;
      }
      nextCompletion = copyCompletion(current.activeCompletion);
    });
    return nextCompletion;
  }

  attachCompletionIdentity(options: CompletionSelector = {}): void {
    this.mutate((current) => {
      const active = current.activeCompletion;
      if (!active) return;
      if (!this.matchesCompletion(active, options, { allowThreadFallback: true })) {
        return;
      }
      const nextTaskAliases = uniqueTokens([active.taskId, ...active.taskIdAliases, options.taskId]);
      const nextTurnAliases = uniqueTokens([active.turnId, ...active.turnIdAliases, options.turnId]);
      const nextThreadId = normalizeToken(options.threadId) ?? active.threadId;
      const nextTaskId = normalizeToken(options.taskId) ?? active.taskId ?? nextTaskAliases[0] ?? null;
      const nextTurnId = normalizeToken(options.turnId) ?? active.turnId ?? nextTurnAliases[0] ?? null;
      if (
        active.threadId === nextThreadId &&
        active.taskId === nextTaskId &&
        active.turnId === nextTurnId &&
        areDraftsEqual(
          Object.fromEntries(active.taskIdAliases.map((alias) => [alias, alias])),
          Object.fromEntries(nextTaskAliases.map((alias) => [alias, alias]))
        ) &&
        areDraftsEqual(
          Object.fromEntries(active.turnIdAliases.map((alias) => [alias, alias])),
          Object.fromEntries(nextTurnAliases.map((alias) => [alias, alias]))
        )
      ) {
        return;
      }
      active.threadId = nextThreadId;
      active.taskId = nextTaskId;
      active.taskIdAliases = nextTaskAliases;
      active.turnId = nextTurnId;
      active.turnIdAliases = nextTurnAliases;
      active.updatedAt = nowIso();
    });
  }

  cancelActiveCompletion(
    options: CompletionSelector & { restoreDraft?: boolean } = {}
  ): SessionCompletionSnapshot | null {
    let cancelled: SessionCompletionSnapshot | null = null;
    this.mutate((current) => {
      const active = current.activeCompletion;
      if (!active) return;
      if (!this.matchesCompletion(active, options, { allowThreadFallback: true })) {
        return;
      }
      if (active.status === "canceled") {
        cancelled = copyCompletion(active);
        return;
      }
      active.status = "canceled";
      active.errorText = null;
      active.updatedAt = nowIso();
      const shouldRestoreDraft = options.restoreDraft !== false;
      if (shouldRestoreDraft && active.submittedDraft) {
        const drafts = { ...(current.drafts || {}) };
        drafts[active.tabId] = active.submittedDraft;
        current.drafts = drafts;
      }
      if (active.submittedDraft) {
        const pending = { ...(current.pendingSubmittedDrafts || {}) };
        pending[active.tabId] = active.submittedDraft;
        current.pendingSubmittedDrafts = pending;
      }
      cancelled = copyCompletion(active);
    });
    return cancelled;
  }

  completeActiveCompletion(options: CompletionSelector = {}): void {
    this.transitionActiveCompletion("completed", options);
  }

  failActiveCompletion(
    options: CompletionSelector & { errorText?: string | null } = {}
  ): void {
    this.mutate((current) => {
      const active = current.activeCompletion;
      if (!active) return;
      if (!this.matchesCompletion(active, options, { allowThreadFallback: true })) {
        return;
      }
      if (active.status === "failed" && active.errorText === (options.errorText ?? null)) {
        return;
      }
      active.status = "failed";
      active.errorText = options.errorText ?? null;
      active.updatedAt = nowIso();
    });
  }

  shouldAcceptLiveEvent(type: string, data: unknown): boolean {
    const current = this.state;
    if (!current) return true;
    const identity = readCompletionEventIdentity(type, data);
    if (!identity.relevant) return true;

    const active = current.activeCompletion ?? null;
    const history = current.completionHistory ?? [];
    const matchedHistorical = history.find((completion) =>
      this.matchesCompletion(completion, identity, { allowThreadFallback: false })
    );
    if (matchedHistorical) {
      return false;
    }
    if (!active) {
      return true;
    }
    const matchesActive = this.matchesCompletion(active, identity, {
      allowThreadFallback: type === "message.created" && identity.role === "assistant",
    });
    if (matchesActive) {
      return active.status !== "canceled";
    }
    if ((identity.taskId || identity.turnId) && identity.threadId && active.threadId) {
      return identity.threadId !== active.threadId;
    }
    if (
      type === "message.created" &&
      identity.role === "assistant" &&
      identity.threadId &&
      active.threadId
    ) {
      return identity.threadId !== active.threadId;
    }
    return true;
  }

  consumeAcceptedLiveEvent(event: AcceptedLiveEvent): void {
    const current = this.state;
    if (!current) return;
    const identity = readCompletionEventIdentity(event.type, event.data);
    if (!identity.relevant) return;
    const eventKey = buildLiveEventKey(event);
    if (!this.markLiveEventProcessed(eventKey)) {
      return;
    }
    switch (event.type) {
      case "task.progress":
        this.transitionActiveCompletion("streaming", identity);
        return;
      case "message.created":
        if (identity.role !== "assistant") return;
        this.attachCompletionIdentity(identity);
        this.transitionActiveCompletion("streaming", identity);
        return;
      case "task.completed":
        this.completeActiveCompletion(identity);
        return;
      case "task.failed":
      case "completion.error": {
        const payload = unwrapEventPayload(event.data);
        this.failActiveCompletion({
          ...identity,
          errorText:
            normalizeToken(payload.error ?? payload.message ?? payload.detail) ?? null,
        });
        return;
      }
      case "task.cancelled":
        this.cancelActiveCompletion({ ...identity, restoreDraft: false });
        return;
      default:
        return;
    }
  }

  subscribe(listener: SessionListener): () => void {
    this.listeners.add(listener);
    if (this.state) listener(copyState(this.state));
    return () => {
      this.listeners.delete(listener);
    };
  }

  tabOpen(threadId?: string, title?: string): SessionTab {
    return this.mutate((current) => {
      const active = current.tabs.find((tab) => tab.tabId === current.activeTabId);
      const tab = this.createTab({
        threadId,
        title,
        providerId: active?.providerId ?? this.defaultProviderId,
        modelId: active?.modelId || this.defaultModelId,
        inferenceMode: this.getSelectedInferenceMode(current),
      });
      current.tabs.push(tab);
      current.activeTabId = tab.tabId;
      this.markTabActive(tab.tabId);
      return tab;
    });
  }

  tabClose(tabId: TabId): void {
    this.mutate((current) => {
      const idx = current.tabs.findIndex((tab) => tab.tabId === tabId);
      if (idx < 0) return;
      const [closed] = current.tabs.splice(idx, 1);
      this.activationHistory = this.activationHistory.filter(
        (candidate) => candidate !== closed?.tabId
      );
      if (current.drafts && closed) {
        delete current.drafts[closed.tabId];
        if (!Object.keys(current.drafts).length) {
          delete current.drafts;
        }
      }
      if (current.pendingSubmittedDrafts && closed) {
        delete current.pendingSubmittedDrafts[closed.tabId];
        if (!Object.keys(current.pendingSubmittedDrafts).length) {
          delete current.pendingSubmittedDrafts;
        }
      }
      if (current.activeCompletion?.tabId === tabId) {
        current.completionHistory = this.pushCompletionHistory(
          current.completionHistory,
          current.activeCompletion
        );
        current.activeCompletion = null;
      }

      if (!current.tabs.length) {
        const replacement = this.createTab({
          providerId: closed?.providerId ?? this.defaultProviderId,
          modelId: closed?.modelId || this.defaultModelId,
          inferenceMode: this.getSelectedInferenceMode(current),
        });
        current.tabs.push(replacement);
        current.activeTabId = replacement.tabId;
        this.markTabActive(replacement.tabId);
        return;
      }

      if (current.activeTabId === tabId) {
        const priorTabId = this.getMostRecentRemainingTabId(current.tabs);
        const nextActive =
          current.tabs.find((tab) => tab.tabId === priorTabId) ??
          current.tabs[Math.max(0, idx - 1)] ??
          current.tabs[0];
        current.activeTabId = nextActive.tabId;
        this.markTabActive(nextActive.tabId);
      }
    });
  }

  tabActivate(tabId: TabId): void {
    this.mutate((current) => {
      if (!current.tabs.some((tab) => tab.tabId === tabId)) return;
      current.activeTabId = tabId;
      this.markTabActive(tabId);
    });
  }

  tabActivateNext(): void {
    this.tabActivateByOffset(1);
  }

  tabActivatePrevious(): void {
    this.tabActivateByOffset(-1);
  }

  tabReorder(tabOrder: TabId[]): void {
    this.mutate((current) => {
      if (!tabOrder.length || current.tabs.length < 2) return;
      const byId = new Map(current.tabs.map((tab) => [tab.tabId, tab]));
      const next: SessionTab[] = [];
      for (const tabId of tabOrder) {
        const tab = byId.get(tabId);
        if (!tab) continue;
        next.push(tab);
        byId.delete(tabId);
      }
      for (const tab of byId.values()) {
        next.push(tab);
      }
      current.tabs = next;
      if (!current.tabs.some((tab) => tab.tabId === current.activeTabId)) {
        current.activeTabId = current.tabs[0]?.tabId ?? current.activeTabId;
      }
    });
  }

  tabSetModel(tabId: TabId, modelId: string): void {
    this.mutate((current) => {
      const tab = current.tabs.find((candidate) => candidate.tabId === tabId);
      if (!tab) return;
      const normalized = modelId.trim() || this.defaultModelId;
      if (tab.modelId === normalized) return;
      tab.modelId = normalized;
      tab.updatedAt = nowIso();
    });
  }

  tabSetProvider(tabId: TabId, providerId: string | null): void {
    this.mutate((current) => {
      const tab = current.tabs.find((candidate) => candidate.tabId === tabId);
      if (!tab) return;
      const normalized = providerId?.trim() || null;
      if ((tab.providerId ?? null) === normalized) return;
      tab.providerId = normalized;
      tab.updatedAt = nowIso();
    });
  }

  tabSetInferenceMode(
    tabId: TabId,
    inferenceMode: ComposerInferenceMode
  ): void {
    this.mutate((current) => {
      if (!current.tabs.some((candidate) => candidate.tabId === tabId)) return;
      const normalized = isReasoningMode(inferenceMode)
        ? inferenceMode
        : this.defaultInferenceMode;
      const nextSelectedInferenceMode = current.selectedInferenceMode;
      const alreadySelected =
        isReasoningMode(nextSelectedInferenceMode) &&
        nextSelectedInferenceMode === normalized;
      let changed = !alreadySelected;
      const timestamp = nowIso();
      for (const tab of current.tabs) {
        if (tab.inferenceMode === normalized) continue;
        tab.inferenceMode = normalized;
        tab.updatedAt = timestamp;
        changed = true;
      }
      if (!changed) return;
      current.selectedInferenceMode = normalized;
    });
  }

  tabSetThread(
    tabId: TabId,
    threadId?: string | null,
    title?: string | null
  ): void {
    this.mutate((current) => {
      const tab = current.tabs.find((candidate) => candidate.tabId === tabId);
      if (!tab) return;
      const nextThreadId = threadId?.trim() || undefined;
      const providedTitle = title?.trim() || undefined;
      const nextTitle = providedTitle ?? (nextThreadId ? tab.title : undefined);
      const nextPendingThread = !nextThreadId;
      if (
        tab.threadId === nextThreadId &&
        tab.pendingThread === nextPendingThread &&
        tab.title === nextTitle
      ) {
        return;
      }
      tab.threadId = nextThreadId;
      tab.pendingThread = nextPendingThread;
      tab.title = nextTitle;
      tab.updatedAt = nowIso();
      if (current.activeCompletion?.tabId === tabId) {
        current.activeCompletion.threadId = nextThreadId ?? null;
        current.activeCompletion.updatedAt = nowIso();
      }
    });
  }

  tabSetDraft(tabId: TabId, text: string): void {
    this.mutate(
      (current) => {
        if (!current.tabs.some((tab) => tab.tabId === tabId)) return;
        const nextDraft = text ?? "";
        const currentDraft = current.drafts?.[tabId] ?? "";
        if (nextDraft === currentDraft) return;
        const drafts = { ...(current.drafts || {}) };
        if (!nextDraft.trim()) {
          delete drafts[tabId];
        } else {
          drafts[tabId] = nextDraft;
        }
        current.drafts = Object.keys(drafts).length ? drafts : undefined;
      },
      { debounceMs: 300 }
    );
  }

  async clear(): Promise<void> {
    this.state = null;
    this.hydrated = false;
    if (this.persistTimer) {
      clearTimeout(this.persistTimer);
      this.persistTimer = null;
    }
    runtimeSessionCacheByKey.delete(this.runtimeKey);
    await this.store.deleteSessionState(this.userId, this.deviceId);
    writeStoredInferenceMode(null);
    if (SessionSpine.activeInstance === this) {
      SessionSpine.activeInstance = null;
      SessionSpine.emitActiveSnapshot();
    }
    this.emit();
  }

  private mutate<T>(
    mutator: (state: SessionSpineState) => T,
    options: MutationOptions = {}
  ): T {
    if (!this.state) {
      this.state = this.createDefaultState({});
      this.writeRuntimeSnapshot(this.state);
      this.hydrated = true;
    }
    const current = this.state;
    const working = copyState(current);
    const result = mutator(working);
    if (isStateSemanticallyEqual(current, working)) {
      return result;
    }
    this.state = this.normalizeState(
      {
        ...working,
        version: Math.max(current.version, SESSION_SCHEMA_VERSION) + 1,
        updatedAt: nowIso(),
      },
      { includeRuntimeFields: true }
    );
    this.writeRuntimeSnapshot(this.state);
    this.syncActivationHistory(this.state);
    writeStoredInferenceMode(this.getSelectedInferenceMode(this.state));
    this.emit();
    this.schedulePersist(options.debounceMs ?? 0);
    return result;
  }

  private transitionActiveCompletion(
    status: CompletionLifecycleStatus,
    selector: CompletionSelector = {}
  ): void {
    this.mutate((current) => {
      const active = current.activeCompletion;
      if (!active) return;
      if (!this.matchesCompletion(active, selector, { allowThreadFallback: true })) {
        return;
      }
      if (active.status === status) return;
      active.status = status;
      if (status !== "failed") {
        active.errorText = null;
      }
      active.updatedAt = nowIso();
    });
  }

  private pushCompletionHistory(
    history: SessionCompletionSnapshot[] | undefined,
    completion: SessionCompletionSnapshot | null | undefined
  ): SessionCompletionSnapshot[] | undefined {
    const snapshot = copyCompletion(completion);
    if (!snapshot) return history;
    const next = [
      snapshot,
      ...(history ?? []).filter(
        (candidate) => candidate.completionId !== snapshot.completionId
      ),
    ];
    return next.slice(0, COMPLETION_HISTORY_LIMIT);
  }

  private matchesCompletion(
    completion: SessionCompletionSnapshot,
    selector: CompletionSelector,
    options: { allowThreadFallback: boolean }
  ): boolean {
    const taskId = normalizeToken(selector.taskId);
    if (taskId && completion.taskIdAliases.includes(taskId)) {
      return true;
    }
    const turnId = normalizeToken(selector.turnId);
    if (turnId && completion.turnIdAliases.includes(turnId)) {
      return true;
    }
    const tabId = selector.tabId ?? null;
    if (tabId && completion.tabId === tabId) {
      return true;
    }
    if (!options.allowThreadFallback) {
      return false;
    }
    const threadId = normalizeToken(selector.threadId);
    if (threadId && completion.threadId && completion.threadId === threadId) {
      return true;
    }
    return !taskId && !turnId && !tabId && !threadId;
  }

  private resolveCompletionTabId(
    state: SessionSpineState,
    selector: CompletionSelector
  ): TabId | null {
    if (selector.tabId && state.tabs.some((tab) => tab.tabId === selector.tabId)) {
      return selector.tabId;
    }
    const normalizedThreadId = normalizeToken(selector.threadId);
    if (normalizedThreadId) {
      const threadMatch = state.tabs.find((tab) => tab.threadId === normalizedThreadId);
      if (threadMatch) return threadMatch.tabId;
    }
    return state.activeTabId ?? state.tabs[0]?.tabId ?? null;
  }

  private markTabActive(tabId: TabId): void {
    this.activationHistory = this.activationHistory.filter(
      (candidate) => candidate !== tabId
    );
    this.activationHistory.push(tabId);
  }

  private tabActivateByOffset(direction: 1 | -1): void {
    this.mutate((current) => {
      if (current.tabs.length <= 1 || !current.activeTabId) return;
      const activeIndex = current.tabs.findIndex(
        (tab) => tab.tabId === current.activeTabId
      );
      if (activeIndex < 0) return;
      const nextIndex =
        (activeIndex + direction + current.tabs.length) % current.tabs.length;
      const nextTab = current.tabs[nextIndex];
      if (!nextTab || nextTab.tabId === current.activeTabId) return;
      current.activeTabId = nextTab.tabId;
      this.markTabActive(nextTab.tabId);
    });
  }

  private getMostRecentRemainingTabId(tabs: SessionTab[]): TabId | null {
    const allowed = new Set(tabs.map((tab) => tab.tabId));
    for (let index = this.activationHistory.length - 1; index >= 0; index -= 1) {
      const candidate = this.activationHistory[index];
      if (allowed.has(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  private syncActivationHistory(state: SessionState): void {
    const allowed = new Set(state.tabs.map((tab) => tab.tabId));
    const preserved = this.activationHistory.filter((tabId) => allowed.has(tabId));
    for (const tab of state.tabs) {
      if (!preserved.includes(tab.tabId)) {
        preserved.push(tab.tabId);
      }
    }
    this.activationHistory = preserved;
    if (state.activeTabId) {
      this.markTabActive(state.activeTabId);
    }
  }

  private emit(): void {
    if (!this.state) {
      if (SessionSpine.activeInstance === this) {
        SessionSpine.emitActiveSnapshot();
      }
      return;
    }
    const snapshot = copyState(this.state);
    for (const listener of this.listeners) {
      listener(snapshot);
    }
    if (SessionSpine.activeInstance === this) {
      SessionSpine.emitActiveSnapshot();
    }
  }

  private schedulePersist(debounceMs: number): void {
    if (this.persistTimer) {
      clearTimeout(this.persistTimer);
      this.persistTimer = null;
    }
    if (debounceMs > 0) {
      this.persistTimer = setTimeout(() => {
        void this.persistNow();
      }, debounceMs);
      return;
    }
    void this.persistNow();
  }

  private async persistNow(): Promise<void> {
    if (!this.state) return;
    if (this.persistTimer) {
      clearTimeout(this.persistTimer);
      this.persistTimer = null;
    }
    if (!this.canPersist()) return;
    try {
      await this.store.setSessionState(
        this.userId,
        this.deviceId,
        this.toPersistedState(this.state),
        this.resolveTtl(this.state)
      );
    } catch (error) {
      console.warn("[session] failed to persist state", error);
    }
  }

  private resolveTtl(state: SessionState): number {
    const hasDrafts = Boolean(state.drafts && Object.keys(state.drafts).length);
    return hasDrafts ? this.draftsTtlSeconds : this.ttlSeconds;
  }

  private createTab(input: {
    threadId?: string;
    title?: string;
    providerId?: string | null;
    modelId?: string;
    inferenceMode?: ComposerInferenceMode;
  }): SessionTab {
    const timestamp = nowIso();
    return {
      tabId: generateTabId(),
      threadId: input.threadId?.trim() || undefined,
      pendingThread: !(input.threadId?.trim() || undefined),
      title: input.title?.trim() || undefined,
      providerId: input.providerId?.trim() || this.defaultProviderId,
      modelId: input.modelId?.trim() || this.defaultModelId,
      inferenceMode: isReasoningMode(input.inferenceMode)
        ? input.inferenceMode
        : this.defaultInferenceMode,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
  }

  private createDefaultState(options: HydrateOptions): SessionSpineState {
    const selectedInferenceMode = this.resolveSelectedInferenceMode({
      tabs: [],
      activeTabId: "",
      selectedInferenceMode: options.inferenceMode,
    });
    const tab = this.createTab({
      threadId: options.threadId,
      title: options.title,
      providerId: options.providerId ?? this.defaultProviderId,
      modelId: options.modelId || this.defaultModelId,
      inferenceMode: selectedInferenceMode,
    });
    return {
      deviceId: this.deviceId,
      userId: this.userId,
      tabs: [tab],
      activeTabId: tab.tabId,
      drafts: undefined,
      pendingSubmittedDrafts: undefined,
      activeCompletion: null,
      completionHistory: undefined,
      selectedInferenceMode,
      version: SESSION_SCHEMA_VERSION,
      updatedAt: nowIso(),
    };
  }

  private normalizeState(
    state: SessionState | SessionSpineState,
    options: { includeRuntimeFields?: boolean } = {}
  ): SessionSpineState {
    const persistedState = state as SessionSpineState;
    const selectedInferenceMode = this.resolveSelectedInferenceMode(persistedState);
    const safeTabs = Array.isArray(state.tabs) ? state.tabs : [];
    const tabs = safeTabs.length
      ? safeTabs.map((tab) => {
          const normalizedThreadId = tab.threadId?.trim() || undefined;
          return {
            tabId: tab.tabId || generateTabId(),
            threadId: normalizedThreadId,
            pendingThread:
              normalizedThreadId == null
                ? typeof tab.pendingThread === "boolean"
                  ? tab.pendingThread
                  : true
                : false,
            title: tab.title?.trim() || undefined,
            providerId: tab.providerId?.trim() || this.defaultProviderId,
            modelId: tab.modelId?.trim() || this.defaultModelId,
            inferenceMode: selectedInferenceMode,
            createdAt: tab.createdAt || nowIso(),
            updatedAt: tab.updatedAt || tab.createdAt || nowIso(),
          };
        })
      : [
          this.createTab({
            providerId: this.defaultProviderId,
            modelId: this.defaultModelId,
            inferenceMode: selectedInferenceMode,
          }),
        ];

    const activeTabId = tabs.some((tab) => tab.tabId === state.activeTabId)
      ? state.activeTabId
      : tabs[0].tabId;

    let drafts = state.drafts ? { ...state.drafts } : undefined;
    if (drafts) {
      const validTabs = new Set(tabs.map((tab) => tab.tabId));
      for (const tabId of Object.keys(drafts)) {
        if (!validTabs.has(tabId)) delete drafts[tabId];
      }
      if (!Object.keys(drafts).length) {
        drafts = undefined;
      }
    }

    let pendingSubmittedDrafts = options.includeRuntimeFields
      ? persistedState.pendingSubmittedDrafts
        ? { ...persistedState.pendingSubmittedDrafts }
        : undefined
      : undefined;
    if (pendingSubmittedDrafts) {
      const validTabs = new Set(tabs.map((tab) => tab.tabId));
      for (const tabId of Object.keys(pendingSubmittedDrafts)) {
        if (!validTabs.has(tabId)) delete pendingSubmittedDrafts[tabId];
      }
      if (!Object.keys(pendingSubmittedDrafts).length) {
        pendingSubmittedDrafts = undefined;
      }
    }

    const base: SessionSpineState = {
      ...state,
      deviceId: state.deviceId || this.deviceId,
      userId: state.userId || this.userId,
      tabs,
      activeTabId,
      drafts,
      pendingSubmittedDrafts,
      selectedInferenceMode,
      version: Math.max(state.version || 0, SESSION_SCHEMA_VERSION),
      updatedAt: state.updatedAt || nowIso(),
      activeCompletion: null,
      completionHistory: undefined,
    };

    if (!options.includeRuntimeFields) {
      return base;
    }

    const activeCompletion = this.normalizeCompletion(
      persistedState.activeCompletion,
      tabs,
      activeTabId
    );
    const completionHistory = Array.isArray(persistedState.completionHistory)
      ? persistedState.completionHistory
          .map((completion) => this.normalizeCompletion(completion, tabs, activeTabId))
          .filter(
            (completion): completion is SessionCompletionSnapshot => completion != null
          )
          .filter(
            (completion, index, all) =>
              all.findIndex(
                (candidate) => candidate.completionId === completion.completionId
              ) === index
          )
          .slice(0, COMPLETION_HISTORY_LIMIT)
      : [];

    base.activeCompletion = activeCompletion;
    base.completionHistory = completionHistory.length ? completionHistory : undefined;
    return base;
  }

  private normalizeCompletion(
    completion: SessionCompletionSnapshot | null | undefined,
    tabs: SessionTab[],
    activeTabId: TabId
  ): SessionCompletionSnapshot | null {
    if (!completion) return null;
    const tabId = tabs.some((tab) => tab.tabId === completion.tabId)
      ? completion.tabId
      : activeTabId;
    const taskIdAliases = uniqueTokens([completion.taskId, ...completion.taskIdAliases]);
    const turnIdAliases = uniqueTokens([completion.turnId, ...completion.turnIdAliases]);
    return {
      completionId: normalizeToken(completion.completionId) ?? generateCompletionId(),
      tabId,
      threadId:
        normalizeToken(completion.threadId) ??
        tabs.find((tab) => tab.tabId === tabId)?.threadId ??
        null,
      status: normalizeCompletionStatus(completion.status),
      taskId: normalizeToken(completion.taskId) ?? taskIdAliases[0] ?? null,
      taskIdAliases,
      turnId: normalizeToken(completion.turnId) ?? turnIdAliases[0] ?? null,
      turnIdAliases,
      submittedDraft: completion.submittedDraft ?? "",
      errorText: normalizeToken(completion.errorText) ?? null,
      startedAt: completion.startedAt || nowIso(),
      updatedAt: completion.updatedAt || completion.startedAt || nowIso(),
    };
  }

  private toPersistedState(state: SessionSpineState): SessionState {
    const {
      activeCompletion: _activeCompletion,
      completionHistory: _completionHistory,
      pendingSubmittedDrafts: _pendingSubmittedDrafts,
      ...persisted
    } = state;
    return persisted as SessionState;
  }

  private readRuntimeSnapshot(): SessionSpineState | null {
    const runtime = runtimeSessionCacheByKey.get(this.runtimeKey);
    if (!runtime?.snapshot || !hasVolatileRuntimeState(runtime.snapshot)) return null;
    return this.normalizeState(runtime.snapshot, { includeRuntimeFields: true });
  }

  private writeRuntimeSnapshot(state: SessionSpineState): void {
    const runtime = runtimeSessionCacheByKey.get(this.runtimeKey);
    if (!runtime) return;
    runtime.snapshot = copyState(state);
  }

  private markLiveEventProcessed(eventKey: string): boolean {
    if (!eventKey) return true;
    const runtime = runtimeSessionCacheByKey.get(this.runtimeKey);
    if (!runtime) return true;
    if (runtime.processedLiveEventKeys.includes(eventKey)) {
      return false;
    }
    runtime.processedLiveEventKeys.push(eventKey);
    if (runtime.processedLiveEventKeys.length > RECENT_COMPLETION_EVENT_LIMIT) {
      runtime.processedLiveEventKeys.splice(
        0,
        runtime.processedLiveEventKeys.length - RECENT_COMPLETION_EVENT_LIMIT
      );
    }
    return true;
  }

  private getSelectedInferenceMode(
    state: SessionSpineState | null | undefined
  ): ComposerInferenceMode {
    return this.resolveSelectedInferenceMode(state ?? null);
  }

  private resolveSelectedInferenceMode(
    state: Partial<SessionSpineState> | null | undefined
  ): ComposerInferenceMode {
    const persisted = state?.selectedInferenceMode;
    if (isReasoningMode(persisted)) {
      return persisted;
    }

    const tabs = Array.isArray(state?.tabs) ? state.tabs : [];
    const activeTab =
      typeof state?.activeTabId === "string"
        ? tabs.find((tab) => tab.tabId === state.activeTabId)
        : null;
    if (isReasoningMode(activeTab?.inferenceMode)) {
      return activeTab.inferenceMode;
    }

    const firstValidTab = tabs.find((tab) => isReasoningMode(tab.inferenceMode));
    if (firstValidTab?.inferenceMode) {
      return firstValidTab.inferenceMode;
    }

    return readStoredInferenceMode() ?? this.defaultInferenceMode;
  }
}
