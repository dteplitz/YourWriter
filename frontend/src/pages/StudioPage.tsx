import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Brief, Piece, Writer } from '../types';
import * as api from '../api/client';
import StudioTransition from '../components/StudioTransition';
import BriefSetup from '../components/BriefSetup';
import SessionExperience from '../components/SessionExperience';
import './writing.css';

type StudioStep = 'transition' | 'brief' | 'session';

export default function StudioPage() {
  const { writerId } = useParams<{ writerId: string }>();
  const navigate = useNavigate();

  const [writer, setWriter] = useState<Writer | null>(null);
  const [step, setStep] = useState<StudioStep>('transition');
  const [brief, setBrief] = useState<Brief | null>(null);
  const [pieces, setPieces] = useState<Piece[]>([]);
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
      const [writerData, piecesData] = await Promise.all([
        api.getWriter(id),
        api.getPieces(id).catch(() => [] as Piece[]),
      ]);
      setWriter(writerData);
      setPieces(piecesData);
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

  const recentPiece = pieces.length > 0 ? pieces[pieces.length - 1] : undefined;

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

      {step === 'transition' && (
        <StudioTransition
          writer={writer}
          recentPiece={recentPiece}
          onEnter={() => setStep('brief')}
        />
      )}

      {step === 'brief' && (
        <BriefSetup
          writerId={writerId}
          onStartSession={handleStartSession}
          onBack={() => setStep('transition')}
        />
      )}

      {step === 'session' && brief && (
        <SessionExperience
          writerId={writerId}
          brief={brief}
          onPieceSaved={(piece) => setPieces((prev) => [piece, ...prev])}
          onSessionEnd={() => setStep('transition')}
        />
      )}
    </div>
  );
}
