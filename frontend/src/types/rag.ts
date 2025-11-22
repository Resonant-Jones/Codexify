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
}

export interface RagGraphNode {
  node_id: string;
  kind: string;
  text: string;
}

export interface RagTraceResponse {
  documents: RagDocument[];
  graph: RagGraphNode[];
}

export type { ChatMessage } from "./ui";
