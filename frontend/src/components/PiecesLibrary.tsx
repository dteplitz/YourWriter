import { useState, useEffect } from 'react';
import type { Piece } from '../types/studio';
import * as api from '../api/client';

interface PiecesLibraryProps {
  writerId: string;
}

function formatRelativeDate(isoDate: string): string {
  const now = new Date();
  const date = new Date(isoDate);
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'hoy';
  if (diffDays === 1) return 'ayer';
  if (diffDays < 7) return `hace ${diffDays} días`;
  if (diffDays < 14) return 'hace 1 semana';
  if (diffDays < 30) return `hace ${Math.floor(diffDays / 7)} semanas`;
  if (diffDays < 60) return 'hace 1 mes';
  return `hace ${Math.floor(diffDays / 30)} meses`;
}

function truncate(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars) + '…';
}

export default function PiecesLibrary({ writerId }: PiecesLibraryProps) {
  const [pieces, setPieces] = useState<Piece[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    loadPieces();
  }, [writerId]);

  const loadPieces = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getPieces(writerId);
      setPieces(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar las piezas');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedId(prev => (prev === id ? null : id));
  };

  return (
    <div className="pieces-library">
      <div className="pieces-library-header">
        <h3 className="pieces-library-title">Discografía</h3>
      </div>
      <div className="pieces-library-divider" />

      {loading && (
        <div className="pieces-library-empty">Cargando piezas...</div>
      )}

      {!loading && error && (
        <div className="pieces-library-error">{error}</div>
      )}

      {!loading && !error && pieces.length === 0 && (
        <div className="pieces-library-empty">
          Todavía no hay piezas. Entrá al Studio para crear la primera.
        </div>
      )}

      {!loading && !error && pieces.length > 0 && (
        <ul className="pieces-library-list">
          {pieces.map((piece) => (
            <li
              key={piece.id}
              className={`piece-item${expandedId === piece.id ? ' piece-item--expanded' : ''}`}
              onClick={() => toggleExpand(piece.id)}
            >
              <div className="piece-item-row">
                <span className="piece-item-format-badge">{piece.format}</span>
                <span className="piece-item-preview">
                  {expandedId === piece.id
                    ? piece.title || truncate(piece.content, 60)
                    : truncate(piece.title || piece.content, 60)}
                </span>
                <span className="piece-item-meta">
                  {piece.word_count} palabras · {formatRelativeDate(piece.created_at)}
                </span>
              </div>
              {expandedId === piece.id && (
                <div className="piece-item-content">{piece.content}</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
