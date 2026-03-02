import { GuardianEventSource } from "@/lib/guardianEventSource";
import { getBackendOutageRemainingMs } from "@/lib/api";

type HubEventListener = (event: LiveEventsHubEvent) => void;
type HubStatusListener = (status: LiveEventsHubStatus) => void;

type HubConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

export type LiveEventsHubConfig = {
  url: string;
  headers: Record<string, string>;
  withCredentials: boolean;
  onUnauthorized?: () => void;
};

export type LiveEventsHubEvent = {
  id: string | null;
  type: string;
  data: unknown;
};

export type LiveEventsHubStatus = {
  readyState: 0 | 1 | 2;
  subscribers: number;
  lastEventId: string | null;
  lastErrorAt: number | null;
  connectAttempt: number;
  retryMs: number;
  connectionStatus: HubConnectionStatus;
};

declare global {
  interface Window {
    __CFY_SSE_STATUS__?: () => LiveEventsHubStatus;
  }
}

const DEFAULT_EVENT_TYPES = [
  "ping",
  "message.created",
  "thread.updated",
  "thread.created",
  "thread.branch",
  "thread.archived",
  "thread.profile.switched",
  "connector.status",
  "connector.sync",
];

const INITIAL_RETRY_MS = 1000;
const MAX_RETRY_MS = 15000;
const JITTER_MIN = 0.8;
const JITTER_MAX = 1.2;

const DEDUPE_LIMIT = 200;
const EVENT_PRESSURE_WINDOW_MS = 2000;
const EVENT_PRESSURE_THRESHOLD = 100;
const EVENT_PRESSURE_FLUSH_MS = 100;
const LAST_EVENT_STORAGE_KEY = "cfy.events.lastId";

const subscribers = new Set<HubEventListener>();
const statusSubscribers = new Set<HubStatusListener>();

let source: GuardianEventSource | null = null;
let sourceOpenListener: ((event: Event) => void) | null = null;
let sourceMessageListener: ((event: MessageEvent) => void) | null = null;
let sourceErrorListener: ((event: Event) => void) | null = null;
let sourceAbortController: AbortController | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pressureFlushTimer: ReturnType<typeof setTimeout> | null = null;
let pressureFlushRaf: number | null = null;

let activeConfig: LiveEventsHubConfig | null = null;
let activeConfigKey = "";

let readyState: 0 | 1 | 2 = GuardianEventSource.CLOSED;
let connectionStatus: HubConnectionStatus = "disconnected";
let connectAttempt = 0;
let retryMs = INITIAL_RETRY_MS;
let lastEventId: string | null = readStoredLastEventId();
let lastErrorAt: number | null = null;

const seenEventIds = new Set<string>();
const seenEventIdQueue: string[] = [];
const seenFallbackHashes = new Set<string>();
const seenFallbackHashQueue: string[] = [];
const perTypeSequence = new Map<string, number>();

const pressureTimestamps: number[] = [];
const bufferedEvents: LiveEventsHubEvent[] = [];
let pressureFuseActive = false;
let pressureLastHighAt = 0;

const lastLogByKey = new Map<string, number>();

function logThrottle(key: string, message: string, ttlMs = 2000): void {
  const now = Date.now();
  const previous = lastLogByKey.get(key) ?? 0;
  if (now - previous < ttlMs) return;
  lastLogByKey.set(key, now);
  console.info(message);
}

function readStoredLastEventId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = String(window.localStorage.getItem(LAST_EVENT_STORAGE_KEY) ?? "").trim();
    return raw.length > 0 ? raw : null;
  } catch {
    return null;
  }
}

function persistLastEventId(eventId: string): void {
  if (typeof window === "undefined" || !eventId) return;
  try {
    window.localStorage.setItem(LAST_EVENT_STORAGE_KEY, eventId);
  } catch {
    // no-op
  }
}

function buildSourceUrl(baseUrl: string): string {
  const resumeEventId = lastEventId ?? readStoredLastEventId();
  if (!resumeEventId) return baseUrl;
  const encoded = encodeURIComponent(resumeEventId);
  if (/[?&]last_id=/.test(baseUrl)) {
    return baseUrl.replace(/([?&])last_id=[^&]*/i, `$1last_id=${encoded}`);
  }
  const joiner = baseUrl.includes("?") ? "&" : "?";
  return `${baseUrl}${joiner}last_id=${encoded}`;
}

