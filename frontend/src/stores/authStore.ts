import { create } from 'zustand';
import type { User } from '../types';
import * as api from '../api/client';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  initFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),

  login: async (email: string, password: string) => {
    const result = await api.login({ email, password });
    localStorage.setItem('token', result.access_token);
    set({
      token: result.access_token,
      isAuthenticated: true,
      user: { id: 0, email, created_at: '' },
    });
  },

  register: async (email: string, password: string) => {
    const result = await api.register({ email, password });
    localStorage.setItem('token', result.access_token);
    set({
      token: result.access_token,
      isAuthenticated: true,
      user: { id: 0, email, created_at: '' },
    });
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  initFromStorage: () => {
    const token = localStorage.getItem('token');
    if (token) {
      set({ token, isAuthenticated: true });
    }
  },
}));
