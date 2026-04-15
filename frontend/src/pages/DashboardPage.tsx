import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import WriterCard from '../components/WriterCard';
import { useWriterStore } from '../stores/writerStore';

export default function DashboardPage() {
  const navigate = useNavigate();
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
          onClick={() => navigate('/writers/new')}
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
          <p>Describe the artist you want and we'll build the first version together.</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate('/writers/new')}
          >
            Create your first writer
          </button>
        </div>
      ) : (
        <div className="writer-grid">
          {writers.map((writer) => (
            <WriterCard key={writer.id} writer={writer} />
          ))}
        </div>
      )}
    </div>
  );
}
