import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ChatPanel from '../components/ChatPanel';
import ConfigPanel from '../components/ConfigPanel';
import EvolutionFeed from '../components/EvolutionFeed';
import { useWriterStore } from '../stores/writerStore';
import * as api from '../api/client';

export default function WriterPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { selectedWriter, selectWriter } = useWriterStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) {
      navigate('/');
      return;
    }
    loadWriter(id);
    return () => {
      selectWriter(null);
    };
  }, [id]);

  const loadWriter = async (writerId: string) => {
    setLoading(true);
    try {
      const writer = await api.getWriter(writerId);
      selectWriter(writer);
    } catch {
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  if (loading || !selectedWriter || !id) {
    return <div className="writer-page-loading">Loading writer...</div>;
  }

  return (
    <div className="writer-page">
      <div className="writer-page-header">
        <button className="btn btn-secondary" onClick={() => navigate('/')}>
          Back
        </button>
        <h2>{selectedWriter.name}</h2>
        <span className="writer-purpose">{selectedWriter.purpose}</span>
      </div>
      <div className="writer-page-content">
        <div className="writer-column writer-column--config">
          <ConfigPanel writerId={id} />
        </div>
        <div className="writer-column writer-column--chat">
          <ChatPanel writerId={id} />
        </div>
        <div className="writer-column writer-column--evolution">
          <EvolutionFeed writerId={id} />
        </div>
      </div>
    </div>
  );
}
