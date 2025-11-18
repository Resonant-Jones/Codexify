/**
 * Firefox DevTools Protocol Commands (STUB)
 *
 * This file contains placeholder FDP command implementations.
 * All functions return static placeholder values.
 */

import type { FDPSession } from "./session";

/**
 * FDP DOM Commands
 *
 * @remarks
 * DORMANT STUBS: All methods return placeholder values.
 */
export const DOMCommands = {
  /**
   * Get the root document node
   *
   * @param session - FDP session
   * @returns Root document node
   *
   * @remarks
   * TODO: Implement using Inspector.getWalker + DOMWalker.documentElement
   */
  async getDocument(session: FDPSession): Promise<Record<string, unknown>> {
    // DORMANT: Return placeholder
    return {
      nodeId: "placeholder-root",
      nodeType: 9,
      nodeName: "#document",
      error: "DORMANT: DOM commands not implemented"
    };
  },

  /**
   * Query selector in document
   *
   * @param session - FDP session
   * @param nodeId - Parent node ID
   * @param selector - CSS selector
   * @returns Matching node IDs
   *
   * @remarks
   * TODO: Implement using DOMWalker.querySelector
   */
  async querySelector(
    session: FDPSession,
    nodeId: string,
    selector: string
  ): Promise<string[]> {
    // DORMANT: Return empty array
    return [];
  },

  /**
   * Get outer HTML of node
   *
   * @param session - FDP session
   * @param nodeId - Node ID
   * @returns Outer HTML string
   *
   * @remarks
   * TODO: Implement using DOMNode.getOuterHTML
   */
  async getOuterHTML(session: FDPSession, nodeId: string): Promise<string> {
    // DORMANT: Return placeholder
    return "<!-- DORMANT: HTML not captured -->";
  }
};

/**
 * FDP CSS Commands
 *
 * @remarks
 * DORMANT STUBS: All methods return placeholder values.
 */
export const CSSCommands = {
  /**
   * Get computed styles for node
   *
   * @param session - FDP session
   * @param nodeId - Node ID
   * @returns Computed style properties
   *
   * @remarks
   * TODO: Implement using CSS.getComputedStyle
   */
  async getComputedStyle(
    session: FDPSession,
    nodeId: string
  ): Promise<Record<string, string>> {
    // DORMANT: Return empty object
    return {};
  },

  /**
   * Get applied styles and cascade for node
   *
   * @param session - FDP session
   * @param nodeId - Node ID
   * @returns CSS cascade information
   *
   * @remarks
   * TODO: Implement using CSS.getAppliedStyles
   */
  async getAppliedStyles(
    session: FDPSession,
    nodeId: string
  ): Promise<
    Array<{
      rule: string;
      selector: string;
      properties: Record<string, string>;
    }>
  > {
    // DORMANT: Return empty array
    return [];
  },

  /**
   * Get layout box model for node
   *
   * @param session - FDP session
   * @param nodeId - Node ID
   * @returns Box model (content, padding, border, margin)
   *
   * @remarks
   * TODO: Implement using CSS.getLayout
   */
  async getBoxModel(
    session: FDPSession,
    nodeId: string
  ): Promise<{
    content: number[];
    padding: number[];
    border: number[];
    margin: number[];
  }> {
    // DORMANT: Return empty box model
    return {
      content: [],
      padding: [],
      border: [],
      margin: []
    };
  }
};

/**
 * FDP Network Commands
 *
 * @remarks
 * DORMANT STUBS: All methods return placeholder values.
 */
export const NetworkCommands = {
  /**
   * Get network activity for current page
   *
   * @param session - FDP session
   * @returns List of network requests
   *
   * @remarks
   * TODO: Implement using Network.getRequestLog
   */
  async getNetworkActivity(
    session: FDPSession
  ): Promise<
    Array<{
      url: string;
      method: string;
      status: number;
      timing: Record<string, number>;
    }>
  > {
    // DORMANT: Return empty array
    return [];
  },

  /**
   * Get HAR (HTTP Archive) data
   *
   * @param session - FDP session
   * @returns HAR format network log
   *
   * @remarks
   * TODO: Implement using Network.getHARLog
   */
  async getHAR(session: FDPSession): Promise<Record<string, unknown>> {
    // DORMANT: Return placeholder HAR
    return {
      log: {
        version: "1.2",
        creator: { name: "SCOUT-FDP", version: "0.1.0" },
        entries: []
      }
    };
  }
};

/**
 * FDP Console Commands
 *
 * @remarks
 * DORMANT STUBS: All methods return placeholder values.
 */
export const ConsoleCommands = {
  /**
   * Get console messages
   *
   * @param session - FDP session
   * @returns Console log messages
   *
   * @remarks
   * TODO: Implement using Console.getCachedMessages
   */
  async getMessages(
    session: FDPSession
  ): Promise<
    Array<{
      level: string;
      text: string;
      timestamp: number;
    }>
  > {
    // DORMANT: Return empty array
    return [];
  }
};

/**
 * FDP Performance Commands
 *
 * @remarks
 * DORMANT STUBS: All methods return placeholder values.
 */
export const PerformanceCommands = {
  /**
   * Get performance metrics
   *
   * @param session - FDP session
   * @returns Performance timing data
   *
   * @remarks
   * TODO: Implement using Performance.getMetrics
   */
  async getMetrics(session: FDPSession): Promise<Record<string, number>> {
    // DORMANT: Return empty object
    return {};
  }
};

// TODO: Implement Storage commands (cookies, localStorage, indexedDB)
// TODO: Implement Debugger commands (breakpoints, stepping, evaluation)
// TODO: Implement Accessibility commands (a11y tree inspection)
// TODO: Add error handling for all command types
// TODO: Add retry logic for transient failures
