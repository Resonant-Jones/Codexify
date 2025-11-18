/**
 * Main processing pipeline for Scout-IDDB plugin
 * Orchestrates sanitization, node generation, and relationship creation
 */

import type {
  RawScoutLog,
  ProcessingResult,
  SanitizationConfig,
  NodeGenerationConfig,
} from "./types";
import { sanitizeLog } from "./sanitize";
import { generateNodes, generateScoutLogNode } from "./generateNode";
import { generateRelations } from "./generateRelations";

/**
 * Main processing function: converts raw Scout log to IDDB nodes + relations
 *
 * IMPORTANT: This is a MOCK implementation that does NOT write to IDDB.
 * It only generates the data structures that WOULD be written.
 */
export function processScoutToIDDB(
  raw: RawScoutLog,
  sanitizationConfig?: SanitizationConfig,
  nodeConfig?: NodeGenerationConfig
): ProcessingResult {
  const warnings: string[] = [];
  const errors: string[] = [];

  try {
    // Step 1: Sanitize the raw log
    const sanitizedLog = sanitizeLog(raw, sanitizationConfig);

    // Step 2: Generate nodes from sanitized log
    const nodes = generateNodes(sanitizedLog, nodeConfig);

    // Get the main log node (always first)
    const logNode = nodes.find((n) => n.type === "ScoutLog");

    if (!logNode) {
      errors.push("Failed to generate ScoutLog node");
      return {
        nodes: [],
        relations: [],
        sanitizedLog,
        warnings,
        errors,
      };
    }

    // Step 3: Generate relationships
    const relations = generateRelations(logNode, nodes, sanitizedLog);

    // Step 4: Return processing result (NO IDDB WRITES!)
    return {
      nodes,
      relations,
      sanitizedLog,
      warnings,
      errors,
    };
  } catch (error) {
    errors.push(
      `Processing failed: ${error instanceof Error ? error.message : String(error)}`
    );

    return {
      nodes: [],
      relations: [],
      sanitizedLog: {
        timestamp: new Date().toISOString(),
        severity: "error",
        message: "Failed to process log",
        tags: [],
        metadata: {},
        extractedEntities: {
          urls: [],
          components: [],
        },
      },
      warnings,
      errors,
    };
  }
}

/**
 * Batch processing function for multiple logs
 *
 * IMPORTANT: This is a MOCK implementation that does NOT write to IDDB.
 */
export function processBatch(
  rawLogs: RawScoutLog[],
  sanitizationConfig?: SanitizationConfig,
  nodeConfig?: NodeGenerationConfig
): ProcessingResult[] {
  return rawLogs.map((raw) =>
    processScoutToIDDB(raw, sanitizationConfig, nodeConfig)
  );
}

/**
 * Export all processing utilities
 */
export * from "./types";
export * from "./sanitize";
export * from "./generateNode";
export * from "./generateRelations";
