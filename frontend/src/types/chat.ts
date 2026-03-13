export interface ChatMessage {
  id: number | string;
  writer_id: number | string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}
