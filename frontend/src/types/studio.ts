import type { Identity } from './writer';

export interface Brief {
  format: string;
  tone: string;
  constraints_applied: string[];
  word_limit?: number;
  notes?: string;
  needs_clarification: boolean;
  clarification_question?: string;
}

export interface Piece {
  id: number;
  writer_id: number;
  title: string;
  content: string;
  format: string;
  word_count: number;
  created_at: string;
}

export interface ToolUseEvent {
  name: string;
  display_name: string;
  query: string;
}

export interface ToolResultEvent {
  name: string;
  summary: string;
}

export interface SessionImportChange {
  field: string;
  action: 'add' | 'modify' | 'remove';
  key?: string | null;
  old_value?: unknown;
  new_value?: unknown;
  value?: unknown;
  reason: string;
}

export interface SessionImportProposalResponse {
  session_id: number;
  writer_id: number;
  lifecycle: 'complete';
  changes: SessionImportChange[];
  reasoning: string;
}

export interface SessionImportRequest {
  changes: SessionImportChange[];
  reasoning: string;
}

export interface SessionImportResponse {
  session_id: number;
  writer_id: number;
  lifecycle: 'imported';
  imported_changes: SessionImportChange[];
  reasoning: string;
  identity: Identity;
}

export interface SessionSkipResponse {
  session_id: number;
  writer_id: number;
  lifecycle: 'skipped';
}

export interface SessionImportFeedback {
  status: 'imported' | 'skipped';
  sessionId: number;
  importedChanges?: SessionImportChange[];
  reasoning?: string;
}

export interface SessionExperienceProps {
  writerId: string;
  brief: Brief;
  onPieceSaved?: (piece: Piece) => void;
  onSessionEnd: (sessionId: number | null) => void;
}
