/**
 * Sanitization logic for Scout logs before IDDB processing
 * Removes sensitive data and normalizes log structure
 */

import type {
  RawScoutLog,
  ScoutSanitizedLog,
  LogSeverity,
  SanitizationConfig,
  EntityExtraction,
} from "./types";

// Default patterns for sensitive data masking
const DEFAULT_MASK_PATTERNS = [
  // API keys and tokens
  /\b[A-Za-z0-9_-]{32,}\b/g,
  // Email addresses
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
  // IP addresses (partial masking)
  /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,
  // Credit card numbers
  /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g,
  // Social security numbers (US)
  /\b\d{3}-\d{2}-\d{4}\b/g,
  // JWT tokens
  /eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*/g,
  // Password-like patterns
  /password[=:]\s*[^\s]+/gi,
  /token[=:]\s*[^\s]+/gi,
  /secret[=:]\s*[^\s]+/gi,
];

// Fields to remove from metadata
const SENSITIVE_FIELDS = [
  "password",
  "token",
  "secret",
  "apiKey",
  "api_key",
  "authorization",
  "cookie",
  "sessionId",
  "creditCard",
  "ssn",
  "privateKey",
  "private_key",
];

/**
 * Sanitizes a raw Scout log entry
 */
export function sanitizeLog(
  raw: RawScoutLog,
  config?: SanitizationConfig
): ScoutSanitizedLog {
  // Normalize timestamp
  const timestamp = normalizeTimestamp(raw.timestamp || new Date());

  // Normalize severity
  const severity = normalizeSeverity(raw.level || raw.severity || "info");

  // Sanitize message
  const message = sanitizeMessage(raw.message, config);

  // Sanitize tags
  const tags = sanitizeTags(raw.tags);

  // Sanitize metadata
  const metadata = sanitizeMetadata(raw.metadata || {}, config);

  // Extract entities for relationship generation
  const extractedEntities = extractEntities(raw, message);

  return {
    timestamp,
    severity,
    message,
    tags,
    metadata,
    extractedEntities,
  };
}

/**
 * Normalizes timestamp to ISO 8601 format
 */
function normalizeTimestamp(timestamp: string | Date): string {
  if (timestamp instanceof Date) {
    return timestamp.toISOString();
  }

  try {
    return new Date(timestamp).toISOString();
  } catch {
    return new Date().toISOString();
  }
}

/**
 * Normalizes log severity to standard levels
 */
function normalizeSeverity(level: string): LogSeverity {
  const normalized = level.toLowerCase();

  switch (normalized) {
    case "debug":
    case "trace":
    case "verbose":
      return "debug";

    case "info":
    case "information":
    case "log":
      return "info";

    case "warn":
    case "warning":
      return "warn";

    case "error":
    case "err":
      return "error";

    case "critical":
    case "fatal":
    case "emergency":
    case "alert":
      return "critical";

    default:
      return "info";
  }
}

/**
 * Sanitizes log message by masking sensitive data
 */
function sanitizeMessage(
  message: string,
  config?: SanitizationConfig
): string {
  let sanitized = message;

  // Apply default mask patterns
  const patterns = config?.maskPatterns || DEFAULT_MASK_PATTERNS;

  for (const pattern of patterns) {
    sanitized = sanitized.replace(pattern, "[REDACTED]");
  }

  // Truncate if needed
  const maxLength = config?.maxMessageLength || 5000;
  if (sanitized.length > maxLength) {
    sanitized = sanitized.substring(0, maxLength) + "... [TRUNCATED]";
  }

  return sanitized;
}

/**
 * Sanitizes and normalizes tags
 */
function sanitizeTags(tags?: string[]): string[] {
  if (!tags || !Array.isArray(tags)) {
    return [];
  }

  return tags
    .filter((tag) => typeof tag === "string" && tag.length > 0)
    .map((tag) => tag.toLowerCase().trim())
    .filter((tag, index, self) => self.indexOf(tag) === index); // Deduplicate
}

/**
 * Sanitizes metadata by removing sensitive fields
 */
function sanitizeMetadata(
  metadata: Record<string, any>,
  config?: SanitizationConfig
): Record<string, any> {
  const sanitized: Record<string, any> = {};

  const fieldsToRemove = new Set([
    ...SENSITIVE_FIELDS,
    ...(config?.removeFields || []),
  ]);

  for (const [key, value] of Object.entries(metadata)) {
    // Skip sensitive fields
    if (fieldsToRemove.has(key)) {
      continue;
    }

    // Recursively sanitize nested objects
    if (value && typeof value === "object" && !Array.isArray(value)) {
      sanitized[key] = sanitizeMetadata(value, config);
    } else if (typeof value === "string") {
      sanitized[key] = sanitizeMessage(value, config);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

/**
 * Extracts entities (URLs, components, runtime) from log data
 */
function extractEntities(
  raw: RawScoutLog,
  sanitizedMessage: string
): EntityExtraction {
  const urls = extractURLs(raw, sanitizedMessage);
  const components = extractComponents(raw);
  const runtimeId = extractRuntimeId(raw);

  return {
    urls,
    components,
    runtimeId,
  };
}

/**
 * Extracts URLs from log data
 */
function extractURLs(raw: RawScoutLog, message: string): string[] {
  const urls: string[] = [];

  // Check explicit URL field
  if (raw.url && typeof raw.url === "string") {
    urls.push(raw.url);
  }

  // Extract URLs from message (simple pattern)
  const urlPattern = /https?:\/\/[^\s]+/g;
  const matches = message.match(urlPattern);
  if (matches) {
    urls.push(...matches);
  }

  // Extract from metadata
  if (raw.metadata?.url) {
    urls.push(raw.metadata.url);
  }

  // Deduplicate
  return [...new Set(urls)];
}

/**
 * Extracts component names from log data
 */
function extractComponents(raw: RawScoutLog): string[] {
  const components: string[] = [];

  // Check explicit component field
  if (raw.component && typeof raw.component === "string") {
    components.push(raw.component);
  }

  // Check source field
  if (raw.source && typeof raw.source === "string") {
    components.push(raw.source);
  }

  // Check metadata
  if (raw.metadata?.component) {
    components.push(raw.metadata.component);
  }

  if (raw.metadata?.source) {
    components.push(raw.metadata.source);
  }

  // Deduplicate
  return [...new Set(components)];
}

/**
 * Extracts runtime instance ID from log data
 */
function extractRuntimeId(raw: RawScoutLog): string | undefined {
  // Check explicit runtime field
  if (raw.runtime && typeof raw.runtime === "string") {
    return raw.runtime;
  }

  // Check metadata
  if (raw.metadata?.instanceId) {
    return raw.metadata.instanceId;
  }

  if (raw.metadata?.runtime) {
    return raw.metadata.runtime;
  }

  return undefined;
}

/**
 * Creates a fingerprint for deduplication
 */
export function createFingerprint(log: ScoutSanitizedLog): string {
  // Simple hash based on key properties
  const input = `${log.timestamp}:${log.severity}:${log.message}`;
  return simpleHash(input);
}

/**
 * Simple string hash function
 */
function simpleHash(str: string): string {
  let hash = 0;

  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }

  return Math.abs(hash).toString(36);
}
