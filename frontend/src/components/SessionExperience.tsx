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
  const streamedTextRef = useRef('');
  const hasLaunchedRef = useRef(false);
  const pieceReceivedRef = useRef(false);

  useEffect(() => {
    if (hasLaunchedRef.current) return;
    hasLaunchedRef.current = true;
    launchStream(brief.notes);
  }, []);

  const launchStream = async (notes?: string) => {
    setSessionState('streaming');
    setStreamedText('');
    streamedTextRef.current = '';
    pieceReceivedRef.current = false;
    setCurrentPhase(null);
    setActiveToolUse(null);
    setError(null);

    const briefWithNotes = notes
      ? { ...brief, notes: notes }
      : brief;

    try {
      await api.sendStudioStream(
        writerId,
        briefWithNotes,
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
          onPieceSaved(piece);
          setSessionState('artifact');
        },
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
            !phaseLabel && !activeToolUse && (
              <div className="session-stream-text session-stream-text--waiting">
                Preparando el take...
              </div>
            )
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
