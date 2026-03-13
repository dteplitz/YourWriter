import { useState, useEffect } from 'react';
import WriterCard from '../components/WriterCard';
import CreateWriterModal from '../components/CreateWriterModal';
import { useWriterStore } from '../stores/writerStore';

export default function DashboardPage() {
  const [showCreate, setShowCreate] = useState(false);
  const { writers, fetchWriters } = useWriterStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadWriters();
  }, []);

  const loadWriters = async () => {
    setLoading(true);
    setError('');
    try {
      await fetchWriters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load writers');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h2>Your Writers</h2>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreate(true)}
        >
          + Create Writer
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      {loading ? (
        <div className="dashboard-loading">Loading writers...</div>
      ) : writers.length === 0 ? (
        <div className="dashboard-empty">
          <p>You haven't created any writers yet.</p>
          <p>Click "Create Writer" to get started.</p>
        </div>
      ) : (
        <div className="writer-grid">
          {writers.map((writer) => (
            <WriterCard key={writer.id} writer={writer} />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateWriterModal onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
