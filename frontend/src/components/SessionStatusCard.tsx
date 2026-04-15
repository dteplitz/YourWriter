import type { SessionSummaryItem } from '../types';

interface SessionStatusCardProps {
  session: SessionSummaryItem;
  onResume: (sessionId: number) => void;
  onReviewImport: (sessionId: number) => void;
  onViewSession: (sessionId: number) => void;
}

function getCardCopy(session: SessionSummaryItem): string {
  if (session.lifecycle === 'active') {
    return 'El Studio ya arranco. Brief, takes y notas siguen disponibles sin obligarte a dejar de conversar.';
  }
  return 'La escritura termino y quedo lista para revisar. Este estado sigue visible, pero con menos urgencia que una sesion abierta.';
}

export default function SessionStatusCard({
  session,
  onResume,
  onReviewImport,
  onViewSession,
}: SessionStatusCardProps) {
  const isActive = session.lifecycle === 'active';

  return (
    <section className="writer-session-card-shell">
      <div className="writer-sidebar-title-row">
        <h3>Estado de sesion</h3>
        <span className="writer-sidebar-caption">
          {isActive ? 'Visible, sin competir con el chat' : 'Un escalon abajo de active'}
        </span>
      </div>

      <div className={`writer-session-card writer-session-card--${session.lifecycle}`}>
        <div className="writer-session-card-kicker">
          {isActive ? 'Sesion en progreso' : 'Sesion pendiente de revision'}
        </div>
        <h4 className="writer-session-card-title">
          {isActive
            ? 'Hay una sesion abierta lista para retomar'
            : 'La escritura termino. Falta decidir que importar'}
        </h4>
        <p className="writer-session-card-copy">{getCardCopy(session)}</p>

        <div className="writer-session-card-meta">
          <div className="writer-session-card-meta-label">
            {session.last_take ? 'Ultimo take' : 'Resumen'}
          </div>
          <div className="writer-session-card-meta-copy">
            {session.last_take ? (
              <>
                Take {session.last_take.take_number}
                {session.last_take.title ? ` · "${session.last_take.title}"` : ''}
                <br />
                {session.last_take.word_count} palabras
              </>
            ) : (
              session.brief_preview
            )}
          </div>
        </div>

        <div className="writer-session-card-actions">
          <button
            className="btn btn-primary"
            onClick={() => (isActive ? onResume(session.id) : onReviewImport(session.id))}
          >
            {isActive ? 'Retomar sesion' : 'Revisar import'}
          </button>
          <button className="btn btn-secondary" onClick={() => onViewSession(session.id)}>
            Ver sesion
          </button>
        </div>
      </div>
    </section>
  );
}
