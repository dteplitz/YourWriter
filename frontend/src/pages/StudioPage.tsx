import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Brief, Writer } from '../types';
import * as api from '../api/client';
import BriefSetup from '../components/BriefSetup';
import SessionExperience from '../components/SessionExperience';
import '../writing.css';

type StudioStep = 'brief' | 'session';

export default function StudioPage() {
  const { writerId } = useParams<{ writerId: string }>();
  const navigate = useNavigate();

  const [writer, setWriter] = useState<Writer | null>(null);
  const [step, setStep] = useState<StudioStep>('brief');
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!writerId) {
      navigate('/');
      return;
    }
    loadData(writerId);
  }, [writerId]);

  const loadData = async (id: string) => {
    setLoading(true);
    try {
      const writerData = await api.getWriter(id);
      setWriter(writerData);
    } catch {
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSession = (b: Brief) => {
    setBrief(b);
    setStep('session');
  };

  if (loading || !writer || !writerId) {
    return (
      <div className="studio-page">
        <div className="session-placeholder">Cargando Studio...</div>
      </div>
    );
  }

  return (
    <div className="studio-page">
      <nav className="studio-nav">
        <button
          className="btn btn-secondary"
          onClick={() => navigate('/writer/' + writerId)}
        >
          ← Artist Profile
        </button>
        <span className="studio-nav-title">Studio · {writer.name}</span>
        <div style={{ minWidth: '120px' }} />
      </nav>

      {step === 'brief' && (
        <BriefSetup
          writer={writer}
          onStartSession={handleStartSession}
          onBack={() => navigate('/writer/' + writerId)}
        />
      )}

      {step === 'session' && brief && (
        <SessionExperience
          writerId={writerId}
          brief={brief}
          onPieceSaved={() => {}}
          onSessionEnd={() => setStep('brief')}
        />
      )}
    </div>
  );
}
