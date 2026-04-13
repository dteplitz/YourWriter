import { useState, useEffect, useRef } from 'react';
import type { SessionExperienceProps, Piece, ToolUseEvent } from '../types/studio';
import * as api from '../api/client';
import WritingArtifact from './WritingArtifact';
import IterationInput from './IterationInput';
import '../session.css';

type SessionState = 'streaming' | 'artifact' | 'done';

const phaseLabels: Record<string, string> = {
  outlining: 'Armando estructura...',
  drafting: 'Primer take...',
  refining: 'Mezclando...',
};

const LOADING_TIPS = [
  'El Studio pasa por research, estructura, borrador y refinado antes de darte la pieza.',
  'Mientras esperás, pensá en las notas del productor que vas a dejar para el próximo take.',
  'El Artist Profile es donde moldeás al writer. El Studio es donde escribe.',
  'Podés iterar tantas veces como quieras — cada take mantiene el contexto del anterior.',
  'Los cambios que pedís en el chat del Artist Profile moldean la identidad del writer con el tiempo.',
  'La discografía guarda todas las piezas del writer. Podés revisarlas entre sesiones.',
];

export default function SessionExperience({
  writerId,
  brief,
  onPieceSaved,
  onSessionEnd,
}: SessionExperienceProps) {
  const [sessionState, setSessionState] = useState<SessionState>('streaming');
  const [streamedText, setStreamedText] = useState('');
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [activeToolUse, setActiveToolUse] = useState<ToolUseEvent | null>(null);
  const [currentPiece, setCurrentPiece] = useState<Piece | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tipIndex, setTipIndex] = useState(0);
  const streamedTextRef = useRef('');
  const hasLaunchedRef = useRef(false);
  const pieceReceivedRef = useRef(false);
  const sessionIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (hasLaunchedRef.current) return;
    hasLaunchedRef.current = true;
    launchStream(brief.notes);
  }, []);

  useEffect(() => {
    if (streamedText) return;
    const interval = setInterval(() => {
      setTipIndex((i) => (i + 1) % LOADING_TIPS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [streamedText]);

  const launchStream = async (iterationNotes?: string) => {
    setSessionState('streaming');
    setStreamedText('');
    streamedTextRef.current = '';
    pieceReceivedRef.current = false;
    setCurrentPhase(null);
    setActiveToolUse(null);
    setError(null);
    setTipIndex(0);

    try {
      await api.sendStudioStream(
        writerId,
        brief,
        (token) => {
          streamedTextRef.current += token;
          setStreamedText(streamedTextRef.current);
          setCurrentPhase(null);
        },
        (phase) => {
          setCurrentPhase(phase);
        },
        (toolUseEvent) => {
          setActiveToolUse(toolUseEvent);
        },
        (_toolResultEvent) => {
          setActiveToolUse(null);
        },
        (piece) => {
          pieceReceivedRef.current = true;
          setCurrentPiece(piece);
          onPieceSaved?.(piece);
          setSessionState('artifact');
        },
        (newSessionId) => {
          sessionIdRef.current = newSessionId;
        },
        sessionIdRef.current ?? undefined,
        iterationNotes,
      );

      // If stream completed without emitting a piece event, surface what we have
      if (!pieceReceivedRef.current) {
        setSessionState('artifact');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error durante el stream');
      setSessionState('artifact');
    }
  };

  const handleIterate = (notes: string) => {
    setCurrentPiece(null);
    launchStream(notes || undefined);
  };



  // Scroll to IterationInput (the textarea is right below the artifact)
  const iterationInputRef = useRef<HTMLDivElement>(null);
  const handleIterateFromArtifact = () => {
    iterationInputRef.current?.querySelector('textarea')?.focus();
  };

  const handleFinish = () => {
    onSessionEnd();
    setSessionState('done');
  };

  const phaseLabel = currentPhase ? (phaseLabels[currentPhase] ?? currentPhase) : null;

  return (
    <div className="session-experience">
      {/* Streaming view */}
      {sessionState === 'streaming' && (
        <div className="session-stream">
          {phaseLabel && (
            <div className="phase-pill">
              <span className="phase-pill-dot pulse" />
              {phaseLabel}
            </div>
          )}

          {activeToolUse && (
            <div className="tool-use-pill">
              <span className="pulse">◉</span>
              Buscando: &ldquo;{activeToolUse.query}&rdquo;
            </div>
          )}

          {streamedText ? (
            <div className="session-stream-text">{streamedText}</div>
          ) : (
            <>
              {!phaseLabel && !activeToolUse && (
                <div className="session-stream-text session-stream-text--waiting">
                  Preparando el take...
                </div>
              )}
              <div className="session-loading-tip">
                {LOADING_TIPS[tipIndex]}
              </div>
            </>
          )}
        </div>
      )}

      {/* Artifact + iteration view */}
      {sessionState === 'artifact' && (
        <div className="session-artifact-view">
          {error && (
            <div className="session-error">{error}</div>
          )}

          {currentPiece ? (
            <>
              <WritingArtifact
                piece={currentPiece}
                onIterate={handleIterateFromArtifact}
                onFinish={handleFinish}
              />
              <div ref={iterationInputRef}>
                <IterationInput
                  onIterate={handleIterate}
                  disabled={false}
                />
              </div>
            </>
          ) : (
            /* Stream ended but no piece received — show raw text */
            <div className="writing-artifact">
              <div className="artifact-content">{streamedText}</div>
              <div className="artifact-actions">
                <button className="btn btn-ghost" onClick={handleFinish}>
                  Finalizar sesión
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {sessionState === 'done' && (
        <div className="session-done">
          <p>Sesión finalizada.</p>
        </div>
      )}
    </div>
  );
}
