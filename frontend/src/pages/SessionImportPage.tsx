import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type { Writer } from '../types';
import type {
  SessionImportChange,
  SessionImportProposalResponse,
} from '../types/studio';
import * as api from '../api/client';
import '../writing.css';
import '../import-flow.css';

type ImportPageState = 'loading' | 'ready' | 'submitting' | 'error';

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return 'none';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function getChangeTarget(change: SessionImportChange): string {
  return change.key ? `${change.field}.${change.key}` : change.field;
}

function getChangeSummary(change: SessionImportChange): string {
  if (change.action === 'modify') {
    return `${formatValue(change.old_value)} -> ${formatValue(change.new_value)}`;
  }
  if (change.action === 'add') {
    return `Add ${formatValue(change.value ?? change.new_value)}`;
  }
  return `Remove ${formatValue(change.value ?? change.old_value)}`;
}

export default function SessionImportPage() {
  const { writerId, sessionId } = useParams<{ writerId: string; sessionId: string }>();
  const navigate = useNavigate();

  const [writer, setWriter] = useState<Writer | null>(null);
  const [proposal, setProposal] = useState<SessionImportProposalResponse | null>(null);
  const [pageState, setPageState] = useState<ImportPageState>('loading');
  const [selectedIndexes, setSelectedIndexes] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  const parsedSessionId = sessionId ? Number(sessionId) : NaN;

  useEffect(() => {
    if (!writerId || !sessionId || Number.isNaN(parsedSessionId)) {
      navigate('/', { replace: true });
      return;
    }
    void loadPage(writerId, parsedSessionId);
  }, [writerId, sessionId]);

  const selectedChanges = useMemo(() => {
    if (!proposal) return [];
    return proposal.changes.filter((_, index) => selectedIndexes.includes(index));
  }, [proposal, selectedIndexes]);

  const loadPage = async (nextWriterId: string, nextSessionId: number) => {
    setPageState('loading');
    setError(null);

    try {
      const [writerResponse, proposalResponse] = await Promise.all([
        api.getWriter(nextWriterId),
        api.createSessionImportProposal(nextSessionId),
      ]);

      setWriter(writerResponse);
      setProposal(proposalResponse);
      setSelectedIndexes(proposalResponse.changes.map((_, index) => index));
      setPageState('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No pudimos preparar el import flow.');
      setPageState('error');
    }
  };

  const handleToggleChange = (index: number) => {
    setSelectedIndexes((current) =>
      current.includes(index)
        ? current.filter((value) => value !== index)
        : [...current, index].sort((a, b) => a - b)
    );
  };

  const handleImport = async () => {
    if (!writerId || !proposal || selectedChanges.length === 0) return;

    setPageState('submitting');
    setError(null);

    try {
      const response = await api.importSessionChanges(proposal.session_id, {
        changes: selectedChanges,
        reasoning: proposal.reasoning,
      });

      navigate('/writer/' + writerId, {
        replace: true,
        state: {
          sessionImportFeedback: {
            status: 'imported',
            sessionId: response.session_id,
            importedChanges: response.imported_changes,
            reasoning: response.reasoning,
          },
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No pudimos importar los cambios.');
      setPageState('ready');
    }
  };

  const handleSkip = async () => {
    if (!writerId || Number.isNaN(parsedSessionId)) return;

    setPageState('submitting');
    setError(null);

    try {
      const response = await api.skipSessionImport(parsedSessionId);
      navigate('/writer/' + writerId, {
        replace: true,
        state: {
          sessionImportFeedback: {
            status: 'skipped',
            sessionId: response.session_id,
          },
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No pudimos skipear esta sesion.');
      setPageState('ready');
    }
  };

  if (!writerId || !sessionId) {
    return null;
  }

  return (
    <div className="session-import-page">
      <nav className="studio-nav">
        <span className="session-import-step">Post-session import</span>
        <span className="studio-nav-title">
          {writer ? `Studio · ${writer.name}` : 'Studio'}
        </span>
        <div className="session-import-step session-import-step--status">
          Session {sessionId}
        </div>
      </nav>

      <div className="session-import-shell">
        <section className="session-import-hero">
          <p className="session-import-eyebrow">Studio to Identity</p>
          <h2>Revisa que queres volver permanente</h2>
          <p className="session-import-subtitle">
            La sesion ya quedo cerrada. Ahora decidis que aprendizajes pasan al
            general stats del writer.
          </p>
        </section>

        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        {pageState === 'loading' && (
          <div className="session-import-card session-import-card--loading">
            Revisando la sesion y generando propuesta...
          </div>
        )}

        {pageState === 'error' && (
          <div className="session-import-card">
            <p>No pudimos abrir este import flow.</p>
            <div className="session-import-actions">
              <button
                className="btn btn-secondary"
                onClick={() => void loadPage(writerId, parsedSessionId)}
              >
                Reintentar
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => navigate('/writer/' + writerId, { replace: true })}
              >
                Volver al Artist Profile
              </button>
            </div>
          </div>
        )}

        {pageState !== 'loading' && pageState !== 'error' && proposal && (
          <>
            <section className="session-import-card">
              <div className="session-import-card-header">
                <h3>Lectura de la sesion</h3>
                <span className="session-import-badge">
                  {proposal.changes.length} cambios propuestos
                </span>
              </div>
              <p className="session-import-reasoning">{proposal.reasoning}</p>
            </section>

            {proposal.changes.length === 0 ? (
              <section className="session-import-card session-import-card--empty">
                <h3>Sin aprendizaje durable</h3>
                <p>
                  El writer no aprendio nada durable en esta sesion. Podes
                  continuar y dejar la identidad como esta.
                </p>
                <div className="session-import-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => void handleSkip()}
                    disabled={pageState === 'submitting'}
                  >
                    {pageState === 'submitting' ? 'Cerrando...' : 'Continuar'}
                  </button>
                </div>
              </section>
            ) : (
              <>
                <section className="session-import-list" aria-label="Cambios propuestos">
                  {proposal.changes.map((change, index) => {
                    const isChecked = selectedIndexes.includes(index);
                    return (
                      <label
                        key={`${getChangeTarget(change)}-${index}`}
                        className={`session-import-change${isChecked ? ' session-import-change--selected' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToggleChange(index)}
                        />
                        <div className="session-import-change-body">
                          <div className="session-import-change-topline">
                            <span className="session-import-change-target">
                              {getChangeTarget(change)}
                            </span>
                            <span className={`session-import-change-action session-import-change-action--${change.action}`}>
                              {change.action}
                            </span>
                          </div>
                          <div className="session-import-change-summary">
                            {getChangeSummary(change)}
                          </div>
                          {change.reason && (
                            <p className="session-import-change-reason">{change.reason}</p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </section>

                <section className="session-import-footer">
                  <div className="session-import-selection">
                    {selectedChanges.length} de {proposal.changes.length} cambios listos para importar
                  </div>
                  <div className="session-import-actions">
                    <button
                      className="btn btn-ghost"
                      onClick={() => void handleSkip()}
                      disabled={pageState === 'submitting'}
                    >
                      Skipear
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={() => void handleImport()}
                      disabled={pageState === 'submitting' || selectedChanges.length === 0}
                    >
                      {pageState === 'submitting' ? 'Importando...' : 'Importar'}
                    </button>
                  </div>
                </section>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
