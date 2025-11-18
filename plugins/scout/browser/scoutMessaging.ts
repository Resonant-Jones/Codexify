/**
 * SCOUT Browser Messaging Protocol
 *
 * Defines message types and utilities for communication between
 * content scripts, background workers, and the main application.
 *
 * This is a STUB implementation defining the message protocol only.
 *
 * @module scout/browser/scoutMessaging
 */

/**
 * Scout message types
 */
export enum ScoutMessageType {
  /** Request to scan the current DOM */
  SCOUT_SCAN_DOM = "scout:scan:dom",

  /** Response with scanned DOM data */
  SCOUT_DOM_DATA = "scout:dom:data",

  /** Request to capture console logs */
  SCOUT_CAPTURE_CONSOLE = "scout:capture:console",

  /** Response with console log data */
  SCOUT_CONSOLE_DATA = "scout:console:data",

  /** Request to capture network activity */
  SCOUT_CAPTURE_NETWORK = "scout:capture:network",

  /** Response with network activity data */
  SCOUT_NETWORK_DATA = "scout:network:data",

  /** Request to capture performance metrics */
  SCOUT_CAPTURE_PERFORMANCE = "scout:capture:performance",

  /** Response with performance data */
  SCOUT_PERFORMANCE_DATA = "scout:performance:data",

  /** Error occurred during capture */
  SCOUT_ERROR = "scout:error",

  /** Acknowledgment */
  SCOUT_ACK = "scout:ack"
}

/**
 * Base message structure
 */
export interface ScoutMessage {
  /** Message type */
  type: ScoutMessageType;

  /** Unique message ID */
  id: string;

  /** Timestamp */
  timestamp: string;

  /** Message payload */
  payload: unknown;

  /** Optional metadata */
  meta?: {
    /** Source of the message */
    source?: "content-script" | "background" | "app";

    /** Target for the message */
    target?: "content-script" | "background" | "app";

    /** Tab ID (if applicable) */
    tabId?: number;
  };
}

/**
 * DOM scan request
 */
export interface ScoutDOMScanRequest extends ScoutMessage {
  type: ScoutMessageType.SCOUT_SCAN_DOM;
  payload: {
    /** Whether to include computed styles */
    includeStyles?: boolean;

    /** Whether to include event listeners */
    includeListeners?: boolean;

    /** Maximum depth to traverse */
    maxDepth?: number;
  };
}

/**
 * DOM data response
 */
export interface ScoutDOMDataResponse extends ScoutMessage {
  type: ScoutMessageType.SCOUT_DOM_DATA;
  payload: {
    /** URL of the page */
    url: string;

    /** Raw HTML content */
    html: string;

    /** Optional metadata */
    meta?: {
      title?: string;
      viewport?: { width: number; height: number };
      userAgent?: string;
    };
  };
}

/**
 * Error message
 */
export interface ScoutErrorMessage extends ScoutMessage {
  type: ScoutMessageType.SCOUT_ERROR;
  payload: {
    /** Error message */
    error: string;

    /** Error code */
    code?: string;

    /** Stack trace (if available) */
    stack?: string;
  };
}

/**
 * Send a Scout message
 *
 * This is a STUB implementation that does nothing.
 *
 * TODO: Implement actual message sending via browser APIs
 * TODO: Add retry logic
 * TODO: Add timeout handling
 * TODO: Add response waiting/promises
 *
 * @param message - Message to send
 * @returns Promise that resolves when message is sent
 */
export async function sendMessage(message: ScoutMessage): Promise<void> {
  // Stub - does nothing
  console.debug("[SCOUT] Message stub (inactive):", message.type);

  // TODO: Implement browser.runtime.sendMessage
  // TODO: Handle response
  // TODO: Add error handling

  return Promise.resolve();
}

/**
 * Generate a unique message ID
 *
 * @returns Unique message ID
 */
export function generateMessageId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 9);
  return `msg_${timestamp}_${random}`;
}

/**
 * Create a Scout message
 *
 * @param type - Message type
 * @param payload - Message payload
 * @param meta - Optional metadata
 * @returns Scout message
 */
export function createMessage(
  type: ScoutMessageType,
  payload: unknown,
  meta?: ScoutMessage["meta"]
): ScoutMessage {
  return {
    type,
    id: generateMessageId(),
    timestamp: new Date().toISOString(),
    payload,
    meta
  };
}

/**
 * Validate a Scout message
 *
 * @param message - Message to validate
 * @returns Whether message is valid
 */
export function isValidScoutMessage(message: unknown): message is ScoutMessage {
  if (!message || typeof message !== "object") {
    return false;
  }

  const m = message as Partial<ScoutMessage>;

  return Boolean(
    m.type &&
    m.id &&
    m.timestamp &&
    Object.values(ScoutMessageType).includes(m.type as ScoutMessageType)
  );
}
