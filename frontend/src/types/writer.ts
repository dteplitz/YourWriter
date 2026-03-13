export interface Identity {
  id: number;
  writer_id: number;
  personality: Record<string, any>;
  emotions: Record<string, any>;
  memories: any[];
  topics: any[];
  constraints: Record<string, any>;
  lifelong_objectives: any[];
  version: number;
  created_at: string;
}

export interface Constraints {
  constraints: Record<string, any>;
}

export interface Writer {
  id: string;
  user_id: string;
  name: string;
  purpose: string;
  created_at: string;
  updated_at: string;
}

export interface WriterCreate {
  name: string;
  purpose?: string;
  style_description?: string;
}

export interface WriterWithIdentity extends Writer {
  identity: Identity | null;
}
