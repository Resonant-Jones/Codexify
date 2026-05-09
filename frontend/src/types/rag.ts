/**
 * RAG Trace type definitions
 *
 * Represents the semantic documents and graph nodes used during
 * a completion request, for debugging and transparency.
 */

export interface RagDocument {
  id: string;
  title: string;
  score: number;
  snippet: string;
  source_type?: string | null;
  role?: string | null;
  thread_id?: number | string | null;
  project_id?: number | string | null;
  retrieval_lane?: string | null;
  policy_reason?: string | null;
  retrieval_policy?: Record<string, unknown> | null;
  suppressed?: boolean | null;
  suppression_reason?: string | null;
}

export interface RagGraphNode {
  node_id: string;
  kind: string;
  text: string;
}

export interface RagSuppressionItem {
  id?: string;
  source_type?: string | null;
  role?: string | null;
  thread_id?: number | string | null;
  project_id?: number | string | null;
  retrieval_lane?: string | null;
  score?: number | null;
  policy_reason?: string | null;
  retrieval_policy?: Record<string, unknown> | null;
  suppressed?: boolean | null;
  suppression_reason?: string | null;
  count?: number | null;
}

export interface RagSuppressionSummary {
  count?: number | null;
  items?: RagSuppressionItem[];
  counts_by_reason?: Record<string, number>;
}

export interface RagTraceResponse {
  documents: RagDocument[];
  graph: RagGraphNode[];
  retrieval_policy?: Record<string, unknown> | null;
  retrieval_provenance?: Record<string, unknown> | null;
  retrieval_suppression?: RagSuppressionSummary | null;
}

export type { ChatMessage } from "./ui";
