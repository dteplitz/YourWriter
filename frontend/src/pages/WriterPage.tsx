import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import ChatPanel from '../components/ChatPanel';
import ConfigPanel from '../components/ConfigPanel';
import EvolutionFeed from '../components/EvolutionFeed';
import { useWriterStore } from '../stores/writerStore';
import type { Identity, EvolutionDetectedEvent } from '../types';
import type { SessionImportFeedback } from '../types/studio';
import * as api from '../api/client';

interface WriterPageLocationState {
  sessionImportFeedback?: SessionImportFeedback;
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
  const heroRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);

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

  // Watch when the config hero scrolls out of view (scroll-event based, more predictable)
  // Also resets scroll to top when the writer-page div first mounts (loading → false).
  // The ref is null during loading state, so we reset here where pageRef is guaranteed valid.
  useEffect(() => {
    const page = pageRef.current;
    if (!page) return;
    page.scrollTop = 0;
    const check = () => {
      const hero = heroRef.current;
      if (!hero) return;
      // heroBottom < 150: hero has scrolled above the visible content area (both headers ~118px)
      setHeroVisible(hero.getBoundingClientRect().bottom > 150);
    };
    page.addEventListener('scroll', check, { passive: true });
    check();
    return () => page.removeEventListener('scroll', check);
  }, [loading]);

  useEffect(() => {
    const state = location.state as WriterPageLocationState | null;
    if (!state?.sessionImportFeedback) return;

    setSessionImportFeedback(state.sessionImportFeedback);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.key]);

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

  const showRpgStrip = !heroVisible && identity !== null;
  const emotions = identity
    ? Object.entries(identity.emotions)
        .filter(([, v]) => typeof v === 'number')
        .slice(0, 5)
    : [];
  const traits = identity ? Object.entries(identity.personality).slice(0, 3) : [];
  const importedSummary = summarizeImportedChanges(sessionImportFeedback);

  return (
    <div ref={pageRef} className="writer-page">
      {/* Sticky header — always visible, gains RPG strip when hero scrolls out */}
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

        {/* RPG stats strip — slides in when config hero is out of view */}
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

      {/* Hero: Artist Profile */}
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

      {/* Below the fold: Chat + Evolution */}
      <div className="writer-below-fold">
        <div className="writer-chat-col">
          <ChatPanel
            writerId={id}
            onEnterStudio={() => navigate('/studio/' + id)}
            onEvolution={(event) => {
              setPendingEvolution(event);
              // Reload identity from server to reflect the evolved state
              api.getIdentity(id).then(setIdentity).catch(() => {});
            }}
          />
        </div>
        <div className="writer-evolution-col">
          <EvolutionFeed writerId={id} autoEvolutionEvent={pendingEvolution} />
        </div>
      </div>
    </div>
  );
}
