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

function nowIso(): string {
  return new Date().toISOString();
}

function generateTabId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `tab-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function copyState(state: SessionState): SessionState {
  return {
    ...state,
    tabs: state.tabs.map((tab) => ({ ...tab })),
    drafts: state.drafts ? { ...state.drafts } : undefined,
  };
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
  a: SessionState["drafts"],
  b: SessionState["drafts"]
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

function isStateSemanticallyEqual(a: SessionState, b: SessionState): boolean {
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
  return areDraftsEqual(a.drafts, b.drafts);
}

export class SessionSpine {
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

  private state: SessionState | null = null;
  private persistTimer: ReturnType<typeof setTimeout> | null = null;
  private hydrated = false;
  private activationHistory: TabId[] = [];

  constructor(config: SessionSpineConfig) {
    this.userId = config.userId;
    this.deviceId = config.deviceId;
    this.store = config.store;
    this.defaultProviderId = config.defaultProviderId ?? DEFAULT_PROVIDER_ID;
    this.defaultModelId = (config.defaultModelId || DEFAULT_MODEL_ID).trim() || DEFAULT_MODEL_ID;
    this.defaultInferenceMode =
      config.defaultInferenceMode ?? DEFAULT_INFERENCE_MODE;
    this.ttlSeconds = config.ttlSeconds ?? SESSION_TTL_SECONDS;
    this.draftsTtlSeconds = config.draftsTtlSeconds ?? SESSION_DRAFTS_TTL_SECONDS;
    this.canHydrate = config.canHydrate ?? (() => true);
    this.canPersist = config.canPersist ?? (() => true);
  }

  async hydrate(options: HydrateOptions = {}): Promise<SessionState> {
    if (!this.canHydrate()) {
      const next = this.createDefaultState(options);
      this.state = next;
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
    this.syncActivationHistory(next);
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
        inferenceMode: active?.inferenceMode || this.defaultInferenceMode,
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

      if (!current.tabs.length) {
        const replacement = this.createTab({
          providerId: closed?.providerId ?? this.defaultProviderId,
          modelId: closed?.modelId || this.defaultModelId,
          inferenceMode: closed?.inferenceMode || this.defaultInferenceMode,
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
      const tab = current.tabs.find((candidate) => candidate.tabId === tabId);
      if (!tab) return;
      const normalized = isReasoningMode(inferenceMode)
        ? inferenceMode
        : this.defaultInferenceMode;
      if (tab.inferenceMode === normalized) return;
      tab.inferenceMode = normalized;
      tab.updatedAt = nowIso();
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
    await this.store.deleteSessionState(this.userId, this.deviceId);
    this.emit();
  }

  private mutate<T>(
    mutator: (state: SessionState) => T,
    options: MutationOptions = {}
  ): T {
    if (!this.state) {
      this.state = this.createDefaultState({});
      this.hydrated = true;
    }
    const current = this.state;
    const working = copyState(current);
    const result = mutator(working);
    if (isStateSemanticallyEqual(current, working)) {
      return result;
    }
    this.state = this.normalizeState({
      ...working,
      version: Math.max(current.version, SESSION_SCHEMA_VERSION) + 1,
      updatedAt: nowIso(),
    });
    this.syncActivationHistory(this.state);
    this.emit();
    this.schedulePersist(options.debounceMs ?? 0);
    return result;
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
    if (!this.state) return;
    const snapshot = copyState(this.state);
    for (const listener of this.listeners) {
      listener(snapshot);
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
        this.state,
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
      inferenceMode: input.inferenceMode || this.defaultInferenceMode,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
  }

  private createDefaultState(options: HydrateOptions): SessionState {
    const tab = this.createTab({
      threadId: options.threadId,
      title: options.title,
      providerId: options.providerId ?? this.defaultProviderId,
      modelId: options.modelId || this.defaultModelId,
      inferenceMode: options.inferenceMode || this.defaultInferenceMode,
    });
    return {
      deviceId: this.deviceId,
      userId: this.userId,
      tabs: [tab],
      activeTabId: tab.tabId,
      drafts: undefined,
      version: SESSION_SCHEMA_VERSION,
      updatedAt: nowIso(),
    };
  }

  private normalizeState(state: SessionState): SessionState {
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
            inferenceMode: isReasoningMode(tab.inferenceMode)
              ? tab.inferenceMode
              : this.defaultInferenceMode,
            createdAt: tab.createdAt || nowIso(),
            updatedAt: tab.updatedAt || tab.createdAt || nowIso(),
          };
        })
      : [
          this.createTab({
            providerId: this.defaultProviderId,
            modelId: this.defaultModelId,
            inferenceMode: this.defaultInferenceMode,
          }),
        ];

    const activeTabId = tabs.some((tab) => tab.tabId === state.activeTabId)
      ? state.activeTabId
      : tabs[0].tabId;

    const drafts = state.drafts ? { ...state.drafts } : undefined;
    if (drafts) {
      const validTabs = new Set(tabs.map((tab) => tab.tabId));
      for (const tabId of Object.keys(drafts)) {
        if (!validTabs.has(tabId)) delete drafts[tabId];
      }
      if (!Object.keys(drafts).length) {
        return {
          ...state,
          deviceId: state.deviceId || this.deviceId,
          userId: state.userId || this.userId,
          tabs,
          activeTabId,
          drafts: undefined,
          version: Math.max(state.version || 0, SESSION_SCHEMA_VERSION),
          updatedAt: state.updatedAt || nowIso(),
        };
      }
    }

    return {
      ...state,
      deviceId: state.deviceId || this.deviceId,
      userId: state.userId || this.userId,
      tabs,
      activeTabId,
      drafts,
      version: Math.max(state.version || 0, SESSION_SCHEMA_VERSION),
      updatedAt: state.updatedAt || nowIso(),
    };
  }
}
