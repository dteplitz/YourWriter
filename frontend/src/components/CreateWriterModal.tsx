import { useState } from 'react';
import { useWriterStore } from '../stores/writerStore';

interface CreateWriterModalProps {
  onClose: () => void;
}

export default function CreateWriterModal({ onClose }: CreateWriterModalProps) {
  const [name, setName] = useState('');
  const [purpose, setPurpose] = useState('');
  const [styleDescription, setStyleDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { createWriter } = useWriterStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim() || !purpose.trim()) {
      setError('Name and purpose are required.');
      return;
    }

    setLoading(true);
    try {
      await createWriter({
        name: name.trim(),
        purpose: purpose.trim(),
        style_description: styleDescription.trim(),
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create writer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Writer</h2>
          <button className="modal-close" onClick={onClose}>
            x
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="writer-name">Name</label>
            <input
              id="writer-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My Tweet Writer"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="writer-purpose">Purpose</label>
            <input
              id="writer-purpose"
              type="text"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="e.g., Write engaging tweets about technology"
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label htmlFor="writer-style">Style Description (plain English)</label>
            <textarea
              id="writer-style"
              value={styleDescription}
              onChange={(e) => setStyleDescription(e.target.value)}
              placeholder="e.g., Casual and witty, uses short punchy sentences, occasionally uses humor"
              rows={4}
              disabled={loading}
            />
          </div>
          {error && <div className="form-error">{error}</div>}
          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Writer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
