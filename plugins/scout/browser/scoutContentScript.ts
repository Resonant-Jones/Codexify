/**
 * SCOUT Content Script
 *
 * Runs in the context of web pages to capture DOM, console logs,
 * network activity, and other page-level data.
 *
 * This is a STUB implementation that does minimal work.
 *
 * @module scout/browser/scoutContentScript
 */

import {
  ScoutMessageType,
  createMessage,
  sendMessage,
  isValidScoutMessage,
  type ScoutMessage,
  type ScoutDOMScanRequest
} from "./scoutMessaging";

/**
 * Content script state
 */
const state = {
  active: false,
  initialized: false,
  listeners: new Map<string, Function>()
};

/**
 * Initialize the content script
 *
 * This is a STUB that does nothing.
 *
 * TODO: Set up message listeners
 * TODO: Inject observers for DOM mutations
 * TODO: Hook console methods for capture
 * TODO: Monitor network via Performance API
 * TODO: Set up CDP integration
 */
function initialize(): void {
  if (state.initialized) {
    return;
  }

  console.debug("[SCOUT] Content script stub loaded (inactive)");

  // TODO: Set up message listener
  // browser.runtime.onMessage.addListener(handleMessage);

  // TODO: Set up DOM mutation observer
  // setupDOMObserver();

  // TODO: Hook console methods
  // hookConsoleMethods();

  // TODO: Set up performance observer
  // setupPerformanceObserver();

  state.initialized = true;
}

/**
 * Handle incoming messages from background script
 *
 * This is a STUB implementation.
 *
 * @param message - Incoming message
 * @returns Response or void
 */
async function handleMessage(message: unknown): Promise<ScoutMessage | void> {
  if (!isValidScoutMessage(message)) {
    console.warn("[SCOUT] Invalid message received:", message);
    return;
  }

  console.debug("[SCOUT] Received message:", message.type);

  switch (message.type) {
    case ScoutMessageType.SCOUT_SCAN_DOM:
      return handleDOMScan(message as ScoutDOMScanRequest);

    case ScoutMessageType.SCOUT_CAPTURE_CONSOLE:
      return handleConsoleCaptureRequest();

    case ScoutMessageType.SCOUT_CAPTURE_NETWORK:
      return handleNetworkCaptureRequest();

    case ScoutMessageType.SCOUT_CAPTURE_PERFORMANCE:
      return handlePerformanceCaptureRequest();

    default:
      console.warn("[SCOUT] Unknown message type:", message.type);
  }
}

/**
 * Handle DOM scan request
 *
 * This is a STUB that returns basic DOM data.
 *
 * TODO: Implement comprehensive DOM capture
 * TODO: Add computed styles capture
 * TODO: Add event listener enumeration
 * TODO: Add shadow DOM traversal
 * TODO: Add iframe content capture
 * TODO: Integrate with CDP for deeper access
 *
 * @param request - DOM scan request
 * @returns DOM data response
 */
async function handleDOMScan(
  request: ScoutDOMScanRequest
): Promise<ScoutMessage> {
  try {
    // Basic DOM capture - just get outerHTML
    const html = document.documentElement.outerHTML;

    const response = createMessage(
      ScoutMessageType.SCOUT_DOM_DATA,
      {
        url: window.location.href,
        html,
        meta: {
          title: document.title,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          },
          userAgent: navigator.userAgent
        }
      },
      {
        source: "content-script"
      }
    );

    return response;
  } catch (error) {
    // Return error message
    return createMessage(
      ScoutMessageType.SCOUT_ERROR,
      {
        error: `DOM scan failed: ${error instanceof Error ? error.message : String(error)}`,
        code: "DOM_SCAN_ERROR"
      },
      {
        source: "content-script"
      }
    );
  }
}

/**
 * Handle console capture request
 *
 * TODO: Implement console log buffering and capture
 *
 * @returns Console data response
 */
async function handleConsoleCaptureRequest(): Promise<ScoutMessage> {
  return createMessage(
    ScoutMessageType.SCOUT_CONSOLE_DATA,
    {
      logs: [],
      note: "Console capture not implemented (stub)"
    },
    {
      source: "content-script"
    }
  );
}

/**
 * Handle network capture request
 *
 * TODO: Implement network activity capture via Performance API
 * TODO: Add CDP network monitoring integration
 *
 * @returns Network data response
 */
async function handleNetworkCaptureRequest(): Promise<ScoutMessage> {
  return createMessage(
    ScoutMessageType.SCOUT_NETWORK_DATA,
    {
      requests: [],
      note: "Network capture not implemented (stub)"
    },
    {
      source: "content-script"
    }
  );
}

/**
 * Handle performance capture request
 *
 * TODO: Implement performance metrics capture
 * TODO: Add Web Vitals integration
 *
 * @returns Performance data response
 */
async function handlePerformanceCaptureRequest(): Promise<ScoutMessage> {
  return createMessage(
    ScoutMessageType.SCOUT_PERFORMANCE_DATA,
    {
      metrics: {},
      note: "Performance capture not implemented (stub)"
    },
    {
      source: "content-script"
    }
  );
}

/**
 * Cleanup on unload
 */
function cleanup(): void {
  console.debug("[SCOUT] Content script cleanup (stub)");

  // TODO: Remove event listeners
  // TODO: Disconnect observers
  // TODO: Restore console methods

  state.initialized = false;
  state.active = false;
}

// Initialize if in browser context
if (typeof window !== "undefined" && typeof document !== "undefined") {
  initialize();
}

// Cleanup on unload
if (typeof window !== "undefined") {
  window.addEventListener("unload", cleanup);
}

/**
 * Export for testing/manual invocation
 */
export {
  initialize,
  handleMessage,
  cleanup,
  state
};
