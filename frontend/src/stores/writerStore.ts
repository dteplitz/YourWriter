import { create } from 'zustand';
import type { Writer, WriterCreate } from '../types';
import * as api from '../api/client';

interface WriterState {
  writers: Writer[];
  selectedWriter: Writer | null;
  fetchWriters: () => Promise<void>;
  createWriter: (data: WriterCreate) => Promise<Writer>;
  selectWriter: (writer: Writer | null) => void;
  deleteWriter: (id: string) => Promise<void>;
}

export const useWriterStore = create<WriterState>((set) => ({
  writers: [],
  selectedWriter: null,

  fetchWriters: async () => {
    const writers = await api.getWriters();
    set({ writers });
  },

  createWriter: async (data: WriterCreate) => {
    const writer = await api.createWriter(data);
    set((state) => ({ writers: [...state.writers, writer] }));
    return writer;
  },

  selectWriter: (writer: Writer | null) => {
    set({ selectedWriter: writer });
  },

  deleteWriter: async (id: string) => {
    await api.deleteWriter(id);
    set((state) => ({
      writers: state.writers.filter((w) => w.id !== id),
      selectedWriter:
        state.selectedWriter?.id === id ? null : state.selectedWriter,
    }));
  },
}));
