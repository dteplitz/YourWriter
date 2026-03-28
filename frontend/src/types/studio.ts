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

export interface SessionExperienceProps {
  writerId: string;
  brief: Brief;
  onPieceSaved?: (piece: Piece) => void;
  onSessionEnd: () => void;
}
