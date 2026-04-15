import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import StudioPage from './StudioPage';

vi.mock('../api/client', () => ({
  getWriter: vi.fn(),
  getWriterSessionsSummary: vi.fn(),
  getSessionDetail: vi.fn(),
  abandonSession: vi.fn(),
}));

vi.mock('../components/SessionExperience', () => ({
  default: ({
    initialSessionId,
    autoStart,
    initialPiece,
  }: {
    initialSessionId?: number | null;
    autoStart?: boolean;
    initialPiece?: { title?: string | null } | null;
  }) => (
    <div>
      Session experience mock {initialSessionId} / autoStart={String(autoStart)} / piece=
      {initialPiece?.title ?? 'none'}
    </div>
  ),
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

describe('StudioPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getWriter).mockResolvedValue(mockWriter);
  });

  it('shows the active-session gate by default', async () => {
    vi.mocked(api.getWriterSessionsSummary).mockResolvedValue({
      highlight: {
        id: 12,
        writer_id: 7,
        lifecycle: 'active',
        brief_preview: 'IA como paisaje cotidiano',
        take_count: 2,
        created_at: '2026-04-14T16:00:00Z',
        updated_at: '2026-04-14T16:20:00Z',
        last_take: null,
      },
      history: [],
    });

    render(
      <MemoryRouter initialEntries={['/studio/7']}>
        <Routes>
          <Route path="/studio/:writerId" element={<StudioPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Ya hay una sesion abierta para este writer/i)).toBeInTheDocument();
    });
  });

  it('shows a soft notice when the latest pending session is complete', async () => {
    vi.mocked(api.getWriterSessionsSummary).mockResolvedValue({
      highlight: {
        id: 11,
        writer_id: 7,
        lifecycle: 'complete',
        brief_preview: 'Revisar import',
        take_count: 3,
        created_at: '2026-04-14T14:00:00Z',
        updated_at: '2026-04-14T15:00:00Z',
        last_take: null,
      },
      history: [],
    });

    render(
      <MemoryRouter initialEntries={['/studio/7']}>
        <Routes>
          <Route path="/studio/:writerId" element={<StudioPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Tenes una sesion pendiente de revision/i)).toBeInTheDocument();
    });

    expect(screen.queryByText(/Ya hay una sesion abierta para este writer/i)).not.toBeInTheDocument();
  });

  it('opens the last artifact directly when resume comes from a completed active take', async () => {
    vi.mocked(api.getWriterSessionsSummary).mockResolvedValue({
      highlight: {
        id: 12,
        writer_id: 7,
        lifecycle: 'active',
        brief_preview: 'IA como paisaje cotidiano',
        take_count: 2,
        created_at: '2026-04-14T16:00:00Z',
        updated_at: '2026-04-14T16:20:00Z',
        last_take: null,
      },
      history: [],
    });
    vi.mocked(api.getSessionDetail).mockResolvedValue({
      id: 12,
      writer_id: 7,
      lifecycle: 'active',
      resume_mode: 'artifact',
      brief: {
        format: 'column',
        tone: 'sobrio',
        constraints_applied: [],
        word_limit: 120,
        notes: 'IA como paisaje cotidiano',
        needs_clarification: false,
        clarification_question: null,
      },
      brief_preview: 'IA como paisaje cotidiano',
      take_count: 2,
      created_at: '2026-04-14T16:00:00Z',
      updated_at: '2026-04-14T16:20:00Z',
      takes: [
        {
          id: 33,
          take_number: 2,
          title: 'El Ruido de Fondo',
          content: 'La IA ya no irrumpe: se filtra como ruido de fondo.',
          word_count: 10,
          iteration_notes: 'Mas sobrio',
          created_at: '2026-04-14T16:20:00Z',
        },
      ],
    });

    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: '/studio/7',
            state: { resumeSessionId: 12 },
          },
        ]}
      >
        <Routes>
          <Route path="/studio/:writerId" element={<StudioPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Session experience mock 12 \/ autoStart=false \/ piece=El Ruido de Fondo/i),
      ).toBeInTheDocument();
    });
  });
});
