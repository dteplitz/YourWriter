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
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
