/**
 * SCOUT-FDP Runtime Types
 *
 * Type definitions for Scout-FDP runtime processing.
 */

/**
 * Scout Raw Payload
 *
 * Raw data captured from Firefox DevTools Protocol.
 */
export interface ScoutRawPayload {
  /** Capture timestamp */
  timestamp: number;
  /** Target URL */
  url: string;
  /** FDP metadata */
  fdpMetadata?: {
    /** Firefox version */
    firefoxVersion?: string;
    /** FDP protocol version */
    protocolVersion?: string;
    /** Actor IDs used in capture */
    actorIds?: string[];
  };
  /** Raw DOM data */
  dom?: {
    /** Document root */
    root?: unknown;
    /** Serialized HTML */
    html?: string;
    /** DOM statistics */
    stats?: {
      nodeCount?: number;
      depth?: number;
    };
  };
  /** Raw CSS data */
  css?: {
    /** Computed styles map */
    computedStyles?: Record<string, Record<string, string>>;
    /** Applied rules and cascade */
    cascade?: Array<{
      nodeId: string;
      rules: Array<{
        selector: string;
        properties: Record<string, string>;
        source?: string;
      }>;
    }>;
    /** Layout box models */
    boxModels?: Record<
      string,
      {
        content: number[];
        padding: number[];
        border: number[];
        margin: number[];
      }
    >;
  };
  /** Raw network data */
  network?: {
    /** HAR log */
    har?: unknown;
    /** Request summary */
    requests?: Array<{
      url: string;
      method: string;
      status: number;
      timing?: Record<string, number>;
    }>;
  };
  /** Console logs */
  console?: Array<{
    level: string;
    text: string;
    timestamp: number;
  }>;
  /** Performance metrics */
  performance?: Record<string, number>;
}

/**
 * Scout Log
 *
 * Processed and sanitized Scout log ready for export.
 */
export interface ScoutLog {
  /** Log schema version */
  version: string;
  /** Generation timestamp */
  generatedAt: string;
  /** Source protocol */
  protocol: "fdp";
  /** Target URL */
  url: string;
  /** Page title */
  title?: string;
  /** FDP-specific metadata */
  fdpMetadata?: {
    firefoxVersion?: string;
    protocolVersion?: string;
  };
  /** Sanitized HTML snapshot */
  html?: string;
  /** CSS data */
  css?: {
    /** Computed styles */
    computedStyles?: Record<string, Record<string, string>>;
    /** Cascade information */
    cascade?: Array<{
      selector: string;
      properties: Record<string, string>;
    }>;
  };
  /** Network summary */
  network?: {
    requestCount?: number;
    totalBytes?: number;
    requests?: Array<{
      url: string;
      method: string;
      status: number;
    }>;
  };
  /** Redaction summary */
  redaction?: RedactionSummary;
  /** Processing metadata */
  processingMetadata?: {
    /** Processing duration in ms */
    durationMs?: number;
    /** Warnings during processing */
    warnings?: string[];
  };
}

/**
 * Redaction Summary
 *
 * Summary of PII and sensitive data redaction.
 */
export interface RedactionSummary {
  /** Whether redaction was applied */
  applied: boolean;
  /** Redaction statistics */
  stats?: {
    /** Number of emails redacted */
    emailsRedacted?: number;
    /** Number of phone numbers redacted */
    phoneNumbersRedacted?: number;
    /** Number of credit card numbers redacted */
    creditCardsRedacted?: number;
    /** Number of API keys redacted */
    apiKeysRedacted?: number;
    /** Number of other sensitive values redacted */
    otherRedacted?: number;
  };
  /** Redaction timestamp */
  timestamp?: string;
}

/**
 * Processing Options
 *
 * Options for Scout payload processing.
 */
export interface ProcessingOptions {
  /** Enable HTML sanitization */
  sanitize?: boolean;
  /** Enable PII redaction */
  redact?: boolean;
  /** Include CSS cascade data */
  includeCascade?: boolean;
  /** Include network data */
  includeNetwork?: boolean;
  /** Include console logs */
  includeConsole?: boolean;
  /** Include performance metrics */
  includePerformance?: boolean;
}

/**
 * Processing Result
 *
 * Result of Scout payload processing.
 */
export interface ProcessingResult {
  /** Whether processing succeeded */
  success: boolean;
  /** Generated Scout log */
  log?: ScoutLog;
  /** Error message if failed */
  error?: string;
  /** Processing warnings */
  warnings?: string[];
}
