import type { SessionStateStore } from "@/state/session/SessionStateStore";
import {
  DEFAULT_MODEL_ID,
  SESSION_DRAFTS_TTL_SECONDS,
  SESSION_SCHEMA_VERSION,
  SESSION_TTL_SECONDS,
  type SessionState,
  type SessionTab,
  type TabId,
} from "@/state/session/types";

type SessionListener = (state: SessionState) => void;

type HydrateOptions = {
  threadId?: string;
  title?: string;
  modelId?: string;
};

type MutationOptions = {
  debounceMs?: number;
};

type SessionSpineConfig = {
  userId: string;
  deviceId: string;
  store: SessionStateStore;
  defaultModelId?: string;
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

export class SessionSpine {
  private readonly userId: string;
  private readonly deviceId: string;
  private readonly store: SessionStateStore;
  private readonly defaultModelId: string;
  private readonly ttlSeconds: number;
  private readonly draftsTtlSeconds: number;
  private readonly canHydrate: () => boolean;
  private readonly canPersist: () => boolean;
  private readonly listeners = new Set<SessionListener>();

  private state: SessionState | null = null;
  private persistTimer: ReturnType<typeof setTimeout> | null = null;
  private hydrated = false;

  constructor(config: SessionSpineConfig) {
    this.userId = config.userId;
    this.deviceId = config.deviceId;
    this.store = config.store;
    this.defaultModelId = (config.defaultModelId || DEFAULT_MODEL_ID).trim() || DEFAULT_MODEL_ID;
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
        modelId: active?.modelId || this.defaultModelId,
      });
      current.tabs.push(tab);
      current.activeTabId = tab.tabId;
      return tab;
    });
  }

  tabClose(tabId: TabId): void {
    this.mutate((current) => {
      const idx = current.tabs.findIndex((tab) => tab.tabId === tabId);
      if (idx < 0) return;
      const [closed] = current.tabs.splice(idx, 1);
      if (current.drafts && closed) {
        delete current.drafts[closed.tabId];
        if (!Object.keys(current.drafts).length) {
          delete current.drafts;
        }
      }

      if (!current.tabs.length) {
        const replacement = this.createTab({
          modelId: closed?.modelId || this.defaultModelId,
        });
        current.tabs.push(replacement);
        current.activeTabId = replacement.tabId;
        return;
      }

      if (current.activeTabId === tabId) {
        const nextActive = current.tabs[Math.max(0, idx - 1)] ?? current.tabs[0];
        current.activeTabId = nextActive.tabId;
      }
    });
  }

  tabActivate(tabId: TabId): void {
    this.mutate((current) => {
      if (!current.tabs.some((tab) => tab.tabId === tabId)) return;
      current.activeTabId = tabId;
    });
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
      if (tab.threadId === nextThreadId && tab.title === nextTitle) return;
      tab.threadId = nextThreadId;
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
    const working = copyState(this.state);
    const result = mutator(working);
    this.state = this.normalizeState({
      ...working,
      version: Math.max(working.version, SESSION_SCHEMA_VERSION) + 1,
      updatedAt: nowIso(),
    });
    this.emit();
    this.schedulePersist(options.debounceMs ?? 0);
    return result;
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
    modelId?: string;
  }): SessionTab {
    const timestamp = nowIso();
    return {
      tabId: generateTabId(),
      threadId: input.threadId?.trim() || undefined,
      title: input.title?.trim() || undefined,
      modelId: input.modelId?.trim() || this.defaultModelId,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
  }

  private createDefaultState(options: HydrateOptions): SessionState {
    const tab = this.createTab({
      threadId: options.threadId,
      title: options.title,
      modelId: options.modelId || this.defaultModelId,
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
      ? safeTabs.map((tab) => ({
          tabId: tab.tabId || generateTabId(),
          threadId: tab.threadId?.trim() || undefined,
          title: tab.title?.trim() || undefined,
          modelId: tab.modelId?.trim() || this.defaultModelId,
          createdAt: tab.createdAt || nowIso(),
          updatedAt: tab.updatedAt || tab.createdAt || nowIso(),
        }))
      : [this.createTab({ modelId: this.defaultModelId })];

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
