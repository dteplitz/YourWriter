export interface EvolutionEntry {
  id: number;
  writer_id: number;
  field_changed: string;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  source_session_id?: number | null;
  created_at: string;
}
