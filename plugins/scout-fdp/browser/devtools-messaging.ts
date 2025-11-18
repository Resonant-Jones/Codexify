/**
 * SCOUT-FDP DevTools Messaging Protocol (STUB)
 *
 * This file defines the message protocol between DevTools components.
 * Currently dormant - no active messaging.
 */

/**
 * Message Types
 *
 * @remarks
 * These constants define the protocol for communication between:
 * - DevTools panel
 * - Background service
 * - Content scripts
 */

// Scan-related messages
export const FDP_SCAN_DOM = "FDP_SCAN_DOM";
export const FDP_SCAN_CSS = "FDP_SCAN_CSS";
export const FDP_SCAN_NETWORK = "FDP_SCAN_NETWORK";
export const FDP_SCAN_COMPLETE = "FDP_SCAN_COMPLETE";
export const FDP_SCAN_ERROR = "FDP_SCAN_ERROR";

// Session-related messages
export const FDP_SESSION_CONNECT = "FDP_SESSION_CONNECT";
export const FDP_SESSION_DISCONNECT = "FDP_SESSION_DISCONNECT";
export const FDP_SESSION_STATUS = "FDP_SESSION_STATUS";

// Export-related messages
export const FDP_EXPORT_LOG = "FDP_EXPORT_LOG";
export const FDP_EXPORT_COMPLETE = "FDP_EXPORT_COMPLETE";

// Settings-related messages
export const FDP_SETTINGS_UPDATE = "FDP_SETTINGS_UPDATE";
export const FDP_SETTINGS_GET = "FDP_SETTINGS_GET";

/**
 * Message Interface
 */
export interface FDPMessage {
  /** Message type (one of the constants above) */
  type: string;
  /** Message payload */
  payload?: unknown;
  /** Target tab ID */
  tabId?: number;
  /** Request ID for correlation */
  requestId?: string;
}

/**
 * Scan Request Message
 */
export interface FDPScanRequest extends FDPMessage {
  type:
    | typeof FDP_SCAN_DOM
    | typeof FDP_SCAN_CSS
    | typeof FDP_SCAN_NETWORK;
  payload: {
    /** URL to scan */
    url: string;
    /** Scan options */
    options?: {
      includeStyles?: boolean;
      includeNetwork?: boolean;
      sanitize?: boolean;
    };
  };
}

/**
 * Scan Response Message
 */
export interface FDPScanResponse extends FDPMessage {
  type: typeof FDP_SCAN_COMPLETE | typeof FDP_SCAN_ERROR;
  payload: {
    /** Scan results */
    data?: unknown;
    /** Error message if failed */
    error?: string;
  };
}

/**
 * Send FDP Message
 *
 * @param message - Message to send
 * @returns Promise resolving to response
 *
 * @remarks
 * DORMANT STUB: Does not send actual messages.
 *
 * TODO: Future implementation should:
 * - Validate message format
 * - Send via browser.runtime.sendMessage (Firefox API)
 * - Wait for response with matching requestId
 * - Handle timeouts and errors
 */
export function sendFDPMessage(message: FDPMessage): Promise<FDPMessage> {
  // DORMANT: No actual messaging
  console.log("[SCOUT-FDP] Message send inactive (dormant)", message);

  return Promise.resolve({
    type: FDP_SCAN_ERROR,
    payload: {
      error: "DORMANT: Messaging not implemented"
    },
    requestId: message.requestId
  });
}

/**
 * Listen for FDP Messages
 *
 * @param handler - Message handler callback
 *
 * @remarks
 * DORMANT STUB: Does not register actual listener.
 *
 * TODO: Future implementation should:
 * - Register browser.runtime.onMessage listener
 * - Filter messages by type
 * - Validate message format
 * - Invoke handler with message and sendResponse
 */
export function onFDPMessage(
  handler: (message: FDPMessage) => void | Promise<FDPMessage>
): void {
  // DORMANT: No actual listener registration
  console.log("[SCOUT-FDP] Message listener inactive (dormant)");

  // TODO: Implement message listener
  // browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  //   if (isFDPMessage(msg)) {
  //     handler(msg);
  //   }
  // });
}

/**
 * Generate request ID
 *
 * @returns Unique request ID
 */
export function generateRequestId(): string {
  return `fdp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Validate FDP message format
 *
 * @param message - Message to validate
 * @returns Whether message is valid
 */
export function isFDPMessage(message: unknown): message is FDPMessage {
  if (typeof message !== "object" || message === null) {
    return false;
  }

  const msg = message as Record<string, unknown>;
  return typeof msg.type === "string" && msg.type.startsWith("FDP_");
}

// TODO: Add message encryption for sensitive data
// TODO: Add message compression for large payloads
// TODO: Add retry logic for failed messages
// TODO: Add message queue for offline scenarios
// TODO: Add message priority system
