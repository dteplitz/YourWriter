import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConfigPanel from './ConfigPanel';

// Mock the api/client module
vi.mock('../api/client', () => ({
  getIdentity: vi.fn(),
  updateIdentity: vi.fn(),
  updateConstraints: vi.fn(),
}));

import * as api from '../api/client';

const mockIdentity = {
  id: 1,
  writer_id: 1,
  personality: { voice: 'neutral', style: 'clear and concise' },
  emotions: { enthusiasm: 0.5, empathy: 0.5 },
  memories: ['First memory'],
  topics: ['fiction'],
  constraints: { maxWords: '500' },
  lifelong_objectives: ['Write compelling stories'],
  version: 3,
  created_at: '2024-01-01T00:00:00Z',
};

describe('ConfigPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getIdentity).mockResolvedValue(mockIdentity);
    vi.mocked(api.updateIdentity).mockResolvedValue(mockIdentity);
    vi.mocked(api.updateConstraints).mockResolvedValue(mockIdentity);
  });

  it('renders read-only mode by default', async () => {
    render(<ConfigPanel writerId="1" />);

    // Wait for identity to load
    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    // Should show version badge
    expect(screen.getByText('v3')).toBeTruthy();

    // Edit button should be present
    expect(screen.getByRole('button', { name: /edit/i })).toBeTruthy();

    // No edit inputs visible in read-only mode
    expect(screen.queryByPlaceholderText('key')).toBeNull();
  });

  it('toggles to edit mode when Edit button is clicked', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    const editBtn = screen.getByRole('button', { name: /edit/i });
    fireEvent.click(editBtn);

    // Should show key/value inputs
    expect(screen.getAllByPlaceholderText('key').length).toBeGreaterThan(0);

    // Should show Save Changes and Cancel buttons
    expect(screen.getByRole('button', { name: /save changes/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeTruthy();
  });

  it('discards changes on Cancel', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: /edit/i }));

    // Modify a key input
    const keyInputs = screen.getAllByPlaceholderText('key');
    fireEvent.change(keyInputs[0], { target: { value: 'modified_key' } });

    // Cancel
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    // Should be back in read-only mode with original data
    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    // Edit inputs should be gone
    expect(screen.queryByPlaceholderText('key')).toBeNull();
  });

  it('shows dirty dot when changes are made', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: /edit/i }));

    // Dirty dot should not be present initially (no changes yet)
    expect(screen.queryByTitle('Unsaved changes')).toBeNull();

    // Modify a value
    const valueInputs = screen.getAllByPlaceholderText('value');
    fireEvent.change(valueInputs[0], { target: { value: 'changed_value' } });

    // Dirty dot should now be visible
    await waitFor(() => {
      expect(screen.getByTitle('Unsaved changes')).toBeTruthy();
    });
  });

  it('calls updateIdentity and updateConstraints on Save', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: /edit/i }));

    // Change a personality value
    const valueInputs = screen.getAllByPlaceholderText('value');
    fireEvent.change(valueInputs[0], { target: { value: 'expressive' } });

    // Click Save Changes
    const saveBtn = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.updateIdentity).toHaveBeenCalledWith('1', {
        personality: expect.any(Object),
      });
      expect(api.updateConstraints).toHaveBeenCalledWith('1', {
        constraints: expect.any(Object),
      });
    });
  });

  it('shows Saved indicator after successful save', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: /edit/i }));

    // Make a change to enable save button
    const valueInputs = screen.getAllByPlaceholderText('value');
    fireEvent.change(valueInputs[0], { target: { value: 'expressive' } });

    fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(screen.getByText(/saved ✓/i)).toBeTruthy();
    });
  });

  it('shows Evolves automatically badge on Emotions and Lifelong Objectives', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/voice: neutral/i)).toBeTruthy();
    });

    const badges = screen.getAllByText('Evolves automatically');
    expect(badges.length).toBe(2);
  });

  it('does not show Evolves automatically badge on Memories or Topics', async () => {
    render(<ConfigPanel writerId="1" />);

    await waitFor(() => {
      expect(screen.getByText(/fiction/i)).toBeTruthy();
    });

    // All "Evolves automatically" badges are only 2 (Emotions + Objectives)
    const badges = screen.getAllByText('Evolves automatically');
    expect(badges.length).toBe(2);
  });
});
