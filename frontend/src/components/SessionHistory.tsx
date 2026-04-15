import type { SessionDetailResponse, SessionSummaryItem } from '../types';

interface SessionHistoryProps {
  history: SessionSummaryItem[];
  detailsById: Record<number, SessionDetailResponse>;
  loadingDetailIds: number[];
  expandedSessionId: number | null;
  onToggleSession: (sessionId: number) => void;
  onResume: (sessionId: number) => void;
  onReviewImport: (sessionId: number) => void;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

export default function SessionHistory({
  history,
  detailsById,
  loadingDetailIds,
  expandedSessionId,
  onToggleSession,
  onResume,
  onReviewImport,
}: SessionHistoryProps) {
  if (history.length === 0) return null;

  return (
    <section className="writer-sessions-history">
      <div className="writer-sessions-history-header">
        <div>
          <h3>Historial de sesiones</h3>
          <p>
            Aparece cuando ya existe historia real. Se mantiene separado de la discografia.
          </p>
        </div>
      </div>

      <div className="writer-session-history-list">
        {history.map((session) => {
          const detail = detailsById[session.id];
          const isExpanded = expandedSessionId === session.id;
          const isLoading = loadingDetailIds.includes(session.id);
          const canResume = session.lifecycle === 'active';
          const canReviewImport = session.lifecycle === 'complete';

          return (
            <div
              key={session.id}
              className={`writer-session-history-item writer-session-history-item--${session.lifecycle}`}
            >
              <div className="writer-session-history-row">
                <div className="writer-session-history-main">
                  <strong>Sesion #{session.id}</strong>
                  <span>{session.brief_preview}</span>
                </div>
                <div className="writer-session-history-status">{session.lifecycle}</div>
                <div className="writer-session-history-meta">
                  {session.take_count} takes
                  <br />
                  {formatDate(session.updated_at)}
                </div>
                <div className="writer-session-history-actions">
                  {canResume && (
                    <button className="btn btn-primary" onClick={() => onResume(session.id)}>
                      Retomar
                    </button>
                  )}
                  {canReviewImport && (
                    <button className="btn btn-primary" onClick={() => onReviewImport(session.id)}>
                      Revisar import
                    </button>
                  )}
                  <button className="btn btn-secondary" onClick={() => onToggleSession(session.id)}>
                    {isExpanded ? 'Ocultar' : 'Ver sesion'}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="writer-session-history-detail">
                  {isLoading && <div className="writer-session-history-loading">Cargando detalle...</div>}
                  {!isLoading && detail && (
                    <>
                      <div className="writer-session-detail-brief">
                        <span className="writer-session-detail-label">Brief</span>
                        <div className="writer-session-detail-brief-grid">
                          <div>
                            <span>Formato</span>
                            <strong>{detail.brief.format}</strong>
                          </div>
                          <div>
                            <span>Tono</span>
                            <strong>{detail.brief.tone}</strong>
                          </div>
                          {detail.brief.word_limit ? (
                            <div>
                              <span>Limite</span>
                              <strong>{detail.brief.word_limit} palabras</strong>
                            </div>
                          ) : null}
                        </div>
                        {detail.brief.notes && (
                          <p className="writer-session-detail-notes">{detail.brief.notes}</p>
                        )}
                      </div>

                      <div className="writer-session-takes">
                        {detail.takes.map((take) => (
                          <article key={take.id} className="writer-session-take-card">
                            <div className="writer-session-take-top">
                              <div>
                                <span className="writer-session-detail-label">Take {take.take_number}</span>
                                <h4>{take.title || `Take ${take.take_number}`}</h4>
                              </div>
                              <div className="writer-session-take-meta">
                                {take.word_count} palabras
                                <br />
                                {formatDate(take.created_at)}
                              </div>
                            </div>
                            {take.iteration_notes && (
                              <p className="writer-session-take-notes">Notas: {take.iteration_notes}</p>
                            )}
                            <p className="writer-session-take-content">{take.content}</p>
                          </article>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
