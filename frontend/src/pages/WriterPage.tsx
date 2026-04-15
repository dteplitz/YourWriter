import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ChatPanel from '../components/ChatPanel';
import ConfigPanel from '../components/ConfigPanel';
import EvolutionFeed from '../components/EvolutionFeed';
import SessionHistory from '../components/SessionHistory';
import SessionStatusCard from '../components/SessionStatusCard';
import { useWriterStore } from '../stores/writerStore';
import type {
  EvolutionDetectedEvent,
  Identity,
  SessionDetailResponse,
  SessionImportFeedback,
  WriterSessionsSummaryResponse,
} from '../types';
import * as api from '../api/client';

interface WriterPageLocationState {
  sessionImportFeedback?: SessionImportFeedback;
  openSessionId?: number;
}

function summarizeImportedChanges(feedback: SessionImportFeedback | null): string {
  if (!feedback || feedback.status !== 'imported' || !feedback.importedChanges?.length) {
    return '';
  }

  const summary = feedback.importedChanges
    .slice(0, 3)
    .map((change) => (change.key ? `${change.action} ${change.field}.${change.key}` : `${change.action} ${change.field}`))
    .join(' · ');

  if (feedback.importedChanges.length > 3) {
    return `${summary} · +${feedback.importedChanges.length - 3} mas`;
  }

  return summary;
}

const EMPTY_SESSION_SUMMARY: WriterSessionsSummaryResponse = {
  highlight: null,
  history: [],
};

