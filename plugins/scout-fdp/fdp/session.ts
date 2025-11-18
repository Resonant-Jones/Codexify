/**
 * Firefox DevTools Protocol Session (STUB)
 *
 * This file contains a placeholder session abstraction for FDP communication.
 * NO actual commands are sent.
 */

/**
 * FDP Command Request
 */
export interface FDPCommand {
  /** Target actor ID */
  to: string;
  /** Command type */
  type: string;
  /** Command parameters */
  [key: string]: unknown;
}

/**
 * FDP Command Response
 */
export interface FDPResponse {
  /** Source actor ID */
  from: string;
  /** Response data */
  [key: string]: unknown;
}

/**
 * FDP Event
 */
export interface FDPEvent {
  /** Event type */
  type: string;
  /** Source actor ID */
  from: string;
  /** Event data */
  [key: string]: unknown;
}

/**
 * FDP Session
 *
 * Manages a connection to Firefox DevTools Protocol.
 *
 * @remarks
 * DORMANT STUB: All methods return placeholder values.
 */
export class FDPSession {
  private connected: boolean = false;
  private actorId: string = "root";

  /**
   * Create a new FDP session
   *
   * @param ws - WebSocket connection (unused in stub)
   */
  constructor(ws?: unknown) {
    // DORMANT: No initialization
    // TODO: Store WebSocket reference
    // TODO: Set up message handlers
    // TODO: Initialize actor registry
  }

  /**
   * Send a command to Firefox DevTools
   *
   * @param command - FDP command object
   * @returns Command response
   *
   * @remarks
   * DORMANT STUB: Returns placeholder response.
   *
   * TODO: Future implementation should:
   * - Serialize command to JSON
   * - Send via WebSocket
   * - Wait for response with matching ID
   * - Handle errors and timeouts
   */
  async sendCommand(command: FDPCommand): Promise<FDPResponse> {
    // DORMANT: No actual command sending
    // TODO: Implement command dispatch
    return {
      from: this.actorId,
      error: "DORMANT: Session is not active"
    };
  }

  /**
   * Subscribe to FDP events
   *
   * @param eventType - Event type to listen for
   * @param handler - Event handler callback
   *
   * @remarks
   * DORMANT STUB: Does nothing.
   *
   * TODO: Future implementation should:
   * - Register event handler
   * - Filter incoming events by type
   * - Invoke handler with event data
   */
  on(eventType: string, handler: (event: FDPEvent) => void): void {
    // DORMANT: No event subscription
    // TODO: Implement event subscription
  }

  /**
   * Unsubscribe from FDP events
   *
   * @param eventType - Event type to stop listening for
   * @param handler - Event handler to remove
   */
  off(eventType: string, handler: (event: FDPEvent) => void): void {
    // DORMANT: No event unsubscription
    // TODO: Implement event unsubscription
  }

  /**
   * Close the FDP session
   *
   * @remarks
   * DORMANT STUB: Does nothing.
   *
   * TODO: Future implementation should:
   * - Close WebSocket connection
   * - Clean up event listeners
   * - Release actor references
   */
  close(): void {
    this.connected = false;
    // DORMANT: No cleanup needed
    // TODO: Implement session cleanup
  }

  /**
   * Check if session is connected
   *
   * @returns Connection status
   */
  isConnected(): boolean {
    return this.connected;
  }

  /**
   * Get root actor ID
   *
   * @returns Actor ID
   */
  getActorId(): string {
    return this.actorId;
  }
}

// TODO: Add request ID tracking for command/response correlation
// TODO: Add command timeout handling
// TODO: Add automatic reconnection on connection loss
// TODO: Add actor lifecycle management (attach/detach)
// TODO: Add batch command support for performance
