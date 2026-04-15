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

export interface WriterInitializationPreview {
  summary: string;
  name: string;
  purpose: string;
  personality: Record<string, string>;
  emotions: Record<string, number>;
  topics: string[];
  constraints: Record<string, string>;
  lifelong_objectives: string[];
}

export interface WriterWithIdentity extends Writer {
  identity: Identity | null;
}

export interface EvolutionChange {
  field: string;
  action: 'add' | 'modify' | 'remove';
  key?: string;            // para dict fields: emotions, personality, constraints
  old_value?: unknown;
  new_value?: unknown;
  value?: unknown;         // para list fields: topics, memories, lifelong_objectives
  reason: string;
}

export interface EvolutionDetectedEvent {
  evolution_detected: true;
  changes: EvolutionChange[];
  reasoning: string;
}
