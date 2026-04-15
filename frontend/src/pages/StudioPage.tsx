import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import type {
  Brief,
  Piece,
  SessionDetailResponse,
  SessionSummaryItem,
  Writer,
  WriterSessionsSummaryResponse,
} from '../types';
import * as api from '../api/client';
import BriefSetup from '../components/BriefSetup';
import SessionExperience from '../components/SessionExperience';
import '../writing.css';

type StudioStep = 'brief' | 'session';

interface StudioPageLocationState {
  resumeSessionId?: number;
}

const EMPTY_SESSION_SUMMARY: WriterSessionsSummaryResponse = {
  highlight: null,
  history: [],
};

export default function StudioPage() {
  const { writerId } = useParams<{ writerId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [writer, setWriter] = useState<Writer | null>(null);
  const [step, setStep] = useState<StudioStep>('brief');
  const [brief, setBrief] = useState<Brief | null>(null);
  const [initialSessionId, setInitialSessionId] = useState<number | null>(null);
  const [initialPiece, setInitialPiece] = useState<Piece | null>(null);
  const [autoStartSession, setAutoStartSession] = useState(true);
  const [loading, setLoading] = useState(true);
  const [sessionsSummary, setSessionsSummary] = useState<WriterSessionsSummaryResponse>(EMPTY_SESSION_SUMMARY);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [completeNoticeDismissed, setCompleteNoticeDismissed] = useState(false);

  useEffect(() => {
    if (!writerId) {
      navigate('/');
      return;
    }
    void loadData(writerId);
  }, [writerId]);

  const loadData = async (id: string) => {
    setLoading(true);
    setResumeError(null);

    try {
      const [writerData, summaryData] = await Promise.all([
        api.getWriter(id),
        api.getWriterSessionsSummary(id).catch(() => EMPTY_SESSION_SUMMARY),
      ]);

      setWriter(writerData);
      setSessionsSummary(summaryData);
      setCompleteNoticeDismissed(false);

      const state = location.state as StudioPageLocationState | null;
      const activeSession =
        summaryData.highlight?.lifecycle === 'active' ? summaryData.highlight : null;

      if (state?.resumeSessionId && activeSession?.id === state.resumeSessionId) {
        await resumeSession(activeSession);
      } else {
        setStep('brief');
        setBrief(null);
        setInitialSessionId(null);
        setInitialPiece(null);
        setAutoStartSession(true);
      }

      if (state?.resumeSessionId) {
        navigate(location.pathname, { replace: true, state: null });
      }
    } catch {
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const resumeSession = async (session: SessionSummaryItem) => {
    setActionLoading(true);
    setResumeError(null);
    try {
      const detail = await api.getSessionDetail(session.id);
      openResumedSession(detail);
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : 'No pudimos retomar la sesion.');
    } finally {
      setActionLoading(false);
    }
  };

  const openResumedSession = (detail: SessionDetailResponse) => {
    setBrief(detail.brief);
    setInitialSessionId(detail.id);
    if (detail.resume_mode === 'artifact') {
      const lastTake = detail.takes[detail.takes.length - 1];
      setInitialPiece(lastTake ? {
        id: lastTake.id,
        writer_id: detail.writer_id,
        title: lastTake.title || `Take ${lastTake.take_number}`,
        content: lastTake.content,
        format: detail.brief.format,
        word_count: lastTake.word_count,
        created_at: lastTake.created_at,
      } : null);
      setAutoStartSession(false);
    } else {
      setInitialPiece(null);
      setAutoStartSession(true);
    }
    setStep('session');
  };

  const abandonAndStartNew = async (sessionId: number) => {
    if (!writerId) return;
    setActionLoading(true);
    setResumeError(null);
    try {
      await api.abandonSession(sessionId);
      const summary = await api.getWriterSessionsSummary(writerId).catch(() => EMPTY_SESSION_SUMMARY);
      setSessionsSummary(summary);
      setStep('brief');
      setBrief(null);
      setInitialSessionId(null);
      setInitialPiece(null);
      setAutoStartSession(true);
      setCompleteNoticeDismissed(false);
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : 'No pudimos abrir una nueva sesion.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartSession = (nextBrief: Brief) => {
    setBrief(nextBrief);
    setInitialSessionId(null);
    setInitialPiece(null);
    setAutoStartSession(true);
    setStep('session');
  };

  if (loading || !writer || !writerId) {
    return (
      <div className="studio-page">
        <div className="session-placeholder">Cargando Studio...</div>
      </div>
    );
  }

  const activeSession =
    sessionsSummary.highlight?.lifecycle === 'active' ? sessionsSummary.highlight : null;
  const completeSession =
    !activeSession && sessionsSummary.highlight?.lifecycle === 'complete'
      ? sessionsSummary.highlight
      : null;

  return (
    <div className="studio-page">
      <nav className="studio-nav">
        <button className="btn btn-secondary" onClick={() => navigate('/writer/' + writerId)}>
          ← Artist Profile
        </button>
        <span className="studio-nav-title">Studio · {writer.name}</span>
        <div style={{ minWidth: '120px' }} />
      </nav>

      {step === 'brief' && activeSession && (
        <div className="studio-session-gate-shell">
          <section className="studio-session-gate">
            <span className="studio-session-gate-kicker">Antes de entrar al Studio</span>
            <h2>Ya hay una sesion abierta para este writer</h2>
            <p>
              El Studio se trata como un evento de trabajo persistente. Si ya hay una
              sesion activa, la decision fuerte vive en la puerta del Studio.
            </p>

            <div className="studio-session-gate-options">
              <article className="studio-session-gate-option">
                <strong>Retomar sesion</strong>
                <p>
                  Volves a la sesion #{activeSession.id}. Se conservan brief, takes,
                  notas y progreso del runtime.
                </p>
              </article>

              <article className="studio-session-gate-option">
                <strong>Empezar nueva sesion</strong>
                <p>
                  La sesion activa pasa a `abandoned` y arrancas una nueva desde cero.
                </p>
              </article>
            </div>

            {resumeError && (
              <div className="form-error" role="alert">
                {resumeError}
              </div>
            )}

            <div className="studio-session-gate-actions">
              <button
                className="btn btn-primary"
                onClick={() => void resumeSession(activeSession)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Retomando...' : `Retomar sesion #${activeSession.id}`}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => void abandonAndStartNew(activeSession.id)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Preparando...' : 'Empezar nueva'}
              </button>
            </div>
          </section>
        </div>
      )}

      {step === 'brief' && !activeSession && (
        <BriefSetup
          writer={writer}
          onStartSession={handleStartSession}
          onBack={() => navigate('/writer/' + writerId)}
          notice={
            completeSession && !completeNoticeDismissed ? (
              <div className="studio-complete-notice">
                <strong>Tenes una sesion pendiente de revision</strong>
                <p>
                  La escritura termino en la sesion #{completeSession.id}. Podes revisar
                  el import antes de abrir otra, o seguir igual si ahora solo queres
                  armar un brief nuevo.
                </p>
                <div className="studio-complete-notice-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => navigate(`/studio/${writerId}/import/${completeSession.id}`)}
                  >
                    Revisar import
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setCompleteNoticeDismissed(true)}
                  >
                    Continuar igual
                  </button>
                </div>
              </div>
            ) : null
          }
        />
      )}

      {step === 'session' && brief && (
        <SessionExperience
          writerId={writerId}
          brief={brief}
          initialSessionId={initialSessionId}
          initialPiece={initialPiece}
          autoStart={autoStartSession}
          onSessionEnd={(sessionId) => {
            if (sessionId) {
              navigate(`/studio/${writerId}/import/${sessionId}`, { replace: true });
              return;
            }
            navigate('/writer/' + writerId, { replace: true });
          }}
        />
      )}
    </div>
  );
}
