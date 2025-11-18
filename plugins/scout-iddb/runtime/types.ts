/**
 * Type definitions for Scout-IDDB plugin
 * These types mirror the schema definitions in /schema/
 */

// ============================================================================
// Node Types
// ============================================================================

export type LogSeverity = "debug" | "info" | "warn" | "error" | "critical";

export type ComponentType =
  | "service"
  | "library"
  | "module"
  | "function"
  | "api"
  | "database"
  | "queue"
  | "other";

export type Environment =
  | "development"
  | "staging"
  | "production"
  | "test"
  | "other";

export interface ScoutLogMetadata {
  source?: string;
  traceId?: string;
  spanId?: string;
  userId?: string;
  [key: string]: any;
}

export interface ScoutIDDBNode {
  id: string;
  type: "ScoutLog" | "Component" | "URL" | "RuntimeInstance";
  properties: Record<string, any>;
}

export interface ScoutLogNode extends ScoutIDDBNode {
  type: "ScoutLog";
  properties: {
    timestamp: string;
    severity: LogSeverity;
    message: string;
    tags?: string[];
    metadata?: ScoutLogMetadata;
    rawFingerprint?: string;
  };
}

export interface ComponentNode extends ScoutIDDBNode {
  type: "Component";
  properties: {
    name: string;
    componentType: ComponentType;
    version?: string;
    namespace?: string;
    repository?: string;
  };
}

export interface URLNode extends ScoutIDDBNode {
  type: "URL";
  properties: {
    fullUrl: string;
    protocol?: string;
    domain: string;
    path?: string;
    queryParams?: Record<string, string>;
    fragment?: string;
    isInternal?: boolean;
  };
}

export interface RuntimeInstanceNode extends ScoutIDDBNode {
  type: "RuntimeInstance";
  properties: {
    instanceId: string;
    environment: Environment;
    runtimeVersion?: string;
    platform?: string;
    region?: string;
    startTime?: string;
    metadata?: Record<string, any>;
  };
}

// ============================================================================
// Relationship Types
// ============================================================================

export type RelationshipState = "pending" | "active" | "inactive";

export type HTTPMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "PATCH"
  | "DELETE"
  | "HEAD"
  | "OPTIONS"
  | "CONNECT"
  | "TRACE"
  | "OTHER";

export type Relevance = "high" | "medium" | "low";

export type DescriptionCategory =
  | "performance"
  | "error"
  | "lifecycle"
  | "behavior"
  | "security"
  | "other";

export type InferredBy = "explicit" | "pattern" | "curator" | "manual";

export interface ScoutIDDBRelation {
  id: string;
  type: string;
  source: string;
  target: string;
  state: RelationshipState;
  properties: Record<string, any>;
}

export interface ObservedAtRelation extends ScoutIDDBRelation {
  type: "OBSERVED_AT";
  source: string; // ScoutLog ID
  target: string; // URL ID
  properties: {
    observedAt: string;
    method?: HTTPMethod;
    statusCode?: number;
    responseTime?: number;
    context?: string;
  };
}

export interface DescribesRelation extends ScoutIDDBRelation {
  type: "DESCRIBES";
  source: string; // ScoutLog ID
  target: string; // Component ID
  properties: {
    relevance?: Relevance;
    category?: DescriptionCategory;
    inferredBy?: InferredBy;
    confidence?: number;
  };
}

export interface GeneratedByRelation extends ScoutIDDBRelation {
  type: "GENERATED_BY";
  source: string; // ScoutLog ID
  target: string; // RuntimeInstance ID
  properties: {
    generatedAt: string;
    processId?: string;
    sessionId?: string;
    sourceFile?: string;
    sourceLine?: number;
  };
}

// ============================================================================
// Processing Types
// ============================================================================

export interface RawScoutLog {
  timestamp?: string | Date;
  level?: string;
  severity?: string;
  message: string;
  tags?: string[];
  metadata?: Record<string, any>;
  source?: string;
  component?: string;
  url?: string;
  runtime?: string;
  [key: string]: any;
}

export interface ScoutSanitizedLog {
  timestamp: string;
  severity: LogSeverity;
  message: string;
  tags: string[];
  metadata: ScoutLogMetadata;
  extractedEntities: {
    urls?: string[];
    components?: string[];
    runtimeId?: string;
  };
}

export interface ProcessingResult {
  nodes: ScoutIDDBNode[];
  relations: ScoutIDDBRelation[];
  sanitizedLog: ScoutSanitizedLog;
  warnings?: string[];
  errors?: string[];
}

// ============================================================================
// Configuration Types
// ============================================================================

export interface SanitizationConfig {
  maskPatterns?: RegExp[];
  removeFields?: string[];
  maxMessageLength?: number;
  allowedDomains?: string[];
}

export interface NodeGenerationConfig {
  createURLNodes?: boolean;
  createComponentNodes?: boolean;
  createRuntimeNodes?: boolean;
  deduplication?: boolean;
}

export interface PluginConfig {
  enabled: boolean;
  sanitization?: SanitizationConfig;
  nodeGeneration?: NodeGenerationConfig;
  batchSize?: number;
  flushInterval?: number;
}

// ============================================================================
// Utility Types
// ============================================================================

export type NodeType = ScoutLogNode | ComponentNode | URLNode | RuntimeInstanceNode;
export type RelationType = ObservedAtRelation | DescribesRelation | GeneratedByRelation;

export interface EntityExtraction {
  urls: string[];
  components: string[];
  runtimeId?: string;
}
