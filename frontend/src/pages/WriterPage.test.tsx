import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import WriterPage from './WriterPage';
import { useWriterStore } from '../stores/writerStore';

vi.mock('../api/client', () => ({
  getWriter: vi.fn(),
  getWriterSessionsSummary: vi.fn(),
  getIdentity: vi.fn(),
}));

vi.mock('../components/ChatPanel', () => ({
  default: () => <div>Chat mock</div>,
}));

vi.mock('../components/ConfigPanel', () => ({
  default: () => <div>Config mock</div>,
}));

vi.mock('../components/EvolutionFeed', () => ({
  default: () => <div>Evolution mock</div>,
}));

import * as api from '../api/client';

const mockWriter = {
  id: '7',
  user_id: '3',
  name: 'Ariadna',
  purpose: 'Urban melancholy',
  created_at: '2026-04-13T12:00:00Z',
  updated_at: '2026-04-13T12:00:00Z',
};

describe('WriterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWriterStore.setState({ selectedWriter: null, writers: [] });
    vi.mocked(api.getWriter).mockResolvedValue(mockWriter);
    vi.mocked(api.getWriterSessionsSummary).mockResolvedValue({
      highlight: {
        id: 12,
        writer_id: 7,
        lifecycle: 'active',
        brief_preview: 'IA como paisaje cotidiano · column · tono sobrio',
        take_count: 2,
        created_at: '2026-04-14T16:00:00Z',
        updated_at: '2026-04-14T16:20:00Z',
        last_take: {
          id: 33,
          take_number: 2,
          title: 'El Ruido de Fondo',
          word_count: 118,
          created_at: '2026-04-14T16:20:00Z',
        },
      },
      history: [
        {
          id: 12,
          writer_id: 7,
          lifecycle: 'active',
          brief_preview: 'IA como paisaje cotidiano · column · tono sobrio',
          take_count: 2,
          created_at: '2026-04-14T16:00:00Z',
          updated_at: '2026-04-14T16:20:00Z',
          last_take: {
            id: 33,
            take_number: 2,
            title: 'El Ruido de Fondo',
            word_count: 118,
            created_at: '2026-04-14T16:20:00Z',
          },
        },
      ],
    });
  });

  it('renders the compact session card and history when sessions exist', async () => {
    render(
      <MemoryRouter initialEntries={['/writer/7']}>
        <Routes>
          <Route path="/writer/:id" element={<WriterPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Chat mock')).toBeInTheDocument();
    });

    expect(screen.getByText(/Estado de sesion/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Retomar sesion/i })).toBeInTheDocument();
    expect(screen.getByText(/Historial de sesiones/i)).toBeInTheDocument();
    expect(screen.getByText(/Sesion #12/i)).toBeInTheDocument();
  });

  it('keeps the writer page focused when there are no sessions yet', async () => {
    vi.mocked(api.getWriterSessionsSummary).mockResolvedValueOnce({
      highlight: null,
      history: [],
    });

    render(
      <MemoryRouter initialEntries={['/writer/7']}>
        <Routes>
          <Route path="/writer/:id" element={<WriterPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Chat mock')).toBeInTheDocument();
    });

    expect(screen.queryByText(/Estado de sesion/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Historial de sesiones/i)).not.toBeInTheDocument();
  });
});