export default function WriterPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { selectedWriter, selectWriter } = useWriterStore();
  const [loading, setLoading] = useState(true);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [heroVisible, setHeroVisible] = useState(true);
  const [pendingEvolution, setPendingEvolution] = useState<EvolutionDetectedEvent | null>(null);
  const [sessionImportFeedback, setSessionImportFeedback] = useState<SessionImportFeedback | null>(null);
  const [sessionsSummary, setSessionsSummary] = useState<WriterSessionsSummaryResponse>(EMPTY_SESSION_SUMMARY);
  const [sessionDetailsById, setSessionDetailsById] = useState<Record<number, SessionDetailResponse>>({});
  const [expandedSessionId, setExpandedSessionId] = useState<number | null>(null);
  const [loadingDetailIds, setLoadingDetailIds] = useState<number[]>([]);
  const [pendingOpenSessionId, setPendingOpenSessionId] = useState<number | null>(null);
  const heroRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const historyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) {
      navigate('/');
      return;
    }
    void loadWriter(id);
    return () => {
      selectWriter(null);
    };
  }, [id]);

  useEffect(() => {
    const page = pageRef.current;
    if (!page) return;
    page.scrollTop = 0;
    const check = () => {
      const hero = heroRef.current;
      if (!hero) return;
      setHeroVisible(hero.getBoundingClientRect().bottom > 150);
    };
    page.addEventListener('scroll', check, { passive: true });
    check();
    return () => page.removeEventListener('scroll', check);
  }, [loading]);

  useEffect(() => {
    const state = location.state as WriterPageLocationState | null;
    if (!state) return;

    if (state.sessionImportFeedback) {
      setSessionImportFeedback(state.sessionImportFeedback);
      if (id) {
        void loadSessions(id);
      }
    }

    if (state.openSessionId) {
      setPendingOpenSessionId(state.openSessionId);
    }

    navigate(location.pathname, { replace: true, state: null });
  }, [location.key]);

  useEffect(() => {
    if (!pendingOpenSessionId) return;
    void openSessionDetail(pendingOpenSessionId, { forceOpen: true, scroll: true });
    setPendingOpenSessionId(null);
  }, [pendingOpenSessionId]);

  const loadWriter = async (writerId: string) => {
    setLoading(true);
    setSessionsSummary(EMPTY_SESSION_SUMMARY);
    setSessionDetailsById({});
    setExpandedSessionId(null);
    try {
      const writer = await api.getWriter(writerId);
      selectWriter(writer);
      await loadSessions(writerId);
    } catch {
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async (writerId: string) => {
    try {
      const summary = await api.getWriterSessionsSummary(writerId);
      setSessionsSummary(summary);
    } catch {
      setSessionsSummary(EMPTY_SESSION_SUMMARY);
    }
  };

  const openSessionDetail = async (
    sessionId: number,
    options: { forceOpen?: boolean; scroll?: boolean } = {},
  ) => {
    if (!options.forceOpen && expandedSessionId === sessionId) {
      setExpandedSessionId(null);
      return;
    }

    setExpandedSessionId(sessionId);

    if (options.scroll) {
      historyRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (sessionDetailsById[sessionId] || loadingDetailIds.includes(sessionId)) {
      return;
    }

    setLoadingDetailIds((current) => [...current, sessionId]);
    try {
      const detail = await api.getSessionDetail(sessionId);
      setSessionDetailsById((current) => ({ ...current, [sessionId]: detail }));
    } finally {
      setLoadingDetailIds((current) => current.filter((value) => value !== sessionId));
    }
  };

  const handleResumeSession = (sessionId: number) => {
    navigate('/studio/' + id, {
      state: {
        resumeSessionId: sessionId,
      },
    });
  };

  const handleReviewImport = (sessionId: number) => {
    navigate(`/studio/${id}/import/${sessionId}`);
  };

  const highlight =
    sessionsSummary.highlight &&
    (sessionsSummary.highlight.lifecycle === 'active' ||
      sessionsSummary.highlight.lifecycle === 'complete')
      ? sessionsSummary.highlight
      : null;

  if (loading || !selectedWriter || !id) {
    return <div className="writer-page-loading">Loading writer...</div>;
  }

  const showRpgStrip = !heroVisible && identity !== null;
  const emotions = identity
    ? Object.entries(identity.emotions)
        .filter(([, value]) => typeof value === 'number')
        .slice(0, 5)
    : [];
  const traits = identity ? Object.entries(identity.personality).slice(0, 3) : [];
  const importedSummary = summarizeImportedChanges(sessionImportFeedback);

  return (
    <div ref={pageRef} className="writer-page">
      <div className="writer-sticky-header">
        <div className="writer-page-header">
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            Back
          </button>
          <div className="writer-page-header-info">
            <h2>{selectedWriter.name}</h2>
            <span className="writer-purpose">{selectedWriter.purpose}</span>
          </div>
          <div style={{ minWidth: '80px' }} />
        </div>

        <div className={`writer-rpg-strip${showRpgStrip ? ' writer-rpg-strip--visible' : ''}`}>
          {emotions.map(([key, value]) => {
            const pct = Math.round(Math.min(1, value as number) * 100);
            return (
              <span key={key} className="rpg-emotion-mini">
                <span className="rpg-emotion-mini-label">{key}</span>
                <span className="rpg-emotion-mini-bar">
                  <span className="rpg-emotion-mini-fill" style={{ width: `${pct}%` }} />
                </span>
                <span className="rpg-emotion-mini-val">{pct}%</span>
              </span>
            );
          })}
          {traits.map(([key, value]) => (
            <span key={key} className="rpg-trait-chip">
              {key}: {String(value)}
            </span>
          ))}
        </div>
      </div>

      {sessionImportFeedback && (
        <div
          className={`writer-session-banner writer-session-banner--${sessionImportFeedback.status}`}
          role="status"
        >
          <div className="writer-session-banner-copy">
            <strong>
              {sessionImportFeedback.status === 'imported'
                ? 'El writer evoluciono por esta sesion.'
                : 'La sesion se cerro sin importar cambios.'}
            </strong>
            {sessionImportFeedback.status === 'imported' && importedSummary && (
              <span>{importedSummary}</span>
            )}
          </div>
          <button
            className="writer-session-banner-dismiss"
            onClick={() => setSessionImportFeedback(null)}
            aria-label="Cerrar mensaje"
          >
            x
          </button>
        </div>
      )}

      <div ref={heroRef} className="writer-hero">
        <ConfigPanel
          writerId={id}
          onIdentityLoaded={setIdentity}
          pendingEvolution={pendingEvolution}
          onEvolutionAccepted={() => setPendingEvolution(null)}
          onEvolutionRollback={() => {
            setPendingEvolution(null);
            api.getIdentity(id).then(setIdentity).catch(() => {});
          }}
        />
      </div>

      <div className="writer-below-fold">
        <div className="writer-chat-col">
          <ChatPanel
            writerId={id}
            onEnterStudio={() => navigate('/studio/' + id)}
            onEvolution={(event) => {
              setPendingEvolution(event);
              api.getIdentity(id).then(setIdentity).catch(() => {});
            }}
          />
        </div>

        <div className="writer-sidebar-col">
          {highlight && (
            <SessionStatusCard
              session={highlight}
              onResume={handleResumeSession}
              onReviewImport={handleReviewImport}
              onViewSession={(sessionId) => {
                void openSessionDetail(sessionId, { forceOpen: true, scroll: true });
              }}
            />
          )}

          <div className="writer-evolution-col">
            <EvolutionFeed
              writerId={id}
              autoEvolutionEvent={pendingEvolution}
              onOpenSession={(sessionId) => {
                void openSessionDetail(sessionId, { forceOpen: true, scroll: true });
              }}
            />
          </div>
        </div>
      </div>

      {sessionsSummary.history.length > 0 && (
        <div ref={historyRef} className="writer-session-history-shell">
          <SessionHistory
            history={sessionsSummary.history}
            detailsById={sessionDetailsById}
            loadingDetailIds={loadingDetailIds}
            expandedSessionId={expandedSessionId}
            onToggleSession={(sessionId) => {
              void openSessionDetail(sessionId);
            }}
            onResume={handleResumeSession}
            onReviewImport={handleReviewImport}
          />
        </div>
      )}
    </div>
  );
}
