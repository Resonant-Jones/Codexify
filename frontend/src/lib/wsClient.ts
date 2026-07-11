/**
 * Plain TypeScript WebSocket client with auto-reconnect, ping/pong keepalive,
 * and typed event dispatch. No framework dependencies.
 *
 * Used by CollaborativeNote (document editing) and reusable for future
 * Codexify collaboration surfaces.
 */

export type WsConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "closed";

export interface WsClientOptions {
  /** Maximum number of reconnect attempts before giving up. Default 5. */
  maxReconnectAttempts?: number;
  /** Initial reconnect delay in milliseconds. Default 1000. */
  baseReconnectDelayMs?: number;
  /** Maximum reconnect delay in milliseconds (capped exponential backoff). Default 15000. */
  maxReconnectDelayMs?: number;
  /** Ping interval in milliseconds. Default 30000. */
  pingIntervalMs?: number;
  /** Optional authentication token appended as a query parameter. */
  token?: string;
  /** Called when the server closes with code 1008 (policy violation / access denied). */
  onUnauthorized?: () => void;
  /** Return false to suppress reconnect for a specific close event. Default allows all non-1008 closes. */
  shouldReconnect?: (event: CloseEvent) => boolean;
}

type EventHandler = (data: unknown) => void;

const DEFAULT_MAX_RECONNECT_ATTEMPTS = 5;
const DEFAULT_BASE_RECONNECT_DELAY_MS = 1_000;
const DEFAULT_MAX_RECONNECT_DELAY_MS = 15_000;
const DEFAULT_PING_INTERVAL_MS = 30_000;

export class WsClient {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<EventHandler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private url = "";
  private options: Required<WsClientOptions>;
  private manualClose = false;
  private _status: WsConnectionStatus = "idle";

  readonly isConnected: boolean = false;

  /** Current connection status. */
  get status(): WsConnectionStatus {
    return this._status;
  }

  /** Called when connected/disconnected state changes. */
  onConnectionChange?: (connected: boolean) => void;

  /** Called when the connection status transitions. */
  onStatusChange?: (status: WsConnectionStatus) => void;

  constructor(url: string, options?: WsClientOptions) {
    this.url = url;
    this.options = {
      maxReconnectAttempts:
        options?.maxReconnectAttempts ?? DEFAULT_MAX_RECONNECT_ATTEMPTS,
      baseReconnectDelayMs:
        options?.baseReconnectDelayMs ?? DEFAULT_BASE_RECONNECT_DELAY_MS,
      maxReconnectDelayMs:
        options?.maxReconnectDelayMs ?? DEFAULT_MAX_RECONNECT_DELAY_MS,
      pingIntervalMs:
        options?.pingIntervalMs ?? DEFAULT_PING_INTERVAL_MS,
      token: options?.token ?? "",
      onUnauthorized: options?.onUnauthorized ?? (() => {}),
      shouldReconnect: options?.shouldReconnect ?? (() => true),
    };
  }

  /** Open a WebSocket connection. Idempotent if already open. */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.manualClose = false;

    const privatePreview = import.meta.env.VITE_PRIVATE_PREVIEW === "true";
    let fullUrl = this.url;
    if (this.options.token && !privatePreview) {
      const separator = fullUrl.includes("?") ? "&" : "?";
      fullUrl = `${fullUrl}${separator}token=${encodeURIComponent(this.options.token)}`;
    }

    this.setStatus("connecting");
    this.ws = new WebSocket(fullUrl);

    this.ws.onopen = () => {
      // Authenticate in the first protocol frame instead of exposing the
      // session token in a URL, where it would reach proxy and browser logs.
      if (this.options.token && privatePreview) {
        this.ws?.send(JSON.stringify({ type: "auth", token: this.options.token }));
      }
      this.reconnectAttempts = 0;
      this.setConnected(true);
    };

    this.ws.onmessage = (event: MessageEvent) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(event.data as string);
      } catch {
        this.dispatch("error", {
          type: "error",
          code: "parse_error",
          message: "Failed to parse WebSocket message",
          raw: typeof event.data === "string" ? event.data.slice(0, 200) : null,
        });
        return;
      }

      // Always dispatch to "message" catch-all
      this.dispatch("message", parsed);

      // If the parsed payload has a `type` field, dispatch to that specific event type
      if (
        parsed &&
        typeof parsed === "object" &&
        "type" in parsed &&
        typeof (parsed as Record<string, unknown>).type === "string"
      ) {
        const eventType = (parsed as Record<string, unknown>).type as string;
        this.dispatch(eventType, parsed);
      }
    };

    this.ws.onerror = () => {
      this.dispatch("error", {
        type: "error",
        code: "socket_error",
        message: "WebSocket connection error",
      });
      // The browser will fire onclose after onerror; let onclose handle state
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.setConnected(false);

      // Code 1008 = policy violation (access denied)
      if (event.code === 1008) {
        this.setStatus("closed");
        this.options.onUnauthorized();
        this.cleanup();
        return;
      }

      if (this.manualClose) {
        this.setStatus("closed");
        this.cleanup();
        return;
      }

      // Let the caller veto reconnection
      if (!this.options.shouldReconnect(event)) {
        this.setStatus("closed");
        this.cleanup();
        return;
      }

      this.scheduleReconnect();
    };
  }

  /**
   * Gracefully disconnect. Suppresses auto-reconnect and cleans up timers.
   * The status transitions to "closed".
   */
  disconnect(): void {
    this.manualClose = true;
    this.clearReconnectTimer();
    this.stopPing();
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    ) {
      this.ws.close(1000, "Client disconnect");
    }
    this.ws = null;
    this.setStatus("closed");
  }

  /**
   * Send a JSON payload. Silently no-ops when the socket is not open.
   */
  send(payload: unknown): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(payload));
  }

  /**
   * Subscribe to events by type. Returns an unsubscribe function.
   *
   * Event types:
   * - Any `type` field value from server messages (e.g., "presence.join", "update")
   * - `"message"` — dispatched for every parsed server message
   * - `"error"` — dispatched on parse failures or socket errors
   */
  on(eventType: string, handler: EventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
    return () => this.off(eventType, handler);
  }

  private off(eventType: string, handler: EventHandler): void {
    this.handlers.get(eventType)?.delete(handler);
  }

  private dispatch(eventType: string, data: unknown): void {
    this.handlers.get(eventType)?.forEach((handler) => {
      try {
        handler(data);
      } catch {
        // Swallow handler errors to prevent one bad listener from breaking others
      }
    });
  }

  private setConnected(connected: boolean): void {
    (this as { isConnected: boolean }).isConnected = connected;
    this.setStatus(connected ? "connected" : "disconnected");
    this.onConnectionChange?.(connected);

    if (connected) {
      this.startPing();
    } else {
      this.stopPing();
    }
  }

  private setStatus(status: WsConnectionStatus): void {
    if (this._status === status) return;
    this._status = status;
    this.onStatusChange?.(status);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, this.options.pingIntervalMs);
  }

  private stopPing(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      this.setStatus("closed");
      this.cleanup();
      return;
    }

    this.setStatus("reconnecting");

    const delay = Math.min(
      this.options.baseReconnectDelayMs *
        Math.pow(2, this.reconnectAttempts),
      this.options.maxReconnectDelayMs
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private cleanup(): void {
    this.clearReconnectTimer();
    this.stopPing();
    this.ws = null;
  }
}
