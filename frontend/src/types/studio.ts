import type { Identity } from './writer';

export interface Brief {
  format: string;
  tone: string;
  constraints_applied: string[];
  word_limit?: number | null;
  notes?: string | null;
  needs_clarification: boolean;
  clarification_question?: string | null;
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

export type SessionLifecycle =
  | 'active'
  | 'complete'
  | 'imported'
  | 'skipped'
  | 'abandoned';

export type SessionResumeMode = 'checkpoint' | 'artifact';

export interface SessionTakeSummary {
  id: number;
  take_number: number;
  title?: string | null;
  word_count: number;
  created_at: string;
}

export interface SessionSummaryItem {
  id: number;
  writer_id: number;
  lifecycle: SessionLifecycle;
  brief_preview: string;
  take_count: number;
  created_at: string;
  updated_at: string;
  last_take?: SessionTakeSummary | null;
}

export interface WriterSessionsSummaryResponse {
  highlight?: SessionSummaryItem | null;
  history: SessionSummaryItem[];
}

export interface SessionTakeDetail {
  id: number;
  take_number: number;
  title?: string | null;
  content: string;
  word_count: number;
  iteration_notes?: string | null;
  created_at: string;
}

export interface SessionDetailResponse {
  id: number;
  writer_id: number;
  lifecycle: SessionLifecycle;
  resume_mode?: SessionResumeMode | null;
  brief: Brief;
  brief_preview: string;
  take_count: number;
  created_at: string;
  updated_at: string;
  takes: SessionTakeDetail[];
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

export interface SessionAbandonResponse {
  session_id: number;
  writer_id: number;
  lifecycle: 'abandoned';
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
  initialSessionId?: number | null;
  initialPiece?: Piece | null;
  autoStart?: boolean;
  onPieceSaved?: (piece: Piece) => void;
  onSessionEnd: (sessionId: number | null) => void;
}
