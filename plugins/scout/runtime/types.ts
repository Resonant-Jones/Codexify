/**
 * SCOUT Runtime Type Definitions
 *
 * Core types for the dormant SCOUT inspection plugin.
 * These types define the shape of data structures used throughout
 * the plugin, following Codexify's type conventions.
 *
 * @module scout/runtime/types
 */

/**
 * Raw payload captured from browser environment
 *
 * This represents unprocessed data before sanitization.
 */
export interface ScoutRawPayload {
  /** Timestamp of capture (ISO 8601) */
  timestamp: string;

  /** URL where data was captured */
  url: string;

  /** Raw DOM content (HTML string) */
  dom: string;

  /** Optional metadata from browser context */
  meta?: {
    /** User agent string */
    userAgent?: string;

    /** Viewport dimensions */
    viewport?: {
      width: number;
      height: number;
    };

    /** Performance metrics */
    performance?: {
      loadTime?: number;
      domContentLoaded?: number;
    };
  };

  /** Optional console logs captured */
  consoleLogs?: Array<{
    level: "log" | "warn" | "error" | "info" | "debug";
    message: string;
    timestamp: string;
  }>;

  /** Optional network activity summary */
  network?: {
    requests?: number;
    errors?: number;
  };
}

/**
 * Redaction summary tracking what was sanitized
 */
export interface RedactionSummary {
  /** Number of fields that were masked */
  fieldsMasked: number;

  /** Number of tokens that were masked */
  tokensMasked: number;

  /** Types of PII detected and redacted */
  detectedPatterns: string[];

  /** Redaction strategy used */
  strategy: "regex" | "ml" | "manual" | "none";

  /** Whether redaction was successful */
  success: boolean;

  /** Any warnings or errors during redaction */
  warnings?: string[];
}

/**
 * Processed and sanitized Scout log
 *
 * This is the final structure stored in IDDB and analyzed by personas.
 */
export interface ScoutLog {
  /** Unique identifier for this log */
  id: string;

  /** Metadata about the log */
  meta: {
    /** Timestamp of capture (ISO 8601) */
    timestamp: string;

    /** URL where data was captured */
    url: string;

    /** Plugin version that created this log */
    scoutVersion: string;

    /** Log schema version */
    schemaVersion: "0.1.0";
  };

  /** Sanitized DOM content */
  dom: {
    /** HTML content after sanitization */
    html: string;

    /** DOM tree statistics */
    stats?: {
      elementCount?: number;
      depth?: number;
      size?: number; // bytes
    };
  };

  /** Redaction information */
  redaction: RedactionSummary;

  /** Optional extracted insights */
  insights?: {
    /** Forms detected */
    forms?: number;

    /** Interactive elements */
    interactive?: number;

    /** External resources */
    externalResources?: number;
  };

  /** Processing metadata */
  processing: {
    /** When this log was processed */
    processedAt: string;

    /** Processing duration in milliseconds */
    duration: number;

    /** Any processing errors */
    errors?: string[];
  };
}

/**
 * Runtime configuration for Scout processing
 */
export interface ScoutRuntimeConfig {
  /** Enable sanitization */
  sanitize: boolean;

  /** Redaction strategy to use */
  redactionStrategy: "regex" | "ml" | "manual" | "none";

  /** Maximum DOM size to process (bytes) */
  maxDomSize: number;

  /** Enable console log capture */
  captureConsoleLogs: boolean;

  /** Enable network activity tracking */
  captureNetwork: boolean;
}

/**
 * Result of Scout payload processing
 */
export interface ScoutProcessingResult {
  /** Processing success status */
  success: boolean;

  /** Generated ScoutLog (if successful) */
  log?: ScoutLog;

  /** Error message (if failed) */
  error?: string;

  /** Processing warnings */
  warnings?: string[];
}
