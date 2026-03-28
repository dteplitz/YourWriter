import { useState } from 'react';
import type { Brief, Writer } from '../types';
import * as api from '../api/client';

type BriefState = 'input' | 'loading' | 'preview' | 'clarifying';

interface BriefSetupProps {
  writer: Writer;
  onStartSession: (brief: Brief) => void;
  onBack: () => void;
}

export default function BriefSetup({ writer, onStartSession, onBack }: BriefSetupProps) {
  const [briefState, setBriefState] = useState<BriefState>('input');
  const [message, setMessage] = useState('');
  const [clarificationAnswer, setClarificationAnswer] = useState('');
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeBrief = async (text: string) => {
    if (!text.trim()) return;
    setError(null);
    setBriefState('loading');
    try {
      const result = await api.sendBrief(writer.id, text.trim());
      setBrief(result);
      setBriefState(result.needs_clarification ? 'clarifying' : 'preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze brief');
      setBriefState('input');
    }
  };

  const handleAnalyze = () => {
    analyzeBrief(message);
  };

  const handleClarificationSubmit = () => {
    if (!clarificationAnswer.trim() || !brief) return;
    const combined = `${message}\n\nAclaración: ${clarificationAnswer.trim()}`;
    setClarificationAnswer('');
    analyzeBrief(combined);
  };

  const handleEditBrief = () => {
    setBriefState('input');
  };

  if (briefState === 'loading') {
    return (
      <div className="brief-setup">
        <div className="brief-setup-inner">
          <div className="brief-loading">
            <div className="brief-spinner" />
            <span>Analizando el brief...</span>
          </div>
        </div>
      </div>
    );
  }

  if (briefState === 'preview' && brief) {
    return (
      <div className="brief-setup">
        <div className="brief-setup-inner">
          <h2 className="brief-setup-title">Brief listo</h2>
          <div className="brief-card">
            <p className="brief-card-title">Detalles de la sesión</p>
            <div className="brief-field">
              <span className="brief-field-label">Formato</span>
              <span className="brief-field-value">{brief.format}</span>
            </div>
            <div className="brief-field">
              <span className="brief-field-label">Tono</span>
              <span className="brief-field-value">{brief.tone}</span>
            </div>
            {brief.word_limit && (
              <div className="brief-field">
                <span className="brief-field-label">Límite</span>
                <span className="brief-field-value">{brief.word_limit} palabras</span>
              </div>
            )}
            {brief.constraints_applied.length > 0 && (
              <div className="brief-field" style={{ flexDirection: 'column', gap: '0.5rem' }}>
                <span className="brief-field-label">Activos</span>
                <div className="brief-constraints">
                  {brief.constraints_applied.map((c) => (
                    <span key={c} className="brief-constraint-tag">{c}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="brief-actions">
            <button className="btn btn-secondary" onClick={handleEditBrief}>
              Editar
            </button>
            <button className="btn btn-primary" onClick={() => onStartSession(brief)}>
              Comenzar sesión
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (briefState === 'clarifying' && brief) {
    return (
      <div className="brief-setup">
        <div className="brief-setup-inner">
          <h2 className="brief-setup-title">Una pregunta antes de empezar</h2>
          <p className="brief-clarification-question">
            {brief.clarification_question}
          </p>
          <textarea
            className="brief-textarea"
            value={clarificationAnswer}
            onChange={(e) => setClarificationAnswer(e.target.value)}
            placeholder="Tu respuesta..."
            rows={3}
          />
          <div className="brief-actions">
            <button className="btn btn-secondary" onClick={handleEditBrief}>
              Volver
            </button>
            <button
              className="btn btn-primary"
              onClick={handleClarificationSubmit}
              disabled={!clarificationAnswer.trim()}
            >
              Continuar
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Default: 'input' state
  return (
    <div className="brief-setup">
      <div className="brief-setup-inner">
        <div className="brief-writer-header">
          <span className="brief-writer-name">{writer.name}</span>
          {writer.purpose && (
            <span className="brief-writer-purpose">{writer.purpose}</span>
          )}
        </div>
        <h2 className="brief-setup-title">¿Qué grabamos hoy?</h2>
        {error && (
          <p style={{ color: 'var(--danger)', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
            {error}
          </p>
        )}
        <textarea
          className="brief-textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Describí qué querés escribir hoy..."
          rows={5}
          autoFocus
        />
        <div className="brief-actions">
          <button className="btn btn-secondary" onClick={onBack}>
            Volver
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAnalyze}
            disabled={!message.trim()}
          >
            Analizar
          </button>
        </div>
      </div>
    </div>
  );
}
