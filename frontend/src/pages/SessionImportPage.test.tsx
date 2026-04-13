import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SessionImportPage from './SessionImportPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ writerId: '7', sessionId: '123' }),
  };
});

vi.mock('../api/client', () => ({
  getWriter: vi.fn(),
  createSessionImportProposal: vi.fn(),
  importSessionChanges: vi.fn(),
  skipSessionImport: vi.fn(),
}));

import * as api from '../api/client';

const mockWriter = {
  id: '7',
  user_id: '3',
  name: 'Nocturna',
  purpose: 'Dark urban fiction',
  created_at: '2026-04-13T12:00:00Z',
  updated_at: '2026-04-13T12:00:00Z',
};

const proposalWithChanges = {
  session_id: 123,
  writer_id: 7,
  lifecycle: 'complete' as const,
  reasoning: 'The session reinforced melancholy and a new urban decay topic.',
  changes: [
    {
      field: 'emotions',
      action: 'modify' as const,
      key: 'melancholy',
      old_value: 0.3,
      new_value: 0.45,
      reason: 'Repeated darker framing across the takes.',
    },
    {
      field: 'topics',
      action: 'add' as const,
      value: 'urban decay',
      reason: 'The imagery became a stable theme.',
    },
  ],
};

describe('SessionImportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.getWriter).mockResolvedValue(mockWriter);
    vi.mocked(api.createSessionImportProposal).mockResolvedValue(proposalWithChanges);
    vi.mocked(api.importSessionChanges).mockResolvedValue({
      session_id: 123,
      writer_id: 7,
      lifecycle: 'imported',
      imported_changes: [proposalWithChanges.changes[0]],
      reasoning: proposalWithChanges.reasoning,
      identity: {
        id: 12,
        writer_id: 7,
        personality: {},
        emotions: { melancholy: 0.45 },
        memories: [],
        topics: ['urban decay'],
        constraints: {},
        lifelong_objectives: [],
        version: 4,
        created_at: '2026-04-13T13:00:00Z',
      },
    });
    vi.mocked(api.skipSessionImport).mockResolvedValue({
      session_id: 123,
      writer_id: 7,
      lifecycle: 'skipped',
    });
  });

  it('imports only the selected subset of changes', async () => {
    render(<SessionImportPage />);

    await waitFor(() => {
      expect(screen.getByText(/The session reinforced melancholy/i)).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(2);

    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole('button', { name: /Importar/i }));

    await waitFor(() => {
      expect(api.importSessionChanges).toHaveBeenCalledWith(123, {
        changes: [proposalWithChanges.changes[0]],
        reasoning: proposalWithChanges.reasoning,
      });
    });

    expect(mockNavigate).toHaveBeenCalledWith('/writer/7', {
      replace: true,
      state: {
        sessionImportFeedback: {
          status: 'imported',
          sessionId: 123,
          importedChanges: [proposalWithChanges.changes[0]],
          reasoning: proposalWithChanges.reasoning,
        },
      },
    });
  });

  it('skips automatically when the proposal is empty', async () => {
    vi.mocked(api.createSessionImportProposal).mockResolvedValueOnce({
      session_id: 123,
      writer_id: 7,
      lifecycle: 'complete',
      reasoning: 'No durable learning detected from this Studio session.',
      changes: [],
    });

    render(<SessionImportPage />);

    await waitFor(() => {
      expect(screen.getByText(/Sin aprendizaje durable/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Continuar/i }));

    await waitFor(() => {
      expect(api.skipSessionImport).toHaveBeenCalledWith(123);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/writer/7', {
      replace: true,
      state: {
        sessionImportFeedback: {
          status: 'skipped',
          sessionId: 123,
        },
      },
    });
  });

  it('lets the user skip a non-empty proposal explicitly', async () => {
    render(<SessionImportPage />);

    await waitFor(() => {
      expect(screen.getByText(/2 cambios propuestos/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Skipear/i }));

    await waitFor(() => {
      expect(api.skipSessionImport).toHaveBeenCalledWith(123);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/writer/7', {
      replace: true,
      state: {
        sessionImportFeedback: {
          status: 'skipped',
          sessionId: 123,
        },
      },
    });
  });
});