function buildConfigKey(config: LiveEventsHubConfig): string {
  const headerEntries = Object.entries(config.headers || {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}:${value}`)
    .join("|");
  return `${config.url}|${config.withCredentials ? "cred" : "anon"}|${headerEntries}`;
}

function statusSnapshot(): LiveEventsHubStatus {
  return {
    readyState,
    subscribers: subscribers.size,
    lastEventId,
    lastErrorAt,
    connectAttempt,
    retryMs,
    connectionStatus,
  };
}

function notifyStatus(): void {
  const snapshot = statusSnapshot();
  for (const listener of statusSubscribers) {
    try {
      listener(snapshot);
    } catch (error) {
      console.error("[live-events-hub] status listener failed", error);
    }
  }
}

function rememberBounded(value: string, set: Set<string>, queue: string[]): void {
  if (!value || set.has(value)) return;
  set.add(value);
  queue.push(value);
  while (queue.length > DEDUPE_LIMIT) {
    const removed = queue.shift();
    if (removed) set.delete(removed);
  }
}

function stringifyData(value: unknown): string {
  try {
    return JSON.stringify(value) ?? "";
  } catch {
    return String(value ?? "");
  }
}

function extractSequence(data: unknown): number | null {
  if (!data || typeof data !== "object") return null;
  const candidate = data as Record<string, unknown>;
  const keys = ["seq", "sequence", "event_seq", "version"];
  for (const key of keys) {
    const raw = candidate[key];
    const parsed = Number(raw);
    if (Number.isFinite(parsed)) return parsed;
  }
  const nested = candidate.data;
  if (nested && typeof nested === "object") {
    const nestedRecord = nested as Record<string, unknown>;
    for (const key of keys) {
      const raw = nestedRecord[key];
      const parsed = Number(raw);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function shouldDropEvent(event: LiveEventsHubEvent): boolean {
  const eventId = event.id ? String(event.id) : "";
  if (eventId) {
    if (seenEventIds.has(eventId)) return true;
    rememberBounded(eventId, seenEventIds, seenEventIdQueue);
  }

  const sequence = extractSequence(event.data);
  if (sequence != null) {
    const previous = perTypeSequence.get(event.type);
    if (previous != null && sequence <= previous) {
      return true;
    }
    perTypeSequence.set(event.type, sequence);
  }

  if (!eventId && sequence == null) {
    const hash = `${event.type}:${stringifyData(event.data)}`;
    if (seenFallbackHashes.has(hash)) return true;
    rememberBounded(hash, seenFallbackHashes, seenFallbackHashQueue);
  }

  return false;
}

function clearReconnectTimer(): void {
  if (!reconnectTimer) return;
  clearTimeout(reconnectTimer);
  reconnectTimer = null;
}

function clearPressureFlushTimer(): void {
  if (!pressureFlushTimer) return;
  clearTimeout(pressureFlushTimer);
  pressureFlushTimer = null;
}

function clearPressureFlushRaf(): void {
  if (pressureFlushRaf == null) return;
  if (typeof window !== "undefined" && typeof window.cancelAnimationFrame === "function") {
    window.cancelAnimationFrame(pressureFlushRaf);
  }
  pressureFlushRaf = null;
}

function pushPressureTimestamp(now: number): void {
  pressureTimestamps.push(now);
  while (
    pressureTimestamps.length > 0 &&
    now - pressureTimestamps[0] > EVENT_PRESSURE_WINDOW_MS
  ) {
    pressureTimestamps.shift();
  }
}

function updatePressureFuse(now: number): void {
  pushPressureTimestamp(now);
  const overPressure = pressureTimestamps.length > EVENT_PRESSURE_THRESHOLD;
  if (overPressure) {
    pressureLastHighAt = now;
    if (!pressureFuseActive) {
      pressureFuseActive = true;
      logThrottle(
        "fuse:enter",
        `[live-events-hub] event pressure fuse enabled (${pressureTimestamps.length} events/${EVENT_PRESSURE_WINDOW_MS}ms)`
      );
    }
    return;
  }
  if (!pressureFuseActive) return;
  if (now - pressureLastHighAt >= EVENT_PRESSURE_WINDOW_MS) {
    pressureFuseActive = false;
    logThrottle("fuse:exit", "[live-events-hub] event pressure fuse disabled");
  }
}

function dispatchEvent(event: LiveEventsHubEvent): void {
  for (const listener of subscribers) {
    try {
      listener(event);
    } catch (error) {
      console.error("[live-events-hub] subscriber failed", error);
    }
  }
}

function flushBufferedEvents(): void {
  pressureFlushTimer = null;
  if (!bufferedEvents.length) return;
  const nextBatch = bufferedEvents.splice(0, bufferedEvents.length);
  for (const event of nextBatch) {
    dispatchEvent(event);
  }
}

function scheduleBufferedFlush(): void {
  if (pressureFlushTimer || pressureFlushRaf != null) return;
  if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
    pressureFlushRaf = window.requestAnimationFrame(() => {
      pressureFlushRaf = null;
      flushBufferedEvents();
    });
    return;
  }
  pressureFlushTimer = setTimeout(() => {
    flushBufferedEvents();
  }, EVENT_PRESSURE_FLUSH_MS);
}

function publishEvent(event: LiveEventsHubEvent): void {
  const now = Date.now();
  updatePressureFuse(now);
  if (pressureFuseActive) {
    bufferedEvents.push(event);
    scheduleBufferedFlush();
    return;
  }
  dispatchEvent(event);
}

function parseEventData(raw: string): unknown {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function clearSourceListeners(boundSource: GuardianEventSource): void {
  if (sourceOpenListener) {
    boundSource.removeEventListener("open", sourceOpenListener as EventListener);
  }
  if (sourceMessageListener) {
    boundSource.removeEventListener(
      "message",
      sourceMessageListener as EventListener
    );
    for (const eventType of DEFAULT_EVENT_TYPES) {
      boundSource.removeEventListener(
        eventType,
        sourceMessageListener as EventListener
      );
    }
  }
  boundSource.onmessage = null;
  boundSource.onerror = null;
  sourceOpenListener = null;
  sourceMessageListener = null;
  sourceErrorListener = null;
}

function closeSource(): void {
  const existing = source;
  if (!existing) return;
  clearSourceListeners(existing);
  try {
    existing.close();
  } catch {
    // no-op
  }
  source = null;
  readyState = GuardianEventSource.CLOSED;
}

function hardReset(): void {
  clearReconnectTimer();
  clearPressureFlushTimer();
  clearPressureFlushRaf();
  bufferedEvents.splice(0, bufferedEvents.length);
  pressureTimestamps.splice(0, pressureTimestamps.length);
  pressureFuseActive = false;
  pressureLastHighAt = 0;
  seenEventIds.clear();
  seenEventIdQueue.splice(0, seenEventIdQueue.length);
  seenFallbackHashes.clear();
  seenFallbackHashQueue.splice(0, seenFallbackHashQueue.length);
  perTypeSequence.clear();
  sourceAbortController?.abort();
  sourceAbortController = null;
  closeSource();
  activeConfig = null;
  activeConfigKey = "";
  lastEventId = readStoredLastEventId();
  lastErrorAt = null;
  connectAttempt = 0;
  retryMs = INITIAL_RETRY_MS;
  connectionStatus = "disconnected";
  notifyStatus();
}

function scheduleReconnect(delayMs?: number): void {
  if (!activeConfig || subscribers.size === 0) return;
  if (reconnectTimer) return;

  const jitteredDelay = (() => {
    if (typeof delayMs === "number" && Number.isFinite(delayMs) && delayMs > 0) {
      return Math.max(250, Math.round(delayMs));
    }
    const baseDelay = Math.min(
      MAX_RETRY_MS,
      INITIAL_RETRY_MS * Math.pow(2, connectAttempt)
    );
    const jitterFactor = JITTER_MIN + Math.random() * (JITTER_MAX - JITTER_MIN);
    return Math.max(250, Math.round(baseDelay * jitterFactor));
  })();
  retryMs = jitteredDelay;
  connectAttempt += 1;
  notifyStatus();
  logThrottle(
    "hub:reconnect",
    `[live-events-hub] reconnect scheduled in ${jitteredDelay}ms (attempt ${connectAttempt})`,
    750
  );

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (!activeConfig || subscribers.size === 0) return;
    connect(activeConfig, true);
  }, jitteredDelay);
}

function connect(config: LiveEventsHubConfig, reconnecting: boolean): void {
  clearReconnectTimer();
  sourceAbortController?.abort();
  sourceAbortController = new AbortController();
  const abortSignal = sourceAbortController.signal;

  closeSource();
  activeConfig = config;
  activeConfigKey = buildConfigKey(config);
  connectionStatus = reconnecting || connectAttempt > 0 ? "reconnecting" : "connecting";
  readyState = GuardianEventSource.CONNECTING;
  notifyStatus();

  const outageDelay = getBackendOutageRemainingMs();
  if (outageDelay > 0) {
    readyState = GuardianEventSource.CLOSED;
    connectionStatus = "reconnecting";
    notifyStatus();
    logThrottle(
      "hub:outage",
      `[live-events-hub] backend outage active; reconnect delayed by ${outageDelay}ms`,
      1000
    );
    scheduleReconnect(outageDelay);
    return;
  }

  const next = new GuardianEventSource(buildSourceUrl(config.url), {
    headers: config.headers,
    withCredentials: config.withCredentials,
    onUnauthorized: config.onUnauthorized,
    autoReconnect: false,
  });
  source = next;

  sourceOpenListener = () => {
    if (abortSignal.aborted) return;
    readyState = GuardianEventSource.OPEN;
    connectionStatus = "connected";
    connectAttempt = 0;
    retryMs = INITIAL_RETRY_MS;
    notifyStatus();
    logThrottle("hub:open", "[live-events-hub] connected", 1000);
  };

  sourceMessageListener = (evt: MessageEvent) => {
    if (abortSignal.aborted) return;
    const payload: LiveEventsHubEvent = {
      id: evt.lastEventId || null,
      type: evt.type || "message",
      data: parseEventData(evt.data as string),
    };
    if (payload.id) {
      lastEventId = payload.id;
      persistLastEventId(payload.id);
    }
    if (shouldDropEvent(payload)) return;
    publishEvent(payload);
  };

  sourceErrorListener = () => {
    if (abortSignal.aborted) return;
    lastErrorAt = Date.now();
    readyState = GuardianEventSource.CLOSED;
    connectionStatus = "reconnecting";
    notifyStatus();
    closeSource();
    scheduleReconnect();
  };

  next.addEventListener("open", sourceOpenListener as EventListener);
  next.addEventListener("message", sourceMessageListener as EventListener);
  for (const eventType of DEFAULT_EVENT_TYPES) {
    next.addEventListener(eventType, sourceMessageListener as EventListener);
  }
  next.onerror = sourceErrorListener;
}

function ensureConnected(config: LiveEventsHubConfig): void {
  const nextKey = buildConfigKey(config);
  if (activeConfigKey && nextKey !== activeConfigKey) {
    connectAttempt = 0;
    retryMs = INITIAL_RETRY_MS;
    connect(config, false);
    return;
  }
  if (!source) {
    connect(config, false);
    return;
  }
  if (readyState === GuardianEventSource.CLOSED && !reconnectTimer) {
    connect(config, true);
  }
}

export function subscribeLiveEventsHub(
  config: LiveEventsHubConfig,
  listener: HubEventListener
): () => void {
  subscribers.add(listener);
  ensureConnected(config);
  notifyStatus();
  return () => {
    subscribers.delete(listener);
    notifyStatus();
    if (subscribers.size === 0) {
      hardReset();
    }
  };
}

export function subscribeLiveEventsHubStatus(
  listener: HubStatusListener
): () => void {
  statusSubscribers.add(listener);
  listener(statusSnapshot());
  return () => {
    statusSubscribers.delete(listener);
  };
}

export function getLiveEventsHubStatus(): LiveEventsHubStatus {
  return statusSnapshot();
}

export function __resetLiveEventsHubForTests(): void {
  hardReset();
}

if (typeof window !== "undefined" && (import.meta as any)?.env?.DEV) {
  window.__CFY_SSE_STATUS__ = getLiveEventsHubStatus;
}
