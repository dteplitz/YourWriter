import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import WriterInitializationPage from './WriterInitializationPage';

vi.mock('../api/client', () => ({
  initializeWriterPreview: vi.fn(),
  createWriterFromPreview: vi.fn(),
}));

import * as api from '../api/client';

const mockPreview = {
  summary: 'Una ensayista sobria de observación cotidiana.',
  name: 'Lina Mercer',
  purpose: 'Escribir ensayos breves sobre tecnología y vida cotidiana.',
  personality: { voice: 'clean', humor: 'dry' },
  emotions: { melancholy: 0.72, curiosity: 0.58 },
  topics: ['technology', 'city'],
  constraints: { tone: 'Avoid corporate tone' },
  lifelong_objectives: ['Name the emotional effect of the internet on urban life.'],
};

describe('WriterInitializationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('generates a preview from free-text description', async () => {
    vi.mocked(api.initializeWriterPreview).mockResolvedValue(mockPreview);

    render(
      <MemoryRouter initialEntries={['/writers/new']}>
        <Routes>
          <Route path="/writers/new" element={<WriterInitializationPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Texto libre/i), {
      target: {
        value: 'Quiero una ensayista de tecnología y vida cotidiana con humor seco.',
      },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generar configuración/i }));

    await waitFor(() => {
      expect(screen.getByText('Lina Mercer')).toBeInTheDocument();
    });

    expect(screen.getByText(/Secondary Seeds/i)).toBeInTheDocument();
    expect(sessionStorage.getItem('writer-initialization-draft-v1')).toContain('Lina Mercer');
  });

  it('restores the saved draft and creates a writer from preview', async () => {
    sessionStorage.setItem(
      'writer-initialization-draft-v1',
      JSON.stringify({
        description: 'Quiero una ensayista de tecnología y vida cotidiana.',
        preview: mockPreview,
      }),
    );
    vi.mocked(api.createWriterFromPreview).mockResolvedValue({
      id: '17',
      user_id: '4',
      name: 'Lina Mercer',
      purpose: 'Escribir ensayos breves sobre tecnología y vida cotidiana.',
      created_at: '2026-04-15T18:00:00Z',
      updated_at: '2026-04-15T18:00:00Z',
    });

    render(
      <MemoryRouter initialEntries={['/writers/new']}>
        <Routes>
          <Route path="/writers/new" element={<WriterInitializationPage />} />
          <Route path="/writer/:id" element={<div>Writer route reached</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Lina Mercer')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Crear writer/i }));

    await waitFor(() => {
      expect(screen.getByText(/Writer route reached/i)).toBeInTheDocument();
    });

    expect(api.createWriterFromPreview).toHaveBeenCalledWith(mockPreview);
    expect(sessionStorage.getItem('writer-initialization-draft-v1')).toBeNull();
  });
});
