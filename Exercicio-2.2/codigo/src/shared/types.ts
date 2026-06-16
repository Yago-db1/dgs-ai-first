// Domain types for the NovaTech Assistant query endpoint.
// These types represent the contract between all internal modules.

export type ConfidenceLevel = 'HIGH' | 'LOW' | 'NOT_FOUND';

export type VigencyStatus = 'active' | 'obsolete';

export interface QueryRequest {
  question: string;
  session_id?: string;
  attendant_id?: string;
}

export interface SourceDocument {
  document_id: string;
  title: string;
  section: string;
  vigency_date: string;
}

export interface SearchChunk {
  id: string;
  content: string;
  score: number;
  source_document: SourceDocument;
  vigency_status: VigencyStatus;
  vigency_warning?: string;
}

export interface PromptContext {
  system: string;
  context_chunks: SearchChunk[];
  user_question: string;
  tokens_used: number;
}

export interface QueryResponse {
  answer: string;
  source_document: SourceDocument; // always present — never null (enforced by response-builder)
  confidence_level: ConfidenceLevel;
  session_id?: string;
}
