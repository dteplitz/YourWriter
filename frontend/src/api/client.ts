import type {
  AuthToken,
  LoginRequest,
  RegisterRequest,
  Writer,
  WriterCreate,
  ChatMessage,
  Identity,
  Constraints,
  EvolutionEntry,
  EvolutionDetectedEvent,
} from '../types';
import type { Brief, Piece, ToolUseEvent, ToolResultEvent } from '../types/studio';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response;
}

// Auth

export async function login(data: LoginRequest): Promise<AuthToken> {
  const response = await fetchWithAuth('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.json();
}

export async function register(data: RegisterRequest): Promise<AuthToken> {
  const response = await fetchWithAuth('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.json();
}

// Writers

export async function getWriters(): Promise<Writer[]> {
  const response = await fetchWithAuth('/writers');
  return response.json();
}

export async function createWriter(data: WriterCreate): Promise<Writer> {
  const response = await fetchWithAuth('/writers', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.json();
}

export async function getWriter(id: string): Promise<Writer> {
  const response = await fetchWithAuth(`/writers/${id}`);
  return response.json();
}

export async function deleteWriter(id: string): Promise<void> {
  await fetchWithAuth(`/writers/${id}`, { method: 'DELETE' });
}

// Chat

export async function sendMessage(
  writerId: string,
  content: string
): Promise<ChatMessage> {
  const response = await fetchWithAuth(`/chat/${writerId}/message`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
  return response.json();
}

export async function sendMessageStream(
  writerId: string,
  content: string,
  onToken: (token: string) => void,
  onPhase?: (phase: string) => void,
  onEvolution?: (event: EvolutionDetectedEvent) => void,
  onDone?: (messageId: number) => void,
): Promise<{ messageId: number }> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/chat/${writerId}/message/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let messageId = 0;

  while (true) {
    const { done, value } = await reader.read();
    // Only break when the server closes the connection — NOT on the `done` SSE event.
    // evolution_detected events are emitted AFTER {"done": true}, so we must keep reading.
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    // Keep the last potentially incomplete line in the buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = JSON.parse(line.slice(6));

      if (data.error) {
        throw new Error(data.error);
      }
      if (data.phase && onPhase) {
        onPhase(data.phase);
      }
      if (data.token) {
        onToken(data.token);
      }
      if (data.done) {
        messageId = data.message_id;
        if (onDone) onDone(data.message_id);
        // Do NOT break — server may still send evolution_detected events.
      }
      if (data.evolution_detected && onEvolution) {
        onEvolution(data as EvolutionDetectedEvent);
      }
    }
  }

  return { messageId };
}

export async function getChatHistory(writerId: string): Promise<ChatMessage[]> {
  const response = await fetchWithAuth(`/chat/${writerId}/history`);
  return response.json();
}

// Identity

export async function getIdentity(writerId: string): Promise<Identity> {
  const response = await fetchWithAuth(`/writers/${writerId}/identity`);
  return response.json();
}

export async function updateIdentity(
  writerId: string,
  identity: Partial<Identity>
): Promise<Identity> {
  const response = await fetchWithAuth(`/writers/${writerId}/identity`, {
    method: 'PUT',
    body: JSON.stringify(identity),
  });
  return response.json();
}

// Constraints

export async function updateConstraints(
  writerId: string,
  constraints: Constraints
): Promise<Identity> {
  const response = await fetchWithAuth(`/writers/${writerId}/constraints`, {
    method: 'PUT',
    body: JSON.stringify(constraints),
  });
  return response.json();
}

// Evolution

export async function getEvolutionLog(
  writerId: string
): Promise<EvolutionEntry[]> {
  const response = await fetchWithAuth(`/writers/${writerId}/evolution`);
  return response.json();
}

export async function rollbackIdentity(writerId: number): Promise<Identity> {
  const response = await fetchWithAuth(`/writers/${writerId}/identity/rollback`, {
    method: 'POST',
  });
  // RollbackResponse has an `identity` field with the rolled-back Identity
  const data = await response.json();
  return data.identity as Identity;
}

// Studio

export async function sendBrief(
  writerId: string,
  message: string
): Promise<Brief> {
  const response = await fetchWithAuth(`/chat/${writerId}/brief`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
  return response.json();
}

export async function getPieces(writerId: string): Promise<Piece[]> {
  const response = await fetchWithAuth(`/writers/${writerId}/pieces`);
  return response.json();
}


export async function sendStudioStream(
  writerId: string,
  brief: Brief,
  onToken: (token: string) => void,
  onPhase?: (phase: string) => void,
  onToolUse?: (event: ToolUseEvent) => void,
  onToolResult?: (event: ToolResultEvent) => void,
  onPiece?: (piece: Piece) => void,
): Promise<void> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/chat/${writerId}/studio/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ brief }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = JSON.parse(line.slice(6));

      if (data.error) {
        throw new Error(data.error);
      }
      if (data.phase && onPhase) {
        onPhase(data.phase);
      }
      if (data.token) {
        onToken(data.token);
      }
      if (data.tool_use && onToolUse) {
        onToolUse(data.tool_use as ToolUseEvent);
      }
      if (data.tool_result && onToolResult) {
        onToolResult(data.tool_result as ToolResultEvent);
      }
      if (data.piece && onPiece) {
        onPiece(data.piece as Piece);
      }
      // data.done is the terminal event — no action needed
    }
  }
}
