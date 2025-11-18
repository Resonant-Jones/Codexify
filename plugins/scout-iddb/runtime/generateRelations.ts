/**
 * Relationship generation logic for Scout logs
 * Creates relationships between nodes (all marked as "pending")
 */

import type {
  ScoutSanitizedLog,
  ScoutIDDBNode,
  ScoutIDDBRelation,
  ObservedAtRelation,
  DescribesRelation,
  GeneratedByRelation,
} from "./types";

/**
 * Generates all relationships from nodes and sanitized log
 */
export function generateRelations(
  logNode: ScoutIDDBNode,
  nodes: ScoutIDDBNode[],
  sanitized: ScoutSanitizedLog
): ScoutIDDBRelation[] {
  const relations: ScoutIDDBRelation[] = [];

  // Find URL nodes and create OBSERVED_AT relationships
  const urlNodes = nodes.filter((n) => n.type === "URL");
  for (const urlNode of urlNodes) {
    const relation = createObservedAtRelation(logNode, urlNode, sanitized);
    if (relation) {
      relations.push(relation);
    }
  }

  // Find Component nodes and create DESCRIBES relationships
  const componentNodes = nodes.filter((n) => n.type === "Component");
  for (const componentNode of componentNodes) {
    const relation = createDescribesRelation(logNode, componentNode, sanitized);
    if (relation) {
      relations.push(relation);
    }
  }

  // Find RuntimeInstance node and create GENERATED_BY relationship
  const runtimeNode = nodes.find((n) => n.type === "RuntimeInstance");
  if (runtimeNode) {
    const relation = createGeneratedByRelation(logNode, runtimeNode, sanitized);
    if (relation) {
      relations.push(relation);
    }
  }

  return relations;
}

/**
 * Creates an OBSERVED_AT relationship between a log and a URL
 */
function createObservedAtRelation(
  logNode: ScoutIDDBNode,
  urlNode: ScoutIDDBNode,
  sanitized: ScoutSanitizedLog
): ObservedAtRelation | null {
  if (logNode.type !== "ScoutLog" || urlNode.type !== "URL") {
    return null;
  }

  // Extract HTTP method if present
  const method = extractHTTPMethod(sanitized);

  // Extract status code if present
  const statusCode = extractStatusCode(sanitized);

  // Extract response time if present
  const responseTime = extractResponseTime(sanitized);

  return {
    id: `rel:${logNode.id}:OBSERVED_AT:${urlNode.id}`,
    type: "OBSERVED_AT",
    source: logNode.id,
    target: urlNode.id,
    state: "pending",
    properties: {
      observedAt: sanitized.timestamp,
      method,
      statusCode,
      responseTime,
      context: sanitized.metadata.context,
    },
  };
}

/**
 * Creates a DESCRIBES relationship between a log and a component
 */
function createDescribesRelation(
  logNode: ScoutIDDBNode,
  componentNode: ScoutIDDBNode,
  sanitized: ScoutSanitizedLog
): DescribesRelation | null {
  if (logNode.type !== "ScoutLog" || componentNode.type !== "Component") {
    return null;
  }

  // Infer relevance based on severity
  const relevance = inferRelevance(sanitized.severity);

  // Infer category from tags and message
  const category = inferCategory(sanitized);

  return {
    id: `rel:${logNode.id}:DESCRIBES:${componentNode.id}`,
    type: "DESCRIBES",
    source: logNode.id,
    target: componentNode.id,
    state: "pending",
    properties: {
      relevance,
      category,
      inferredBy: "explicit",
      confidence: 1.0,
    },
  };
}

/**
 * Creates a GENERATED_BY relationship between a log and a runtime instance
 */
function createGeneratedByRelation(
  logNode: ScoutIDDBNode,
  runtimeNode: ScoutIDDBNode,
  sanitized: ScoutSanitizedLog
): GeneratedByRelation | null {
  if (logNode.type !== "ScoutLog" || runtimeNode.type !== "RuntimeInstance") {
    return null;
  }

  return {
    id: `rel:${logNode.id}:GENERATED_BY:${runtimeNode.id}`,
    type: "GENERATED_BY",
    source: logNode.id,
    target: runtimeNode.id,
    state: "pending",
    properties: {
      generatedAt: sanitized.timestamp,
      processId: sanitized.metadata.processId,
      sessionId: sanitized.metadata.sessionId,
      sourceFile: sanitized.metadata.sourceFile,
      sourceLine: sanitized.metadata.sourceLine,
    },
  };
}

