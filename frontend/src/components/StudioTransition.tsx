import type { Writer, Piece } from '../types';

interface StudioTransitionProps {
  writer: Writer;
  recentPiece?: Piece;
  onEnter: () => void;
}

export default function StudioTransition({
  writer,
  recentPiece,
  onEnter,
}: StudioTransitionProps) {
  // identity is available on WriterWithIdentity — access safely
  const identity = (writer as any).identity ?? null;
  const emotions: Record<string, any> = identity?.emotions ?? {};
  const constraints: Record<string, any> = identity?.constraints ?? {};

  const emotionLabels = Object.entries(emotions)
    .filter(([, val]) => typeof val === 'string' || typeof val === 'number')
    .map(([, val]) => String(val))
    .slice(0, 3)
    .join(' · ');

  const constraintKeys = Object.keys(constraints).slice(0, 4);

  return (
    <div className="studio-transition">
      <div className="studio-transition-content">
        <p className="studio-label">Studio · {writer.name}</p>
        <h1 className="studio-writer-name">{writer.name}</h1>

        {emotionLabels && (
          <p className="studio-emotions">{emotionLabels}</p>
        )}

        {constraintKeys.length > 0 && (
          <ul className="studio-constraints-list">
            {constraintKeys.map((key) => (
              <li key={key} className="studio-constraint-badge">
                {key}
              </li>
            ))}
          </ul>
        )}

        {recentPiece && (
          <p className="studio-recent-piece">
            Last: <em>{recentPiece.title}</em>
          </p>
        )}

        <button className="btn btn-primary studio-enter-cta" onClick={onEnter}>
          Entrar
        </button>
      </div>
    </div>
  );
}
