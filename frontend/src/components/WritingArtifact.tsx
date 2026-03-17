import { useState } from 'react';
import type { Piece } from '../types/studio';

interface WritingArtifactProps {
  piece: Piece;
  onIterate: () => void;
  onFinish: () => void;
}

export default function WritingArtifact({ piece, onIterate, onFinish }: WritingArtifactProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(piece.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available — silently ignore
    }
  };

  return (
    <div className="writing-artifact">
      <div className="artifact-meta">
        <span className="artifact-format-badge">{piece.format}</span>
        <span>{piece.word_count} palabras</span>
      </div>

      {piece.title && (
        <div className="artifact-title">{piece.title}</div>
      )}

      <div className="artifact-content">{piece.content}</div>

      <div className="artifact-actions">
        <button
          className="btn btn-secondary"
          onClick={handleCopy}
        >
          {copied ? '¡Copiado!' : 'Copiar'}
        </button>
        <button
          className="btn btn-primary"
          onClick={onIterate}
        >
          Iterar
        </button>
        <button
          className="btn btn-ghost"
          onClick={onFinish}
        >
          Finalizar sesión
        </button>
      </div>
    </div>
  );
}