/**
 * Extracts HTTP method from sanitized log
 */
function extractHTTPMethod(sanitized: ScoutSanitizedLog): ObservedAtRelation["properties"]["method"] {
  // Check metadata first
  if (sanitized.metadata.method) {
    return normalizeHTTPMethod(sanitized.metadata.method);
  }

  // Try to extract from message
  const methodPattern = /\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|CONNECT|TRACE)\b/i;
  const match = sanitized.message.match(methodPattern);

  if (match) {
    return normalizeHTTPMethod(match[1]);
  }

  return undefined;
}

/**
 * Normalizes HTTP method string
 */
function normalizeHTTPMethod(method: string): ObservedAtRelation["properties"]["method"] {
  const upper = method.toUpperCase();

  switch (upper) {
    case "GET":
    case "POST":
    case "PUT":
    case "PATCH":
    case "DELETE":
    case "HEAD":
    case "OPTIONS":
    case "CONNECT":
    case "TRACE":
      return upper as ObservedAtRelation["properties"]["method"];
    default:
      return "OTHER";
  }
}

/**
 * Extracts HTTP status code from sanitized log
 */
function extractStatusCode(sanitized: ScoutSanitizedLog): number | undefined {
  // Check metadata first
  if (sanitized.metadata.statusCode && typeof sanitized.metadata.statusCode === "number") {
    return sanitized.metadata.statusCode;
  }

  // Try to extract from message (e.g., "200", "404", "500")
  const statusPattern = /\b([1-5]\d{2})\b/;
  const match = sanitized.message.match(statusPattern);

  if (match) {
    return parseInt(match[1], 10);
  }

  return undefined;
}

/**
 * Extracts response time from sanitized log
 */
function extractResponseTime(sanitized: ScoutSanitizedLog): number | undefined {
  // Check metadata first
  if (sanitized.metadata.responseTime && typeof sanitized.metadata.responseTime === "number") {
    return sanitized.metadata.responseTime;
  }

  if (sanitized.metadata.duration && typeof sanitized.metadata.duration === "number") {
    return sanitized.metadata.duration;
  }

  // Try to extract from message (e.g., "123ms", "1.5s")
  const timePattern = /(\d+(?:\.\d+)?)\s*(ms|s)/i;
  const match = sanitized.message.match(timePattern);

  if (match) {
    const value = parseFloat(match[1]);
    const unit = match[2].toLowerCase();

    return unit === "s" ? value * 1000 : value;
  }

  return undefined;
}

/**
 * Infers relevance based on log severity
 */
function inferRelevance(severity: string): DescribesRelation["properties"]["relevance"] {
  switch (severity) {
    case "critical":
    case "error":
      return "high";
    case "warn":
      return "medium";
    default:
      return "low";
  }
}

/**
 * Infers description category from log data
 */
function inferCategory(sanitized: ScoutSanitizedLog): DescribesRelation["properties"]["category"] {
  const message = sanitized.message.toLowerCase();
  const tags = sanitized.tags.map((t) => t.toLowerCase());

  // Check for error patterns
  if (
    sanitized.severity === "error" ||
    sanitized.severity === "critical" ||
    message.includes("error") ||
    message.includes("exception") ||
    message.includes("failed") ||
    tags.includes("error")
  ) {
    return "error";
  }

  // Check for performance patterns
  if (
    message.includes("slow") ||
    message.includes("timeout") ||
    message.includes("latency") ||
    message.includes("performance") ||
    tags.includes("performance")
  ) {
    return "performance";
  }

  // Check for lifecycle patterns
  if (
    message.includes("start") ||
    message.includes("stop") ||
    message.includes("shutdown") ||
    message.includes("initialize") ||
    tags.includes("lifecycle")
  ) {
    return "lifecycle";
  }

  // Check for security patterns
  if (
    message.includes("auth") ||
    message.includes("security") ||
    message.includes("unauthorized") ||
    message.includes("forbidden") ||
    tags.includes("security")
  ) {
    return "security";
  }

  return "behavior";
}
