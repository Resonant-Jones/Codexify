/**
 * Node generation logic for Scout logs
 * Converts sanitized logs into IDDB node structures (mock)
 */

import type {
  ScoutSanitizedLog,
  ScoutLogNode,
  ComponentNode,
  URLNode,
  RuntimeInstanceNode,
  ScoutIDDBNode,
  NodeGenerationConfig,
} from "./types";
import { createFingerprint } from "./sanitize";

/**
 * Generates all nodes from a sanitized log
 */
export function generateNodes(
  sanitized: ScoutSanitizedLog,
  config?: NodeGenerationConfig
): ScoutIDDBNode[] {
  const nodes: ScoutIDDBNode[] = [];

  // Always create the main ScoutLog node
  const logNode = generateScoutLogNode(sanitized);
  nodes.push(logNode);

  // Optionally create URL nodes
  if (config?.createURLNodes !== false) {
    const urlNodes = generateURLNodes(sanitized.extractedEntities.urls || []);
    nodes.push(...urlNodes);
  }

  // Optionally create Component nodes
  if (config?.createComponentNodes !== false) {
    const componentNodes = generateComponentNodes(
      sanitized.extractedEntities.components || []
    );
    nodes.push(...componentNodes);
  }

  // Optionally create RuntimeInstance node
  if (config?.createRuntimeNodes !== false && sanitized.extractedEntities.runtimeId) {
    const runtimeNode = generateRuntimeNode(
      sanitized.extractedEntities.runtimeId,
      sanitized.metadata
    );
    if (runtimeNode) {
      nodes.push(runtimeNode);
    }
  }

  return nodes;
}

/**
 * Generates a ScoutLog node from sanitized log
 */
export function generateScoutLogNode(
  sanitized: ScoutSanitizedLog
): ScoutLogNode {
  const fingerprint = createFingerprint(sanitized);

  return {
    id: `scout-log:${fingerprint}`,
    type: "ScoutLog",
    properties: {
      timestamp: sanitized.timestamp,
      severity: sanitized.severity,
      message: sanitized.message,
      tags: sanitized.tags,
      metadata: sanitized.metadata,
      rawFingerprint: fingerprint,
    },
  };
}

/**
 * Generates URL nodes from extracted URLs
 */
export function generateURLNodes(urls: string[]): URLNode[] {
  return urls.map((url) => generateURLNode(url));
}

/**
 * Generates a single URL node
 */
export function generateURLNode(urlString: string): URLNode {
  let parsed: URL;

  try {
    parsed = new URL(urlString);
  } catch {
    // If parsing fails, create a basic node
    return {
      id: `url:${simpleHash(urlString)}`,
      type: "URL",
      properties: {
        fullUrl: urlString,
        domain: urlString,
      },
    };
  }

  // Parse query parameters
  const queryParams: Record<string, string> = {};
  parsed.searchParams.forEach((value, key) => {
    queryParams[key] = value;
  });

  // Determine if internal (simplified heuristic)
  const isInternal =
    parsed.hostname === "localhost" ||
    parsed.hostname.startsWith("127.") ||
    parsed.hostname.startsWith("192.168.") ||
    parsed.hostname.startsWith("10.") ||
    parsed.hostname.endsWith(".local");

  return {
    id: `url:${simpleHash(parsed.href)}`,
    type: "URL",
    properties: {
      fullUrl: parsed.href,
      protocol: parsed.protocol.replace(":", ""),
      domain: parsed.hostname,
      path: parsed.pathname || undefined,
      queryParams: Object.keys(queryParams).length > 0 ? queryParams : undefined,
      fragment: parsed.hash ? parsed.hash.substring(1) : undefined,
      isInternal,
    },
  };
}

/**
 * Generates Component nodes from extracted component names
 */
export function generateComponentNodes(components: string[]): ComponentNode[] {
  return components.map((name) => generateComponentNode(name));
}

/**
 * Generates a single Component node
 */
export function generateComponentNode(name: string): ComponentNode {
  // Try to infer component type from name
  const componentType = inferComponentType(name);

  // Try to extract version if present (e.g., "myservice@1.2.3")
  const versionMatch = name.match(/@([0-9.]+)$/);
  const cleanName = versionMatch ? name.replace(/@[0-9.]+$/, "") : name;
  const version = versionMatch ? versionMatch[1] : undefined;

  return {
    id: `component:${simpleHash(cleanName)}`,
    type: "Component",
    properties: {
      name: cleanName,
      componentType,
      version,
    },
  };
}

/**
 * Generates a RuntimeInstance node
 */
export function generateRuntimeNode(
  instanceId: string,
  metadata: Record<string, any>
): RuntimeInstanceNode | null {
  // Try to extract environment from metadata
  const environment = metadata.environment || metadata.env || "other";

  return {
    id: `runtime:${simpleHash(instanceId)}`,
    type: "RuntimeInstance",
    properties: {
      instanceId,
      environment: normalizeEnvironment(environment),
      runtimeVersion: metadata.version || metadata.runtimeVersion,
      platform: metadata.platform,
      region: metadata.region,
      startTime: metadata.startTime,
      metadata: {
        ...metadata,
      },
    },
  };
}

/**
 * Infers component type from name
 */
function inferComponentType(name: string): ComponentNode["properties"]["componentType"] {
  const lowerName = name.toLowerCase();

  if (
    lowerName.includes("api") ||
    lowerName.includes("endpoint") ||
    lowerName.includes("controller")
  ) {
    return "api";
  }

  if (
    lowerName.includes("service") ||
    lowerName.includes("server") ||
    lowerName.includes("daemon")
  ) {
    return "service";
  }

  if (
    lowerName.includes("lib") ||
    lowerName.includes("library") ||
    lowerName.includes("package")
  ) {
    return "library";
  }

  if (
    lowerName.includes("db") ||
    lowerName.includes("database") ||
    lowerName.includes("storage")
  ) {
    return "database";
  }

  if (
    lowerName.includes("queue") ||
    lowerName.includes("broker") ||
    lowerName.includes("pubsub")
  ) {
    return "queue";
  }

  if (
    lowerName.includes("func") ||
    lowerName.includes("lambda") ||
    lowerName.includes("handler")
  ) {
    return "function";
  }

  return "module";
}

/**
 * Normalizes environment string
 */
function normalizeEnvironment(env: string): RuntimeInstanceNode["properties"]["environment"] {
  const lower = env.toLowerCase();

  if (lower.includes("dev")) return "development";
  if (lower.includes("stag")) return "staging";
  if (lower.includes("prod")) return "production";
  if (lower.includes("test")) return "test";

  return "other";
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
